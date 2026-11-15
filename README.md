# SECMA — Executive Cognitive Secretary and Portable Capabilities, v8 (English-only)

**Status:** AUTHORITATIVE DESIGN PACKAGE — NOT WORKING SOFTWARE. **Target:** Codex Work, CLI-only implementation, local-first with optional corporate deployment. **Supersedes:** all earlier SECMA design, PRD, TRD, SCS and roadmap packages to the extent of conflicts. Earlier packages are research input, not an executable instruction source.

## The product in one paragraph
SECMA is a professional executive secretary that takes responsibility for work, not merely a chat interface to other agents. It interprets requests, begins safe work, asks worthwhile questions, manages concurrent commitments, communicates at the right moment, restores old context, evaluates outcomes and hands off specialist execution through interchangeable adapters. It must remain useful with smaller, inexpensive models; stronger models are optional for more demanding decisions.

## Start here (single normative sequence)
1. `AGENTS.md` — instructions for any coding agent, including Codex Work.
2. `docs/vision/PRODUCT_PRD.md` — what to build and what must **not** be built.
3. `docs/vision/MODULE_MAP.md` and `docs/prds/M01.md` through `M31.md` — 31 bounded responsibilities.
4. `docs/trd/TECHNICAL_REFERENCE.md` — architecture, technology, portability and interfaces.
5. `docs/rfcs/RFC-010_BEHAVIOR_COMPILER.md`, `RFC-011_STATECHART_MODEL.md`, `RFC-012_SMALL_MODEL_CONTEXT.md` — how agent behavior is produced from configuration.
6. `docs/implementation/ROADMAP.md`, `docs/implementation/SLICES/` and `docs/implementation/implementation_state.json` — mandatory delivery order and resume state.
7. `docs/testing/TEST_STRATEGY.md`, `docs/testing/RISK_COVERAGE_REPORT.md` and `docs/testing/LIVE_MODEL_BENCHMARK.md` — test obligations and proof levels.
8. `docs/redteam/OVERALL_RED_TEAM.md` — cross-cutting blockers and individual module attack sheets.
9. `docs/implementation/CODEX_WORK_MASTER.md` — first handoff prompt.

## Critical constraints
- **English-only** for all prompts, specs, code comments, files, internal descriptions and structured events. User-facing response language follows the requesting user's language unless an explicit override is requested.
- **No SECMA GUI or web application** in this release. CLI and worker only. An upstream provider API does not make SECMA a web app.
- **DBOS initially**, behind a minimal application-level durable-execution port; a Temporal adapter is not implemented in phase 1.
- **Never equate configuration with implementation** or a passing static schema check with live intelligence, durable execution or provider validation.
- **First executable milestone must prove a real LLM performs spontaneous capability discovery** from a natural-language request. Do not hardcode the target capability in the prompt.
- **Always produce redacted evidence:** requirement ID, test source, version, observed result, timestamp and proof tier.
- **Do not require Docker on personal machines.** Optional integration-test containers are permitted but native/remote alternatives must exist.
- **Do not use a prompt to grant privileges, bypass approval or rewrite kernel invariants.**

## Package contents
- 31 individual PRDs and 31 module red-team sheets
- Product PRD, technical reference, model/provider matrix, diagrams and versioned decisions
- 12 RFCs including capability interoperability, prompt compiler, statechart compiler and model competence calibration
- 12 ADRs and a deployment/packaging RFC
- JSON schemas, declarative YAML examples, test fixtures and an *offline specification validator/reference statechart renderer*
- Risk-based coverage report and requirement-to-proof registry
- Codex Work instructions, short vertical slices, resumption state, defect and technical-debt rules

## Evidence statement
Any validation bundled here is **L0 specification validation only**. A real SECMA model runtime has not been implemented in this package. Live LLM, database recovery and provider integration gates must remain `NOT_RUN` until executed by the implementing agent with authorized resources.
