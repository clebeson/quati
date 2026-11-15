# Red Team — M27: Evaluation-driven improvement and self-evolution

**Target slice:** S06. **Scope:** candidate threats specific to M27, not exploit proof.

## Attack cases

- **M27-RT-01**: Never auto-promote permission increases. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M27-RT-02**: Self-judged improvement alone is insufficient evidence. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
