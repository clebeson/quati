# Red Team — M18: Agent and harness adapters

**Target slice:** S04. **Scope:** candidate threats specific to M18, not exploit proof.

## Attack cases

- **M18-RT-01**: An agent does not inherit tenant-wide credentials. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M18-RT-02**: Unsupported resume cannot be silently emulated as successful. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
