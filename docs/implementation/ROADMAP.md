# SECMA Implementation Roadmap v8

**Only this roadmap is normative.** Earlier W00–W15 or R4 M0–M3 plans are superseded and MUST NOT be executed side-by-side. First deliver an interactive, observable secretary; modular boundaries do not imply parallel microservices.

| Slice | Observable deliverable | Key modules |
|---|---|---|
| S00 | Live model + capability discovery + compiler foundations | M01, M02, M14, M15, M17, M25, M26, M30, M31 |
| S01 | ERI: conversation, work triage and selective questions | M03, M04, M05, M08, M30, M31 |
| S02 | DBOS durable commitments and outcome judgment | M06, M07, M09, M10, M26 |
| S03 | Memory, artifacts, user profiles and skills | M08, M11, M12, M13, M16 |
| S04 | Plug-and-play harnesses, brains, MCPs and channels | M18, M19, M20, M29 |
| S05 | Professional discovery, software and causal/incident domain | M21, M22, M23, M24 |
| S06 | Governed evolution and continuous evaluation | M27, M30, M31 |
| S07 | Native OS packaging and corporate hardening | M01, M02, M25, M28 |

## Build order and dependencies
- S00: `CLI → policy+schemas → compiler → model feature probe → SCS discovery → actual model tool-call trajectory`. These are small PRs inside the first slice; a non-tool-capable model is not an acceptable surrogate for dynamic discovery.
- S01: `context envelope → classifier → ERI reducer → optional clarification → safe async work` with honest non-durable limitation until S02.
- S02: `ledger → DBOS adapter → worker → due-time sweeper → outbox → evidence review → delivery`.
- S03: `memory/artifact IDs → preference/profile versioning → optional skills`.
- S04: `agent/brain/MCP ports → fake and one real adapter → channels`.
- S05: `repository discovery → software standards → incident and causal specialist packs`.
- S06: `agent proposals → prompt/statechart compile → eval → staged promotion → rollback`.
- S07: `native package → resource and enterprise provider smoke → operational release gates`.

## Conflict and stop policies
If a blind real-model discovery test fails, stop adding specialist providers and fix the small-model context, descriptions and tool schemas. If DBOS persistence/fault suite fails, stop future module work; don't add a second orchestration framework. If the first secretary episode offers no improvement over directly running a specialist CLI, do not build a GUI or additional agents before diagnosing the ERI behavior.

## Parallelism
Only distinct fixture sets, documentation, independent provider adapters and OS packaging can be parallelized after public interfaces stabilize. State machine, authorization, business ledger and outbox require single ownership/serialized merges. Independent red-team reviewer can work in parallel but cannot rewrite authoritative policy.

## Definition of milestone complete
The declared public-path acceptance tests pass at required L0/L1/L2/L3/L4 level; actual evidence exists; resource/cost bounded; no P0 blocker remains; all incomplete integrations are stated; state revision atomically advanced. Do not pre-generate “all steps done” status.

## Partial module obligations and dependency closure

| Boundary | First slice obligation | Deferred completion and evidence |
|---|---|---|
| M01 CLI | S00 ask/doctor with configuration diagnostics and safe synchronous fixture responses | S02 tell/status/messages and real durable IDs; S07 native OS lifecycle |
| M02 identity | S00 trusted local principal and deny-by-default runtime scope | S03 memory isolation; S04 authenticated callbacks/transcripts; S07 enterprise identity |
| M14/M15 registry | S00 separate definition/binding/assurance, controlled fixture activation, search/describe/invoke validation | S04 external executor feature interoperability; no early provider certification |
| M17/M31 model/context | S00 one approved real tool provider, typed decisions, bounded repair/context and measured discovery | Broader competence remains unverified until role-specific benchmark; additional providers only as needed |
| M25/M26 policy/evidence | S00 preventive denial of writes and redacted trace integrity | S02 effect/outbox reconciliation; S04 dispatch credentials; S07 enterprise controls |
| M30 behavior | S00 deterministic compile/validate/render and protected runtime enforcement | S03 human profile versions/rollback; S06 agent proposals and governed promotion |
| M03/M04/M05/M08 ERI | S01 transient work and reference fixtures with explicit lifetime limits | S02 persistent commitments; S03 historical retrieval and full routing profiles |

These assignments preserve all original FR/AT/RT obligations. The traceability matrix records partial verification separately from whole-requirement PASS. Commands whose supporting slice has not passed return an explicit unavailable response and must never simulate success.

S00/S01 may exercise safe fixture work but cannot promise durable acceptance. The in-process S01 runner is replaced by the S02 durable runner. No production release is permitted before the product invariants and all applicable release gates have evidence.

The corrected executable S00 boundary is defined by `S00_RUNTIME_CONTRACT.md`; this narrows first-slice implementation without deleting deferred product obligations.
