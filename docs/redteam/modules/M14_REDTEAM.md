# Red Team — M14: SCS capability manifest and registry

**Target slice:** S00. **Scope:** candidate threats specific to M14, not exploit proof.

## Attack cases

- **M14-RT-01**: Manifest cannot be auto-enabled merely because schema passes. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M14-RT-02**: A capability ID is not a skill, agent, prompt or tool name. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
