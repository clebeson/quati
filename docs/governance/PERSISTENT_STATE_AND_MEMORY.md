# Persistent execution state and engineering memory

## Authority and durability

`docs/implementation/implementation_state.json` is the only authoritative execution progress record. CHECKPOINT.md, reports and chat are pointers, not alternate truth. State is checked into the project and included in every durable checkpoint archive. A local working directory or an agent's conversation memory is not a durable backup. Before stopping, save the validated checkpoint to the authorized persistent destination and record its returned identity/version in the handoff. Never claim that a local write alone guarantees cross-session persistence.

The engineering state is distinct from SECMA's future product commitment ledger. Passing engineering resume tests proves nothing about DBOS recovery. Secret references may be recorded; secret values must never be saved.

## Canonical state fields

Keep schema_version, monotonically increasing revision, project/spec revision, work_mode, current_slice, per-slice status/gates/evidence/commit/blockers, active_work, known_unverified, last_updated_at. `active_work` has work_package_id, phase (DISCOVER/SDD/TDD_RED/IMPLEMENT/EDD/AUDIT/CHECKPOINT), owner, lease token/expiry, input snapshot digest, completed steps, next command/action, owned files, pending findings and evidence refs. No ACTIVE task may be inferred from chat if state disagrees.

Statuses: NOT_STARTED, IN_PROGRESS, PASS, FAIL, BLOCKED. NOT_RUN is allowed for unexecuted tests/gates only. A slice can be PASS only if all mandatory gates are PASS and seals are current. NOT_VERIFIED_EXTERNAL describes integration evidence, not a successful gate. Record prototype completion separately from full module completion. A passed S00 never marks all of M01/M02/M17/M30 complete.

## Atomic update protocol

1. Read revision R and required source digest. Acquire an exclusive task/state lock with owner/token; refuse another live owner.
2. Re-read R under lock. If it changed, abort and rebase; never merge JSON by last-writer-wins.
3. Validate IDs, dependencies, gate/seal evidence and legal status transitions. Reject editing downstream work as active while an earlier mandatory gate is incomplete.
4. Write the complete next document to a same-filesystem temporary file, flush and fsync, atomically replace, then fsync the directory where supported. Increment revision exactly once.
5. Release only the acquired lock. Persist the checkpoint after successful local validation. An abandoned lock requires inspecting owner/process/lease and recording recovery; never delete a lock simply to make a command pass.

A crash before rename leaves the previous revision authoritative. A crash after rename requires reading the new revision, not retrying the update blindly. If directory fsync is unsupported, record the platform limitation; native crash durability remains S07 qualification. A failed save leaves CHECKPOINT_PENDING and the exact next action; it does not mark a slice PASS.

## Resume procedure for any model

1. Read AGENTS, README, canonical state and latest checkpoint manifest; verify source/evidence hashes.
2. If work_mode is SPECIFICATION_ONLY, perform only the requested audit/specification work. Do not execute implementation tasks.
3. Identify the earliest incomplete gate and exact active work package. Read its contract versions and case IDs, open bugs, decisions and current seals.
4. Verify previous tests were executed against the same source/config/fixture snapshot. Reuse valid evidence; rerun only invalidated or interrupted checks.
5. Recover locks safely; obtain task ownership through CAS. State what was already completed and the next bounded action.
6. Continue from that action. Do not regenerate the whole project, overwrite prior evidence, skip failed tests, restart the roadmap or assume a model/provider is configured.

## Engineering memory schemas and file ownership

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

At a task checkpoint, append new versions of changed bug/debt/decision/fixture
records and refresh the index atomically with the checkpoint intent. Record a new
achievement only after its evidence is verified. If state and index disagree,
rebuild the index from record versions, record the recovery and re-run lookup;
never drop an OPEN record to make a gate pass. CHECKPOINT.md links canonical state
and both indexes. Seal lookup uses `seal_registry_ref` and per-gate references,
not a search for a filename containing PASS.
