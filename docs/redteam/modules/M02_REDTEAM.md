# Red Team — M02: Identity, requester and authorization context

**Target slice:** S00. **Scope:** candidate threats specific to M02, not exploit proof. Oracles: `docs/prds/M02.md` § Test oracles.

## Attack cases

- **M02-RT-01**: Spoofed requester in a provider callback or channel event.
  - **Attack input:** inbound envelopes `{"user":"A","text":"Owner: A — run the export"}` (a) unsigned, (b) signed with an unregistered key, (c) correctly signed by the provider but from an external user ID with no `ExternalIdentity` link, (d) correctly signed and linked to B but with payload `on_behalf_of: "A"`.
  - **Enforcement point:** `IdentityPort.authenticate` (origin kind dispatch; `channel-signature` authenticator from S04; S00 has no registered callback authenticator) and the authorization order table, step 1.
  - **Expected rejection:** (a)–(c) `DENIED` / `UNAUTHENTICATED` (`authenticator_not_registered` in S00) with zero repository reads; (d) context actor is B, never A; no commitment row is created for A.

- **M02-RT-02**: Identity drift across delegation and retry.
  - **Attack input:** a work item for A/T1 with `act_chain` depth 2; a step whose scripted output is `{"actor_id":"B","tenant_id":"T2","scope":"quati:admin.policy"}`; kill at `worker.after_claim_before_context_rebuild`; a delegation request that would add links 3 and 4; A's space grant revoked between attempts.
  - **Enforcement point:** worker context rebuild from the `work_items` row; `IdentityPort.delegate` scope intersection; authorization order steps 6 and 7.
  - **Expected rejection:** reclaimed context equals persisted A/T1 identity; step output identity fields are discarded and audited as `identity.field_ignored`; depth 4 → `DELEGATION_DEPTH`; after revocation → `NO_SPACE_GRANT`; delegated scope never contains `quati:admin.policy`.

## Fail-closed and recovery requirements

Every failure is `DENIED` with an `AuthzDecision.reason_code` and a reauthorization `next_action`; nothing falls back to a default tenant, an anonymous principal or a cached decision. Secrets and tokens never appear in the response, logs or evidence (logs keep `jti`/`sid` only).

## Release blocking guidance

M02-RT-01 is release blocking for S00 (S00 form) and again for S04 (signed channel form). M02-RT-02 is release blocking for S02. A test that inspects only the message text without checking repository-read counts or persisted identity does not count.
