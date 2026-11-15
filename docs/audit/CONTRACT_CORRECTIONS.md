# Contract/compiler corrections and handoff

Date: 2026-11-15. Based on independent findings in CONTRACT_TEST_REVIEW.md. The author of these corrections does not claim independent certification of the fixes. A parent reviewer identified a Cartesian-product semantic bypass in the first correction; two additional regression cases and exact tuple matching address that reproduced defect.

## Applied corrections

- CT-01: commitment state enum matches reference machine. Result verdict remains separate from execution/delivery state.
- CT-02: embedded capability input/output schemas undergo Draft202012 schema checking; nonlocal `$ref`/`$dynamicRef` is rejected before network resolution. Runtime still must validate actual arguments and results.
- CT-03: protected incoming acceptance, classification, review and delivery edges use exact source/guard/action tuples. Receipt and delivery actions cannot be moved to arbitrary targets. These static checks do not execute guards or prove runtime authorization. They cover the reference vocabulary, not arbitrary user-defined executable machines.
- CT-04: compiler now represents clarification, safe reading, specialist role and effective candidate/context/investigation/transition budgets in prompt. Effective investigation budget cannot exceed the machine budget. Incident example lowered from 3 to 2 loops to match its shared machine.
- CT-05: explicit language policy requires a language tag; requester policy rejects irrelevant override fields. The English artifact requirement does not restrict product reply language.
- CT-06: receipt includes compiler version 1.1.0, protected policy identity/hash, behavior/statechart source versions and effective limits. Reference receipt and preview regenerated.
- CT-07: YAML duplicate and nonstring keys rejected; state/event/action/guard identifiers constrained to a data-only identifier grammar; statechart containment checked before file access. Free-form role text is not a security boundary and is not screened as if keyword rejection proved safety.
- CT-08: date-time validation enabled with an explicit checker independent of optional jsonschema format packages. Model competence identity/hash fields strengthened and EVALUATED requires positive samples, measured fields and feature fields. Claimed measurements still require authentic runtime evidence.
- CT-09: ACCEPT outcome requires evidence references and no unresolved gaps. Trusted runtime activation/assurance remains required; schema validity cannot enable a binding.
- CT-11: validator checks classification examples, receipt schema/freshness, preview freshness, commitment state agreement, unique requirement/risk/test/eval identifiers, requirement source references and slice existence. This is structural validation, not proof every requirement has sufficient acceptance coverage.
- RFC consistency: SCS lifecycle now includes `validated`; assurance includes `C0`, as required by RFC-001. Enabled still requires C2 or stronger.

## Reproduced tests

1. `evidence/audit/ct_regressions_red.txt`: initial discriminating regressions against original code.
2. `evidence/audit/ct_regressions_green.txt`: first correction run, **1 failure / 28 pass**, retained honestly. Missing optional date-time format support required explicit checking.
3. `evidence/audit/ct_regressions_green_2.txt`: 29 pass after timestamp fix.
4. `evidence/audit/ct_semantic_review_red.txt`: reviewer-proposed bypass regression run before tuple fix.
5. `evidence/audit/ct_semantic_review_green.txt`: **31 pass**, after exact tuple fix.
6. `../.venv/bin/python spec_tools/validate_spec.py`: L0 PASS after reference regeneration.

Rerun with `../.venv/bin/python -m pytest tests/test_reference_compiler.py tests/test_audit_regressions.py -q`. A third-party pytest plugin reports a deprecation warning; no tests were skipped in this suite. These are L0 tests, including static adversarial negatives. No model, external account, DBOS or application runtime is exercised.

## Explicit unresolved limits

- Reference commitment statechart remains a prototype. Its cancellation, timed waits, delivery-failure resumption and post-effect reconciliation require S02 design and real DBOS/Postgres tests before effect-bearing activation. Do not run the reference chart as a production worker state machine.
- No statechart DSL can itself prove authorization, source authentication or evidence authenticity. The application must enforce these separately, including expected machine role and trusted promotion.
- JSON Schema nested local reference existence and instance behavior are checked when validating actual inputs/outputs; a self-contained schema can still use recursion. Runtime validation needs bounded inputs and resource policy.
- Competence and assurance values remain claims until linked to trusted evidence. Positive sample count is not adequate statistical calibration.
- Scope/traceability corrections are owned by the primary auditor. This compiler change does not make all 93 requirements implemented.
- S00 live provider, blind selection and no-tool greeting gates remain dependent on authorized real model execution. No offline result advances those gates.
