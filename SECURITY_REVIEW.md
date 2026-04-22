# ATH Protocol v0.1 — Security Review

**Date**: 2026-04-22
**Scope**: Full specification review of the Agent Trust Handshake Protocol v0.1
**Artifacts reviewed**: All files under `specification/0.1/`, `spec/openapi.yaml`, `schema/0.1/schema.json`, `docs/tutorials/security/`, and supporting documents.

---

## Security Model Confirmation

Before enumerating issues, this section confirms the protocol's intended security model as derived from the normative threat model (`specification/0.1/basic/threat-model.mdx`) and related specification documents.

### Trust Architecture

ATH v0.1 is an **application-layer** protocol that extends OAuth 2.0 with agent identity and a two-phase authorization model. The security model is structured as follows:

- **Trust root**: The ATH implementor (A4) — either a gateway (Gateway Mode) or the service itself (Native Mode). All protocol security guarantees terminate at A4. Compromise of A4 is explicitly out of scope (OOS6).
- **Two-phase authorization**: Phase A (app-side: implementor approves agent registration with constrained scopes) + Phase B (user-side: end user completes OAuth consent). Both phases are mandatory; neither can be bypassed.
- **Scope confinement via intersection**: `Effective = Agent Approved ∩ User Consented ∩ Requested`. No token may carry scopes outside this set.
- **Agent identity**: URI-based (`agent_id`), verified by fetching a public key from the agent's `.well-known/agent.json` and validating a signed JWT attestation (ES256 required, EdDSA recommended).
- **Token model**: Bearer tokens (RFC 6750) bound to `(agent_id, user_id, provider_id, scopes)`. Sender-constrained tokens (DPoP, mTLS) are recommended but not required in v0.1.
- **Transport security**: Delegates entirely to TLS 1.2+ (AS1–AS3). HSTS required.

### Actors and Trust Levels

| Actor | Trust Level |
|-------|-------------|
| End user (A1) | Honest but gullible |
| Agent runtime (A2) | Semi-trusted; identified by key, constrained by Phase A |
| Agent developer (A3) | Untrusted for identity claims |
| ATH implementor (A4) | Fully trusted (root of trust) |
| Upstream OAuth AS (A5) | Trusted to implement RFC 6749 / RFC 9700 |
| Upstream resource server (A6) | Trusted within its own model |

### In-Scope Attackers

| ID | Attacker | Summary |
|----|----------|---------|
| T1 | Malicious agent | Controls agent runtime; tries to exceed approval, impersonate, or steal tokens |
| T2 | Malicious local user | Legitimate credentials; tries to escape tenant isolation or hijack sessions |
| T3 | Side-channel observer | Learns protocol message contents despite TLS (Referer, logs, extensions, screen sharing) |
| T4 | Phishing attacker | Social engineering; operates counterfeit pages; limited by browser same-origin policy |

### Security Goals (G1–G10)

G1 Agent identity integrity, G2 App-side authorization non-bypass, G3 User-side authorization non-bypass, G4 Scope confinement, G5 Session integrity, G6 Token unforgeability/containment, G7 Revocation responsiveness, G8 Phishing surface minimization, G9 Mix-up resistance, G10 Interoperability consistency.

---

## Findings

### CRITICAL

#### C1. Revocation endpoint lacks authentication — enables unauthorized token revocation

**Affected spec**: `server/revocation.mdx`, `spec/openapi.yaml` (TokenRevocationRequest), `schema/0.1/schema.json` (TokenRevocationRequest)
**Goals threatened**: G6, G7
**Attackers**: T1, T2, T3

`POST /ath/revoke` requires only `client_id` and `token`. It does not require `client_secret` or `agent_attestation`. The `client_id` is not a secret — it may appear in logs, URLs, or be guessable.

**Impact**: Any party who learns or guesses a valid `(client_id, token)` pair can revoke the token. A T3 side-channel observer who captures a token can immediately revoke it, causing denial of service to the legitimate agent. A T2 malicious local user can weaponize revocation to disrupt other tenants' agents. Furthermore, the spec does not state that the `client_id` must match the token's binding — without that check, any `client_id` could revoke any token.

**Comparison**: RFC 7009 (OAuth Token Revocation) requires client authentication for the revocation endpoint. ATH's omission of this is a deviation from established security practice.

**Recommendation**: Require `client_secret` (or a fresh `agent_attestation`) in the revocation request. Validate that the presented `client_id` matches the token's bound `agent_id`. Consider making revocation idempotent and not revealing whether the token existed (per RFC 7009 §2.2).

---

#### C2. Token exchange content type contradicts own security requirement

**Affected spec**: `specification/0.1/basic/security.mdx` (line 24), `spec/openapi.yaml` (lines 131–165), `schema/0.1/schema.json` (TokenExchangeRequest)
**Goals threatened**: G10 (Interoperability consistency)
**Attackers**: All (specification defect creates implementation divergence)

The normative security requirement states:

> Token exchange requests MUST use `application/x-www-form-urlencoded` content type per RFC 6749 §4.1.3

However, the OpenAPI specification defines the `/ath/token` endpoint with `application/json` content type, and the `TokenExchangeRequest` schema is defined as a JSON object. All documentation examples show JSON request bodies.

**Impact**: This is a direct internal contradiction within the normative specification. Implementors following the OpenAPI (the machine-readable contract) will produce JSON token requests that violate the security requirement. Implementors following the security section will produce form-encoded requests that fail against OpenAPI-generated servers. This violates G10 and creates a class of interoperability failures. Additionally, deviating from RFC 6749's form-encoded requirement breaks compatibility with standard OAuth middleware and may expose implementations to JSON-specific injection vectors that OAuth's form-encoded design intentionally avoids.

**Recommendation**: Resolve the contradiction. Either update the OpenAPI/schema to use `application/x-www-form-urlencoded` (preferred, aligns with OAuth standards), or remove the form-encoded MUST from the security section and document why JSON was chosen instead.

---

### HIGH

#### H1. `state` parameter is optional — weakens CSRF and session fixation protection

**Affected spec**: `schema/0.1/schema.json` (AuthorizationRequest), `spec/openapi.yaml` (AuthorizationRequest), `specification/0.1/server/authorization.mdx`
**Goals threatened**: G5 (Session integrity)
**Attackers**: T1, T4

The `state` parameter in `AuthorizationRequest` is not listed in the `required` array. It is described as "Opaque state parameter for CSRF protection" but its use is entirely optional.

**Impact**: Without a mandatory `state`, the authorization flow is vulnerable to CSRF attacks (T4) and session fixation. A T1 malicious agent or T4 phishing attacker could induce a user to complete an OAuth consent flow that binds the resulting token to the attacker's session rather than the user's intended session. While PKCE protects the code exchange from interception, it does not prevent a CSRF attack where the attacker initiates the flow. OAuth 2.0 Security BCP (RFC 9700, §4.7) recommends `state` as mandatory.

**Recommendation**: Move `state` to the `required` array in both the JSON Schema and OpenAPI. The implementor MUST validate `state` on the callback, rejecting any response where `state` does not match the value bound to the user's session.

---

#### H2. No `jti` (JWT ID) claim required in agent attestation — enables replay attacks

**Affected spec**: `specification/0.1/basic/identity.mdx` (Required Claims), `schema/0.1/schema.json`
**Goals threatened**: G1 (Agent identity integrity)
**Attackers**: T3

The attestation JWT's required claims are `iss`, `sub`, `aud`, `iat`, `exp`. The `jti` claim is absent from the required set. The threat model mentions `jti` in AS9 (entropy requirements) but does not mandate its inclusion.

**Impact**: A T3 side-channel observer who captures a valid attestation JWT (from Referer headers, logs, browser extensions, etc.) can replay it against the same implementor for the full remaining validity of the token. Without `jti` and server-side replay detection, there is no way to distinguish a legitimate use from a replay. This is especially dangerous because the attestation is used for both registration and authorization — replaying it could initiate unauthorized authorization flows.

**Recommendation**: Add `jti` to the required claims. Mandate that implementors maintain a replay cache of seen `jti` values for the lifetime of each attestation (until `exp`). Alternatively, require very short-lived attestations (e.g., 60 seconds) to minimize the replay window.

---

#### H3. Agent identity document has no caching or freshness requirements — stale keys accepted after rotation

**Affected spec**: `specification/0.1/basic/identity.mdx` (Verification procedure)
**Goals threatened**: G1 (Agent identity integrity), G7 (Revocation responsiveness)
**Attackers**: T1

The verification procedure says to fetch the agent identity document and extract the public key, but specifies no caching policy, no `Cache-Control` requirements, and no maximum staleness.

**Impact**: An implementor may cache an agent's public key for hours or days. If the agent's private key is compromised and the developer rotates the key (publishing a new public key), the implementor continues to accept attestations signed by the compromised key until its cache expires. This window could be indefinitely long. Combined with absent `jti`, a compromised key yields unlimited impersonation until the cache is manually flushed.

**Recommendation**: Specify a MUST for maximum cache lifetime (e.g., 5 minutes). Require the identity document to include `Cache-Control` headers. Provide a mechanism for emergency key revocation that doesn't depend on cache expiry (e.g., an `agent_key_revocation_endpoint` or OCSP-like check).

---

#### H4. `redirect_uris` is optional at registration but redirect validation depends on it

**Affected spec**: `specification/0.1/server/registration.mdx`, `specification/0.1/basic/threat-model.mdx` (G8), `schema/0.1/schema.json` (AgentRegistrationRequest)
**Goals threatened**: G8 (Phishing surface minimization)
**Attackers**: T1, T4

G8 requires: "`user_redirect_uri` MUST be validated against a pre-registered list (`redirect_uris`) using exact-match comparison." However, `redirect_uris` is optional in `AgentRegistrationRequest` — it is not in the `required` array.

**Impact**: If an agent registers without providing `redirect_uris`, the implementor has no allowlist to validate against. This creates dangerous ambiguity: a permissive implementation that allows any `user_redirect_uri` when no list was registered enables open redirect attacks. A T1 malicious agent or T4 phishing attacker could redirect users to attacker-controlled pages after consent, potentially stealing authorization codes or confusing users. A strict implementation that blocks all redirects when none are registered breaks legitimate agents that forgot the optional field.

**Recommendation**: Either make `redirect_uris` required in the registration request, or add a normative rule that if `redirect_uris` is not provided, the implementor MUST reject any authorization request that includes `user_redirect_uri`.

---

#### H5. `GET /ath/agents/{clientId}` has no authentication — information disclosure

**Affected spec**: `spec/openapi.yaml` (lines 73–99)
**Goals threatened**: G2 (App-side authorization non-bypass, indirectly)
**Attackers**: T1, T2

The agent status endpoint has no authentication requirement. Any caller can query the registration status, approved scopes, and provider approvals of any agent by its `clientId`.

**Impact**: A T1 or T2 attacker can enumerate registered agents, discover which providers they are approved for, and learn their approved scope sets. This information aids in planning targeted attacks: knowing which scopes are approved helps a T1 craft authorization requests that will succeed, and knowing other agents' capabilities helps T2 in impersonation strategies. The `clientId` space can be brute-forced if the format is predictable (e.g., `ath_travelbot_001`).

**Recommendation**: Require authentication (at minimum `client_secret` or `agent_attestation`) for this endpoint. Alternatively, restrict it to return information only about the caller's own registration.

---

### MEDIUM

#### M1. `public_key` field has no type constraint — type confusion risk

**Affected spec**: `schema/0.1/schema.json` (AgentIdentityDocument, line 180–182)
**Goals threatened**: G1 (Agent identity integrity)
**Attackers**: T1

The `public_key` field in the agent identity document schema has a `description` but no `type` constraint. It can be any JSON value: string, object, array, number, boolean, or null.

**Impact**: Implementations that parse `public_key` permissively may be vulnerable to type confusion attacks. A T1 attacker could publish a `public_key` value that exploits parsing differences between implementations (e.g., a number that is coerced to a string in one library but causes an error in another, or an array that triggers unexpected behavior). This can lead to signature verification bypasses or denial of service.

**Recommendation**: Constrain the type to `"type": ["string", "object"]` to allow PEM (string) or JWK (object) formats only. Better yet, define separate subschemas for each format with appropriate validation.

---

#### M2. No maximum lifetime specified for ATH access tokens

**Affected spec**: `specification/0.1/basic/threat-model.mdx` (Known Limitations), `schema/0.1/schema.json` (TokenResponse)
**Goals threatened**: G6 (Token containment)
**Attackers**: T1, T3

The known limitations section acknowledges bearer token theft risk (OOS17) and notes "Implementors may issue longer-lived tokens to mitigate UX friction." No MUST or SHOULD bound on `expires_in` is specified.

**Impact**: Without a maximum, implementors could issue tokens valid for days, weeks, or even indefinitely. Since v0.1 uses bearer tokens, a longer-lived token dramatically increases the blast radius of token theft (OOS17). The spec acknowledges this risk but provides no guardrail against it.

**Recommendation**: Specify a RECOMMENDED maximum token lifetime (e.g., 1 hour) and a MUST NOT exceed ceiling (e.g., 24 hours). If longer access is needed, address it through the planned refresh token mechanism.

---

#### M3. Token response leaks `user_consented` scopes to the agent

**Affected spec**: `specification/0.1/basic/scope-intersection.mdx`, `schema/0.1/schema.json` (ScopeIntersection, TokenResponse)
**Goals threatened**: G8 (Phishing surface minimization, by extension)
**Attackers**: T1

The `scope_intersection` in the token response includes `user_consented` — the full set of scopes the user approved, even those not in the effective set.

**Impact**: A T1 malicious agent learns exactly which additional scopes the user is willing to consent to (e.g., the user consented to `mail:send` but the agent was only approved for `mail:read`). The agent can use this information for targeted social engineering: re-registering with a different identity to obtain broader Phase A approval for the scopes it now knows the user will accept. This is an information leak that violates the principle of least disclosure.

**Recommendation**: Remove `user_consented` from the response to the agent, or replace it with a boolean indicating whether the user's consent was broader than the effective set. The full breakdown can be logged server-side for audit without exposing it to the agent.

---

#### M4. No attestation freshness enforcement — `iat` is not required to be recent

**Affected spec**: `specification/0.1/basic/identity.mdx` (Verification procedure)
**Goals threatened**: G1 (Agent identity integrity)
**Attackers**: T1, T3

The verification procedure checks `exp` (not expired) and `aud` (matches verifier) but does not require `iat` to be recent. An attestation with `iat` weeks in the past but `exp` far in the future would pass validation.

**Impact**: A T1 attacker or T3 side-channel observer can stockpile long-lived attestation JWTs pre-signed by the agent's key. Even after key rotation, these pre-signed tokens remain valid until `exp`. Combined with H3 (no cache freshness), this extends the usability of a compromised key beyond what `exp` alone suggests.

**Recommendation**: Require implementors to validate that `iat` is within a bounded window (RECOMMENDED: 5 minutes of the current time). This limits both pre-computed stockpiling and replay utility.

---

#### M5. No `iss` parameter in ATH's own authorization response — mix-up attack surface

**Affected spec**: `specification/0.1/server/authorization.mdx` (AuthorizationResponse), `specification/0.1/basic/threat-model.mdx` (G9)
**Goals threatened**: G9 (Mix-up resistance)
**Attackers**: T1

G9 (Mix-up resistance) is stated as a goal, and AS6 mentions RFC 9207 (`iss` in authorization responses) for the upstream AS. However, the ATH implementor's own authorization response (`POST /ath/authorize` response) does not include any implementor identifier.

**Impact**: When an agent interacts with multiple ATH implementors concurrently, a T1 attacker operating a malicious implementor can perform a mix-up attack: the malicious implementor returns an `authorization_url` and `ath_session_id` from a legitimate implementor, causing the agent to complete a flow at the wrong implementor and deliver the resulting code/token to the attacker. Without an implementor identifier in the response, the agent cannot verify which implementor actually produced the response.

**Recommendation**: Add a mandatory `ath_implementor_id` (or `iss`) field to `AuthorizationResponse` and `TokenResponse`. The agent MUST verify this matches the implementor it sent the request to.

---

#### M6. Proxy endpoint HTTP method inconsistency and path traversal surface

**Affected spec**: `spec/openapi.yaml` (lines 167–217), `specification/0.1/server/proxy.mdx`
**Goals threatened**: G4 (Scope confinement)
**Attackers**: T1

The OpenAPI spec defines only `GET` for `/ath/proxy/{providerId}/{path}`, but the MDX specification says `ANY /ath/proxy/{provider_id}/{path}`. Additionally, the `{path}` parameter is user-controlled with no normalization requirements beyond the AS10 assumption.

**Impact**: The method inconsistency means some implementations may only allow GET while others allow all methods including POST, PUT, DELETE. A T1 attacker using an implementation that follows the MDX (allowing ANY) could perform write operations against the upstream service that the implementor intended to be read-only. The `{path}` parameter, without explicit path traversal prevention rules in the protocol itself, relies entirely on AS10 (an assumption on the implementor, not a protocol constraint).

**Recommendation**: Resolve the HTTP method inconsistency. If all methods are intended, update the OpenAPI to use `any` or list all methods. Add a normative requirement that the `{path}` parameter MUST be normalized (resolved `.` and `..`, stripped leading slashes) before constructing the upstream URL, and MUST NOT escape the intended upstream API base path.

---

#### M7. No replay protection on `POST /ath/authorize` request

**Affected spec**: `specification/0.1/server/authorization.mdx`
**Goals threatened**: G5 (Session integrity)
**Attackers**: T3

The authorization request from agent to implementor includes no nonce or idempotency key. The `state` parameter (even if made mandatory per H1) is for the OAuth redirect, not for the agent-to-implementor request itself.

**Impact**: A T3 side-channel observer who captures an authorization request (including the attestation JWT — see H2) can replay it multiple times, generating multiple valid `ath_session_id` values. Each session triggers an independent OAuth flow, potentially confusing the user or the implementor's session tracking. At scale, this enables session exhaustion DoS.

**Recommendation**: Require a request-level nonce (distinct from `state`) that the implementor records and enforces as single-use. Alternatively, require the `ath_session_id` to be deterministically bound to the attestation's `jti` so that replayed attestations produce the same session rather than new ones.

---

#### M8. `ath_session_id` has no specified lifetime or expiry

**Affected spec**: `specification/0.1/server/authorization.mdx`, `specification/0.1/server/token.mdx`
**Goals threatened**: G5 (Session integrity), G6 (Token containment)
**Attackers**: T2, T3

The `ath_session_id` is issued during authorization and consumed during token exchange, but the spec does not mandate a maximum session lifetime, expiry, or single-use constraint.

**Impact**: A long-lived session allows a T3 attacker who captures the `ath_session_id` a large window to complete the token exchange (if they also obtain the authorization code). Without a single-use constraint, the same session could theoretically be used for multiple token exchanges. The `SESSION_EXPIRED` error code exists in the schema but no normative text defines when a session expires.

**Recommendation**: Add a MUST for maximum session lifetime (RECOMMENDED: 10 minutes). Mandate that `ath_session_id` is single-use — consumed upon successful token exchange.

---

### LOW

#### L1. No agent key rotation mechanism specified

**Affected spec**: `specification/0.1/basic/identity.mdx` (Agent Identity Document)
**Goals threatened**: G1 (Agent identity integrity)

The agent identity document has a single `public_key` field. No mechanism is defined for:
- Publishing multiple keys (e.g., current + next for rollover)
- Signaling key rotation (e.g., `kid` matching between identity document and JWT header)
- Emergency key revocation (beyond removing the old key from the document)

**Impact**: Key rotation is operationally difficult. During rotation, attestations signed by the old key are immediately invalid once the document is updated, causing a brief availability outage. There is no way for an implementor to know a rotation happened vs. a key compromise.

**Recommendation**: Support JWKS (JSON Web Key Set) format for the `public_key` field, allowing multiple keys with `kid` identifiers. Define a key rotation protocol or at minimum recommend overlapping key validity periods.

---

#### L2. Error `details` field allows arbitrary JSON — information leakage risk

**Affected spec**: `schema/0.1/schema.json` (ATHError, line 524–527)
**Goals threatened**: G10 (Interoperability consistency)

`ATHError.details` is typed as `"type": "object", "additionalProperties": true` with no constraints on what may be included.

**Impact**: Implementations may inadvertently include sensitive information in error details: stack traces, internal state, database query fragments, or internal IP addresses. This aids T1/T2 attackers in reconnaissance. Without defined constraints, each implementation's error details will differ, undermining G10.

**Recommendation**: Define an explicit schema for `details` that limits fields to protocol-relevant information. Add a MUST NOT for including internal implementation details, stack traces, or credential material in error responses.

---

#### L3. No CORS requirements for ATH endpoints

**Affected spec**: (Not addressed anywhere in the specification)
**Goals threatened**: G5, G8

The specification does not address Cross-Origin Resource Sharing (CORS) policy for ATH endpoints.

**Impact**: Without CORS guidance, an implementor might set permissive CORS headers (e.g., `Access-Control-Allow-Origin: *`). This would allow a T4 attacker's malicious webpage to make cross-origin requests to ATH endpoints from a victim's browser, potentially initiating authorization flows or calling the proxy endpoint using cookies/credentials the browser automatically includes.

**Recommendation**: Add a normative requirement that ATH endpoints MUST NOT include permissive CORS headers unless specifically required for the deployment's browser-based agent architecture. If browser-based agents are supported, CORS origins MUST be restricted to registered agent origins.

---

#### L4. No rate limiting specified for registration endpoint

**Affected spec**: `specification/0.1/basic/security.mdx` (Rate Limiting section)
**Goals threatened**: G7 (Revocation responsiveness, indirectly — resource exhaustion)

Rate limiting is SHOULD-level for per-agent API calls but there is no mention of rate limiting on `/ath/agents/register` specifically.

**Impact**: An attacker can perform mass registration attempts, potentially exhausting the implementor's database, triggering costly attestation verification operations (fetching identity documents, verifying JWTs), or filling the agent registry with garbage entries that make legitimate agent review harder.

**Recommendation**: Add a SHOULD for rate limiting on the registration endpoint, including per-IP and per-developer-id throttling.

---

#### L5. Discovery document `agent_registration_endpoint` could be an open redirect target

**Affected spec**: `specification/0.1/basic/discovery.mdx` (Gateway Catalog Discovery)
**Goals threatened**: G8 (Phishing surface minimization)

The discovery document at `/.well-known/ath.json` includes an `agent_registration_endpoint` URL. Agents are expected to follow this URL to register.

**Impact**: If an attacker can manipulate the discovery document (e.g., via a compromised CDN or misconfigured cache), they can redirect agent registration requests (which include `agent_attestation` JWTs and developer credentials) to an attacker-controlled endpoint. While TLS protects the initial fetch, CDN-level and DNS-level attacks are partially realistic in enterprise environments.

**Recommendation**: Recommend that agents validate that the `agent_registration_endpoint` URL has the same origin as the discovery document URL, or is on a pre-configured allowlist. Consider signing the discovery document.

---

#### L6. `client_secret` generation and entropy requirements are implicit

**Affected spec**: `specification/0.1/basic/threat-model.mdx` (AS9), `schema/0.1/schema.json` (AgentRegistrationResponse)
**Goals threatened**: G6 (Token unforgeability)

AS9 requires 128 bits of entropy for random values including `client_secret`, but this is stated as an assumption on the implementor, not as a format constraint. The schema example `"ath_secret_xxxxx"` suggests a short, potentially weak format.

**Impact**: If implementors do not follow AS9 strictly, weak `client_secret` values could be brute-forced, allowing T1 or T2 attackers to impersonate agents at the token exchange step.

**Recommendation**: Add a minimum length requirement to the `client_secret` schema (e.g., `minLength: 32`). Consider recommending a specific format (e.g., base64url-encoded 256-bit random).

---

## Summary Table

| ID | Severity | Title | Goals | Attackers |
|----|----------|-------|-------|-----------|
| C1 | **Critical** | Revocation endpoint lacks authentication | G6, G7 | T1, T2, T3 |
| C2 | **Critical** | Token exchange content type contradicts security requirement | G10 | All |
| H1 | **High** | `state` parameter is optional | G5 | T1, T4 |
| H2 | **High** | No `jti` required in attestation — replay attacks | G1 | T3 |
| H3 | **High** | No caching/freshness requirements for agent identity documents | G1, G7 | T1 |
| H4 | **High** | `redirect_uris` optional but redirect validation depends on it | G8 | T1, T4 |
| H5 | **High** | Agent status endpoint has no authentication | G2 | T1, T2 |
| M1 | **Medium** | `public_key` has no type constraint | G1 | T1 |
| M2 | **Medium** | No maximum token lifetime specified | G6 | T1, T3 |
| M3 | **Medium** | Token response leaks `user_consented` scopes | G8 | T1 |
| M4 | **Medium** | No attestation `iat` recency enforcement | G1 | T1, T3 |
| M5 | **Medium** | No `iss` in ATH authorization response — mix-up risk | G9 | T1 |
| M6 | **Medium** | Proxy endpoint method inconsistency and path traversal | G4 | T1 |
| M7 | **Medium** | No replay protection on authorize request | G5 | T3 |
| M8 | **Medium** | `ath_session_id` has no specified lifetime | G5, G6 | T2, T3 |
| L1 | **Low** | No key rotation mechanism | G1 | — |
| L2 | **Low** | Error `details` allows arbitrary JSON | G10 | — |
| L3 | **Low** | No CORS requirements specified | G5, G8 | T4 |
| L4 | **Low** | No rate limiting on registration endpoint | — | T1, T2 |
| L5 | **Low** | Discovery document lacks integrity protection | G8 | T4 |
| L6 | **Low** | `client_secret` entropy requirements are implicit | G6 | T1, T2 |

**Total**: 2 Critical, 5 High, 8 Medium, 6 Low

---
---

# Part II — Protocol-Layer Analysis

**Date**: 2026-04-22
**Scope**: Deep structural analysis of the ATH v0.1 protocol state machine, cross-layer bindings, and handshake flow mechanics. This section focuses on protocol-level design flaws — the kind that cannot be fixed by an individual implementor following the spec more carefully, because the spec itself is structurally incomplete.

**Methodology**: Each finding below was discovered by tracing the actual data that flows between each protocol step, asking "what binds step N to step N+1?" and "what proves to party X that party Y actually performed step Z?". The analysis covers:
- The Phase A → Phase B cryptographic binding chain
- The ATH session state machine and its interaction with the underlying OAuth flow
- The proxy enforcement model and its relationship to scope semantics
- Gateway Mode vs. Native Mode security parity
- The identity layer's interaction with the token layer

Each finding is classified under the protocol's own security model (goals G1–G10, attackers T1–T4, assumptions AS1–AS10).

---

## CRITICAL

### P1. Phase A → Phase B binding is severed: `client_id`/`client_secret` are the only link — and they are static shared secrets

**Layer**: Registration (Phase A) ↔ Authorization (Phase B) binding
**Goals threatened**: G1, G2, G3, G5
**Attackers**: T1 (especially T1 colluding with T2)

#### The binding gap

Phase A produces `(client_id, client_secret, approved_scopes)`. Phase B starts with the agent presenting `client_id` + a fresh `agent_attestation` at `POST /ath/authorize`. The token exchange at `POST /ath/token` uses `client_id` + `client_secret` + `ath_session_id` + `code`.

The **only** cryptographic link between these two phases is the `client_secret` — a static shared secret issued once at registration time. There is no proof-of-possession at token exchange. Specifically:

1. **The attestation JWT is not required at token exchange.** The `TokenExchangeRequest` schema requires `client_id`, `client_secret`, `code`, `ath_session_id`, and `grant_type`. It does not require `agent_attestation`. This means the token exchange is authenticated solely by a static shared secret, not by proof of the agent's private key.

2. **The `client_secret` is a long-lived symmetric credential.** It never expires (no rotation mechanism is specified), and it is transmitted in every token exchange. If a T3 observer or T2 tenant captures the `client_secret` (which is sent in the request body of every token exchange — potentially logged, captured in APM, or visible to middleware), they can perform unlimited token exchanges for any session they also capture or initiate.

3. **The attestation at `POST /ath/authorize` is not bound to the resulting `ath_session_id`.** The implementor verifies the attestation when creating the session, but the spec does not require the implementor to store a binding between the attestation (or the agent's public key fingerprint) and the `ath_session_id`. At token exchange time, there is no mechanism to prove that the same private key that initiated the authorization is the one completing it.

#### Attack scenario (T1 + T3)

Agent X registers legitimately (Phase A) and obtains `client_id_X` + `client_secret_X`. A T3 side-channel observer captures `client_secret_X` from a log or error-reporting sink. The observer can now:
- Call `POST /ath/authorize` with their own attestation (they control a different agent key) but using `client_id_X` — the spec checks the attestation against the `client_id`'s registration, but...
- The spec says the implementor "MUST verify the attestation JWT is valid" and "MUST verify the agent is registered" — but does not say the attestation's `sub` (agent_id) must match the `client_id`'s registered `agent_id`. This is an implicit assumption never stated as a MUST.
- Even if that check exists, the observer waits for a legitimate agent X to call `POST /ath/authorize` and captures the `ath_session_id`. Then at token exchange, they present `client_id_X` + `client_secret_X` + the captured `ath_session_id` + the code (if also captured via side channel). No fresh attestation is needed.

This breaks G1 (the agent's identity is not cryptographically proven at token exchange), G3 (the consent flow may be completed by a different party), and G5 (the session initiated by one party is completed by another).

#### Root cause

The protocol uses a static shared secret (`client_secret`) where it should require proof-of-possession of the agent's private key. The attestation JWT — the protocol's own proof-of-possession mechanism — is absent from the most security-critical step (token exchange).

#### Recommendation

- **Require `agent_attestation` in the `TokenExchangeRequest`** with the `aud` claim set to the token endpoint. This binds the token exchange to current possession of the agent's private key.
- **Bind the `ath_session_id` to the attestation's public key fingerprint** at creation time, and verify the same fingerprint at token exchange.
- **Define `client_secret` rotation** and a maximum lifetime.
- **Explicitly state as a MUST** that the attestation's `sub` claim must match the `client_id`'s registered `agent_id` at every endpoint that accepts both.

---

### P2. The OAuth authorization code is delivered to the agent, but PKCE is held by the implementor — creating a split-knowledge gap that the protocol does not close

**Layer**: ATH authorization flow ↔ underlying OAuth flow
**Goals threatened**: G3, G5
**Attackers**: T1, T2

#### The architectural problem

In the ATH flow:
1. Agent calls `POST /ath/authorize` → Implementor generates PKCE `code_verifier` / `code_challenge`, stores verifier server-side, returns `authorization_url` (containing `code_challenge`) and `ath_session_id`.
2. User visits `authorization_url`, consents, upstream AS redirects callback to **the ATH implementor** (per "the OAuth callback is handled by the ATH implementor").
3. Agent calls `POST /ath/token` with `code` + `ath_session_id` → Implementor exchanges code at upstream AS using stored `code_verifier`.

But there is a critical ambiguity: **how does the agent get the `code`?**

The `TokenExchangeRequest` requires a `code` field described as "OAuth authorization code from the callback." The authorization spec says "the OAuth callback is handled by the ATH implementor." If the callback goes to the implementor, then the implementor already has the code — why does the agent need to present it?

Two readings are possible:
- **Reading A**: The OAuth callback goes to the ATH implementor, the implementor stores the code, and the agent's `code` field is redundant or used as a confirmation. But then what is the `code`? The spec doesn't say the implementor forwards the code to the agent.
- **Reading B**: The OAuth callback redirects to the agent (via `user_redirect_uri`), the agent receives the code, and presents it at `/ath/token`. But then the PKCE `code_verifier` is held by the implementor, and the code is held by the agent — and the only thing tying them together is the `ath_session_id`.

Under Reading B (which the field descriptions and flow diagrams imply), the `ath_session_id` becomes the sole binding between the agent's code and the implementor's PKCE verifier. If a T2 attacker can guess or capture an `ath_session_id`, they can present a different authorization code (from their own OAuth flow) against the implementor's PKCE verifier. The PKCE verifier/challenge pair protects the upstream AS, but it does not protect the ATH implementor's mapping — those are two different layers.

Under Reading A, the `code` field in `TokenExchangeRequest` is a protocol design error — it requires the agent to present something the agent doesn't have, or alternatively, the implementor must somehow convey the code to the agent through an unspecified channel.

#### Impact

This ambiguity is a specification defect under G10 (interoperability) and creates actual security exposure under either reading:
- Under Reading A: the token exchange schema requires a field the agent can't fill, or requires a new unspecified communication channel.
- Under Reading B: `ath_session_id` capture enables code substitution attacks, and the PKCE protection does not extend across the ATH ↔ OAuth boundary.

#### Recommendation

- **Explicitly specify the callback routing**: who receives the OAuth callback (implementor? agent? both?) and how the authorization code reaches the agent.
- **If the callback goes to the implementor**: remove `code` from the `TokenExchangeRequest` (the implementor already has it), and have the agent present only `ath_session_id` + `client_id` + `client_secret` + `agent_attestation`.
- **If the callback goes to the agent**: add a second PKCE-like mechanism at the ATH layer (not the upstream OAuth layer) where the agent generates a challenge at `POST /ath/authorize` and presents the verifier at `POST /ath/token`, so that code substitution is prevented even if `ath_session_id` leaks.
- **In either case**: bind the `ath_session_id` to the user's browser session (e.g., via an HTTP-only cookie) so it cannot be used from a different context.

---

## HIGH

### P3. The proxy layer cannot enforce scope semantics — scope strings are opaque

**Layer**: Token binding ↔ Proxy enforcement
**Goals threatened**: G4 (Scope confinement)
**Attackers**: T1

#### The gap

G4 says "No token MUST permit any operation outside [the effective scopes]." The proxy behavior says it "Checks the requested operation is within the granted scopes." But the specification defines **no mapping between scope strings and API operations**.

Scopes are free-form strings (e.g., `"mail:read"`, `"mail:send"`). The proxy receives an HTTP request to `/ath/proxy/example-mail/v1/messages` with method `GET`. The proxy knows the token carries scope `["mail:read"]`. But there is no specified mechanism for the proxy to determine that:
- `GET /v1/messages` requires `mail:read` (permitted)
- `POST /v1/messages` requires `mail:send` (denied)
- `DELETE /v1/messages/{id}` requires `mail:delete` (denied)

This mapping is entirely implementation-defined. The protocol says "checks scopes" but provides no framework for what checking means.

#### Impact

Without a scope-to-operation mapping standard, G4 is **unenforceable at the protocol level** in Gateway Mode. Each gateway must invent its own mapping, and there is no way for an agent developer or user to predict what operations a scope will actually permit. A T1 agent approved for `mail:read` might be able to call `POST /v1/messages/send` if the gateway's mapping doesn't cover that path, or if `GET` with specific query parameters triggers a write operation on the upstream API.

This is not merely an implementation detail — it is a structural gap in the protocol's scope confinement claim. The spec claims G4 but delegates 100% of its enforcement to unspecified implementation behavior.

#### Recommendation

- Acknowledge that G4 is only provably preserved for the scope *intersection computation*, not for the scope-to-operation enforcement at the proxy.
- Define a scope descriptor format (e.g., `{"scope": "mail:read", "methods": ["GET"], "paths": ["/v1/messages/**"]}`) that providers publish in the discovery document and that the proxy enforces.
- Alternatively, explicitly state that scope-to-operation mapping is implementation-defined and therefore G4's guarantee stops at "the token's scope set is correct" rather than "the token only permits correct operations."

---

### P4. `ath_session_id` is not bound to the user's identity or browser session — enables session swapping across users

**Layer**: ATH session state machine
**Goals threatened**: G3, G5
**Attackers**: T1, T2

#### The gap

`POST /ath/authorize` returns an `ath_session_id`. `POST /ath/token` requires the same `ath_session_id`. But the session is not cryptographically or contextually bound to:
- The **user** who will perform the OAuth consent (there is no user identity at `POST /ath/authorize` time — the user hasn't consented yet)
- The **user agent** (browser) that will perform the consent
- The **OAuth `state`** that the upstream AS will return (this is generated by the implementor, not by the agent)

After the user completes OAuth consent, the upstream callback delivers the `code` to the implementor. The implementor must then associate this `code` with the correct `ath_session_id`. But the spec doesn't say how. The `ath_session_id` was returned to the agent, and the OAuth callback is a separate HTTP request from the user's browser. The correlation between these two channels is unspecified.

#### Attack scenario (T2)

User A is a legitimate user. User B is a T2 attacker. Both use the same multi-tenant gateway.

1. Agent calls `POST /ath/authorize` for User A → gets `ath_session_id_A`, `authorization_url_A`.
2. Agent calls `POST /ath/authorize` for User B → gets `ath_session_id_B`, `authorization_url_B`.
3. T2 (User B) induces User A to visit `authorization_url_B` instead of `authorization_url_A` (via link substitution, since the agent directs the user to the URL).
4. User A consents at `authorization_url_B`, which completes User B's session.
5. Token exchange with `ath_session_id_B` now produces a token bound to User A's consent but under User B's session context.

This is a variant of the classic OAuth session fixation attack, but at the ATH layer. The protocol's `state` parameter (even if mandatory) protects the OAuth redirect, not the ATH session→user binding.

#### Root cause

The `ath_session_id` is created before the user is known and is returned to the agent (who is semi-trusted). The protocol provides no mechanism to bind the session to a specific user's browser after the fact.

#### Recommendation

- **Bind `ath_session_id` to the user's browser** by setting an HTTP-only cookie during the `POST /ath/authorize` step (or having the implementor's redirect to `authorization_url` pass through an implementor-hosted page that sets the cookie).
- **At callback time**, verify the cookie matches the session. This prevents a different user from completing the flow.
- **At token exchange time**, verify that the code's associated user matches the session's associated user (after callback).

---

### P5. No attestation-to-session continuity — the agent identity is verified once at authorize but not enforced at token exchange

**Layer**: Identity verification ↔ Token issuance binding
**Goals threatened**: G1, G5, G6
**Attackers**: T1

#### The gap

The authorize step (`POST /ath/authorize`) requires `agent_attestation` and verifies it. But the token exchange step (`POST /ath/token`) does not require an attestation — it authenticates only via `client_id` + `client_secret`.

This means the agent's identity is proven at the start of the flow but not at the end. The token is bound to the agent's `agent_id`, but the binding is based on the `client_id` lookup, not on fresh proof of key possession.

#### Impact

If `client_secret` leaks (which is a realistic risk — it is transmitted in every token exchange request body), any party holding the secret can complete any pending authorization flow without possessing the agent's private key. This breaks G1 at the token issuance boundary: the issued token is nominally bound to the agent, but was obtained without the agent proving identity at the moment of issuance.

This is distinct from P1 in that P1 focuses on the overall Phase A→B binding, while P5 is specifically about the identity proof gap within Phase B: the attestation at authorize does not extend to the token exchange.

#### Recommendation

- Require `agent_attestation` in `TokenExchangeRequest` with `aud` set to the token endpoint URL.
- The implementor MUST verify the attestation's `sub` matches the `client_id`'s registered `agent_id`, and that the attestation is fresh (issued within the session's lifetime).

---

### P6. Gateway Mode creates an implicit OAuth token aggregation layer that the protocol does not adequately constrain

**Layer**: Gateway Mode ↔ Upstream OAuth
**Goals threatened**: G3, G4, G6
**Attackers**: T1 (via scope escalation through provider confusion)

#### The gap

In Gateway Mode, the implementor holds upstream OAuth tokens for all `(user, provider)` pairs. When the proxy receives a request, it:
1. Validates the ATH token (bound to `agent_id, user_id, provider_id, scopes`)
2. Looks up the stored upstream OAuth token for `(user_id, provider_id)`
3. Makes the upstream API call using the upstream token

But the upstream OAuth token may have **broader scopes** than the ATH token. User U may have previously consented to `mail:read, mail:send, mail:delete` via a different agent or via direct OAuth. The gateway stores this upstream token. Agent X has an ATH token with only `mail:read`.

The protocol says the proxy "Checks the requested operation is within the granted scopes" — but this check is against the ATH token's scopes, not the upstream token's scopes. The upstream request is made with the upstream token, which may have `mail:send` or `mail:delete` capabilities.

#### Impact

The gateway becomes a **scope laundering** risk: the ATH layer says `mail:read`, but the upstream call is made with a token that has `mail:read + mail:send + mail:delete`. If the proxy's scope-to-operation mapping is imperfect (see P3), or if the upstream API's scope enforcement is lax, the agent could access capabilities beyond its ATH scope.

Furthermore, if two agents (Agent X with `mail:read` and Agent Y with `mail:send`) share the same `(user, provider)` upstream token, Agent X's proxy requests are authenticated upstream with a token that also carries Agent Y's consent — the upstream service cannot distinguish them.

#### Recommendation

- **Mandate per-agent-per-user upstream tokens**: the gateway SHOULD obtain a separate upstream OAuth token for each `(agent_id, user_id, provider_id)` triple, scoped to only the effective ATH scopes. This prevents scope laundering across agents.
- If per-agent tokens are not feasible, **mandate that the proxy enforces scope constraints before constructing the upstream request** — and define what enforcement means (see P3).
- Acknowledge explicitly in the threat model that the upstream token may be broader than the ATH token and that the gateway is responsible for not exceeding the ATH scope.

---

## MEDIUM

### P7. Native Mode has no specified enforcement mechanism — security requirements are inherited but unimplementable

**Layer**: Gateway Mode ↔ Native Mode parity
**Goals threatened**: G2, G4, G6, G10
**Attackers**: T1

#### The gap

The spec says Native Mode services "MUST validate the bound ATH token on every request." But in Native Mode, A4/A5/A6 coincide. The proxy endpoint doesn't exist. The service's "existing API endpoints serve the role of `/ath/proxy/{provider_id}/{path}`."

But the spec provides no guidance on **how** a native service validates the ATH token at its existing endpoints. There is no standardized:
- HTTP header scheme for presenting ATH tokens to native endpoints (the proxy uses `Authorization: Bearer <ath_token>` + `X-ATH-Agent-ID`, but native services have their own auth)
- Discovery of which endpoints require ATH vs. standard OAuth
- Mechanism for the native service to distinguish an ATH-authorized request from a standard OAuth-authorized request

#### Impact

Two spec-conformant Native Mode implementations will almost certainly use incompatible request formats, violating G10. An agent developer cannot write a single client that works with both Gateway and Native mode, because the proxy interface is well-defined but the native interface is "whatever the service does."

This also weakens G2 and G4, because there is no way to verify that a Native Mode service actually enforces ATH scope intersection — the enforcement mechanism is entirely undefined.

#### Recommendation

- Define a standard request format for Native Mode (e.g., reuse the same `Authorization` + `X-ATH-Agent-ID` headers).
- Define a standard introspection endpoint that native services can call to validate ATH tokens.
- Alternatively, acknowledge that Native Mode interoperability is not a v0.1 guarantee and restrict G10 to Gateway Mode.

---

### P8. The OAuth callback routing creates an undefined trust boundary between the ATH implementor and the user's browser

**Layer**: ATH authorize ↔ OAuth redirect ↔ ATH token exchange
**Goals threatened**: G3, G5
**Attackers**: T1, T4

#### The gap

The handshake flow diagram (step 4–5) shows:
- Step 3: ATH implementor → Service: "Initiate OAuth flow"
- Step 4: Service → User: "OAuth consent page"
- Step 5: User → Service: "User approves consent"

Then the flow jumps to step 6 (scope intersection) without specifying the callback route. The authorization MDX says "After consent, the OAuth callback is handled by the ATH implementor." But the ATH implementor returned an `authorization_url` to the **agent**, and the agent directs the user to it. The user's browser then interacts with the upstream AS directly.

The callback URL in the upstream OAuth flow (the `redirect_uri` registered with the upstream AS) must be an ATH implementor URL. After the user consents, the AS redirects to this callback URL. The implementor receives `code` + `state`. Then somehow, the agent learns the code to call `POST /ath/token`.

The protocol never specifies:
- What the implementor does after receiving the callback (does it redirect the user to the agent's `user_redirect_uri`? does it include the `code` in that redirect?)
- Whether the `code` in `TokenExchangeRequest` is the upstream OAuth code or an ATH-specific code
- If the implementor exchanges the upstream code immediately (in the callback handler) and the agent presents an ATH-specific code, how that secondary code is generated and bound

#### Impact

This is a structural ambiguity in the protocol's most security-critical flow. Different implementors will handle the callback differently:
- Some will redirect to the agent's `user_redirect_uri` with the upstream code as a query parameter — exposing the code in URL, Referer, browser history (T3 risk)
- Some will exchange the upstream code immediately and issue an ATH-specific intermediate code — adding an undocumented step
- Some will have no way to communicate the code to the agent, breaking the flow

This is not merely a documentation gap; it is an unspecified protocol step. The security of the entire flow depends on how this step is implemented, and the spec provides no guidance.

#### Recommendation

- **Fully specify the callback flow**: the implementor receives the upstream callback, exchanges the upstream code with the upstream AS (using the stored PKCE verifier), stores the upstream token server-side, and then either:
  - (a) Redirects the user to the agent's `user_redirect_uri` with an ATH-specific one-time `code` (not the upstream code), or
  - (b) Notifies the agent via a webhook/polling mechanism that the session is ready, eliminating the need for the agent to present a `code` at all.
- If (a), define the ATH-specific code and its binding to `ath_session_id`. If (b), remove `code` from `TokenExchangeRequest`.

---

### P9. Scope string semantics are undefined — no formal scope language enables scope confusion attacks

**Layer**: Scope intersection computation
**Goals threatened**: G4, G10
**Attackers**: T1

#### The gap

Scopes are free-form strings compared by set intersection. The spec gives examples like `mail:read`, `mail:send`, `mail:delete` but defines no formal grammar, no hierarchy, and no wildcard or parametric scope model.

#### Attack scenarios

1. **Scope aliasing**: An agent requests `mail:read`. The upstream AS returns `mail:read mail:readonly` (space-separated, per OAuth convention). The ATH implementor parses this as two scopes. The scope intersection computes `{mail:read} ∩ {mail:read, mail:readonly}` = `{mail:read}`. But what if the upstream interprets `mail:readonly` as a superset of `mail:read`? The intersection is performed on strings, not on semantics.

2. **Case sensitivity**: Is `Mail:Read` the same as `mail:read`? The spec doesn't say. One implementor says yes, another says no. G10 violated.

3. **Scope hierarchy confusion**: A service defines `files:*` as "all file operations." An agent is approved for `files:read`. The scope intersection of `{files:read}` ∩ `{files:*}` depends on whether the implementor understands `*` as a wildcard — the spec says nothing about wildcards.

4. **Delimiter confusion**: OAuth uses space-separated scope strings. The ATH JSON schema uses arrays. If an implementor receives `"scopes": ["mail:read mail:send"]` (one string with a space) vs. `"scopes": ["mail:read", "mail:send"]` (two strings), the intersection produces different results.

#### Recommendation

- Define a formal scope string grammar (RECOMMENDED: use the ABNF from RFC 6749 §3.3 — `scope-token = 1*( %x21 / %x23-5B / %x5D-7E )`).
- State that scope comparison is **case-sensitive byte-for-byte** (matching OAuth practice).
- State that scope strings MUST NOT contain spaces (each scope is a single token).
- State that no hierarchy or wildcard interpretation exists at the protocol level — all scope comparison is exact-match.

---

### P10. The `provider_id` in the proxy path is not validated against the token's `provider_id` binding

**Layer**: Proxy enforcement
**Goals threatened**: G4, G6
**Attackers**: T1

#### The gap

The proxy endpoint is `/ath/proxy/{providerId}/{path}`. The proxy behavior says it validates the ATH token and "verifies the agent identity matches the token binding." It checks "the requested operation is within the granted scopes." But it does not explicitly say it verifies `{providerId}` in the URL matches the token's bound `provider_id`.

The `TokenResponse` includes `provider_id`. The proxy URL includes `{providerId}`. These should match. But this check is never stated as a MUST.

#### Impact

A T1 agent with a token bound to `provider_id: "example-mail"` could call `/ath/proxy/example-calendar/v1/events` — a different provider. If the gateway looks up the upstream token by `(user_id, provider_id_from_url)` rather than `(user_id, provider_id_from_token)`, and the user has an upstream token for `example-calendar`, the request succeeds — the agent accessed a provider it was not authorized for.

This is a cross-provider escalation that breaks G4 directly.

#### Recommendation

- Add a normative MUST: the proxy MUST verify that `{providerId}` from the request URL matches the `provider_id` bound to the presented ATH token. If they do not match, return `PROVIDER_MISMATCH` (the error code already exists in the schema but is never referenced in the proxy spec).

---

### P11. Registration returns `client_secret` in the HTTP response body — no secure delivery channel

**Layer**: Phase A security
**Goals threatened**: G1, G6
**Attackers**: T3

#### The gap

`POST /ath/agents/register` returns `client_secret` in a JSON response body. This is the sole delivery of the secret — there is no out-of-band delivery, no key wrapping, and no mechanism to retrieve the secret later if it is lost.

The response travels over TLS, but T3 (side-channel observer) can observe it through:
- Server-side access logs that log response bodies
- APM/error-reporting tools that capture HTTP responses
- Middleware or proxies that inspect response bodies
- The agent runtime's own logging

#### Impact

The `client_secret` is the authentication credential for every subsequent token exchange (P1 amplifies this — it is the *sole* credential). Its compromise grants permanent impersonation ability until the registration is revoked. Delivering it in a plain HTTP response body makes it vulnerable to the full T3 attacker set.

#### Recommendation

- Use a key-wrapping scheme: the registration request includes a one-time public key, and the `client_secret` is returned encrypted to that key.
- Alternatively, use the agent's already-published `public_key` to encrypt the `client_secret` in the response.
- At minimum, add a normative MUST NOT for logging or caching the registration response body.

---

### P12. No mechanism to revoke or re-register an agent after key compromise — identity lifecycle gap

**Layer**: Agent identity lifecycle
**Goals threatened**: G1, G7
**Attackers**: T1 (after key compromise), T2

#### The gap

The spec defines registration (`POST /ath/agents/register`) and token revocation (`POST /ath/revoke`). It does not define:
- **Agent registration revocation**: a mechanism for the implementor or the agent developer to revoke the registration itself (not just individual tokens)
- **Agent re-registration**: what happens when a compromised agent's key is rotated — G1 says "MUST NOT be impersonable by substituting a different key against the same `agent_id` without the prior key authorizing the transition," but no endpoint exists for key transition
- **Emergency deregistration**: the registration spec says duplicate registrations SHOULD return 409, so after compromise, the legitimate developer cannot re-register with a new key

#### Impact

If an agent's private key is compromised:
1. The developer rotates the key in their `agent.json`
2. But the old `client_id` + `client_secret` are still valid at the implementor (issued at registration time, no expiry)
3. The attacker can continue to call `POST /ath/token` using the old credentials
4. The developer cannot re-register (409 Conflict) and cannot revoke the old registration (no endpoint for this)
5. The only recourse is contacting the implementor out-of-band — not a protocol solution

G7 (Revocation responsiveness) explicitly requires "agent registration is revoked" but no API endpoint exists to perform this revocation.

#### Recommendation

- Add a `DELETE /ath/agents/{clientId}` or `POST /ath/agents/{clientId}/revoke` endpoint requiring `agent_attestation` with the current key.
- Define a key rotation endpoint that accepts an attestation signed by the old key authorizing the transition to a new key.
- The implementor MUST provide a mechanism (API or admin) to revoke agent registrations.

---

## LOW

### P13. The 8-step handshake diagram and the actual endpoint flow describe different protocols

**Layer**: Specification consistency
**Goals threatened**: G10

The handshake flow diagram in `handshake-flow.mdx` shows an 8-step flow. The Chinese annotated document shows a 16-step flow. The actual API endpoints define a 5-endpoint flow (register, authorize, callback, token, proxy) with different step boundaries.

The 8-step diagram shows the ATH implementor initiating the OAuth flow (step 3: "Implementor → Service: Initiate OAuth flow"), but the actual authorize endpoint returns an `authorization_url` to the agent, and the agent directs the user — the implementor doesn't initiate the flow directly to the service.

This creates implementation ambiguity: the diagram implies server-to-server OAuth initiation, while the endpoint spec implies a redirect-based flow through the user's browser.

#### Recommendation

Reconcile the diagram with the actual endpoint flow. Clearly show which messages are HTTP API calls, which are browser redirects, and which are user actions. Number the steps to match the endpoint sequence.

---

### P14. The `X-ATH-Agent-ID` header at the proxy is redundant and creates a confused-deputy opportunity

**Layer**: Proxy authentication
**Goals threatened**: G1, G6

The proxy requires two authentication inputs: `Authorization: Bearer <token>` and `X-ATH-Agent-ID: <agent_uri>`. The token is already bound to `agent_id`. The header is client-asserted and can be set to any value.

The spec says the proxy "verifies the agent identity matches the token binding." This implies comparing the `X-ATH-Agent-ID` header to the token's bound `agent_id`. But this check is tautological if the token is authoritative — the header adds no security.

If the proxy uses the header value for logging, routing, or any decision other than the token check, a T1 attacker can set it to a different agent's ID while presenting their own token, creating log confusion or confused-deputy behavior.

#### Recommendation

- Remove the `X-ATH-Agent-ID` header requirement from the proxy. The agent identity should be extracted solely from the validated token.
- If the header is retained for operational reasons, state as a MUST that the proxy MUST NOT use the header for any purpose other than comparing it to the token's binding, and MUST reject requests where they do not match.

---

## Protocol-Layer Summary Table

| ID | Severity | Title | Layer | Goals | Attackers |
|----|----------|-------|-------|-------|-----------|
| P1 | **Critical** | Phase A→B binding severed: no proof-of-possession at token exchange | Registration ↔ Authorization | G1, G2, G3, G5 | T1, T3 |
| P2 | **Critical** | Authorization code routing and PKCE split-knowledge gap | ATH ↔ OAuth flow | G3, G5 | T1, T2 |
| P3 | **High** | Scope-to-operation mapping is absent — G4 unenforceable at proxy | Token ↔ Proxy | G4 | T1 |
| P4 | **High** | `ath_session_id` not bound to user identity or browser session | Session state machine | G3, G5 | T1, T2 |
| P5 | **High** | No attestation at token exchange — identity verification gap | Identity ↔ Token issuance | G1, G5, G6 | T1 |
| P6 | **High** | Gateway stores broader upstream tokens than ATH scope — scope laundering | Gateway ↔ Upstream OAuth | G3, G4, G6 | T1 |
| P7 | **Medium** | Native Mode enforcement mechanism undefined | Gateway ↔ Native parity | G2, G4, G6, G10 | T1 |
| P8 | **Medium** | OAuth callback routing unspecified — critical flow step missing | ATH ↔ OAuth redirect | G3, G5 | T1, T4 |
| P9 | **Medium** | Scope string grammar undefined — aliasing and comparison ambiguity | Scope computation | G4, G10 | T1 |
| P10 | **Medium** | Proxy `{providerId}` not validated against token binding | Proxy enforcement | G4, G6 | T1 |
| P11 | **Medium** | `client_secret` delivered in plain response body | Phase A security | G1, G6 | T3 |
| P12 | **Medium** | No agent registration revocation or key rotation endpoint | Identity lifecycle | G1, G7 | T1, T2 |
| P13 | **Low** | Handshake diagram inconsistent with endpoint flow | Spec consistency | G10 | — |
| P14 | **Low** | `X-ATH-Agent-ID` header is redundant and creates confused-deputy risk | Proxy authentication | G1, G6 | T1 |

**Part II Total**: 2 Critical, 4 High, 6 Medium, 2 Low

---

## Combined Totals (Part I + Part II)

| Severity | Part I | Part II | Total |
|----------|--------|---------|-------|
| **Critical** | 2 | 2 | **4** |
| **High** | 5 | 4 | **9** |
| **Medium** | 8 | 6 | **14** |
| **Low** | 6 | 2 | **8** |
| **Total** | 21 | 14 | **35** |
