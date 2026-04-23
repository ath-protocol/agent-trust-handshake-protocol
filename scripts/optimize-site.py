#!/usr/bin/env python3
"""Post-build optimizer for Mintlify static export.

Adapted from https://github.com/A7um/ContextManagementBook/blob/main/scripts/optimize-book.py

Performs three optimizations on the exported _site/ directory:

1. Prefetch: injects <link rel="prefetch"> for sibling doc pages so sidebar
   navigation feels instant after the first page load.

2. Preload: injects <link rel="preload"> for critical CSS and font files,
   saving a round-trip on first paint.

3. Service Worker: writes sw.js and registers it from every page.  After the
   first visit all pages and assets are served cache-first with background
   refresh — repeat visits require zero network round-trips.

Also rewrites root-relative paths when BASE_PATH is set (for GitHub Pages
subpath hosting, e.g. /my-repo/).  This includes:
  - HTML href/src/content attributes
  - CSS url() references
  - Webpack publicPath in JS chunks
  - Next.js App Router basePath functions (hasBasePath / removeBasePath)
  - RSC flight data (assetPrefix + canonicalUrlParts)

Safe and idempotent: re-running is a no-op when markers are already present.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

SITE_DIR = Path(os.environ.get("SITE_DIR", "_site"))
BASE_PATH = os.environ.get("BASE_PATH", "")  # e.g. "/agent-trust-handshake-protocol"
MARKER = "<!-- optimize-site -->"

SW_CACHE_VERSION = "ath-docs-v3"


# ---------------------------------------------------------------------------
# 1. Path rewriting for subpath hosting
# ---------------------------------------------------------------------------


def rewrite_html_paths(html: str, base: str) -> str:
    """Rewrite root-relative paths in HTML for subpath hosting.

    Script tag interiors are left alone so that inline RSC flight data
    (self.__next_f.push) is not corrupted.  Only the <script src="...">
    attribute and RSC resource-hint paths (HL/HS directives) are rewritten.
    """
    parts = re.split(r"(<script[^>]*>.*?</script>)", html, flags=re.DOTALL)

    result_parts: list[str] = []
    for part in parts:
        if part.startswith("<script"):
            part = re.sub(r'(<script[^>]*\s(?:src|href))="/', rf'\1="{base}/', part)
            part = re.sub(
                r'(<link[^>]*\s(?:href|src))="/',
                rf'\1="{base}/',
                part,
            )
            part = part.replace(':HL[\\"/', f':HL[\\"{base}/')
            part = part.replace(':HS[\\"/', f':HS[\\"{base}/')
            part = part.replace('\\"p\\":\\"\\",', f'\\"p\\":\\"{base}\\",')
            part = part.replace(f"{base}{base}", base)
            result_parts.append(part)
        else:
            part = re.sub(r'(href|src|content)="/', rf'\1="{base}/', part)
            part = re.sub(r"url\(/", f"url({base}/", part)
            for prefix in (
                "_next/", "logo/", "favicons/", "favicon", "docs/",
                "specification/", "community/", "schema/", "sitemap",
                ".well-known/", "llms", "style.css", "zh/", "sw.js",
            ):
                part = part.replace(f'"{base}/{prefix}', f'"{base}/{prefix}')
                part = part.replace(f'"/{prefix}', f'"{base}/{prefix}')
            part = part.replace(f"{base}{base}", base)
            result_parts.append(part)

    return "".join(result_parts)


def rewrite_js_paths(js: str, base: str) -> str:
    """Rewrite critical root-relative paths in JS chunks."""
    js = js.replace('.p="/_next/"', f'.p="{base}/_next/"')
    js = js.replace('"/_next/data/"', f'"{base}/_next/data/"')
    js = js.replace('"/_next/image"', f'"{base}/_next/image"')
    js = js.replace('"/_next/"', f'"{base}/_next/"')

    for prefix in ("docs/", "specification/", "community/", "schema/", "zh/"):
        js = js.replace(f'href:"/{prefix}', f'href:"{base}/{prefix}')
    js = js.replace('href:"/', f'href:"{base}/')

    js = js.replace(f"{base}{base}", base)
    return js


def patch_nextjs_basepath(js: str, base: str) -> str:
    """Patch the Next.js hasBasePath / removeBasePath / addBasePath modules.

    Mintlify builds with basePath="" so the generated code is:
      hasBasePath(e)    → pathHasPrefix(e, "")   (always true)
      removeBasePath(e) → return e               (noop)
      addBasePath(e)    → addPathPrefix(e, "")    (noop)

    We rewrite these to use the actual base path so the App Router can
    reconcile window.location with the RSC canonical URL.
    """
    esc = base.replace("/", "\\/")

    js = re.sub(
        r'(function \w+\(e\)\{return\(0,\w+\.pathHasPrefix\)\(e,)""\)',
        rf'\1"{base}")',
        js,
    )

    js = re.sub(
        r'(\(0,\w+\.addPathPrefix\)\(e,)""\)',
        rf'\1"{base}")',
        js,
    )

    js = re.sub(
        r'(function (\w+)\(e\)\{return e\})(Object\.defineProperty\(t,"__esModule".*?"removeBasePath",\{enumerable:!0,get:function\(\)\{return \2\}\})',
        lambda m: m.group(0).replace(
            m.group(1),
            f'function {m.group(2)}(e){{return e.startsWith("{base}")?e.slice({len(base)})||"/":e}}',
        ),
        js,
    )

    return js


def rewrite_css_paths(css: str, base: str) -> str:
    """Rewrite root-relative url() references in CSS for subpath hosting."""
    css = re.sub(r'url\(/_next/', f'url({base}/_next/', css)
    css = css.replace(f"{base}{base}", base)
    return css


def rewrite_paths(site_dir: Path, base: str) -> int:
    """Rewrite all root-relative paths for subpath hosting. Returns count."""
    count = 0
    for html_path in site_dir.rglob("*.html"):
        original = html_path.read_text(encoding="utf-8")
        rewritten = rewrite_html_paths(original, base)
        if rewritten != original:
            html_path.write_text(rewritten, encoding="utf-8")
            count += 1

    for js_path in (site_dir / "_next").rglob("*.js"):
        original = js_path.read_text(encoding="utf-8")
        rewritten = rewrite_js_paths(original, base)
        rewritten = patch_nextjs_basepath(rewritten, base)
        if rewritten != original:
            js_path.write_text(rewritten, encoding="utf-8")
            count += 1

    for css_path in (site_dir / "_next").rglob("*.css"):
        original = css_path.read_text(encoding="utf-8")
        rewritten = rewrite_css_paths(original, base)
        if rewritten != original:
            css_path.write_text(rewritten, encoding="utf-8")
            count += 1
    return count


# ---------------------------------------------------------------------------
# 2. Prefetch links
# ---------------------------------------------------------------------------

def collect_pages(site_dir: Path) -> list[Path]:
    """Collect all page HTML files, sorted for deterministic output."""
    pages = []
    for p in sorted(site_dir.rglob("index.html")):
        rel = p.relative_to(site_dir)
        if any(seg.startswith("_") or seg.startswith(".") for seg in rel.parts[:-1]):
            continue
        pages.append(p)
    return pages


def build_prefetch_links(current: Path, pages: list[Path], site_dir: Path, base: str) -> str:
    """Build prefetch <link> tags for all pages except the current one."""
    links = []
    for p in pages:
        if p.resolve() == current.resolve():
            continue
        page_url = base + "/" + str(p.parent.relative_to(site_dir).as_posix()) + "/"
        page_url = page_url.replace("//", "/")
        links.append(f'<link rel="prefetch" href="{page_url}" />')
    return "\n    ".join(links)


# ---------------------------------------------------------------------------
# 3. Preload hints
# ---------------------------------------------------------------------------

def find_critical_assets(site_dir: Path, base: str) -> list[tuple[str, str]]:
    """Identify critical CSS and font files for preloading."""
    assets = []
    css_dir = site_dir / "_next" / "static" / "css"
    if css_dir.exists():
        for css in sorted(css_dir.glob("*.css")):
            rel = base + "/_next/static/css/" + css.name
            assets.append((rel, "style"))

    media_dir = site_dir / "_next" / "static" / "media"
    if media_dir.exists():
        for font in sorted(media_dir.glob("*-s.p.woff2")):
            rel = base + "/_next/static/media/" + font.name
            assets.append((rel, "font"))
    return assets


def build_preload_links(site_dir: Path, base: str) -> str:
    """Build preload <link> tags for critical assets."""
    assets = find_critical_assets(site_dir, base)
    links = []
    for href, as_type in assets:
        crossorigin = ' crossorigin="anonymous"' if as_type == "font" else ""
        links.append(f'<link rel="preload" href="{href}" as="{as_type}"{crossorigin} />')
    return "\n    ".join(links)


# ---------------------------------------------------------------------------
# 4. Service Worker
# ---------------------------------------------------------------------------

SERVICE_WORKER_JS = """\
const CACHE_VERSION = '__CACHE_VERSION__';
const CACHE_SCOPE = self.registration.scope;
const PRECACHE_URLS = __PRECACHE_URLS__;

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      cache.addAll(PRECACHE_URLS.map((u) => new Request(u, { cache: 'reload' })))
        .catch(() => {})
    )
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;
  if (!url.href.startsWith(CACHE_SCOPE)) return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        fetch(event.request).then((resp) => {
          if (resp && resp.status === 200 && resp.type === 'basic') {
            caches.open(CACHE_VERSION).then((c) => c.put(event.request, resp));
          }
        }).catch(() => {});
        return cached;
      }
      return fetch(event.request).then((resp) => {
        if (resp && resp.status === 200 && resp.type === 'basic') {
          const copy = resp.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(event.request, copy));
        }
        return resp;
      });
    })
  );
});
"""

SW_REGISTER_SNIPPET = """\
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('__BASE__/sw.js', { scope: '__BASE__/' }).catch(() => {});
  });
}
</script>"""


def generate_service_worker(site_dir: Path, pages: list[Path], base: str) -> None:
    """Write sw.js with a precache manifest of all pages and critical assets."""
    precache: list[str] = []
    for p in pages:
        page_url = base + "/" + str(p.parent.relative_to(site_dir).as_posix()) + "/"
        page_url = page_url.replace("//", "/")
        precache.append(page_url)

    for href, _ in find_critical_assets(site_dir, base):
        precache.append(href)

    precache_literal = "[\n  " + ",\n  ".join(f'"{u}"' for u in precache) + "\n]"
    sw_content = (
        SERVICE_WORKER_JS
        .replace("__PRECACHE_URLS__", precache_literal)
        .replace("__CACHE_VERSION__", SW_CACHE_VERSION)
    )
    (site_dir / "sw.js").write_text(sw_content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 5. Injection
# ---------------------------------------------------------------------------

def inject_into_html(html: str, prefetch: str, preload: str, sw_snippet: str) -> str | None:
    """Inject optimization tags before </head>. Returns None if already done."""
    if MARKER in html:
        return None

    head_close = html.find("</head>")
    if head_close == -1:
        return None

    injection = (
        f"\n    {MARKER}\n"
        f"    {preload}\n"
        f"    {prefetch}\n"
        f"    {sw_snippet}\n"
    )
    return html[:head_close] + injection + html[head_close:]


# ---------------------------------------------------------------------------
# 6. Directory redirects for GitHub Pages
# ---------------------------------------------------------------------------

REDIRECT_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
<title>Redirecting…</title>
</head>
<body><a href="{target}">Redirecting…</a></body>
</html>
"""


def create_directory_redirects(site_dir: Path, base: str) -> int:
    """Create index.html redirects for directories that lack one.

    Mintlify exports pages like specification/0.1/index/index.html but the
    tab link points to /specification/0.1 which resolves to the parent
    directory. GitHub Pages returns 404 because there is no index.html there.
    This creates a small redirect page in each such gap.
    """
    count = 0
    for dirpath in sorted(site_dir.rglob("*")):
        if not dirpath.is_dir():
            continue
        idx = dirpath / "index.html"
        if idx.exists():
            continue
        subdirs_with_index = [
            d for d in dirpath.iterdir()
            if d.is_dir() and (d / "index.html").exists()
        ]
        if not subdirs_with_index:
            continue
        target_name = subdirs_with_index[0].name
        target_url = base + "/" + str(dirpath.relative_to(site_dir).as_posix()) + "/" + target_name + "/"
        target_url = target_url.replace("//", "/")
        idx.write_text(REDIRECT_TEMPLATE.format(target=target_url), encoding="utf-8")
        count += 1
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not SITE_DIR.exists():
        print(f"error: {SITE_DIR} not found", file=sys.stderr)
        return 1

    base = BASE_PATH.rstrip("/")

    redirects = create_directory_redirects(SITE_DIR, base)
    if redirects:
        print(f"optimize-site: created {redirects} directory redirect(s)")

    if base:
        count = rewrite_paths(SITE_DIR, base)
        print(f"optimize-site: rewrote paths in {count} files (base: {base})")
    else:
        print("optimize-site: no BASE_PATH set, skipping path rewriting")

    pages = collect_pages(SITE_DIR)
    if not pages:
        print("error: no HTML pages found", file=sys.stderr)
        return 1
    print(f"optimize-site: {len(pages)} pages found")

    preload_block = build_preload_links(SITE_DIR, base)
    sw_snippet = SW_REGISTER_SNIPPET.replace("__BASE__", base)

    modified = 0
    for page in pages:
        html = page.read_text(encoding="utf-8")
        prefetch_block = build_prefetch_links(page, pages, SITE_DIR, base)
        result = inject_into_html(html, prefetch_block, preload_block, sw_snippet)
        if result is None:
            continue
        page.write_text(result, encoding="utf-8")
        modified += 1

    generate_service_worker(SITE_DIR, pages, base)
    sw_size = (SITE_DIR / "sw.js").stat().st_size / 1024
    print(f"optimize-site: injected into {modified} pages")
    print(f"optimize-site: wrote sw.js ({sw_size:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
