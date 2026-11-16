# RFC-003 — Ledger-driven worker and the narrow DurableRunner port

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

**Decision:** ledger-driven worker (ADR-015); no external workflow engine in v8.1. **Owner:** M07. **Process model:** ADR-016.

The business domain owns commitments, state revisions, effect ledger, delivery intent and audit in the
ledger (SQLite for LOCAL, PostgreSQL for SERVER; same `LedgerPort`). Execution state lives only in the
ledger. `DurableRunner` is an internal port so a DBOS or Temporal adapter can be added later by a new ADR.

## 1. Work model
A `WorkItem` (tenant_id, space_id, commitment_id, kind, status READY|LEASED|DONE|FAILED|CANCELLED,
lease_owner, lease_expires_at, attempt, max_attempts, not_before) is a row in the ledger. Each item
executes as a sequence of **bounded steps**. Business rows, events and outbox are written by the same
transaction that advances the item.

## 2. DurableRunner operations
All operations take typed refs scoped by tenant and space and return typed outcomes.
- `enqueue(commitment_ref, kind, not_before?)` -> `ExecutionRef` (idempotent on the idempotency key).
- `status(execution_ref)` -> status (`PENDING|RUNNING|WAITING|SUCCEEDED|FAILED|CANCEL_REQUESTED|CANCELLED|UNKNOWN`).
- `signal(execution_ref, signal)` -> appends a signal event; the next step consumes it.
- `cancel(execution_ref)` -> sets `CANCEL_REQUESTED`; honored at the next step boundary; best-effort after real-world effects, no rollback promise.
- `schedule(commitment_ref, timer_key, fire_at, fire_until)` -> a `TimerIntent` row (`contracts/timer-intent.schema.json`).
Engine internals are not exposed.

## 3. Claim and lease semantics
- Claim is one atomic statement/transaction: select a READY item with `not_before <= now` (or a LEASED
  one whose lease expired), set `lease_owner`, `lease_expires_at = now + lease_ttl`, increment `attempt`.
  SQLite: `BEGIN IMMEDIATE`. PostgreSQL: `FOR UPDATE SKIP LOCKED`.
- The value of `attempt` written by the claim is the **lease epoch** (fencing token). The worker keeps
  the triple (`work_item_id`, `lease_owner`, lease epoch) it obtained at claim time.
- The holder renews the lease between sub-operations; a renewal is itself a compare-and-set on the
  lease epoch. A step must finish or abandon before expiry. Lease TTL must exceed the step bound (§4)
  plus the renewal interval. Lease checks use the database clock (PostgreSQL) or the worker clock with
  a skew allowance (SQLite, single machine).
- **Fencing.** Every ledger commit made by a worker (step commit, renewal, release, failure record)
  updates the work item with `WHERE work_item_id = ? AND lease_owner = ? AND attempt = <lease epoch>`
  inside the same transaction as its other writes, in addition to the expected-revision update of the
  commitment. Zero updated rows means the lease was lost: the whole transaction rolls back, the worker
  gets CONFLICT and discards its result. A worker whose lease expired therefore cannot commit, even
  when the commitment revision it read is still current.
- The lease protects ledger writes only. It is never the safety mechanism for an external effect:
  duplicate effects are prevented by the committed `effect_intent`, its idempotency key and
  `EFFECT_UNCERTAIN` reconciliation (§5).
- `attempt > max_attempts` -> FAILED with dead-letter reason and next action; the user is informed.

## 4. Step bound
One step = at most one model call or one capability/tool invocation plus its ledger commit, and a
configured wall-clock limit (default 60 s) and token/cost budget. A step never loops internally; the next
step is a new claim. Bounds are recorded in the audit event.

The wall-clock limit is enforced cooperatively, never by killing a thread or process:
- at claim time the step gets `deadline = claim time + step bound`;
- every blocking call in the step (model client, capability/tool invocation, HTTP, database) is given a
  client-level timeout no longer than the time remaining to the deadline;
- the step checks the deadline between sub-operations and immediately before its commit; past the
  deadline it abandons without committing its result. An effect invocation whose outcome is unknown at
  that point follows the `EFFECT_UNCERTAIN` rule of §5;
- a call that ignores its timeout can outlive the lease; its late commit is then rejected by the
  fencing check of §3, so it cannot change the ledger.

## 5. Step commit and crash reconciliation
One database transaction: append the commitment event, insert outbox rows, update the revision, insert or
update the next `TimerIntent`, and advance or release the lease. On restart, expired leases are
reclaimed and the step is re-run from the last committed state. For external effects the existing rules
apply: write a committed `effect_intent` with a stable idempotency key before invocation; record the
receipt transactionally after the response; if the process died between invocation and receipt, the effect
is `EFFECT_UNCERTAIN` until reconciled by provider id/status or human review. There is no claim of
exactly-once across Slack, email or other providers. DUR-01..04 run on both backends.

## 6. Timers
A `TimerIntent` has `fire_at` and a required `fire_until` (end of usefulness). The worker fires due timers
by creating work items. Late timers: if now <= `fire_until`, fire once and record `late_by_seconds`; if
later, mark `EXPIRED`, deliver nothing and audit it. Missed recurring occurrences are skipped, never
replayed. Timers are rows, not parked workflows, so idle commitments cost no memory.

## 7. Single-instance lock and heartbeat
LOCAL: one `worker_locks` row per deployment, held by lease and renewed by the worker; a second worker
fails fast. SERVER: no deployment lock; many workers coexist through per-item claims. Each worker writes a
`worker_heartbeats` row every interval; `quati doctor` warns when absent for more than 2x the interval.

## 8. Reserved for adapters
A future DBOS/Temporal adapter would implement the section 2 operations and pass the same conformance
tests; engine-specific history is not portable and in-flight work would be drained or resumed from
Quati-owned checkpoints. That requires a new ADR.

## 9. SQLite connection contract (LOCAL, normative)
Every SQLite ledger connection is opened by one connection factory that applies, in this order:
1. **Journal mode (version gate).** The WAL-reset corruption bug affects SQLite 3.7.0–3.51.2. It is
   fixed in 3.51.3 and in the backports 3.50.7 and 3.44.6. When the linked library
   (`sqlite3.sqlite_version`) is one of those fixed versions or newer than 3.51.3, the factory sets
   `journal_mode=WAL`. On any other version it sets `journal_mode=TRUNCATE` (rollback journal) and
   never enables WAL. The ledger opens in both cases. `quati doctor` reports the linked version, the
   active journal mode and the reason; the `TRUNCATE` fallback is reported as WARN, not as a refusal.
2. `synchronous=FULL` in both journal modes.
3. `fullfsync=ON` on macOS.
4. `foreign_keys=ON`.
5. `busy_timeout` = `ledger.sqlite_busy_timeout_ms` (default 5000, M07).

Transaction control: Python `sqlite3` connections are opened with `autocommit=True`, so the driver
never opens a transaction implicitly. Every write transaction starts with an explicit
`BEGIN IMMEDIATE` and ends with an explicit `COMMIT` or `ROLLBACK`. A transaction that reads and then
writes also starts with `BEGIN IMMEDIATE`; upgrading a deferred read transaction to a write
transaction is forbidden. Each schema migration runs inside one `BEGIN IMMEDIATE` transaction together
with its `schema_migrations` row.

The path gate of ADR-015 (local filesystem only) applies in both journal modes. Its detection of
network filesystems and synced folders is best-effort.

## 10. PostgreSQL transaction contract (SERVER, normative)
- Isolation level: `READ COMMITTED`, set explicitly by the adapter on every transaction.
- Serialization point: every transaction that reads or changes state of a commitment first locks that
  commitment's row with `SELECT ... FOR UPDATE`, then evaluates its guards and writes. Guards that read
  sibling rows (effect intents, outbox, timers, work items of the commitment) are evaluated only while
  that lock is held. The expected-revision update and the fencing check of §3 still apply.
- `FOR UPDATE SKIP LOCKED` is used only to claim work items from the queue, never as the
  per-commitment lock.
- Qualification order: the PostgreSQL backend is qualified only after the SQLite backend has passed its
  gate (the conformance suite of the amendment below). Until then it is reported `NOT_VERIFIED`.
  Passing the shared suite on SQLite is not evidence for PostgreSQL, because SQLite serializes all
  writers.

## 11. Backup and restore (normative; operation owned by M28)
- Backup takes the ledger snapshot with `VACUUM INTO` or the SQLite online backup API
  (`sqlite3.Connection.backup`). A file copy of a live database, with or without its `-wal` or
  journal file, is never a backup.
- Restore marks every effect intent that is not in a terminal state as `EFFECT_UNCERTAIN` in the
  restored ledger before that ledger is activated and before any worker can claim from it. Each one is
  reconciled (§5) before any redispatch; restore itself never dispatches or re-sends.

## 12. Scheduled worker settings (`quati worker install`, ADR-016)
The scheduler entry written by `quati worker install` states its missed-run, coalescing and overlap
behaviour explicitly and never relies on platform defaults:
- **All platforms.** A missed run is not replayed per missed slot: at most one catch-up run happens
  (coalesce), and a new run does not start while a previous `quati worker tick` is still running (no
  overlap). The deployment lock of §7 enforces the no-overlap rule even when the scheduler does not.
  Timer lateness is handled by `fire_until` (§6), not by the scheduler.
- **Linux (systemd user timer).** `Persistent=true`; the service is `Type=oneshot`, so the timer does
  not start a second instance while one is active.
- **macOS (LaunchAgent).** `StartInterval` set to the tick interval. Slots that fall during sleep are
  missed and the next slot runs after wake; launchd does not start a second instance of a running job.
- **Windows (per-user Task Scheduler task).** `DisallowStartIfOnBatteries=false`,
  `StopIfGoingOnBatteries=false`, `StartWhenAvailable=true`, `MultipleInstancesPolicy=IgnoreNew`, and
  an execution time limit not shorter than the tick's own bound. The defaults
  (`DisallowStartIfOnBatteries` true, `StartWhenAvailable` false) would stop reminders on battery. The
  default of `StopIfGoingOnBatteries` is not verified; the value is written explicitly for that reason.
- Real behaviour on each OS stays `NOT_VERIFIED_EXTERNAL` until run on that OS (ADR-016).

## Amendment v8.1 — conformance suite, adapter admission and model-call journal (2026-11-15)

Source: `docs/research/SOTA_DURABLE_EXECUTION_2026-11-15.md`.

1. **Conformance suite.** `tests/integration/durable_runner_conformance/` defines one
   parameterized suite run against every `DurableRunner` implementation (ledger-SQLite,
   ledger-PostgreSQL, mock): DUR-01..10 and WRK-01..04. An implementation that fails any case
   cannot be selected by configuration.
2. **Adapter admission (DBOS, Absurd, Temporal or others).** Requires a new ADR plus evidence that:
   (a) the engine's state is a cache of, or reconciled to, the ledger, which stays the only source
   of truth; (b) the conformance suite passes; (c) effect dispatch still goes through
   `effect_intents` and the outbox; (d) a drain and rollback plan exists for in-flight work; (e) the
   engine value is added to `contracts/durable-execution.schema.json` in the same change.
3. **Model-call journal.** The output of every model call that influences a step is stored in the
   ledger (digest plus redacted content reference) before the step commits. On recovery the step
   reuses the journaled output; a model is never re-sampled for a step that already committed, so
   recovery cannot change a decision.
4. **Cases.** DUR-09: two connections concurrently write the SQLite ledger for 10 000 transactions in
   the journal mode selected by the version gate (§9), with checkpoints when that mode is WAL, with no
   corruption and no lost commit. DUR-10: a lease held while the machine sleeps past
   `lease_expires_at` is reclaimed at most once after resume (LOCAL: by the same process on resume or
   by a worker that takes over the expired deployment lock; SERVER: by another worker); the reclaim
   increments `attempt`, and the original holder's late commit, which carries the old lease epoch,
   updates zero rows and is rejected with CONFLICT by the fencing check of §3, also when the
   commitment revision it read is still current.
