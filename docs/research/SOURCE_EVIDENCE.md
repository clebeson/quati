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
