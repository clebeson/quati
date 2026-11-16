# Live Model Competence Bench — Blind Routing and Communication

## Benchmark objective
Determine whether a specific provider/model/prompt/config can *autonomously* identify intent, discover a newly installed capability, choose valid tools, follow the state contract, communicate concisely and recognize insufficient evidence. Model/provider compatibility is not an intrinsic property of Quati's manifest.

## Protocol
1. Register 2–4 capabilities including at least two confusable domains; keep target identities in a sealed fixture file only.
2. Start the ordinary CLI with standard system profile and no injected test guidance, invoke real model with natural-language utterance that **does not contain capability IDs**.
3. Capture the real provider's tool calls, arguments, reasoning decision fields (not private chain-of-thought), returned tool results, control gate decisions, elapsed time, cost and final human delivery.
4. Repeat with synthetic distractors, disabled tools, wrong permission, unsupported tools, newly installed binding while conversation lives, and no-tool greeting.
5. Run multi-turn episodes where user adds constraints while executor works, user requests prior artifact a week later, and a second async job finishes first.
6. Have evaluators blinded to implementation path score outcome, correctness, unnecessary questions and communication timing. Compare against baseline (direct specialist CLI invocation and prior Quati profile) to ensure Quati adds value.

## Initial dataset distribution (proposed; not executed)
| Family | Seed count | Why it matters |
|---|---:|---|
| Social/no-work greetings | 6 | Detect needless jobs/tool calling |
| Simple answer/status | 6 | Avoid expensive deep flows |
| Professional PRD/discovery | 8 | Correct contextual research and clarification |
| Deep incident/causal | 8 | Mandatory evidence and uncertainty |
| Old-work reference/artifact edits | 6 | Correct memory and lineage |
| Similar/disabled/unsafe capability | 8 | Abstention and policy gate |
| Concurrent/asynchronous multi-turn | 8 | ERI responsibility and timing |
| **Total initial cases** | **50** | Multi-purpose, not 50 times every model |

Build an independent sealed holdout of at least 30 cases after initial seed development. Do not write holdout cases into model-visible skill catalogs. Provider/model class differences require representative comparative samples and only deeper repeated trials where variance is high.

## Objective scoring
- `intent_family_correct`, `needs_work_correct`, `capability_top1_correct`, `safe_abstention_correct`, `tool_args_valid`, `policy_allow_deny_correct`, `outcome_evidence_valid`, `false_completion`, `unnecessary_question`, `meaningful_update`, `correct_reference`, `correct_recipient`, `response_verbosity`, `time_to_receipt`, `time_to_meaningful_update`, `tokens`, `cost`.
- Distinguish offline “schema-perfect decision” from actual end-to-end completed outcome.
- For high-risk mistakes, zero tolerance in tested cases; for general routing, calibrate threshold with confidence interval and baseline. If a cheap model underperforms, restrict its role rather than weakening acceptance.

## Realness check
Evaluator asserts actual provider transport was invoked and observable tool-call trajectory was emitted; mocks/hardcoded routes cannot satisfy this. Distinguish unavailable credential (`BLOCKED`) from provider unsupported tools (`FAIL`) and test harness internal errors (`INCONCLUSIVE`).
