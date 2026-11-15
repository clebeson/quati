# SECMA v8 comprehensive compliance audit

Date: 2026-11-15. Authority: attached SECMA v8 archive, whose SHA-256 and complete 172-file inventory are recorded in `evidence/audit/baseline/source_inventory.json`.

## Executive verdict

The original package is a design, not a working SECMA system. Its modular monolith, SCS outcome contracts, replaceable adapters, CLI-only delivery and protected kernel remain the intended architecture. Original baseline tests pass but do not justify runtime, live intelligence, durability or release claims. Correct semantic contract and traceability defects before implementing the bounded S00 prototype. No GUI, new broker, extra orchestrator or module-per-service decomposition is justified.

S00 must remain BLOCKED until an authorized real tool-capable model proves blind capability discovery. S01–S07 cannot be executed around this gate. Missing provider access is an actual dependency, not permission to simulate successful evidence.

## Audit scope and independent work

- Architecture review: PRDs M01–M31, product, RFCs 001–012, ADRs 001–012, diagrams, TRD, roadmap and slice instructions; consolidated source equivalence.
- Contract/test review: all 14 JSON schemas, examples, compiler/validator, seed cases, holdout policy, test/risk ledgers and all threat sheets.
- Traceability review: all explicit FR/AT/RT IDs, K1–K10 and shared normative obligations, with phase, contract, scenario and proof-tier mapping.
- Dependency review: official sources for architecture-critical model/runtime/protocol boundaries; remaining optional adapter references are inventoried as unqualified. Future implementation must qualify exact versions and licenses. Public documentation does not imply installed services or credentials.
- Execution baseline: 14 reference tests passed after installing test dependencies. Original L0 validator passed. Both are L0 only. Initial missing pytest was an environment prerequisite, recorded separately.

Review reports preserve their original findings before correction. A reviewer who later fixes a finding does not independently certify that fix; parent integration review and regression tests provide a separate review step. No external penetration test, OS matrix or live provider result is implied.

## Significant findings and disposition

| Boundary | Original deficiency | Required correction / remaining proof |
|---|---|---|
| State contracts | Commitment and interaction vocabularies disagree between schema, RFC and reference chart. | Reconcile wire vocabulary; separate result verdict and delivery lifecycle. Runtime transactional transitions remain S02. |
| Protected transitions | Allowed guard/action names can be recombined to skip evidence and authorization. | Reject invalid protected edge tuples; runtime policy still owns authorization. |
| Cancellation/recovery | Example graph lacks complete uncertain-effect cancellation and timeout recovery. | Quarantine as non-release reference; require S02 recovery model and fault proofs before activation. |
| SCS schema | Malformed nested schemas pass outer validation; assurance claims look executable. | Validate nested schemas and references; separate trusted fixture binding/assurance from manifest metadata. |
| Behavior compiler | Meaningful options ignored, override language unspecified, receipt lacks trusted input identities. | Compile effective options, constrain budgets, extend receipts, reject ambiguous YAML and escaping paths. |
| Traceability | FRs mechanically mapped to AT-01/RT-01; threats and shared invariants absent. | Complete matrix; planned tests explicitly separate from executable tests and evidence. |
| Phase scope | First module contribution confused with full module completion; prototype conflicts with durable promise. | S00/S01 transient prototype receipts; no durable acceptance until S02; preserve full requirement gates. |
| Provider compatibility | Endpoint label conflated with observed support; pricing/residency not probeable in full. | Unknown by default; actual nonce tool probe and role-specific live evaluation; attested metadata separate. |
| Evidence | Public seeds and static validators could be overread as intelligence evidence. | Retain proof tiers, independent holdouts, explicit BLOCKED and NOT_VERIFIED_EXTERNAL. |
| Inventory | Missing deployment RFC claimed; aggregate duplicates canonical sources. | Correct inventory and regenerate aggregate reproducibly. |

Detailed finding IDs, reproductions, rationale and affected files are in `ARCHITECTURE_REVIEW.md`, `CONTRACT_TEST_REVIEW.md`, `TRACEABILITY_REVIEW.md` and their correction logs. Remaining product risks stay open in `docs/redteam/OPEN_RISKS.md`; design corrections alone cannot close them.

## Implementation readiness and roadmap

Use `docs/implementation/ROADMAP.md` and `S00_RUNTIME_CONTRACT.md`. S00 implements public CLI, explicit local identity, preventive read-only fixture policy, governed compilation, SCS discovery and bounded Pydantic AI adapter. No durable work is accepted. Tests begin red, then real code is implemented, then evidence is recorded. Subsequent slices require the preceding gate to PASS at the required tier.

The final checkpoint must report exact tests and commit, per-gate status, resource observations and missing evidence. Unknown costs are null, not zero. No external writes, production access, publishing or deployment are authorized by this audit.
