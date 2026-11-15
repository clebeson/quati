# External Dependency and Source Review

Reviewed: 2026-11-15. Scope: architecture-critical official documentation plus complete URL inventory from the research register and provider matrix. Documentation retrieval is L0 evidence, never provider conformance, local runtime qualification, entitlement, pricing approval or security certification. No credentials or production systems were accessed.

## Observed facts and implications

| Boundary | Official source retrieved | Observation | SECMA implication |
|---|---|---|---|
| Pydantic AI model transport | https://pydantic.dev/docs/ai/models/openai/ | Custom OpenAI client/base URL is supported. Chat Completions and Responses are distinct model classes. Client retries are separate from agent retries. | Use an explicit transport class; disable hidden SDK retries when enforcing the application budget. Actual tool support remains per configured model/endpoint. |
| Pydantic AI on-demand capabilities | https://pydantic.dev/docs/ai/capabilities/on-demand/ | Official page retrieved; this pass did not qualify a concrete installed on-demand API surface. | Do not infer SCS semantics or installed SDK compatibility from documentation presence. Explicit search/describe/invoke tools remain a bounded implementation choice. |
| DBOS persistence | https://docs.dbos.dev/python/programming-guide | Default system database is SQLite; documentation recommends PostgreSQL for production. Workflows checkpoint step state. | Native/remote PostgreSQL is compatible with avoiding mandatory Docker. SECMA business-ledger atomicity still needs S02 tests. |
| DBOS communication | https://docs.dbos.dev/python/tutorials/workflow-communication | Send/receive supports workflow messages; receive has timeout and optional suspend. | Signal semantics can map behind the durable port; do not assume external provider delivery acknowledgement. |
| DBOS recovery, waits and limits | https://docs.dbos.dev/python/tutorials/workflow-tutorial | Sleep persists wake-up time. Normal waits retain resident resources; suspend is identified as Enterprise. Recovery assumes application/database return online. Steps may retry before recorded completion; uncaught workflow errors terminate. | Retain bounded ledger sweeper design. Do not promise zero-RAM waiting, execution while a laptop sleeps, or exactly-once external effects. Validate crash windows and errors against a pinned release. |
| MCP | https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro | Connects AI applications with tools, data and external systems. | Tool discovery/invocation transport is not an outcome-assurance contract. |
| A2A | https://a2a-protocol.org/latest/ | Describes communication between opaque agent applications and explicitly distinguishes agent-to-agent interaction from MCP tools/data. | Use as an optional agent adapter; do not substitute agent status for SECMA commitment/evidence ownership. |
| Agent Skills | https://agentskills.io/home | Skill folders contain metadata/instructions and may bundle scripts/resources; progressive loading is documented. | Procedural content does not itself grant authority, install trusted code or prove capability outcome. |

The protocol/SCS separation above is an architectural inference from the sources, consistent with the package's own SCS contract. None of these pages establishes SECMA functionality.

## Remaining qualification gates

- S00: pinned Pydantic AI/OpenAI transport packaging and offline adapter tests; authorized real model probe and blind tool-call trajectories. SDK importability is insufficient.
- S02: pin DBOS and database driver; review exact version's license/enterprise requirements; measure actual PostgreSQL crash/retry/transaction boundaries and resource behavior. The official documentation supports the design caveats but does not demonstrate this application's behavior.
- S04/S07: per-provider credentials, endpoint allowlists, proxy/CA, tenant semantics, supported OS and actual feature smoke. Corporate Genplat and Hermes/Tamanduá/Opai lack supplied canonical endpoint/contracts and remain NOT_QUALIFIED.
- No asserted provider region, price, commercial entitlement or native platform support follows from this review. Operator attestations and measured features must stay separate.
- URL inventory below is complete for the two named registers, not a claim that all linked websites or their infinitely expanding outbound references were audited. Optional future providers were deliberately not installed or executed.

## URL inventory

`DOC_REVIEWED` means only the specific facts above were inspected. `NOT_QUALIFIED` includes deferred/unvisited references and is not a failed service check.

| URL | Status |
|---|---|
| https://a2a-protocol.org/ | DOC_REVIEWED |
| https://agentskills.io/ | DOC_REVIEWED |
| https://ai.google.dev/gemini-api/docs | NOT_QUALIFIED |
| https://ai.pydantic.dev/evals/ | NOT_QUALIFIED |
| https://developers.openai.com/api/ | NOT_QUALIFIED |
| https://developers.openai.com/api/docs/guides/agents-api/overview | NOT_QUALIFIED |
| https://developers.openai.com/api/docs/guides/agents/sdk | NOT_QUALIFIED |
| https://docs.dbos.dev/python/integrating-dbos | NOT_QUALIFIED |
| https://docs.dbos.dev/python/programming-guide | DOC_REVIEWED |
| https://docs.dbos.dev/python/reference/queues | NOT_QUALIFIED |
| https://docs.dbos.dev/python/tutorials/workflow-communication | DOC_REVIEWED |
| https://docs.dbos.dev/python/tutorials/workflow-tutorial | DOC_REVIEWED |
| https://docs.langchain.com/oss/python/langgraph/interrupts | NOT_QUALIFIED |
| https://docs.temporal.io/ | NOT_QUALIFIED |
| https://docs.x.ai/ | NOT_QUALIFIED |
| https://dspy.ai/ | NOT_QUALIFIED |
| https://dspy.ai/current/api/optimizers/MIPROv2/ | NOT_QUALIFIED |
| https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/interrupts.mdx | NOT_QUALIFIED |
| https://github.com/pytransitions/transitions | NOT_QUALIFIED |
| https://json-schema.org/ | NOT_QUALIFIED |
| https://learn.chatgpt.com/docs/app-server | NOT_QUALIFIED |
| https://learn.chatgpt.com/docs/codex-sdk | NOT_QUALIFIED |
| https://modelcontextprotocol.io/ | DOC_REVIEWED |
| https://openrouter.ai/blog/tutorials/tool-calling/ | NOT_QUALIFIED |
| https://openrouter.ai/docs/ | NOT_QUALIFIED |
| https://opentelemetry.io/ | NOT_QUALIFIED |
| https://platform.claude.com/docs/en/agent-sdk/overview | NOT_QUALIFIED |
| https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner | NOT_QUALIFIED |
| https://platform.claude.com/docs/en/api | NOT_QUALIFIED |
| https://pydantic.dev/docs/ai/capabilities/on-demand/ | DOC_REVIEWED |
| https://pydantic.dev/docs/ai/capabilities/overview/ | NOT_QUALIFIED |
| https://www.postgresql.org/docs/ | NOT_QUALIFIED |
