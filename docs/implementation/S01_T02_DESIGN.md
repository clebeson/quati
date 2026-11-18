# S01-T02 discovery and design

Status: SDD candidate, not independently specification-ready. No T02 runtime or test source
exists. Canonical state controls progress. Predecessor T01 contribution accepted
and pushed at 8706018; full S01 gates remain NOT_RUN.

## Exact scope

Local A01 optional preference does not block authorized read discovery; A02
ambiguous authority stops unsafe dispatch; A03 no fabricated receipt. INT-01 and
INT-02 remain CONTRIBUTION_ONLY; their real-model full proof belongs to T04.
No full requirement plan is owned by T02. T03 owns follow-up, async isolation and
bounded role fallback. S02 owns durable ledger, timers, approval and delivery.

T02 consumes T01 typed classification and policy reducer, constructs ModelResult,
reference resolution, clarification, first USER_TURN WorkSnapshot and M03
InteractionDecision through existing ask/chat. No production access or live write.
The read-only effect ceiling remains enforced independently of model proposals.

## Discovery findings requiring specification resolution before code

| ID | Observed inconsistency or missing boundary | Proposed consuming resolution / owner |
|---|---|---|
| G01 | T02 owns only application/unit/evals, but M05 is pure domain and assertions require public deterministic CLI paths. Planned local assertions point to evals despite contribution-only ownership. | Expand exact domain/CLI/fixture/integration ownership and move only local assertions to a distinct integration basename; retain all T04 L3 cases and thresholds. |
| G02 | M05 C4 excludes route ask, yet its following normative paragraph requires C5/C6 for ask without a missing blocking field. | C4 permits start_safe_work and ask; safety and missing-field rows still precede it. |
| G03 | M05-FR-03 still demands SQLite in S01; runtime contract stages ephemeral work in S01. | S01 ephemeral oracle, separate mandatory S02 SQLite proof; T03 owns repeated-answer behavior. |
| G04 | M08 budget says 8 tools / 30 s, while authoritative boundary says 6 tools / 30 s HTTP or 180 s CLI. | Preserve stricter shared boundary, including repair and retry accounting; no increased budget. |
| G05 | M04 temporal catalog is said to live in behavior policy but no such field exists; requester timezone has no source. Future candidate timestamps can make recency exceed 1. | Define versioned English/Portuguese catalog and trusted timezone source, explicit assumptions/default, temporal ambiguity behavior and bounded recency before scoring. |
| G06 | First WorkSnapshot lacks request text, language, validated binding/missing-field facts and provenance; M05 refers to context outside its signature. | Specify typed trusted snapshot inputs and which producer supplies each field. Do not infer identity, authority or deadline from model prose. |
| G07 | M03 consumes M06/M09 before those modules ship. | Real minimal USER_TURN communication calculation only; unsupported timer/result inputs typed unavailable until their owning task. Never fabricate a later-module verdict. |
| G08 | InteractionPort apply vs CLI receipt acknowledgement, conversation CAS, ephemeral work creation and idempotency replay are underspecified together. | Single-owner staged application transaction, publish projection/work only at declared acknowledgement; no durable promise. Define retry/fault truth when a read already happened. |
| G09 | M05 eligible safe work is needed before M03 D8, while capabilities are discovered dynamically by the model. | Define exact timing of search/describe, selected trusted registry effects, M25 pre-authorization and actual read observation. No automatic invocation of every catalog reader. |
| G10 | Direct informational ANSWER is permitted, but BUG-2026-002 forbids trusting a simple_answer label/prose as completed investigation. | Code-owned social/work/receipt messages; no model text as completion proof. Bound informational output and use explicit uncertainty when trusted answer context is unavailable. Preserve old protected negatives. |
| G11 | Strong routes require qualification, while fallback is T03 and MOD-01 is not complete. | Keep unqualified/unavailable roles blocked; separate recommendation, current selected provider and later fallback. No fabricated competence. |
| G12 | Decision sidecar loader/compiler exists but runtime does not install, consume or bind it. | Explicit init installs defaults without replacing existing operator files; missing/invalid configured policy fails closed before dispatch; compiler receipt binds validated hash. |
| G13 | Language selection/detection and question/contact templates have no exact consuming wire. | English/Portuguese only, deterministic selected/detected language with versioned templates; no GUI or hidden preference persistence. |
| G15 | M05 C3 requires escalation but M03 D3 would ask again. | Add D2E before D3; keep deny/escalate precedence and classification unchanged. |
| G16 | M05 C1 could block optional work, and its question limit is absent from the row. | Apply C1 to missing blocking fields only; skip repeated optional questions and use C6 safe start. |
| G14 | LOG-0061 input/error mapping and future concurrency preconditions remain open. | Validate typed trusted capability sequences and map context serialization errors before public use; retain T03 concurrency ownership. |

Additional consuming findings resolved in the SDD candidate:

- G17: M03 escalate copied a free model reason; use code-owned TRIAGE_ESCALATED
  and hash the raw reason. Public messages/metadata never copy that prose.
- G18: missing authenticated tenant/principal must be rejected by M02, not asked
  as if a valid work identity existed. Only missing work scope reaches M05.
- G19: a candidate cap of one could hide ambiguity. Minimum is two; compute verdict
  before display truncation and pass exactly displayed plausible refs to M05.
- G20: safe_work_allowed=false lacked an explicit M05/M03 consuming veto path.
  C4 returns NO_WORK and D7V handles it without accidental D0 or execution.
- G21: a quoted inaccessible ref with a non-null model hint is UNRESOLVED, just
  like an unknown ref, not a special private-existence signal.
- G22: unavailable reference context cannot prove that no old work exists. Return
  typed unavailability when required context cannot be established.
- G23: S00 registry admission before every model call conflicts with CAP-04's
  independent informational path; split converse/classification from source/tool
  admission while preserving each source's ACL/audit checks before access.
- G24: current product languages are English/Portuguese. Validate the configured
  fallback primary subtag and bind code-owned locale/template catalogs.
- G25: AskSession counts logical calls, while Provider.complete can issue several
  transport attempts up to its larger own limit. The new run-bound budget must
  count attempts and recheck timeout on each retry without altering probe identity.

The SDD candidate runtime contract now gives concrete dispositions for G01-G25;
independent review and exact transitive-source checks remain before SPEC_READY.
No T02 tests or implementation source have been authored.

## Existing seams and reuse

AskSession owns classification repairs, shared request/time budgets, discovery tools
and evidence. CLIService.ask authenticates, validates state/authorization and
records the receipt; its conversation projection publishes only after sink success.
composition.ask_runtime creates registry/discovery and compiles the behavior prompt.
BehaviorCompiler already accepts a validated DecisionPolicy and binds its hash.
LocalPolicyGate remains the effect ceiling; no new provider or alternate auth path.

The ripwire pack-task conceptual ranking primarily found statechart/compiler/trace
symbols, not an existing clarification implementation; direct reads confirmed no
M03/M04/M05 runtime. Do not invent a microservice, queue or new command to bridge it.

## Design readiness

The candidate resolves G01-G25 in authoritative PRDs/runtime contract/type catalog/task ownership
before test or implementation code, subject to independent retest. It defines lifecycle/receipt failure ordering,
all supported reachable decision tuples, deterministic positive/negative/fault
observations and public CLI fixtures. Root authors kernel tests first, Haiku runs
red/green, a fresh bounded Sonnet review checks conformity and selects new attacks.
No S01 gate, live integration or production readiness follows from this discovery.

## Visited sources and limits

Input hashes: evidence/S01/T02-2026-11-18/input_snapshot.json. Read task/DAG,
canonical state, governance, M03/M04/M05/M08 and relevant M06/M09/M31 boundaries,
INT-01/INT-02/CAP-04, fixture recipes, schemas, existing ask/CLI/composition seams,
legacy DEC-001/LESSON-001/BUG-2026-002 and current LOG debt. DEC-001 is historical:
current implementation authorization supersedes its specification-only mode.
Relevant M31 envelope/fallback and M06 USER_TURN/timing sections were re-read;
implementation bodies not fully read must be inspected before modifying them. No production/provider operation ran.

## Initial specification corrections

G02/G03/G04/G15/G16 have consuming specification fixes: ask is eligible for safe
start when no blocking field is missing; S01 clarification uses ephemeral records;
M08 uses the shared six-tool / HTTP-30s / CLI-180s envelope; M03 D2E escalates
re-ask exhaustion; open optional questions cannot halt authorized read work. These
are specification-only changes, not runtime behavior or proof. All dispositions are now in the SDD candidate contract; independent review and
corrections remain mandatory before tests or source.

## Candidate disposition

S01_T02_RUNTIME_CONTRACT now specifies policy installation/binding, typed snapshot
producers, code-owned locale/uncertainty, read-only admission, raw retry budgets,
M03 E1/D2E/D7V, joint publication/replay and bounded ephemeral state. Authoritative
PRDs, type catalog, candidate-cap minimum and task/local-test ownership have been
updated consistently. Independent SDD review must still challenge lifecycle
ordering, producer-error precedence and scope before SPEC_READY is recorded.
