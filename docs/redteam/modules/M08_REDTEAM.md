# Red Team — M08: Triage, prioritization and task planning

**Target slice:** S03. **Scope:** candidate threats specific to M08, not exploit proof.

## Attack cases

- **M08-RT-01**: Attack input: fake ModelPort classification output adds `"model_role":"strong","privilege":"admin"`; variant with risk low for a capability whose registry effect is dangerous. Enforcement point: schema validation of `request-classification.schema.json` (`additionalProperties:false`) and the DECISION_RULES §3.1-§3.3 policy pass (effect class from the trusted registry, model role computed). Expected rejection: first variant yields the fail-closed classification CLASSIFICATION_INVALID_ESCALATE; second yields R2 escalate ROUTE_EFFECT_DANGEROUS; TriageMeta.model_role always equals the §3.3 result. Oracle: `tests/unit/test_triage_redteam.py::test_model_cannot_grant_own_privilege`.

- **M08-RT-02**: Attack input: model intent "quick_lookup" (synonym outside the vocabulary) and a proposed capability id "send_mail" absent from the registry (registry has `email.send`, effect write). Enforcement point: schema enum validation and the §3.1 rule that an absent registry entry counts as dangerous; route table R2 and default R0. Expected rejection: intent synonym yields CLASSIFICATION_INVALID_ESCALATE; unknown capability yields effect dangerous and R2 escalate; safe_work_allowed false; no tuple reaches respond or start_safe_work. Oracle: `tests/unit/test_triage_redteam.py::test_synonym_cannot_bypass_gates`.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
