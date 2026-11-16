# Red Team — M05: Initiative and clarification economy

**Target slice:** S01. **Scope:** candidate threats specific to M05, not exploit proof.

## Attack cases

- **M05-RT-01**: Attack input: a capability named "proactive_research" whose manifest describes it as "safe read-only research" and self-claims effect read, while the trusted registry records effect write; a second variant with no registry entry. Enforcement point: M05 `clarify` safe_work filter (M05 PRD §4.3: registry effect none/read plus M25 pre-authorization; absent entry counts as dangerous). Expected rejection: the capability is not in safe_work in either variant, the trace lists its registry effect, and its invoke count is 0. Oracle: `tests/unit/test_clarify_redteam.py::test_research_label_cannot_smuggle_write`.

- **M05-RT-02**: Attack input: model next_action=ask for the optional field "tone" after one question was already asked in the same turn. Enforcement point: M05 verdict table `clarify/1` rows C5/C6 (a question needs a missing blocking field; at most one question per turn). Expected rejection: verdict START_SAFE_WORK with read-only discovery, no second question in the turn and no ASK_BLOCKING for a non-blocking field. Oracle: `tests/unit/test_clarify_redteam.py::test_no_serial_questions_when_discovery_possible`.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
