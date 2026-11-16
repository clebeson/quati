# Common PRD rules

These rules apply to every module PRD (`docs/prds/M01.md` … `M31.md`). Each PRD references this file instead of repeating the text. A module PRD may tighten a rule; it may not relax one.

## 1. Contract and state expectations

- Inputs are typed and carry `request_id`, `actor_ref`, `tenant_ref` (or an explicit local principal), `policy_version` and `trace_id` wherever the module's boundary in `docs/architecture/BOUNDARY_CONTRACTS.md` declares them.
- Results of nontrivial work declare `status`, `evidence_refs`, `uncertainties` and `next_action`.
- External effects go through the effect gateway (M19) after authorization (M25). Prompt text, retrieved documents and tool output never trigger an effect directly.
- A module may compose several SCS capabilities, but it exposes one stable business boundary and never leaks vendor SDK types to domain callers.
- A state-changing operation requires: expected state revision (compare-and-set), idempotency key, authorization decision and trace. A missing optional integration returns typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`; it never returns a fabricated success.
- Typed error codes are the closed list in `BOUNDARY_CONTRACTS.md` ("Common wire and trust rules"). It includes `CONFIG_INVALID` (configuration or package content that is present but fails validation; `NOT_CONFIGURED` is for absent configuration) and `BUDGET_EXCEEDED` (a request, tool-call, token, quota or transition budget is exhausted before the work completes). Module-specific reason codes are detail tags under one of these codes; a PRD never introduces a new code.
- Wire shapes come from `contracts/*.schema.json`; port signatures come from `BOUNDARY_CONTRACTS.md` and `TYPE_CATALOG.md`. If a PRD disagrees with either, that is a specification bug: record it in `docs/governance/LOG.md` and fix the specification before writing code.

## 2. Scope limits (non-goals for every module)

- No separate microservice or specialized conversational agent merely because a module has a PRD.
- No new tool, model, queue, UI, policy language or data store unless a named acceptance case proves the existing boundaries cannot satisfy it.
- No production access, no unapproved external sends or writes, and no change of security configuration through generated prompts.
- Adjacent modules listed in a PRD are integration relationships, not a mandate to build them in advance.

## 3. Test policy

- Every FR, AT and RT ID has a row in the PRD's `## Test oracles` table naming one lane, one descriptive test function, its fixture, the deterministic expected observation and the negative observation. That row is the authoritative test name; `docs/testing/REQUIREMENT_TEST_PLANS.json` must agree with it.
- Lane selection, determinism rules, coverage thresholds and who writes versus who runs tests are defined in `docs/testing/TEST_ENGINEERING_STANDARD.md`.
- Each AT is demonstrated from the public entry path (CLI, application use case or provider port with production enforcement), not by calling an internal helper.
- Each RT is an adversarial test that exercises the real policy or state gate in code. A model refusing in text is not proof.
- A fault test is required wherever failure can corrupt state or safety; it uses a named crash-injection point, never a sleep.
- Shared contract tests are reused, not copied into every module.
- Each ID is tracked as `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. Document validation alone never produces `PASS`.

## 4. Definition of done

A module requirement is done when an implementer has demonstrated its test-oracle row from the public entry path, shown the negative and the relevant fault behavior, archived sanitized evidence through `scripts/record_evidence.py`, and an independent reviewer has confirmed that no unrequested scope was introduced.

## 5. Slice-tag convention and milestone interpretation

- The header line `Delivery slice` (or `Initial contribution slice`) names the slice of first implementation. A requirement line may end with `**Slice tag:** (Sxx)` to move that single requirement to a different slice.
- First implementation is not completion of the module. `docs/implementation/ROADMAP.md` and `docs/traceability/FULL_REQUIREMENTS_MATRIX.csv` define partial obligations and later gates. An unmet AT or RT stays `NOT_RUN` or `BLOCKED`; passing an early slice does not mark the module `PASS`.

## 6. Implementation handoff

Start from `AGENTS.md`, `IMPLEMENTATION_READY_INDEX.md`, the selected work package in `docs/implementation/work_packages/`, and the module PRD. Follow SDD → TDD → EDD and the role split in `docs/implementation/PARALLEL_EXECUTION_AND_MODEL_ROLES.md`.

## 7. Line format (tooling contract)

`docs/traceability/build_matrix.py` scrapes requirement lines. Each requirement stays on one physical line in the form `**Mxx-FR-nn (MUST):** body`, `**Mxx-AT-nn:** body **Evidence:** …` or `**Mxx-RT-nn:** body **Proof:** …`, optionally ending with a slice tag. IDs are never added, removed or renumbered without updating the inventory lock in `spec_tools/validate_readiness.py` through a recorded decision.
