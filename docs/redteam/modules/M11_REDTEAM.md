# Red Team — M11: Episodic and semantic memory

**Target slice:** S03. **Scope:** candidate threats specific to M11, not exploit proof.

## Attack cases

- **M11-RT-01**: Embedding similarity must not override access control. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M11-RT-02**: Summaries cannot replace original artifact lineage. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
