# Red Team — M04: Intent, reference and ambiguity resolution

**Target slice:** S01. **Scope:** candidate threats specific to M04, not exploit proof.

## Attack cases

- **M04-RT-01**: Keyword-based false positives must not launch jobs. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M04-RT-02**: Reference resolution cannot leak another requester’s private artifacts. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
