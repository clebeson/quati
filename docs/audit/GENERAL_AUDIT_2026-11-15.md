# SECMA v8 — General specification audit (2026-11-15)

> Historical audit snapshot. The current reconciliation and observed checks are in `SPECIFICATION_FINALIZATION_2026-11-15.md`; older counts and dispositions describe their original scope.


Status: FINAL (24 findings: 7 BLOCKER, 11 HIGH, 6 MEDIUM). Specification audit only (work_mode SPECIFICATION_ONLY); no runtime changes.
Method: five parallel scoped reviewers (PRDs M01–M10, M11–M20, M21–M31, technology/architecture,
delivery process/tests). The lead auditor re-checks evidence before a finding is accepted here.
Each finding below is marked VERIFIED (the lead auditor re-read the cited text) or REPORTED (from a
reviewer, not yet re-checked).

Selection criterion: only gaps that block implementation, cause implementers to diverge, or push the
product away from its own goals. Cosmetic issues and "add more tests" are excluded on purpose.

## Findings

### A-01 (HIGH, VERIFIED) — Proactive secretary behavior has no delivery path before S04
The product promise is proactive ("communicates at the right moment", "useful update by recorded due
time", quiet hours). But the MVP is CLI-only with no channel adapter before S04 (M29), and TRD §4 says
that when the laptop sleeps "local worker pauses". The only outbound surface listed in TRD §13 is
`secma messages --unread` (pull). Undefined: what counts as "delivered" for a local CLI user in
S02/S03 (DeliveryPort requires a "sink acknowledgement"), and what the ERI timing oracle measures
when nobody is polling.
Fix: define a first local sink in S02 (for example, a local inbox table plus an optional OS desktop
notification) and its exact ACK semantics (written to inbox = delivered; read = acknowledged). State
explicitly that timeliness guarantees hold only while the worker runs.

### A-02 (MEDIUM, VERIFIED) — The "MVP decision" table still leaves choices open
TRD §3 is titled "choose one implementation per initial boundary", but it says "Typer; switch to
argparse if packaging materially suffers", "Jinja2 ... or pure Python string assembly", and
"isolated Postgres or SQLite only in non-release prototype". Each "or" is a choice the implementer
makes silently, which DELIVERY_GOVERNANCE forbids ("Remaining design ambiguity is a specification
defect").
Fix: pick one for each (recommended: argparse or Typer, one chosen; pure-Python assembly; see the
persistence findings below) and move the alternative to "Deferred".

### A-03 (BLOCKER, VERIFIED) — Mandatory PostgreSQL contradicts "local-first, no Docker, Win/macOS/Linux"
TRD §4: "Default production-like persistence is PostgreSQL native/remote"; BOUNDARY_CONTRACTS ledger
spec mandates one PostgreSQL transaction (timestamptz, JSONB); TRD §3 allows SQLite "only in
non-release prototype". No document says how a personal Windows/macOS user obtains and operates a
Postgres server (service, port, upgrades, backup), so the local profile has no shippable database.
Fix: a LedgerPort with two backends: SQLite (WAL, `BEGIN IMMEDIATE`) as the local profile, PostgreSQL
as the corporate profile; portable DDL (JSON text, ISO-8601 UTC); the same DUR-01..04 crash tests on
both. The uniqueness keys and expected-revision updates already specified work on SQLite.

### A-04 (HIGH, VERIFIED) — DBOS role is duplicated by SECMA's own ledger; the boundary is undecided
SECMA already owns commitment_events, workflow_refs, outbox, effect_intents, timer_intents + sweeper,
leases and crash reconciliation (BOUNDARY_CONTRACTS "Ledger transaction specification"). RFC-003/TRD §5
avoid DBOS long waits (suspension is an enterprise feature). DurableRunner.schedule "may be
implemented through ledger timers". ADR-003 rationale is one line ("Lower operational overhead") with
no alternatives. Result: two sources of truth (DBOS state and workflow_refs) plus a reconciliation
problem that exists mostly because both are used. Also, the spec forbids claiming atomicity between
DBOS and business transactions while DBOS transactions in the same database can checkpoint
atomically. The spec does not evaluate that option.
Lead-auditor judgement: not necessarily "drop DBOS", but the spec must decide one of:
(a) ledger-driven worker (claim with lease → bounded step → commit event), DBOS deferred; or
(b) DBOS owns step execution in the same database as the ledger, with ledger writes inside DBOS
transactions, and workflow_refs is removed as a separate truth.
Recommended: (a) for the local profile, since it also resolves A-03. Rewrite ADR-003 with real
alternatives. Remove `temporal` from the `durable-execution.schema.json` engine enum (YAGNI).

### A-05 (HIGH, VERIFIED) — Worker process model on a personal machine is undefined
`secma worker start` exists (TRD §13), and TRD §4 says that when the machine sleeps the worker pauses.
Nothing defines who starts the worker (systemd user unit / launchd / Task Scheduler), the single-
instance lock, the catch-up policy for missed timers after sleep, or how the user learns that
reminders are not firing. This is the core of a "secretary" promise (see A-01).
Fix: specify `secma worker run` (foreground) and `secma worker tick` (drain-and-exit, OS-scheduled),
plus a tested missed-timer catch-up rule and a `doctor` warning when no worker heartbeat exists.

### A-06 (HIGH, VERIFIED) — Stack decisions left for implementers to guess
Absent from TRD/matrix/ADRs/pyproject: DB driver and migration tool, config format and location,
secret-reference backend, search engine for capability and memory search ("up to K candidate tools"
with no ranking method), logging format. Suggested defaults (reviewer opinion, endorsed by the lead
auditor): stdlib sqlite3 / psycopg 3 with plain-SQL hash-checked migrations; TOML via tomllib +
platformdirs; keyring with env-var fallback; SQLite FTS5/BM25 first with embeddings deferred; JSONL
logs with an optional OTel extra; install via `uv tool`/pipx.

### A-07 (MEDIUM, VERIFIED) — The lock is single-platform and has no hashes
requirements-lock.txt is "Reproduced Linux Python 3.12" only, has no hashes, and mixes test and
runtime sets, although the product targets 3 OSes. The httpx2/httpcore2 pins were checked and are
legitimate. Fix: `uv lock` (cross-platform, hashed) with dependency groups.

### A-08 (MEDIUM, REPORTED, plausible) — No local-model profile or structured-output fallback ladder
The adapter uses OpenAI-compatible transport, so Ollama/vLLM would work, but the matrix names only
hosted providers, despite "local-first" and "useful with smaller models". There is no specified
fallback order when probing shows tool calls or native JSON schema are unsupported.
Fix: name a local OpenAI-compatible profile, and define the order native structured output → tool
call → prompted JSON with bounded repair → BLOCKED.

### A-09 (BLOCKER, VERIFIED) — Policy format and "trusted configuration" are undefined
M25 says authorities are granted "through trusted configuration" and evaluated over
actor/tenant/destination/effect/data class/consent/expiry, but no policy file format, schema,
location, owner or edit path exists. prompt-build-receipt fixes `policy_ref` to a constant, and the
candidate code hard-codes a fixture dict. RFC-007 mentions "signed installation/operator policies"
with no key or verifier. M25's non-goal rejects "policy languages", which leaves nothing in place.
Fix: `contracts/policy.schema.json` with a declarative default-deny allowlist (capability, effect,
destination pattern, data class, expiry), stored as a local file protected by OS permissions;
signing deferred to S07.

### A-10 (BLOCKER, VERIFIED) — Approver identity and approval UX in a CLI-only product are undefined
ApprovalRef has approver_id/actor_id (TYPE_CATALOG:26), and approval binding is specified in detail
(RFC-007), but there is no `secma approve` command and no rule for who can approve. In a single-user
CLI, actor and approver are the same human, and the agent's process can type into the same terminal.
Promotion approvals (M27, M30, ProfilePort.activate) reuse the undefined concept.
Fix: one ADR. The approver is the OS-authenticated local owner. Approval is a separate
`secma approve <intent-id>` that shows the canonical digest/destination/content and requires an
interactive TTY, so it cannot be invoked from capability, tool or harness subprocesses (they get no
TTY and a marked environment). Multi-user approver rules are deferred.

### A-11 (HIGH, VERIFIED) — PRD slice tags contradict the roadmap and the S00 safety rules
- M25 is "Delivery slice: S00", but M25-AT-01 is "Forged instruction in Slack message cannot
  self-approve a write". RFC-007 says S00 "denies all write/dangerous capabilities", and Slack exists
  only in S04.
- M01 is S00, but M01-AT-02 requires "an asynchronous request prints a real commitment ID". Real
  commitments are S02, and PRODUCT_PRD forbids presenting transient IDs as commitments.
- M08 says "S01 foundations; S03 completion" in its header and "Target phase: S03" in its handoff,
  while M04/M03 in S01 need its classification.
Root cause: each PRD has one slice tag, but its FR/AT lines span several slices.
Fix: add an earliest-slice tag per FR/AT line (with a fixture-only variant where relevant), and
regenerate the traceability matrix from those tags.

### A-12 (HIGH, VERIFIED) — PRD vocabularies do not match the schema enums
- M04-FR-01: "social, answer, context lookup, compound work, investigation and external action".
  The schema intent enum is social/simple_answer/status_query/context_lookup/professional_work/
  deep_investigation/external_action. There is no "compound work", and status_query is unmentioned.
- M09-FR-03: "complete, partial, blocked or inconclusive". The outcome-assessment enum is
  ACCEPT/INVESTIGATE_MORE/PARTIAL/BLOCKED.
- M08 promises "prioritization/urgency", but no priority or urgency field exists anywhere in
  TYPE_CATALOG or the schemas.
Fix: PRDs cite schema enums by name. Add a priority/urgency field or drop the claim.

### A-13 (HIGH, VERIFIED) — PRDs are template clones and carry almost no module-specific definitions
M21 and M22 differ by only 44 diff lines after normalising the module ID. Every PRD is about 69
lines, with sections 4–10 boilerplate and 3 FR + 2 AT + 2 RT one-liners as the only substance.
The real behavior lives in contracts/ROADMAP/ACCEPTANCE_CASES. Consequences: subjective terms
("materially affect scope", "meaningful progress", "useful moments", "likely changes the decision")
have no threshold, type or owner, and no PRD says which module owns the final InteractionDecision
(M03 vs M05 vs M08).
Fix (keep it light): replace the repeated sections with one shared template reference; for each
module add the owned output types and one decision rule per subjective term (e.g. ask only when a
missing field is in a fixed blocking set, or ≥2 candidates remain within a margin). State that
"usefulness" is an EDD rubric metric, not a gate oracle.

### A-14 (BLOCKER, VERIFIED) — Memory (M11/M13) has no store, search method or `as_of` meaning, and its types cannot carry the PRD fields
M11-FR-02 searches "by requester, time, project, method and commitment", but TYPE_CATALOG `Episode`
has only work_ref/entry_kind/content_ref/evidence_refs/acl_scope/observed_at/expires_at/supersedes_ref.
`search(context, query, scope, as_of)` (BOUNDARY_CONTRACTS) never defines `as_of`. M11-RT-01/RFC-005
cite "similarity/embedding search", but no engine is named anywhere. M13 needs explicit/observed/
inferred preferences with confidence, and RFC-005 names Preference/Decision/Claim records, none of
which is in the catalog. M11-AT-01 ("the study from last week") is therefore not implementable as written.
Fix: lexical FTS plus structured filters for S03, with embeddings out of scope; add requester_ref,
project_ref, method_ref and confidence to Episode (or add a Preference type); define `as_of` = "records
observed at or before T, with corrections known at T applied".

### A-15 (BLOCKER, REPORTED, spot-checked) — Capability ranking and install/registry persistence are undefined
M15-FR-02 ranks by "outcome fit, permission, assurance, cost, model compatibility and health", with no
method or weights (`rank_reasons` is free text). There are three install mechanisms: S00 install
`--fixture-handler` only, M14-AT-01 "unknown capability discoverable on next run", and M18-AT-01
descriptor install after approval. None of them says where S00 manifests persist, and no S00→S02
registry migration exists (the tables are "DDL produced in S02").
Fix: filter by hard constraints, then a lexical score over name/description/intents, then let the LLM
choose among the top K (the ranking is only a shortlist; the choice is the LLM's, as the product intends).
Use a file-backed registry under the state dir in S00, an S02 import task, and one install flow with
fixture and descriptor modes.

### A-16 (HIGH, REPORTED) — Capability lifecycle/assurance model is inconsistent
RFC-001 uses upper-case DRAFT→VALIDATED→STAGED→ENABLED, while the schemas use lower case. The manifest
self-declares `lifecycle` and `assurance`, contradicting "definition, binding and measured assurance
separate". There are two scales (manifest C0..C5 and binding verification UNVERIFIED..PRODUCTION) with no
mapping, plus a separate `binding.enabled` boolean, and no rule for who may enable.
Fix: make lifecycle and assurance registry-owned (not in the manifest), use one enum casing and one
scale, and gate enabling on A-10 approval.

### A-17 (HIGH, REPORTED) — Manifest schema is weaker than M14/RFC-001 claim
The `id` pattern does not require a namespace, `input_schema`/`output_schema` are bare objects, there are
no compatibility or evidence-requirement fields, and `capability_version` is not semver-constrained, so
"duplicate ID with incompatible major version" cannot be detected.
Fix: tighten exactly these fields; nothing more.

### A-18 (HIGH, REPORTED) — Model routing/escalation (M17) has no data or operation
ModelPort has only probe/classify/run. The competence schema has no thresholds, risk tier, cost,
region, auth kind, tool_choice or parallel-call fields, although M17-FR-02/03 and TECHNICAL_REFERENCE
need them, and TECHNICAL_REFERENCE admits the thresholds "require real benchmarking".
Fix: one operator-config `RoutingPolicy` (minimum accuracy and abstention, escalation order, risk→role,
cost cap), plus the missing probe fields marked attested/unknown. Ship with one configured model and
escalation disabled until benchmarked (see A-21).

### A-19 (MEDIUM, VERIFIED) — Agent Skills (M16) have no type, port or binding
No "skill" appears in TYPE_CATALOG, BOUNDARY_CONTRACTS or contracts/. "Eligible capability" (M16-AT-01)
is undefined. Fix: a SkillDescriptor (name, hash, path, requested permissions) attached as data to a
binding, never a capability; or defer M16 out of S03.

### A-20 (MEDIUM, REPORTED) — Duplicate tool paths and unspecified first targets
- MCP: there are both an SCS binding `adapter_type=mcp` and `ToolGateway.call`. State that MCP tools
  reach the model only via SCS manifests and that invoke delegates to ToolGateway.
- M20: name the first brain provider (local Markdown folder) and its ACL rule; defer cursors,
  conflicts and watch.
- M12: "route edit to capable handler" has no editable-format handler notion. Name one source format
  for the chart AT.

### A-21 (BLOCKER, VERIFIED) — S00 gate requires a 30-case sealed benchmark by an independent evaluator
TEST_EXECUTION_PROTOCOL makes S00-GATE-02 depend on MOD-01 (≥30 sealed cases, ≥26 correct, Wilson
95%). Over a 2-fixture catalog, this is statistically weak (the lower bound at 26/30 is about 70%) and
needs an unnamed separate evaluator. S00_RUNTIME_CONTRACT itself says the S00 smoke "is not the sealed
30-case benchmark", so the two documents disagree about what S00 proves.
Fix: S00 gate = CAP-01/02 repeated N times (e.g. 9/10) with logged trajectories. Move MOD-01 to a
precondition for enabling autonomous routing or role promotion, not for S00.

### A-22 (BLOCKER, VERIFIED) — No MVP / definition of done for the product
Each milestone has a definition of done, but none says which slices make a usable product. S00/S01 are
"not releases", S02 is the first durable value, and S03–S07 (Windows/macOS native, enterprise
hardening, evolution, packs) are all gated as mandatory in a strict linear chain of 35 tasks.
Fix: one paragraph in ROADMAP: MVP = S00+S01+S02 on Linux at L2/L3 (plus the A-01 local sink), with
S03+ as ordered backlog. Allow S03 and S04 to proceed independently after S02.

### A-23 (HIGH, VERIFIED) — Governance ceremony exceeds what one developer + agents can honestly execute
- Seals: 9 seal kinds, 5 per task plus 3 per slice. That is about 200 hand-made records, each with a
  per-file SHA manifest, and no issuing tool (validators only check). The seal index is empty.
- Independence: the reviewer "did not author" requires a different human/agent, with no signing, so
  it is a process claim the spec cannot verify.
- State: a lease/lock protocol protects a single JSON file with one writer.
- Ops memory: six registries plus a memory_lookup field on every task.
- Human-scored ERI rubric (two blinded reviewers, undefined "no worse than baseline") gates S01.
Risk: implementers either fake the ceremony (which violates AGENTS.md rule 7 truthfulness) or stall.
Fix: git commit SHA + test log + transcript as evidence; 3 seals per slice (TESTS_VERIFIED,
EVIDENCE_VERIFIED, SLICE_ACCEPTED); define "independent" as a fresh-context reviewer run or the owner;
use a revision check instead of the lock; make human rubrics advisory, and gate S01 on its
machine-checkable assertions.

### A-24 (MEDIUM, VERIFIED) — Mechanical inconsistencies in the plan
- `tests/planned/...` is used in 109 test paths in WORK_PACKAGES.json (and in ACCEPTANCE_CASES). The
  directory does not exist and contradicts the AGENTS.md test layout.
- SLICES/S00.md says NOT_STARTED while implementation_state.json says S00 BLOCKED.
- Owned paths are whole directories shared by up to 19 tasks, so "single ownership" is vacuous.
- S00 alone spans nine modules, including the compiler/statechart (M30), before any user value.
Fix: map the planned paths to tests/unit|integration|evals|external|chaos, state that status is
derived from state.json only, and move M30 to the first slice that changes profiles.

## Sound choices (keep)
- Modular monolith with ports (no per-PRD services).
- Pure-reducer statechart for commitments.
- effect_intent + EFFECT_UNCERTAIN, with reconcile-before-retry.
- Tenant-scoped idempotency keys and optimistic revisions.
- Timers as ledger rows.
- Feature probing of the provider instead of trusting model names.
- Explicit proof tiers L0–L5, with honest NOT_VERIFIED_EXTERNAL.
- Search → describe → invoke with bounded candidates.
- The commitment-first product framing.
- Both spec validators pass at L0 (consistency only, which they state honestly).

## Over-specification to remove
- PRD boilerplate (A-13).
- Seal/registry ceremony (A-23).
- The `temporal` engine enum and the DurableRunner breadth (A-04).
- Six brain providers and four harnesses named where one of each is built (A-20).
- Heavy S03 AT/RT sets in M12/M13 beyond the gates.
- Before S02: the 30-case benchmark gate (A-21) and Windows/macOS native gates (A-22).

## Prioritised resolution order (before authorising implementation)
1. A-22 MVP scope and A-21 S00 gate, which define what must be built.
2. A-03/A-04/A-05 persistence and worker decision (one ADR), plus A-01 local delivery.
3. A-09/A-10 policy file and approval command (one ADR).
4. A-14/A-15 memory and capability search method (FTS-first), with the type-catalog additions.
5. A-11/A-12 slice tags and vocabulary alignment (mechanical; regenerate the matrix).
6. A-23 governance simplification.
7. The remaining HIGH/MEDIUM items, then A-02/A-06/A-07 stack picks.

## Limits of this audit
- Specification only; no runtime code was executed except the two spec validators (PASS at L0).
- Findings marked REPORTED were produced by a reviewer and only spot-checked by the lead auditor.
- PRDs M21–M31 were reviewed in less depth than M01–M20.

## Disposition (2026-11-15, lead)

Each finding is closed at the specification level only (L0). No runtime proof exists for any of them.

| Finding | Status | Where resolved |
|---|---|---|
| A-01 | RESOLVED | ADR-016: local inbox sink (DELIVERED on commit, ACKNOWLEDGED on read) and best-effort desktop notification. Timeliness only while a worker runs (TRD §4, §13). |
| A-02, A-06, A-07 | RESOLVED | ADR-015 §5 stack picks: Typer, TOML + platformdirs, keyring, JSONL logs, `uv tool`, `uv lock` with hashes. TRD rows 28–32. |
| A-03, A-04, A-05 | RESOLVED | ADR-015: one LedgerPort (SQLite LOCAL, PostgreSQL SERVER), ledger-driven worker, DBOS not used, `temporal`/`dbos` removed from the engine enum. ADR-016 covers the worker process model. S02 docs, ROADMAP, PRDs and slices were reworded. |
| A-08 | RESOLVED | PROVIDER_AND_TECHNOLOGY_MATRIX has a local OpenAI-compatible profile row. BOUNDARY_CONTRACTS ModelPort defines the structured-output ladder: native schema → forced tool call → prompted JSON with ≤2 repairs → BLOCKED. |
| A-09, A-10 | RESOLVED | RFC-014 covers the policy document, K1–K9, ApprovalRequest and human-only TTY approval. RFC-013 covers identity. TRD §13 lists the approvals/policy commands. |
| A-11, A-12 | RESOLVED | PRD slice tags and vocabulary were aligned (DELIVERY_PLAN_CHANGES_2026-11-15 §5). |
| A-13 | RESOLVED | docs/prds/DECISION_RULES.md: M03 owns the final InteractionDecision; one operational rule per subjective term, linked from the affected PRDs. The proposed `behavior_policy.*`/`routing_policy.*` fields still need a schema in S00. |
| A-14 | RESOLVED | RFC-005 v8.1: quarantine, trust_origin, bitemporal `known_as_of`, FTS5 behind SearchPort. Episode row in TYPE_CATALOG. |
| A-15 … A-20 | RESOLVED | RFC-015 covers packaging (SKILL.md / MCP / A2A + `scs/1.1` sidecar), the registry-owned lifecycle and assurance (`capability-registry-record.schema.json`), selection (filters → bm25 → top-K → LLM / NONE_FITS), SkillDescriptor, MCP via ToolGateway, the first M20 provider and the M12 chart format. The RoutingPolicy schema is in `model-competence.schema.json`. |
| A-21 | RESOLVED (changed) | The S00 gate is CAP-01/02 at 30/30 (10 paraphrases × 3 runs, shuffled catalog; Wilson LB 0.886) with zero unauthorized effects. The "9 of 10" rule was rejected (Wilson LB 0.596). MOD-01 moves to S04-T05. See the TEST_EXECUTION_PROTOCOL statistics note. |
| A-22 | RESOLVED | ROADMAP "Product MVP" is S00+S01+S02, Linux, LOCAL. |
| A-23 | RESOLVED | DELIVERY_GOVERNANCE has three seals. LOG.md was added. The legacy lease fields were removed from the state schema. |
| A-24 | RESOLVED | Test locators use the real lane directories, including `tests/packaging/` (AGENTS.md, PROJECT_STRUCTURE). |

Additions after the user review (2026-11-15):
- **Offline memory consolidation (dreaming pattern):** RFC-005 amendment v8.2, RFC-008 context-layer note, TYPE_CATALOG `MemorySnapshot`/`ConsolidationRun`, TRD `secma memory …` commands, cases MEM-07..09 (S03-T04). Research: docs/research/SOTA_AGENT_MEMORY_DREAMING_2026-11-15.md.
- **Local worker usability:** ADR-016 amendment `secma worker install|uninstall` (explicit, idempotent, user-level, refused inside a capability context) plus status/doctor warning; case WRK-05 (S02-T05).

Residual implementer drift, not fixed here because `src/` is out of scope:
- `src/secma/assets/contracts/*` must be re-synced with `contracts/`, otherwise `test_m30_packaged_compiler_matches_reviewed_source` fails.
- `src/secma/application/catalog.py` and `adapters/catalog_store.py` still emit `lifecycle`/`assurance` inside `scs/1.0` manifests.
