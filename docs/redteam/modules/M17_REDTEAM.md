# Red Team — M17: LLM providers, routing and competence profiles

**Target slice:** S00. **Scope:** candidate threats specific to M17, not exploit proof.

## Attack cases

- **M17-RT-01**: Provider compatibility label is not proof of supported functions. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M17-RT-02**: Codex sign-in is not an OpenAI API key. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
