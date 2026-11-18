# S01-T02 consuming runtime contract

Status: corrected SDD candidate; focused independent retest required before
source. Canonical state is SDD; no T02 runtime or test source exists. This document supplements S01_RUNTIME_CONTRACT, M03/M04/M05/M08 and
the JSON contracts. It authorizes no effect, release or production access.

## 1. Public scope and proof

Deliver the initial admitted USER_TURN path through existing quati ask/chat:
normalized classification, reference resolution, selective clarification, authorized
read discovery, exactly one M03 decision and a receipt-coordinated ephemeral turn.
T02 does not deliver follow-up updates, async execution, timers, role fallback,
durable commitments, approvals, delivery or a new command. T03/S02 retain those
owners. INT-01/INT-02 local assertions use deterministic integration tests; their
full L3 cases and all thresholds remain T04-owned and unchanged.

Missing authentication is rejected by M02 before M03, model or source lookup.
Invalid behavior/decision policy is rejected before business admission. These
refusals do not invent a conversation owner or an accepted business turn.

## 2. Policy and model boundaries

Explicit quati init installs the packaged decision-policy defaults into the LOCAL
configuration directory only when the sidecar does not exist. It never replaces
an existing valid or invalid operator file. Existing profiles can run init again
to install the missing sidecar. Installation uses the existing private-directory,
locked atomic-write and fsync primitives, with named fault points; partial failure
is explicit and retryable, never a successful configuration claim.

Runtime reads a regular, non-symlink, owner-matching 0600 sidecar with the existing
secure snapshot/loader checks. Missing, unreadable, malformed or invalid bytes
produce CONFIG_INVALID before dispatch; no implicit runtime defaults. The loaded
DecisionPolicy hash is bound by BehaviorCompiler and recorded in every triage and
interaction receipt. Authorization policy_version remains separate.

Reuse the T01 pure reducer after the real structured-output ladder. Record raw
proposal hash and normalized classification hash separately. The public normalized
projection has stage POLICY_APPLIED and code-owned reason text; optional presence
is preserved and any present model commitment_ref is null in public output. Raw
model strings are retained only through hashes or approved synthetic evidence.

The optional context_policy section uses its documented schema defaults when
absent; present lower limits are honored. Defaults never replace a missing sidecar.
A selected default language must have en or pt as its primary BCP-47 subtag;
unsupported configured languages are CONFIG_INVALID in the current local profile.

The selected default provider remains the explicitly configured, feature-probed
provider. Computing a model_role is not a qualification or an autonomous switch.
T02 never dispatches a strong-role recommendation to an unqualified/missing role:
render an honest code-owned blocking question/denial/escalation where applicable,
and otherwise BLOCKED NOT_CONFIGURED ESCALATION_UNAVAILABLE, without another
model or discovery call. T03 owns qualified-role selection and bounded fallback.

Provider.reset_run binds a per-turn request/deadline budget without changing the
provider configuration or its probe key. Count raw transport attempts, including
429 retries, separately from logical complete calls; recheck remaining deadline
and timeout before every transport attempt and before a retry delay. A provider's
larger configured budget cannot override the turn's eight-attempt cap. This
closes the observed wrapper-count versus transport-retry gap before runtime use.

The shared envelope remains at most 8 provider requests including retries/repairs,
6 tool calls, 2048 output tokens per request, 30 seconds HTTP or 180 seconds vendor
CLI. All checks use the injected clock and run before the affected call. A lower
configured bound wins. The raw-attempt cap is min(8, config.max_requests). Expose
actual provider attempt count to AskSession/Usage rather than substituting the
logical call-list length. Inject retry sleep together with the clock in tests;
recompute timeout=min(configured timeout, remaining) on every raw attempt and
reject a delay beyond the remaining deadline. Assert config_hash/probe key is
unchanged by run-budget binding. No new provider, transport or raised budget is introduced.

## 3. Typed snapshot and trust

WorkSnapshot gains explicit request_text, language, requester_timezone,
request_body_hash, clarification_inputs, read_observations and model_result fields.
It retains event_source, work_ref/work_revision/state and the independently
produced resolution, clarification and plan. USER_TURN classification is passed
alongside; non-user event types remain unavailable on the public T02 path.
When a required producer fails, dependency_error is a typed code-owned error and
its unavailable verdict field is null; M03 E1 handles it after deny/escalate.
No producer result is fabricated merely to fill the snapshot. Fields unused by
an already decisive deny/escalate row are explicitly not evaluated. Normal
decision rows require their actual producer inputs; malformed normal snapshots
are INVALID_INPUT, not a permission or a successful default decision.

ClarificationInputs contains trusted normalized facts, not another model response:
effect_class; approval_valid; selected_capability; recipient_required/recipient_bound (null until selection); scope_missing;
deadline_unresolved; optional_missing fields; open question fields; per-field ask
counts; and question_already_emitted. The application obtains these from the
current authenticated context, registry schema/effects, M25 decision, deterministic
temporal resolver and ephemeral work state. Missing tenant/principal is never
converted into scope_missing. M05 consumes these inputs and never authorizes.

EligibleRead carries capability_ref, trusted registry effect and the observed M25
allowance for the exact input/binding. Write, dangerous, unknown, denied or
unavailable entries never enter safe_work. A label such as proactive research is
irrelevant. Context serialization errors and malformed trusted capability
sequences are mapped to typed INVALID_INPUT before use (LOG-0061).

ModelResult contains actual text, normalized classification, structured tool
observations, measured usage, effective prompt hash, observed model/provider/config
identity, observed feature report and evidence refs. Text is untrusted and never
establishes authority, completion or delivery. Unknown usage/cost stays null.

## 4. Reference resolution and locale

M04 runs its social/simple_answer guard before candidate retrieval. Every other
source is queried with the authenticated context. Filter tenant/actor/ACL before
validation, scoring or trace publication. Current S01 sources are the ephemeral
session's own work/turns and explicitly installed synthetic artifacts; no cross-user
or memory-service search is implied. A source outage is reported as an assumption
and typed unavailability when required context cannot be established, never proof
that no prior work exists.

Candidate ref/title/owner/space/observed_at are typed source data. Require an aware
observed_at not later than injected now; invalid source times are omitted with a
generic assumption after ACL filtering. Compute exact_id, NFKC-casefolded title
overlap, temporal window, ownership and nonnegative recency per DECISION_RULES,
with Decimal weights and half-even four-place rounding. Determine plausibility,
ambiguity and top-two gap before truncating the displayed plausible list. The
candidate cap is at least two; omitted items cannot manufacture RESOLVED. Pass
exactly displayed plausible refs to M05 and disclose truncation generically.

The supported versioned English/Portuguese catalog contains ISO dates, today/hoje,
yesterday/ontem, this week/esta semana, last week/semana passada, this month/este
mes and last month/mes passado.
Accented Portuguese aliases (este mês, mês passado) are explicit entries;
normalization does not silently remove accents from arbitrary request text.
Windows are half-open, in the trusted requester timezone, ISO weeks start Monday.
Conflicting temporal windows or an unsupported required relative deadline are
unresolved rather than guessed. Missing source context or unresolvable reference
scope blocks a target-specific read and yields one focused question/unavailability.

The CLI may select --language en|pt and --time-zone with a validated IANA name for
ask/chat. Otherwise language is detected using a versioned English/Portuguese
word catalog, falling back to behavior_policy.default_language; timezone is UTC
with explicit TIMEZONE_DEFAULTED_UTC assumption for relative expressions. These
are process/request settings, not learned or persisted preferences. Catalog and
template identities are bound by code_digest. Other languages are not emitted.

## 5. Selective questions and read discovery

M05 checks the five blocking fields in configured order, including the corrected
C1/C4 rules. A model ask without a blocking field can start safe reads. An open
optional question does not halt reads; no second question is emitted this turn.
A read-safety veto remains a veto: NO_WORK is consumed by M03 D7V, rather than an
accidental D0 or an invented permission. Exhaustion is consumed by D2E.

Classification does not require a registry catalog query. After identity/converse,
configuration, receipt and feature-report admission, build its protected envelope
without reading source/tool state. Only a route needing reference/tool data runs
registry/ACL/audit/package admission before that access. Thus an unavailable tool
subsystem cannot block the direct informational path; it cannot bypass source ACLs.
Context.to_wire is validated and mapped to typed errors before use, but credential
metadata is not added to the model-visible envelope just to exercise serialization.

M05 evaluation has two unpublished phases. Phase 1 uses only knowable facts:
M04 target scope, stated deadline, authenticated work scope, question counters,
and the M08 code-derived intent effect floor. In particular external_action has
floor write even before a capability is chosen, so S01's absence of a verified
approval blocks it immediately. Recipient facts are not invented before selection.
M03 still emits exactly one final decision.

Phase 2 uses the actual selected, permitted registry entry/schema and bound input.
SelectedInvocationFacts is generated by DiscoveryTurn after context/shortlist/
registry checks; no facts are fabricated for a hidden or unselected ID. A missing
critical argument refusal may carry these facts with policy_verdict=null, never
an ALLOW. EligibleRead exists only after real M25 allowance for valid bound input.
Add a deny-only per-DiscoveryTurn invocation guard after ordinary authorization,
registry, schema and M25 checks and before a handler. It returns only null (no extra veto) or InvocationVeto (stop); invalid return
values fail closed. It cannot replace an ALLOW, modify arguments/scope or turn a
DENY into an ALLOW. The callback is bound to this DiscoveryTurn, not mutable
shared-service state. It re-evaluates M05 with
immutable selected facts and stops on a critical veto before the handler. A known
selected entry with a missing critical argument is already refused by schema;
the loop stops and uses that typed refusal's trusted selection facts for the one
final M05/M03 decision. Repairable model syntax/describe errors retain the bounded
repair ladder; missing user facts are not silently guessed.

Never query a hidden/not-shortlisted ID merely to learn its effect. Such a
proposal remains indistinguishable from an unknown ID, takes the existing refusal
and code-derived dangerous-effect escalation, and executes no handler. A known
non-read selection blocks without a handler; an unknown selection escalates rather
than pretending a known email capability or approval requirement was observed.

The application performs M05 blocking preflight before discovery. Search/describe
are read-only discovery, not acceptance or execution of every reader in a catalog.
Only the model's actual selected invocation is considered; existing shortlist,
describe, schema, ACL, registry and M25 guards still run before the handler.
Required missing arguments cannot reach a handler. Every selected effect is
checked against the normalized route and the protected read-only ceiling.

If phase 1 is deny/escalate, ASK_BLOCKING, WAIT_OPEN_QUESTION or NO_WORK for a
start/ask route, issue no discovery tools or capability reads. D6 context/status
reads are distinct from safe-work creation and may run with M05 NO_WORK. A
blocking reference query itself remains ACL-filtered M04 work, not a capability
invoke. A later phase-2 veto stops all further discovery/model calls; earlier
authorized reads cannot be undone and remain visible in read_observations and
work_performed. For T02 public D3/WAIT/ESCALATE, prospective safe_work is empty;
parallel read starts on an already blocked turn are deferred. Thus tool_calls=[]
is required for an early blocking turn, not falsified after an actual earlier read.

The synchronous T02 path records actual selected read attempts and their trusted
policy/result observations, then produces one final M05/M03 decision. No second
M03 decision is emitted for the same inbound event. safe_work identifies the
selected authorized reads for this turn; apply never re-executes an observed read.
No unknown or model-labelled safe action is scheduled. Failed reads remain failed;
zero verified steps cannot produce a completed-step message. The first work record
may remain BLOCKED with explicit next action, retaining its process-only owner.
T03 owns execution that remains pending while another user turn arrives.

## 6. Interaction, receipt and publication

The session owns one immutable published aggregate: conversation projection,
logical work records, bounded recent turn summaries and replay results. The
projection itself retains only ID/owner/revision; the new ephemeral store is a T02
capability, not a claim that all session memory stays constant-space. Credentials
and raw model transcripts are not stored. The code-owned prototype constants are MAX_SESSION_TURNS=1000 and
MAX_SESSION_WORKS=20, both recorded in receipt limits. After current authentication
and replay lookup, check the turn quota before a model call. Check the possible
new-work quota after classification/reference/phase-1, before capability effects;
work need is not known before classification. Reserve no published slot or ID at
these checks. Only acknowledged D8/D9 and nontrivial D3 allocate work; a D3 is nontrivial
exactly when normalized classification.work_needed is true; D1/D2/E1/
D5/D6/D7V and WAIT do not. A discarded candidate consumes no quota or replay entry;
unpublished generated IDs may be skipped, never returned as accepted work.
A quota refusal is receipted and advances only the projection (as a failed ask),
not accepted-turn history/work/replay capacity; no key is silently evicted.
Turn exhaustion is a pre-business refusal (no M03 decision). Work exhaustion
substitutes E1 dependency_error=WORK_QUOTA_EXCEEDED only when this turn would
allocate a new work record. A D5 answer or trivial D3 still runs at a full work
quota; an existing binding consumes no new slot. Replay precedes both quota
checks and remains available after exhaustion. No new question/work is emitted
on a quota refusal.

InteractionPort is bound to the trusted owner/session. decide validates its
snapshot and emits the M03 first-match result, including E1/D2E/D7V. Its table reducer
is pure; the application may retain a non-published prepared decision/snapshot for
apply, but decide performs no I/O or published business-state write.
apply checks the same owner, request/decision body, expected conversation revision
and idempotency key. Same scoped key and body returns a fresh copy of the stored
TurnResult unchanged before CAS; a different body conflicts without effects.
Replay writes no new request receipt, advances no revision and reuses the original
receipt reference. Current access is rechecked (security audit may record that
check); no new business turn, model or read occurs. Fresh CLI request IDs mean
replay proof is at the public application contract, not claimed from duplicate
plain-text CLI lines.
The orchestrator performs request replay lookup before model/discovery so that a
replay does not repeat a read. Authentication and current scope are rechecked.
The canonical request body includes owner, text, selected locale/timezone, bound
work and current policy/provider/build identities; ephemeral credential/trace IDs are not business
content. Cache disclosure requires current access to all recorded source spaces.
A returned mutable Response cannot mutate the stored replay (store immutable bytes
and return a fresh decoded value).

Reuse/extract the existing application receipt coordinator. Prepare a candidate
aggregate and exact public response, including the projection metadata for chat,
before hashing. Write the receipt; only after acknowledgement publish the whole
aggregate with one assignment and return TurnResult. Re-entrant/in-flight apply
is rejected before effects. No callbacks or I/O occur inside publication. On sink
failure discard the candidate: no conversation/work/replay advance or success
response. An already executed authorized read is disclosed conservatively by the
existing receipt_not_written failure; retry may repeat that read, never an external
write. Process death loses S01 work, including after a receipt file was written.
No source describes this as crash durability.

TurnResult is an application record whose response is the ordinary CLI Response;
it is not recursively embedded inside its own response. Public data carries the
InteractionDecision, turn_id and work_ref plus the existing outcome fields.
commitment_id stays null, launched/delivered stay false in S01, and every work
reference explicitly says PROCESS_ONLY / no continuation after exit. One-shot
requests expose no data.conversation; their internal session still scopes a turn.

## 7. Messages and missing dependencies

All social, question, receipt, start, progress and blocked-work text is versioned
application-owned English/Portuguese template text from observed facts. Public
reason codes are code-owned tokens; raw classifier reason strings are hashed.
No model completion claim is copied into a message, reason or receipt field.
Only the existing code-owned social table yields a successful GREETING. A model
social label outside that table uses the bounded uncertainty path, never turns
request-bearing text into a successful greeting. T02 provides no trusted answer
context for D5. Every non-code-social D5 takes the uncertainty path: BLOCKED
EVIDENCE_INSUFFICIENT with no work/performance claim; model ANSWER prose is never
displayed. Verified read observations belong to D6/D8/D9, not D5.

ANSWER permits bounded informational content but grants no completed-work status.
Without trusted answer context, T02 emits a concise code-owned uncertainty statement
with no tool/job and no successful work claim; it does not present unchecked model
prose as completed investigation (BUG-2026-002). CAP-04 explicitly permits this
uncertainty outcome. No broad general-knowledge answer engine is claimed by T02.

The initial USER_TURN communication calculation is a real deterministic subset of
M06: receipt/question kind and next_contact_at from injected now, configured delay
and resolved business deadline. It schedules no timer or delivery. M09 judgments,
async results and timer events remain typed unavailable until their owning task;
missing producers are never replaced with fabricated normal verdicts.

## 8. Tests and retained proof

Root writes discriminating unit/table/boundary tests before implementation. Cover
all routing/clarification/ERI combinations, reachable-tuple consistency, ACL-before-
score, Decimal/timezone/tie/truncation edges, scope/approval/recipient/deadline
questions, raw model reason/message attacks, state CAS/replay immutability,
receipt faults and publication quotas. Public local assertions live at
 tests/integration/test_clarify_cli.py::test_optional_preference_does_not_block_research,
 test_missing_tenant_or_approval_blocks_write and test_faults_never_fabricate_progress,
respectively. These reuse the descriptive M05 oracle functions, not duplicate wrappers.

The new prd-read fixture reads one of two actual synthetic PRD texts and computes
missing required heading gaps from the text, binding each check to the document
hash; it does not look up a canned oracle answer. Its preferred_format input is
optional. The mail-send fixture is explicitly synthetic and must never execute
under the S01 read-only ceiling; no network sending integration is implemented.

A01 uses actual CLI plus scripted provider and real synthetic read capability:
optional format absent, one authorized read, non-blocking question/receipt and
process-only work. A02 covers external-action confirmation, missing work scope,
missing authenticated identity and privilege-smuggling, all with zero write calls.
A03 injects source unavailability and receipt failure, preserving truthful blocked
state/owner and no fabricated completion or acknowledged work after sink failure.

No deterministic fake qualifies a real model. Fresh bounded Sonnet SDD/code reviews
are independent of implementation, choose additional negatives and verify fixes.
All coverage thresholds, public-path regression checks and T04 L3 cases remain.

## 9. Exact locale and regression rules

Locale catalog version locale-catalog/1 tokenizes NFKC-casefolded alphabetic words
without modifying raw request bytes. Explicit selection wins, then a code-owned
social match, then the larger distinct word-set intersection below; a tie or no
match uses the validated default primary subtag and records LANGUAGE_DEFAULTED.
English words: the, please, review, summarize, send, include, what, does, is, my,
last, week, format, hello, thanks, deadline. Portuguese words: por, favor, revise,
revisar, resuma, resumir, enviar, envie, inclua, que, meu, minha, semana, formato,
olá, obrigado, prazo, lacunas, isto, esta. This is bounded deterministic detection,
not an empirical universal language claim. Temporal aliases are separate from
intent classification and never create work by keyword.

Existing regression expectations may change only for the explicitly staged public
policy/interaction fields, declared opaque IDs and the new zero-tool informational
uncertainty path. Normalize IDs only after checking their scope, stability and
revision; verify receipt output hashes before normalization. Do not strip status,
permission, model identity, provider errors, observed effects or work/delivery truth.
Source/tool admission is now after classification where needed, so an authorized
converse classification may occur even when a later registry lookup is denied;
that denial still has zero registry content reads or capability effects. Missing
authenticated identity/config/receipt safety still yields zero model calls.

The new synthetic PRD reader and denied synthetic mail sender are local fixtures,
not a real repository/email integration. A reader's gap output is computed from
actual supplied fixture content and independently verified; a canned result keyed
to the expected test answer is not acceptable evidence.

## 10. Reachability and outward behavior

| M03 row | T02 application behavior |
|---|---|
| D1 | Code-owned behavior-policy veto; no tool/handler call. |
| D2 | Code-owned escalation/deferred notice; no human notification or new provider role. Preserve an actual classifier/provider error when present. |
| E1 | Typed missing required producer or unsupported owner behavior, never a fabricated verdict. |
| D2E | Pure rule implemented/tested; answered-field failure counters are T03-produced, so no claim of a completed T02 answer/re-ask workflow. |
| D3 | One blocking question; empty prospective safe_work; new process-only work only for a nontrivial turn, if quota and receipt succeed. |
| D4 | Existing verified own question remains open; WAIT with next_contact_at, no re-ask/read/work revision. State explicitly that answers are not consumed in T02. |
| D5 | Trusted social preflight or code-owned informational uncertainty; no source/tool call or new work. |
| D6 | Context lookup uses the existing bounded read loop; status_query reads only verified own session work, never creates/revises work. Unknown/missing status context yields typed uncertainty, no invented status. |
| D7 | Pure rule retained, but T02 does not apply WORK_REVISED. Preflight marks FOLLOW_UP_NOT_IMPLEMENTED dependency_error before discovery; E1 gives a truthful refusal. Work revision stays unchanged; a newly receipted refusal may advance only the conversation projection. |
| D7V | No safe-work permission: explicit blocked escalation, no tools or new work. |
| D8/D9 | Initial synchronous authorized-read work only, observed facts and process-only ownership; no background worker. |
| D10-D14 | Not admitted by the T02 public profile; typed UNSUPPORTED, no fabricated M06 timer/M09 assessment/delivery. Pure table enumeration is not runtime proof for them. |
| D0 | Fail-closed incompatible/future tuple. Assert that every supported producer-built T02 snapshot selects a specific non-D0 row. |

A code-owned social-table match supplies exactly this trusted preflight before M03:
intent=social, work_needed=false, complexity=trivial, risk=none, uncertainty=low,
safe_work_allowed=false, next_action=respond, reason_code=PREFLIGHT_SOCIAL; optional
fields absent. It passes the M08 pure policy pass, has provenance CODE_SOCIAL_TABLE,
no ModelResult and zero provider calls. Its successful receipt counts toward turn
quota and advances the projection exactly like any newly receipted ask.

The default provider's prototype eligibility is the fixed operator-selected role
with the existing exact-config feature probe. It is not an EVALUATED competence
claim and enables no autonomous model-role switch. Record semantic qualification
as NOT_VERIFIED until the required actual-model proof. Any non-default role needed
for another model/discovery call is unavailable in T02: E1 dependency_error
ROLE_NOT_QUALIFIED, outer BLOCKED/NOT_CONFIGURED and template
ESCALATION_UNAVAILABLE (result_kind=BLOCKED). Code-owned blocking
questions/denials need no further model role and retain their earlier safety row.
T03/MOD-01 owns qualification/fallback; T04 must requalify current source.

| Decision / observation | Response status; error | result_kind / template | Work/effect truth |
|---|---|---|---|
| D1 veto | DENIED; FORBIDDEN | BLOCKED / REQUEST_NOT_PROCEEDED | No new work or effect; code-owned behavior veto, no fabricated M25 decision. |
| D2 after classifier/provider error | Original typed BLOCKED/UNAVAILABLE and actual error | BLOCKED / MODEL_UNAVAILABLE | No read/new work; preserve actual error and fail-closed classification. |
| D2 without provider error | BLOCKED; UNSUPPORTED | BLOCKED / ESCALATION_UNAVAILABLE | No human/SME contacted; no new role dispatched. |
| E1 role unavailable | BLOCKED; NOT_CONFIGURED | BLOCKED / ESCALATION_UNAVAILABLE | Classification only; no discovery/new work. |
| E1 source/registry/audit unavailable | UNAVAILABLE; TEMPORARILY_UNAVAILABLE | BLOCKED / SOURCE_UNAVAILABLE | No access after refusal; retain verified existing owner only. |
| E1 current source ACL denied | DENIED; FORBIDDEN | BLOCKED / SOURCE_ACCESS_DENIED | No private candidate/content disclosed. |
| E1 unsupported follow-up | UNAVAILABLE; UNSUPPORTED | BLOCKED / FOLLOW_UP_UNAVAILABLE | Existing work unchanged; no later model/read. |
| D2E or D7V | BLOCKED; EVIDENCE_INSUFFICIENT | BLOCKED / SAFE_WORK_BLOCKED | No invented field, accepted work or review notification. |
| D3 | BLOCKED; APPROVAL_REQUIRED for confirmation/scope, otherwise EVIDENCE_INSUFFICIENT | QUESTION / ASK_FIELD | At most one question; no prospective parallel work. Prior reads, if any, remain reported. |
| D4 | BLOCKED; EVIDENCE_INSUFFICIENT | WAIT / QUESTION_STILL_OPEN | No answer consumed, no repeated question or work revision. |
| D5 code-social | SUCCEEDED; null | GREETING / SOCIAL_GREETING | Zero model/tool/work; no authority from model labels. |
| D5 other social/simple answer without trusted context | BLOCKED; EVIDENCE_INSUFFICIENT | INFORMATION_UNCERTAIN / NO_TRUSTED_ANSWER_CONTEXT | Zero tool/new work, no unchecked prose or successful work claim. |
| D6 known explicit own-work status | SUCCEEDED; null | WORK_STATUS / WORK_STATUS_KNOWN | No new/revised work or capability call; stored state only, not a delivered-result claim. |
| D6 verified read | Existing observed SUCCEEDED/PARTIAL outcome and error | FIXTURE_RESULT / VERIFIED_READ_RESULT | Only actual verified read steps; no new logical work. |
| D6 unknown status/context or failed read | Actual UNAVAILABLE/BLOCKED and typed error | BLOCKED/NO_CAPABILITY / CONTEXT_UNAVAILABLE | No invented status/result. |
| D8/D9 with verified read | SUCCEEDED or actual PARTIAL outcome | FIXTURE_RESULT / READ_WORK_OBSERVED | New process-only work IN_PROGRESS; read-step completion is not whole-work completion. |
| D8/D9 without verified result | Actual UNAVAILABLE/BLOCKED and typed error | BLOCKED/NO_CAPABILITY / READ_WORK_BLOCKED | Acknowledged logical record may remain BLOCKED; no worker or completed-result claim. |
| D0 | BLOCKED; EVIDENCE_INSUFFICIENT | BLOCKED / DECISION_FAIL_CLOSED | No new work or effect. |
| Turn quota exceeded | BLOCKED; BUDGET_EXCEEDED | BLOCKED / TURN_QUOTA_EXCEEDED | No M03 decision, model or read; projection-only receipted refusal. |
| E1 new-work quota exceeded | BLOCKED; BUDGET_EXCEEDED | BLOCKED / WORK_QUOTA_EXCEEDED | No new question/work/read; existing binding and non-allocating rows remain usable. |
| Replay current source access revoked | DENIED; FORBIDDEN | BLOCKED / SOURCE_ACCESS_DENIED | No cached result disclosed, new business receipt or revision; security audit only. |
| D3 late veto after verified read | PARTIAL; APPROVAL_REQUIRED for confirmation/scope, otherwise EVIDENCE_INSUFFICIENT | QUESTION / ASK_FIELD | Preserve earlier verified reads; stop all further calls and prospective work. |
| D2 late escalation after verified read | PARTIAL; original typed provider error if present, otherwise UNSUPPORTED | BLOCKED / ESCALATION_UNAVAILABLE | Preserve earlier verified reads; no human notification or further role/call. |
| D7V late safety veto after verified read | PARTIAL; EVIDENCE_INSUFFICIENT | BLOCKED / SAFE_WORK_BLOCKED | Preserve earlier verified reads; no further calls or new work. |
| Receipt sink failure | INTERNAL_ERROR; INTERNAL_ERROR, exit 1 | receipt_not_written | No aggregate/replay advance; conservatively report operation_may_have_taken_effect. |

Always commitment_id=null, launched=false, delivered=false in this prototype.
work_performed is based only on actual verified read observations and can be true
after a late veto; never hide those earlier reads or turn them into whole-work
completion. Nonterminal logical-work next_contact_at is a plan, with explicit
contact_scheduled=false: no scheduled timer/contact or ETA is claimed.

When a late veto/provider failure follows an actual verified read, preserve the
observed partial read result and use PARTIAL rather than falsely claiming zero
work. The table's BLOCKED/UNAVAILABLE cases describe zero verified reads. Decision
action remains ASK/ESCALATE and no overall OutcomeAssessment or delivery is
fabricated by that partial observation. All prior tool steps and hashes remain.

The closed dependency_error token for an unavailable recommended role is
ROLE_NOT_QUALIFIED; its outer error is NOT_CONFIGURED. ESCALATION_UNAVAILABLE
is the English template identifier (localized text is code-owned), never an error
code. D2 uses reason_code=TRIAGE_ESCALATED; E1 uses reason_code=DEPENDENCY_UNAVAILABLE; the separate dependency_error
retains ROLE_NOT_QUALIFIED or the actual producer code.

The follow-up preflight uses the M03 first-match order: after D1/D2 and blocking
M05/WAIT and D5/D6, a normalized next_action in {start_safe_work, ask} plus a
verified same-owner nonterminal work binding (explicit snapshot work_ref or M04
RESOLVED to such work) is the exact D7 predicate. No revision keyword is required
or sufficient. In T02 this predicate yields E1 FOLLOW_UP_NOT_IMPLEMENTED before
discovery; the pure table still tests D7 for the later owner. A resolved reference
with next_action=search_context remains D6 and may read known status without
revising work. A resolved reference alone never implies a revision. Test both a
bound start_safe_work refusal and the same binding with search_context/status_query
returning stored state, unchanged work revision and zero capability calls.

## 11. Producer errors and exact local proof disposition

| Trigger | Consumption |
|---|---|
| Missing authentication/config/receipt safety | Pre-business admission refusal; zero model/source access. |
| Invalid/exhausted classification or classifier unavailable | M08 fail-closed, M03 D2, actual provider error preserved. |
| M04 required reference source unavailable | E1 with unavailable resolution null. No guessed binding/new work. |
| Supplementary context source unavailable while not required | Report assumption, use remaining valid sources; never claim complete context. |
| UNRESOLVED/AMBIGUOUS target | M05 target_resource, D3 one question. |
| Known selected missing critical input or non-read effect | Phase-2 veto, zero handler, final D3 unless deny/escalate already wins. |
| Unknown/not-shortlisted proposal | Existing generic selection refusal, normalized dangerous effect, D2; no existence lookup. |
| Required role unavailable | E1 ROLE_NOT_QUALIFIED before another model/discovery call. |
| Unsupported follow-up mutation | E1 FOLLOW_UP_NOT_IMPLEMENTED before discovery; work unchanged. |
| Sink failure | Receipt fault path; no successful apply/TurnResult. |

Phase-1 source requirements are explicit: a known work_ref, non-null classification
reference hint or recognized old-work reference request requires available prior
context. Ordinary time-window lookup (for example calendar meetings this week)
is not by itself an old-work binding request. The same source outage cannot be
reported as proof that no earlier work exists. Social/simple_answer return before
reference cue/source evaluation. Reference cues only reduce scope by requesting
clarification; they never change intent or create/authorize work by keyword.

| IDs | T02 contribution | Remaining full owner |
|---|---|---|
| M03-FR-01 | Trusted social classification, D5/receipt/no-work tests. | T04 full acceptance. |
| M03-FR-02 | Pure table and supported USER_TURN reachability/outward mapping. | T03 async integration; T04 full acceptance. |
| M03-FR-03, M03-AT-02 | No follow-up/async completion claim. | T03 then T04; real ledger separately S02. |
| M03-AT-01 | Greeting and initial safe-read portion only. | T03 restriction update, T04 full case. |
| M03-RT-01 | Code-owned messages/reasons reject unobserved progress. | T04 full-case integration. |
| M03-RT-02 | Summary bound and no repeated T02 question; no timer claim. | T03 answer/re-ask, S02 timer suppression. |
| M04-FR-01, M04-FR-02, M04-AT-02, M04-RT-01 | Pure resolution/score, private filtering, ambiguity and informational guard. | T04 S01 full acceptance. |
| M04-FR-03 | No correction append claim. | T03 prototype; S02 real ledger. |
| M04-AT-01, M04-RT-02 | No S03 memory-integration claim; shared ACL negatives may contribute only. | S03 full acceptance. |
| M05-FR-01, M05-FR-02, M05-AT-01, M05-AT-02, M05-RT-01, M05-RT-02 | Clarification rules and real guarded synchronous initial read/denial. | T04 full S01 acceptance. |
| M05-FR-03 | No answer binding/replay-update completion claim. | T03 prototype; S02 real ledger. |

The task's empty owned/final plan lists remain empty. Related IDs are not a PASS
claim. Exact local A01/A02/A03 use the public CLI test locators in WORK_PACKAGES;
per-PRD unit oracle names remain unchanged. Application CAS/replay/fault proof is
separate at tests/integration/test_s01_interaction_apply.py; repeated CLI lines
are not presented as a replay-key test.

## 12. Review dispositions and executable oracle ownership

The first independent SDD review is NEEDS_CORRECTION; no runtime source existed.
This revision resolves its findings before TDD. Two recommendations need precise
qualification: the intent effect floor is already knowable in phase 1, and a late
veto cannot erase earlier reads. An unknown/not-shortlisted ID cannot be looked up
just to produce a specific approval question: it escalates without an existence
oracle. Replays reuse the original receipt, rather than changing evidence_refs
while claiming byte-identical TurnResult.

Reference-cue catalog old-reference/1 matches whole normalized words again,
previous, earlier, same, novamente, anterior, mesmo, mesma; phrases that study,
that report, aquele estudo, aquele relatório, esse estudo, esse relatório; or an
explicit work- reference. Normal time-window lookup alone is not a cue. After
the social/informational guard, reference_required is also true for a non-null
classification hint or a verified snapshot work_ref. M05 target_resource is
missing when this requirement has no resolved target, even if M04 correctly
returned NO_REFERENCE for a null model hint. This only blocks/asks; it never
changes classification or starts work by keyword.

| Oracle / scope | Actual T02 locator or explicit later owner |
|---|---|
| Local A01 / M05-AT-01 initial read contribution | tests/integration/test_clarify_cli.py::test_optional_preference_does_not_block_research |
| Local A02 / M05-AT-02 denial contribution | tests/integration/test_clarify_cli.py::test_missing_tenant_or_approval_blocks_write |
| Local A03 receipt/source fault contribution | tests/integration/test_clarify_cli.py::test_faults_never_fabricate_progress |
| M05-FR-01/FR-02/RT-01/RT-02 pure rules | tests/unit/test_clarify.py and test_clarify_redteam.py, exact PRD function names |
| M04-FR-01/FR-02/RT-01 pure rules | tests/unit/test_reference_resolution.py, test_reference_score.py and test_reference_redteam.py, exact PRD function names |
| M04-AT-02 ambiguity contribution | tests/integration/test_reference_cli.py::test_two_last_week_studies_yield_one_question |
| M03-FR-01/FR-02/RT-01 pure rules | tests/unit/test_eri_decision.py and test_eri_redteam.py, exact PRD function names |
| Initial social/USER_TURN CLI contribution | tests/integration/test_eri_cli.py (no full three-turn M03-AT-01 claim) |
| CAS/replay/receipt/quotas | tests/integration/test_s01_interaction_apply.py (public application contract) |
| M08 budget and privilege/synonym contributions | tests/unit/test_triage_budget.py and test_triage_redteam.py, exact PRD function names |
| M03-FR-03/AT-02, full M03-AT-01, M04-FR-03, M05-FR-03 | T03/T04; no partial test renamed to imply full acceptance |
| M03-RT-02 answered re-ask/timer suppression | T03/S02; T02 covers only supported summary/question portions |
| M04-AT-01/RT-02 memory integration | S03; T02 shared ACL negatives are contribution-only |

Required discriminating supplemental oracles: phase-1 external intent asks before
any tool; phase-2 veto executes no selected handler; a read followed by an unknown
write-like proposal preserves the earlier verified read and stops with one final
escalation; a known visible non-read selection is refused without handler; direct
source outage is not invented status; social preflight has no model; unsupported
follow-up has no work revision; current access is checked on cache replay; quota
999/1000/1001 and work 20/21 boundaries including replay after exhaustion; returned-response mutation cannot change
replay bytes; a lower provider cap and retry/deadline cap stop before transport.

Provider/transport errors keep their actual existing M01 status/error/exit mapping
on every path, including a loop failure after classification. M03 describes the
interaction; it does not turn BUDGET_EXCEEDED, DEADLINE_EXCEEDED or OUTPUT_INVALID
into an invented success or generic source outage. Human-facing business message
and display lines use the selected/detected language; technical diagnostics and
reason codes remain English.
