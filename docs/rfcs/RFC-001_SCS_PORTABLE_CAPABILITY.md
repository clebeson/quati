# RFC-001 — Portable SCS Capabilities

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

**Decision:** Proposed. **Owners:** M14/M15. **Scope:** every outcome capability.

An SCS capability is an outcome-oriented contract, not a prompt, skill, tool, graph or agent. The public manifest requires a namespaced ID, semantic version, human-understandable positive/negative intent examples, typed input/output schemas, desired result, evidence requirements, side-effect classification, approval/policy scopes, compatibility requirements and assurance state. Definition, implementation binding and independent evidence of competence are separate artifacts. Manifests are plain JSON/YAML and may be indexed; on-demand selection may be mapped onto Pydantic AI deferred capabilities, a direct tool call or any other compatible runtime.

### Resolution
`search(query, actor, context)` returns only authorized short descriptions; `describe(id)` supplies a bounded specification; `invoke(id, args, commitment_ref)` creates a job after policy; `status(ref)` returns progress/outcome. A resolver checks `ENABLED`, compatible schemas, operational availability, assurance tier, tenant policy, cost and relevant feature flags. Several bindings may exist per definition; no prompt change is required when a binding is replaced. Direct invocation by code is allowed for deterministic orchestration, but does not prove LLM discovery.

### Assurance and lifecycle
`DRAFT → VALIDATED → STAGED → ENABLED`; `DEPRECATED/DISABLED` never silently destroy active jobs. C0 syntax only, C1 contract, C2 deterministic integration, C3 blind real-model selection, C4 authorized external provider, C5 operational assurance. Publishing never upgrades assurance automatically. A model-generated capability begins at DRAFT and must not request a higher privilege than trusted operator policy.

### Required negative cases
Duplicate ID with incompatible major version; package with harmful write effects but read-only metadata; disabled binding referenced by a model; two similar capabilities with different costs; no executor; missing outcome evidence; untrusted prompt-injection inside the description. A capability MUST not be reported available just because `capability.json` validates.

## Amendment v8.1 (RFC-015)

The rules in RFC-015 replace the overlapping parts of this RFC:

- **Manifest.** `contracts/scs-capability.schema.json` is now `scs/1.1`, a thin sidecar next to an optional Agent Skills `SKILL.md`. The manifest no longer contains `lifecycle` or `assurance`. Both are registry-owned (`contracts/capability-registry-record.schema.json`), because a package must not vouch for itself.
- **Lifecycle.** The single lifecycle casing is upper case: DRAFT, VALIDATED, STAGED, ENABLED, DEPRECATED, DISABLED. ENABLED requires a HUMAN approval (RFC-014) and assurance ≥ C2.
- **Assurance mapping.** Binding `verification` maps onto C0–C5 as defined in RFC-015 §5.
- **Integrity.** Integrity is the directory sha256 in `capabilities.lock`, recomputed at every load. A mismatch refuses the load. Signatures (Sigstore or similar) are a deferred optional field.
- **"Compatibility requirements".** This is the optional `compatibility` object.
- **"Evidence requirements".** These are `outcomes.criteria` plus `outcome_verification`, which is required for write and dangerous effects together with `destinations`.
- **Incompatible major version.** The negative case "duplicate ID with incompatible major version" is now detectable, because `version` is strict semver and `id` is namespaced.
