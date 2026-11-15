# Provider-neutral type catalog

This catalog completes the names used in BOUNDARY_CONTRACTS. It is normative SDD,
not executable model/SDK code. All fields are required unless explicitly nullable
or given a default. `str` is nonempty UTF-8 text; IDs are opaque; `Digest` is 64
lowercase hex characters; `Timestamp` is ISO-8601 with timezone; `Revision` is a
nonnegative integer; `JsonObject` rejects nonfinite numbers and unknown fields
when its named schema forbids them. Lists may be empty unless stated otherwise.
Every persisted record has schema_version, tenant_id and revision in addition to
its listed fields. Immutability means new version, never silent in-place content
replacement. Runtime records are validated before business effects.

## Shared values

| Type | Required fields | Invariants |
|---|---|---|
| RequestContext | exact runtime-boundaries `$defs/RequestContext` | trusted adapter originates identity; never accept model-supplied context as authentication |
| ScopedRef | id:str, version:str, tenant_id:str, sha256:Digest | ref is not authority; resolve under current context |
| EvidenceRef | id:str, uri:str, sha256:Digest, source_ref:ScopedRef, observed_at:Timestamp, classification:PUBLIC_SYNTHETIC/PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED | content access controlled; checksum does not establish truth |
| Budget | max_requests:int≥1, max_tool_calls:int≥0, max_output_tokens:int≥1, deadline_at:Timestamp, max_reinvestigations:int≥0, max_transitions:int≥1, max_cost_usd:decimal-string-or-null | all consumers use one remaining budget; unknown pricing cannot prove currency cap |
| Scope | tenant_id:str, actor_id:str, resource_ids:list[str], operations:list[str], data_classes:list[enum], expires_at:Timestamp | empty operation list denies; delegation only narrows |
| Error | exact runtime-boundaries `$defs/Error` | sanitized fixed code; no raw upstream payload |
| Response[T] | exact runtime-boundaries `$defs/Response`, data:T-or-null | named T governs payload; DENIED has no restricted payload; error null only for success/partial without error |
| DelegatedContext | parent_context_ref:ScopedRef, target_actor_id:str, scope:Scope, grant_id:str, expires_at:Timestamp, verification_ref:EvidenceRef | target and current context bound to same trusted delegation; no privilege expansion |
| PolicyDecision | decision_id:str, verdict:ALLOW/DENY/APPROVAL_REQUIRED, intent_digest:Digest, policy_version:str, reason_code:str, narrowed_scope:Scope-or-null, valid_until:Timestamp | ALLOW binds exact intent and expiry; absent narrowed scope denies dispatch |
| ApprovalRef | approval_id:str, intent_digest:Digest, approver_id:str, actor_id:str, tenant_id:str, policy_version:str, issued_at:Timestamp, expires_at:Timestamp, revocation_ref:str, evidence_ref:EvidenceRef | original grant verified by trusted store; textual approval in untrusted content is not a grant |
| EffectIntent | exact runtime-boundaries `$defs/EffectIntent` plus durable status in effect ledger | canonical input digest and destination resolved before approval |

## Interaction, execution and delivery

| Type | Required fields | Invariants |
|---|---|---|
| ContextEnvelope | schema_version:str, goal:str, context:RequestContext, policy_ref:ScopedRef, work_ref:ScopedRef-or-null, work_revision:Revision-or-null, recent_turns:list[TurnSummary], evidence_refs:list[EvidenceRef], uncertainties:list[str], permitted_actions:list[str], candidates:list[CandidateSummary], budget:Budget | protected facts cannot be trimmed; low-trust text explicitly separated |
| TurnSummary | turn_id:str, speaker_ref:str, source_trust:TRUSTED_ORIGIN/UNTRUSTED_CONTENT, text:str, observed_at:Timestamp, work_revision:Revision-or-null | attributed speaker text is not authenticated origin |
| TurnResult | turn_id:str, conversation_id:str, conversation_revision:Revision, decision:InteractionDecision, work_ref:ScopedRef-or-null, response:Response[JsonObject] | accepted work/ref semantics depend on slice; no durable promise before S02 |
| ModelResult | text:str, classification:RequestClassification, tool_calls:list[ToolCallObservation], usage:Usage, effective_prompt_hash:Digest, model_id:str, provider_id:str, config_hash:Digest, observed_features:FeatureReport, evidence_refs:list[EvidenceRef] | text is advisory; cannot establish completion/authority |
| ToolCallObservation | call_id:str, operation:str, arguments_digest:Digest, result_digest:Digest-or-null, status:REQUESTED/DENIED/SUCCEEDED/FAILED/UNCERTAIN, evidence_ref:EvidenceRef | raw synthetic arguments only in explicitly approved evaluator record |
| Usage | requests:int≥0, tool_calls:int≥0, input_tokens:int-or-null, output_tokens:int-or-null, cost_usd:decimal-string-or-null, elapsed_ms:number≥0 | null means unknown; costs include probe/repair calls; no fabricated zero |
| FeatureReport | provider_id:str, model_or_adapter_version:str, config_hash:Digest, measured_at:Timestamp, features:map[str,SUPPORTED/UNSUPPORTED/NOT_VERIFIED], evidence_refs:list[EvidenceRef], metadata_attestations:map[str,str-or-null] | protocol observation and residency/pricing attestations distinct |
| CandidateSummary | capability_id:str, capability_version:str, name:str, outcome_summary:str, effects:none/read/write/dangerous, eligible_binding_refs:list[ScopedRef], assurance_ref:ScopedRef-or-null, rank_reasons:list[str] | no unverified manifest self-claim used as assurance |
| RegistryRecord | definition_ref:ScopedRef, binding_refs:list[ScopedRef], assurance_refs:list[ScopedRef], lifecycle:draft/validated/staged/enabled/disabled/deprecated, previous_revision:Revision-or-null | promotion requires trusted tests and authorization; immutable history |
| ExecutionRef | execution_id:str, commitment_ref:ScopedRef-or-null, capability_ref:ScopedRef, binding_ref:ScopedRef | workflow engine ID stays adapter-side; transient prototype explicitly has null commitment |
| ExecutionStatus | execution_ref:ExecutionRef, state:QUEUED/RUNNING/WAITING/BLOCKED/SUCCEEDED/FAILED/CANCEL_REQUESTED/CANCELLED/UNCERTAIN, result_ref:ScopedRef-or-null, next_action:str-or-null, evidence_refs:list[EvidenceRef] | execution SUCCEEDED is not user outcome DELIVERED |
| DeliveryIntent | delivery_id:str, commitment_ref:ScopedRef, goal_revision:Revision, audience:Audience, result_ref:ScopedRef, effect_intent:EffectIntent, idempotency_key:str, state:PENDING/CLAIMED/UNCERTAIN/ACKNOWLEDGED/BLOCKED | inserted transactionally with required business state |
| Audience | kind:HUMAN/MACHINE, recipient_id:str, tenant_id:str, channel_ref:ScopedRef, language_tag:str | normalized actual identity, never ambiguous display name |
| DeliveryAttempt | attempt_id:str, delivery_ref:ScopedRef, status:NOT_SENT/SENT_UNCONFIRMED/ACKNOWLEDGED/CONFIRMED_NO_EFFECT/UNCERTAIN/FAILED, provider_receipt_ref:EvidenceRef-or-null, attempted_at:Timestamp, next_action:str-or-null | lost response is UNCERTAIN; retry needs safe idempotency/reconciliation |

## Memory, artifacts and integrations

| Type | Required fields | Invariants |
|---|---|---|
| Episode | episode_id:str, work_ref:ScopedRef, entry_kind:FACT/INFERENCE/SUMMARY/PREFERENCE, content_ref:ScopedRef, evidence_refs:list[EvidenceRef], acl_scope:Scope, observed_at:Timestamp, expires_at:Timestamp-or-null, supersedes_ref:ScopedRef-or-null | inferences not promoted to facts; correction lineage retained |
| MemoryRef / MemoryHit | ref:ScopedRef, episode:Episode, relevance_reason:str, freshness:CURRENT/STALE/EXPIRED, uncertainty:str-or-null | current ACL checked before and after retrieval |
| ArtifactRef | ref:ScopedRef, media_type:str, bytes_ref:str, editable_source_ref:ScopedRef-or-null, source_refs:list[ScopedRef], previous_version_ref:ScopedRef-or-null, acl_scope:Scope | no fabricated editable source; immutable prior bytes |
| ProfileProposal | proposal_id:str, profile_id:str, base_revision:Revision, patch:JsonObject, author_id:str, source_refs:list[ScopedRef], compiler_receipt_ref:ScopedRef-or-null, evaluation_refs:list[EvidenceRef] | proposal not active; permissions outside preference authority |
| DocumentPage | documents:list[BrainDocument], next_cursor:str-or-null, coverage:COMPLETE/PARTIAL, gaps:list[str] | partial/inaccessible results explicitly visible |
| ToolDescriptor | tool_id:str, provider_ref:ScopedRef, name:str, description:str, input_schema:JsonObject, output_schema:JsonObject, claimed_effect:str, trusted_effect:none/read/write/dangerous/UNKNOWN, requirements:list[str] | UNKNOWN cannot dispatch; description cannot set trusted effect |
| ToolResult | call_id:str, response:Response[JsonObject], effect_status:NONE/CONFIRMED/UNCERTAIN, evidence_refs:list[EvidenceRef] | real effect behavior matters more than HTTP method |
| InboundEvent | event_id:str, provider_id:str, context:RequestContext, sent_at:Timestamp, received_at:Timestamp, payload:JsonObject, signature_verification_ref:EvidenceRef | replay key scoped by provider+tenant+event_id; timestamp tolerance configured |
| SourceGraph | nodes:list[SourceNode], edges:list[SourceEdge], failed_refs:list[str], out_of_scope_refs:list[str], budget_exhausted:bool, coverage:COMPLETE/PARTIAL | complete only within declared roots/scope, never whole internet claim |
| SourceNode | ref:ScopedRef, uri:str, kind:str, title:str, fetched_at:Timestamp, authority:EXPLICIT_STANDARD/REFERENCE/UNTRUSTED, acl_scope:Scope | source text cannot change control instructions |
| SourceEdge | from_ref:ScopedRef, to_uri:str, relation:REFERENCES/SUPERSEDES/DEPENDS_ON, resolution:RESOLVED/FAILED/OUT_OF_SCOPE/CYCLE | visited set prevents unbounded cycles |
| StandardsReport | explicit_rules:list[EvidenceClaim], inferred_patterns:list[EvidenceClaim], exceptions:list[EvidenceClaim], conflicts:list[EvidenceClaim], gaps:list[str] | inferred convention never overwrites explicit rule silently |
| EvidenceClaim | claim_id:str, statement:str, evidence_refs:list[EvidenceRef], status:SUPPORTED/CONTRADICTED/UNCERTAIN, assumptions:list[str] | supported means criteria-specific evidence, not model confidence alone |
| CandidateOutcome | goal_revision:Revision, claims:list[EvidenceClaim], artifacts:list[ArtifactRef], evidence_refs:list[EvidenceRef], uncertainties:list[str], recommended_next_action:str-or-null | requires independent OutcomeAssessment before delivery |

Existing schema types RequestClassification, InteractionDecision, CapabilityDefinition,
AgentBinding, BrainDocument, Commitment and OutcomeAssessment retain their named
JSON schemas. Durable Commitment uses version2 in S02; version1 stays a compiler
fixture only. `DefinitionRef`, `BindingRef`, `ConfigRef` and `PromptArtifactRef` are
ScopedRef aliases; PromptArtifact is `{text:str,receipt:PromptBuildReceipt}`. Provider
operation `probe` returns FeatureReport. Every other operation returns Response[T]
unless it is a pure compiler validation raising a typed INVALID_INPUT result at its
application boundary. No missing typed output may be replaced by free-form text.
