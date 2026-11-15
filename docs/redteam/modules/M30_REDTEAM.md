# Red Team — M30: Behavior package, prompt and statechart compiler

**Target slice:** S00. **Scope:** candidate threats specific to M30, not exploit proof.

## Attack cases

- **M30-RT-01**: A generated prompt cannot grant tool permission. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M30-RT-02**: An LLM-generated transition proposal cannot enter production without semantic checks. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
