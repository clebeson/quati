# RFC-004 — Model, Harness, Channel and Brain Provider Contracts
**Decision:** typed ports + per-feature probes, without forced lowest-common-denominator behavior.

`ModelProvider`: chat, tools, structured output, streaming, usage, region, auth, cost and semantic competence. `HarnessProvider`: discover, health, invoke, status, cancel, optional resume/stream, artifact refs and specific sandbox/approval guarantees. `BrainProvider`: list, search, read, optional write/watch/version, ACL, source IDs and freshness. `ChannelProvider`: verify inbound origin, map sender, send, thread reference, delivery receipt, cancellation if supported.

Providers MUST describe actual support as capability flags and report `UNSUPPORTED`, `NOT_CONFIGURED`, `UNAUTHORIZED`, `TEMPORARILY_UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`, not fake success. A new specialized Excel chart agent binds a manifest to a harness executor, declares input/output and tests editability; disabling it must not break greetings or the secretary's committed-task ledger.

Transport options include MCP (tools), A2A (agent tasks), local CLI subprocess with timeouts, SDK APIs, filesystem/Git repositories and corporate proxies. Vendor credentials are not interchangeable. OpenAI-compatible gateways vary by tool and JSON support; probe the exact configured model. Do not assume a UI-centric Work product exposes a supported local agent API. If available, Codex SDK/app-server and managed Agents API are separate integrations.
