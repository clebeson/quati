# State-of-the-art review: identity, authorization, agent delegation, information flow (2026-11-15)

Scope: RFC-013, ADR-013, ADR-014, `contracts/identity.schema.json`, and RFC-014 (read only). Verdicts: KEEP / ADOPT / CHANGE / REJECT. "UNVERIFIED" means I could not confirm the point from a primary source in this session. Several sources below are IETF datatracker pages fetched through a summarizing tool; re-check exact version numbers before citing them in a PR.

## Bottom line

The design is sound and mostly matches the state of the art: short-lived audience-bound tokens, no grants in tokens, live grant resolution, RFC 8693 delegation, agents never approve, pre-filtered retrieval. The main risks are not missing standards. They are (a) three places where we invented what a standard already names, (b) one missing information-flow dimension (integrity/taint), and (c) S00 ceremony that exceeds the MVP need.

## 1. Fine-grained authorization

| Item | What / maturity | Source | Verdict |
|---|---|---|---|
| Zanzibar ReBAC: OpenFGA | Zanzibar-inspired authorization service. CNCF Incubating since 2025-10-28 (accepted 2022-09-14). Runs as a server with its own store. | https://www.cncf.io/projects/openfga/ | REJECT as a dependency now. A daemon breaks "local, no server". Keep the *tuple shape* (below). |
| SpiceDB (AuthZed) | Zanzibar server. One listing shows v1.54.0 (2026-06-18); an in-process embedded mode exists in the docs, and the Python/.NET embedded wrappers are third-party. | https://pypi.org/project/spicedb-embedded/ (third-party) | REJECT for MVP. UNVERIFIED: official Python embedding and SQLite datastore. |
| Permify | Zanzibar-style, open source. I found no current maintenance or status evidence. | (secondary comparison only) | REJECT. UNVERIFIED status. |
| Cedar | AWS policy language: default deny, `forbid` overrides `permit`, schema validation, symbolic verification (`cedar-policy-symcc`). Official bindings are Rust, wasm and CLI only. | https://github.com/cedar-policy/cedar | See below. |
| cedarpy | Python wheels for Cedar. v4.12.2 (2026-10-14) tracks Cedar 4.12. Single maintainer, **not supported by AWS or the Cedar team** (README). | https://pypi.org/project/cedarpy/ | REJECT as a hard dependency; revisit when an official Python binding exists. Cedar's CNCF/governance status UNVERIFIED. |
| OPA/Rego | CNCF Graduated (2021). A claim that the Styra team moved to Apple comes from one blog; UNVERIFIED. | https://www.cncf.io/announcements/2021/02/04/cloud-native-computing-foundation-announces-open-policy-agent-graduation/ | REJECT. General-purpose language contradicts RFC-014's non-goal. |
| Oso (Polar) | The open-source library has been deprecated since 2023-12-18 in favor of the managed Oso Cloud; it gets critical fixes only. | https://www.osohq.com/docs/oss/project/changelogs.html (via search; UNVERIFIED on the current README) | REJECT. |
| AuthZEN 1.0 (OpenID) | A standard Subject/Action/Resource/Context decision API. Final status UNVERIFIED. In June 2026 two new WG drafts appeared: AARP (approval/consent prerequisites) and COAZ (MCP tool authorization). | https://openid.net/openid-foundation-advances-authorization-for-the-agent-era-with-new-authzen-working-group-drafts/ | CHANGE (cheap): shape `AuthorizationPort.check` as subject/action/resource/context. Watch AARP, which is the same problem as our `APPROVAL_REQUIRED`. |

**Is SpaceGrant a custom model that should be Cedar or OpenFGA?** No. SpaceGrant has three roles, flat groups and one resource level. It is one relational table plus a `max()`. A Zanzibar engine would add a service for a lookup. The minimal-cost path that keeps the "1 works ⇔ N works" property is:

1. Store SpaceGrant as tuples `(subject, relation, object)`, for example `user:U reader space:S` and `group:G#member contributor space:S`. This is isomorphic to an OpenFGA/SpiceDB model. Migrating later is a data export, not a redesign.
2. Keep RFC-014's JSON rules. They are a strict subset of Cedar semantics: default deny, deny wins, no expressions. Add a normative mapping (principal, action, resource, context) so that a future Cedar adapter behind `PolicyPort` can pass the same golden cases. Write the golden cases once, as conformance fixtures.
3. Do not mix the two: RFC-014 K4 already says policy ALLOW never grants content access. That separation is correct and is what Cedar-plus-ReBAC deployments do.

Over-engineering flag: RFC-013 §14 already defers OPA/Cedar, which is right. Do not spend S00 effort on adapters.

## 2. Agent identity and delegation

| Item | What / maturity | Source | Verdict |
|---|---|---|---|
| RFC 8693 token exchange (`act`, `may_act`) | Published standard for delegation. | https://www.rfc-editor.org/rfc/rfc8693 (not re-fetched; UNVERIFIED this session) | KEEP. CHANGE (low): RFC 8693 takes a separate `actor_token`; use the agent's own short token, not only its client authentication. Optionally use `may_act` to pre-authorize the secretary for a human. |
| OAuth Transaction Tokens | draft-ietf-oauth-transaction-tokens-11 (2026-07-30), WG consensus, awaiting write-up; WG milestone to IESG Dec 2026. Claims `txn`, `scope`, `tctx`, `rctx`, `req_wl`. Designed for call chains inside one trust domain. | https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/ | CHANGE (low): do not adopt. Document that `cmt`/`eid` map to `txn`/`tctx` so S05 can emit real Txn-Tokens if an enterprise gateway wants them. |
| RFC 9068 JWT access-token profile | Standard profile: header `typ: at+jwt`; required `iss, exp, aud, sub, client_id, iat, jti`. | https://www.rfc-editor.org/rfc/rfc9068 (not re-fetched; UNVERIFIED this session) | CHANGE: our claims lack `client_id`, and the schema should require `typ: at+jwt`. This blocks token confusion with ID tokens. |
| RFC 9449 DPoP / sender constraint | Proof-of-possession for bearer tokens. | https://www.rfc-editor.org/rfc/rfc9449 (UNVERIFIED this session) | CHANGE: `cnf` is optional today. Make it required for tokens leaving the process (capability subprocess, remote A2A) in SERVER; DPoP or mTLS. In LOCAL the token never leaves the process, so skip it. |
| RFC 9396 Rich Authorization Requests | `authorization_details` structured, typed grants. | https://www.rfc-editor.org/rfc/rfc9396 (UNVERIFIED this session) | CHANGE: express the effect-intent binding (`eid`) and the approval payload as `authorization_details` with a `secma_effect` type. This also makes CIBA and RAR approvals possible later. |
| OAuth 2.1 | draft-ietf-oauth-v2-1-17, 2026-10-31, still "WG Document", IESG milestone Dec 2026. | https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/ | KEEP. Our flows (code + PKCE, device, private_key_jwt, no implicit or password) comply. Call it a target, not a standard. |
| RFC 8628 device flow | Standard; MCP's spec does not use it, but OIDC providers do. | https://www.rfc-editor.org/rfc/rfc8628 (UNVERIFIED this session) | KEEP for `secma login`. |
| CIBA | OpenID Foundation spec, not an IETF RFC. Auth0 documents CIBA + RAR for asynchronous human approval of agent actions. | https://auth0.com/ai/docs/intro/asynchronous-authorization | CHANGE: keep our own ApprovalRequest as the source of truth, with a pluggable approval channel. Add CIBA as an S07 adapter. Never make it mandatory; many IdPs lack it (UNVERIFIED which). |
| MCP authorization, **newest revision 2026-07-28** (previous 2025-11-25) | 2025-11-25: Client ID Metadata Documents (CIMD) recommended, OIDC discovery, incremental scope consent, RFC 8707 `resource` parameter mandatory, RFC 9728 mandatory, token passthrough forbidden. 2026-07-28: stateless protocol (no sessions or handshake), DCR deprecated in favor of CIMD, RFC 9207 `iss` validation, credentials keyed by issuer, Roots/Sampling/Logging deprecated, tasks moved to an extension, multi-round-trip `input_required`. STDIO servers should not use this OAuth flow. | https://modelcontextprotocol.io/specification/versioning, https://modelcontextprotocol.io/specification/2026-07-28/changelog, https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization | CHANGE: RFC-013 §5.3 says outbound tokens come from "token exchange", but MCP servers expect auth code + PKCE with `resource` plus RFC 9728 discovery. Specify: per-server tokens keyed by issuer, audience-bound, never forwarded, secret references for STDIO. Cite 2026-07-28 as the baseline. |
| A2A v1.0.0 | Security schemes follow OpenAPI (API key, HTTP, OAuth2 auth code / client credentials / device code, OIDC, mTLS); signed AgentCards; extended card behind authentication; servers must not reveal whether a resource exists to unauthorized clients (§3.3.2). | https://a2a-protocol.org/latest/specification/ | KEEP. `client-key` maps onto OAuth2 client credentials. CHANGE (low): verify AgentCard signatures when an admin registers a remote agent. IDN-04's "same response" rule matches §3.3.2. |
| WIMSE / SPIFFE / agent drafts | WIMSE architecture draft-07 (2026-03) is a WG draft. `draft-klrc-aiagent-auth-03` is expired and replaced by `draft-ietf-wimse-aims`. `draft-oauth-ai-agents-on-behalf-of-user-02` (WSO2) expired 2026-02. `draft-ni-wimse-ai-agent-identity-03` is Informational. SPIFFE link: UNVERIFIED. | https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/, https://datatracker.ietf.org/doc/html/draft-oauth-ai-agents-on-behalf-of-user-02 | REJECT as dependencies; no stable target exists. Keep ULID `sub`; allow a later SPIFFE-ID mapping via `ExternalIdentity`. |

Other confirmations: "grants not in tokens, live resolution, revocation set on writes" matches current practice. Step-up via `amr`/`auth_time` corresponds to RFC 9470; not re-fetched, UNVERIFIED.

Over-engineering flags for the MVP:
- **JWT/JWKS in-process at S00.** Minting and verifying a JWS in the same process proves nothing about N. Keep one `AccessTokenClaims` type and one verifier, but serialize to JWT only at a process boundary (subprocess, HTTP).
- **Keyring plus Ed25519 per CLI call.** Headless Linux often has no Secret Service (general knowledge; not a primary source). Specify the 0600 file fallback now, or `local-os` will break in CI and containers.
- **Refresh tokens, AUDITOR, nested limits.** Already scoped S05+; keep them out of S00.

## 3. Permission-aware retrieval and information-flow control

| Item | What / maturity | Source | Verdict |
|---|---|---|---|
| ACL pre-filter vs post-filter | Practitioner consensus: filter inside the query; post-filtering exposes unauthorized chunks to the process. Caches, rerankers and summaries must sit inside the boundary. OWASP LLM08 (Vector and Embedding Weaknesses) lists cross-tenant leaks and embedding inversion. I read only secondary summaries; primary OWASP text UNVERIFIED. | https://nhimg.org/permission-aware-rag-guide (secondary) | KEEP pre-filter then post-check (RFC-013 §6). |
| CaMeL | Google DeepMind/ETH: trusted planner derives control flow; an untrusted-data model has no tools; an interpreter tracks per-value provenance and readers. 77% of AgentDojo tasks with provable security vs 84% undefended. | https://arxiv.org/pdf/2503.18813 | REJECT full adoption for MVP (needs a restricted interpreter, a large cost). ADOPT the principle: untrusted content never selects effects. |
| FIDES | Microsoft: confidentiality and integrity labels, deterministic policy enforcement, selective hiding of data from the LLM; blocked all AgentDojo injections with policy checks enabled (abstract-level; I read only a summary). | https://arxiv.org/pdf/2505.23643 | CHANGE: add the integrity dimension (below). |
| Dual-LLM pattern | Quarantined versus privileged model. I did not fetch the original post; the CaMeL paper generalizes it. UNVERIFIED primary. | n/a | KEEP optional; our capability-isolation design already covers this. |

**Comparison with our ProvenanceLabel.** `readers(target) ⊆ readers(source)` is the standard confidentiality lattice rule (no downgrade without declassification), and RFC-013 §7 plus RFC-014 K5 add the correct declassification record bound to a digest. The label is per turn or object and covers confidentiality only. Gaps:

1. **No integrity label.** FIDES and CaMeL both separate "who may read this" from "can this be trusted to drive actions". Without an integrity taint, a document, tool result or channel message in context can still steer an effect. RFC-007's trust order is a prompt-level rule, not a code-level check on effect arguments. Add `untrusted` (a boolean or a set of source classes) to the label, computed by trusted code. Rule: an effect whose arguments derive from tainted input becomes `APPROVAL_REQUIRED`, regardless of tenant policy. Verify against RFC-007 whether this already exists.
2. **External audiences are undefined.** `audience(A) ⊆ readers(S)` has no meaning for an email recipient who is not a principal. State that `readers(external) = ∅`, so any delivery of labelled content outside the tenant needs approval.
3. **Pre-filter cannot express the label check.** "Item label ⊆ readable spaces" is an array containment test that FTS5/vector indexes cannot filter efficiently. Pre-filter by `space_id`, then post-check labels with over-fetch, and compute counts only after the post-check (IDN-04).
4. **Side channels beyond counts and snippets:** total-hit counts, facets, "did you mean", reranker scores, latency, and provider-side prompt caches. Add these to IDN-04. Embeddings are as sensitive as text: store them under the same space key and encryption.
5. **Per-turn coarseness is acceptable** for the MVP. Over-tainting is safe, and per-value tracking is the CaMeL cost we should not pay yet.

## Recommended deltas

| Target file | Change | Priority | Slice |
|---|---|---|---|
| `docs/rfcs/RFC-013_IDENTITY_TENANCY_SPACES.md` §7, `contracts/identity.schema.json` | Add an integrity/taint field to ProvenanceLabel; effects with tainted arguments need approval (K-rule in RFC-014, enforced in the effect gateway) | HIGH | S02 |
| RFC-013 §7 | Define `readers(external recipient) = ∅`; deliveries outside the tenant always need declassification approval | HIGH | S02 |
| RFC-013 §6, IDN-04 | Pre-filter by space then post-check labels; counts computed after the check; list side channels (facets, suggestions, scores, timing, caches) in the red-team case | HIGH | S03 |
| `contracts/identity.schema.json` (AccessTokenClaims) | Require `client_id` and header `typ: at+jwt` (RFC 9068); `cnf` required for tokens leaving the process in SERVER | MEDIUM | S05 |
| RFC-013 §5.3 | Outbound MCP: authorization code + PKCE, `resource` (RFC 8707), RFC 9728 discovery, tokens keyed by issuer, no passthrough, STDIO uses secret references; baseline MCP 2026-07-28 | MEDIUM | S05 |
| RFC-013 §4/§11, ADR-014 | S00 uses a typed claims object with the same verifier; serialize to JWT/JWKS only at process boundaries | MEDIUM | S00 |
| RFC-013 §3 (`local-os`) | Specify a 0600 key-file fallback when no OS keyring is available | MEDIUM | S00 |
| RFC-013 §10 | `AuthorizationPort.check` takes subject/action/resource/context (AuthZEN shape); store SpaceGrant as relation tuples | MEDIUM | S00 |
| RFC-014 (separate author) | Add a Cedar-semantics mapping plus golden conformance cases; no Cedar or cedarpy dependency | LOW | S07 |
| RFC-013 §5.1 | Use an explicit `actor_token`; optional `may_act`; express `eid`/approval payload as RAR `authorization_details`; `aud` as a URI | LOW | S05 |
| RFC-013 §5.3, A2A | Verify AgentCard signatures at agent registration; map `client-key` to OAuth2 client credentials | LOW | S05 |
| RFC-013 §5, ADR-014 | Note `cmt`/`eid` to Transaction Token (`txn`/`tctx`) mapping; approval channel pluggable, CIBA + RAR adapter (watch AuthZEN AARP) | LOW | S07 |
