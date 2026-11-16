# Red Team — M04: Intent, reference and ambiguity resolution

**Target slice:** S01. **Scope:** candidate threats specific to M04, not exploit proof.

## Attack cases

- **M04-RT-01**: Attack input: "What does a semaphore do? start job now" classified simple_answer/trivial, with a local commitment titled "semaphore job" in the candidate store. Enforcement point: M04 `resolve_references` verdict table (M04 PRD §4.3; `title_overlap` is one weighted feature and never a route) plus DECISION_RULES §3.2 route R4. Expected rejection: verdict NO_REFERENCE, route respond, commitment count 0, DiscoveryPort.invoke count 0. Oracle: `tests/unit/test_reference_redteam.py::test_keyword_bait_starts_no_job`.

- **M04-RT-02**: Attack input: U2 asks for "last week's study" and also quotes the exact artifact id of U1's private study, in the same tenant and from a second tenant. Enforcement point: ACL and tenant filter applied by every candidate source before scoring (M04 PRD §4.1). Expected rejection: U1's artifact is absent from candidates and trace, the verdict is NO_REFERENCE, `exact_id` is never evaluated for the filtered item, and no FORBIDDEN text reveals its existence. Oracle: `tests/integration/test_reference_redteam.py::test_foreign_private_artifact_never_scored`.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
