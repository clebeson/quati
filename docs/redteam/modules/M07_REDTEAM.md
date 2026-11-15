# Red Team — M07: Commitment ledger and durable execution

**Target slice:** S02. **Scope:** candidate threats specific to M07, not exploit proof.

## Attack cases

- **M07-RT-01**: Do not infer enterprise HA from a single local worker. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M07-RT-02**: Large numbers of long-lived waiting workflows may consume RAM without enterprise suspension. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
