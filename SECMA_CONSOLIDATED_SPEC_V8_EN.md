# SECMA v8 — Consolidated English Product and Technical Specification

---

> **Design only:** not an implemented SECMA application. Canonical detail remains in source files and their IDs.

---

## 1. Product Definition

---

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


---

## 2. Technical Reference

---

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

---

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
| M08 | [Triage, prioritization and task planning](docs/prds/M08.md) | S03 | M04 M05 M14 M15 M30 M31 |
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

---

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


---

## 5. Test Coverage Rationale

---

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

---

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

---

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

---

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

---

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

---

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


---

## Module M02

---

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


---

## Module M03

---

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


---

## Module M04

---

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


---

## Module M05

---

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


---

## Module M06

---

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


---

## Module M07

---

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


---

## Module M08

---

# M08 — Triage, prioritization and task planning

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S03. **Normative language:** MUST/SHOULD/MAY.

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


---

## Module M09

---

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


---

## Module M10

---

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


---

## Module M11

---

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


---

## Module M12

---

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


---

## Module M13

---

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


---

## Module M14

---

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


---

## Module M15

---

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


---

## Module M16

---

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


---

## Module M17

---

# M17 — LLM providers, routing and competence profiles

**Specification status:** PROPOSED, NOT IMPLEMENTED. **Delivery slice:** S00. **Normative language:** MUST/SHOULD/MAY.

## 1. Purpose and outcome

Support inexpensive and stronger models with honest feature probes and measured quality thresholds.

## 2. Responsibility and ownership

This module owns its observable outcome; it must not independently reinterpret identity, authorization, durable commitment or delivery status owned by M02/M25/M07/M10. Adjacent modules: M25, M26, M31. These are integration relationships, NOT a mandate to build them all in advance.

## 3. Normative requirements

- **M17-FR-01 (MUST):** Support OpenRouter/OpenAI-compatible plus explicit native API adapters for nonportable features.

- **M17-FR-02 (MUST):** Probe tool calls, JSON output, timeouts, concurrency, streaming, region, budgets and pricing instead of guessing.

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


---

## Module M18

---

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


---

## Module M19

---

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


---

## Module M20

---

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


---

## Module M21

---

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


---

## Module M22

---

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


---

## Module M23

---

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


---

## Module M24

---

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


---

## Module M25

---

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


---

## Module M26

---

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


---

## Module M27

---

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


---

## Module M28

---

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


---

## Module M29

---

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


---

## Module M30

---

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


---

## Module M31

---

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
