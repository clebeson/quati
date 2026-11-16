# Quati implementation-ready package index

**Current mode: IMPLEMENTATION_AUTHORIZED.** The user authorized incremental delivery
from S00 with SDD/TDD/EDD, independent audits and continuous checkpoints. Canonical
state selects the active task. Existing candidate code must be requalified; passing
specification checks never promotes runtime gates.

## Read order

1. AGENTS.md and canonical `docs/implementation/implementation_state.json`.
2. `docs/vision/PRODUCT_PRD.md` and `docs/architecture/PROJECT_STRUCTURE.md`.
3. `docs/governance/DELIVERY_GOVERNANCE.md` — SDD/TDD/EDD, audits and required seals.
4. `docs/governance/PERSISTENT_STATE_AND_MEMORY.md` — locks, CAS, memory and resume.
5. `docs/architecture/BOUNDARY_CONTRACTS.md` and relevant schemas — exact trust and operation semantics.
   `docs/architecture/GUARD_PREDICATES.md` and `contracts/guard-registry.json` define every lifecycle guard; `docs/prds/PRD_COMMON.md` holds the rules shared by all PRDs, and each PRD's `## Normative detail` and `## Test oracles` sections are authoritative.
6. `docs/implementation/ROADMAP.md`, `WORK_PACKAGES.json` and selected `work_packages/Sxx.md`.
7. `docs/testing/TEST_ENGINEERING_STANDARD.md` (coverage gates, determinism, who writes and who runs tests), `docs/testing/TEST_EXECUTION_PROTOCOL.md`, `ACCEPTANCE_CASES.json`, `REQUIREMENT_TEST_PLANS.json` and fixture recipes.
8. `docs/traceability/FULL_REQUIREMENTS_MATRIX.csv` — complete planning registry; not a test-pass registry.
9. `docs/audit/SPECIFICATION_FINALIZATION_2026-11-15.md` — current reconciliation, checks and limitations; earlier audit reports remain historical inputs.
10. `docs/implementation/PARALLEL_EXECUTION_AND_MODEL_ROLES.md` — roles, parallel work and the single-writer rule; `docs/implementation/CODEX_WORK_MASTER.md` — master handoff; `docs/implementation/SMALL_MODEL_EXECUTION_PROMPT.md` — brief for smaller implementer and test-runner models.

## Package contents that matter

- 31 module PRDs, 15 RFCs and 16 ADRs, preserving the original architecture.
- 243 explicit requirement/acceptance/threat/invariant/shared-obligation plans.
- 101 shared acceptance scenarios with inputs, operations, assertions, negatives, faults and proof tiers.
- 125 synthetic fixture recipes (31 module recipes and 94 case recipes); sealed evaluator data stays separate.
- 35 dependency-ordered work packages, with owned paths and acceptance conditions.
- Governance seal and engineering memory schemas; records for known defects and historical checks.
- Version-2 durable commitment transition specification, keeping version-1 compiler fixtures separate.
- One canonical persistent execution state and explicit recovery/resume procedures.

## Checks

Use Python 3.12+ and the pinned test dependencies. The authoritative planning check is:

```bash
python spec_tools/validate_spec.py
python spec_tools/validate_readiness.py
python -m pytest tests/test_reference_compiler.py tests/test_audit_regressions.py tests/test_spec_readiness.py
```

Candidate runtime tests are separate. A mismatch against the revised specification
must be repaired by a future authorized implementation, not by weakening the spec.
No actual model, ledger/worker crash, external-provider or OS qualification is claimed by
these offline commands.

## Execution prerequisites, not hidden design decisions

Future S00 needs an approved tool-capable model endpoint/model ID/secret reference
and bounded synthetic-call authorization. S02 needs the SQLite ledger/worker test
harness; the PostgreSQL backend needs a real PostgreSQL instance to pass the RFC-003 conformance suite. S04 needs an approved actual harness; external integrations require
isolated authorized accounts before their features are claimed supported. S07
needs actual target OS hosts and deployment resource/egress profiles. All are
explicitly BLOCKED when absent; none should be fabricated or requested merely to
complete this specification audit.
