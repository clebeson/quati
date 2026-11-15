# Red Team — M29: Channel and inbound/outbound messaging

**Target slice:** S04. **Scope:** candidate threats specific to M29, not exploit proof.

## Attack cases

- **M29-RT-01**: Do not send to a guessed user or channel. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M29-RT-02**: Do not claim receipt when provider times out after possible send. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
