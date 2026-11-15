# Final independent specification readiness review

## Scope and disposition

This is a read-only specification audit of the implementation handoffs, governance and memory contracts, shared acceptance scenarios, requirement-level plans, work-package registry, canonical engineering state, and the v2 commitment artifacts. It does not review or qualify candidate runtime code. The retained S00 candidate remains unapproved.

**Disposition: NOT READY for small-model implementation handoff.** The offline structural readiness validator passes at L0, but it expressly does not establish semantic coverage. The findings below leave material ambiguity about which tests close each task, what durable record a worker must read/write for seals, and the exact v2 state payload.

## Findings

### F1 — Requirement plans are not closed into task-level test gates (P1)

`WORK_PACKAGES.json` gives each task a `requirement_ids` list and a `test_case_ids` list, while `REQUIREMENT_TEST_PLANS.json` separately gives every obligation its own `planned_test_path`, `shared_case_refs`, `work_package_refs`, and `final_gate_task`. There is no binding rule that tells the task owner to execute the requirement-specific planned test for every assigned obligation, nor a machine-readable mapping from an obligation to the task that must run its test. The readiness validator only checks that these references exist; it does not check coverage or task-scope alignment.

For example, S00-T01 owns 29 requirements but lists only SOC-01. Its done conditions cover three CLI behaviors, and there is no declared completion rule tying the other M01/M02/M26 planned tests to this task. At the other end, 53 plans use S07-T04 as final gate. A future implementer cannot tell whether the last task re-runs every historical obligation, consumes sealed prior evidence, or re-tests only its listed OPS/EVD cases. Those choices affect the exact gate and evidence required.

**Required correction:** define an explicit per-task obligation/test set (or an unambiguous rule to derive it from `work_package_refs` and final gates), state whether tests run at contribution versus final acceptance, and make task completion require current evidence for each applicable plan. Mark shared cases used outside their declared slice as regression reuse or remove the ambiguous cross-slice references. Do not treat the 240 planning rows as executed coverage.

### F2 — v2 commitment payload cannot represent several required lifecycle invariants (P1)

`BOUNDARY_CONTRACTS.md` says every nonterminal commitment has a persisted `next_action` and deadline; it also requires goal revision, current evidence, responsible blocker ownership, and preserved dispatch/effect state on BLOCKED/resume. `contracts/commitment-v2.schema.json` currently permits only `next_update_at`, state, revision, outcome verdict/ref and identity basics. It has no `next_action`, deadline, goal revision, blocker owner/reason, effect state, or evidence/current-assessment reference. Thus a record that validates against the declared v2 schema can omit fields needed to enforce the normative control-table rules.

Additionally, `BOUNDARY_CONTRACTS.md` names `CONTROL_TRANSITIONS.csv` as a view of the normative JSON, but that file is absent. The JSON transition table is checked by an ad-hoc L0 function rather than a declared schema. The cross-artifact check currently establishes only equal state vocabularies, not completeness of the per-state payload or guard/action vocabulary.

**Required correction:** extend the v2 payload contract to carry the fields needed by the normative lifecycle (or explicitly define a separate linked ledger record schema with exact required fields), add the promised generated CSV view or remove that claim, and validate table shape and cross-artifact fields structurally.

### F3 — The resume protocol has no canonical current-seal lookup/reference (P1)

`DELIVERY_GOVERNANCE.md` says seals are immutable, digest-scoped, invalidated by transitive artifact changes, and required by gates. `PERSISTENT_STATE_AND_MEMORY.md` tells a resuming model to identify current seals. But `implementation_state.json` has gate statuses and evidence references without seal IDs/paths, and the schema has no per-gate seal reference. The seal directory is empty, and no index/lookup format or selection rule for “latest valid seal for scope+digest” is specified. A future worker can see a gate marked PASS without being able to identify the exact seal record, verify its artifact map, or determine whether it was superseded.

**Required correction:** store explicit seal references per gate (including scope, kind, verdict and record path/ID) or specify a deterministic seal registry index and verification lookup; define how gate status is reconciled with seal status. Current empty seals are appropriate for the paused, unexecuted state and are not themselves a defect.

### F4 — Task handoffs do not identify the memory records required at resume/checkpoint (P2)

Memory registries and sample fixture, bug, debt, achievement, decision and lesson records exist, and their schemas validate. However, task handoffs and canonical state do not carry the relevant memory IDs/paths to inspect or update; `active_work.pending_findings` is empty in the current state and the general work-package resume action only says to resume from state. The directory convention is discoverable, but the governance rule requires open bugs/debt/decisions and evidence-backed record updates to be considered before proceeding. A small model may miss a known P1 bug or mark a task complete without updating its regression/achievement record.

**Required correction:** add memory refs (or defined registry indexes with mandatory query rules) to state/checkpoint and task handoff, and specify which record types are mandatory to check/update per task. Preserve existing `OPEN` historical bug/debt and `NOT_RUN` test status; do not rewrite them as resolved based on the specification audit.

## Checks and limits

- `python SECMA_SPEC_V8_EN/spec_tools/validate_readiness.py` passes: 240 requirements, 47 shared cases, 240 obligation plans, 35 work packages and 78 fixture recipes at L0.
- All 47 shared cases and 240 requirement plans are marked `NOT_RUN`; fixture recipes are planning recipes, not built fixture evidence.
- The L0 validator checks IDs, references, schema syntax, phase order, and selected v2 invariants. It does not validate semantic assertion coverage, per-task obligation closure, seal/state linkage, or that v2 record fields can represent the full normative behavior.
- No runtime, model, database crash-recovery, external-provider, native-OS or release qualification was performed or inferred.

## Ready criteria

Resolve F1–F3 before authorizing implementation. Resolve F4 before a small-model handoff. Then rerun structural readiness checks and have an independent semantic reviewer disposition the resulting mapping and lifecycle artifacts. Specification-only status remains in force until the user separately authorizes implementation.
