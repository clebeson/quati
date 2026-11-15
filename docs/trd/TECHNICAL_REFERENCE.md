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
