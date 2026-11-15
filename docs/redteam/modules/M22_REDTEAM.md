# Red Team — M22: Software engineering discovery and specifications

**Target slice:** S05. **Scope:** candidate threats specific to M22, not exploit proof.

## Attack cases

- **M22-RT-01**: Do not expand a short PRD into hundreds of speculative tickets. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M22-RT-02**: No “implemented” claim from documents-only generation. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
