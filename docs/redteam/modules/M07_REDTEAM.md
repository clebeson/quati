# Red Team — M07: Commitment ledger and durable execution

**Target slice:** S02. **Scope:** candidate threats specific to M07, not exploit proof. Oracles: `docs/prds/M07.md` § Test oracles.

## Attack cases

- **M07-RT-01**: A single local worker presented as highly available.
  - **Attack input:** with W1 holding the `worker_locks` lease, start W2 (`quati worker run`) for the same deployment; set config `worker.instances: 2` and `availability: ha` in the config file; ask the assistant "is my worker highly available?" and inspect the receipt.
  - **Enforcement point:** `worker_locks` lease acquisition (single row per `deployment_id`); closed config schema (M01 config write rule: unknown keys `worker.instances` and `availability` → `config validate` exit 2 `config_unknown_key`); `status`/`doctor` compute `availability` from the profile, never from config or model text.
  - **Expected rejection:** W2 exits 4 `worker_lock_held` and writes no heartbeat; the config is rejected with `INVALID_INPUT`; `status --json` reports `availability: "single_worker"`; no receipt or evidence contains an HA or failover claim.

- **M07-RT-02**: Memory exhaustion through many long-lived waiting commitments.
  - **Attack input:** 10,000 commitments in `WAITING_INPUT` with timers 30 days ahead, plus 100 due items, created through `CommitmentLedger.accept` from a script.
  - **Enforcement point:** worker claim query (`LIMIT worker.claim_batch_size`, `not_before <= now`); no in-process registry of waiting commitments; instrumentation counter `loaded_commitments_max`.
  - **Expected rejection:** `loaded_commitments_max` equals `claim_batch_size`; RSS growth between the 100 and 10,000 baselines ≤ `worker.max_rss_growth_mib`; the 100 due items complete; no waiting commitment changes state.

## Fail-closed and recovery requirements

A failed CAS, guard, lease or idempotency check writes nothing and returns `CONFLICT` with its reason code. A crash at any named hook leaves the prior committed state, and recovery never deletes unknown-effect history or dispatches an effect twice without `confirmed_no_effect`.

## Release blocking guidance

Both cases block S02. A test that checks only a message string, or that replaces the real worker subprocess with an in-process stub for M07-AT-01, does not count.
