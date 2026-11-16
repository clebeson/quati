# RFC-008 — Assurance, Model Evaluation and Governed Self-Improvement

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

A capability or prompt candidate may be improved by an agent but may only be **promoted** by a trusted registry pipeline. Candidate generation reads traces and failure clusters, proposes instructions/profile/statechart changes, compiles them, runs deterministic tests and independent LLM evaluation, compares against baseline and sealed holdouts, and requests review for higher-risk modifications. No candidate can modify kernel permissions or redefine evidence thresholds through its own instructions.

Separate measurements: syntax validity, contract behavior, autonomous selection accuracy, real outcome sufficiency, context recovery, timing, safety refusal, cost/latency and external interoperability. Prefer fewer discriminating tests over thousands of shallow schema assertions. Gold labels do not appear in model-visible prompts or tool registry metadata. Judge disagreement must be surfaced rather than averaged to a false certainty.

## Judge rules (v8.1)

1. **Deterministic checks come first.** Chosen capability id, argument schema validity, effects attempted, evidence resolution and state transitions are all checked by code. A model judge is used only for the properties code cannot decide, such as relevance or the honesty of a narrative.
2. **Independent judge.** The judge or grader model is different from the model under test. It is pinned by exact model id, and its prompt, rubric and scenario set are versioned and recorded by digest.
3. **What a judge cannot do.** A judge score can never override a failed deterministic check or a zero-tolerance safety property.
4. **Reporting and expiry.** Results are reported with N, the pass count and the Wilson 95% lower bound, following the TEST_EXECUTION_PROTOCOL statistics note. A change to any recorded digest expires the result.

## Context-layer changes (2026-11-15)
Prompt, instruction, routing and memory-layer changes (including the offline memory consolidator,
RFC-005 v8.2) follow the same candidate → deterministic checks → sealed evaluation → approved promotion
→ instant rollback path. A consolidation *run* is data and is gated by RFC-005 v8.2 rule 7; a change to
the consolidator's prompt or model is a behavior change gated here.
