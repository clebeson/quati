# SOTA review: memory, brains and knowledge (2026-11-15)

Scope: compare SECMA memory/brain design (RFC-005, RFC-013 s6-7, M11, M13, M20, `Episode` in TYPE_CATALOG, `contracts/brain-document.schema.json`, audit A-14/A-20) with 2025-2026 practice. MVP = single user, Linux, SQLite, slices S00-S02. Evidence came from web search excerpts, not full-paper reads; anything not confirmed is marked UNVERIFIED.

## 0. What SECMA has today (repo facts)

- RFC-005: scope-aware Episode/Commitment/Decision/Preference/Claim/SourceRef records, correction history, "retrieved prompts cannot override trusted instructions".
- RFC-013: PERSONAL/TEAM/ORGANIZATION/SHARED spaces; additive grants; admin cannot read content; **pre-filter by AuthorizedScope, then post-check**; `source_space_ids` provenance label on derived data.
- Episode has `observed_at`, `expires_at`, `supersedes_ref`, `entry_kind` FACT/INFERENCE/SUMMARY/PREFERENCE. MemoryHit has freshness CURRENT/STALE/EXPIRED.
- Audit A-14 (BLOCKER): no store, no search method, `as_of` undefined, Episode lacks requester/project/method/confidence. Suggested FTS-first plus `as_of` = "observed at or before T, with corrections known at T applied".
- `brain-document.schema.json` has `visibility` enum private/team/organization/public, which conflicts with RFC-013 space kinds (PERSONAL/TEAM/ORGANIZATION/SHARED) and has no space_id or content hash.

## 1. Agent memory systems

| System | What it does | Maturity | Source | Verdict |
|---|---|---|---|---|
| Zep / Graphiti | Temporal KG with episodic, semantic-entity and community layers. Bi-temporal: event timeline T and ingestion timeline T'. Edges carry valid_at/invalid_at; contradicted facts are invalidated, never deleted. Evaluated on DMR and LongMemEval; reported gains up to 18.5% relative (secondary source; absolute ~11 pts). | Paper Jan 2025; Apache-2.0 OSS; needs a graph DB | https://arxiv.org/abs/2501.13956 | **ADOPT the semantics, REJECT the engine.** Keep `observed_at` (transaction time) and add `valid_from`/`valid_to` on facts. `supersedes_ref` already approximates edge invalidation. A graph DB is over-engineering for MVP. |
| Mem0 / Mem0g | LLM extraction of natural-language memories with ADD/UPDATE/DELETE/NOOP-style consolidation (UNVERIFIED detail); Mem0g adds a graph. Claims +26% relative LLM-judge over OpenAI memory, ~91% lower p95 latency and >90% fewer tokens vs full context on LoCoMo (vendor paper). | Widely used; vendor-authored benchmark | https://arxiv.org/abs/2504.19413 | **CHANGE.** Borrow the write-time consolidation loop (extract, compare to neighbors, decide add/update/supersede/ignore). SECMA must make the decision a *proposal* validated by code, and never DELETE original evidence (M11-FR-03). Reject Mem0g for MVP. |
| Letta (MemGPT) | In-context editable "memory blocks" (core) plus embedding-backed archival store written only via explicit tool calls. Sleep-time agents consolidate in the background. | Production OSS; docs partly secondary here | https://www.letta.com/blog/agent-memory ; https://docs.letta.com/guides/agents/sleeptime (not opened) | **ADOPT concept.** A small bounded "core profile" (preferences, standing rules) injected every turn, plus searchable archive. This maps to M13 Preference plus RFC-012 context budget. Sleep-time consolidation = a scheduled DBOS workflow, post-MVP. |
| LangMem | Semantic / episodic / procedural taxonomy; hot-path memory tools vs background extraction manager; consolidation jobs. Docs not opened (secondary only). | Library, LangGraph-coupled | https://github.com/langchain-ai/langmem (UNVERIFIED details) | **KEEP/ADOPT taxonomy.** Map to `entry_kind`; add PROCEDURE only via the behavior compiler (agents may only propose, per AGENTS.md rule 5), never as free memory. |
| A-MEM | Zettelkasten-style linked notes that evolve. | Research paper (arXiv 2502.12110, UNVERIFIED) | not fetched | **REJECT** for MVP. Link-evolution rewrites old notes, which violates immutability of evidence. |
| Anthropic memory tool | Client-side, file-based `/memories` directory; Claude does view/create/str_replace/insert/delete/rename; host must block path traversal. Beta header. | Beta, official | https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool | **ADOPT as an adapter pattern, not the model.** Markdown files are a good human-inspectable view, but writes must pass SECMA's validator. Agent-authored files must not be a store of record. |
| OpenAI memory / Claude.ai memory | Product-level saved memories plus chat-history reference; user can view/delete. | Product, closed | UNVERIFIED (not fetched) | **KEEP** (SECMA already requires user-visible correction). Add a "what do you remember about X" view and delete-by-user in S02 CLI. |
| LoCoMo / LongMemEval | LongMemEval (ICLR 2025): 500 questions, five abilities: extraction, multi-session reasoning, temporal reasoning, **knowledge updates**, **abstention**. LoCoMo: long multi-session dialogues. Vendor LoCoMo numbers are not comparable across papers. | Standard | https://arxiv.org/abs/2410.10813 ; https://github.com/xiaowu0162/LongMemEval | **ADOPT as eval design source.** Add temporal, update and abstain cases to M11-AT; do not gate on public leaderboard scores. |

**SOTA synthesis**
- Types: working (context), core profile, episodic (raw, immutable), semantic (derived facts), procedural (behavior policy).
- Writes: extract async or at a defined boundary, compare to existing items, then add/supersede/ignore.
- Conflicts: invalidate, do not delete. Keep both with validity intervals.
- Forgetting: TTL plus explicit user delete; keep the audit tombstone. SECMA's `expires_at` and "index retention differs from artifact retention" already fit.
- Temporal: answer "as of T" needs valid time and transaction time. SECMA has only the latter.

**Verdict on `as_of`:** the A-14 definition (observed <= T with corrections known at T) is correct transaction-time semantics. CHANGE: name it `known_as_of`, and add optional `valid_at` for "what was true on date X". Two lines in BOUNDARY_CONTRACTS, no engine change. Required for M11-AT-01 ("study from last week") only as `observed_at` range; valid-time is NOT needed in S00-S02.

## 2. Retrieval for local-first

| Item | Description | Maturity | Source | Verdict |
|---|---|---|---|---|
| SQLite FTS5 (BM25) | Built-in lexical index, `bm25()` ranking, no dependency. | Very mature | https://www.sqlite.org/fts5.html | **KEEP/ADOPT for S01-S02.** Matches audit "FTS-first". |
| sqlite-vec | Vector virtual table extension by Alex Garcia, pure C; runs on a laptop. Version status (pre-1.0) UNVERIFIED. | Young, active | https://github.com/asg017/sqlite-vec | **Defer** past S02 behind a `SearchPort`; do not make a hard dependency. |
| RRF hybrid | score = sum 1/(k+rank), k~60; recommended by sqlite-vec author for FTS5+vector; used in Llama Stack's sqlite-vec provider. | De facto standard | https://simonwillison.net/2024/Oct/4/hybrid-full-text-search-and-vector-search-with-sqlite/ | **ADOPT** when vectors arrive. Rank-only fusion needs no score calibration. |
| pgvector | Postgres vector type with HNSW/IVFFlat; pairs with `tsvector` for lexical. | Mature | https://github.com/pgvector/pgvector | **KEEP** for SERVER profile. Same `SearchPort`, same RRF in SQL. |
| Contextual Retrieval | LLM prepends 50-100 token context to each chunk before embedding and BM25. Anthropic: top-20 failure 5.7% to 3.7% (embeddings), 2.9% (+BM25), 1.9% (+rerank). Vendor eval. | Technique, cheap with prompt caching | https://www.anthropic.com/news/contextual-retrieval | **LOW-priority ADOPT** for M20 document ingestion only. Costs an LLM call per chunk. Not for chat memory. |
| Reranker / local embeddings | Cross-encoder rerank of top ~50; small local embedding models (e.g. BGE/e5/nomic class). Model choice UNVERIFIED. | Mature | not fetched | **Defer.** Out of scope until an eval shows FTS recall is insufficient. |

**Minimal SOTA stack:** one SQLite file; `episode` rows plus an FTS5 table plus structured filters (space, requester, project, time, kind); a `SearchPort` returning ranked IDs. Step 2 adds sqlite-vec plus RRF; the Postgres profile uses `tsvector` + pgvector with identical port and fusion. Over-engineering for MVP: embeddings, reranker, graph DB, contextual chunking, community summaries, sleep-time agents.

## 3. Shared knowledge, ACLs, poisoning

| Item | Finding | Verdict |
|---|---|---|
| Pre-filter vs post-filter | Post-filtering top-K can drop all authorized results and leaks existence via timing/counts. Pre-filter (metadata filter inside the index query) is the recommended approach. General practice, no single primary source fetched (UNVERIFIED). | **KEEP.** RFC-013 s6 "pre-filter, then post-check" is right. Add a test that unauthorized items cannot change rank, count or latency class of authorized results. |
| Per-space index vs shared index + filter | Per-space indexes give hard isolation and easy deletion; shared index is cheaper. | **CHANGE:** one SQLite DB per PERSONAL space in the local profile (physical isolation); in Postgres one table with mandatory `space_id` and RLS as defense in depth. Decision belongs in RFC-013. |
| Provenance / citation | `source_space_ids` label (RFC-013 s7) is stronger than most products. Every MemoryHit must carry source ref, observed_at, content hash. | **KEEP;** add `content_sha256` to brain-document and Episode. |
| Memory poisoning | MINJA: query-only injection into agent memory, 98.2% injection success, 76.8% attack success reported (https://arxiv.org/abs/2503.03704). AgentPoison: backdoors RAG/memory, >80% average success (UNVERIFIED venue). A 2026 study reports moderation and sanitization largely ineffective (https://arxiv.org/abs/2601.05504). OWASP lists memory poisoning in its agentic list (UNVERIFIED id). | **CHANGE (HIGH).** Prompt-level defenses are not enough. Required code rules: (a) INFERENCE and untrusted-source episodes are never promoted to FACT or PREFERENCE without user confirmation; (b) a memory item's `trust_origin` (USER/OWNER_DOCUMENT/THIRD_PARTY/MODEL) is stored and rendered into context as data, never as instruction; (c) memory cannot alter policy, authorization or behavior config (already RT-01 spirit); (d) writes from third-party content need a quarantine state; (e) red-team test per AGENTS.md using a planted episode. |

`Episode` has no `trust_origin` or `author_ref`. That is the largest poisoning gap in the type.

## 4. Interop formats

| Item | Description | Maturity | Verdict |
|---|---|---|---|
| Markdown folder / Obsidian vault | Plain files, front matter, wikilinks. Human-editable, git-diffable. | De facto for personal knowledge | **KEEP/ADOPT** as the first M20 provider (matches audit A-20). Use file hash + mtime as `version`; front-matter `space`/`acl` is advisory only, ACL comes from the SECMA space binding. |
| MCP memory servers | The reference MCP memory server is a JSON knowledge-graph file; many third-party variants. MCP is an access protocol, not a memory schema. UNVERIFIED current state. | Fragmented | **KEEP as optional adapter** behind the existing ToolGateway rule (A-20). Do not expose memory writes to the model through MCP. |
| Emerging standard for "brain" portability | None confirmed. Anthropic's memory tool defines a file-command interface only. | None | **REJECT** designing a custom brain format; export = Markdown plus JSONL of Episodes with hashes. |

## Over-engineering flags (for S00-S02)

Six brain providers, ingestion cursors/conflicts/watch (M20), Claim/Decision/Preference as separate stores, embeddings, graph, community layer, sleep-time consolidation, procedural memory, contextual chunking. Keep: Episode table, FTS5, `known_as_of`, supersede chain, trust_origin, pre-filter, one Markdown brain read-only.

## Recommended deltas

| Target file | Change | Priority | Slice |
|---|---|---|---|
| docs/architecture/TYPE_CATALOG.md (Episode) | Add `requester_ref`, `project_ref`, `method_ref`, `confidence`, `trust_origin` (USER/OWNER_DOCUMENT/THIRD_PARTY/MODEL), `content_sha256`, `space_id`; optional `valid_from`/`valid_to` | BLOCKER | S02 |
| BOUNDARY_CONTRACTS (memory search) | Define `known_as_of` (observed<=T, corrections known at T); `valid_at` optional and out of MVP; name FTS5 + structured filters as the only S02 method | BLOCKER | S02 |
| docs/rfcs/RFC-005 | Add promotion rule: INFERENCE or untrusted-origin items need user confirmation before FACT/PREFERENCE; memory never alters policy; quarantine state for third-party writes | HIGH | S02 |
| contracts/brain-document.schema.json | Replace `visibility` enum with `space_id` (RFC-013 kinds); add `content_sha256`; keep `acl_ref` derived from space grants | HIGH | S02 |
| docs/rfcs/RFC-013 s6 | Decide: one SQLite file per PERSONAL space locally; mandatory `space_id` + RLS in Postgres; add leakage test (rank/count/timing invariant) | MEDIUM | S02 |
| docs/prds/M11.md | Add LongMemEval-style ATs: knowledge update, temporal question, abstention when memory absent, poisoned-episode red-team | MEDIUM | S02 |
| docs/prds/M20.md | First provider = read-only Markdown folder; defer cursors, conflict resolution, watch, MCP/other providers | MEDIUM | S02 |
| docs/prds/M13.md | Core-profile concept: bounded preference block injected each turn; consolidation job deferred | LOW | post-S02 |
| Architecture / ports | `SearchPort` with FTS5 impl; sqlite-vec + RRF and pgvector as later implementations; embeddings and reranker explicitly out of MVP | LOW | S03+ |
| docs/prds/M20.md | Contextual retrieval as optional ingestion step, only after eval shows recall gap | LOW | S04+ |
