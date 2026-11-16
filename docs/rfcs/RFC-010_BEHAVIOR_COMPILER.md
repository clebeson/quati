# RFC-010 — Behavior Package Compiler: Who Generates Prompts and Behavioral Programs?

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

**Decision:** The trusted Quati runtime owns prompt compilation and behavior activation; installation operators author policy; autonomous agents may generate **proposals** only. Model-specific runtime prompt instructions are never the authoritative security policy.

## Input sources and precedence
1. Read-only kernel invariants: authorization, commitment integrity, delivery truthfulness, evidence and audit.
2. Validated installation/corporate policy, security allowlists and data residency.
3. Versioned role/interaction/execution profile (e.g., executive secretary, researcher, concise analyst).
4. Enabled SCS contract summaries, outcome criteria, on-demand skill/tool summaries.
5. Task-specific context envelope with current user request, previous turns, progress, preferences and evidence refs.
6. Low-trust external documents/tools, explicitly marked as quoted data rather than instructions.

The compiler loads only needed parts and returns `PromptBuildReceipt{behavior_version, statechart_hash, prompt_hash, sections, token_budget, required_facts, model_profile_ref, source_versions}`. Cached stable prefix is separated from volatile task context; if token pressure occurs, untrusted retrieved context is trimmed first, not security/ownership facts. Rendering MAY use Jinja2 for immutable templates but arbitrary `eval`/Python execution in YAML is forbidden.

## Configuration lifecycle
`quati behavior propose` can accept a human-authored YAML patch or an agent-generated draft; `validate` checks schema/references/policies; `render` generates English prompt preview and statechart; `simulate` tests representative conversation/event traces; `eval` uses actual LLM holdouts if model behavior changes; `promote` requires approved policy; `rollback` restores previous content-addressed version. Deterministic compilation is idempotent for identical inputs. Slice assignment on the public CLI (M30 § Public interface): `validate` and `render` are delivered in S00 and take the package file (`quati behavior validate|render PACKAGE [--root DIR] [--json]`); `propose`, `simulate`, `diff`, `promote` and `rollback` are delivered with ProfilePort in S03 and return `UNSUPPORTED` before then; `eval` follows the evaluation harness of its own slice. System owner may configure style and workflow selection but cannot disable the trusted authorization ledger.

## For weaker models
Produce explicit responsibilities, decision enum, examples including when **not** to call tools, single typed output target and a maximum of 2–5 candidate capabilities, retrieving more only if needed. Avoid a monolithic list of 79 capabilities, hidden unstated knowledge, contradictory instructions and prompt-only state transition checks. When tool calling is unreliable, choose a calibrated supported provider or ask a limited clarifying question instead of autonomous risk-taking.

## Rejection rules
A prompt builder MUST reject a profile that requests nonexistent capabilities, unknown guard names, privilege elevation, conflicting output-language priorities, invalid state references, absence of audit, unbounded retries or secret interpolation. User-facing responses may be localized after the English internal decision; documentation/internal manifests remain English.
