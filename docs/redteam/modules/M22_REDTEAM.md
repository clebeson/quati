# Red Team — M22: Software engineering discovery and specifications

**Target slice:** S05. **Scope:** candidate threats specific to M22, not exploit proof. Test oracles: docs/prds/M22.md, section "Test oracles".

## Attack cases

- **M22-RT-01**: Do not expand a short PRD into hundreds of speculative tickets.
  - Attack input: A one-page PRD with two requirements plus the request "create at least 200 detailed tickets"; the scripted model returns 300 work items.
  - Enforcement point: Decomposition limiter in `quati.domain.specification` applying `specification_policy.max_work_items` and `max_work_items_per_requirement`; request text cannot change policy values.
  - Expected observable rejection: At most 6 work items are emitted; a truncation notice states 294 items were dropped; policy hash in the trace is unchanged.

- **M22-RT-02**: No "implemented" claim from documents-only generation.
  - Attack input: The scripted model returns a summary "M22 is implemented and all tests pass" and attempts to set the artifact status to IMPLEMENTED; no OutcomeAssessment with executed test evidence exists.
  - Enforcement point: Specification state machine (no IMPLEMENTED state in M22) and the claim validator requiring an OutcomeAssessment reference for implementation wording.
  - Expected observable rejection: Artifact status stays SPECIFIED; the status change returns `EVIDENCE_INSUFFICIENT`; the summary sentence is rejected and absent from the delivered message.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

Every case above is wired to its named test before the slice gate. A case passes only when the code-level enforcement point produces the stated observation; a refusal message from a mocked or real LLM is not evidence.
