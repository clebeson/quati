# SOTA review: durable execution for SECMA v8.1 (ADR-015 challenged)

> Note (2026-11-15): the DBOS claims in these notes were re-checked. Where they describe or criticise ADR-015, or recommend SQLite settings, they are superseded by ADR-015 (corrected rationale) and RFC-003; this file is kept unchanged below as a historical working record.

Date: 2026-11-15. Status: WORKING NOTES. Claims marked UNVERIFIED were not confirmed from a primary source in this session (they come from prior knowledge or secondary results).

## 1. Verdict

The decision "no DBOS in v8.1; ledger-driven worker over one LedgerPort (SQLite + PostgreSQL)" is **defensible**, but ADR-015 currently rests on two premises that the 2026 evidence weakens, and it needs rewording:

1. ADR-015 says DBOS "still needs PostgreSQL for the corporate path" and implies it cannot serve LOCAL. **DBOS Transact Python supports SQLite as its system database** (primary source: docs.dbos.dev configuration page: the system database "may be either Postgres or SQLite, though Postgres is recommended for production"; with no connection string it creates a SQLite file named after the app; `use_listen_notify` is ignored on SQLite, which always polls). So "DBOS cannot run local" is false.
2. The real reasons to reject DBOS are different and stronger: SQLite is officially a dev/test backend there, the ledger/business atomicity argument, and the extra truth source. These should replace the weaker rationale.

## 2. Evidence by option

**DBOS Transact Python (MIT license, ~1.7k stars; PyPI release 3.1.0 dated Sep 2026 per a secondary index, UNVERIFIED).**
- SQLite supported; Postgres recommended for production. A DBOS log line at launch reportedly says the SQLite system DB is for dev/test (community issue #940, UNVERIFIED as official).
- Known SQLite gaps: sharding requires Postgres-compatible DB (docs); attribute-based workflow filtering Postgres-only in 3.1.0 (third-party issue, UNVERIFIED); a queue's global concurrency can be exceeded with several workers on SQLite because the budget read is outside the claim transaction (issue #940 against 3.4.0, UNVERIFIED). Docs state a SQLite file cannot serve a multi-server deployment (expected).
- June 2026 release post: Python gained pluggable data sources and native async transactional steps; transactional steps checkpoint in the same transaction as app writes, so "exactly once" holds for writes **in a configured database**. This is the capability the audit (A-04 option b) pointed at. It does not help external effects (email, calendar), which still need SECMA's `effect_intent` and `EFFECT_UNCERTAIN` rules.
- The post only mentions SQLite as a backend for DBOS Go v0.17; nothing new for Python SQLite.
- Pydantic AI ships `DBOSDurability`, `TemporalDurability`, `PrefectDurability` (co-maintained with vendors; one engine per agent; model requests and wrapped tool calls are journaled and replayed on restart; the in-flight unit is retried). Streaming and batched requests differ per engine. The same page lists Restate, Absurd, pgtask, Azure Durable Task and Airflow integrations.

**Temporal.** Python SDK plus a dev server exist, but the dev-server persistence and determinism details were not confirmed here (UNVERIFIED). Workflow code must be deterministic and runs on a separate server cluster; the product has no "no server for one user" mode in production. Right to reject for LOCAL; keep as a SERVER-profile adapter candidate only.

**Absurd (Armin Ronacher).** Postgres-only; one SQL file of stored procedures; claim-based, no coordinator; checkpointed steps; Python/TS SDKs and CLI; about five months of production use reported in April 2026; Pydantic AI has an Absurd durability capability. It is architecturally the closest published relative of SECMA's design (claim, bounded step, checkpoint in the same DB) and is evidence that **"durable execution = a small SQL schema + claim + checkpoint" is mainstream SOTA**, not NIH. It is Postgres-only, so it cannot be the LOCAL backend.

**Restate, Inngest, Hatchet, pgmq, PGQueuer, Procrastinate, Huey, litequeue, persist-queue, LangGraph checkpointers.** Not re-verified from primary sources this session; treat all statements as UNVERIFIED. Working understanding: Restate, Inngest and Hatchet need a server process (self-host or cloud), which contradicts LOCAL "no server". pgmq, PGQueuer and Procrastinate are Postgres-only queues (no checkpointed multi-step semantics beyond retry). Huey, litequeue and persist-queue give SQLite queues but no atomic "event + outbox + next timer" with the business ledger, so they would still sit beside the ledger. LangGraph SqliteSaver/PostgresSaver checkpoint graph state, not business commitments; wrong source of truth for SECMA.

**SQLite limits (primary: sqlite.org/wal.html).** One writer at a time; WAL works only on one machine, not over network filesystems (so no synced-folder or NAS databases); a long-lived reader can starve checkpoints and the WAL grows unbounded; the **WAL-reset bug affects 3.7.0 through 3.51.2, fixed in 3.51.3 (backports 3.44.6, 3.50.7)** and needs two or more connections writing or checkpointing at the same instant. Consequence: pin a minimum SQLite version in the spec (the Python build's bundled SQLite varies by OS and Python version) and test it in `doctor`.
**Litestream** (v0.5.x, actively maintained, separate process, single server): suitable as an optional LOCAL backup recipe; do not make it a dependency. Keep it out of the ledger correctness story.

**Local scheduling (primary: systemd.timer man page).** `Persistent=true` on `OnCalendar=` timers catches up runs missed while the machine was off; calendar timers use the realtime clock, so a firing during suspend is handled after resume (once, even if several elapsed); monotonic timers pause during suspend; `WakeSystem=` is not available to user timers. Hence a user timer cannot wake a sleeping laptop, and "missed timers after sleep" is solved by `fire_at`/`fire_until` plus a catch-up rule in the worker, as ADR-016 already specifies. launchd (`StartCalendarInterval` coalesces missed runs after sleep) and Windows Task Scheduler ("run as soon as possible after a missed start") offer equivalents: UNVERIFIED here, verify before the S-slice that writes the installer docs.

**Outbox and idempotency (UNVERIFIED this session, widely documented).** Same-transaction outbox plus idempotent consumers keyed by a stable idempotency key is the accepted pattern; the ledger design matches it. Delivery is at-least-once; exactly-once effects only via provider idempotency keys or reconciliation, which is what `EFFECT_UNCERTAIN` encodes.

## 3. Hand-rolled vs library: trade-offs

| Dimension | Ledger worker (ADR-015) | DBOS (+ Pydantic AI `DBOSDurability`) |
|---|---|---|
| Code owned | Lease, retry, timers, recovery (bounded, tested by DUR-*) | Less engine code, but SECMA still needs ledger, outbox, effects, timers (long waits), inbox, heartbeat |
| Truth sources | One (ledger) | Two unless ledger writes occur inside DBOS transactions and `workflow_refs` is deleted |
| SQLite (LOCAL) | Designed for it, claim inside `BEGIN IMMEDIATE` | Supported but dev/test-grade; known multi-worker queue edge case (UNVERIFIED) |
| PostgreSQL (SERVER) | `FOR UPDATE SKIP LOCKED`, RLS | First-class, best-supported path |
| Crash semantics | Lease expiry and reclaim; step must be idempotent | Replay from journal; steps at-least-once unless transactional; workflow code must be deterministic |
| LLM-step integration | Own journal of model calls; no replay of non-deterministic output unless stored | Ready-made journaling of model/tool calls; one engine per agent; behavior-policy hooks must fit its replay rules |
| Testability | Deterministic clock and fault injection are fully ours | Engine internals opaque; replay semantics add test surface |
| Dependency/license | stdlib `sqlite3`, `psycopg` | MIT; brings its own system tables, migrations, SQLAlchemy stack (UNVERIFIED), upgrade coupling |
| Windows/macOS | Pure Python, portable | Pure Python; SQLite path portable (UNVERIFIED on Windows CI) |
| Multi-tenant server | Tenant keys and RLS under our control | DBOS state is not tenant-scoped by itself; RLS over its tables would be our job (UNVERIFIED) |
| Protected kernel | Invariants enforced in our transaction | Engine sits outside the kernel; "authorization before effects" and "versioned behavior policy" must be re-checked inside replayed steps |

Reading: DBOS would remove roughly the claim/lease/retry code (a few hundred lines) but not the ledger, outbox, timers with `fire_until`, inbox, heartbeat or effect reconciliation. The saving is smaller than it looks and it adds coupling to the kernel invariants. The strongest counter-argument is the same-transaction checkpoint for business writes; but SECMA's ledger already gives that atomicity natively because the worker commits event, outbox and next timer in its own transaction.

## 4. Recommendation (single)

**Keep ADR-015 (ledger-driven worker over one LedgerPort), but amend it**: (a) correct the factual claim that DBOS cannot serve LOCAL, replacing it with the verified reasons (SQLite is dev/test-grade in DBOS, multi-worker SQLite queue edge cases, second truth source, replay determinism against the protected kernel); (b) define the `DurableRunner` conformance suite now so a DBOS or Absurd adapter for SERVER stays an option, and add a Pydantic AI-agnostic "model call journal" in the ledger so LLM outputs are stored once and not re-sampled after a crash; (c) pin SQLite minimum version for the WAL-reset fix. Revisit adoption of DBOS only for the SERVER profile after S-slices pass, if worker-HA needs exceed `SKIP LOCKED` claims.

## 5. Open risks to record

- SQLite WAL on synced folders or network drives is unsupported: `doctor` must refuse such paths.
- Checkpoint starvation from long read transactions in the CLI: bound read transaction length.
- `BEGIN IMMEDIATE` with `busy_timeout` (several seconds) and a retry-with-jitter wrapper; verified only by test, not by this research (UNVERIFIED as best practice here).
- Laptop sleep: worker lease clocks must use wall-clock plus a monotonic sanity check; a resume after long sleep must treat all leases as expired candidates, not assume the old holder is dead without checking the lock row.

## Recommended deltas

| Target file | Change | Priority | Slice |
|---|---|---|---|
| docs/adrs/ADR-015.md | Replace the DBOS rejection rationale: remove "needs PostgreSQL", add verified SQLite dev/test status, queue-concurrency caveat (UNVERIFIED), replay-determinism vs kernel, and the same-transaction checkpoint counter-argument | High | Spec (now) |
| docs/rfcs/RFC-003_DURABLE_EXECUTION_PORT.md | Add DurableRunner conformance suite and an "adapter admission" checklist (DBOS, Absurd, Temporal); model-call journal rule (store LLM output once, no re-sampling on recovery) | High | S02 |
| docs/adrs/ADR-016.md | Cite systemd `Persistent=` semantics, no `WakeSystem` for user timers; add launchd and Task Scheduler catch-up verification as an open item | Medium | S04 |
| TRD / BOUNDARY_CONTRACTS (ledger section) | Minimum SQLite version (WAL-reset fix: 3.51.3 or backports 3.50.7 / 3.44.6); `doctor` check; refuse network and synced paths for LOCAL DB | High | S01 |
| tests/chaos (registered as DUR-09/DUR-10) | Two-connection concurrent write/checkpoint stress test and sleep/resume lease test on SQLite | Medium | S01 |
| docs/adrs/ADR-003.md | Keep superseded; add link to this note | Low | Spec |
| contracts/durable-execution.schema.json | Keep engine enum `ledger | mock`; add a note that `dbos`/`absurd` need an adapter ADR | Low | S02 |
| docs/research/SOTA_DURABLE_EXECUTION_2026-11-15.md follow-up | Verify Restate, Inngest, Hatchet, pgmq, LangGraph, launchd and Task Scheduler claims against primary sources | Low | Spec |
