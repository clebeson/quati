# Persistent execution state and engineering memory

## Authority and durability

`docs/implementation/implementation_state.json` is the only authoritative execution progress record. CHECKPOINT.md, reports and chat are pointers, not alternate truth. State is checked into the project and included in every durable checkpoint archive. A local working directory or an agent's conversation memory is not a durable backup. Before stopping, save the validated checkpoint to the authorized persistent destination and record its returned identity/version in the handoff. Never claim that a local write alone guarantees cross-session persistence.

The engineering state is distinct from Quati's future product commitment ledger. Passing engineering resume tests proves nothing about ledger/worker recovery. Secret references may be recorded; secret values must never be saved.

## Canonical state fields

Keep schema_version, monotonically increasing revision, project/spec revision, work_mode, current_slice, per-slice status/gates/evidence/commit/blockers, active_work, known_unverified, last_updated_at. `active_work` has work_package_id, phase (DISCOVER/SDD/TDD_RED/IMPLEMENT/EDD/AUDIT/CHECKPOINT), owner, input snapshot digest, completed steps, next command/action, owned files, pending findings and evidence refs. No ACTIVE task may be inferred from chat if state disagrees.

Statuses: NOT_STARTED, IN_PROGRESS, PASS, FAIL, BLOCKED. NOT_RUN is allowed for unexecuted tests/gates only. A slice can be PASS only if all mandatory gates are PASS and seals are current. NOT_VERIFIED_EXTERNAL describes integration evidence, not a successful gate. Record prototype completion separately from full module completion. A passed S00 never marks all of M01/M02/M17/M30 complete.

## Atomic update protocol

1. Read revision R from `implementation_state.json`.
2. Make the change, validate IDs, dependencies, gate evidence and legal status transitions, and reject editing downstream work as active while an earlier mandatory gate is incomplete.
3. **Compare-and-set under writer coordination:** canonical metadata writers use scripts/checkpoint_execution.py and the same canonical state path. A bounded POSIX advisory flock serializes revision validation, journal/state/ledger writes and recovery. Re-read revision R under that lock; if changed, abort and rebase. Write the next document to a same-filesystem temporary file, fsync, atomically replace and increment exactly once. Revision re-read plus rename alone is not atomic CAS against an uncoordinated writer. Never merge by last-writer-wins.
4. **Commit:** when an authorized writable Git checkout is available, record the change with a git commit. The commit is the checkpoint source identity. In an exported tree without writable Git metadata, record source_commit=null and a checksummed package manifest; report the missing persistent-save receipt rather than inventing a commit. There is no persistent lease/token/expiry protocol. The helper uses a transient OS-released advisory lock; Git history or an export snapshot identifies the checkpoint source.

The legacy `lease_token` and `lease_expires_at` fields were removed from the state schema (2026-11-15); the transient advisory writer lock plus revision check is the local concurrency control. Legacy `scripts/checkpoint_state.py` does not participate in this journal protocol; it refuses to run (exit 2) when `execution_ledger.jsonl` or `execution_journal/` exists next to the target state file. Use `scripts/checkpoint_execution.py`.

A crash before rename leaves the previous revision authoritative. A crash after rename requires reading the new revision, not retrying the update blindly. If directory fsync is unsupported, record the platform limitation; native crash durability remains S07 qualification. A failed save leaves CHECKPOINT_PENDING and the exact next action; it does not mark a slice PASS.

## Resume procedure for any model

1. Read AGENTS, README, canonical state and latest checkpoint manifest; verify source/evidence hashes.
2. If work_mode is SPECIFICATION_ONLY, perform only the requested audit/specification work. Do not execute implementation tasks.
3. Identify the earliest incomplete gate and exact active work package. Read its contract versions and case IDs, open bugs, decisions and current seals.
4. Verify previous tests were executed against the same source/config/fixture snapshot. Reuse valid evidence; rerun only invalidated or interrupted checks.
5. Read LOG.md as well as the legacy memory index. Check that the revision is unchanged since you read it (compare-and-set) and the git tree is clean. State what was already completed and the next bounded action.
6. Continue from that action. Do not regenerate the whole project, overwrite prior evidence, skip failed tests, restart the roadmap or assume a model/provider is configured.

## Legacy engineering memory schemas and fixture ownership

New bug/debt/decision/lesson/achievement and risk events go to docs/governance/LOG.md.
The versioned records below are preserved historical inputs; their OPEN statuses are not
silently closed. A later LOG event may resolve an old ID only with the required proof.
New fixture provenance continues to use the fixture schema and memory index.
The legacy schema/index validator checks preserved records, not a requirement to create
six separate registries for each task.

All records use the schema in `state/schemas/engineering-record.schema.json`, with type-specific required fields below. Index files contain IDs and paths only; individual immutable versions carry facts. Append a new version to change a record, retaining supersedes/source evidence. Never place client-private material in fixtures or memory.

| Registry | Required content | Completion condition |
|---|---|---|
| fixtures | fixture_id, version, source classification/license, purpose, construction recipe, seed, SHA-256, allowed use, privacy class, oracle location, covered case IDs | validated bytes match checksum; gold labels inaccessible to tested model |
| bugs | bug_id, severity, trigger, expected/observed, affected requirement IDs, public reproduction, first failing evidence, root cause, owner, regression case, resolution | regression passes and independent relevant reviewer verifies; otherwise OPEN/BLOCKED |
| debt | debt_id, shortcut, reason, risk, owner, expiry/trigger, bounded repair plan, tests proving limitation | repaired with evidence or explicitly renewed by authorized owner; cannot waive kernel invariants |
| achievements | achievement_id, precise user outcome, scope, proof tier, source/config/fixture digest, evidence, reviewer, limitations | evidence-backed verified outcome only; document count and mock success are not live achievements |
| decisions | decision_id, ADR/RFC ref, question, alternatives, choice, rationale, consequences, migration/supersession | decision accepted for identified scope; external availability remains separately measured |
| lessons | lesson_id, incident/bug/evidence refs, root lesson, applicable boundary, preventive change, regression link | supported observation; no speculative anecdote promoted to policy |

A fixture oracle is not model-visible source. Seed data may be public; sealed holdout labels remain in a separate restricted evaluator location with a checksum and access log. Never write chain-of-thought. Sanitized evidence must preserve the information needed to reproduce the decision without credentials or restricted content.

## Checkpoint contents

Include canonical specifications, schema/examples, traceability, test plans, work packages, governance/memory records, current state, source candidate if retained, red/green results, known failures and exact reproduction commands. Include source hashes and version/commit history or a git bundle when no remote repository is synced. Exclude credentials, caches, installed dependencies and unrelated local files. A final archive checksum cannot be embedded inside itself; record it in the delivery/save receipt or a sibling manifest.

## Deterministic memory lookup on resume

`memory/index.json` maps stable record IDs and versions to paths, types, status,
requirement IDs and scope. It is rebuildable from immutable records. Each work
package includes `memory_lookup`: match its related requirement IDs, include
DEC-001 and LESSON-001 globally, and inspect OPEN/IN_PROGRESS/BLOCKED bugs, debt,
decisions and fixture records. Canonical `active_work.memory_refs` identifies the
records relevant to the current checkpoint. Runtime-candidate defects remain
OPEN until a future implementation proves their resolution; a planning audit
does not close them.

At a task checkpoint, append governance events to LOG.md, referencing existing IDs
when applicable. Append fixture versions and refresh their index when fixture bytes
change. Record an achievement only after its evidence is verified. If state and index disagree,
rebuild the index from record versions, record the recovery and re-run lookup;
never drop an OPEN record to make a gate pass. CHECKPOINT.md links canonical state
and both indexes. Seal lookup uses `seal_registry_ref` and per-gate references,
not a search for a filename containing PASS.

## Recoverable execution journal (authorized implementation)

`execution_ledger.jsonl` stores strictly contiguous revisions after an explicit first
anchor. Every event includes the previous event hash, before/after canonical-state
hashes, phase, next action, completed steps and the active-work metadata patch.
Hashes use sorted, compact UTF-8 JSON with ensure_ascii=False, the engineering
journal encoding; this is distinct from product `quati-json/1` canonical digests.
The chain is unkeyed: it detects accidental/incomplete edits, not an actor who can
rewrite the entire state/history. Never call it tamper-proof.

Each update first writes a complete immutable prepared event and state_after under
`execution_journal/`. Sync the event file, journal directory and newly created journal
parent before canonical state replacement. Then sync the replaced state/directory,
append and sync the ledger row and its directory. Recovery accepts only a matching
before-state or matching already-replaced after-state, completes the missing work,
and stops for the caller to re-read before submitting another update. Divergent hashes,
missing revisions, authority/mode violations and wrong revisions fail closed.

Metadata updates cannot change execution authorization, slice statuses or gate values.
Resolving a finding removes the exact tracked pending item and records that resolution
in the journal; root supplies the corresponding review/evidence reference. Any future
gate-promotion tool must join this writer protocol and validate the applicable seals.
No legacy helper or direct JSON write may bypass the journal after initialization.

On an IO/fsync failure the helper emits CHECKPOINT_PENDING and the exact re-read/recovery
next action, with a platform/IO limitation. Do not claim the failure receipt was saved
when the same filesystem is unavailable. Recovery tests include actual subprocess
termination and cooperating-writer contention where observed; they do not qualify
host power loss, network filesystems, native Windows/macOS or the product ledger.
Always resolve the same canonical state/ledger paths; path aliases and unrelated
writers are outside the tested advisory-lock guarantee.

Task-DAG acceptance is an orchestrator/reviewer obligation: before changing the active
work package, inspect the predecessor's linked delivery receipt, tests and independent
review. The metadata helper checks the current/earliest incomplete slice ceiling; it
does not infer task acceptance from counts or automatically certify same-slice task
dependencies. It cannot promote a task, slice or gate or launch runtime work. Record
the actual predecessor acceptance and its evidence in the canonical completed_steps
and evidence_refs before selecting the next task. No metadata event substitutes for
the required semantic review.
