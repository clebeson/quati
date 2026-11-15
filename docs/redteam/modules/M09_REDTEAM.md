# Red Team — M09: Sufficiency, evidence and stopping judgment

**Target slice:** S02. **Scope:** candidate threats specific to M09, not exploit proof.

## Attack cases

- **M09-RT-01**: A model grading its own output alone is not valid proof. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M09-RT-02**: No infinite self-critique loop to satisfy an undefined standard. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
