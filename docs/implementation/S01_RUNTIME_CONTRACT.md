# S01 prototype runtime contract

Normative realization of the S01 work packages, supplementary to the named PRDs
and JSON schemas. This document resolves LOG-0058 / design gaps G1-G10. It does
not change the protected kernel, authorize external effects or waive real-model
proof. S01 is a development prototype, not a durable secretary release.

## 1. Package boundaries

| Package | Delivered boundary | Explicitly not claimed |
|---|---|---|
| S01-T01 | Typed RequestClassification ingress; pure classification-policy reducer; schema-compatible direct RequestContext; constant-space conversation identity/revision on the existing CLI chat path. | Full InteractionPort, question selection, new model-authored ANSWER output, background execution, historical reference resolution, follow-ups or model escalation. |
| S01-T02 | M03 decisions for user turns, M04 reference resolution, M05 clarification and safe read kickoff, validated direct answers. | Durable acceptance, concurrent follow-up/result binding, timers or confirmed external delivery. |
| S01-T03 | Ephemeral logical-work updates, revision/idempotency checks, independent work isolation and bounded role fallback. | Crash recovery or continuation after process exit. |
| S01-T04 | Complete slice requirements and blind real-model cases on the exact current source/configuration. | Passing a contribution test as full case proof. |

T01's pure reducer is a tested building block, not an activated model-routing
policy. It consumes an already validated DecisionPolicy and never dispatches a
model or a capability. Runtime policy installation/consumption belongs to T02;
role availability and fallback belong to T03. The S00 public read-discovery path
and its guards continue during T01. No model recommendation grants authority.
T01 exposes a complete schema-shaped public classification projection, labelled
classification_stage=SCHEMA_VALIDATED, or the code-owned FAIL_CLOSED value after
classifier failure. Free model strings remain undisplayed: public reason_code is
CLASSIFICATION_VALIDATED and any present commitment_ref is null. The raw proposal
is retained only through classification_sha256 and approved synthetic evidence;
that hash does not identify the sanitized public projection. Optional confidence
is a bounded number, never authority. Typed domain serialization remains lossless.
This is not the step-5 M08 value consumed by M03/M04. Pure reducer recommendations
do not change dispatch, role or priority before T02. In particular, publishing a
complete schema shape must not regress the S00 prohibition on model-written
completion claims in free-text classification fields.

## 2. Classification foundation (T01)

`RequestClassification` has exactly the vocabulary of
`contracts/request-classification.schema.json`. Frozen typed values reject extra
keys, missing required keys, non-boolean flags, unknown enums, invalid optional
references and nonfinite/out-of-range confidence. Serialization preserves the
input's optional-field presence. Domain validation uses standard-library code;
schema-equivalence tests exercise the canonical JSON Schema at the boundary.

The existing model structured-output ladder still runs first. An exhausted
classification ladder publishes the DECISION_RULES section 3.1 fail-closed
classification, while retaining the actual provider error/status. It dispatches
no discovery calls. Other provider failures during classification also retain
their actual error and use the fail-closed classification; absence of a model
response is never a successful classification claim.

The pure policy reducer applies DECISION_RULES section 3 and M08 priority/1 to a
typed proposal, a loaded DecisionPolicy, an injected `now`, an optional trusted
resolved business deadline, and a caller-supplied trusted capability-effect map.
An unknown proposed capability is dangerous. No model text supplies effect,
role, priority, policy or identity. The transport deadline in RequestContext is
not a business deadline. Invalid proposals use the published fail-closed value.
The low-level table has R0 for out-of-vocabulary inputs; normalized valid tuples
never select R0. Exhaustively test all 1344 valid tuples and restrictive proposal
routes. A result's role is a recommendation, not measured role qualification.

## 3. Direct RequestContext (T01)

All existing required context fields remain required on the wire. Direct LOCAL
requests serialize `act: null`; T01 implements no delegated authentication.
The direct serializer discards caller-supplied delegation data and always emits
null; an invalid informational policy version is rejected before serialization.
`policy_version` may be null when identity authentication cannot determine the
authorization policy. Null never means ALLOW: authorization still loads and
checks the trusted policy before effects, independently of this informational
field. Non-null policy versions remain nonempty strings. Convert tuple fields to
JSON arrays at serialization. Caller text and classification cannot override any
context field. Existing contexts/examples with a string policy version remain
valid. The earlier S00 schema mismatch is historical, not a new exemption. Tests must prove that missing trusted policy still denies when context.policy_version is null, that a forged context version changes no policy decision, and that EffectIntent receives its version from the trusted policy argument rather than the context. act=null serializes as JSON null. The full M26 audit act_chain field is S02-owned (its direct-origin mapping is []); T01 does not falsely claim that S00 audit records already emit it.

## 4. Ephemeral conversation projection (T01)

The application owns one `ConversationSession` per `quati chat` invocation; the
CLI only constructs and passes it. Authentication and all S00 admission checks
still run on every turn through CLIService.ask. A fresh service may be composed
for each turn with the same application session. Authentication `session_id`,
request ID and token JTI remain fresh and are not conversation locators.

The projection stores only opaque conversation ID, tenant ID, actor ID and an
integer revision. It stores no transcript, credentials, jobs, work IDs or durable
commitments. IDs are injected; production composition uses its existing ID
generator. The first authenticated turn whose receipt is written binds the
session to its tenant/actor. Every later turn checks that ownership before any
model, capability or receipt write. An ownership mismatch is FORBIDDEN, with no
restricted response payload, no receipt and no revision change. The exception ends chat with exit 4, rather than continuing under a different principal. Test an injected principal change and observe zero effects and writes for that failed turn. Revision starts at zero and advances exactly once
per successfully receipted ask response, including a receipted refusal. Empty
lines, local commands and unauthenticated/unreceipted failures do not advance it.

Prepare the next projection before writing the receipt; include its metadata in
the response before hashing that response. Commit the prepared revision only
after the receipt sink succeeds. A sink failure leaves the prior projection
unchanged and discards the prepared result. Existing M01 mapping remains receipt_not_written / INTERNAL_ERROR / exit 1 with operation_may_have_taken_effect=true and no conversation metadata on the failure response. Chat ends immediately; it does not process the next line. A separately retried application turn prepares from the unchanged revision, without a claim that earlier effects rolled back. Pure revision application checks the expected revision and rejects a
stale value with REVISION_CONFLICT and no mutation. T01 is a synchronous,
single-owner session; cross-thread scheduling and work-result isolation are T03.
Do not infer worker or effect rollback from a projection failure.

Every chat ask response with data includes:
`conversation: {id: str, revision: int>=1, lifetime: PROCESS_ONLY,
continues_after_exit: false}`. This is an explicit machine-readable lifetime
disclosure, not a persistent work reference. Existing commitment_id stays null,
and launched/delivered retain their existing truth conditions. One-shot ask has
no conversation metadata. The receipt's output_hash binds the actual printed
response with evidence_refs empty, including this metadata. Only those declared
conversation fields differ when comparing equivalent chat and one-shot turns;
all prior content, status, authorization and evidence assertions still apply.

## 5. M03/M04 contract realization after T01

InteractionPort instances bind a trusted conversation identity and owner at
construction. They never derive it from model text or RequestContext.session_id.
`conversation_revision` / apply's expected_revision are conversation revisions;
WorkSnapshot.work_revision is a separate logical-work revision. The request_id
is the per-turn idempotency key, scoped to tenant/actor/conversation. Apply checks
the complete request/decision body against the stored key; same key/body returns
the identical stored TurnResult before CAS, a different body conflicts. These
work/decision replay semantics are implemented in T02/T03, not inferred from the
T01 projection counter.

S01 WorkSnapshot is supplied by the application from its in-process store. Its
USER_TURN classification is required; TIMER/ASYNC_RESULT classification is null.
T01 does not instantiate these work snapshots or implement InteractionPort.
T02 owns request_text, language, reference/clarification/contact inputs and the
first work snapshot. T03 owns async binding and logical-work revision changes.
Unavailable later-module inputs must produce a typed unavailable result, never
fabricated M05/M06/M09 verdicts, timers or provider acknowledgements.

In S01, ledger/commitment wording in M03/M04 oracles means the corresponding
application-owned ephemeral logical-work record. Work identity is carried by
TurnResult.work_ref; InteractionDecision.commitment_id is null until S02. A
logical-work reference never claims crash durability. SQLite/CommitmentLedger
conformance and crash/restart assertions require the real S02 backend separately.
S01 tests must assert the prototype disclaimer and may not call this ledger proof.

M03's first-match oracle selects exactly one row including D0 for incompatible
input combinations. D0 is a real fail-closed outcome; the Cartesian product of
individual enums is not a declaration that every cross-field tuple is coherent.
Every WAIT still requires a non-null next_contact_at.

M04 returns NO_REFERENCE for social/simple_answer before candidate retrieval or
scoring, regardless of coincidental title keywords. It never changes the M08
classification. Reference resolution and any work creation remain separate.

### Oracle responsibility (contributions, not final acceptance)

| Oracle | T01 contribution | Remaining implementation/full proof |
|---|---|---|
| M08-FR-01 | Typed separation; pure role/priority/route rules. | T02 activates runtime policy; T04 accepts full slice proof. |
| M08-FR-03 | Invalid/exhausted classifier output becomes fail-closed. | T02 runtime budget test_triage_budget; T03 role fallback; T04 full proof. |
| M08-AT-02 | No end-to-end ambiguity claim. | T02 test_triage_cli and clarification; T04 real-model case. |
| M08-RT-01 | Schema rejects model privilege/role/effect fields; pure reducer trusts registry effects only. | T02 consumes normalized values before dispatch; T04 full proof. |
| M08-RT-02 | Invalid intent and unknown proposed capability fail closed in pure tests. | T02 rechecks selected capability effects on runtime dispatch; T04 full proof. |

T02 must enumerate reachable M03 tuples from the validated classifier and verdict
producers and assert that no supported reachable tuple falls into D0 by accident.
Cartesian incompatible tuples still fail closed through D0. T02 also owns
ModelResult construction; the TYPE_CATALOG S01 milestone is not a T01 delivery.

## 6. Model text and qualification

During T01, model-authored text remains undisplayed on the S00 path. T02 may
display only a validated, bounded M03 ANSWER for informational requests; receipt,
progress, question and work-start messages remain code-owned templates based on
observed state. In both languages (English/Portuguese), no model text is evidence
of completed work, authority or provider delivery. SOC-02/CAP-04/INT-01 remain
CONTRIBUTION_ONLY until T04's real-model proof.

Changes to source or runtime-boundary assets expire reuse of the old live code/
asset digest for the current tree. S00 acceptance remains historical proof on its
sealed commit. Do not edit its seals or present that old qualification as S01
proof. T04 must requalify affected discovery/social safety paths and the new ERI
cases on one current, pre-registered source/configuration snapshot. No paid run
or new slice PASS is implied by this contract or by T01's deterministic tests.
