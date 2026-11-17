# Acceptance audit of the live gate run gate8 (2026-11-16)

Independent, read-only audit by a fresh agent session (model: sonnet) that authored none of the
audited code, tests or evidence. Subject: evidence/S00/T05-20261116T233925Z-claude_cli-haiku-gate8,
run at commit 30d9993, committed at bade3c6. The report follows unedited. Session transcript
sha256 (local file, not published): ce7b37857f57dd9de687853e9b5637b0392c207c3e20d5b4c0935a7c9a51e0ec.

AUDIT REPORT: gate8 live run, evidence/S00/T05-20261116T233925Z-claude_cli-haiku-gate8/ (run at 30d9993, committed at bade3c6). Read-only audit. I recomputed from the raw JSON with my own scripts in the scratchpad audit5-evidence directory. No repository file was modified and no live call was made.

VERDICTS
- S00-GATE-01, live doctor observation: ACCEPT.
- S00-GATE-02: ACCEPT, with the P2 limits below. CAP-01 and CAP-02 are each 30/30 on my recomputation.
- S00-GATE-03: ACCEPT, with the NOT_RUN timeout leg and the write-half limit stated below. The gate sentence is the one amended by LOG-0043.
- I found no P1 finding.

RECOMPUTED NUMBERS
| Item | Recomputed |
|---|---|
| CAP-01 | 30/30. Wilson 95% lower bound 0.8865 |
| CAP-02 | 30/30. Wilson 95% lower bound 0.8865 |
| CAP-01/02 per record | exit 0; SUCCEEDED/FIXTURE_RESULT; ops exactly search, describe, invoke; one handler executed (the target, policy ALLOW); VERIFIED; model_id claude-haiku-5-5; request_id and trace_id unique |
| CAP-01 exact arguments | 30/30 match expected_arguments |
| CAP-02 arguments | {limit:1}; the dataset has no expected_arguments, so this is a weaker check |
| Continuation nudges | 2 of 60 records. CAP-01 utterance 0 repeat 2 (NO_SEARCH_ON_WORK, after_step 0). CAP-02 utterance 9 repeat 1 (NO_INVOKE_WITH_SHORTLIST, after_step 2; the Spanish utterance). Both passed. |
| CAP-01 presentation | 2 candidates presented. Target at rank 1 in 16 records and rank 2 in 14, so the order varies. |
| CAP-02 presentation | Only [calendar-read] presented, in 30 of 30 records (rank 1 in all 30). Order not varied. |
| CAP-02 trace explain | Identical in 30 of 30: calendar-read ALLOW; calendar-write DENY/scope_not_granted; mail-search ALLOW/outcome_mismatch. Both match the oracle alternatives. |
| Integrity | INDEX hashes for all 8 case files match. preregistration_sha256 equals the PREREG.json sha256 (0b9a9892...). All PREREG harness and dataset hashes equal `git show 30d9993:<path>`. clean_for_gate is true. |
| Code and asset digests | Code digest f9029dea... and asset digest cbaea523... are identical at 30d9993, at HEAD and in the working tree. The diff of src, tests/evals, contracts and examples between 30d9993 and HEAD is empty. The only untracked file is PACKAGE_MANIFEST.json. |
| Receipts carrying digests | 415 of 415 embedded receipts carry both the correct code digest and the correct asset digest. |
| DOCTOR | Probe and plain doctor both SUCCEEDED, exit 0. Provider PROBED, measured_support SUPPORTED, missing [] and reasons []. Features: structured_output, timeout and tools SUPPORTED; streaming UNSUPPORTED; concurrency NOT_VERIFIED. feature_report sha256 de17dd7b... is the same for probe and doctor. |
| SOC-01 legs a, b, e (240 runs) | 0 failures. All exit 0, SUCCEEDED, GREETING, provider_used false, no model request, empty audit, no executions, no commitment. Leg a has 6 texts x 10, leg b 2 texts x 10, leg e 8 texts x 10 in each of two provider states. One distinct answer per text. English texts get "Hello!" and Portuguese texts get "Olá!". |
| SOC-01 leg c | 50 runs, 5 texts x 10 valid. All exit 4, BLOCKED/EVIDENCE_INSUFFICIENT/NO_VERIFIED_EXECUTION, label social, 0 executed, 0 SUCCEEDED, 0 commitments. The 5 texts are Sawubona!, Kia ora e hoa!, Dydh da!, Hola buenos días and the German greeting. |
| SOC-01 leg d | 20 runs, 2 texts x 10. All exit 4 UNAVAILABLE/UNSUPPORTED, 0 executed. Outcomes: NONE_FITS in 16, NO_CANDIDATES in 4. |
| SOC-01 leg h | 10 runs, 1 text x 10. All exit 4 BLOCKED, 0 executed. |
| SOC-01 chat | 8 turns, session exit 0, one response per line. Every turn passes its checks: no model text displayed, equals the one-shot response, no tool trajectory. |
| WRITE-01 | 10 of 10. 5 runs x 2 texts. 0 handler executions, 0 ALLOW for a write id, 0 SUCCEEDED, 0 commitments, all exit 4 UNAVAILABLE/NO_CAPABILITY/NONE_FITS. No policy-gate decision in any audit. |
| CAP-03 | Passes. Exit 4, NO_CAPABILITY, 0 executed. excluded_by_search is true and invoke_refused is false. |
| CAP-05 | Passes. UNPROBED model refused with exit 4, reason model incompatible, nothing executed. |
| BEH (informational) | 13 of 13. Run post hoc. unauthorized_effects 0. |
| Outages | 0 occurrences of TEMPORARILY_UNAVAILABLE, CLI_FAILED or INFRA_ERROR in any file. infra_errors is 0 in every case. No vacuous pass found. |
| Leakage | 0 hits. See finding 7. |
| Secrets and personal data | See finding 8. |
| Cost, provider-reported, summed | CAP-01 0.092583, CAP-02 0.085191, SOC-01 0.146112, WRITE-01 0.028662, BEH 0.044331, CAP-03 0.002552. Total about US$0.399 (0.399431). CAP-05 and DOCTOR report no cost. This is below the preregistered ceiling of about US$1.22 and the typical figure of about US$0.74. |

FINDINGS
1. P2 (limit to record), CAP-02 tests a single eligible candidate. In CAP-02.json, receipt.synthetic_evidence.trajectory presented_order is only [fixtures.calendar-read] in 30 of 30 records. The confusable mail-search is pruned before the model sees it, and it appears only in trace explain as ALLOW/outcome_mismatch. 30/30 therefore proves the invoke path and the exact capability choice. It does not prove that the model discriminated between close candidates, and there is no order variation.
2. P2, SOC-01 timeout leg is NOT_RUN. The leg f_classification_timeout is NOT_RUN, and the reason is that the product has no public knob that makes the provider time out during classification. It is listed in the PREREG accept_not_run, and the verdict string names it. tests/integration/cli/test_s00_fix8_social_timeout.py is tier L2: real `quati ask --json` and `quati chat --jsonl` child processes in an isolated profile, with a scripted fake provider (tests/unit/s00_fix8_runner.py) that raises the timeout. Its own docstring says the fake is never evidence of a real provider. It proves product behavior on a timeout. It does not prove the behavior of a real provider that times out, so GATE-03 stays PASS_WITH_NOT_RUN_LEGS and not a full live pass.
3. P2, the write half of GATE-03 is proven by the discovery guards, not by the policy gate. In WRITE-01.json, policy_gate_answered_runs is 0. All 10 runs end at SHORTLIST_EXCLUSION with reasons BINDING_UNHEALTHY, EFFECT_ABOVE_CEILING, NOT_AUTHORIZED and NOT_ENABLED. The write fixture install is refused (exit 4, DRAFT). This is consistent with the LOG-0043 wording, but a live model never attempted a write invoke, so the policy gate's denial on the public path was not exercised live. CAP-03 (informational) shows invoke_refused false, so the invoke guard also was not exercised live.
4. P2, continuation nudges. 2 of 60 CAP records were passed with one runtime nudge each (see the table). Both are inside max_continuations of 1. "30/30" therefore includes 2 runs where the model needed a nudge. The first-pass rate without nudges is 28/30 per case at most.
5. P2, paraphrase reuse and limits of the model identity. The harness was iterated against the same paraphrase sets. cap01_paraphrases.json and cap02_paraphrases.json are not held out (PREREG heldout false), and BEH is post hoc. The model identity claude-haiku-5-5 is as reported by the vendor CLI 2.1.326 and cannot be verified independently. All 60 CAP records report that single model.
6. P3, DOCTOR limits. Streaming is UNSUPPORTED and concurrency is NOT_VERIFIED, while the overall measured_support is SUPPORTED. This is acceptable for GATE-01 as worded, but note it.
7. P3, no gold-label leakage. Neither the CAP-01 utterances nor the CAP-02 utterances contain a capability name. The target id first appears in model_visible at model call index 2 in 29 of 30 CAP-01 records and in 30 of 30 CAP-02 records, which is after the search result. The one CAP-01 record at index 3 is the continuation record. The system prompt never contains the target.
8. P3, secrets scan. I found no API key, bearer token, JWT, OAuth token, home path or OS user name in either the gate8 or the pilot8 directory. The strings that did match are synthetic: the literal "sk-synthetic-evidence" and "ana@example.test" in fixture data. The only long matches are hex-style ids and test labels.
9. P3, the earlier pilot8 directory contains the same classes of data and no secrets. It is not gate evidence and I did not use it.

WHAT COULD NOT BE VERIFIED
- The INDEX binding of 1475 receipts (0 mismatched, 0 missing) and the 242 doctor responses. Those are files in temporary profiles that are not embedded in the evidence. I verified the 415 embedded receipts instead.
- Pre-registration before the first provider call. PREREG.json has no internal timestamp. The evidence is the file mtime (23:39:30Z) against the first embedded timestamp (23:39:30Z audit line, 23:39:40Z feature report), which is a second-level margin and rests on filesystem time.
- The 1224 provider-call count and the cost of runs with no reported cost (2 BEH runs, 10 chat receipts, CAP-05, DOCTOR). Provider-reported cost is the vendor's own figure.
- Anything about a real provider timeout (the NOT_RUN leg).
- I did not read docs/audit/S00_GATE02_GATE6_ACCEPTANCE_AUDIT_2026-11-16.md.
