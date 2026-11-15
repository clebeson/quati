# Red Team — M19: MCP and action gateway

**Target slice:** S04. **Scope:** candidate threats specific to M19, not exploit proof.

## Attack cases

- **M19-RT-01**: Prompt injection in tool description cannot override authorization. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M19-RT-02**: MCP token forwarded only to authorized destination and not leaked in logs. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
