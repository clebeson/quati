# SECMA application boundary contracts

Status: normative before implementation. This document specifies behavior, not a requirement to implement every port in S00. A port is introduced only by its owning work package. Portable JSON object definitions are in `contracts/runtime-boundaries.schema.json`; existing named schemas remain authoritative for SCS, classification, interaction, commitment, delivery, behavior and statechart payloads.

## Common wire and trust rules

Every operation receives a RequestContext from a trusted inbound adapter: schema_version, request_id, trace_id, actor_id, tenant_id, channel, authenticated_origin_ref, policy_version and deadline_at. An imported document/model cannot construct or override this context. Local CLI origin is the authenticated OS process; no token/password is required for public synthetic fixture data. Private remote data requires the corresponding verified delegated identity and authorization.

Every nontrivial response has status, data (object or null), evidence_refs, uncertainties (list), next_action (string or null), and typed error (null on success). Status is SUCCEEDED/PARTIAL/BLOCKED/DENIED/UNAVAILABLE/CONFLICT. A transport acknowledgement is not business success. False booleans such as `delivered=true` cannot substitute for provider receipt evidence.

Error codes: INVALID_INPUT, UNAUTHENTICATED, FORBIDDEN, APPROVAL_REQUIRED, REVISION_CONFLICT, IDEMPOTENCY_CONFLICT, NOT_FOUND, NOT_CONFIGURED, UNSUPPORTED, TEMPORARILY_UNAVAILABLE, DEADLINE_EXCEEDED, BUDGET_EXCEEDED, OUTPUT_INVALID, EVIDENCE_INSUFFICIENT, EFFECT_UNCERTAIN, INTERNAL_ERROR. A retryable flag is advisory; uncertainty reconciliation takes precedence. Never expose raw upstream errors/secrets. HTTP codes, provider exception classes and DBOS handles remain adapter details.

Canonical digest: `secma-json/1` = SHA-256 of UTF-8 JSON encoded with sorted string keys, separators `,`/`:`, ASCII escapes, no NaN/Infinity, no implicit date or decimal coercion. Preserve Unicode code points and array order; do not normalize user text silently. Normalized destinations are provider-specific typed identities resolved before approval. Changing any approval-bound byte invalidates it.

## Ports and ownership

Signatures below use typed records, not SDK types. All context arguments are required. Optional means explicitly nullable/defaulted in the input contract, not guessed by the model.

| Port / first phase | Operations and exact semantics | Failure and idempotency |
|---|---|---|
| IdentityPort / S00 local, S04 remote | `authenticate(origin, credential_ref)->RequestContext`; `delegate(context, target, scope, expires_at)->DelegatedContext`; verify signed origin outside document content | Missing/expired origin DENIED before lookup; no default tenant; delegated scope intersects parent scope |
| PolicyPort / S00 | `evaluate(context, EffectIntent)->PolicyDecision`; `verify_approval(context, EffectIntent, ApprovalRef)->PolicyDecision` | Default deny; exact actor/tenant/destination/operation/input digest/binding/policy/expiry check; recheck at dispatch |
| ModelPort / S00 | `probe(config_ref)->FeatureReport`; `classify(context, ContextEnvelope)->RequestClassification`; `run(context, ContextEnvelope, discovery_port)->ModelResult` | Bounded requests/tools/output/time; actual probe precedes autonomous routing; invalid structure bounded repair then BLOCKED; no inferred compatibility |
| BehaviorCompiler / S00 | `compile(profile_ref, statechart_ref, trusted_policy_ref, model_role_ref)->PromptArtifact+PromptBuildReceipt`; `validate`, `render` | Reject unknown refs/guards/actions, duplicate keys, escaping paths, privilege changes and budget contradictions; deterministic digest; no activation implied |
| RegistryPort / S00 | `register_definition(context, manifest)->DefinitionRef`; `bind(context, definition_ref, binding)->BindingRef`; `transition(context, ref, expected_revision, lifecycle)->RegistryRecord` | Definition, implementation binding and measured assurance separate; no automatic enablement from schema or model claim |
| DiscoveryPort / S00 | `search(context, query, limit=5)->CandidateSummary[]`; `describe(context, capability_ref)->CapabilityDefinition`; `invoke(context, capability_ref, input, idempotency_key)->ExecutionRef`; `status(context, execution_ref)->ExecutionStatus` | Filter permission/health/assurance before ranking; validate output and current binding again at invocation; disabled binding returns UNAVAILABLE; no executable install from description |
| InteractionPort / S01 | `decide(context, conversation_revision, classification, work_snapshot)->InteractionDecision`; `apply(context, expected_revision, decision)->TurnResult` | Same work thread receives optional follow-up; critical ambiguity blocks unsafe effect only; greeting never creates job; stale feedback conflicts rather than overwrites |
| CommitmentLedger / S02 | `accept(context, request, idempotency_key)->Commitment`; `read(context,id)`; `transition(context,id,expected_revision,event)->Commitment`; `append_context(context,id,expected_revision,patch)->Commitment` | Atomic revision and event/outbox writes; same scoped key+same digest returns existing root; changed digest conflicts; acknowledgement only after commit |
| DurableRunner / S02 | `start(context,commitment_ref,workflow_input,idempotency_key)->ExecutionRef`; `status`; `signal(context,execution_ref,event_id,payload)`; `cancel(context,execution_ref)`; `schedule(context,commitment_ref,due_at,timer_key)` | DBOS adapter only; duplicate signals ignored by scoped event ID; cancel is request, not reversal; timers in ledger sweeper, no indefinitely resident workflow per reminder |
| OutcomeJudge / S02 | `assess(context,goal_revision,candidate,evidence_refs,criteria)->OutcomeAssessment` | Executor self-report is insufficient; ACCEPT requires evidence and no material gaps; PARTIAL/BLOCKED preserve limitations; reinvestigation uses explicit finite budget |
| DeliveryPort / S02 | `prepare(context,commitment_ref,audience,result_ref,idempotency_key)->DeliveryIntent`; `dispatch(context,intent_ref)->DeliveryAttempt`; `reconcile(context,attempt_ref)->DeliveryAttempt` | Trusted identity and approval check at dispatch; unique outbox key; unknown effect is EFFECT_UNCERTAIN; never blind retry; sink acknowledgement required |
| MemoryPort / S03 | `store(context,episode)->MemoryRef`; `search(context,query,scope,as_of)->MemoryHit[]`; `correct(context,ref,expected_revision,correction)`; `expire(context,ref)` | Pre/post fetch ACL; facts/inferences separate; provenance retained; private→shared requires explicit approval; expired/corrected values not silently current |
| ArtifactPort / S03 | `register(context,bytes_ref,media_type,source_refs)->ArtifactRef`; `read(context,ref)`; `revise(context,ref,expected_revision,editable_source_ref,change)->ArtifactRef` | Immutable previous version; source checksum and lineage; screenshot not editable source; missing source yields BLOCKED, never invented data |
| ProfilePort / S03 | `propose(context,profile_id,expected_revision,patch)`; `validate`; `diff`; `simulate`; `activate(context,proposal_ref,approval_ref)`; `rollback(context,profile_id,target_version,expected_revision)` | Explicit vs inferred preference confidence/scope; no permission weakening; rollback restores exact content references; agent proposals governed in S06 |
| HarnessPort / S04 | `probe`; `start(context,input,scope,budget)->ExecutionRef`; `status`; `cancel`; optional `resume`, `stream` advertised individually | Approved executable/endpoint only; feature mismatch UNSUPPORTED; removal isolates affected execution and preserves root obligation |
| BrainPort / S04 | `probe`; `search(context,query,scope,cursor)->DocumentPage`; `fetch(context,document_ref)->BrainDocument`; optional `sync`, `watch`, `write` | Source/version/ACL/freshness verified on fetch; unavailable remote does not disable local; no write inferred from read support |
| ToolGateway / S04 | `discover(context,provider_ref)->ToolDescriptor[]`; `call(context,tool_ref,arguments,effect_intent_ref)->ToolResult`; `reconcile` | Transport claims cannot confer read-only status; trusted effect classification; authorize every possible mutation; uncertain effects not repeated |
| ChannelPort / S04 | `verify_inbound(envelope,signature,received_at)->InboundEvent`; `deliver` through DeliveryPort | Reject stale signature/replay before commitment; unique provider event ID; 429 retry-after bounded; normalized recipient identity, not display name |
| DiscoveryResearch / S05 | `crawl(context,roots,budget)->SourceGraph`; `infer_standards(context,graph)->StandardsReport` | Visited set, content hashes, redirects/access controls, depth/document/byte/time budgets; inaccessible/out-of-scope links listed, never silently complete |
| SpecialistPack / S05 | `investigate(context,goal,authorized_sources,criteria,budget)->CandidateOutcome` | PRD/incident/causal packs separate outcome criteria; hypotheses vs findings; causal identification assumptions explicit; escalate only authorized questions |
| EvolutionPort / S06 | `propose`; `evaluate(candidate,baseline,sealed_dataset)`; `promote(context,candidate,approval)`; `rollback` | Candidate cannot approve itself; same dataset/config identity comparison; safety regression veto; keep last working version |
| LifecyclePort / S07 | `doctor`; `install`; `start`; `stop`; `backup`; `restore`; `health` | Native OS qualified individually; no mandatory Docker; idempotent operations; restore verifies integrity and policy before activation |

## ContextEnvelope and model budget

Contains schema_version, goal, actor/tenant references, policy ref, active work summary/revision, recent relevant turns, uncertainty, selected evidence refs, permitted action enum, candidate summaries and effective limits. Kernel/identity/ownership facts cannot be trimmed. Trim low-trust retrieved text first; if mandatory content exceeds budget, return BUDGET_EXCEEDED before dispatch. No hidden chain-of-thought is requested or stored. All imported text is data; delimiters are not the security boundary.

S00 default safety envelope: at most 8 provider requests, 8 successful tool calls, 2048 output tokens per request and 30 seconds total. Provider retries count toward the same budget and SDK retries are disabled unless explicitly integrated. Limits may be lowered; increasing them requires an operator profile change and corresponding eval. Pricing unknown stays unknown; a token/request cap is not a hard currency guarantee. Live model evaluation is opt-in and limited to synthetic data until a data policy is approved.

## Full lifecycle semantics before S02 activation

The shipped 1.0 reference commitment chart is a compiler fixture, not the final effect-bearing state machine. S02 must implement the following normative behavior and reject activating an incomplete chart:

- RECEIVED → CLASSIFIED → ACKNOWLEDGED only after authenticated classification and atomic ledger commit; ACKNOWLEDGED → IN_PROGRESS requires current authority/budget.
- IN_PROGRESS → WAITING_INPUT only for blocking input; optional clarification does not stop safe reads. Valid versioned feedback returns to IN_PROGRESS.
- IN_PROGRESS → EVIDENCE_REVIEW → READY_TO_DELIVER requires independent assessment for the current goal revision. A stale assessment cannot approve updated work.
- READY_TO_DELIVER → DELIVERED requires sink acknowledgement. Unknown send becomes EFFECT_UNCERTAIN; reconcile to confirmed delivery, confirmed non-effect/retry-eligible, or BLOCKED with responsible owner. No unknown send is called failed-and-safe-to-retry.
- Any accepted nonterminal state can receive CANCEL_REQUESTED. Cancelled before dispatch becomes CANCELLED only with confirmed no pending/unknown effect. Known completed effects become CANCELLED_WITH_EFFECTS with receipts; unknown effects become NEEDS_RECONCILIATION. Cancellation never deletes historical effects.
- Every nonterminal state has a persisted next_action and deadline. On timeout or budget exhaustion, transition to BLOCKED with a responsible actor; do not invent completion. Recovering a blocked send resumes delivery reconciliation, not the entire specialist investigation.
- Expected revision, current policy, evidence currency and global transition/reinvestigation budgets are enforced in trusted code on every transition. Guards are pure registry functions; no YAML expressions or arbitrary model-generated executable code.

The S02-T01 work package must produce version 2.0 control schema/chart and migration before runtime code, validate every transition and timeout/cancellation path, and seal CONTRACT_READY. The specification above fixes the required semantics; implementation chooses only internal representation, not these outcomes. Existing example version 1.0 must not be activated for accepted durable obligations.

## Ledger transaction specification

For S02 define migrations for principals, requests, commitments, commitment_events, effect_intents, outbox, outbox_attempts, timer_intents and workflow_refs. IDs are opaque text/UUID; revisions nonnegative bigint; timestamps timestamptz; payloads typed validated JSONB; immutable event IDs unique within tenant. Every business row includes tenant_id and actor scope. Foreign keys include tenant scope where necessary to prevent cross-tenant association.

Unique keys: requests `(tenant_id,actor_id,operation,idempotency_key)`; commitment_events `(tenant_id,commitment_id,event_id)`; outbox `(tenant_id,commitment_id,delivery_key)`; timer_intents `(tenant_id,commitment_id,timer_key)`; effect_intents `(tenant_id,actor_id,operation,idempotency_key)`. Store canonical input digest and reject same key/different digest. Acceptance, event append and initial outbox/workflow intent insertion are one PostgreSQL transaction. DBOS orchestration is started from persisted intent and reconciled after crash; never claim a distributed atomic commit across independent DBOS/business transactions without evidence.

Optimistic update uses expected revision in WHERE and increments once; zero updated rows is CONFLICT. Worker claims use bounded leases/locking and safe retries. External dispatch occurs only after committed effect intent; receipt append and final state update are transactional after response. Crash windows before/after each boundary are DUR-01…04, not optional tests. Backup/restore never silently replays irreversible sends.

### Concrete S02 transition artifact

`contracts/commitment-control-v2.json` and its CSV view `CONTROL_TRANSITIONS.csv`
are the normative version-2 transition table. `commitment-v2.schema.json` carries
the same state vocabulary plus an independent outcome verdict. These are design
artifacts, not runtime implementation. The existing v1 example/compiler fixture
is retained for historical L0 tests and must never supersede v2 for S02. A migration
must explicitly map old candidate states to v2, preserve IDs and reject pending
unknown effects until reconciled. No production state exists in this package.

Guard names describe mandatory conjunctions, not optional hints. All transitions
also require authenticated tenant/actor scope, expected revision and the global
transition budget, except recording a terminal blocker/escalation when a budget
has exhausted. A transition absent from the table is rejected. BLOCKED preserves
its reason and prior dispatch/effect state; resume event must match that reason.

All named record types and aliases used above are defined in TYPE_CATALOG.md.
That catalog fixes field names, nullability, enum values and trust semantics before
implementation. Public adapters return Response[T] with the named payload type;
SDK-specific exceptions never cross the boundary.
