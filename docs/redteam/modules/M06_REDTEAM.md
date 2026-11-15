# Red Team — M06: Expectation and communication management

**Target slice:** S02. **Scope:** candidate threats specific to M06, not exploit proof.

## Attack cases

- **M06-RT-01**: Network failure must not be reported as successful delivery. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M06-RT-02**: A fixed timeout must not be misrepresented as estimated completion. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
