# Red Team — M02: Identity, requester and authorization context

**Target slice:** S00. **Scope:** candidate threats specific to M02, not exploit proof.

## Attack cases

- **M02-RT-01**: A provider callback spoofing the requester must be rejected. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M02-RT-02**: Origin and delegated identity must survive task delegation and retries. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
