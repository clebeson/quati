# Red Team — M15: Capability discovery, resolver and execution controller

**Target slice:** S00. **Scope:** candidate threats specific to M15, not exploit proof.

## Attack cases

- **M15-RT-01**: A hard-coded golden target is passed to the router during evaluation.
  - Attack input: an eval case whose utterance or system prompt contains the expected id `incident.triage`, and a variant where the runner pre-builds the shortlist from the case's `expected_capability_id` instead of calling `search`.
  - Enforcement point: the eval runner leak check (M15 Normative detail, "Eval leak check") over model-visible bytes, and the shortlist provenance check that accepts only a shortlist produced by `DiscoveryPort.search` in the same turn.
  - Expected observable rejection: case marked `INVALID_CASE` reason `GOLDEN_TARGET_LEAK` and counted as a failure; the shortlist variant is rejected with the same reason; the eval summary cannot report 30/30.

- **M15-RT-02**: A malformed tool call becomes an unvalidated side effect.
  - Attack input: `quati_invoke` with truncated JSON `{"capability_id":"x`, an unknown tool `quati_exec`, an id outside the shortlist, and `{"amount":"ten"}` against an integer schema.
  - Enforcement point: invoke guard steps 1–7 (M15 Normative detail) executed before `DurableRunner.enqueue` and `PolicyPort.evaluate`.
  - Expected observable rejection: `TOOL_CALL_MALFORMED`, `TOOL_CALL_MALFORMED`, `NOT_IN_SHORTLIST`, `ARGUMENTS_SCHEMA_INVALID`; zero EffectIntents, zero enqueues and zero binding calls.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
