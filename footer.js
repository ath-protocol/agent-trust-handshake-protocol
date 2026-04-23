// Custom footer copyright notice
(function() {
  function addCopyright() {
    const footer = document.querySelector('footer');
    if (footer && !document.getElementById('ath-copyright')) {
      const copyright = document.createElement('div');
      copyright.id = 'ath-copyright';
      copyright.style.cssText = 'margin-top:2rem;padding-top:1.5rem;border-top:1px solid rgba(128,128,128,0.2);text-align:center;font-size:0.875rem;color:rgba(128,128,128,0.7);line-height:1.5';
      copyright.innerHTML = 'Copyright \u00A9 Agent Trust Handshake Protocol Contributors.';
      footer.appendChild(copyright);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', addCopyright);
  } else {
    addCopyright();
  }

  const observer = new MutationObserver(addCopyright);
  observer.observe(document.body, { childList: true, subtree: true });
})();
