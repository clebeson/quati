# Engineering Records — Bugs, Debt, Logs, Fixtures and Evidence

## Bug record
`BUG-YYYY-NNN`, trigger, user impact, affected module/FR, severity P0-P3, reproducibility steps, expected vs actual, first failing public path, stack/trace reference, security/data classification, failing test, root cause, resolution PR, regression proof. P0/P1 block relevant gate. Never label an unresolved defect a planned feature.

## Technical debt record
`DEBT-NNN`, knowingly accepted shortcut, owner, cost of postponement, scope and security risk, test showing current boundary, expiry/trigger, estimated repair and ADR link. Debt cannot waive kernel invariants, authorization, honest status or lost-commitment protection. Do not create a backlog item for every stylistic preference.

## Fixture policy
Every fixture includes `fixture_id`, purpose, source classification (synthetic, sanitized, public, licensed), version, seed, permissible use, hidden expected labels, and checksum. No client data in repository or screenshots; test fixtures for malicious content explicitly marked untrusted. Holdout test labels stored outside the model prompt and outside searchable capability descriptions.

## Logs and traces
Structured JSON local log by default: timestamp with zone, event ID, correlation/commitment/workflow ID, tenant-safe reference, behavior/config/model/binding versions, policy decision and effect ID. PII and secrets redacted. Work artifacts large enough to exceed context live in artifact store with checksummed reference. Avoid logging raw prompt/context unless authorized and retention-limited.

## Evidence bundle per gate
`evidence/<slice>/<run-id>/manifest.json` containing git SHA, operating system, Python/runtime versions, versions of DBOS/Pydantic AI/model/provider, command invocations (sanitized), dataset checksum, pass/fail/blocked counts, timing/CPU/RAM when tested, output file hashes and independent reviewer verdict. Evidence captured from test runner, not generated as an assertion by the model.

## Revision and concurrency
`implementation_state.json` revision must be compare-and-swap/atomic; if two Codex Work sessions edit same slice, one must stop/rebase. Independent provider-specific adapters may run on disjoint branches after interface stabilization. Shared schema, state reducer, outbox and security policy changes have single owner per slice.
