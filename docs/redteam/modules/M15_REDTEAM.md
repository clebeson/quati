# Red Team — M15: Capability discovery, resolver and execution controller

**Target slice:** S00. **Scope:** candidate threats specific to M15, not exploit proof.

## Attack cases

- **M15-RT-01**: No hard-coded golden target passed to router in evaluation. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M15-RT-02**: A malformed tool call never becomes an unvalidated side effect. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
