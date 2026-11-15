# Migration from Earlier SECMA Specifications

**Authoritative status:** This v8 package supersedes earlier SECMA PRD v2, SCS v0.1/v0.3/v1, audit R4, CLI/TRD R6, and modular PRD/TRD v7 on overlapping requirements. Those earlier files are **not included** because portions were in Portuguese, contain different stage numbering or prescribe premature infrastructure. This package rewrites the relevant requirements in English and records the design decisions below.

| Prior idea | v8 treatment | Reason |
|---|---|---|
| 79 capabilities or 30 executive capability files | retained as a future catalog concept, NOT initial 79 runnable modules | manifest count is not empirical competence |
| v7 29 module PRDs | rewritten in English as M01–M29 with unique FR/AT/RT | preserve coverage without conflicting languages |
| Need to dynamically write prompts and state graphs | added M30, RFC-010/011, typed compiler schemas | explicit accountable owner and governance |
| Strong and small models | added M31, RFC-012, per-provider competence profiles | large context is not proof of reasoning |
| DBOS vs Temporal | DBOS initial, minimal durable port, Temporal future | low local infrastructure, avoid big abstraction now |
| Pydantic AI capabilities | reuse as one runtime implementation of SCS | do not reinvent native tool discovery |
| CLI-only request | binding in PRD, TRD and implementation gates | do not build frontend/HTTP app |
| S0a..S4 and conflicting W00..W15 | **only S00–S07** is normative | prevent agent resumption confusion |
| Fake Slack/Drive integration tests | L2 local fakes + L4 authorized live smoke | honest verification tiers |
| Auto-evolving prompts | staged propose/compile/eval/promote/rollback | prevent unsafe self-modification |
| Context restoration and stakeholder management | ERI first vertical slices | product differentiator over specialist CLI |

Translation note: legacy content is summarized and rewritten rather than mechanically translated word-for-word, since conflicting and speculative legacy instructions must not enter the new authoritative corpus. All user-visible SECMA responses are localized by runtime policy; internal authoring language is English.
