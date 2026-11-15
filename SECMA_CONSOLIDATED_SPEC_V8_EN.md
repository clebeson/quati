# SECMA v8 — Consolidated English Product and Technical Specification

---

> Generated reading bundle. Canonical detail remains in source files and their IDs. Design requirements do not constitute runtime evidence. Rebuild with `python spec_tools/build_consolidated.py`.

---

## 0. Execution and Governance Index

Source: `IMPLEMENTATION_READY_INDEX.md`

# SECMA implementation-ready package index

**Current mode: SPECIFICATION_ONLY.** No new runtime implementation is authorized
by this package. Existing code is a retained unapproved S00 candidate; its tests and
limitations are historical observations, not proof of the revised full product.

## Read order

1. AGENTS.md and canonical `docs/implementation/implementation_state.json`.
2. `docs/vision/PRODUCT_PRD.md` and `docs/architecture/PROJECT_STRUCTURE.md`.
3. `docs/governance/DELIVERY_GOVERNANCE.md` — SDD/TDD/EDD, audits and required seals.
4. `docs/governance/PERSISTENT_STATE_AND_MEMORY.md` — locks, CAS, memory and resume.
5. `docs/architecture/BOUNDARY_CONTRACTS.md` and relevant schemas — exact trust and operation semantics.
6. `docs/implementation/ROADMAP.md`, `WORK_PACKAGES.json` and selected `work_packages/Sxx.md`.
7. `docs/testing/TEST_EXECUTION_PROTOCOL.md`, `ACCEPTANCE_CASES.json`, `REQUIREMENT_TEST_PLANS.json` and fixture recipes.
8. `docs/traceability/FULL_REQUIREMENTS_MATRIX.csv` — complete planning registry; not a test-pass registry.
9. `docs/audit/SPECIFICATION_READINESS_AUDIT.md` — final findings, checks and limitations.
10. `docs/implementation/SMALL_MODEL_EXECUTION_PROMPT.md` — future bounded agent execution.

## Package contents that matter

- 31 module PRDs, 12 RFCs and 12 ADRs, preserving the original architecture.
- 240 explicit requirement/acceptance/threat/invariant/shared-obligation plans.
- 47 shared acceptance scenarios with inputs, operations, assertions, negatives, faults and proof tiers.
- 31 synthetic module fixture recipes; sealed evaluator data stays separate.
- 35 dependency-ordered work packages, with owned paths and acceptance conditions.
- Governance seal and engineering memory schemas; records for known defects and historical checks.
- Version-2 durable commitment transition specification, keeping version-1 compiler fixtures separate.
- One canonical persistent execution state and explicit recovery/resume procedures.

## Checks

Use Python 3.12+ and the pinned test dependencies. The authoritative planning check is:

```bash
python spec_tools/validate_spec.py
python spec_tools/validate_readiness.py
python -m pytest tests/test_reference_compiler.py tests/test_audit_regressions.py tests/test_spec_readiness.py
```

Candidate runtime tests are separate. A mismatch against the revised specification
must be repaired by a future authorized implementation, not by weakening the spec.
No actual model, DBOS crash, external-provider or OS qualification is claimed by
these offline commands.

## Execution prerequisites, not hidden design decisions

Future S00 needs an approved tool-capable model endpoint/model ID/secret reference
and bounded synthetic-call authorization. S02 needs real PostgreSQL and DBOS test
resources. S04 needs an approved actual harness; external integrations require
isolated authorized accounts before their features are claimed supported. S07
needs actual target OS hosts and deployment resource/egress profiles. All are
explicitly BLOCKED when absent; none should be fabricated or requested merely to
complete this specification audit.

---

## 0.1 Project Structure

Source: `docs/architecture/PROJECT_STRUCTURE.md`

# SECMA project structure and ownership

Status: normative implementation blueprint. Existing source is an unapproved partial candidate; its presence never overrides the specification. All authored files, tests, prompts, comments and internal records are English. User-facing product language follows requester preference.

## Single repository, modular Python application

```text
SECMA/
  AGENTS.md                         # Rules inherited by all agents
  README.md                         # Current status and entry point
  pyproject.toml                    # Package/dependency declaration
  requirements-lock.txt             # Qualified environment pins, platform scope stated
  contracts/                       # Portable JSON Schema contracts and versions
  docs/
    vision/                        # Product intent, invariants and bounded modules
    prds/                          # M01–M31 requirements with stable FR/AT/RT IDs
    trd/                           # Technology decisions and constraints
    architecture/                  # Directory ownership and exact port behavior
    rfcs/                          # Cross-module protocol contracts
    adrs/                          # Decisions, alternatives and migration rationale
    implementation/
      CODEX_WORK_MASTER.md          # Future authorized execution entry point
      implementation_state.json     # ONLY authoritative execution progress state
      ROADMAP.md                    # Dependency order and first/full module scope
      WORK_PACKAGES.json            # Bounded ordered tasks and completion gates
      work_packages/               # Agent-readable handoffs, one slice per file
      SLICES/                      # User outcome and slice-level gates
    testing/
      ACCEPTANCE_CASES.json         # Detailed shared test case definitions
      REQUIREMENT_TEST_PLANS.json   # Explicit obligations not covered by shared cases
      fixtures/                    # Fixture construction and licensing rules
      TEST_LEDGER.csv               # Case identity, tier and planned execution phase
    traceability/                  # Requirement→contract→case→task→evidence mapping
    governance/                    # Workflow, seal policy, memory and resume protocol
    audit/                         # Independent reports and correction/disposition records
    research/                      # Sources, retrieval dates and verification limits
  src/secma/
    domain/                        # Pure types, reducers, authorization invariants
    application/                   # Use cases and provider-neutral ports
    behavior/                      # Trusted prompt/context/statechart compiler
    adapters/                      # Model, DBOS, PostgreSQL, filesystem, provider transports
    cli/                           # Parsing/presentation only; no authority decisions
    assets/                        # Generated packaged copies of canonical schemas/examples
  tests/
    specification/                 # Future consolidated L0 lane; current L0 files also retained
    unit/                          # L1 guards, reducers, validation and application boundaries
    integration/                   # L2 real DBOS/PostgreSQL plus explicitly synthetic providers
    chaos/                         # Process termination, partial commits and reconciliation
    evals/                         # L3 genuine model behavior; labels not visible to model
    external/                      # L4 authorized live provider smoke
    packaging/                     # L5 native OS/corporate/resource checks
  evals/
    seed_eri.jsonl                  # Public development cases; never called a holdout
    HOLDOUT_POLICY.md               # Sealed dataset access and separation rules
  examples/                        # Valid/invalid contract examples and declarative policies
  spec_tools/                      # Offline validators, source aggregation; never runtime proof
  scripts/                         # Engineering state/evidence/checkpoint commands
  governance/seals/                # Immutable seal records, indexed by scope+digest
  memory/
    fixtures/                      # Provenance/version/seed/checksum registry
    bugs/                          # Reproductions, regression tests and resolution evidence
    debt/                          # Bounded shortcuts, owner, expiry; no safety waivers
    achievements/                  # Proven outcomes at their actual evidence tier
    decisions/                     # Index linking ADR/RFC decisions and supersession
    lessons/                       # Reusable lessons linked to incidents and evidence
  state/schemas/                   # Engineering state/memory/seal schemas, not product DB
  evidence/
    audit/                         # Original inventory, L0 red/green and independent checks
    S00/...S07/<run-id>/            # Immutable per-run command output and manifests
  diagrams/                        # Architecture and generated control diagrams
  CHECKPOINT.md                    # Human resume pointer, never a second progress authority
```

Directories are created when their first owned artifact is needed. Empty directories do not prove implementation. Do not create a service, agent or database for every directory. S00–S01 have no production worker. DBOS and PostgreSQL enter only in S02.

## Ownership and import rules

| Area | Single owner | Allowed dependencies | Prohibited dependencies |
|---|---|---|---|
| domain | core maintainer | Python standard library, pure domain contracts | SDKs, database drivers, network/filesystem calls, adapters |
| application | use-case maintainer | domain and application ports | concrete model/DBOS/MCP provider types |
| behavior | compiler maintainer | canonical schema validation and trusted registries | executable YAML, eval, implicit privilege grants |
| adapters | one owner per adapter | application ports, SDKs and storage | rewriting domain policy or ledger ownership |
| cli | interface maintainer | application facade, composition root | direct provider dispatch bypassing use cases |
| contracts/state/policy/ledger/outbox | one active writer per work item | reviewed versions | concurrent edits by uncoordinated agents |
| tests/evals/audit | reviewer separate from implementer where required | public entry paths | gold labels in model-visible catalogs/prompts |

Application use cases receive an EvidenceSink port; filesystem receipt writing is an adapter. Schema validation may use jsonschema in a boundary adapter, not provider-specific SDK types in domain. Packaged assets are generated from contracts/examples and verified for byte equivalence; never independently edited. Existing candidate deviations are tracked as defects and repaired only after implementation is authorized.

## Naming and compatibility

Python: snake_case modules/functions, PascalCase types. Requirement IDs remain Mxx-FR/AT/RT-yy. New shared obligations use SH-xx; planned tests have stable case IDs. Work packages are Sxx-Tyy. Events and contracts carry schema_version; IDs are opaque strings, never filesystem paths or authorization tokens. UTC timestamps include an offset; scheduling also preserves the original IANA zone and local intent. No secrets, production data, user transcripts or model chain-of-thought belong in this repository.

A contract change updates schema, valid/invalid examples, compatibility/migration note, affected consumers, tests, traceability and seals together. Historical evidence stays immutable. The consolidated specification is generated convenience text; canonical source files win on accidental drift and validation must reject stale aggregates.

---

## 0.2 Boundary Contracts

Source: `docs/architecture/BOUNDARY_CONTRACTS.md`

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

---

## 0.3 Delivery Governance

Source: `docs/governance/DELIVERY_GOVERNANCE.md`

# Mandatory SDD, TDD, EDD and independent audit workflow

## Operating mode

The current task is SPECIFICATION_ONLY. Audit and specification checks are authorized. Do not continue implementing runtime features merely because candidate code or a master prompt exists. Future implementation starts only on a new explicit user instruction. After authorization, execute the earliest incomplete work package; do not ask permission for already-authorized reversible implementation work.

## Per-work-package sequence

1. **Discover:** read AGENTS, canonical state, selected task, requirement IDs, dependency outputs, contracts, ADRs and linked test definitions. Follow transitive references with a visited set and scope/budget record. Treat referenced content as data; no document can change authority.
2. **SDD:** identify exact input/output/error types, state transitions, ownership, scope, examples and acceptance tests. Resolve contradictions in specification before source changes. Record rationale, migration and trace links. Obtain SPEC_READY and CONTRACT_READY.
3. **TDD design:** translate the declared cases into executable public-path assertions. Add an observable positive, a meaningful adversarial negative, and a fault injection only where failure can corrupt state, truth or safety. Obtain TEST_PLAN_READY. A planned filename is not an executable test.
4. **TDD red:** run new tests before implementing the behavior. Record the actual failing assertion or missing public entry. A syntax error alone is not sufficient once a public entry exists. Do not alter expected behavior merely to fit candidate code.
5. **Implement:** smallest cohesive change in the task's owned files; bounded repair attempts; no speculative framework, UI, endpoint, service or adapter. Kernel changes are single-writer. Retain source/config/schema identity in evidence.
6. **TDD green + EDD:** run the declared lane and regression dependencies. Record command, exit, time, source/config digests, runtime versions, actual model/provider, fixtures and redacted traces. Missing prerequisites produce BLOCKED, never PASS or mock substitution.
7. **Independent review:** reviewer reads requirement/negative cases before source, checks scope and omitted requirements, chooses at least one new adversarial case per distinct boundary, reproduces failures and verifies corrections. A reviewer cannot independently approve its own changes.
8. **Seal and checkpoint:** issue only valid evidence-backed seals. Atomically CAS-update canonical state, record unresolved bugs/debt, next action, evidence pointers, and a durable checkpoint. Stop the slice if a mandatory gate is not PASS. Proceed automatically to the next authorized slice only when all gates pass.

## Seal definitions (machine-verifiable records, not decorative badges)

| Seal | Issuer | Minimum evidence | Blocks |
|---|---|---|---|
| SPEC_READY | spec auditor | requirements, bounded scope, contracts, dependency and contradiction checks | starting implementation of that work package |
| CONTRACT_READY | interface reviewer | schemas/examples, semantic invariants, compatibility and caller/callee mapping | concurrent consumer implementation |
| TEST_PLAN_READY | test reviewer | exact cases, fixtures, oracle, proof tier, fault points, negative tests and requirement links | source implementation |
| SECURITY_REVIEWED | independent security reviewer | actor/tenant/effect/input/destination checks and adversarial evidence at applicable tier | effect-bearing activation and slice acceptance |
| TESTS_VERIFIED | test runner + reviewing owner | observed required tests pass, no skipped mandatory test | gate PASS |
| EVIDENCE_VERIFIED | evidence auditor | hashes, provenance, redaction, source/config match and honest tier | any achievement or completion claim |
| INDEPENDENT_AUDIT_PASSED | reviewer who did not author the reviewed changes | scope audit and independent negatives resolved; no relevant P0/P1 | slice acceptance |
| SLICE_ACCEPTED | authorized orchestrator | all slice gates plus applicable seals valid on same snapshot | downstream slice |
| RELEASE_READY | authorized release owner | all applicable product invariants, live integrations and OS/security/operational gates | release/deployment, which still requires explicit authorization |

SPEC_READY/CONTRACT_READY/TEST_PLAN_READY are planning seals only. They never imply that source exists or that an LLM works. Automated validators can issue STRUCTURAL_CHECK_PASSED evidence, not independent human/business approval. Security and operational obligations cannot be waived by a planning seal.

## Seal content and invalidation

Each seal records seal_id, kind, scope IDs, verdict PASS/FAIL/BLOCKED, UTC time, issuer identity and role, reviewed artifact SHA-256 map, source commit or snapshot digest, requirement/test IDs, evidence refs+digests, proof tier, rationale, unresolved findings and supersedes. Reviewer independence is checked against authors of changed files. Signature fields are optional until a real signing infrastructure exists; never call an unsigned JSON record tamper-proof.

Any change to an included artifact, transitive dependency contract, test oracle, fixture, model/provider configuration, behavior profile or protected policy invalidates the affected seal. Do not mutate the old record: add a new record referring to it. Source-sensitive seals do not expire solely by wall-clock time unless the environment policy requires it; credentials, revocation and provider behavior can invalidate them earlier. Missing evidence, digest mismatch, self-review or unknown issuer means INVALID. An invalid seal cannot be inherited by a later phase.

## Explicit release blockers

Known unauthorized effects, tenant leaks, false completion, lost accepted obligations, blind retries of uncertain effects, mutable/fabricated evidence, missing mandatory actual-model/durability tests, and independent P0/P1 findings block acceptance. Remaining design ambiguity is a specification defect, not an invitation for a smaller model to choose silently. Environment prerequisites are explicit BLOCKED dependencies with an owner/next action; they are not unresolved architecture decisions.

## Cost discipline

Use economical agents for bounded fixture authoring, mechanical checks and documentation. Use stronger reasoning only for unresolved architecture, security or difficult audit findings. Do not rerun successful unaffected suites or paid evaluations without changed inputs or new evidence. Parallelize disjoint fixtures/docs/adapters only after contracts are sealed; never parallelize writes to canonical state, shared policy or ledger/outbox. Record model/provider and cost if measured; unknown cost is null.

## Canonical seal lookup and gate reconciliation

`governance/seals/index.json` is the registry of immutable seal record IDs, paths,
record SHA-256 values, kinds, scopes and supersedes links. Each canonical slice
stores `gate_seal_refs[gate_id]` as explicit references to the exact records used
for that gate. Empty lists are correct for unexecuted gates and cannot support PASS.

On resume: resolve the exact state reference through the index; verify record hash,
scope/kind, issuer independence, evidence availability, every reviewed artifact
hash and supersession. Do not select the newest timestamp blindly. If two records
claim the same current scope/snapshot without an explicit supersession relation,
return BLOCKED for ambiguity. An index entry is a locator, not proof; the immutable
record and its evidence are authoritative. A PASS gate with missing/invalid seals
must be downgraded to BLOCKED by a revisioned reconciliation update, preserving
its previous status and invalidation reason in the audit event. Never rewrite the
old seal or silently retain PASS.

At task completion, every local_assertion requires current passing evidence. Cases
marked CONTRIBUTION_ONLY prove only that task's local assertion; their full proof
belongs to `full_proof_owner_task`. FULL_REQUIRED cases must meet the declared
tier. Every `owned_requirement_plan_id` requires a coverage claim identifying the
actual test assertion, exact evidence and fulfilled requirement portion. The final
gate accepts only FULL coverage for every `final_acceptance_plan_id`; reusable
sealed evidence is consumed without rerun when all relevant inputs still match.
Missing, partial, stale or wrong-tier evidence blocks the gate. A shared scenario
association alone never closes a requirement plan.


### Mandatory evidence and source binding

Every seal requires `evidence_sha256`, whose keys exactly equal `evidence_refs`, and
`source_snapshot` with `manifest_path` and `manifest_sha256`. The manifest is a JSON
object with `schema_version: secma-source-snapshot/1` and `files`, a nonempty map
of package-relative paths to SHA-256 digests. Include every sealed artifact and all
source, contracts, prompts, fixtures, configuration (redacted), and test inputs used
for the claim. The reviewer checks completeness against the command/input record;
a digest alone cannot prove completeness. Exclude the seal itself and the manifest
itself to avoid circular hashing. Resolve all paths inside the package; reject traversal,
missing files, changed bytes, or missing digest entries. Hash raw file bytes. Verify
manifest bytes first, then every member. A Git commit may be supplementary provenance;
it never replaces the manifest for a dirty or exported tree. `validate_seal_provenance`
checks these bindings. Mutation tests cover changed evidence/source, unbound evidence,
and path escape. Examples are constructed in `tests/test_spec_readiness.py`; these
synthetic examples are not issued seals or runtime evidence.

---

## 0.4 Persistent State and Memory

Source: `docs/governance/PERSISTENT_STATE_AND_MEMORY.md`

# Persistent execution state and engineering memory

## Authority and durability

`docs/implementation/implementation_state.json` is the only authoritative execution progress record. CHECKPOINT.md, reports and chat are pointers, not alternate truth. State is checked into the project and included in every durable checkpoint archive. A local working directory or an agent's conversation memory is not a durable backup. Before stopping, save the validated checkpoint to the authorized persistent destination and record its returned identity/version in the handoff. Never claim that a local write alone guarantees cross-session persistence.

The engineering state is distinct from SECMA's future product commitment ledger. Passing engineering resume tests proves nothing about DBOS recovery. Secret references may be recorded; secret values must never be saved.

## Canonical state fields

Keep schema_version, monotonically increasing revision, project/spec revision, work_mode, current_slice, per-slice status/gates/evidence/commit/blockers, active_work, known_unverified, last_updated_at. `active_work` has work_package_id, phase (DISCOVER/SDD/TDD_RED/IMPLEMENT/EDD/AUDIT/CHECKPOINT), owner, lease token/expiry, input snapshot digest, completed steps, next command/action, owned files, pending findings and evidence refs. No ACTIVE task may be inferred from chat if state disagrees.

Statuses: NOT_STARTED, IN_PROGRESS, PASS, FAIL, BLOCKED. NOT_RUN is allowed for unexecuted tests/gates only. A slice can be PASS only if all mandatory gates are PASS and seals are current. NOT_VERIFIED_EXTERNAL describes integration evidence, not a successful gate. Record prototype completion separately from full module completion. A passed S00 never marks all of M01/M02/M17/M30 complete.

## Atomic update protocol

1. Read revision R and required source digest. Acquire an exclusive task/state lock with owner/token; refuse another live owner.
2. Re-read R under lock. If it changed, abort and rebase; never merge JSON by last-writer-wins.
3. Validate IDs, dependencies, gate/seal evidence and legal status transitions. Reject editing downstream work as active while an earlier mandatory gate is incomplete.
4. Write the complete next document to a same-filesystem temporary file, flush and fsync, atomically replace, then fsync the directory where supported. Increment revision exactly once.
5. Release only the acquired lock. Persist the checkpoint after successful local validation. An abandoned lock requires inspecting owner/process/lease and recording recovery; never delete a lock simply to make a command pass.

A crash before rename leaves the previous revision authoritative. A crash after rename requires reading the new revision, not retrying the update blindly. If directory fsync is unsupported, record the platform limitation; native crash durability remains S07 qualification. A failed save leaves CHECKPOINT_PENDING and the exact next action; it does not mark a slice PASS.

## Resume procedure for any model

1. Read AGENTS, README, canonical state and latest checkpoint manifest; verify source/evidence hashes.
2. If work_mode is SPECIFICATION_ONLY, perform only the requested audit/specification work. Do not execute implementation tasks.
3. Identify the earliest incomplete gate and exact active work package. Read its contract versions and case IDs, open bugs, decisions and current seals.
4. Verify previous tests were executed against the same source/config/fixture snapshot. Reuse valid evidence; rerun only invalidated or interrupted checks.
5. Recover locks safely; obtain task ownership through CAS. State what was already completed and the next bounded action.
6. Continue from that action. Do not regenerate the whole project, overwrite prior evidence, skip failed tests, restart the roadmap or assume a model/provider is configured.

## Engineering memory schemas and file ownership

All records use the schema in `state/schemas/engineering-record.schema.json`, with type-specific required fields below. Index files contain IDs and paths only; individual immutable versions carry facts. Append a new version to change a record, retaining supersedes/source evidence. Never place client-private material in fixtures or memory.

| Registry | Required content | Completion condition |
|---|---|---|
| fixtures | fixture_id, version, source classification/license, purpose, construction recipe, seed, SHA-256, allowed use, privacy class, oracle location, covered case IDs | validated bytes match checksum; gold labels inaccessible to tested model |
| bugs | bug_id, severity, trigger, expected/observed, affected requirement IDs, public reproduction, first failing evidence, root cause, owner, regression case, resolution | regression passes and independent relevant reviewer verifies; otherwise OPEN/BLOCKED |
| debt | debt_id, shortcut, reason, risk, owner, expiry/trigger, bounded repair plan, tests proving limitation | repaired with evidence or explicitly renewed by authorized owner; cannot waive kernel invariants |
| achievements | achievement_id, precise user outcome, scope, proof tier, source/config/fixture digest, evidence, reviewer, limitations | evidence-backed verified outcome only; document count and mock success are not live achievements |
| decisions | decision_id, ADR/RFC ref, question, alternatives, choice, rationale, consequences, migration/supersession | decision accepted for identified scope; external availability remains separately measured |
| lessons | lesson_id, incident/bug/evidence refs, root lesson, applicable boundary, preventive change, regression link | supported observation; no speculative anecdote promoted to policy |

A fixture oracle is not model-visible source. Seed data may be public; sealed holdout labels remain in a separate restricted evaluator location with a checksum and access log. Never write chain-of-thought. Sanitized evidence must preserve the information needed to reproduce the decision without credentials or restricted content.

## Checkpoint contents

Include canonical specifications, schema/examples, traceability, test plans, work packages, governance/memory records, current state, source candidate if retained, red/green results, known failures and exact reproduction commands. Include source hashes and version/commit history or a git bundle when no remote repository is synced. Exclude credentials, caches, installed dependencies and unrelated local files. A final archive checksum cannot be embedded inside itself; record it in the delivery/save receipt or a sibling manifest.

## Deterministic memory lookup on resume

`memory/index.json` maps stable record IDs and versions to paths, types, status,
requirement IDs and scope. It is rebuildable from immutable records. Each work
package includes `memory_lookup`: match its related requirement IDs, include
DEC-001 and LESSON-001 globally, and inspect OPEN/IN_PROGRESS/BLOCKED bugs, debt,
decisions and fixture records. Canonical `active_work.memory_refs` identifies the
records relevant to the current checkpoint. Runtime-candidate defects remain
OPEN until a future implementation proves their resolution; a planning audit
does not close them.

At a task checkpoint, append new versions of changed bug/debt/decision/fixture
records and refresh the index atomically with the checkpoint intent. Record a new
achievement only after its evidence is verified. If state and index disagree,
rebuild the index from record versions, record the recovery and re-run lookup;
never drop an OPEN record to make a gate pass. CHECKPOINT.md links canonical state
and both indexes. Seal lookup uses `seal_registry_ref` and per-gate references,
not a search for a filename containing PASS.

---

## 0.5 Test Execution Protocol

Source: `docs/testing/TEST_EXECUTION_PROTOCOL.md`

# Test execution, fixtures, oracles and gate decisions

## Planning coverage versus implementation evidence

`ACCEPTANCE_CASES.json` describes shared cross-module scenarios. `REQUIREMENT_TEST_PLANS.json` describes each exact obligation, including portions not fully asserted by a shared scenario. A related module/case is not proof of coverage. The validator checks IDs, references, fields and declared mappings; semantic audit checks that assertions actually test the requirement. Every planned case starts NOT_RUN. Existing candidate tests are historical partial evidence, not automatic approval of this revised specification.

Public entry paths mean CLI/application/provider port with production enforcement, not calling an internal mock's answer. Lower-tier assertions remain useful but cannot replace the mandatory higher tier. No test must use production accounts or production data. Missing approved resources yields BLOCKED for required L3/L2, and NOT_VERIFIED_EXTERNAL for unconfigured optional external integrations.

## Required lanes and exit rules

| Lane | Input | Required observation | Exit condition |
|---|---|---|---|
| Specification L0 | schemas/examples/docs/traceability/tasks | no missing ID, contradictory phase, invalid example, orphan requirement/case or stale generated artifact | all structural tests pass and semantic auditor dispositions complete |
| Deterministic L1 | real policy/reducer/compiler code, synthetic ports | public-path positive + adversarial rejection + exact state/call-count assertions | zero safety bypasses, all declared assertions pass |
| Durable L2 | actual DBOS and PostgreSQL, controllable synthetic endpoints | kill/restart and concurrent transaction evidence | no lost accepted root, no duplicate confirmed effect, explicit uncertainty when unknown |
| Behavioral L3 | approved actual tool-capable model, blinded synthetic utterances | actual requests/tool calls/arguments/outcomes and configuration identity | predeclared oracle and threshold pass; mocks never counted |
| External L4 | explicitly authorized isolated provider account/workspace | authentic provider receipts and feature-specific failure behavior | only exercised features qualified; unavailable others remain unverified |
| Operational L5 | actual target OS/corporate profile | install/reboot/resource/backup/egress checks | per-platform declared gates pass; Linux result not copied to other OS |

A test run that is skipped, expected-failed, inconclusive or lower-tier is not PASS for a mandatory gate. Report all counts separately. Flaky tests keep their first failure; rerun does not erase it. Repeat only to diagnose variance with fixed seeds/configs or after a correction. Two failed repair attempts without new evidence require a bounded blocker/diagnosis, not an infinite loop.

## Fixture construction and oracle ownership

Every fixture has a versioned registry entry, source classification/license, deterministic construction recipe, seed where used, input hashes, privacy scope, allowed uses and oracle location. Refer to the scenario-specific values in ACCEPTANCE_CASES and module recipes in REQUIREMENT_TEST_PLANS. Store data separately from expected results. Never feed the expected capability ID, expected conclusion or evaluator score to the tested model.

Development seed cases are public and reusable. A separate evaluator produces at least 30 sealed low-risk routing cases after candidate stabilization, with balanced distractors/abstention and no duplicates/paraphrases copied from training examples. The model receives natural language and ordinary catalog summaries only. Evaluator records dataset hash before the run; changing cases or scoring after seeing results invalidates the comparison. Malicious strings are synthetic and explicitly low-trust inputs.

## S00 realness and calibration

CAP-01 and CAP-02 must show a real model selecting through search → describe → invoke for a newly installed unknown capability and a confusable alternative. Validate actual arguments/output/evidence. A direct programmatic invocation is only L1. SOC-01 records deterministic greeting behavior as L1 separately from an explicit real-model greeting evaluation; do not label the no-model fast path L3. All write attempts are rejected by trusted code regardless of model text.

MOD-01 autonomous low-risk role qualification: at least 30 sealed cases under one exact provider/model/prompt/config/catalog snapshot; at least 26 correct routing/abstention decisions out of 30 (or ≥85% rounded up for larger N); zero observed critical unauthorized-effect, tenant-leak or false-completion failures. Report the Wilson 95% interval with numerator/denominator, cost and latency. The observed score is not a universal guarantee. Failure demotes/disables that role, never lowers the threshold after the run. Additional risky roles require their own calibrated scope and cases.

S00-GATE-02 is PASS only after CAP-01/02 and applicable MOD-01 low-risk role qualification. This does not require all later ERI/specialist competencies. Unknown prices remain null; exact usage and limits are recorded. No paid live tests are executed during this specification-only audit.

## ERI episode oracle

Use scripted concurrent events with a virtual clock for deadlines, and actual LLM turns for interpretation. Episodes include: greeting, simple question, PRD request with optional preference missing, critical missing authority, mid-flight correction, two similar prior references, job B finishes before A, provider outage, quiet hours, and unsupported outcome claim. Required assertions: same root/ephemeral ID where appropriate, no duplicate kickoff, updated scope revision, no fabricated receipt, optional question does not block safe read step, blocking question prevents unsafe dispatch, useful update by recorded due time, and no quiet-hours override except an explicitly configured critical escalation.

Communication rubric: 1 misleading/irrelevant; 2 accurate but missing essential next action; 3 accurate, concise and actionable; 4 additionally well-timed and context-aware; 5 achieves outcome with no avoidable follow-up. Two blinded reviewers score the same paired baseline/candidate episodes; disagreements >1 point require an adjudication note. Gate: no critical truth/safety failures, median score ≥3, and candidate no worse than direct-specialist baseline on outcome/required follow-ups. Timing measured against agreed checkpoints, never an invented ETA. Review quality is not established by a model grading itself alone.

## Fault matrix and exact recovery expectations

| Injection point | Persisted expected state | Required response/recovery |
|---|---|---|
| before acceptance transaction commit | no accepted root/outbox | no accepted receipt; retry may create one root |
| after commit, before worker dispatch | one accepted root + intent | restart dispatches same intent once logically |
| two workers same request key/digest | one root; unique scoped key | both receive same root or one conflict/retry; no duplicate root |
| same key, changed digest | original unchanged | IDEMPOTENCY_CONFLICT |
| after provider accepts, before ACK persisted | pending/unknown attempt | EFFECT_UNCERTAIN; reconcile; no blind retry |
| stale goal revision candidate result | current goal remains open | evidence rejected as stale; reassess only current revision |
| cancel before effect dispatch | cancellation requested then no-effect confirmation | CANCELLED, no send |
| cancel after confirmed effect | historical receipt remains | CANCELLED_WITH_EFFECTS, disclose effect |
| cancel with lost ACK | unknown effect retained | NEEDS_RECONCILIATION, never pretend reversal |
| expiry/revocation after planning before dispatch | no dispatch | DENIED, approval cannot be reused |
| crash during engineering state checkpoint | old or new whole revision | never truncated JSON; lease recovery recorded |
| evidence bytes modified | hash mismatch | affected evidence/seals invalid; no PASS inheritance |

Inject SIGKILL against a real subprocess, not an exception in a fake workflow. Record process IDs, DB transaction boundaries and recovery commands without credentials. Database/network faults must be deterministic and tenant-isolated.

## Scheduling and provider limits

Persist due times in UTC plus original IANA zone/local intent. DST nonexistent times require an explicit correction; ambiguous folds require the chosen offset/fold to be stored. Business-day schedules require a named holiday-calendar version; absent calendar returns BLOCKED rather than guessing. Quiet/vacation profiles suppress noncritical proactive messages and preserve pending next action; profile changes never grant privileges.

Bound concurrency, retries, tool count, tokens and elapsed time. Retry only known-safe operations or idempotent provider operations whose semantics were qualified. 429 obeys bounded Retry-After; 401/403 do not retry forever. Disable expired/unprobed configuration before invocation. Clock injection is a test adapter, never model-controlled wall time.

## Operational measurements and release profile

S07 records CPU/RAM/latency for 60 seconds idle and 100 pending due commitments, declared hardware/OS/dependency versions, worker concurrency and baseline. The default acceptance is no unbounded growth, no one-resident-sleeping-workflow-per-timer design, and no missed/duplicate commitments in this load. Numeric deployment resource ceilings must be provided by the selected deployment profile before its release gate; absent ceilings blocks that deployment profile, not specification completeness. Never invent a measured footprint.

For Linux x64, Windows x64 and macOS ARM64, run fresh native install, startup/shutdown, restart and backup/restore. Verify approved proxy/CA and egress at the transport boundary. Optional adapters cannot be described as supported without L4 evidence for the actually enabled features.

---

## 1. Product Definition

Source: `docs/vision/PRODUCT_PRD.md`

# PRD-000 — SECMA: Executive Cognitive Secretary

**Version:** 8.0 proposed. **Status:** design only. **Audience:** implementers, auditors and product stakeholders. **Delivery shape:** headless CLI + durable worker, local-first.

## Problem
Existing AI agents can research, code, use tools or perform workflows but often fail to manage the human relationship across long-running requests. Users must remember what they asked, re-explain context, chase progress, resolve partial results and judge whether work is sufficient. Building more specialist agents is not a substitute for taking responsibility for the user outcome.

## Success definition
SECMA behaves as a reliable professional secretary: it hears the actual request, discriminates greetings and questions from delegable work, clarifies selectively, starts reversible research without waiting unnecessarily, creates durable commitments, supervises multiple executors, updates the requester at useful moments, remembers prior work with evidence, audits results and delivers concise answers plus reproducible artifacts. It also serves machine requesters through typed contracts.

## User personas
- Individual professional: native CLI, own models and data, lightweight resource profile.
- Corporate employee: authorized calendar, email, Slack, internal MCPs, delegated identity and enterprise model gateway.
- Technical lead/engineer: coding agents, PRD/TRD/ADR discovery and software-project investigation.
- Analyst: data and causal investigations, reproducible hypotheses, evidence lineage and uncertainty.
- Agent or service: structured request, async callbacks, idempotent machine-readable delivery.
- Administrator: plugin catalogs, security boundaries, agent/harness profiles, budgets, diagnosis, audits and rollback.

## Primary product narratives
1. “Good morning.” → a normal concise greeting; **no job**, no executor, no fake proactive activity.
2. “What is a PRD?” → immediate informational response; optional authorized context search only if relevant.
3. “Draft a PRD for a causal measurement engine.” → concise acknowledgement; safe repository discovery starts; optional goal question does not block; a persistent commitment is created; follow-up constraints update it.
4. “Do that study from last week for Company X.” → resolve last week's method, artifact version and permission; ask one disambiguating question only if two plausible studies remain.
5. “Add a line to last week's chart.” → find editable artifact and source data, create a new version and explicitly disclose when source is unavailable.
6. “Why did Ads positions 4 and 5 fall while 1 and 3 did not?” → analytical capability, confounder-aware timeline, evidence, missing-source notices, uncertainty and selective SME escalation.
7. “The customer is missing from the dashboard.” → incident investigation across authorized docs/logs/datastores without production writes; return proof, alternative hypotheses and next steps.
8. “Contact the owner of the data source.” → explicit identity, scope and permission checks before outbound message, with receipt only after confirmed provider result.
9. “We just installed a new specialist harness for editing Excel charts.” → manifest/assurance/health/policy checks; automatic catalog discovery and provider-neutral invocation; failover or typed unavailable when removed.
10. “My company blocks public APIs and Docker.” → corporate profile uses approved model endpoint, native CLI and authorized remote state; no hidden third-party egress.

## Product invariants — release blockers
- K1: A clear work request is never silently dropped, conflated with a greeting, or falsely acknowledged as started.
- K2: Every accepted root commitment has a persistent owner, revisioned state and next responsible action until closure or explicitly blocked state.
- K3: An LLM proposes intent and action; trusted code enforces security, state transitions, deadlines and outbound effects.
- K4: No unauthorized external effects or cross-tenant data access regardless of prompt/skill/tool content.
- K5: “Delivered” requires a recorded provider/CLI delivery acknowledgement; unknown external effects are surfaced as uncertain, not retried blindly.
- K6: A specialized investigation cannot claim sufficiency merely because an executor returned text; independent evidence rules apply.
- K7: Capability definitions, runtime bindings and measured assurance are distinct. A manifest alone is not executable.
- K8: Model feature support and competence are measured per model/provider/configuration. Large context is not assumed to mean sound judgment.
- K9: User preferences influence presentation and noncritical initiative, not permissions or evidentiary standards.
- K10: User-facing responses use the user's language or explicit preference; internal prompts, contracts, logs and documentation are English.

## Scope of initial product (S00–S02)
**Included:** CLI, one actual model provider, social/simple/work classification, one real blind discovery of installable capability, safe work start, ERI relationship updates, durable ledger and DBOS worker, progress timing, outcome sufficiency and honest delivery; evidence collection, retry/rollback and basic auth/policy. **Excluded initially:** full enterprise SSO, dozens of harnesses, every brain, marketplace, production-scale HA, UI, autonomous prompt promotion, cross-tenant sharing, true external Slack/Google write integrations.

## Personalization contract
Operator profile, interaction profile, execution profile and requester preference are distinct and versioned. The system MAY learn stylistic preferences based on repeated user corrections, with confidence and scope; it MUST offer inspect/correct/delete and MUST NOT silently alter safety policy. Configuration changes are proposed, compiled, simulated, evaluated and then atomically activated with rollback.

## User expectations and attention
Users do not need heartbeat spam; they do need accurate receipts, relevant new findings, blocking questions and communicated delays before agreed contact milestones. The secretary can provide “I will update you after the next evidence checkpoint” when no supportable ETA exists. It may offer progressive depth and describe actual uncertainty, but must avoid hollow praise, speculation about timing and long unsolicited text.

## Availability and performance
Small-model operation is a **target to demonstrate**, not an assertion. Personal mode needs low idle CPU, bounded RAM, no mandatory Docker and usable offline read-only functions when external APIs are not available. Worker resumption depends on the worker actually running; sleeping laptops do not execute jobs without remote worker.

## Measurement (not vanity test counts)
- User outcome completion, correct classification and safe abstention, meaningful question ratio, notification usefulness, false-completion rate, retrieval precision, end-to-end latency, resource idle footprint, cost per completed commitment.
- Hard-blocking: known unauthorized effects, known tenant leaks, lost accepted commitments under designated fault suite, unreported uncertain send.
- Model-dependent: evaluate independent blind holdouts and record model performance before enabling autonomous operation for that profile. Do not set ungrounded universal accuracy guarantees.

## Non-goals
SECMA is not a humanoid simulation, universal AGI, alternate operating system, a new universal tool protocol, a mandatory container orchestrator, a secret-sharing superagent, a browser-first app or a replacement for the domain specialist engines it delegates to.

## Traceability
All detailed product requirements are in `docs/prds/M01.md`–`M31.md` with stable FR/AT/RT identifiers and coverage in `docs/traceability/REQUIREMENTS.csv`. The implementation roadmap is normative and limits expansion despite the complete long-term vision.

## Prototype boundary before S02

S00 and S01 are restricted development prototypes, not releases satisfying the durable-commitment success definition. Their transient request/work identifiers MUST NOT be represented as persistent commitments; responses explicitly disclose in-process lifetime whenever work spans turns. They cannot promise continuation after exit/restart or accept unattended durable obligations. K2 remains an unchanged release blocker and becomes executable at S02. S00 fixture capabilities demonstrate discovery, not professional investigation outcomes.

---

## 2. Technical Reference

Source: `docs/trd/TECHNICAL_REFERENCE.md`

# TRD-000 — Technical Reference Architecture (v8)

## 1. Architecture decisions and design constraints
**Start as a modular monolith** (`secma` CLI and `secma worker`) with protected pure domain logic, Pydantic AI for the model interaction loop, SCS outcome manifests, governed prompt/context and statechart compilation, DBOS durable workflows and independent PostgreSQL business ledger. Add optional interfaces/adapters only when a demonstrable use case requires them. No web UI, backend HTTP server or Docker requirement in MVP.

## 2. Layered architecture
`Inbound CLI/provider adapters → Request normalizer and identity → ERI policy+context → model decision → SCS discovery/resolver → capability-specific controller → harness/tool/brain adapters → evidence/outcome judge → durable commitment/outbox → audience delivery.` The local worker accepts events from durable inbox; no agent is allowed to rewrite the ledger directly.

### Domain purity
`domain/` defines `Request`, `ActorRef`, `Commitment`, `InteractionDecision`, `OutcomeContract`, `CapabilityDefinition`, `ProviderFeatures`, `ExecutionPlan`, `DeliveryIntent`, `EffectIntent`, `AuditEvent` and `BehaviorPackageRef`. Runtime adapters implement application ports. No Pydantic AI/DBOS/Codex/Anthropic/MCP types in these schemas.

### Behavioral boundaries
- **Conversation turn**: ephemeral interpretation of incoming speech/text or system event, always recorded if a work state changes.
- **Commitment**: persistent obligation to a requester, not tied to a particular model, channel or workflow.
- **Capability**: SCS contract for result; may have several implementations, each with health, cost, permissions and empirical assurance.
- **Interaction policy**: a versioned expression of allowed initiative, reply style, timing, escalation and communication budget.
- **Control statechart**: deterministic legal transitions; dynamic choice of action happens inside validated guard/action interfaces.
- **Execution graph**: optional specialist implementation; not all capabilities have a LangGraph graph.

## 3. Technology shortlist (choose one implementation per initial boundary)
| Boundary | MVP decision | Why | Deferred alternatives |
|---|---|---|---|
| Language | Python 3.12+ subject to pinned SDK compatibility | Pydantic, provider SDKs, tests | Rust/Go for profiled hot path |
| CLI | Typer; switch to argparse if packaging materially suffers | typed commands | Web/desktop |
| Agent loop | Pydantic AI + on-demand capabilities/tools | progressive disclosure and typed tool calls | OpenAI Agents SDK, LangGraph, custom engines |
| Data validation | Pydantic v2 + JSON Schema Draft 2020-12 | typed, language-agnostic contracts | handwritten shape validators |
| Durable execution | DBOS, one engine-specific adapter | no separate orchestrator server | Temporal adapter when demanded |
| Persistent business state | PostgreSQL | ledger, outbox, ACL, indexing, audit | remote managed PostgreSQL |
| Local dev quickstart | isolated Postgres or SQLite only in non-release prototype | DBOS docs permit SQLite default | mandatory Docker disallowed |
| Statechart implementation | plain validated transition table + pure reducer initially | small, auditable, fast | `transitions` library if nested graphs needed; LangGraph for specialist graph |
| Prompt compilation | Jinja2 only for fixed trusted templates, or pure Python string assembly | deterministic artifacts and hashes | DSPy candidate optimization after eval |
| Model providers | OpenRouter via OpenAI-compatible transport + feature probing | user-preferred tests | native OpenAI, Anthropic, Gemini, xAI, enterprise |
| Harness providers | interface with feature flags and one real adapter later | hot-swap/no vendor leak | Codex SDK, Claude Agent SDK, Hermes, Tamanduá, A2A |
| Knowledge | local Markdown/Git initially + BrainProvider port | easiest auditable proof | GBrain, LLM Wiki, Obsidian integration, remote |
| Testing | pytest, jsonschema, property/state tests, Pydantic Evals | proof by risk | Pact when third-party consumer-driven contracts warranted |
| Tracing | OpenTelemetry-compatible spans + sanitized local event log | local-first and vendor-neutral | hosted observability |

## 4. Portability and profiles
Use local, hybrid and corporate profiles. Installer probes OS/architecture, allowed network, corporate proxies/CA, available DB, provider tool support, signed executables and user permissions. DBOS is a Python dependency, not Docker. Default production-like persistence is PostgreSQL native/remote; don't assume a corporate laptop can run containers. Windows/macOS/Linux tests cover process supervision, install, filesystem encoding and exit behavior. If user machine sleeps, local worker pauses: persistent workflows are recoverable but not executing.

## 5. Critical DBOS qualification
DBOS documentation says SQLite is the default system database for development and PostgreSQL is recommended for production. Importantly, `suspend=True` for long waiting workflows is tied to DBOS Transact Enterprise; open-source workflows waiting in `DBOS.sleep`/`DBOS.recv` may occupy resident resources. SECMA SHOULD store reminder due times in its ledger, run a bounded sweeper/reconciliation worker and avoid creating an indefinitely sleeping DBOS workflow per commitment. Benchmark concurrent waits rather than assume zero RAM. DurableRunner port: `start`, `status`, `signal`, `cancel`, `schedule` (last operation may be implemented through ledger timers), plus typed capability discovery and errors. Engine internals remain adapter-specific; do not build a Temporal clone in Python.

## 6. Persistence and event schema
Tables (logical, exact DDL produced in S02): `principals`, `requests`, `conversation_turns`, `commitments`, `commitment_events`, `workflow_refs`, `outbox`, `outbox_attempts`, `effect_intents`, `artifact_refs`, `capability_definitions`, `capability_bindings`, `model_competence`, `profile_versions`, `policy_decisions`, `memory_refs`, `audit_events`, `evaluation_runs`. Version all mutated rows, unique idempotency keys scoped to principal/action and use append-only audit events. Align DBOS transaction boundaries with business outbox to prevent acknowledgement races.

## 7. Model selection and compatibility
A `ModelProvider` has transport, model ID, approved endpoint and region, credential reference, feature probe results (`tools`, `tool_choice`, `structured_output`, `parallel_calls`, `streaming`, `usage`), latency/cost budgets and model-specific measured skill. OpenRouter's OpenAI-compatible surface does not guarantee every model supports tools. A provider with no reliable tool-calling MUST not handle capability discovery autonomously; it may handle simple no-tool replies or be paired with an approved tool-capable router. Codex CLI/SDK and Claude Agent SDK are **harnesses**, not API keys; OpenAI Agents API (managed cloud execution) is a separate adapter and demands explicit feature/availability check.

## 8. Model runtime policy for weak/fast models
Preflight benign deterministic shortcuts (greeting/no-work only if confident), otherwise ask light model for a **typed intent decision**, not free-form chain-of-thought. Build small contextual envelopes: user goal, requester policy, commitment state, recent relevant turns, retrieved evidence refs, and up to K candidate tools. Load detailed skill/capability descriptions only when selected. Use untrusted-text delimiters, fixed priority rules and bounded repair retries; escalate uncertain high-risk/analytical tasks to stronger permitted model rather than promising universal competency. Never use prompt length as a quality proxy.

## 9. Prompt and statechart compilation
The `BehaviorPackageCompiler` is a deterministic trusted service/library that converts approved YAML profiles + locked kernel requirements + SCS capability descriptions into versioned prompt artifacts and declarative statechart tables. It must validate references, reachable states, allowed edges, finite loops/budgets, approved guard IDs and policy constraints. An LLM MAY propose a draft profile or prompt variant; proposal is untrusted and must pass the compiler, model eval and authorized promotion. Generated code execution from YAML is prohibited. Implementation may use `transitions` only if its value is demonstrated; avoid LangGraph solely to represent a five-state conversation lifecycle.

## 10. Capability and integration policies
SCS lifecycle = `DRAFT → VALIDATED → STAGED → ENABLED` with `DISABLED/DEPRECATED` states; disabling a binding must leave accepted commitments coherent. Runtime selection prefers assurance, permissions, compatibility, health and measured cost; agent self-claims and repository stars are not assurance. External adapter reads, writes, cancel/resume and streaming are **feature flags**, not assumed universal. Do not install untrusted code when scanning skill/agent manifests. Provider absence is typed and isolated.

## 11. Authorization and external effects
Trusted policy enforcement occurs before invocation and before each external effect; operational defaults are read-only. Principal/tenant scope is attached at every hop. Optional enterprise OPA/OpenFGA services are adapters for requirements that actually justify them; not MVP mandatory. Side-effect uncertainty after provider response loss remains `EFFECT_UNCERTAIN` until reconciled. No general exactly-once claim across Slack, email or other providers.

## 12. Failure, observability and recovery
Clock, entropy, file and network adapters support reproducible injected faults. Add trace spans for intake, classification, context selection, capability discovery, policy decision, execution, evidence review, outbox insertion and delivery. Stop after bounded retries, store dead-letter reason and next action, and keep user informed. Emit model output hashes/IDs without logging secrets or sensitive raw payloads by default.

## 13. Public CLI (proposed, unimplemented)
```
secma init --profile local
secma doctor --json
secma config validate|diff|simulate|propose|apply|rollback
secma profiles list|describe|test
secma behavior compile|render|validate|eval
secma models add|probe|bench
secma capabilities list|search|describe|install|validate|enable|disable|eval
secma agents add|probe|list|remove
secma brains add|probe|list|sync
secma ask "Please draft a PRD about feature X" --json
secma tell <commitment-id> "Also check our incident RFCs"
secma status <commitment-id> --json
secma messages --unread
secma audit show <commitment-id> --json
secma worker start
secma eval run --suite <suite> --provider <profile>
```
Every command exposes safe errors and structured JSON with stable exit codes. Work can start while CLI is closed only if a worker remains running.

## 14. Integration into code factory
The spec agent owns FR→contract→test generation; the implementation agent owns working code; an independent reviewer owns adversarial test selection and evidence audit. A successful compile of config is NOT a successful LLM eval; successful simulated provider test is NOT external certification. See `docs/governance/FACTORY_OPERATING_RULES.md`.

## 15. Deferred architecture questions
- Enterprise HA requirements and DBOS licensing, including optional Conductor/suspension features, require procurement/licensing review.
- Per-model competence thresholds and resource budgets require real benchmarking.
- Corporate model gateways have no assumed compatibility; probe each capability.
- Cross-engine workflow migration requires drain/checkpoint strategy and is not simple history import.
- External connectors require owner authorization before full live smoke.

---

## 3. Module Inventory

Source: `docs/vision/MODULE_MAP.md`

# SECMA v8 — Module Inventory

The architecture contains **31 responsibility modules** but deliberately starts as a modular Python monolith, not 31 services or LLM agents. Each module has a detailed normative PRD and an independent red-team sheet.

| ID | Module | Earliest slice | Related modules |
|---|---|---|---|
| M01 | [CLI, packaging and local lifecycle](docs/prds/M01.md) | S00 | M02 M17 M26 |
| M02 | [Identity, requester and authorization context](docs/prds/M02.md) | S00 | M25 |
| M03 | [Executive Relationship Intelligence (ERI)](docs/prds/M03.md) | S01 | M04 M05 M06 M07 M09 M10 M30 M31 |
| M04 | [Intent, reference and ambiguity resolution](docs/prds/M04.md) | S01 | M11 M31 |
| M05 | [Initiative and clarification economy](docs/prds/M05.md) | S01 | M04 M25 M30 |
| M06 | [Expectation and communication management](docs/prds/M06.md) | S02 | M07 M10 M13 M30 |
| M07 | [Commitment ledger and durable execution](docs/prds/M07.md) | S02 | M02 M25 M26 |
| M08 | [Triage, prioritization and task planning](docs/prds/M08.md) | S01 (foundation), S03 (completion) | M04 M05 M14 M15 M30 M31 |
| M09 | [Sufficiency, evidence and stopping judgment](docs/prds/M09.md) | S02 | M07 M10 M26 |
| M10 | [Audience-aware delivery and artifact packaging](docs/prds/M10.md) | S02 | M06 M07 M12 |
| M11 | [Episodic and semantic memory](docs/prds/M11.md) | S03 | M02 M07 M25 M26 |
| M12 | [Versioned artifacts and reproducible edits](docs/prds/M12.md) | S03 | M11 M26 |
| M13 | [Personalization and relationship preferences](docs/prds/M13.md) | S03 | M02 M03 M11 |
| M14 | [SCS capability manifest and registry](docs/prds/M14.md) | S00 | M02 M25 M26 |
| M15 | [Capability discovery, resolver and execution controller](docs/prds/M15.md) | S00 | M14 M17 M25 M31 |
| M16 | [Agent Skills discovery and packaging](docs/prds/M16.md) | S03 | M14 M19 M25 |
| M17 | [LLM providers, routing and competence profiles](docs/prds/M17.md) | S00 | M25 M26 M31 |
| M18 | [Agent and harness adapters](docs/prds/M18.md) | S04 | M14 M15 M25 M26 |
| M19 | [MCP and action gateway](docs/prds/M19.md) | S04 | M02 M25 M26 |
| M20 | [Second-brain provider adapters](docs/prds/M20.md) | S04 | M02 M11 M25 |
| M21 | [Knowledge, ecosystem and repository discovery](docs/prds/M21.md) | S05 | M19 M20 M25 |
| M22 | [Software engineering discovery and specifications](docs/prds/M22.md) | S05 | M21 M12 M09 |
| M23 | [Incident investigation and root-cause analysis](docs/prds/M23.md) | S05 | M21 M19 M09 |
| M24 | [Data analysis and causal inquiry](docs/prds/M24.md) | S05 | M19 M20 M09 |
| M25 | [Preventive policy and approvals](docs/prds/M25.md) | S00 | M02 |
| M26 | [Audit, observability and evidence](docs/prds/M26.md) | S00 | M02 |
| M27 | [Evaluation-driven improvement and self-evolution](docs/prds/M27.md) | S06 | M09 M13 M14 M25 M26 M30 |
| M28 | [Portability, operations and enterprise deployment](docs/prds/M28.md) | S07 | M01 M07 M17 M18 M25 |
| M29 | [Channel and inbound/outbound messaging](docs/prds/M29.md) | S04 | M02 M06 M07 M10 M25 |
| M30 | [Behavior package, prompt and statechart compiler](docs/prds/M30.md) | S00 | M14 M25 M26 |
| M31 | [Context engineering and model competence calibration](docs/prds/M31.md) | S00 | M17 M30 M15 |

Modules M30 and M31 are **new canonical additions**: configuration-to-behavior compilation and competence-aware context engineering. The previous 29-module inventory is retained as M01–M29, with each PRD rewritten in English and updated to fit the new controller design.

---

## 4. Implementation Roadmap

Source: `docs/implementation/ROADMAP.md`

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

## Detailed execution and governance authority

`WORK_PACKAGES.json` contains 35 bounded tasks; `work_packages/S00.md`–`S07.md`
provide ordered handoffs. They refine this roadmap without permitting skipped
slice gates. Read PROJECT_STRUCTURE, BOUNDARY_CONTRACTS, DELIVERY_GOVERNANCE and
PERSISTENT_STATE_AND_MEMORY before implementing. SPECIFICATION_ONLY mode prohibits
new runtime implementation until explicitly authorized.

Phase corrections: informational-answer SOC-02/CAP-04 are S01; runtime profile
rollback CMP-04 is S03; full trace ACL/retention EVD-01 is S07, with local private
receipt checks starting in S00. S00-GATE-02 includes blind discovery plus MOD-01
low-risk role calibration. No full-module completion is inferred from a first slice.

---

## 5. Test Coverage Rationale

Source: `docs/testing/RISK_COVERAGE_REPORT.md`

# Test Coverage Justification and Gap Report (Design v8)

**Truth statement:** This package specifies tests; the only executed checks included in it are L0 documentation/schema/reference-compiler tests. No claims of tested live LLM, DBOS recovery, native OS portability or external Slack/Gmail/model enterprise APIs are made.

## Why we do not create thousands of tests
Requirement count is not risk count. Multiple PRDs share a single authorization gate, a single ledger integrity rule and one model discovery mechanism. Duplicate tests that only assert identical mocks increase CI cost without reducing risk. Instead, choose tests at each unique failure boundary, prefer property/state tests over enumerated messages, and test integrations through their public entry paths. Add new cases when a production incident, architectural change or unique negative scenario reveals an uncovered boundary.

## Risk-weighted coverage by layer
| Risk area | Impact | First mandatory proof | Justification for tests | Current proof |
|---|---|---|---|---|
| Unauthorized external effects | Critical | L1 policy + L2 gateway negative | Consequence irreversible; cannot rely on LLM refusal | NOT_RUN |
| Wrong tenant/identity | Critical | L1/L2 identity + retrieval ACL | Avoid privacy breaches and forged commands | NOT_RUN |
| Lost/duplicated commitment | Critical | L2 DBOS/PG fault suite | Core product promise; worker restart/two workers | NOT_RUN |
| Wrong capability selection | High | L3 blind real-model holdout | SCS's central hypothesis is empirical | NOT_RUN |
| False completed investigation | High | L2 evidence gate + L3 multi-turn | Prevent misleading confident findings | NOT_RUN |
| Bad update timing/spam | Medium–high | virtual clock + L3 ERI eval | Core differentiation over plain specialist CLI | NOT_RUN |
| Forgotten previous artifact | High | provenance fixture + L3 dialogue | Must identify correct work, not hallucinate | NOT_RUN |
| Compiler allows unsafe state/prompt | Critical | L0 compiler negative + L1 activation gate | Configuration is externally adjustable and agent-proposable | L0 ONLY |
| Weak model/tool incompatibility | High | model probe + L3 targeted eval | Tool support differs across models even within same gateway | NOT_RUN |
| DBOS long wait RAM/resource | Medium–high | L2 load test with due-time policy | Open-source suspension may not be available | NOT_RUN |
| Adapter provider removed mid-job | Medium–high | L2 fake executor kill | Server must remain responsive and obligations persist | NOT_RUN |
| Prompt injection from repo/skill | Critical | L1 tool gate + L2 injected source | Untrusted text must not become authority | NOT_RUN |
| External provider quirks | Medium–high | local HTTP fake + L4 authorized smoke | Local compatibility is not live integration guarantee | NOT_VERIFIED_EXTERNAL |
| Windows/macOS/Linux install | Medium–high | L5 native OS smoke | Pure Python is insufficient evidence for SDK/executable support | NOT_RUN |
| Self-improvement regression | High | evaluator gate + sealed holdout | Avoid automatic weakening or overfitting | NOT_RUN |

## Coverage measures
1. **Requirements coverage** = FR IDs with a linked observable acceptance case / total FR IDs. This is traceability, not test pass.
2. **Risk coverage** = unique P0/P1 failure boundaries with executing negative/fault proofs / required boundaries.
3. **Transition coverage** = (valid edges exercised and invalid edges rejected) / declared statechart edges + forbidden candidate transitions. Pure reducer/property tests are suitable.
4. **Behavior coverage** = held-out multi-turn episodes across intent, context, action, pause, user follow-up, executor callback, update and final delivery.
5. **External evidence coverage** = provider features with authorized live smoke / features claimed validated; unsupported/unavailable remain explicit.
6. **Code coverage** is a supporting signal, not a gate by itself; aim 90% deterministic policy/reducer branch coverage and ~80% other core domain where useful, but approve on risk scenarios, not an arbitrary global number.

## Phase exit hierarchy
S00: actual supported-model tool choice and safe abstention; S01: human dialogue/optional clarification while safe research progresses; S02: DBOS recovered commitment + honest delivery; S03: old-work reference/prefs; S04: new harness or brain removed without global outage; S05: evidence-based deep investigation; S06: prompt improvement cannot self-approve; S07: native/enterprise deployment security and resources measured.

## Coverage audit procedure
Auditor reads each module's PRD AT/RT without looking at its implementation, checks one public-entry proof and one nonredundant negative, then identifies missing safety branches. Audit status is `NO-GO` if a required L2/L3/L4 proof was substituted by L0/L1 or if a P0 invariant is knowingly violated. Record gaps in `OPEN_RISKS.md`, not a fabricated “pass rate.”

---

## 6. Prompt and Statechart Compiler

Source: `docs/rfcs/RFC-010_BEHAVIOR_COMPILER.md`

# RFC-010 — Behavior Package Compiler: Who Generates Prompts and Behavioral Programs?

**Decision:** The trusted SECMA runtime owns prompt compilation and behavior activation; installation operators author policy; autonomous agents may generate **proposals** only. Model-specific runtime prompt instructions are never the authoritative security policy.

## Input sources and precedence
1. Read-only kernel invariants: authorization, commitment integrity, delivery truthfulness, evidence and audit.
2. Validated installation/corporate policy, security allowlists and data residency.
3. Versioned role/interaction/execution profile (e.g., executive secretary, researcher, concise analyst).
4. Enabled SCS contract summaries, outcome criteria, on-demand skill/tool summaries.
5. Task-specific context envelope with current user request, previous turns, progress, preferences and evidence refs.
6. Low-trust external documents/tools, explicitly marked as quoted data rather than instructions.

The compiler loads only needed parts and returns `PromptBuildReceipt{behavior_version, statechart_hash, prompt_hash, sections, token_budget, required_facts, model_profile_ref, source_versions}`. Cached stable prefix is separated from volatile task context; if token pressure occurs, untrusted retrieved context is trimmed first, not security/ownership facts. Rendering MAY use Jinja2 for immutable templates but arbitrary `eval`/Python execution in YAML is forbidden.

## Configuration lifecycle
`secma behavior propose` can accept a human-authored YAML patch or an agent-generated draft; `validate` checks schema/references/policies; `render` generates English prompt preview and statechart; `simulate` tests representative conversation/event traces; `eval` uses actual LLM holdouts if model behavior changes; `promote` requires approved policy; `rollback` restores previous content-addressed version. Deterministic compilation is idempotent for identical inputs. System owner may configure style and workflow selection but cannot disable the trusted authorization ledger.

## For weaker models
Produce explicit responsibilities, decision enum, examples including when **not** to call tools, single typed output target and a maximum of 2–5 candidate capabilities, retrieving more only if needed. Avoid a monolithic list of 79 capabilities, hidden unstated knowledge, contradictory instructions and prompt-only state transition checks. When tool calling is unreliable, choose a calibrated supported provider or ask a limited clarifying question instead of autonomous risk-taking.

## Rejection rules
A prompt builder MUST reject a profile that requests nonexistent capabilities, unknown guard names, privilege elevation, conflicting output-language priorities, invalid state references, absence of audit, unbounded retries or secret interpolation. User-facing responses may be localized after the English internal decision; documentation/internal manifests remain English.

---

## 7. Statechart Invariants

Source: `docs/rfcs/RFC-011_STATECHART_MODEL.md`

# RFC-011 — Statechart Contract Compiler and Controlled Agency

Every nontrivial SCS capability MUST have a **control policy** with allowed lifecycle states, obligations, legal transitions, guards, deadlines and failure handling. This does **not** mean every capability requires LangGraph or a static graph of reasoning. Simple capabilities may have a single terminal result; long-running investigations can have complex internal workflows owned by their executor.

## Proposed mechanism
Represent control states and transitions in declarative YAML conforming to a JSON Schema. A pure-Python compiler validates all states exist, initial/terminal reachability, forbidden back-edges, known guard/action registry, transition uniqueness and bounded revisit counts. It emits a deterministic transition table, Mermaid diagram and semantic digest. In MVP use a simple trusted `next_state(current, event, policy_context)` reducer persisted to the commitment ledger. `transitions` (MIT) is optional if future hierarchical/parallel complexity justifies it; LangGraph is optional inside specialist harnesses rather than part of the SECMA protected kernel.

## Hard state constraints
- State changes are transactional and compare expected revision.
- External side effects occur only after authorization; guards must be pure and deterministic.
- `DELIVERED` requires outcome evidence and delivery acknowledgement, not only model text.
- `CANCEL_REQUESTED` can transition to cancelled, complete-with-effects, or needs-reconciliation, not pretend past effects reversed.
- Waiting for optional user input must not block safe parallel read-only steps.
- Every nonterminal state must have a recovery/timeout/escalation path; all cycles need explicit attempt/cost/time budgets.

## Complexity thresholds
Use an enum/reducer for five to ten predictable states; add declarative `transitions` only when more than one stateful workflow actually benefits. Do not generate arbitrary Python workflow code from a natural-language prompt and trust it. Agent-produced machine drafts must be reviewed for changed authority and tested before promotion.

---

## 8. Small Model Context Engineering

Source: `docs/rfcs/RFC-012_SMALL_MODEL_CONTEXT.md`

# RFC-012 — Context Engineering, Weak-Model Routing and Decision Quality

**Problem:** A large context window does not imply deep reasoning, reliable tool choice or sustained goal tracking. SECMA must remain helpful on inexpensive models without pretending they match high-capability models on scientific investigations.

## Two-stage classification
Trusted fast preflight handles explicit greeting and local command shortcuts only when high confidence and no hidden side-effect intent. Otherwise a small tool-capable model returns a typed `RequestClassification`: intention family, risk/effect, expected complexity, missing critical info, candidate domain, provisional depth, whether safe work can start, and confidence/abstain. Policy then decides allowed actions. `DEEP_ANALYSIS`, high uncertainty, sensitive work or repeated failures trigger a stronger approved model or a bounded clarification.

## Progressive context layers
A minimal envelope includes role constraints, active commitment summary, short recent interaction, target schema, available action enum and top ranked capability descriptions; source details/skills expand only after selection. Artifact and knowledge retrieval must attach provenance, ACL and freshness. User preferences affect phrasing, not security or result proof. Stable prompt prefix enables caching where supported; retrieval snippets go into explicitly lower-trust sections.

## Model competence profiles
A provider descriptor contains observed tool-calling reliability, JSON validity, intentional abstention, routing/top-k recall, tool-result continuation, evidence judgment and cost per task class, all with model version, provider, prompt digest and sample sizes. An unsupported feature is never inferred from “OpenAI-compatible”. A cheap model may handle greetings, status and low-risk routing even if not competent for independent causal inference. Escalation is a configured policy decision, not an agent’s claimed confidence alone.

## Evaluation
Blind holdouts include paraphrases, novel installed capabilities, near-match distractors, disabled providers, greetings, long-context interruption, contradictions and adversarial tool descriptions. Record actual tool calls and rejected attempts. No role is called “supported” until behavior has been measured under that exact provider configuration; test with multiple seeds/trials as variance requires, rather than arbitrary 100% model success claims.

---

## 9. Technology Evidence

Source: `docs/research/SOURCE_EVIDENCE.md`

# Source and Technology Evidence Register

Research checked for the SECMA v8 architecture; public product claims must be reverified against pinned versions when implementation begins.

1. **Pydantic AI capabilities / deferred loading**: reuses tools, instructions, hooks and model settings with on-demand exposure; SCS remains outcome contract. https://pydantic.dev/docs/ai/capabilities/overview/ ; https://pydantic.dev/docs/ai/capabilities/on-demand/
2. **DBOS Python durability**: workflows, steps, SQLite default and PostgreSQL production recommendation. https://docs.dbos.dev/python/programming-guide ; https://docs.dbos.dev/python/integrating-dbos
3. **DBOS queue/communication/long waits**: persisted messages, idempotency and enterprises-only suspension caveat. https://docs.dbos.dev/python/reference/queues ; https://docs.dbos.dev/python/tutorials/workflow-communication ; https://docs.dbos.dev/python/tutorials/workflow-tutorial
4. **Lightweight FSM**: `transitions`, MIT, guards, nested and graph options; optional only. https://github.com/pytransitions/transitions
5. **LangGraph**: interrupts/checkpoint and redo-of-node concerns; optional specialist runtime. https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/interrupts.mdx
6. **OpenRouter**: OpenAI-compatible tool loop but supported tools differ per model; verify tool-capable endpoints. https://openrouter.ai/blog/tutorials/tool-calling/
7. **Codex SDK / App Server / Agents API**: separate local SDK, event-rich app-server and managed cloud agent API. https://learn.chatgpt.com/docs/codex-sdk ; https://learn.chatgpt.com/docs/app-server ; https://developers.openai.com/api/docs/guides/agents-api/overview
8. **OpenAI Agents SDK**: agent loop, handoffs, guardrails and SDK tracing; optional alternate harness. https://developers.openai.com/api/docs/guides/agents/sdk
9. **Anthropic tool runner and Agent SDK**: separate managed tool runner and coding/agent SDK; permissions and identity must be checked per endpoint. https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner ; https://platform.claude.com/docs/en/agent-sdk/overview
10. **Prompt optimization**: DSPy MIPROv2 optimizes examples/instructions but needs independent evaluation, optional after S06. https://dspy.ai/current/api/optimizers/MIPROv2/
11. **MCP, A2A and Agent Skills**: open interoperability protocols for tools, agents and procedural packages; not a cross-vendor contract for outcome assurance. https://modelcontextprotocol.io/ ; https://a2a-protocol.org/ ; https://agentskills.io/
12. **OpenTelemetry/JSON Schema**: tracing vocabulary and portable validation semantics. https://opentelemetry.io/ ; https://json-schema.org/

## Assumptions deliberately NOT asserted
No empirical local RAM/CPU benchmark; no claim that a personal subscription provides an API key; no guaranteed model tool use from an OpenAI-compatible label; no claim that DBOS open-source suspends arbitrarily many parked jobs without resources; no guaranteed migration of DBOS workflow histories to Temporal; no live corporate model availability or Slack account; no implementation of the SECMA runtime from this documentation package.

---

## Module M01

Source: `docs/prds/M01.md`

# M01 — CLI, packaging and local lifecycle

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Provide a headless command interface whose user can submit, inspect, modify and audit work without a web service.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M17, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M01-FR-01 (MUST):** Provide ask/tell/status/messages/config/doctor with stable machine-readable JSON and English diagnostics.

- **M01-FR-02 (MUST):** Distinguish a received request from a launched workflow and an actually delivered result.

- **M01-FR-03 (MUST):** Run with a user-scoped native install; Docker remains optional and no web UI is started.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to CLI, packaging and local lifecycle.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M01-AT-01:** Fresh CLI install is usable on at least the reference OS and reports a provider-disabled configuration. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M01-AT-02:** A social greeting returns without generating a commitment; an asynchronous request prints a real commitment ID. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M01-RT-01:** Closing an interactive terminal is not a substitute for stopping a long-running worker. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M01-RT-02:** Incorrect shell quoting, filesystem paths or unsupported OS must not corrupt config. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M01-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M02

Source: `docs/prds/M02.md`

# M02 — Identity, requester and authorization context

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Identify who is asking, who owns each commitment, and which data/action scopes apply.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M25. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M02-FR-01 (MUST):** Authenticate request origin; do not accept self-asserted identity inside untrusted text.

- **M02-FR-02 (MUST):** Bind tenant, user, channel and delegated actor to each request, event, capability and artifact.

- **M02-FR-03 (MUST):** Implement deny-by-default on missing or expired authority and offer a clear reauthorization route.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Identity, requester and authorization context.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M02-AT-01:** Forged author in imported transcript cannot create an authorized action. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M02-AT-02:** Identical remembered phrases for two users never cross tenant or identity scope. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M02-RT-01:** A provider callback spoofing the requester must be rejected. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M02-RT-02:** Origin and delegated identity must survive task delegation and retries. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M02-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M03

Source: `docs/prds/M03.md`

# M03 — Executive Relationship Intelligence (ERI)

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S01. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Act as a professional executive secretary across turns, tasks, channels and time.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M04, M05, M06, M07, M09, M10, M30, M31. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M03-FR-01 (MUST):** Separate conversational politeness from work commitment and real progress.

- **M03-FR-02 (MUST):** Choose message, silence, question, start safe work or deliver based on context and relationship preference.

- **M03-FR-03 (MUST):** Bind follow-up instructions and async executor results to correct commitment without promising unseen actions.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Executive Relationship Intelligence (ERI).

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M03-AT-01:** A greeting stays conversational; a PRD request starts safe discovery; subsequent changes update the same work. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M03-AT-02:** An async result for commitment B never interrupts unrelated conversation A. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M03-RT-01:** Avoid false statements such as “I have already investigated” before observed work. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M03-RT-02:** Detect recursive clarification, excessive verbosity and unsolicited updates. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M03-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S01. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M04

Source: `docs/prds/M04.md`

# M04 — Intent, reference and ambiguity resolution

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S01. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Infer intent and resolve references to previous requests without guessing.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M11, M31. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M04-FR-01 (MUST):** Distinguish social, answer, context lookup, compound work, investigation and external action.

- **M04-FR-02 (MUST):** Represent multiple plausible references with confidence and evidence; ask one focused question if ambiguous.

- **M04-FR-03 (MUST):** Capture open assumptions, scope changes and explicit user corrections as events.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Intent, reference and ambiguity resolution.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M04-AT-01:** “Do the study again for company X” resolves its prior method and scope with permission checks. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M04-AT-02:** Two plausible “last week” artifacts trigger a brief disambiguation instead of an invented selection. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M04-RT-01:** Keyword-based false positives must not launch jobs. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M04-RT-02:** Reference resolution cannot leak another requester’s private artifacts. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M04-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S01. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M05

Source: `docs/prds/M05.md`

# M05 — Initiative and clarification economy

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S01. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Determine when to act safely versus request missing information.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M04, M25, M30. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M05-FR-01 (MUST):** Start authorized, reversible reading while optional details remain unresolved.

- **M05-FR-02 (MUST):** Ask only for decisions that materially affect scope, risk, cost or outcome; account for user interruption cost.

- **M05-FR-03 (MUST):** Support answer-in-parallel: revise work after the user supplies detail rather than creating a second job.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Initiative and clarification economy.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M05-AT-01:** Missing optional preference does not block research. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M05-AT-02:** Missing tenant or irreversible-write approval blocks action with a specific question. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M05-RT-01:** Do not execute harmful tools under the label of “proactive research”. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M05-RT-02:** Avoid serial questioning when parallel read-only discovery could resolve uncertainty. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M05-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S01. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M06

Source: `docs/prds/M06.md`

# M06 — Expectation and communication management

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S02. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Keep requesters appropriately informed without spam or silent abandonment.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M07, M10, M13, M30. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M06-FR-01 (MUST):** Store next-contact commitment and escalation trigger with a durable timestamp.

- **M06-FR-02 (MUST):** Distinguish receipt, meaningful progress, blocking question, delay notice, partial result and final delivery.

- **M06-FR-03 (MUST):** Respect recipient availability and notification preferences but allow justified urgent alerts.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Expectation and communication management.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M06-AT-01:** Simulated time advance triggers due update without requiring the LLM to be running. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M06-AT-02:** No repeated “still working” messages unless policy and actual context justify them. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M06-RT-01:** Network failure must not be reported as successful delivery. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M06-RT-02:** A fixed timeout must not be misrepresented as estimated completion. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M06-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S02. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M07

Source: `docs/prds/M07.md`

# M07 — Commitment ledger and durable execution

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S02. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Persist responsibility independently of the DBOS engine and recover after interruption.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M25, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M07-FR-01 (MUST):** Keep root commitment, immutable events, optimistic revision, outbox, effect-intent and execution mapping.

- **M07-FR-02 (MUST):** Run DBOS behind minimal DurableRunner application port; extend port only for actual use cases.

- **M07-FR-03 (MUST):** Reconcile unknown external effects, cancel best-effort and preserve workflow ownership on worker restart.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Commitment ledger and durable execution.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M07-AT-01:** SIGKILL worker between read and report; resume without duplicate commitment. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M07-AT-02:** Crash after simulated external send and before ACK yields uncertain effect, never false exactly-once. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M07-RT-01:** Do not infer enterprise HA from a single local worker. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M07-RT-02:** Large numbers of long-lived waiting workflows may consume RAM without enterprise suspension. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M07-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S02. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M08

Source: `docs/prds/M08.md`

# M08 — Triage, prioritization and task planning

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S01 foundations; S03 completion. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Select engagement mode, desired depth, risk handling and delegation plan via governed configuration.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M04, M05, M14, M15, M30, M31. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M08-FR-01 (MUST):** Classify social/quick/context/work/deep/action separately from difficulty, urgency and risk.

- **M08-FR-02 (MUST):** Support versioned routing policy, prompt reference, model role and capability preferences with diff/simulate/rollback.

- **M08-FR-03 (MUST):** Apply resource budgets and unknown-risk escalation before delegating work.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Triage, prioritization and task planning.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M08-AT-01:** Operator changes a deep-investigation profile without code and simulator reports changed outcomes. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M08-AT-02:** Ambiguous task routes to safe discovery/clarification rather than blind write tool. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M08-RT-01:** A model must not choose or grant its own privileged execution level. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M08-RT-02:** Adversarial synonym must not bypass mandatory evidence gates. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M08-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S03. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M09

Source: `docs/prds/M09.md`

# M09 — Sufficiency, evidence and stopping judgment

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S02. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Ensure the completed work answers the requester’s decision need or clearly states its limits.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M07, M10, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M09-FR-01 (MUST):** Evaluate claim coverage, conflicting evidence, recency and whether further investigation likely changes the decision.

- **M09-FR-02 (MUST):** Require independently recorded outcome assessment before final delivery for nontrivial work.

- **M09-FR-03 (MUST):** Return complete, partial, blocked or inconclusive with bounded follow-up, never fabricated certainty.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Sufficiency, evidence and stopping judgment.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M09-AT-01:** Misleading correlation cannot be reported as causal proof. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M09-AT-02:** Insufficient report triggers a bounded retry or partial delivery with specific open gaps. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M09-RT-01:** A model grading its own output alone is not valid proof. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M09-RT-02:** No infinite self-critique loop to satisfy an undefined standard. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M09-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S02. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M10

Source: `docs/prds/M10.md`

# M10 — Audience-aware delivery and artifact packaging

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S02. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Present only relevant decision information to humans and typed results to systems.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M06, M07, M12. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M10-FR-01 (MUST):** Use shared result ID with audience adapters for human, system and group destinations.

- **M10-FR-02 (MUST):** Deliver concise summary with expand-on-demand and links to versioned evidence.

- **M10-FR-03 (MUST):** Persist delivery attempts, acknowledgement and last confirmed channel status.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Audience-aware delivery and artifact packaging.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M10-AT-01:** Human receives concise finding; machine receives schema-valid result for same execution. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M10-AT-02:** Duplicate callback does not create duplicate final notification. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M10-RT-01:** Do not send sensitive results to wrong channel or group. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M10-RT-02:** Do not mark an outbound message delivered before provider acknowledgement. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M10-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S02. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M11

Source: `docs/prds/M11.md`

# M11 — Episodic and semantic memory

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S03. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Recover prior working context and preferences with provenance and scope filters.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M07, M25, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M11-FR-01 (MUST):** Keep factual episodic records separate from inferred preference and summarization.

- **M11-FR-02 (MUST):** Search by requester, time, project, method and commitment, and provide source-linked references.

- **M11-FR-03 (MUST):** Apply updates/retention/corrections without silently overwriting original evidence.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Episodic and semantic memory.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M11-AT-01:** A request for “the study from last week” resolves or asks focused clarification. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M11-AT-02:** Conflicting memory evidence remains marked uncertain and does not contaminate another user. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M11-RT-01:** Embedding similarity must not override access control. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M11-RT-02:** Summaries cannot replace original artifact lineage. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M11-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S03. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M12

Source: `docs/prds/M12.md`

# M12 — Versioned artifacts and reproducible edits

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S03. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Preserve editable source of PRDs, charts, files and reports across revisions.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M11, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M12-FR-01 (MUST):** Store artifact IDs, immutable versions, content hashes, source lineage and format metadata.

- **M12-FR-02 (MUST):** Route incremental edit to a capable handler when the source format is genuinely editable.

- **M12-FR-03 (MUST):** Maintain user-facing summary separate from full generated deliverable.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Versioned artifacts and reproducible edits.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M12-AT-01:** Old chart can be revised with one additional data series while retaining original version. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M12-AT-02:** Non-editable source triggers honest request or conversion plan, never invented data. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M12-RT-01:** File paths from untrusted documents cannot escape authorized workspace. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M12-RT-02:** Never silently replace original artifact when write approval is required. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M12-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S03. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M13

Source: `docs/prds/M13.md`

# M13 — Personalization and relationship preferences

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S03. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Adapt conversational style to each user without excessive interviews or unwanted personalization.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M03, M11. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M13-FR-01 (MUST):** Distinguish explicit, observed and inferred preferences, each with confidence and scope.

- **M13-FR-02 (MUST):** Allow inspect, correction, expiration, and rollback of profile updates.

- **M13-FR-03 (MUST):** Separate communication preferences from permissions and quality requirements.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Personalization and relationship preferences.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M13-AT-01:** Repeated request for shorter replies updates a low-risk style preference, not audit policy. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M13-AT-02:** User correction removes stale inferred preference from future decisions. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M13-RT-01:** Do not infer sensitive personal traits from documents. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M13-RT-02:** Preference of one group must not become a universal default. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M13-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S03. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M14

Source: `docs/prds/M14.md`

# M14 — SCS capability manifest and registry

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Define portable, discoverable outcome capabilities independent of executable technology.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M25, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M14-FR-01 (MUST):** Validate namespaced IDs, semver, typed input/output, positive/negative intents, outcome and evidence contracts.

- **M14-FR-02 (MUST):** Maintain definitions, executable bindings and measured assurance as separate records.

- **M14-FR-03 (MUST):** Publish packages only after static/semantic checks and authorized lifecycle promotion.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to SCS capability manifest and registry.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M14-AT-01:** Installing an unknown capability makes it discoverable on next run with no root prompt edits. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M14-AT-02:** Invalid capability requesting destructive effects under read-only policy is rejected. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M14-RT-01:** Manifest cannot be auto-enabled merely because schema passes. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M14-RT-02:** A capability ID is not a skill, agent, prompt or tool name. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M14-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M15

Source: `docs/prds/M15.md`

# M15 — Capability discovery, resolver and execution controller

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Let the actual model discover and request capabilities while the runtime selects safe implementation.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M14, M17, M25, M31. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M15-FR-01 (MUST):** Expose search, describe, invoke and status via stable tool schemas and progressive disclosure.

- **M15-FR-02 (MUST):** Rank candidates by outcome fit, permission, assurance, cost, model compatibility and health.

- **M15-FR-03 (MUST):** Enforce output contracts and execution-state guards; support graceful unavailability and fallback.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Capability discovery, resolver and execution controller.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M15-AT-01:** Real LLM selects a newly installed, unnamed capability from a distracting catalog. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M15-AT-02:** Disabled, incompatible or unauthorized capability cannot be invoked even if LLM requests it. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M15-RT-01:** No hard-coded golden target passed to router in evaluation. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M15-RT-02:** A malformed tool call never becomes an unvalidated side effect. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M15-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M16

Source: `docs/prds/M16.md`

# M16 — Agent Skills discovery and packaging

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S03. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Reuse portable procedural skills and tools independently from SCS outcome contracts.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M14, M19, M25. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M16-FR-01 (MUST):** Read skills with explicit manifest and trusted boundary; discover incrementally rather than injecting all instructions.

- **M16-FR-02 (MUST):** Validate included scripts/assets and reject auto-execution of downloaded code.

- **M16-FR-03 (MUST):** Maintain version, provenance, permission mapping and execution evidence.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Agent Skills discovery and packaging.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M16-AT-01:** Skill installed from local directory is only visible to eligible capability. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M16-AT-02:** Malicious SKILL.md cannot rewrite approval policy or leak secrets. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M16-RT-01:** Skill instructions are untrusted data until authorized. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M16-RT-02:** Skill does not imply capability assurance or invocation rights. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M16-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S03. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M17

Source: `docs/prds/M17.md`

# M17 — LLM providers, routing and competence profiles

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Support inexpensive and stronger models with honest feature probes and measured quality thresholds.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M25, M26, M31. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M17-FR-01 (MUST):** Support OpenRouter/OpenAI-compatible plus explicit native API adapters for nonportable features.

- **M17-FR-02 (MUST):** Probe tool calls, JSON output, timeouts, concurrency and streaming; enforce configured budgets. Record region and pricing as separately sourced operator/provider attestations or UNKNOWN, never infer them from protocol success.

- **M17-FR-03 (MUST):** Route to small model for safe simple work, escalate to stronger approved provider on failure or ambiguity.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to LLM providers, routing and competence profiles.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M17-AT-01:** A tool-incompatible model is rejected before capability invocation. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M17-AT-02:** Failing small-model schema parsing triggers bounded repair/escalation, not silent success. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M17-RT-01:** Provider compatibility label is not proof of supported functions. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M17-RT-02:** Codex sign-in is not an OpenAI API key. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M17-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M18

Source: `docs/prds/M18.md`

# M18 — Agent and harness adapters

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S04. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Add and remove Codex, Claude Code, Hermes, Tamanduá, A2A or custom executors without changing ERI.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M14, M15, M25, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M18-FR-01 (MUST):** Provider capability declaration includes invoke/status/resume/cancel/stream and artifact support.

- **M18-FR-02 (MUST):** Use signed/approved executable, sandbox, scopes, quotas and stable correlation IDs.

- **M18-FR-03 (MUST):** Handle killed/uninstalled harness through typed degradation and rerouting without losing root commitment.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Agent and harness adapters.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M18-AT-01:** New Excel chart agent installed from a descriptor is discoverable after approval and passing capability eval. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M18-AT-02:** Removal of active harness marks execution degraded; secretary remains responsive. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M18-RT-01:** An agent does not inherit tenant-wide credentials. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M18-RT-02:** Unsupported resume cannot be silently emulated as successful. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M18-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S04. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M19

Source: `docs/prds/M19.md`

# M19 — MCP and action gateway

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S04. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Discover external tools and enforce every action before side effects.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M25, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M19-FR-01 (MUST):** Support MCP client discovery; map tool metadata to scopes and side-effect level.

- **M19-FR-02 (MUST):** Require identity-specific authorization, policy and consent before dispatch, even if model requested tool.

- **M19-FR-03 (MUST):** Record effect intent, outcome, unknown status and available compensation.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to MCP and action gateway.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M19-AT-01:** Read-only simulated MCP tool executes with proof of no state changes. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M19-AT-02:** Tool advertising read-only but mutating state is detected in contract harness where observable. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M19-RT-01:** Prompt injection in tool description cannot override authorization. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M19-RT-02:** MCP token forwarded only to authorized destination and not leaked in logs. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M19-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S04. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M20

Source: `docs/prds/M20.md`

# M20 — Second-brain provider adapters

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S04. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Read and optionally write knowledge through local filesystem, Git, Obsidian/Markdown, GBrain, LLM Wiki and remote providers.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M11, M25. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M20-FR-01 (MUST):** Declare read/search/list/write/watch capabilities and permissions; no universal writable-brain assumption.

- **M20-FR-02 (MUST):** Maintain source references, ACL filtering, ingestion cursors, timestamps, provenance and conflict resolution.

- **M20-FR-03 (MUST):** Support offline local provider and mock remote provider before adding optional real integrations.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Second-brain provider adapters.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M20-AT-01:** Folder knowledge query returns cited accessible records. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M20-AT-02:** Remote brain unavailable does not prevent normal greeting or unrelated work. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M20-RT-01:** Untrusted repository README cannot become privileged instruction. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M20-RT-02:** Stale source cannot be presented as current verified policy. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M20-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S04. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M21

Source: `docs/prds/M21.md`

# M21 — Knowledge, ecosystem and repository discovery

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S05. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Find reusable patterns, engineering standards, repositories and published knowledge before inventing solutions.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M19, M20, M25. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M21-FR-01 (MUST):** Traverse authorized doc/repo references recursively with cycle, scope, depth and cost limits.

- **M21-FR-02 (MUST):** Distinguish observed standard from inferred convention based on corpus evidence.

- **M21-FR-03 (MUST):** Check license, maintenance, source credibility, compatibility and provenance before recommending code reuse.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Knowledge, ecosystem and repository discovery.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M21-AT-01:** Discover corporate PRD conventions from fixture repo and identify exceptions. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M21-AT-02:** Graph of circular RFC references terminates with complete coverage report. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M21-RT-01:** No automatic execution of downloaded scripts. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M21-RT-02:** No unapproved crawl across private or unrelated repositories. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M21-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S05. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M22

Source: `docs/prds/M22.md`

# M22 — Software engineering discovery and specifications

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S05. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Produce technically grounded PRD/TRD/DSD/ADR/RFC and implementation requests for external agents.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M21, M12, M09. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M22-FR-01 (MUST):** Discover and cite local standards before writing; separate evidence, assumptions and recommendations.

- **M22-FR-02 (MUST):** Link cross-document requirements and identify missing decisions before decomposing work.

- **M22-FR-03 (MUST):** Deliver versioned specs with traceability and bounded acceptance tests.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Software engineering discovery and specifications.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M22-AT-01:** Novel PRD based on repository docs includes source trace links and uncertainty. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M22-AT-02:** Conflicting ADRs trigger an explicit conflict decision, not fabricated harmonization. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M22-RT-01:** Do not expand a short PRD into hundreds of speculative tickets. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M22-RT-02:** No “implemented” claim from documents-only generation. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M22-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S05. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M23

Source: `docs/prds/M23.md`

# M23 — Incident investigation and root-cause analysis

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S05. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Conduct deep, read-safe technical investigation with transparent hypotheses and outcomes.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M21, M19, M09. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M23-FR-01 (MUST):** Construct incident timeline from authorized logs/events, identify competing hypotheses.

- **M23-FR-02 (MUST):** Distinguish cause, correlate and unsupported speculation with source provenance.

- **M23-FR-03 (MUST):** Request missing SME input when worth its interruption cost, using permissioned communication.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Incident investigation and root-cause analysis.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M23-AT-01:** Missing dashboard company investigation identifies a concrete permission or data-path hypothesis. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M23-AT-02:** Misleading timestamp coincidence does not become RCA without corroboration. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M23-RT-01:** No production mutation without explicit gate. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M23-RT-02:** A failed telemetry source must remain visible as an evidence gap. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M23-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S05. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M24

Source: `docs/prds/M24.md`

# M24 — Data analysis and causal inquiry

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S05. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Investigate trends, treatment effects and confounders without overstating causality.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M19, M20, M09. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M24-FR-01 (MUST):** Verify data lineage, cohorts, units, selection effects and measurement biases.

- **M24-FR-02 (MUST):** Represent causal DAG/hypotheses and choose appropriate tests if supported.

- **M24-FR-03 (MUST):** Report observed associations and unknown identification assumptions explicitly.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Data analysis and causal inquiry.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M24-AT-01:** Simpson paradox dataset prevents false causal conclusion. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M24-AT-02:** Ads position 4/5 decline vs 1/3 includes selection-confounding caveat. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M24-RT-01:** No fabricated experiment or inaccessible data result. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M24-RT-02:** No unconditional causal assertion from observational correlation. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M24-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S05. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M25

Source: `docs/prds/M25.md`

# M25 — Preventive policy and approvals

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Enforce safety before tool calls and capability side effects regardless of model compliance.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M25-FR-01 (MUST):** Grant authorities through trusted configuration, not from prompts or memory.

- **M25-FR-02 (MUST):** Evaluate actor, tenant, destination, requested effect, data class, consent and expiry.

- **M25-FR-03 (MUST):** Deny, defer approval, or allow with auditable decision and narrowed credentials.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Preventive policy and approvals.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M25-AT-01:** Forged instruction in Slack message cannot self-approve a write. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M25-AT-02:** Unapproved external message is never sent even when all prompts request it. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M25-RT-01:** No permissive fallback when policy engine is absent. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M25-RT-02:** No approval reuse across different operation signatures. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M25-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M26

Source: `docs/prds/M26.md`

# M26 — Audit, observability and evidence

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Reconstruct every request, model decision, routing choice, side effect and delivery attempt.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M26-FR-01 (MUST):** Assign correlation IDs and immutable event records with versioned contracts.

- **M26-FR-02 (MUST):** Record model/agent/config/prompt/capability hashes, timestamps, costs, evidence links, decisions and status.

- **M26-FR-03 (MUST):** Support sanitized trace replay without reexecuting irreversible actions.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Audit, observability and evidence.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M26-AT-01:** Operator can explain why a capability was chosen for a task. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M26-AT-02:** Secrets and restricted content are redacted before trace export. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M26-RT-01:** Do not claim fully reproducible model outputs without matching provider snapshot. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M26-RT-02:** Audit logs must be access-controlled and retention bounded. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M26-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M27

Source: `docs/prds/M27.md`

# M27 — Evaluation-driven improvement and self-evolution

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S06. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Allow agents to propose better prompts, workflows, skills and routing without uncontrolled self-modification.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M09, M13, M14, M25, M26, M30. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M27-FR-01 (MUST):** Create staged candidate changes with baseline, targeted eval and sealed holdout comparison.

- **M27-FR-02 (MUST):** Require semantic compatibility, risk checks, approvals and instant rollback for promotion.

- **M27-FR-03 (MUST):** Monitor post-promotion regressions and record attribution of improvement.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Evaluation-driven improvement and self-evolution.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M27-AT-01:** Candidate that increases unsafe tool-use accuracy regression fails promotion. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M27-AT-02:** A small-model-optimized prompt can be rolled back without affecting ledger. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M27-RT-01:** Never auto-promote permission increases. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M27-RT-02:** Self-judged improvement alone is insufficient evidence. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M27-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S06. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M28

Source: `docs/prds/M28.md`

# M28 — Portability, operations and enterprise deployment

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S07. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Install local/hybrid/corporate instances with resource awareness and no mandatory Docker.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M01, M07, M17, M18, M25. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M28-FR-01 (MUST):** Support user-scoped install, config doctor, backup/restore and process supervisor by OS.

- **M28-FR-02 (MUST):** Profile RAM/CPU/storage, sleep behavior, proxy, corporate CA, offline setup and approved provider allowlists.

- **M28-FR-03 (MUST):** Keep durable engine behind port and distinguish local dev reliability from enterprise HA.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Portability, operations and enterprise deployment.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M28-AT-01:** Windows/macOS/Linux native smoke without Docker. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M28-AT-02:** Offline enterprise profile refuses disallowed egress and works with supplied authorized assets. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M28-RT-01:** Never bundle unlicensed third-party binaries. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M28-RT-02:** One laptop sleeping means no background execution without remote always-on worker. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M28-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S07. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M29

Source: `docs/prds/M29.md`

# M29 — Channel and inbound/outbound messaging

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S04. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Normalize CLI and optional Slack/Telegram/email inbound events and deliver appropriately to the originating audience.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M02, M06, M07, M10, M25. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M29-FR-01 (MUST):** Capture authentic sender, channel, conversation thread, request ID and delivery intent.

- **M29-FR-02 (MUST):** Use inbox/outbox, retries, idempotency where provided, expiry and uncertain-delivery reconciliation.

- **M29-FR-03 (MUST):** Treat notification preferences and channels as user-specific, not provider-wide.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Channel and inbound/outbound messaging.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M29-AT-01:** Fake Slack HMAC/replay and rate-limit tests pass locally without Slack credentials. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M29-AT-02:** Real-provider absence returns NOT_VERIFIED_EXTERNAL, not validated. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M29-RT-01:** Do not send to a guessed user or channel. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M29-RT-02:** Do not claim receipt when provider times out after possible send. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M29-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S04. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M30

Source: `docs/prds/M30.md`

# M30 — Behavior package, prompt and statechart compiler

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Transform versioned operator configuration and agent-proposed drafts into validated, auditable prompts and control policies.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M14, M25, M26. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M30-FR-01 (MUST):** Compile immutable system constraints, selected interaction profile, active capacity contracts and bounded context into a prompt receipt.

- **M30-FR-02 (MUST):** Validate declarative statechart states/edges/guards; reject unsafe or unreachable transitions and missing terminal paths.

- **M30-FR-03 (MUST):** Expose propose/validate/render/simulate/diff/promote/rollback with review gates; never eval executable expressions from YAML.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Behavior package, prompt and statechart compiler.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M30-AT-01:** Given profile change, compiled prompt/statechart hash changes predictably and rollback restores previous digest. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M30-AT-02:** Malformed machine with dead-end state, privilege-changing guard or infinite unbudgeted cycle is rejected. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M30-RT-01:** A generated prompt cannot grant tool permission. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M30-RT-02:** An LLM-generated transition proposal cannot enter production without semantic checks. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M30-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.

---

## Module M31

Source: `docs/prds/M31.md`

# M31 — Context engineering and model competence calibration

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Help fast and weak reasoning models correctly use context, tools and state without overloading prompts.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M17, M30, M15. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M31-FR-01 (MUST):** Build small, typed per-decision context envelopes with current goal, state, relevant history, tool descriptions and uncertainty.

- **M31-FR-02 (MUST):** Calibrate model support and empirical routing performance separately by model/provider/config hash.

- **M31-FR-03 (MUST):** Use deterministic fallback, repair budget and optional stronger model escalation while preserving task ownership.

## 4. Contract and state expectations

- Inputs MUST be typed and include `request_id`, `actor_ref`, `tenant_ref` or an explicit local principal, `policy_version`, and `trace_id` as appropriate to Context engineering and model competence calibration.

- Results MUST declare `status`, `evidence_refs`, `uncertainties`, and `next_action` where work is nontrivial. External effects must be mediated through the effect gateway and never through arbitrary prompt instructions.

- The module may compose multiple SCS capabilities, but it MUST expose a stable business boundary and MUST NOT leak vendor SDK types to domain callers.

- State-changing operations require valid state revision, idempotency intent, authorization decision and a trace. Absence of an optional integration must return typed `UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`.

## 5. Observable acceptance tests

- **M31-AT-01:** Small model handles greeting without tool calling and complex task routes to safe capability discovery. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

- **M31-AT-02:** Context update after user correction changes only relevant prompt segment and keeps validated instructions stable. **Evidence:** public CLI/contract entry, trace, asserted state and negative-path observation.

## 6. Threat model and per-module red team

- **M31-RT-01:** Huge context window is not evidence of better reasoning. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

- **M31-RT-02:** Prompt truncation must not discard security or ownership facts. **Proof:** adversarial test exercising the actual policy or state gate, not an LLM refusal alone.

## 7. Explicit non-goals and scope constraints

- Do not create a separate microservice or specialized conversational agent solely because this module has a PRD.

- Do not add new tools, models, queues, UI, policy languages or data stores unless a concrete acceptance case proves the existing boundaries insufficient.

- No direct access to production, no unapproved external sending or writes, and no changes to security configuration through generated prompts.

## 8. Test plan and implementation gate

- Require one public-path positive, one discriminating negative and a fault test only where failure can corrupt state or safety. Reuse shared contract tests rather than copying them to every module.

- Unit/state-transition/property tests for deterministic decisions; fake services for missing provider APIs; live LLM eval only where model behavior is under test; live external smoke marked separately.

- Track each FR/AT/RT ID in the coverage registry with `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED` or `NOT_VERIFIED_EXTERNAL`. No equivalent “green” from documents-only validation.

## 9. Definition of done

An implementer can demonstrate both M31-AT cases from the public entry path, show the negative and relevant failure behavior, archive sanitized evidence, and justify that no unrequested scope was introduced.

## 10. Implementation handoff

Target phase: S00. Start from `AGENTS.md`, the canonical TRD, behavior compiler RFC and this PRD. Maintain SDD → TDD → EDD traceability; use a fresh branch and record actual coverage.

## Milestone interpretation

The delivery slice identifies first implementation, not automatic completion of every requirement in this module. `docs/implementation/ROADMAP.md` and the requirements traceability matrix define partial obligations and later dependency gates. An unmet AT/RT remains NOT_RUN/BLOCKED; passing an early slice does not mark the whole module PASS. Shared contract, safety and scope requirements remain mandatory at every exercised boundary.
