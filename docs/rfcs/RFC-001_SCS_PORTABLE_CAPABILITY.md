# RFC-001 — Portable SCS Capabilities
**Decision:** Proposed. **Owners:** M14/M15. **Scope:** every outcome capability.

An SCS capability is an outcome-oriented contract, not a prompt, skill, tool, graph or agent. The public manifest requires a namespaced ID, semantic version, human-understandable positive/negative intent examples, typed input/output schemas, desired result, evidence requirements, side-effect classification, approval/policy scopes, compatibility requirements and assurance state. Definition, implementation binding and independent evidence of competence are separate artifacts. Manifests are plain JSON/YAML and may be indexed; on-demand selection may be mapped onto Pydantic AI deferred capabilities, a direct tool call or any other compatible runtime.

### Resolution
`search(query, actor, context)` returns only authorized short descriptions; `describe(id)` supplies a bounded specification; `invoke(id, args, commitment_ref)` creates a job after policy; `status(ref)` returns progress/outcome. A resolver checks `ENABLED`, compatible schemas, operational availability, assurance tier, tenant policy, cost and relevant feature flags. Several bindings may exist per definition; no prompt change is required when a binding is replaced. Direct invocation by code is allowed for deterministic orchestration, but does not prove LLM discovery.

### Assurance and lifecycle
`DRAFT → VALIDATED → STAGED → ENABLED`; `DEPRECATED/DISABLED` never silently destroy active jobs. C0 syntax only, C1 contract, C2 deterministic integration, C3 blind real-model selection, C4 authorized external provider, C5 operational assurance. Publishing never upgrades assurance automatically. A model-generated capability begins at DRAFT and must not request a higher privilege than trusted operator policy.

### Required negative cases
Duplicate ID with incompatible major version; package with harmful write effects but read-only metadata; disabled binding referenced by a model; two similar capabilities with different costs; no executor; missing outcome evidence; untrusted prompt-injection inside the description. A capability MUST not be reported available just because `capability.json` validates.
