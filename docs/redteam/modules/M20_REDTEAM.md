# Red Team — M20: Second-brain provider adapters

**Target slice:** S04. **Scope:** candidate threats specific to M20, not exploit proof.

## Attack cases

- **M20-RT-01**: Untrusted repository README cannot become privileged instruction. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M20-RT-02**: Stale source cannot be presented as current verified policy. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
