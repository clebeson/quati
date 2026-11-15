# Red Team — M26: Audit, observability and evidence

**Target slice:** S00. **Scope:** candidate threats specific to M26, not exploit proof.

## Attack cases

- **M26-RT-01**: Do not claim fully reproducible model outputs without matching provider snapshot. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M26-RT-02**: Audit logs must be access-controlled and retention bounded. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
