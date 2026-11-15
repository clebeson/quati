# SECMA implementation-ready package index

**Current mode: SPECIFICATION_ONLY.** No new runtime implementation is authorized
by this package. Existing code is a retained unapproved S00 candidate; its tests and
limitations are historical observations, not proof of the revised full product.

## Read order

1. AGENTS.md and canonical `docs/implementation/implementation_state.json`.
2. `docs/vision/PRODUCT_PRD.md` and `docs/architecture/PROJECT_STRUCTURE.md`.
3. `docs/governance/DELIVERY_GOVERNANCE.md` — SDD/TDD/EDD, audits and required seals.
4. `docs/governance/PERSISTENT_STATE_AND_MEMORY.md` — locks, CAS, memory and resume.
5. `docs/architecture/BOUNDARY_CONTRACTS.md` and relevant schemas — exact trust and operation semantics.
6. `docs/implementation/ROADMAP.md`, `WORK_PACKAGES.json` and selected `work_packages/Sxx.md`.
7. `docs/testing/TEST_EXECUTION_PROTOCOL.md`, `ACCEPTANCE_CASES.json`, `REQUIREMENT_TEST_PLANS.json` and fixture recipes.
8. `docs/traceability/FULL_REQUIREMENTS_MATRIX.csv` — complete planning registry; not a test-pass registry.
9. `docs/audit/SPECIFICATION_READINESS_AUDIT.md` — final findings, checks and limitations.
10. `docs/implementation/SMALL_MODEL_EXECUTION_PROMPT.md` — future bounded agent execution.

## Package contents that matter

- 31 module PRDs, 12 RFCs and 12 ADRs, preserving the original architecture.
- 240 explicit requirement/acceptance/threat/invariant/shared-obligation plans.
- 47 shared acceptance scenarios with inputs, operations, assertions, negatives, faults and proof tiers.
- 31 synthetic module fixture recipes; sealed evaluator data stays separate.
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
No actual model, DBOS crash, external-provider or OS qualification is claimed by
these offline commands.

## Execution prerequisites, not hidden design decisions

Future S00 needs an approved tool-capable model endpoint/model ID/secret reference
and bounded synthetic-call authorization. S02 needs real PostgreSQL and DBOS test
resources. S04 needs an approved actual harness; external integrations require
isolated authorized accounts before their features are claimed supported. S07
needs actual target OS hosts and deployment resource/egress profiles. All are
explicitly BLOCKED when absent; none should be fabricated or requested merely to
complete this specification audit.
