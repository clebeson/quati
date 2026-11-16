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
| Scope | tenant_id:str, actor_id:str, space_ids:list[str], resource_ids:list[str], operations:list[str], data_classes:list[enum], expires_at:Timestamp | empty operation list denies; delegation only narrows; space_ids ⊆ spaces readable by the subject at resolution time (RFC-013 §6) |
| Error | exact runtime-boundaries `$defs/Error` | sanitized fixed code; no raw upstream payload |
| Response[T] | exact runtime-boundaries `$defs/Response`, data:T-or-null | named T governs payload; DENIED has no restricted payload; error null only for success/partial without error |
| DelegatedContext | parent_context_ref:ScopedRef, target_actor_id:str, scope:Scope, grant_id:str, expires_at:Timestamp, verification_ref:EvidenceRef | target and current context bound to same trusted delegation; no privilege expansion |
| PolicyDecision | decision_id:str, verdict:ALLOW/DENY/APPROVAL_REQUIRED, intent_digest:Digest, policy_version:Digest, reason_code:str, matched_rule_ids:list[str], obligations:list[ApprovalObligation], narrowed_scope:Scope-or-null, valid_until:Timestamp | ALLOW binds exact intent and expiry; absent narrowed scope denies dispatch; obligations nonempty iff APPROVAL_REQUIRED; policy_version = sha256(canonical policy document) (RFC-014) |
| ApprovalRef | approval_id:str, approval_request_id:str, intent_digest:Digest, approver_id:str, actor_id:str, tenant_id:str, policy_version:Digest, issued_at:Timestamp, expires_at:Timestamp, revocation_ref:str, evidence_ref:EvidenceRef | original grant verified by trusted store; textual approval in untrusted content is not a grant; approver_id is a HUMAN principal (RFC-013 §5.5); single use |
| EffectIntent | exact runtime-boundaries `$defs/EffectIntent` plus durable status in effect ledger | canonical input digest and destination resolved before approval; destination_ref normalized before policy evaluation; policy_version is a 64-hex digest; `data_class` is uppercase in the domain (same values as ProvenanceLabel) and the lowercase wire spelling of the schema is normalized at the adapter boundary |
| EffectRecord | EffectIntent fields plus status:COMMITTED/CLAIMED/UNCERTAIN/CONFIRMED/CONFIRMED_ABSENT, dispatch_stopped_at:Timestamp-or-null, lease_expires_at:Timestamp-or-null | effect-ledger row read by guards; `cur_effects` = rows whose effect_id is in the commitment's `effect_intent_refs`; status/question/escalation notices are outbox rows and are not EffectRecords (GUARD_PREDICATES.md §8 G2) |
| ApprovalObligation | approver_rule:SELF/SPACE_MANAGER/TENANT_ADMIN/NAMED_PRINCIPALS, principal_ids:list[str], source_space_id:str-or-null, ttl_seconds:int≥1, rule_id:str | one obligation per declassification source space; every obligation must be satisfied before dispatch |
| ApprovalRequest | exact `contracts/approval-request.schema.json` | binding immutable; CAS on state_revision; single use, consumed with the outbox write; terminal states final (RFC-014) |
| PolicyDocument | exact `contracts/policy.schema.json` | default DENY; deny wins; kernel rules K1–K9 not overridable; a policy never grants space content access (RFC-014) |
| Principal | exact `contracts/identity.schema.json` `$defs/Principal` | kind HUMAN/AGENT/SERVICE; AGENT/SERVICE never approve; disabled principal ⇒ all tokens rejected (RFC-013) |
| Group, Membership | exact identity schema `$defs/Group`, `$defs/Membership` | groups are flat; tenant role OWNER/ADMIN/MEMBER/GUEST(+AUDITOR); admin role confers no content access |
| Space, SpaceGrant | exact identity schema `$defs/Space`, `$defs/SpaceGrant` | kind PERSONAL/TEAM/ORGANIZATION/SHARED; roles READER/CONTRIBUTOR/MANAGER; every data object carries one space_id |
| AccessTokenClaims | exact identity schema `$defs/AccessTokenClaims` | carries no space grants (resolved live); never placed in model input, logs or evidence; delegated tokens carry `act`, depth ≤ 3 |
| AuthorizedScope | exact identity schema `$defs/AuthorizedScope` | computed by trusted runtime per transaction; applied as a pre-filter before ranking and re-checked on fetch |
| ProvenanceLabel | exact identity schema `$defs/ProvenanceLabel` | computed_by trusted_runtime; write/deliver allowed only if readers(target) ⊆ readers(source), else APPROVAL_REQUIRED by source MANAGER |
| AuthzDecision | exact identity schema `$defs/AuthzDecision` | default deny; valid only for the current transaction |

## Interaction, execution and delivery

| Type | Required fields | Invariants |
|---|---|---|
| ContextEnvelope | schema_version:str, goal:str, context:RequestContext, policy_ref:ScopedRef, work_ref:ScopedRef-or-null, work_revision:Revision-or-null, recent_turns:list[TurnSummary], evidence_refs:list[EvidenceRef], uncertainties:list[str], permitted_actions:list[str], candidates:list[CandidateSummary], budget:Budget | protected facts cannot be trimmed; low-trust text explicitly separated |
| TurnSummary | turn_id:str, speaker_ref:str, source_trust:TRUSTED_ORIGIN/UNTRUSTED_CONTENT, text:str, observed_at:Timestamp, work_revision:Revision-or-null | attributed speaker text is not authenticated origin |
| TurnResult | turn_id:str, conversation_id:str, conversation_revision:Revision, decision:InteractionDecision, work_ref:ScopedRef-or-null, response:Response[JsonObject] | accepted work/ref semantics depend on slice; no durable promise before S02 |
| ModelResult | text:str, classification:RequestClassification, tool_calls:list[ToolCallObservation], usage:Usage, effective_prompt_hash:Digest, model_id:str, provider_id:str, config_hash:Digest, observed_features:FeatureReport, evidence_refs:list[EvidenceRef] | text is advisory; cannot establish completion/authority |
| ToolCallObservation | call_id:str, operation:str, arguments_digest:Digest, result_digest:Digest-or-null, status:REQUESTED/DENIED/SUCCEEDED/FAILED/UNCERTAIN, evidence_ref:EvidenceRef | raw synthetic arguments only in explicitly approved evaluator record |
| Usage | requests:int≥0, tool_calls:int≥0, input_tokens:int-or-null, output_tokens:int-or-null, cost_usd:decimal-string-or-null, elapsed_ms:number≥0 | null means unknown; costs include probe/repair calls; no fabricated zero |
| FeatureReport | provider_id:str, transport:str, model_or_adapter_version:str, config_hash:Digest, measured_at:Timestamp, features:map[str,SUPPORTED/UNSUPPORTED/NOT_VERIFIED], observations:map[str,reason code], aborted:error code or null, evidence_refs:list[EvidenceRef], metadata_attestations:map[str,str-or-null] | protocol observation and residency/pricing attestations distinct |
| CandidateSummary | capability_id:str, capability_version:str, name:str, outcome_summary:str, effects:none/read/write/dangerous, eligible_binding_refs:list[ScopedRef], assurance_ref:ScopedRef-or-null, rank_reasons:RankReasons | no unverified manifest self-claim used as assurance |
| RankReasons | filter_results:list, bm25:float, rank:int, shortlist_k:int | structured, one object per candidate (M15); filter reason codes NOT_AUTHORIZED/EFFECT_ABOVE_CEILING/DATA_CLASS_ABOVE_CEILING/BINDING_UNHEALTHY/MODEL_INCOMPATIBLE/COST_ABOVE_CAP/NOT_ENABLED; the element shape of filter_results is not fixed by M15 |
| RegistryRecord | exact `contracts/capability-registry-record.schema.json` (lifecycle DRAFT/VALIDATED/STAGED/ENABLED/DEPRECATED/DISABLED; assurance C0..C5) plus definition_ref:ScopedRef, binding_refs:list[ScopedRef], previous_revision:Revision-or-null | lifecycle and assurance are registry-owned, never read from the manifest; ENABLED needs a HUMAN ApprovalRef and assurance ≥ C2; any digest change expires assurance; immutable history (RFC-015) |
| ExecutionRef | execution_id:str, commitment_ref:ScopedRef-or-null, capability_ref:ScopedRef, binding_ref:ScopedRef | workflow engine ID stays adapter-side; transient prototype explicitly has null commitment |
| ExecutionStatus | execution_ref:ExecutionRef, state:PENDING/RUNNING/WAITING/SUCCEEDED/FAILED/CANCEL_REQUESTED/CANCELLED/UNKNOWN, result_ref:ScopedRef-or-null, next_action:str-or-null, evidence_refs:list[EvidenceRef] | execution SUCCEEDED is not user outcome DELIVERED; vocabulary is RFC-003 §2 and `contracts/durable-execution` (authoritative); UNKNOWN is reconciled, never restarted |
| DeliveryIntent | delivery_id:str, commitment_ref:ScopedRef, goal_revision:Revision, audience:Audience, result_ref:ScopedRef, effect_intent:EffectIntent, idempotency_key:str, state:PENDING/CLAIMED/UNCERTAIN/ACKNOWLEDGED/BLOCKED | inserted transactionally with required business state; authoritative domain state; the delivery-envelope wire state is derived by the mapping table in `docs/prds/M10.md` |
| Audience | kind:HUMAN/MACHINE, recipient_id:str, tenant_id:str, channel_ref:ScopedRef, language_tag:str | normalized actual identity, never ambiguous display name; a group is HUMAN whose `channel_ref` membership the trusted sink adapter resolves to more than one reader (no GROUP kind); wire `recipient_kind` is `human`/`system`, mapped at the adapter (M10) |
| DeliveryAttempt | attempt_id:str, delivery_ref:ScopedRef, status:NOT_SENT/SENT_UNCONFIRMED/ACKNOWLEDGED/CONFIRMED_NO_EFFECT/UNCERTAIN/FAILED, provider_receipt_ref:EvidenceRef-or-null, attempted_at:Timestamp, next_action:str-or-null | lost response is UNCERTAIN; retry needs safe idempotency/reconciliation |
| ResultRecord | result_id, commitment_id, goal_revision, status, data_ref, evidence_refs:list, uncertainties:list, next_action, error, source_space_ids:list, data_class, content_digest | input of the pure audience adapters; rendering never changes status, evidence or uncertainties (M10) |
| WorkSnapshot | event_source:USER_TURN/TIMER/ASYNC_RESULT, work_ref:ScopedRef-or-null, work_revision:Revision-or-null, state, resolution:ReferenceResolution, clarification:ClarificationVerdict, plan:CommunicationPlan, result (ASYNC_RESULT only: the result envelope with its commitment_id and the M09 OutcomeAssessment) | read from one committed revision; `classification` passed alongside is null for TIMER and ASYNC_RESULT (M03) |
| ReferenceResolution | verdict:NO_REFERENCE/UNRESOLVED/AMBIGUOUS/RESOLVED, candidates:list[{ref, features:{exact_id, title_overlap, time_window, ownership, recency}, score, observed_at}], top_gap, assumptions:list[str] | deterministic function of its inputs and `now`; AMBIGUOUS never binds a work ref (M04) |
| ClarificationVerdict | verdict:ASK_BLOCKING/START_SAFE_WORK/START_SAFE_WORK_WITH_OPTIONAL_QUESTION/WAIT_OPEN_QUESTION/NO_WORK, question_field:str-or-null, question_blocking:bool, safe_work:list[capability_id], candidates:list[ref], reason_code:str | at most one question per turn (M05) |
| CommunicationPlan | kind:receipt/progress/blocking_question/delay_notice/partial_result/final_delivery-or-null, suppressed:bool, suppression_reason:str-or-null, urgent_override:bool, next_contact_at:Timestamp, escalation_trigger_at:Timestamp-or-null, reason_code:str | pure function of commitment snapshot, event, clock, policy and availability; timers scheduled through DurableRunner (M06) |
| TriageMeta | model_role:small/strong, priority:P0/P1/P2/P3, route_row:R0..R9, route_table_id, policy_hash, budget_used:{requests, tool_calls, output_tokens, elapsed_s}, reason_code | returned with RequestClassification by `classify_turn`; never edits the classification (M08) |
| AuditEvent | EventEnvelope fields plus event_hash:Digest, prev_event_hash, space_ids:list, act_chain:list, jti, decision, reason_code, status, taint_labels:list, recorded | event_hash = sha256(`quati-json/1` {envelope, recorded, payload_digest, prev_event_hash}); append-only hash chain (M26) |
| CapabilityExplanation | commitment_id, selected:{capability_id, version, binding_hash}, candidates:list[{capability_id, version, rank_features, authorization:ALLOW/DENY/APPROVAL_REQUIRED, excluded_reason:scope_not_granted/outcome_mismatch/capability_unavailable/policy_denied/lower_rank}], policy_decision_id, model_id, provider_id, effective_prompt_hash, model_rationale:{text, advisory:true}-or-null, event_ids:list | built from recorded events only; model rationale is advisory (M26) |
| ReplayReport | trace_id, steps:list[{event_id, kind, outcome:MATCH/DIVERGED/NOT_RECORDED/BLOCKED, model_reproducibility:RECORDED_ONLY/SNAPSHOT_MATCHED/NOT_REPRODUCIBLE-or-null}], fully_reproducible:bool, provider_calls:0, effect_calls:0 | fully_reproducible only when every model step is SNAPSHOT_MATCHED (M26-RT-01) |
| ExportManifest | path, event_count, first_event_hash, last_event_hash, redacted_fields:int, scanner_version | export is redacted and bounded by `audit.export_max_events` (M26) |
| WorkItem | work_item_id, tenant_id, space_id, commitment_id, kind, status:READY/LEASED/DONE/FAILED/CANCELLED, lease_owner, lease_expires_at, attempt, max_attempts, not_before | ledger-owned; one claimant per lease; expired lease reclaimable (ADR-015); `attempt` is the lease epoch (fencing token) that every worker commit must match (RFC-003 §3) |
| TimerIntent | exact `contracts/timer-intent.schema.json` | fires at most once; past fire_until ⇒ EXPIRED with audit event; late fire records late_by_seconds (ADR-016) |
| InboxMessage | exact `contracts/inbox-message.schema.json` | DELIVERED on commit, ACKNOWLEDGED on read; scoped by tenant and space |
| WorkerHeartbeat, WorkerLock | deployment_id, worker_id/owner_id, beat_at, interval_seconds, profile, lease_expires_at | one active worker per LOCAL deployment; missing heartbeat for 2× interval ⇒ doctor warning |

## Memory, artifacts and integrations

| Type | Required fields | Invariants |
|---|---|---|
| Episode | episode_id:str, tenant_id:str, space_id:str, work_ref:ScopedRef, requester_ref:str, project_ref:str-or-null, method_ref:ScopedRef-or-null, entry_kind:FACT/INFERENCE/SUMMARY/PREFERENCE, status:ACTIVE/QUARANTINED/SUPERSEDED/EXPIRED, trust_origin:USER/OWNER_DOCUMENT/THIRD_PARTY/MODEL, author_ref:str, confidence:float[0,1], content_ref:ScopedRef, content_sha256:Digest, evidence_refs:list[EvidenceRef], provenance:ProvenanceLabel, observed_at:Timestamp, recorded_at:Timestamp, valid_from:Timestamp-or-null, valid_to:Timestamp-or-null, expires_at:Timestamp-or-null, supersedes_ref:ScopedRef-or-null, revision:Revision, claim_key:str-or-null | `revision` is the compare-and-set value for `correct`; `claim_key` is the normalized subject key for conflict detection (M11); inferences not promoted to facts; quarantine rule of RFC-005 rule 3 (a–e; M11): every THIRD_PARTY write is QUARANTINED for every entry_kind; a MODEL FACT or PREFERENCE is QUARANTINED; a MODEL INFERENCE or SUMMARY is QUARANTINED unless it has at least one evidence_ref and all of them resolve to non-quarantined USER/OWNER_DOCUMENT sources; a quarantined episode is excluded from search, the core profile and any trusted context; release only through `MemoryPort.confirm` by a HUMAN owner of the space, audited, changing status only; correction invalidates (valid_to/SUPERSEDED), never deletes; rendered to models as data, never as instruction (RFC-005) |
| MemorySnapshot | snapshot_id:str, tenant_id:str, space_id:str, base_snapshot_ref:ScopedRef-or-null, state:CANDIDATE/ACTIVE/DISCARDED/ROLLED_BACK, entry_count:int≥0, bytes:int≥0, run_ref:ScopedRef, verification_refs:list[EvidenceRef], approval_ref:ScopedRef-or-null | one ACTIVE per space; activation and rollback are one ledger transaction; candidate never modifies the base (RFC-005 v8.2) |
| ConsolidationRun | run_id:str, tenant_id:str, space_id:str, input_snapshot_ref:ScopedRef, output_snapshot_ref:ScopedRef-or-null, model_ref:str, prompt_digest:Digest, budget:Budget, dropped_entries:list[str], status:QUEUED/RUNNING/SUCCEEDED/FAILED | reads one space only; cannot raise trust_origin or un-quarantine; size budget enforced |
| MemoryRef / MemoryHit | ref:ScopedRef, episode:Episode, relevance_reason:str, freshness:CURRENT/STALE/EXPIRED, uncertainty:str-or-null | current ACL checked before and after retrieval; `relevance_reason` is serialized JSON `{"matched_filters":[...],"text_score":float,"rank":int}` (M11) |
| MemoryQuery | text:str, requester_ref:str-or-null, project_ref:str-or-null, method_ref:ScopedRef-or-null, work_ref:ScopedRef-or-null, time_from:Timestamp-or-null, time_to:Timestamp-or-null, relative_time:LAST_WEEK/THIS_WEEK/LAST_MONTH-or-null, entry_kinds:list[FACT/INFERENCE/SUMMARY/PREFERENCE], include_history:bool (default false), limit:int | text ≤ `memory_policy.query_max_chars`; empty entry_kinds means all; relative_time and an absolute window are mutually exclusive (INVALID_INPUT `TIME_FILTER_CONFLICT`) (M11) |
| ArtifactRef | ref:ScopedRef, media_type:str, bytes_ref:str, editable_source_ref:ScopedRef-or-null, source_refs:list[ScopedRef], previous_version_ref:ScopedRef-or-null, acl_scope:Scope, artifact_id:str, version:int≥1, content_sha256:Digest, format_profile:CHART_VEGALITE5_CSV/MARKDOWN/BINARY_OPAQUE, summary_ref:ScopedRef-or-null | no fabricated editable source; immutable prior bytes |
| ChangeRequest | kind:ADD_SERIES, series_name:str, values:list[{x:str, y:number}], source_refs:list[ScopedRef] | any other kind is UNSUPPORTED `CHANGE_KIND_UNSUPPORTED` in S03 (M12) |
| ArtifactSummary | artifact_id:str, version:int, text:str, created_at:Timestamp | text ≤ `artifact_policy.summary_max_chars` (M12) |
| ProfileProposal | proposal_id:str, profile_id:str, base_revision:Revision, patch:JsonObject, author_id:str, source_refs:list[ScopedRef], compiler_receipt_ref:ScopedRef-or-null, evaluation_refs:list[EvidenceRef] | proposal not active; permissions outside preference authority |
| PreferenceRecord | record_id, profile_id, key, value, source_kind:EXPLICIT/OBSERVED/INFERRED, confidence:float[0,1], scope:USER/GROUP/TENANT, owner_id, status:ACTIVE/SUPERSEDED/EXPIRED, observations:int, signal_refs:list[ScopedRef], created_at, expires_at:Timestamp-or-null, version:int | key ∈ `preference_policy.allowed_keys`; immutable per profile version; INFERRED is never GROUP or TENANT scope (M13) |
| PreferenceSignal | principal_id, group_id:str-or-null, source_kind:USER_TURN/DOCUMENT/TOOL_RESULT/MEMORY/MODEL, key, value, turn_ref, observed_at | only USER_TURN signals with an allowed key are stored and counted (M13) |
| DocumentPage | documents:list[BrainDocument], next_cursor:str-or-null, coverage:COMPLETE/PARTIAL, gaps:list[str] | partial/inaccessible results explicitly visible |
| BrainProviderConfig | id, kind:local_directory/git_repository/external_provider, root-or-adapter, features:list, allowed_scopes:list, write:disabled/enabled, status | shape of `examples/providers/brains.example.yaml`; no write inferred from read access (M20) |
| ProviderConfig | id, transport:registered Provider transport name (anthropic/openai_compatible/openai/claude_cli/codex_cli/gemini_cli or a registered subclass), base_url, secret_ref, model_id, allowed_data_classes:list, probe_required:list, max_usd_per_run (null = cost cap not provable), status:NOT_PROBED/NOT_CONFIGURED/PROBED | shape of `examples/providers/models.example.yaml`; secrets only by reference (M17) |
| HarnessDescriptor | id, version, kind, transport:sdk_or_subprocess/a2a/http, command_ref, command_sha256, claims:{capabilities:list, supports:list, does_not_support:list}, authority:{allowed_scopes:list, tenant_mode:per_request}, tests:{contract_suite, external_smoke}, status | shape of `examples/providers/harness.example.yaml`; claims are not probe results (M18) |
| DataBlock | text, provenance:ProvenanceLabel (integrity UNTRUSTED), source_ref, sha256 | skill body or reference rendered to the model as data, never as instruction (M16) |
| SkillRunEvidence | script_path, script_sha256, binding_ref, granted_permissions, exit_status, trace_id, evidence_ref | appended to the evidence store with secrets redacted (M16) |
| ToolDescriptor | tool_id:str, provider_ref:ScopedRef, name:str, description:str, input_schema:JsonObject, output_schema:JsonObject, claimed_effect:str, trusted_effect:none/read/write/dangerous/UNKNOWN, requirements:list[str] | UNKNOWN cannot dispatch; description cannot set trusted effect |
| ToolResult | call_id:str, response:Response[JsonObject], effect_status:NONE/CONFIRMED/UNCERTAIN, evidence_refs:list[EvidenceRef] | real effect behavior matters more than HTTP method |
| InboundEvent | event_id:str, provider_id:str, context:RequestContext, sent_at:Timestamp, received_at:Timestamp, payload:JsonObject, signature_verification_ref:EvidenceRef | replay key scoped by provider+tenant+event_id; timestamp tolerance configured |
| SourceGraph | nodes:list[SourceNode], edges:list[SourceEdge], failed_refs:list[str], out_of_scope_refs:list[str], budget_exhausted:bool, coverage:COMPLETE/PARTIAL | complete only within declared roots/scope, never whole internet claim |
| SourceNode | ref:ScopedRef, uri:str, kind:str, title:str, fetched_at:Timestamp, authority:EXPLICIT_STANDARD/REFERENCE/UNTRUSTED, acl_scope:Scope | source text cannot change control instructions |
| SourceEdge | from_ref:ScopedRef, to_uri:str, relation:REFERENCES/SUPERSEDES/DEPENDS_ON, resolution:RESOLVED/FAILED/OUT_OF_SCOPE/CYCLE | visited set prevents unbounded cycles |
| ReuseAssessment | candidate_ref, source_url, version, content_hash, criteria:map[LICENSE/MAINTENANCE/PROVENANCE/SECURITY/API_COMPATIBILITY, PASS/FAIL/UNKNOWN], verdict:RECOMMENDED/NOT_RECOMMENDED/UNVERIFIED, local_validation_note:str, evidence_refs | result of `DiscoveryResearch.assess_reuse` (M21) |
| FetchResult | ref, final_ref, status, content_type, bytes, content_hash | result of the internal `SourceFetcher.fetch` (M21) |
| StandardsReport | explicit_rules:list[EvidenceClaim], inferred_patterns:list[EvidenceClaim], exceptions:list[EvidenceClaim], conflicts:list[EvidenceClaim], gaps:list[str] | inferred convention never overwrites explicit rule silently |
| EvidenceClaim | claim_id:str, statement:str, evidence_refs:list[EvidenceRef], status:SUPPORTED/CONTRADICTED/UNCERTAIN, assumptions:list[str], kind:EVIDENCE/ASSUMPTION/RECOMMENDATION/OPEN_DECISION | supported means criteria-specific evidence, not model confidence alone; `kind` is required by M22 |
| HypothesisClaim | EvidenceClaim fields plus label:CAUSE/CORRELATE/SPECULATION/REFUTED, supporting_refs, refuting_refs, mechanism, source_ids | incident hypothesis label is separate from EvidenceClaim.status (M23) |
| CausalHypothesis | dag_nodes, dag_edges, treatment, outcome, adjustment_set, assumptions:list[{text, status:DECLARED/UNKNOWN, source_ref}] | DAG with named treatment, outcome and adjustment set (M24) |
| Estimate | kind:ASSOCIATION/CAUSAL_UNDER_ASSUMPTIONS, method, value, ci_low, ci_high, n, strata:list[{name, n, value}], reversal:bool, computation_ref, dataset_hash | causal wording allowed only for CAUSAL_UNDER_ASSUMPTIONS (M24) |
| CandidateOutcome | goal_revision:Revision, claims:list[EvidenceClaim], artifacts:list[ArtifactRef], evidence_refs:list[EvidenceRef], uncertainties:list[str], recommended_next_action:str-or-null, producer_actor_id:str | requires independent OutcomeAssessment before delivery; assessor_actor_id ≠ producer_actor_id (GUARD_PREDICATES.md §8 G3) |
| GuardEvent | name:control event enum, envelope:EventEnvelope, expected_revision:Revision, payload:typed per event (GUARD_PREDICATES.md §3.1) | expected_revision and payloads are proposed schema gap G1 |
| CommitmentUsage | requests:int≥0, tool_calls:int≥0, output_tokens:int≥0, cost_usd:decimal-string-or-null | aggregated from the ledger for the commitment, never model-reported (GUARD_PREDICATES.md §8 G6) |
| GuardInput | commitment, snapshot_committed:bool, event:GuardEvent, context:RequestContext, token_revoked:bool, now:Timestamp, active_policy_version:Digest-or-null, policy_decision, approval, effects:list[EffectRecord], attempts:list[DeliveryAttempt], delivery, assessment, candidate_producer_actor_id, evidence:list[EvidenceRef], classification, budget:Budget, usage:CommitmentUsage, config | loaded from one committed snapshot before evaluation; guards are pure functions of it (GUARD_PREDICATES.md §2-3) |
| EvolutionCandidate | candidate_id, kind:PROMPT/BEHAVIOR/SKILL/ROUTING/STATECHART, parent_digest, candidate_digest, author_id, author_model_id, permission_diff, state:STAGED/EVALUATED/PROMOTED/SUPERSEDED/ROLLED_BACK/REJECTED | a candidate cannot approve or promote itself (M27) |
| EvaluationReport | dataset_digest, holdout_digest, identity:{model_id, provider_id, config_hash, budget_hash}, baseline:{n, passes, wilson_low}, candidate:{n, passes, wilson_low}, safety_regressions:list[case_id], judge:{model_id, provider_id} | baseline and candidate compared under one dataset/config identity; any safety regression vetoes promotion (M27) |
| PromotionDecision | decision:PROMOTED/DENIED/ROLLED_BACK, reason, active_digest, rollback_target_digest, approval_ref | returned by `promote` and `rollback` (M27) |
| LifecycleReport | operation, status, os:{family, version, arch}, package_digest, checks:list[{name, status:PASS/FAIL/NOT_MEASURED, value, unit, evidence_ref}], profile:LOCAL_DEV/ENTERPRISE_HA | each OS reported separately; unmeasured checks are NOT_MEASURED, never PASS (M28) |
| BackupManifest | backup_id, created_at, schema_version, policy_digest, ledger_digest, files:list[{path, sha256}] | restore verifies digests, schema and policy before activation (M28) |

Fields listed without a type in the rows above are named by the owning PRD without a
type; the PRD cited in the row stays the source until it fixes one. Additions over the
named JSON schemas, pending the matching `contracts/` change: Commitment carries
`space_id:str` (GUARD_PREDICATES.md §8 G8) and the M06 contact fields `next_contact_at`,
`escalation_trigger_at`, `last_contact_at` and `last_unsolicited_at`; OutcomeAssessment
carries `assessor_actor_id:str` and `assessed_at:Timestamp` (G3), `assessor_kind`
RULES/JUDGE_MODEL and, in its trace, `stripped_fields:list[str]` (M09); BrainDocument as
returned carries `freshness:CURRENT/STALE/UNKNOWN` (M20). M09 label vocabularies:
`claim_kind` DESCRIPTIVE/CAUSAL/PREDICTIVE (unlabelled = CAUSAL) and `support_kind`
DIRECT/CORRELATIONAL/TESTIMONIAL (unlabelled = CORRELATIONAL). `EffectivePreferences`
(M13), `AuditFilter`, `AuditEventView` (M26), `DataQualityRecord` (M24),
`ValidationReport` (M30) and `RenderedPayload` (M10) are named by their PRDs without a
field list and are open specification gaps, not free-form types.

Existing schema types RequestClassification, InteractionDecision, CapabilityDefinition,
AgentBinding, BrainDocument, Commitment and OutcomeAssessment retain their named
JSON schemas. Durable Commitment uses version2 in S02 and carries optional `priority` P0..P3 (M08-FR-01 proposes it, M07 persists it; the due time is the existing `deadline_at`, no separate `due_at`); version1 stays a compiler
fixture only. `DefinitionRef`, `BindingRef`, `ConfigRef` and `PromptArtifactRef` are
ScopedRef aliases; PromptArtifact is `{text:str,receipt:PromptBuildReceipt}`. Provider
operation `probe` returns FeatureReport. Every other operation returns Response[T]
unless it is a pure compiler validation raising a typed INVALID_INPUT result at its
application boundary. No missing typed output may be replaced by free-form text.

## Executive decision thresholds

`DecisionPolicy` is the complete `decision-policy/1` document in
`contracts/decision-policy.schema.json`: positive revision, behavior_policy and
routing_policy. Its canonical JSON digest is `decision_policy_hash`, distinct from
PolicyDecision.policy_version (authorization). Operator-owned configuration cannot
remove the minimum blocking fields or add an authorization bypass. S00-T02 validates
the contract; S01-T02 consumes it. See DECISION_RULES.md section 4.
