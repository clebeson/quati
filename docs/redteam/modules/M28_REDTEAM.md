# Red Team — M28: Portability, operations and enterprise deployment

**Target slice:** S07. **Scope:** candidate threats specific to M28, not exploit proof.

## Attack cases

- **M28-RT-01**: Never bundle unlicensed third-party binaries. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M28-RT-02**: One laptop sleeping means no background execution without remote always-on worker. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
