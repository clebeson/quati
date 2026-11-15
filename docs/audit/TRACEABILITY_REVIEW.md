# Independent Traceability Review

Date: 2026-11-15. Scope: original v8 PRDs, product invariants, RFCs, governance rules, schemas, slices, test strategy, and requirement/test ledgers. This is a specification audit, not runtime certification.

## Findings recorded before corrections

| ID | Severity | Observation | Consequence | Correction |
|---|---|---|---|---|
| TRACE-01 | P1 | REQUIREMENTS.csv contains 93 functional and 62 acceptance rows, but none of the 62 module red-team obligations or 10 product invariants. | Security obligations disappear from completion tracking. | Add every FR/AT/RT/K to the full matrix. |
| TRACE-02 | P1 | Every FR points mechanically to its module's AT-01 and RT-01. M07-FR-03 reconciliation belongs to AT-02; M30-FR-02 invalid-machine rejection belongs to AT-02. | Presence of a reference falsely implies semantic coverage. | Curate FR-to-AT links and add dedicated planned cases when existing ATs cover only part. |
| TRACE-03 | P1 | Neither requirement ledger includes code, exact executable test, contract, evidence, or proof-tier links. Test ledger describes 46 proposed scenarios without executable locators. | Cannot establish implementation/test coverage or resume gates from artifacts. | Separate planned scenario/locator from actual test/evidence status. All new mappings remain NOT_RUN until independently recorded. |
| TRACE-04 | P1 | Shared typed-input, output, adapter-independence, revision and authorization obligations in PRD section 4 lack IDs. RFC-specific invariants and process rules also lack ledger rows. | Passing three FRs does not satisfy a module's full normative content. | Assign shared derived obligations with source links and owner modules; retain original IDs unchanged. |
| TRACE-05 | P1 | A single S00 phase label is attached to complete multi-slice modules, including async delivery, persistence, promotion and adapters. | Passing the first narrow gate could falsely complete a whole PRD. | Separate first-slice contribution from full verification horizon; roadmap scope remains authoritative. |
| TRACE-06 | P2 | Several boundaries are prose contracts without schemas: approval/effect intent, identity context, preference, artifact version, registry lifecycle. | Implementers may invent incompatible shapes. | Matrix explicitly labels PROSE_ONLY and requires contract definition before the relevant implementation, rather than fabricating schema coverage. |

## Method and assurance limits

Each original module contributes exactly three FRs, two ATs and two RTs. The updated matrix preserves those texts and identifiers, adds K1–K10 and derived shared obligations, maps existing schemas only where relevant, and records a concrete scenario and planned test for each row. A planned locator is deliberately not an assertion that the file exists. Related test-ledger cases are pointers for reuse, not evidence that they fully satisfy a requirement.

The matrix is an audit baseline. Source or runtime changes require regeneration/reconciliation and actual test/evidence attribution. No module is marked implemented and no L3, L4 or L5 claim is inferred from this work. Source-file hashes record the snapshot used. Unidentified new requirements cannot be guaranteed absent from arbitrary future prose; maintain stable IDs during subsequent specification changes.
