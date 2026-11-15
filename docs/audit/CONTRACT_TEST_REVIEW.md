# Independent contract and test review — original SECMA v8

Date: 2026-11-15. Scope: all 14 contracts, reference compiler and validator, 14 reference tests, all example files, testing documents and ledger, seed evaluation and holdout policy, all 31 module threat sheets and global risk documents, requirements and risk CSVs. This is independent static review and targeted local reproduction, not penetration testing or live-model evidence. Corrections below are recommendations at this review snapshot.

## Verdict

NO-GO for runtime/completion claims. GO for correcting specifications and then implementing the bounded S00 candidate. The package honestly discloses that its runtime is absent. Its structural checks pass but leave material semantic gaps. They cannot serve as promotion gates without stronger validation.

## Executed baseline

- `python spec_tools/validate_spec.py`: exit 0, L0 PASS.
- `python -m pytest tests/test_reference_compiler.py -q`: exit 1, pytest not installed in the initial interpreter. `/usr/bin/python3` also lacks pytest. This is an environment prerequisite, not evidence of a failing product test.
- Direct Python reproductions using the real reference compiler: malformed embedded input schema accepted; premature delivery edge accepted; changing clarification style does not change rendered prompt. No provider or credential used.

## Findings

| ID | Severity | Concrete evidence and consequence | Required correction / proof |
|---|---|---|---|
| CT-01 | P1 | `commitment.schema.json` admits UNDERSTANDING/ACCEPTED/EXECUTING/REVIEWING/COMPLETED/PARTIAL/FAILED, whereas `examples/statecharts/commitment.yaml` uses CLASSIFIED/ACKNOWLEDGED/IN_PROGRESS/EVIDENCE_REVIEW/READY_TO_DELIVER/DELIVERED. Persisting actual reference states fails the published contract. | Pick canonical machine vocabulary, keep result verdict separate from delivery state, add schema-machine consistency test. |
| CT-02 | P1 | `scs-capability.schema.json` constrains input/output schemas only to object. Setting input_schema to `{"type":"not-a-type"}` is accepted by `validate_schema`. | Validate nested schemas with Draft202012 and constrain external reference resolution. Test invalid types/references and actual input/output instances. |
| CT-03 | P0 design risk | `validate_machine` validates name allowlists and topology but no invariant-bearing edge semantics. RECEIVED → DELIVERED with authorized_request is accepted when remaining states remain reachable. Registered `always` and delivery actions can be recombined. | Protected semantics for acceptance/evidence/delivery and immutable runtime guards; reject bypass graph. Static validation alone must not claim authorization. |
| CT-04 | P1 | `validate_behavior` ignores clarification_style, language_policy, max_investigation_loops, safe_read_ahead, specialist_role and max_capability_candidates in effective prompt. Changing clarification_style leaves prompt identical. Incident profile says 3 investigation loops while referenced chart budget is 2. | Compile effective options or explicitly designate runtime-owned fields, enforce coherent budgets, test each meaningful mutation. |
| CT-05 | P1 | `explicit_override` language mode has no language field. It is impossible to encode the selected override. | Add conditional required language tag; default requester policy remains multilingual. |
| CT-06 | P1 | Prompt receipt lacks compiler version, trusted policy identity/hash, source identities and effective runtime limits. Hashing the behavior alone does not identify the complete policy/compiler input. | Version receipt and include trusted inputs; regenerate reference output and test deterministic change detection. |
| CT-07 | P1 | `yaml.safe_load` silently accepts duplicate mapping keys, allowing reviewed and effective configuration to differ. Arbitrary state/event strings can alter Mermaid output. | Reject duplicate keys and constrain DSL identifiers; test traversal/symlink containment before reading and malicious identifiers. |
| CT-08 | P1 | `validate_schema` does not enable format checking, so date-time annotations do not reject invalid timestamps. Several assurance/hash fields allow empty strings; competence EVALUATED with zero samples is schema-valid. | Enforce timestamp formats and appropriate identity/hash constraints. Distinguish static shapes from evidence-backed assurance promotion. |
| CT-09 | P1 | Outcome ACCEPT may have zero evidence and nonempty gaps; binding enabled may be UNVERIFIED. No schema can prove claimed evidence exists or matches binding/config. | Add structural consistency constraints where universal; require runtime evidence registry and trusted activation gate. No self-declared assurance grants execution. |
| CT-10 | P1 | All 93 FR rows map mechanically to their module AT-01 and RT-01. For example M30-FR-02 unsafe-machine validation maps to hash-change AT-01 rather than AT-02. CSV lacks contract, code, executable test, proof tier and evidence links. | Repair semantic mapping and explicitly represent NOT_IMPLEMENTED/NOT_RUN. Planned cases are not executed coverage. |
| CT-11 | P1 | L0 validator only checks section names, file counts, schema syntax, two profile/machine examples and one capability. It ignores classifications, receipt validation, reference integrity, ledger IDs and links. | Validate all available structured examples and cross-reference IDs; assert expected inventory and duplicated IDs. |
| CT-12 | P2 | Benchmark family distribution is proposed, not realized: seed has 4 social, 6 simple, 8 deep, 15 professional, 6 status, 7 context and 4 external utterances; no actual multi-turn episodes. Fifty rows alone cannot prove concurrent or asynchronous behavior. | Label public seeds as single-turn development data and add phase-specific episodes plus genuinely sealed holdout after candidate. |
| CT-13 | P1 | Test ledger has 46 planned cases, all NOT_RUN; only 14 executable reference tests exist. Most threat rows repeat generic assertions, with no concrete executor/fixture mapping. | Build discriminating shared boundary suites incrementally; attach exact public-path tests and raw run evidence. Do not create one duplicate test per PRD. |

## Coverage assessment

The requirements file contains 155 rows: 93 normative FRs and 62 acceptance statements. The risk register contains module threat scenarios, not implementation evidence. Presence of IDs is structural traceability only. No L1–L5 behavior is demonstrated by this original package. Existing reference tests address unreachable states, unregistered actions/guards, duplicate transitions, deterministic hashing, policy reference allowlist, unknown profile keys, write approval metadata, draft enablement, terminal outgoing edges and missing statechart files. Missing discriminating L0 negatives include duplicate YAML keys, nested schema validity, timestamp formats, protected-edge bypass, ignored options, source versions and schema/machine consistency.

## Independence and limits

The review did not use the implementation to choose baseline threat expectations. Subsequent fixes authored by this reviewer require another agent to review them; this report does not independently certify its own later fixes. Real LLM selection, policy runtime, tenant isolation, immutable audit storage, durable recovery, external provider interoperability, resource limits and native OS operation remain unverified. Missing credentials should block the applicable S00 live gate without turning offline proofs into simulated L3 success.
