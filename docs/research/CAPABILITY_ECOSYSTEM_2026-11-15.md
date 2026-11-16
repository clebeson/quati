# Capability ecosystem research — 2026-11-15

Status: WORKING NOTES (inputs to RFC-015). Research was done by parallel subagents and checked by the lead. Claims marked UNVERIFIED could not be confirmed from a primary source.

## 1. whitebeardit/agents-team-crafter ("TeamAgents: AI Team Crafter")

**What it is.** A multi-tenant SaaS:
- Stack: Next.js frontend, Fastify + MongoDB backend, OpenAI Agents SDK.
- Purpose: build and govern teams of agents per workspace. A team has one coordinator and several specialists. It connects to channels (Slack, Telegram, WhatsApp), a "Second Brain" knowledge vault, run/audit records, and templates.
- Not a file-based capability format. It has no SKILL.md files and no manifest files. Capabilities are DB records and TypeScript presets.
- License: Whitebeard **Non-Commercial**. We may reuse ideas, not code.

**Concepts worth borrowing.** All paths are in the upstream repo.

| Concept | Where | SECMA use |
|---|---|---|
| Binding `kind` values: `builtin_ref`, `http_webhook`, `mcp_ref`, `internal_action` | `backend/src/modules/tool-definitions/infra/workspace-tool-definition.model.ts` | Confirms that SCS bindings should be keyed by adapter type |
| `riskLevel`, `requiresConfirmation`, `readAfterWriteRequired` | `backend/src/modules/business-tools/application/business-action-presets.ts` | `readAfterWriteRequired` is the same idea as SECMA outcome verification; risk maps to `effects` |
| `domain.{boundaries, exclusions, exampleUserPhrases, inputDescription, outputDescription}` | `backend/src/modules/agents/application/agent-config.schemas.ts` | Good routing metadata. Adopt as `when_to_use` / `when_not_to_use` / `examples` |
| Domain packs with `dependsOnDomainIds`, plus a resolver for the dependency closure | `business-tools/application/domain-capability-registry.ts` | Precedent for packs and dependency closure |
| Stable dotted ids (`crm.search_customer`). Import normalises legacy payloads | `docs/agent-export-import-runtime-contract.md` | Stable ids and versioned import normalisation |
| Export sanitisation and credential slots | `templates/application/sanitize-template-export.ts`, `template-credential-slots.ts` | Portable packages carry `secret_ref` slots and never values |
| "Tool JSON Schema must always have `properties`" (an OpenAI 400 error) | `.cursor/rules/openai-tool-json-schema.mdc` | Add as a manifest lint rule |
| Only the coordinator is a top-level agent; specialists are exposed as tools | `docs/HANDOFF_DSL.md` | Same shape as SECMA's secretary-as-orchestrator |

**Weaknesses SECMA must not copy:**
- Risk is an ordinal flag. Confirmation is declared but enforced mainly in the UI or prompt (INFERRED from grep).
- The deterministic handoff policy engine was removed, so delegation is decided by the LLM.
- No provenance, signatures or hashes. Versions are bare strings with no pinning.
- No LLM evals for capability selection.
- `config: Mixed` is untyped. MCP tools are stored as name and description only.
- Secrets are stripped by a key-name regex.
- Vendor lock-in: OpenAI only.

## 2. Anthropic / Claude capability formats

Sources:
- https://code.claude.com/docs/en/skills
- https://agentskills.io/specification
- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/plugins/marketplace-reference
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/permissions

**Agent Skills (open standard, agentskills.io).**
- Layout: `skill-name/SKILL.md` plus optional `scripts/`, `references/` and `assets/`.
- Front matter:
  - `name`: 1–64 chars, lowercase with hyphens, and equal to the directory name.
  - `description`: 1–1024 chars.
  - Optional: `license`, `compatibility` (≤500 chars), `metadata` (a string map) and `allowed-tools` (experimental).
- Progressive disclosure:
  - Only name and description are always in context.
  - The body loads when the skill is invoked.
  - Bundled files load on demand.
  - Scripts are executed, not loaded.
- Claude Code adds `when_to_use`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `context: fork` and `hooks`.
- Adoption by other tools (Codex, Gemini CLI, Copilot, Cursor, …) is UNVERIFIED from a primary source. The lead is checking it in round 2.

**Plugins and marketplaces.**
- `.claude-plugin/plugin.json` requires only `name`. It may also list `version`, `skills`, `commands`, `agents`, `hooks`, `mcpServers`, `userConfig` and `dependencies`.
- `marketplace.json` requires `name`, `owner` and `plugins[]`. A plugin `source` can be a relative path, github (`repo`, `ref`, `sha`), url, npm or archive (sha256).
- A sha pin blocks updates. `claude plugin validate` checks a plugin.

**Subagents.**
- Format: a Markdown file with front matter `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills` and `mcpServers`.
- Routing matches the request against `description`.

**MCP.**
- A tool has `name`, `title`, `description`, `inputSchema`, `outputSchema` and `annotations`.
- Annotations are `readOnlyHint`, `destructiveHint` (default true), `idempotentHint` and `openWorldHint`.
- **Clients must treat annotations as untrusted** unless the server is trusted.
- HTTP auth is OAuth 2.1 with PKCE, RFC 9728 resource metadata and the RFC 8707 `resource` indicator. STDIO takes credentials from the environment.
- Registry `server.json` has a reverse-DNS `name`, a `version`, `remotes[]` and `packages[]` (registryType, identifier, version, transport).

**Hooks and permissions.**
- Permission rule order is deny → ask → allow. An allow never overrides a deny.
- A PreToolUse hook can block a call (exit 2), or return `permissionDecision` with `allow`, `deny`, `ask` or `defer`.
- The enforcement point is outside the model.

## 3. Other ecosystems

Sources: https://a2a-protocol.org/latest/specification/, https://learn.chatgpt.com/docs/build-skills, https://geminicli.com/docs/extensions/reference/, https://adk.dev/agents/config/, https://pydantic.dev/docs/ai/tools-toolsets/toolsets/, https://modelcontextprotocol.io/registry/about, https://packaging.python.org/en/latest/specifications/entry-points/.

| System | Format | Discovery | Versioning | Side-effect declaration | Auth |
|---|---|---|---|---|---|
| A2A Agent Card | `agent-card.json`. Fields include `skills[]` (`id`, `name`, `description`, `tags`, `examples`, `securityRequirements`), `capabilities`, `securitySchemes` and `signatures` | `/.well-known/agent-card.json`, registries | card `version` | **none** | APIKey/HTTP/OAuth2/OIDC/mTLS |
| Codex skills | `SKILL.md` (`name`, `description`) plus optional `agents/openai.yaml` (`policy.allow_implicit_invocation`, `dependencies.tools`) | `.agents/skills` walk-up, `$HOME/.agents/skills` | none | implicit-invocation flag only | via MCP deps |
| AGENTS.md | plain Markdown, concatenated from root to cwd | directory walk | none | none | none |
| Gemini CLI extension | `gemini-extension.json` (`name`, `version`, `mcpServers`, `excludeTools`, `settings[].sensitive`) | `extensions install <git>` | version field, `--ref` | `excludeTools` only | keychain settings |
| OpenAI Agents SDK / Pydantic AI | code decorators; `needs_approval`; `ApprovalRequiredToolset` → `DeferredToolRequests` | code | code | approval is enforced in code, not declared | code |
| LangChain / CrewAI / Semantic Kernel | `@tool`, `agents/*.jsonc`, `@kernel_function` | code | none | **prose only** | code |
| MCP Registry | `server.json` (`name` reverse-DNS, `version`, `packages[]` with `environmentVariables[].isSecret`, `remotes[]`) | REST registry, metadata only | version | MCP annotations (untrusted) | namespace verification |
| Python entry points | `entry_points` group | `importlib.metadata` | dist version | none | none |
| OCI agent artifacts | no ratified standard | — | — | — | — |

**Key finding.** No surveyed standard declares side effects structurally and enforceably. The closest are MCP annotations, which are explicitly untrusted, and the OpenAI and Pydantic AI approval wrappers, which are code rather than metadata. SECMA's effect, destination and outcome-verification sidecar therefore fills a real gap. It is not a duplicate format.

**Other notes:**
- The Gemini CLI page says it was replaced by Antigravity CLI for some tiers on 2026-06-18. This is relevant only as an import target, so it is low priority.
- Smithery docs were unreachable (UNVERIFIED).

## 4. Lead judgement (preliminary)

1. **Do not invent an authoring format.** SKILL.md (Agent Skills) is the authoring unit for instruction-only and script-backed capabilities. MCP `tools/list` is the import unit for tool servers. The A2A Agent Card is the import and export unit for remote agents.
2. **The SCS manifest becomes a thin sidecar, not a replacement.** It holds what none of those formats can express:
   - *enforced* effects (none/read/write/dangerous)
   - destinations
   - data-class ceiling
   - outcome verification (cf. `readAfterWriteRequired`)
   - assurance and lifecycle, owned by the registry
   - pinned source digest
   - an eval suite
3. **Vendor hints are untrusted.** MCP annotations and `allowed-tools` are imported as *hints*. Only the registry's assigned effect class, after review, is enforced. When nothing is known, the default is `dangerous`, mirroring `destructiveHint` default true.
4. **Packaging and provenance** reuse the marketplace idea: a git or archive source with a sha256 pin, plus a lockfile. Credentials travel only as `secret_ref` slots.
