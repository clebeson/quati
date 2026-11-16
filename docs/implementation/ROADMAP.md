# Quati Implementation Roadmap v8

**Only this roadmap is normative.** Earlier W00–W15 or R4 M0–M3 plans are superseded and MUST NOT be executed side-by-side. First deliver an interactive, observable secretary; modular boundaries do not imply parallel microservices.

| Slice | Observable deliverable | Key modules |
|---|---|---|
| S00 | Live model + capability discovery + compiler foundations | M01, M02, M14, M15, M17, M25, M26, M30, M31 |
| S01 | ERI: conversation, work triage and selective questions | M03, M04, M05, M08, M30, M31 |
| S02 | Ledger-backed durable commitments and outcome judgment | M06, M07, M09, M10, M26 |
| S03 | Memory, artifacts, user profiles and skills | M08, M11, M12, M13, M16 |
| S04 | Plug-and-play harnesses, brains, MCPs and channels | M18, M19, M20, M29 |
| S05 | Professional discovery, software and causal/incident domain; SERVER multi-user profile (RFC-013) | M21, M22, M23, M24 (plus identity profile work in M02/M25) |
| S06 | Governed evolution and continuous evaluation | M27, M30, M31 |
| S07 | Native OS packaging and corporate hardening | M01, M02, M25, M28 |

## Product MVP

The product MVP is **S00 + S01 + S02** on **Linux**, at proof tiers **L2/L3**, using the **LOCAL profile only** (RFC-013 section 11): a single user, SQLite storage, the `local-os` authenticator, a ledger-driven worker and local inbox delivery. Post-MVP adapters and operating systems do not block this LOCAL MVP. The S02 gate requires the real SQLite backend; PostgreSQL parity is mandatory before the SERVER profile can be accepted in S05.

- **Post-MVP backlog (ordered):** S03 memory/artifacts/profiles, S04 harnesses/brains/MCP/channels, S05 professional domains plus the SERVER multi-user profile, S06 governed evolution, S07 native packaging and hardening.
- **S03 and S04 are independent after S02.** S03-T01 and S04-T01 both depend only on S02-T05 (the last S02 task). S05-T01 depends on both S03-T04 and S04-T05.
- **S05 also carries the SERVER multi-user profile** (RFC-013 section 12: Postgres with RLS, `oidc-device`, teams, A2A agents, token and session controls). Its identity acceptance cases are IDN-04..IDN-11; IDN-10 proves that IDN-01..03 pass unchanged on both profiles.
- **Windows and macOS native packaging are post-MVP** (S07). Linux is the only MVP operating system.
- **MOD-01** (the 30-case sealed model benchmark) is not an MVP or S00 condition. It is a precondition for enabling autonomous routing or role promotion, owned by S04-T05; until it passes, routing uses fixed role assignment.

## Build order and dependencies
- S00: `CLI → policy+schemas → compiler → model feature probe → SCS discovery → actual model tool-call trajectory`. These are small PRs inside the first slice; a non-tool-capable model is not an acceptable surrogate for dynamic discovery.
- S01: `context envelope → classifier → ERI reducer → optional clarification → safe async work` with honest non-durable limitation until S02.
- S02: `LedgerPort (SQLite LOCAL; PostgreSQL backend contract-tested) with numbered per-dialect migrations → ledger-driven worker (`quati worker run|tick`, ADR-015/016) with leases, heartbeat and `quati doctor` worker check → timers with catch-up (`fire_at`/`fire_until`) → outbox → evidence review → local inbox delivery`. DBOS is not in S02 or S06 scope (ADR-015). Timeliness holds only while a worker runs. S02 also imports the S00 file capability registry into the ledger (RFC-015 §6).
- S03: `memory/artifact IDs → preference/profile versioning → optional skills`. Independent of S04 after S02.
- S04: `agent/brain/MCP ports → fake and one real adapter → channels → MOD-01 role qualification`. Independent of S03 after S02.
- S05: `SERVER profile identity (IDN-04..IDN-11) and repository discovery → software standards → incident and causal specialist packs`; starts after both S03 and S04.
- S06: `agent proposals → prompt/statechart compile → eval → staged promotion → rollback`.
- S07: `native package → resource and enterprise provider smoke → operational release gates`.

## Conflict and stop policies
If a blind real-model discovery test fails, stop adding specialist providers and fix the small-model context, descriptions and tool schemas. If the ledger-worker persistence/fault suite (DUR/WRK cases, RFC-003 conformance) fails, stop future module work; don't add an orchestration framework as a workaround. If the first secretary episode offers no improvement over directly running a specialist CLI, do not build a GUI or additional agents before diagnosing the ERI behavior.

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

## Detailed execution and governance authority

`WORK_PACKAGES.json` contains 35 bounded tasks; `work_packages/S00.md`–`S07.md`
provide ordered handoffs. They refine this roadmap without permitting skipped
slice gates. Read PROJECT_STRUCTURE, BOUNDARY_CONTRACTS, DELIVERY_GOVERNANCE and
PERSISTENT_STATE_AND_MEMORY before implementing. SPECIFICATION_ONLY mode prohibits
new runtime implementation until explicitly authorized.

Phase corrections: informational-answer SOC-02/CAP-04 are S01; runtime profile
rollback CMP-04 is S03; full trace ACL/retention EVD-01 is S07, with local private
receipt checks starting in S00. S00-GATE-02 is CAP-01/CAP-02 passing in 30 of 30
repeated live runs each; MOD-01 low-risk role calibration is re-phased to S04 as a precondition
for autonomous routing/role promotion. No full-module completion is inferred from a first slice.
