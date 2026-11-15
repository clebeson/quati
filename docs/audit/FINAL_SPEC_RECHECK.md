# Final specification recheck

## Scope and disposition

Read-only recheck of the corrections for F1–F4 in the prior independent review. This covers work-package/test-plan closure, the v2 commitment payload and transition table, canonical seal lookup, and memory lookup/resume references. Runtime code and implementation behavior were not reviewed.

**Disposition: CONDITIONALLY NOT READY for a fully evidence-backed small-model handoff.** F1, F2 and F4 are resolved for specification planning. F3's canonical lookup and gate linkage are resolved, but the seal record still cannot carry all of the provenance that its normative policy requires.

## Recheck results

| Finding | Result | Basis |
|---|---|---|
| F1: task and requirement-test closure | Resolved | Tasks now distinguish related requirements, local assertions, task-owned and final-acceptance plan IDs, and contribution versus full-proof case ownership. Plans name the test owner and require full evidence or valid sealed reuse at that gate. |
| F2: v2 lifecycle payload | Resolved | The v2 schema now includes action/deadline, goal revision, blocker/reconciliation/effect and assessment/evidence fields with state-dependent requirements. A control-table schema, valid/invalid payload examples, type catalog and CSV equality check are present. |
| F3: seal lookup/provenance | Partially resolved; blocker remains | Canonical state has per-gate seal refs and a registry locator; the validator rejects PASS without referenced seals and checks record/artifact hashes. However, the seal schema's `evidence_refs` are bare strings and has no evidence-digest map or source snapshot/commit digest, although DELIVERY_GOVERNANCE requires evidence refs **and digests** and the source commit or snapshot digest on each seal. The seal-reference validator therefore cannot establish those required provenance links. |
| F4: memory lookup/resume | Resolved for current package | There is a typed memory index; every task has a requirement-scoped lookup rule; canonical active work lists the relevant memory records; handoffs require inspecting open bugs/debt/decisions and updating relevant records. Current memory index entries match the package's seven record files, and active-work references include those records. |

### Remaining blocker — seal evidence provenance fields (P1)

`state/schemas/governance-seal.schema.json` only permits `evidence_refs: string[]`; `validate_seal_references` checks referenced seal-file and artifact hashes but does not resolve or hash the seal's evidence files. The schema also has no source snapshot/commit digest, despite the seal-content rule requiring one. As written, an otherwise schema-valid PASS seal can cite evidence with no bound digest and no source snapshot identity, weakening the prescribed invalidation and same-snapshot review checks.

**Required correction:** define evidence references as immutable path/ID plus SHA-256 (or a referenced evidence manifest with an exact digest contract), include the reviewed source commit/snapshot digest, and make the L0 seal validator resolve and verify those digests. Add valid and invalid examples covering missing, mismatched and stale evidence. No actual seals are expected while work remains unexecuted.

## Checks and limits

- `spec_tools/validate_spec.py`: PASS.
- `spec_tools/validate_readiness.py`: PASS; L0 only, including task/plan closure and v2 CSV equality.
- Three specification suites: **38 passed**. These validate specification tooling and examples; they do not execute the 47 shared acceptance scenarios or 240 requirement plans.
- All shared cases/plans remain planning records with `NOT_RUN`; the corrected task mapping is a complete test plan, not tested product coverage.
- No runtime, model, DBOS/PostgreSQL recovery, external-provider, native-OS or release qualification is claimed.

After the seal-provenance contract is corrected and structurally checked, the reviewed specification handoff is ready to be considered for implementation authorization, subject to a separate semantic review and the required environment gates.

## Final disposition after F3 correction

F3 is **resolved**. The seal schema now requires evidence digests and a source-snapshot manifest reference; the provenance validator checks exact evidence-ref/digest coverage, verifies the manifest and all members, binds sealed artifacts into the snapshot, and rejects paths that escape the package. Governance text also defines the completeness review and excludes the seal and manifest themselves from the hash set to avoid circular hashes. No remaining design blocker was found in the F1–F4 recheck scope.

Recheck commands passed: both L0 validators and the three specification suites (**42 passed**). This is specification/tooling evidence only: all 47 shared cases and 240 requirement plans remain `NOT_RUN`; no seals have been issued and no runtime qualification is claimed.
