# Execution checkpoint helper — independent review

**Review date:** 2026-11-15  
**Scope:** `scripts/checkpoint_execution.py`, its tests, and `docs/governance/PERSISTENT_STATE_AND_MEMORY.md`.  
**State safety:** The helper was not run against project canonical state. All review fixtures used temporary files.  
**Disposition:** **Acceptable for bounded local engineering-metadata checkpointing under the amended contract.** This does not qualify host power-loss durability or SECMA's product commitment ledger.

## Final re-review

After the author's fixes, this command passed **30 tests**:

```text
python3 -m pytest tests/unit/test_execution_checkpoint.py tests/unit/test_execution_checkpoint_review.py -q
30 passed
```

The review tests also launch two real CLI subprocesses at a shared start barrier with the same expected revision. Exactly one saves and one receives a revision conflict; the final state and single ledger row agree. The concurrency test passed five additional independent runs.

Two actual helper subprocesses were terminated with `SIGKILL`: once after the real atomic prepared-journal write and once after the real atomic canonical-state replacement, before ledger append. In each case, the normal CLI recovery path completed one event and returned a re-read-required conflict instead of applying a second update. These are local L1 engineering subprocess proofs, not host crash or power-loss tests.

## Findings and closure

- **ECP-01 — journal directory durability (closed):** The initial implementation did not sync the parent directory for a newly created journal directory before canonical state replacement. The helper now syncs the journal directory and its parent before advancing state. `test_parent_directory_is_synced_before_canonical_state_replace` verifies the real fsync/replace ordering.
- **ECP-02 — authorization/slice guard (closed within helper scope):** The helper now rejects missing or unknown implementation work modes, checks explicit execution authorization when present, and requires a nonempty canonical slice map plus a known `current_slice`. It enforces the earliest-incomplete/current-slice ceiling. Tests reject missing, empty, missing-current and unknown-current slice authority without writing state or a ledger. Metadata patches cannot edit work mode, authorization, slice statuses or gates.
- **ECP-03 — fsync failure handoff (closed):** I/O/fsync errors produce structured `CHECKPOINT_PENDING` output with a recovery action and platform/IO limitation. The helper does not claim that the diagnostic was saved when the filesystem may be unavailable. The failure-path test injects an `OSError`; no unsupported-filesystem or power-loss behavior is inferred.
- **ECP-04 — revision continuity (closed):** The helper validates event hashes and predecessor hashes and requires consecutive revisions after the first ledger anchor. The test constructs a self-consistent, hash-valid 9→11 gap and confirms rejection.
- **Malformed canonical input (closed for reviewed shape checks):** Scalar state, boolean/non-integer revision, missing/non-object `active_work`, and missing or invalid slice authority fail before writes.

## Contract and authority boundaries

The amended `PERSISTENT_STATE_AND_MEMORY.md` now matches the transient POSIX `flock`, journal-first fsync ordering, metadata-only scope and structured pending-checkpoint diagnostic. The helper serializes cooperating CLI writers using the same canonical state path. The contract explicitly excludes path aliases and unrelated/non-participating writers from this tested guarantee; the helper's module docstring also discloses that boundary.

The helper does **not** validate same-slice task-DAG dependencies, delivery receipts or the semantic quality of evidence. The amended contract assigns predecessor receipt and independent-review checks to the orchestrator/reviewer before switching active work packages. The helper cannot promote a task, slice or gate and cannot launch runtime work. A `resolve-finding` event records the exact pending item and metadata patch; the caller remains responsible for supplying the corresponding review/evidence reference as required by the workflow.

The journal chain is unkeyed. It detects accidental or incomplete edits, not an actor able to rewrite canonical state and the full ledger. The implementation uses POSIX `flock`; this review does not qualify native Windows/macOS or network filesystems. No claim is made about SECMA's runtime product ledger.

## Evidence

The exact test command, result, environment, and SHA-256 digests of the reviewed helper, tests, contract, and this report are recorded in `evidence/S00/engineering-checkpoint/review/independent-recheck-20261115T2200Z.json`. The evidence is labeled `L1_ENGINEERING_SUBPROCESS` and is not a product recovery qualification.
