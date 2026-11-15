# RFC-003 — Minimum Durable Execution Port
**Decision:** DBOS adapter first; Temporal optional later. **Owner:** M07.

The business domain owns commitments, state revisions, effect ledger, delivery intent and audit. A `DurableRunner` port initially exposes `start`, `status`, `signal`, `cancel`, `schedule`. Every operation accepts typed refs and returns typed outcomes. Internals such as DBOS messages, queue IDs, workflow decorators, persistence callbacks, retry policy or cancellation semantics remain inside the adapter unless a real business requirement proves a new portable operation is needed.

### DBOS specifics
Open-source DBOS Python can run with SQLite by default; PostgreSQL is recommended for production. Its workflow communication supports messages, idempotency keys and events. Workers are processes: closing the last worker pauses progress. The open-source edition's long wait and sleep resource usage must be measured; `suspend=True`/long wait suspension belongs to an enterprise feature according to current docs. Avoid one indefinitely parked workflow per commitment; keep a ledger scheduling table and sweep due events with bounded worker concurrency.

### Exactly-once boundary
Database commits and DBOS step replay are not the same as guaranteed exactly-once external Slack or email writes. Emit an `EffectIntent` with stable idempotency key before invocation; record acknowledged outcome or `EFFECT_UNCERTAIN` when downstream completion is ambiguous. Reconcile via provider ID/status or human review. Cancellation is best-effort after real-world side effects; do not promise rollback that does not exist.

### Migration plan
If enterprise requirements demand Temporal, implement a new adapter, run conformance tests and route **new** jobs to it while old DBOS jobs drain or are resumed from SECMA-owned checkpoints. Do not claim engine-specific workflow history is automatically transferable.
