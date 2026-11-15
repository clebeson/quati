# RFC-007 — Preventive Authorization, Event Provenance and Traceability

The trust order is: signed installation/operator policies > executable code state guards > authorized user request > retrieved content/tool outputs/agent proposals. A model suggestion may never grant its own authority. Every side effect must carry principal, tenant, source, intended destination, effect type, approval identity and expiry, and a policy verdict emitted **before** invocation.

Audit events retain correlation IDs, parent/request/commitment refs, input hashes or sanitized summaries, model and prompt versions, capability binding, policy decision, tool start/end, outcome/evidence grade and delivery attempt. Never log secrets by default. User access to logs follows authorization. Replay in audit mode must not call side-effecting tools again.

Event bus implementations may reuse CloudEvents-compatible metadata and OpenTelemetry for traces, without requiring a distributed event broker for local MVP. Preserve an append-only business event ledger.
