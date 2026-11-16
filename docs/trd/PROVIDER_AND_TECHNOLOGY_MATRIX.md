# Technology and Provider Matrix — Decision and Capability Semantics

**Research date:** November 15, 2026. Product-specific performance and OS support are NOT measured. URLs are source evidence, not proof that any specific provider is already installed or approved.

| Component | Current role | Available interface | Limitation / decision gate | Authoritative reference |
|---|---|---|---|---|
| Pydantic AI capabilities | initial on-demand bundle & tool loop | typed tools, deferred capability | SCS remains separate; probe exact release | https://pydantic.dev/docs/ai/capabilities/on-demand/ |
| Pydantic AI Evals | behavioral evaluation | cases / datasets | external judge needs calibration | https://ai.pydantic.dev/evals/ |
| DBOS Python | deferred (not used in v8.1, ADR-015) | workflow, step, queue, messages, events | possible future adapter behind DurableRunner; suspension enterprise | https://docs.dbos.dev/python/programming-guide |
| Temporal | deferred; removed from the engine enum | workflows, signals, queries | distinct runtime; no simple history import | https://docs.temporal.io/ |
| `transitions` | optional Python FSM | pure state machine, guards, diagrams | not mandatory in MVP | https://github.com/pytransitions/transitions |
| LangGraph | optional specialist reasoning graph | graph/checkpoint/interrupt | resuming re-executes node code; side-effect care | https://docs.langchain.com/oss/python/langgraph/interrupts |
| OpenRouter | initial user-token LLM endpoint | OpenAI-compatible API | models differ in tool/json support | https://openrouter.ai/docs/ |
| Local OpenAI-compatible server (Ollama, vLLM, llama.cpp server) | optional LOCAL model profile, no data leaves the machine | OpenAI-compatible chat/tools | tool-call and JSON-schema support vary per model; probe decides the structured-output ladder (BOUNDARY_CONTRACTS ModelPort); no competence claim without the S00 eval | https://github.com/ollama/ollama/blob/main/docs/openai.md |
| Native OpenAI API | optional direct model provider | model/tool/structured output | API access not implied by Codex login | https://developers.openai.com/api/ |
| OpenAI Agents SDK | optional alternate agent runtime | handoffs/tools/guardrails | not required in Quati protected kernel | https://developers.openai.com/api/docs/guides/agents/sdk |
| OpenAI Codex SDK | coding harness adapter | Python SDK/app-server | SDK and managed cloud Agents API are distinct | https://learn.chatgpt.com/docs/codex-sdk |
| OpenAI Agents API | managed Codex harness option | managed API | explicit pricing, entitlement and data policy | https://developers.openai.com/api/docs/guides/agents-api/overview |
| Claude Agent SDK | code/agent harness | supported SDK/CLI | auth and permissions differ from raw model API | https://platform.claude.com/docs/en/agent-sdk/overview |
| Anthropic model API | native model provider | Messages/tools | native features may require separate adapter | https://platform.claude.com/docs/en/api |
| Gemini API | optional provider | model/structured/tool | feature and model support varies | https://ai.google.dev/gemini-api/docs |
| xAI API | optional provider | compatible/native | do not assume parity; run probe | https://docs.x.ai/ |
| Corporate Genplat-style gateway | restricted enterprise model endpoint | configured endpoint/CA/auth | tenant-specific contract; no generic compatibility claim | organization-provided documentation required |
| Hermes/Tamanduá/Opai | optional specialist harness | capability binding and subprocess/SDK when available | do not assume a canonical protocol for all | project-specific docs required |
| MCP | tool discovery & invocation | client/server protocol | tools are not outcome capabilities | https://modelcontextprotocol.io/ |
| A2A | agent-to-agent task exchange | Agent Cards and task events | not a replacement for durable ledger | https://a2a-protocol.org/ |
| Agent Skills | procedural reusable skills | SKILL.md, assets | no automatic authority or outcome guarantee | https://agentskills.io/ |
| OpenTelemetry | standard traces | spans/context | telemetry destination optional, local by default | https://opentelemetry.io/ |
| DSPy | future eval-based prompt optimization | optimization programs | experimental candidate generation, not runtime authority | https://dspy.ai/ |
| PostgreSQL | SERVER-profile ledger (RLS); SQLite is the LOCAL ledger | native driver | remote approved DB allowed; no Docker requirement | https://www.postgresql.org/docs/ |

## Adapter introduction policy
Do not implement all provider adapters now. Begin with one verified OpenRouter tool-capable model and deterministic fake provider. Next, implement one real harness adapter selected by the user and one local brain adapter. Add another only when a real requirement/test or enterprise constraint demands it. Each adapter registers features, version, credential source and independent conformance state.

## Native cross-platform packaging
Use Python wheel/`uv` for developer installs and packaging smoke tests on Linux x64, Windows x64 and macOS ARM64. Bundled binaries, enterprise entitlements, process supervisors and offline distribution are later release requirements and cannot be assumed from “pure Python” alone. Third-party license obligations must be checked per installed provider.
