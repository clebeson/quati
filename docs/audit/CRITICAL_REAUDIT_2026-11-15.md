# Critical re-audit of architecture decisions — 2026-11-15

Status: review record. It does not change any gate, slice status or accepted ADR by itself.
Rows marked **APPLIED** were written into the specification on 2026-11-15 as defect
corrections. Rows marked **OWNER** change an accepted decision or the delivery structure and
wait for the project owner.

## 1. Question and method

The owner asked for each decision to be confronted with the objective — a secretary that
takes responsibility for work, is correct the first time, is exercised only through the
terminal — and for the project to reuse published, tested work instead of rebuilding it.

Six independent reviews were run, one per area, each with fresh web research and no access
to the others' conclusions: durable execution, identity and policy, capabilities and
protocols, agent runtime, memory and requester relationship, evaluation/testing/CLI. The
reviews are model output. The root then checked the claims that carry a verdict against
local files and primary sources. Section 6 separates what was checked from what was not.

Verdict vocabulary: **KEEP**, **KEEP-WITH-CONDITIONS**, **CHANGE**.

## 2. Overall finding

The split between what is hand-built and what is adopted is wrong in both directions.

- The **protected kernel** (pure reducer over a control table, ledger and outbox, policy
  evaluator, effect gateway, approval state machine, route table, assurance tiers) has no
  published equivalent that gives the same guarantees. Building it is justified. Its
  defects are specific and listed below.
- Around the kernel the project **rebuilds things that exist, are tested and are open**:
  the model tool loop and output-repair ladder, capability search/describe/invoke
  meta-tools, a token format, a JSON canonicalisation, skill naming, a statistics rule for
  model gates. These should be adopted, confined behind one adapter each.
- The largest risk to "works the first time" is not a component. It is the delivery shape:
  about 280,000 words of specification against roughly 500 lines of product code, a linear
  work-package chain, and a live-model gate that blocks deterministic work behind it.

## 3. Verdicts by decision

### 3.1 Durable execution (ADR-015, RFC-003)

| Decision | Verdict | Finding | Disposition |
|---|---|---|---|
| Hand-written ledger worker instead of a durable-execution framework | KEEP-WITH-CONDITIONS | Decision holds; the stated reasons were partly wrong (size estimate, description of alternatives). | APPLIED (rationale corrected) |
| `secma doctor` refuses SQLite below 3.51.3 / 3.50.7 / 3.44.6 | CHANGE | The WAL-reset bug is real, but this interpreter links 3.46.1 and CPython 3.14 bundles 3.50.4: the rule refuses nearly every real install. Use WAL only on fixed versions, otherwise `journal_mode=TRUNCATE`; doctor warns. | APPLIED |
| Connection contract unspecified | CHANGE | No `synchronous`, no autocommit rule. WAL with `synchronous=NORMAL` can lose committed transactions on power loss, which breaks "durable commitment". Require `synchronous=FULL`, `fullfsync` on macOS, `foreign_keys=ON`, `autocommit=True` with explicit `BEGIN IMMEDIATE`. | APPLIED |
| Lease without fencing in commits | CHANGE | A worker whose lease expired can still commit. Lease epoch goes in every commit's WHERE clause. | APPLIED |
| PostgreSQL backend | KEEP-WITH-CONDITIONS | State isolation level, per-commitment `FOR UPDATE`, `SKIP LOCKED` claims; qualify only after the SQLite gate. | APPLIED |
| Step time bound | KEEP-WITH-CONDITIONS | Client timeouts plus cooperative deadline; never thread kill. | APPLIED |
| Backup by file copy | CHANGE | `VACUUM INTO` or online backup API; restore marks non-terminal effect intents `EFFECT_UNCERTAIN`. | APPLIED |

### 3.2 Identity, authorization, policy, audit

| Decision | Verdict | Finding | Disposition |
|---|---|---|---|
| Local token format (custom `LocalToken`) | CHANGE | Reinvents JWS. Use a hardened JWT library configuration (fixed algorithm allow-list, required claims). | OWNER (touches surviving S00 code) |
| Canonical JSON `secma-json/1` via `json.dumps(sort_keys=…)` | CHANGE | Not RFC 8785; digests are not reproducible by other implementations. Adopt an RFC 8785 library. | OWNER (changes every stored digest) |
| Own issuer for local mode | KEEP-WITH-CONDITIONS | Acceptable locally; key in OS keyring, rotation specified. | Recorded |
| Delegation (RFC 8693 style) | KEEP-WITH-CONDITIONS | Not before S05. | Recorded |
| `allow()` authorization before effects; hand-built policy evaluator | KEEP | Small, pure, auditable; general policy engines add surface without adding the effect/approval semantics. | — |
| Approval lifecycle | KEEP-WITH-CONDITIONS | Single use must be persisted (`consumed_at`, `consumed_by_effect_id`). | APPLIED (contract gap G4) |
| Audit trail | CHANGE | No tamper evidence. Hash-chain audit events and add `secma audit verify`. | OWNER (new requirement IDs) |
| Prompt-injection taint rules | KEEP-WITH-CONDITIONS | Mutating tool calls from a model are proposals only; never executed without the gateway. | Recorded |
| `policy.decision_ttl_s` undefined in RFC-014 | CHANGE | Added, default 60 s, range 10–300. | APPLIED |

### 3.3 Capabilities and protocols

| Decision | Verdict | Finding | Disposition |
|---|---|---|---|
| Home-grown search/describe/invoke meta-tools | CHANGE | Duplicates MCP tool discovery, Agent Skills and framework tool search. Keep only the effect/assurance metadata layer, which has no standard equivalent. | OWNER |
| Effect metadata file; effect gateway; assurance tiers | KEEP | The genuinely original and necessary part. | — |
| Skill naming and layout | CHANGE | Follow the published Agent Skills layout. | OWNER (RFC-015 §4) |
| MCP | KEEP-WITH-CONDITIONS | Hash tool definitions and detect drift before S04. | OWNER (new requirement) |
| A2A | KEEP | Disabled by default is correct; enabling by default would be dangerous. | — |
| Slack inbound through public webhook | CHANGE | Socket Mode by default: no public endpoint for a local-first product. | OWNER |

### 3.4 Agent runtime

| Decision | Verdict | Finding | Disposition |
|---|---|---|---|
| `ModelPort` | KEEP-WITH-CONDITIONS | Keep the port. Do not adopt LiteLLM (two PyPI compromises reported in 2026). | Recorded |
| Hand-built tool loop and output-repair ladder | CHANGE | Use Pydantic AI's iteration API, journal each step to the ledger, count validation retries inside the S00 8-request cap, confine imports to one adapter package. | OWNER |
| Pure reducer | KEEP | — | — |
| Behavior compiler | CHANGE | Protection flags are hard-coded dictionaries in `spec_tools/behavior_compiler.py`; `policy_ref` was a literal. Protection belongs in contract data and the compiler must fail closed. | APPLIED in part: `policy_ref` is now `trusted_policy/default@<sha256>`; protection flags remain in compiler code (LOG-0013) |
| Dependency pins | CHANGE | `pydantic-ai-slim 2.68.0` was uploaded 2026-11-12, three days before this review. No hash-locked lock file. Pin releases at least two weeks old and lock with hashes. | OWNER |

### 3.5 Commitment model, memory, communication

| Decision | Verdict | Finding | Disposition |
|---|---|---|---|
| Control table: goal change after work is ready | CHANGE (defect) | No `goal_revision` row from READY_TO_DELIVER, EVIDENCE_REVIEW, SEND_PENDING: a changed goal would be delivered stale. | APPLIED for the three states; ACKNOWLEDGED and IN_PROGRESS rows: OWNER |
| Control table: dead ends and unbounded loop (T1–T8) | CHANGE (defect) | See GUARD_PREDICATES §9. | APPLIED for T1–T4, T7, T8 (56 transitions, guards G25/G26 added with inferred clauses: OWNER confirms); T5 escalation bound stays OPEN (OWNER) |
| No requester acceptance after delivery | CHANGE | Delivery closes the commitment; the requester cannot reject. Published commitment theory (Winograd and Flores; Singh) has an explicit acceptance step. Add `ACCEPTANCE_PENDING`. | OWNER (new state; persisted shape) |
| No decline, counter-offer, or "who holds the ball" | CHANGE | The secretary cannot refuse or renegotiate; delay notices fire while waiting on the requester. | OWNER |
| Partial delivery closes the remainder | CHANGE | `partial → READY_TO_DELIVER` loses the open part. | OWNER (depends on acceptance state) |
| Memory quarantine | CHANGE (defect) | RFC-005 and M11 contradicted each other along a published memory-poisoning path. One fail-closed rule now. | APPLIED |
| In-house memory, 25 KB core block, M03 reducer, RFC-009 tiers | KEEP | — | — |
| FTS5 tokenizer `porter` | CHANGE | English-only stemmer in a multilingual product. Default `unicode61 remove_diacritics 2`. | APPLIED |
| Notification limits per commitment | CHANGE | Limits must be per recipient across commitments. | APPLIED |
| Reuse assessment (M21) | KEEP-WITH-CONDITIONS | Use OSV, deps.dev and OpenSSF Scorecard data with an offline snapshot. | OWNER (new detail) |
| Owner purge of memory | CHANGE | No way to delete poisoned or private content. | OWNER if it needs a new ID |

### 3.6 Evaluation, testing, delivery

| Decision | Verdict | Finding | Disposition |
|---|---|---|---|
| No conversational terminal session specified | CHANGE | `secma chat` added to M01, line-based, `--jsonl` scriptable, no state of its own. | APPLIED |
| Test plans named and placed before oracle tables existed | CHANGE | Plans realigned to the PRD oracle tables and real lanes. | APPLIED |
| Model gate "each scenario 30/30" | CHANGE | Statistically too strict to pass with a good model and uninformative when it fails. Pre-registered pooled rule (N=60, at least 58, zero safety violations, clustered standard errors, at most two declared candidates); paired McNemar non-inferiority for M27. | OWNER |
| Live-model gate blocks deterministic work | CHANGE | Deterministic tasks must not depend on S00-GATE-02. Walking skeleton first. | OWNER (DAG change) |
| No usable version control | CHANGE | Restore git from `source-history.bundle`; commits as checkpoints, annotated tags as seals. | OWNER |
| No lock file with hashes | CHANGE | `uv lock`, hash-checked, CycloneDX export. | OWNER |
| Test-suite guards | CHANGE | Timeouts, random order, network and model-request block, requirement markers instead of name matching. | OWNER |
| State-machine testing | CHANGE | Property-based stateful tests, exhaustive table explorer, enumerated crash points with integrity check. | OWNER |
| Mutation testing for `domain/` and `behavior/` | CHANGE | Coverage alone does not show the tests discriminate. | OWNER |
| "Test runner" as a model role | CHANGE | A script (`make gate`) is cheaper and cannot edit tests. | OWNER |
| Tiers L0–L5, injected clock, Typer, ADR-010, RFC-008 judge rules | KEEP | — | — |

## 4. Decisions waiting for the owner, ranked

1. **Restore version control** from the bundle before any more implementation.
2. **Walking skeleton and un-chained DAG**: one thin path `secma chat` → ledger → one
   effect → delivery through all layers before widening; deterministic tasks independent
   of the live-model gate.
3. **Requester acceptance, decline and renegotiation** in the control table. The persisted
   state shape must be decided before S00 ledger code is written, even if behaviour ships
   later.
4. **Adopt instead of build**: tool loop and output repair (Pydantic AI behind one
   adapter), RFC 8785 canonicalisation, standard JWT, Agent Skills layout, MCP discovery.
5. **Model gate statistics**: pooled pre-registered rule replacing "each 30/30".
6. **Hash-chained audit** with `secma audit verify`.
7. **Lock file with hashes; pins at least two weeks old.**
8. **Test-suite guards, stateful and mutation testing; runner as a script.**
9. **Slack Socket Mode; MCP drift detection; M21 data sources; memory purge.**

## 5. What stays blocked regardless

- S00-GATE-02 needs a separately verified, approved real model endpoint.
- No independent semantic review of the rewritten PRDs has been performed by a party other
  than the authoring agents.
- There is no gate-promotion tool; no slice status may be inferred from this document.

## 6. Evidence status

Checked by the root against primary sources or local files:

- WAL-reset bug range and fixed versions (sqlite.org/wal.html); `synchronous=NORMAL`
  durability note (sqlite.org/pragma.html); CPython 3.14 bundles SQLite 3.50.4
  (CPython `PCbuild/get_externals.bat`); local Python 3.13.7 links SQLite 3.46.1.
- `pydantic-ai-slim 2.68.0` upload time 2026-11-12 (PyPI JSON).
- DBOS issue #940 closed 2026-11-09.
- Local: ADR-015 lines 25, 78–79, 84; absence of `synchronous`/autocommit rules; control
  table gaps; RFC-005 rule 3 versus M11 lines 15, 92, 93; no `uv.lock`, zero hashes in
  `requirements-lock.txt`; linear work-package chain; hard-coded protection in
  `spec_tools/behavior_compiler.py`; canonical bytes in `src/secma/application/identity.py:56`.

Reported by secondary sources only: the two 2026 LiteLLM PyPI compromises.

Not checked by the root (treat as reviewer claims): Pydantic AI feature details; MCP
2026-07-28 revision details; 2026 JOSE CVEs; Windows Task Scheduler defaults; DBOS version
numbers; `uv` flag names; the evaluation review's version and date tables.

## 7. Closing addendum: open items after integration (2026-11-15)

The integration pass ended with `validate_spec.py` PASS, `validate_readiness.py` PASS
(243 requirements, 243 plans, 101 shared cases, 125 fixtures, 35 work packages) and
`143 passed` in pytest. These are L0 specification checks only; they prove no runtime
behavior. The items below were found during integration and were **not** decided,
because the specification is silent or the choice belongs to the project owner. Each
is tracked in `docs/governance/LOG.md` (LOG-0013, LOG-0014).

### 7.1 Inferred text that the owner must confirm

| Item | Where | What was inferred |
|---|---|---|
| Guard G25 `provider_proves_no_effect` | `docs/architecture/GUARD_PREDICATES.md`, `contracts/guard-registry.json` | Clause "attempts >= max_delivery_attempts"; the resulting block is not resumable unless another effect is still UNCERTAIN |
| Guard G26 `acceptance_block_resolved_authorized` | same | All clauses; denial code `INVALID_INPUT`; target CLASSIFIED |
| `merge_feedback` on a new goal | same | Stops every COMMITTED effect; from SEND_PENDING the commitment takes the cancel path and the requester resubmits |
| `model-competence` measured block | `contracts/model-competence.schema.json` | Nesting of `per_metric` and shape of `confusion_matrix` |
| Policy sections | `contracts/policy.schema.json` | Numeric bounds; `causal_lexicon` as a flat list |
| PostgreSQL isolation, scheduler unit types, M06 `horizon_s` | RFC-003 §10, §12; `docs/prds/M06.md` | `READ COMMITTED`; systemd `Type=oneshot`; horizon = deadline minus acceptance instant |
| Planned test files for M11–M20 and K/SH derived IDs | `docs/testing/REQUIREMENT_TEST_PLANS.json` | File names follow `tests/<lane>/test_mNN.py`; 23 K/SH IDs have no oracle table |
| SUF-02 planned path | `docs/testing/TEST_CASES.md` | Moved to `tests/integration/test_quality.py::test_suf_02`, tier L2 |

### 7.2 Open specification questions (no change made)

1. T5: bound for the BLOCKED `deadline` loop (default, per-commitment counter, behavior after the last escalation).
2. `goal_revision` rows for ACKNOWLEDGED and IN_PROGRESS.
3. `docs/prds/M09.md` line 80 says `reinvestigation_budget` is 0–5; the schema allows 0–10; whether the control-table `budget.max_reinvestigations` field stays.
4. Profile vocabulary: M28 and `LifecycleReport.profile` use LOCAL_DEV / ENTERPRISE_HA; RFC-003, M01 and the TRD use LOCAL / SERVER.
5. `docs/prds/M08.md` lists `timeout_seconds` 30 under `Budget`; TYPE_CATALOG `Budget` has `deadline_at` only.
6. DUR-09 fault "kill the process during a checkpoint" has no meaning in TRUNCATE mode; SUF-01 shares the deterministic M09-AT-02 oracle but stays in `tests/evals`.
7. ADR-016 mentions launchd `StartCalendarInterval`; RFC-003 §12 says `StartInterval`.
8. Record field lists still undefined in TYPE_CATALOG: DataQualityRecord, LifecyclePort arguments, AuditFilter, AuditEventView, EffectivePreferences, ValidationReport, RenderedPayload, EventRef, `ModelResult.provider_snapshot_id`, the M09 claim carrier, `RankReasons.filter_results` element, WorkSnapshot open-question names; `Space` has no language attribute (needed for the English-only `porter` option); depth/document/byte budgets belong in `discovery_policy`, not `Budget`.
9. Contract schemas still behind TYPE_CATALOG: `CONFIG_INVALID` in the `Error.code` enum of `contracts/runtime-boundaries.schema.json`, BrainDocument freshness, the ExecutionStatus enum, DoctorReport (no schema), `rank_reasons` wire shape.
10. Work-package DAG: S04-T01 depends only on S02-T05, so the S03 and S04 chains overlap on owned paths; no S02 task owns `src/secma/cli`; M02-AT-02 is first exercisable in S05 but owned in S07; IDN-10 LOCAL legs are in no S00 task.
11. Items that need new requirement IDs: owner purge of memory (conflicts with M11-FR-03), a sixth M05 detector for intent alternatives with divergent effects, a PostgreSQL write-skew DUR case, the M30 "compiler rejects shortlist > 5" rule.
12. RFC-011 has no Status line; RFC-013 and RFC-014 are PROPOSED while ADR-013..016 are accepted.
13. `evidence/SPEC_AUDIT_SUMMARY.json` still says 240 requirement rows; it is hashed evidence and was left untouched.

Items 8–10 must be closed in the specification before the work package that consumes
them starts (AGENTS.md rule 8); none of them blocks S00-T01..T02.

