# Delivery Plan Changes, 2026-11-15

> Historical audit snapshot. The current reconciliation and observed checks are in `SPECIFICATION_FINALIZATION_2026-11-15.md`; older counts and dispositions describe their original scope.


Responds to docs/audit/GENERAL_AUDIT_2026-11-15.md findings A-11, A-12, A-21, A-22, A-23 and A-24, plus RFC-013 section 13 identity cases. Documentation only; no runtime source was written.

## Decisions applied

1. **MVP (A-22).** ROADMAP.md has a "Product MVP" section: S00+S01+S02, Linux, proof tiers L2/L3, LOCAL profile only. S03+ is ordered post-MVP backlog. S05 also carries the SERVER profile (IDN-04..11). S03 and S04 are independent after S02 (S04-T01 depends on S02-T05; S05-T01 on S04-T05 and S03-T04). Windows/macOS native is S07. Slice notes were added to SLICES/S02, S04 and S05.
2. **S00 gate (A-21).** CAP-01/02 must each pass 9 of 10 live runs with trajectories and recorded provider/model identity. MOD-01 moved to S04-T05 as a precondition for autonomous routing and role promotion. Updated in WORK_PACKAGES.json, work_packages/*.md, ACCEPTANCE_CASES.json, TEST_LEDGER.csv, TEST_CASES.md, TEST_EXECUTION_PROTOCOL.md, ROADMAP.md, S00_RUNTIME_CONTRACT.md and SLICES/S00.md.
3. **Governance (A-23).** DELIVERY_GOVERNANCE.md: three mandatory seals per slice, minimum manifest of commit SHA + test log + transcript hash, "independent" defined as fresh-context reviewer or human owner and stated to be a process control, not cryptographic. PERSISTENT_STATE_AND_MEMORY.md: revision compare-and-set plus git commit replaces lock/lease. ERI rubric is advisory (TEST_EXECUTION_PROTOCOL.md, TEST_STRATEGY.md); the S01 gate uses machine-checkable assertions. New docs/governance/LOG.md replaces the separate registries; old registry guidance is marked deprecated in BUGS_DEBT_LOGS_AND_FIXTURES.md and DOCUMENT_INDEX.md. Seal schema, validators and per-file manifest tooling were left unchanged and are now optional.
4. **Mechanical (A-24).** All `tests/planned/...` locators mapped to tests/unit|integration|evals|external|chaos|packaging (also in build_matrix.py output). PROJECT_STRUCTURE.md documents the convention and `tests/packaging/`. Status in SLICES/S00..S07.md now points to implementation_state.json only.
5. **PRD tags (A-11/A-12).** Done earlier; build_matrix.py parses the optional header tag.
6. **Identity cases.** IDN-01..IDN-11 added to ACCEPTANCE_CASES.json (58 cases), TEST_LEDGER.csv, CASE_FIXTURES.json and attached to work-package tasks (IDN-01/02 at S00-T05, IDN-03 at S02-T05, IDN-04..11 at S05-T04), linked to M02/M25 requirements.

## M30 separability

M30 was not moved out of S00. S00 `ask` consumes a compiled profile and prompt receipt, and S00-GATE-04 and CMP-01..03 share S00-T02, so removal would break the S00 gate.

## Shared-file changes requested

- **AGENTS.md:** add `tests/packaging/` to the test directory list (line 37) and state that planned test locators use the real lane directories, never `tests/planned/`.
- **state/schemas/implementation-state.schema.json:** remove the legacy `lease_token` and `lease_expires_at` fields (currently nullable, left null).
- **Seal schema and validators:** optionally make `source_snapshot` per-file manifests optional and add the three-seal policy as the required minimum. Not done here to keep validators unchanged.
- **TYPE_CATALOG.md and commitment schema:** add priority P0..P3 and `due_at` for M08 (carried from earlier work).
- **ADR/TRD authors:** reconcile S02 (slice doc and gates assume PostgreSQL and DBOS) with the MVP LOCAL profile (SQLite, ledger-driven worker). DBOS/Postgres belongs to the SERVER profile.
- **M25.md:** `M25-AT-01-SLACK` is intentionally not matched by build_matrix.py; confirm its intended handling.

## Open questions

- Whether the S02 gate wording must be split into LOCAL and SERVER variants once ADR/TRD authors respond.
- `pytest -q tests` fails at collection in tests/unit/test_model_adapter.py (`No module named 'pydantic_ai'`), an environment issue that predates these edits.

> **Superseded (lead, 2026-11-15):** the "9 of 10" CAP-01/02 gate is replaced by 30/30 (10 paraphrases × 3 runs; Wilson lower bound 0.886). The shared-file requests listed here were applied: AGENTS.md tests/packaging, lease fields removed, TYPE_CATALOG priority (with `deadline_at`, no `due_at`), S02 reconciliation. M25-AT-01-SLACK is still an open question.
