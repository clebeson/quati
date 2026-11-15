# Red Team — M01: CLI, packaging and local lifecycle

**Target slice:** S00. **Scope:** candidate threats specific to M01, not exploit proof.

## Attack cases

- **M01-RT-01**: Closing an interactive terminal is not a substitute for stopping a long-running worker. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M01-RT-02**: Incorrect shell quoting, filesystem paths or unsupported OS must not corrupt config. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
