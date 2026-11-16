# RFC-007 — Preventive Authorization, Event Provenance and Traceability

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

The trust order is: signed installation/operator policies > executable code state guards > authorized user request > retrieved content/tool outputs/agent proposals. A model suggestion may never grant its own authority. Every side effect must carry principal, tenant, source, intended destination, effect type, approval identity and expiry, and a policy verdict emitted **before** invocation.

Audit events retain correlation IDs, parent/request/commitment refs, input hashes or sanitized summaries, model and prompt versions, capability binding, policy decision, tool start/end, outcome/evidence grade and delivery attempt. Never log secrets by default. User access to logs follows authorization. Replay in audit mode must not call side-effecting tools again.

Event bus implementations may reuse CloudEvents-compatible metadata and OpenTelemetry for traces, without requiring a distributed event broker for local MVP. Preserve an append-only business event ledger.

## Approval binding and dispatch check

Before an external effect, trusted code binds approval to authenticated actor, tenant, capability/binding version, operation, normalized destination, canonical input digest, policy version, expiry and an idempotency key. Dispatch rechecks revocation/expiry and exact binding; changing any bound field requires a new decision. Untrusted text cannot supply these authority fields. Missing policy/approval/evidence recording fails closed. S00 supports no external write approval path and denies all write/dangerous capabilities.

## Policy format, approver identity and multi-user (pointer)

The policy document format, the meaning of "trusted configuration", policy storage and versioning, approver identity, the approval request lifecycle and the CLI approval UX are specified in `RFC-014_POLICY_AND_APPROVAL.md`. Roles, scopes, agent delegation ("agents never approve") and the cross-space declassification rule are specified in `RFC-013_IDENTITY_TENANCY_SPACES.md`. Multi-user approvals (approver rules other than `SELF`) arrive with S05; before S05 only the single local human principal exists and S00 still denies all write/dangerous capabilities. The `policy_version` bound in the approval binding above is the content digest defined in RFC-014.

## Output-taint rule (v8.1)

Data returned by a tool, a capability, a retrieved document or a third-party message is labelled with a `ProvenanceLabel` (RFC-013 §7.1). Its integrity is UNTRUSTED unless the source is the requester or an OWNER_DOCUMENT inside the requester's own space.

- **Untrusted arguments.** An effectful action (write or dangerous) whose arguments the model built while untrusted content was in context is routed through K8 (RFC-014). The policy engine returns APPROVAL_REQUIRED by SELF, whatever the model claims about where the arguments came from. The rule is evaluated against the context window's labels, not the model's explanation.
- **Untrusted readers.** When a destination's reader set includes an untrusted or external party (K9), the payload must be a typed output that validates against the capability `output_schema`. Free model text is not delivered verbatim.
- **Audit.** Audit events record which labels were present (`taint_labels[]`) for every effect decision.
