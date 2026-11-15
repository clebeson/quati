# RFC-007 — Preventive Authorization, Event Provenance and Traceability

The trust order is: signed installation/operator policies > executable code state guards > authorized user request > retrieved content/tool outputs/agent proposals. A model suggestion may never grant its own authority. Every side effect must carry principal, tenant, source, intended destination, effect type, approval identity and expiry, and a policy verdict emitted **before** invocation.

Audit events retain correlation IDs, parent/request/commitment refs, input hashes or sanitized summaries, model and prompt versions, capability binding, policy decision, tool start/end, outcome/evidence grade and delivery attempt. Never log secrets by default. User access to logs follows authorization. Replay in audit mode must not call side-effecting tools again.

Event bus implementations may reuse CloudEvents-compatible metadata and OpenTelemetry for traces, without requiring a distributed event broker for local MVP. Preserve an append-only business event ledger.

## Approval binding and dispatch check

Before an external effect, trusted code binds approval to authenticated actor, tenant, capability/binding version, operation, normalized destination, canonical input digest, policy version, expiry and an idempotency key. Dispatch rechecks revocation/expiry and exact binding; changing any bound field requires a new decision. Untrusted text cannot supply these authority fields. Missing policy/approval/evidence recording fails closed. S00 supports no external write approval path and denies all write/dangerous capabilities.
