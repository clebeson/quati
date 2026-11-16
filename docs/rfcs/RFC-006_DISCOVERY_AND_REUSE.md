# RFC-006 — Professional Repository and External Knowledge Discovery

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

Discovery is a first-class **capability**, not a permanent hidden spider. It uses declared research policies and source permissions. It crawls authorized references transitively (PRD → ADR → RFC → code/docs) with cycle detection, rate limits, depth limits, time/expense budgets, and a coverage report showing visited, failed and out-of-scope sources. No arbitrary downloaded code is executed during discovery.

Outputs distinguish `explicit_standard` from `inferred_common_pattern`, `exception` and `conflict`. A proposed corporate PRD format derives from cited corpus evidence, not asserted familiarity. Reuse recommendations include license, version, maintenance activity, security posture, API compatibility and a note on what would require local validation. Search can be on-demand or scheduled only when authorized, observable and bounded.

## Amendment v8.1 — retrieval method for capability discovery (RFC-015 §7)

Capability search runs in this order:

1. **Hard filters**, applied by deterministic code. They cover authorization scope, effect ceiling, data class, health, model compatibility and cost cap. Every filter failure is recorded as a reason code.
2. **Lexical score.** SQLite FTS5 `bm25()` scores name, description and positive intents.
3. **Shortlist** of the top K, where K is `RoutingPolicy.max_shortlist_k`.
4. **Choice.** The LLM chooses among the shortlist or answers NONE_FITS.

The retriever sits behind `SearchPort`. Embeddings, hybrid retrieval and rerankers stay deferred until a measured recall@K failure on the capability eval set justifies them, and adding them needs an ADR. Repository and knowledge discovery (this RFC's main subject) uses the same port.
