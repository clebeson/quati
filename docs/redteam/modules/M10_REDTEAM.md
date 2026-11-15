# Red Team — M10: Audience-aware delivery and artifact packaging

**Target slice:** S02. **Scope:** candidate threats specific to M10, not exploit proof.

## Attack cases

- **M10-RT-01**: Do not send sensitive results to wrong channel or group. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M10-RT-02**: Do not mark an outbound message delivered before provider acknowledgement. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
