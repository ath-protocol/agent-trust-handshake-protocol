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
