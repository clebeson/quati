# Agent memory: in-band notes and offline consolidation ("dreaming") — 2026-11-15

Status: RESEARCH NOTE (input to RFC-005 amendment v8.2, RFC-008, ADR-016). Lead-verified from the
primary sources below.

## Sources
- Anthropic, "The components of agent memory" (engineering article, 2026).
- Claude Managed Agents — Dreams: https://platform.claude.com/docs/en/managed-agents/dreams
  (research preview; beta header `dreaming-2026-04-21`).

## What the sources say
1. Agent memory = knowledge gained from experience and kept across sessions as context.
2. Three parts: (a) in-session note writing to a memory directory; (b) a small injected top layer
   (an index such as MEMORY.md, about 200 lines / 25 KB); (c) offline "dreaming" that reorganizes
   notes and tests them against the session transcripts.
3. A dream is an async job: input = a memory store + 1–100 sessions; output = a **new** store.
   "The input store is never modified, so you can review the output and discard it."
4. Reported effect (CL-Bench): Opus 5.5 0.655 → 0.838; Sonnet 5.5 0.644 → 0.833.
5. Reported risks: a wrong note is carried into every session; drift; longer instructions reduce
   adherence; a consolidated wiki grew to 1.77× its corpus.

## SECMA mapping
| Source idea | SECMA rule |
|---|---|
| In-session notes | RFC-005 rule 5 (ADD/UPDATE/INVALIDATE/NOOP validated by code) |
| Injected top layer | RFC-005 rule 8, capped by `core_block_max_bytes` (v8.2 rule 6) |
| Dream writes a new store | `ConsolidationRun` → candidate `MemorySnapshot` (v8.2 rules 2–3) |
| Test notes against transcripts | Evidence verification, deterministic first (v8.2 rule 4) |
| Review/discard output | Promote / discard / rollback as a pointer swap (v8.2 rule 7) |
| Wrong-note, drift, bloat risks | MEM-08, MEM-09, size budget (v8.2 rule 6) |

## What SECMA adds (not in the sources)
- Multi-tenant scope: one run reads one space; TEAM/ORG promotion needs a MANAGER approval.
- Trust ceiling: consolidation cannot un-quarantine or raise trust_origin (memory-injection results
  such as MINJA show prompt-level defenses are insufficient).
- Provider neutrality: the run is a ledger work item; a vendor dream API is only an optional adapter.

## Not adopted
- Letting the model edit the active store directly during consolidation.
- Graph memory and embeddings before an eval shows a recall gap (RFC-005 rule 7).
