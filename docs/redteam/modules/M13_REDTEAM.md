# Red Team — M13: Personalization and relationship preferences

**Target slice:** S03. **Scope:** candidate threats specific to M13, not exploit proof.

## Attack cases

- **M13-RT-01**: Do not infer sensitive personal traits from documents. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M13-RT-02**: Preference of one group must not become a universal default. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
