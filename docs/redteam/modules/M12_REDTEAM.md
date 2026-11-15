# Red Team — M12: Versioned artifacts and reproducible edits

**Target slice:** S03. **Scope:** candidate threats specific to M12, not exploit proof.

## Attack cases

- **M12-RT-01**: File paths from untrusted documents cannot escape authorized workspace. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

- **M12-RT-02**: Never silently replace original artifact when write approval is required. Inject via public CLI/provider boundary; assert authorization, state, evidence and user-facing honesty.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
