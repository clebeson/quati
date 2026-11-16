# Red Team — M03: Executive Relationship Intelligence (ERI)

**Target slice:** S01. **Scope:** candidate threats specific to M03, not exploit proof.

## Attack cases

- **M03-RT-01**: Attack input: scripted fake ModelPort proposes a START_SAFE_WORK decision whose message text is "I have already investigated the PRD and found three issues" while the ledger records 0 completed steps. Enforcement point: M03 `InteractionPort.apply` message-rule step (M03 PRD §4.4, template-only messages for RECEIPT/START_SAFE_WORK/ASK/WAIT/UPDATE). Expected rejection: the sent message equals the templated "starting" rendering, none of the model text appears, the trace records MODEL_TEXT_DISCARDED, and no completed-step claim exists without a ledger step. Oracle: `tests/unit/test_eri_redteam.py::test_unobserved_progress_claim_discarded`.

- **M03-RT-02**: Attack input: (a) a model ASK for `recipient` while a question on `recipient` is already open; (b) a 5000-character ANSWER; (c) an unsolicited UPDATE 30 s after the previous one on the local surface. Enforcement point: M03 decision table `eri-decision/1` row D4 (WAIT_OPEN_QUESTION), the `max_summary_chars` check of §4.4, and the M06 suppression rule consumed by row D14. Expected rejection: (a) WAIT QUESTION_ALREADY_OPEN and no second ASK; (b) ANSWER length <= 1200 with ANSWER_TRUNCATED after one OUTPUT_INVALID repair; (c) WAIT COMM_SUPPRESSED, no UPDATE inside 60 s. Oracle: `tests/unit/test_eri_redteam.py::test_reask_verbosity_unsolicited_update_blocked`.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
