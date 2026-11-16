# Stakeholder-to-Module Coverage (English Canonical Reinterpretation)

| Stakeholder need | Owners | Required proof | First gate |
|---|---|---|---|
| Fast greetings and simple factual answers without delegation | M03/M04/M17/M31 | Actual LLM or deterministic safe entry; no job created | S00/S01 |
| Smart decision to start safe research while asking only valuable questions | M03/M05/M30 | Real multi-turn episode + commitment update | S01 |
| Human expectation and attention management | M06/M10/M13 | Virtual clock + blind usefulness ratings | S02/S03 |
| Durable multiple jobs, independent of chat window | M07/M06 | SQLite LedgerPort + worker crash and concurrency suite (PostgreSQL backend contract-tested) | S02 |
| Understand old work after days/weeks | M04/M11/M12 | Authorized prior commitment/artifact retrieval or honest ambiguity | S03 |
| Detailed PRD/document creation with concise human summary | M10/M12/M22 | Versioned artifact, sources, summary, trace | S03/S05 |
| Dynamic SCS capability discovery by weak and strong models | M14/M15/M17/M31 | Blind actual provider tool trace, negative & distractor cases | S00 |
| Every capability follows explicit result/control contract | M14/M30/M31 | Compiler negative validation + runtime state enforcement | S00/S02 |
| Install and remove arbitrary specialist harness | M18/M15 | Adapter conformance; removal while task running | S04 |
| OpenAI/Codex/Claude/Hermes/Genplat model and harness providers | M17/M18 | Feature probe and separate auth smoke | S00/S04 |
| Any second brain, Git repository, folder, GBrain, wiki | M20/M11/M21 | Local provider, fake remote and real smoke if available | S04 |
| MCP skills/tools/A2A delegation | M16/M18/M19 | Tool/access policy and contract tests | S03/S04 |
| Deep repo discovery of PRD/TRD/DSD/ADR/RFC | M21/M22 | Recursive fixture corpus coverage + provenance | S05 |
| Incident and causal Ads analysis | M23/M24/M09 | Evidence/alternative hypothesis/causal trap cases | S05 |
| Learning communication preferences without intrusion | M13/M03 | Repeated-user correction plus profile rollbacks | S03 |
| Agent-assisted prompt/flow improvement | M27/M30 | staged candidate+independent holdout+rollback | S06 |
| Enterprise portable, Docker-free, corporate restrictions | M28/M25/M17 | Native OS, network/residency and resource tests | S07 |
| All specs, prompts and code internal artifacts in English | M01/M30, governance | Repo English-only check, per-user response language test | S00/S01 |
| Prompt compilation and state machines from editable configuration | M30/M31 | deterministic digest, rejected unsafe state machine, controlled promotion | S00 |
| Robustness without meaningless tests | testing/governance | risk-to-proof ledger and reviewer justification | all |

The stakeholder requests remain broader than the MVP. Deferred features retain module ownership but MUST NOT be described as implemented. See `MIGRATION_FROM_PREVIOUS_VERSIONS.md` for superseded legacy versions.
