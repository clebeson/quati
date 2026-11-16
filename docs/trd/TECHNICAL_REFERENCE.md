# TRD-000 — Technical Reference Architecture (v8)

## 1. Architecture decisions and design constraints
**Start as a modular monolith** (`quati` CLI and `quati worker`) with protected pure domain logic, Pydantic AI for the model interaction loop, SCS outcome manifests, governed prompt/context and statechart compilation, a ledger-driven worker (ADR-015) and one LedgerPort with two backends: SQLite (LOCAL) and PostgreSQL with RLS (SERVER). Add optional interfaces/adapters only when a demonstrable use case requires them. No web UI or Docker requirement. The HTTP server (`quati server`) exists only in the SERVER profile (ADR-013); LOCAL runs in-process.

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
| CLI | Typer | typed commands, single choice | argparse, Web/desktop |
| Agent loop | Pydantic AI + on-demand capabilities/tools | progressive disclosure and typed tool calls | OpenAI Agents SDK, LangGraph, custom engines |
| Data validation | Pydantic v2 + JSON Schema Draft 2020-12 | typed, language-agnostic contracts | handwritten shape validators |
| Durable execution | Ledger-driven worker behind the narrow `DurableRunner` port (ADR-015, RFC-003) | one source of truth, no engine server | DBOS or Temporal adapters by new ADR |
| Persistent business state | One LedgerPort: SQLite (journal mode by the version gate of RFC-003 §9: WAL only on SQLite ≥ 3.51.3 or the backports 3.50.7 / 3.44.6, otherwise `journal_mode=TRUNCATE` with a doctor WARN; `BEGIN IMMEDIATE`) for LOCAL; PostgreSQL with RLS for SERVER; stdlib `sqlite3` and `psycopg` 3 | ledger, outbox, ACL, audit on both profiles | managed PostgreSQL variants |
| Migrations | numbered plain SQL files per dialect directory with a checksum table | reviewable, no ORM | Alembic |
| Config and secrets | TOML via `tomllib` in the `platformdirs` user config dir (SERVER: path from env); secrets via `keyring` with env-var fallback, referenced only by `secret_ref` | portable, no secrets in files | other secret managers as adapters |
| Logging | JSON Lines; optional OpenTelemetry extra | local-first | hosted observability |
| Packaging and lock | `uv tool install` or pipx; `uv lock` cross-platform with hashes, runtime and test groups (requirement only) | reproducible on three OSes | OS installers |
| Statechart implementation | plain validated transition table + pure reducer initially | small, auditable, fast | `transitions` library if nested graphs needed; LangGraph for specialist graph |
| Prompt compilation | Pure Python string assembly | deterministic artifacts and hashes | Jinja2 for fixed trusted templates, DSPy candidate optimization after eval |
| Model providers | OpenRouter via OpenAI-compatible transport + feature probing | user-preferred tests | native OpenAI, Anthropic, Gemini, xAI, enterprise |
| Harness providers | interface with feature flags and one real adapter later | hot-swap/no vendor leak | Codex SDK, Claude Agent SDK, Hermes, Tamanduá, A2A |
| Knowledge | local Markdown/Git initially + BrainProvider port | easiest auditable proof | GBrain, LLM Wiki, Obsidian integration, remote |
| Testing | pytest, jsonschema, property/state tests, Pydantic Evals | proof by risk | Pact when third-party consumer-driven contracts warranted |
| Tracing | OpenTelemetry-compatible spans + sanitized local event log | local-first and vendor-neutral | hosted observability |

## 4. Portability and profiles
Two deployment profiles (ADR-013, ADR-015). **LOCAL**: in-process application, SQLite (WAL or `TRUNCATE` journal per RFC-003 §9), OS-bound identity, worker as a local process (`quati worker run` or scheduler-driven `quati worker tick`, ADR-016). **SERVER**: `quati server` with PostgreSQL RLS, OIDC, and the worker inside the server. Installer probes OS/architecture, proxies/CA, provider tool support and user permissions; it never needs Docker or a database server for LOCAL. Windows/macOS/Linux tests cover worker supervision via OS schedulers, install, filesystem encoding and exit behavior. If the user machine sleeps, nothing executes; on wake the catch-up rule fires missed timers once, with `late_by_seconds`, unless `fire_until` has passed (RFC-003 §6). Timeliness holds only while a worker runs.

## 5. Durable execution (ledger-driven worker)
DBOS is not used in v8.1 (ADR-015). A worker claims a ready work item with a lease, runs one bounded step, and commits the event, outbox and next timer in one ledger transaction; expired leases are reclaimed on restart. Timers are ledger rows with `fire_at` and `fire_until`. `DurableRunner` operations are `enqueue`, `status`, `signal`, `cancel`, `schedule` (RFC-003). Engine adapters for DBOS or Temporal are deferred and need a new ADR; do not build a Temporal clone.

## 6. Persistence and event schema
Tables (logical, exact DDL produced in S02): `principals`, `requests`, `conversation_turns`, `commitments`, `commitment_events`, `workflow_refs`, `outbox`, `outbox_attempts`, `effect_intents`, `artifact_refs`, `capability_definitions`, `capability_bindings`, `model_competence`, `profile_versions`, `policy_decisions`, `memory_refs`, `audit_events`, `evaluation_runs`. Version all mutated rows, unique idempotency keys scoped to principal/action and use append-only audit events. Also `work_items`, `timer_intents`, `inbox_messages`, `worker_heartbeats`, `worker_locks` and `schema_migrations`. Every table has `tenant_id NOT NULL`; data objects have `space_id`; unique keys start with `tenant_id`. Step commits and outbox transitions share one ledger transaction to prevent acknowledgement races.

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
quati init --profile local
quati doctor --json
quati config validate|diff|simulate|propose|apply|rollback
quati profiles list|describe|test
quati behavior compile|render|validate|eval
quati models add|probe|bench
quati capabilities list|search|describe|install|import|validate|enable|disable|eval   # RFC-015
quati agents add|probe|list|remove
quati brains add|probe|list|sync
quati ask "Please draft a PRD about feature X" --json
quati tell <commitment-id> "Also check our incident RFCs"
quati status <commitment-id> --json
quati inbox [--unread] [--ack <message-id>]   # alias: quati messages
quati audit show <commitment-id> --json
quati login | logout | whoami                     # RFC-013; login is SERVER (OIDC device grant), whoami both
quati spaces list|create|describe <space-id>      # RFC-013
quati grants list|add|revoke <space-id> ...       # RFC-013 space grants (MANAGER only)
quati principals list|add|disable                 # RFC-013, SERVER profile, tenant ADMIN
quati approvals list [--state PENDING] | revoke <approval-request-id>   # RFC-014
quati approve <approval-request-id>               # RFC-014, HUMAN + TTY only
quati deny <approval-request-id>                  # RFC-014, HUMAN + TTY only
quati policy show | edit | diff <file> | apply [--adopt] <file>         # RFC-014
quati worker run          # foreground loop
quati worker tick         # drain due work, then exit (for systemd user timer, launchd, Task Scheduler)
quati worker install [--interval 60s] | uninstall   # ADR-016: explicit user-level scheduler entry
quati memory consolidate <space-id> | candidates [<space-id>] | diff <snapshot-id> | promote <snapshot-id> | rollback <space-id>   # RFC-005 v8.2
quati server              # SERVER profile only: HTTP API + worker
quati eval run --suite <suite> --provider <profile>
```
Every command exposes safe errors and structured JSON with stable exit codes. `approve` and `deny` refuse when stdin/stdout is not a TTY (LOCAL), when `QUATI_CAPABILITY_CONTEXT` is set (the command is running inside a capability or agent), and when the token is not a HUMAN principal holding `quati:approve` (RFC-014). Work progresses while the CLI is closed only if a worker is running (`worker run`, a scheduler invoking `worker tick`, or `quati server`). `quati doctor` warns when no worker heartbeat was seen within 2x the interval. Delivery in LOCAL is to the inbox (DELIVERED when committed; ACKNOWLEDGED when read via `quati inbox`); an optional desktop notification is best-effort and never an acknowledgement (ADR-016).

## 14. Integration into code factory
The spec agent owns FR→contract→test generation; the implementation agent owns working code; an independent reviewer owns adversarial test selection and evidence audit. A successful compile of config is NOT a successful LLM eval; successful simulated provider test is NOT external certification. See `docs/governance/FACTORY_OPERATING_RULES.md`.

## 15. Deferred architecture questions
- Enterprise HA requirements (multi-instance SERVER workers) and any future DBOS/Temporal adapter, including licensing review, need a new ADR.
- Per-model competence thresholds and resource budgets require real benchmarking.
- Corporate model gateways have no assumed compatibility; probe each capability.
- Cross-engine workflow migration requires drain/checkpoint strategy and is not simple history import.
- External connectors require owner authorization before full live smoke.
