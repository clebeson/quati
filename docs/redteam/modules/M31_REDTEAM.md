# Red Team — M31: Context engineering and model competence calibration

**Target slice:** S00. **Scope:** candidate threats specific to M31, not exploit proof.

## Attack cases

- **M31-RT-01**: Huge context window is not evidence of better reasoning. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M31-RT-02**: Prompt truncation must not discard security or ownership facts. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
