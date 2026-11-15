# Red Team — M23: Incident investigation and root-cause analysis

**Target slice:** S05. **Scope:** candidate threats specific to M23, not exploit proof.

## Attack cases

- **M23-RT-01**: No production mutation without explicit gate. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M23-RT-02**: A failed telemetry source must remain visible as an evidence gap. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
