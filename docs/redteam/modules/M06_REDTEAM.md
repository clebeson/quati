# Red Team — M06: Expectation and communication management

**Target slice:** S02. **Scope:** candidate threats specific to M06, not exploit proof.

## Attack cases

- **M06-RT-01**: Attack input: fake DeliveryPort returns TEMPORARILY_UNAVAILABLE (network failure) for a final_delivery message. Enforcement point: M06 timing rule (M06 PRD §4.3: `last_contact_at` and delivery wording change only on an M10 DELIVERED/acknowledged status) and the M07 transition guard into DELIVERED. Expected rejection: commitment stays READY_TO_DELIVER, `last_contact_at` unchanged, CLI status reads "not delivered", no "sent" wording in any rendered message. Oracle: `tests/integration/test_contact_redteam.py::test_network_failure_not_reported_delivered`.

- **M06-RT-02**: Attack input: S00 30 s budget and a TimerIntent fire_until, with fake model UPDATE text "done in 30 seconds". Enforcement point: `CommunicationPlan` has no ETA field (M06 PRD §4.1) and M03 template-only UPDATE rendering (M03 PRD §4.4). Expected rejection: the rendered message equals the COMM_NEXT_CONTACT template ("next update by <time>"), the model ETA text is absent and the trace records MODEL_TEXT_DISCARDED. Oracle: `tests/unit/test_contact_redteam.py::test_timeout_not_rendered_as_eta`.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
