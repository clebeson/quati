# RFC-004 — Model, Harness, Channel and Brain Provider Contracts

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

**Decision:** typed ports + per-feature probes, without forced lowest-common-denominator behavior.

`ModelProvider`: chat, tools, structured output, streaming, usage, region, auth, cost and semantic competence. `HarnessProvider`: discover, health, invoke, status, cancel, optional resume/stream, artifact refs and specific sandbox/approval guarantees. `BrainProvider`: list, search, read, optional write/watch/version, ACL, source IDs and freshness. `ChannelProvider`: verify inbound origin, map sender, send, thread reference, delivery receipt, cancellation if supported.

Providers MUST describe actual support as capability flags and report `UNSUPPORTED`, `NOT_CONFIGURED`, `UNAUTHORIZED`, `TEMPORARILY_UNAVAILABLE` or `NOT_VERIFIED_EXTERNAL`, not fake success. A new specialized Excel chart agent binds a manifest to a harness executor, declares input/output and tests editability; disabling it must not break greetings or the secretary's committed-task ledger.

Transport options include MCP (tools), A2A (agent tasks), local CLI subprocess with timeouts, SDK APIs, filesystem/Git repositories and corporate proxies. Vendor credentials are not interchangeable. Every `ModelProvider` is a subclass of the single abstract `Provider` base class selected by a registered `transport` name (M17); the base class owns configuration checks, budgets, retries, output validation and the probe, so a new vendor implements only the wire call. A vendor command-line tool used as a model transport authenticates itself; Quati never reads its sign-in files and runs it with its own tools disabled. OpenAI-compatible gateways vary by tool and JSON support; probe the exact configured model. Do not assume a UI-centric Work product exposes a supported local agent API. If available, Codex SDK/app-server and managed Agents API are separate integrations.

## Observed versus attested metadata

Feature reports distinguish observed protocol behavior, configuration, provider/operator attestation, and UNKNOWN. Network success does not prove data residency, retention, licensing or pricing. Preserve source/version/as-of information for attested metadata and refuse unsupported claims.

## Optional trace export (v8.1, S02 or later)

An optional exporter may map Quati trace events to OpenTelemetry GenAI semantic-convention names.

- The convention version is pinned, and its Development stability status is recorded.
- The exporter is off by default.
- It never exports content or arguments, only ids, timings, token counts and outcome codes, unless the operator explicitly enables content export for a LOCAL deployment.
- The internal audit trace stays authoritative. The export is a copy.
