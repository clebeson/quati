# AGENTS.md — Normative coding-agent instructions for SECMA

These instructions apply to Codex Work and any other implementation agent. Read `README.md` and the **specific** slice handoff before modifying source. Every artifact, prompt, test fixture, report and code comment authored for the project MUST be in English; the SECMA product must answer end users in their selected or detected language.

## Current execution authorization

Current mode is SPECIFICATION_ONLY, as recorded in canonical state. Do not implement
new runtime features until the user explicitly authorizes implementation. Audit,
specification corrections, offline specification validators and test definitions
are permitted. Retained candidate source is not normative or approved.

Before future implementation, read `IMPLEMENTATION_READY_INDEX.md`, project layout,
`DELIVERY_GOVERNANCE.md`, `PERSISTENT_STATE_AND_MEMORY.md`, the work-package DAG and
its selected handoff. English is mandatory for every authored internal artifact.

## Scope discipline and authority
1. Work on only the earliest slice whose gate is not `PASS`; do not skip a failed gate or implement unrelated downstream modules because their PRDs exist.
2. Build the simplest cohesive Python implementation with clear internal package boundaries; **do not create one microservice per PRD**.
3. Domain code MUST NOT import DBOS, Pydantic AI, specific model SDKs, MCP transports, A2A or database adapters. Reference interfaces and the local policy engine are permitted.
4. The protected kernel invariants are: identity/tenant, authorization before effects, durable commitment, transactional or reconcilable outbox, evidence integrity, audit trace, and versioned behavior policy. Do not allow operators, prompts or self-improvement agents to disable them.
5. An agent may propose prompt, skill, model routing and statechart changes; only the compiler/validator can accept them, and release promotion requires applicable tests and authorized approval.
6. No live external writes, production access, merge, release or deployment without explicit authorization. Use user-approved credentials only through secret references, never in logs or patches.
7. Do not claim a mock, schema check, deterministic mock LLM or simulated webhook is proof of a real provider integration. Report `BLOCKED`/`NOT_VERIFIED_EXTERNAL` truthfully.
8. Avoid unnecessary clarification: if only a key, scope or authorization is missing, request that single blocking dependency; use safe local fixtures for other work.

## Workflow: SDD → TDD → EDD
- **Specification Driven:** select FR/AT/RT IDs; define boundaries and what is out of scope; resolve contradictions before code. New requirements go into a PRD with ADR/RFC when architecture changes.
- **Test Driven:** design discriminating behavior tests first; use small deterministic unit tests for guards and reducers, integration tests for DBOS/ledger and blind real-LLM tests for dynamic capability choice. No self-fulfilling mocks.
- **Evidence Driven:** store immutable, redacted test result, scenario, exact model and config identity, trace, exceptions, resource measurements when applicable and all unsatisfied gates. An implementation cannot declare itself independently audited.

## Code organization and defaults
- `src/secma/domain/` for typed core business concepts and pure reducers.
- `src/secma/application/` for use cases and ports.
- `src/secma/adapters/` for DBOS, Postgres, LLMs, harnesses, channels, skills and knowledge providers.
- `src/secma/cli/` for Typer/argparse presentation only.
- `src/secma/behavior/` for compilation of prompts, context envelopes and declarative statecharts.
- `tests/unit/`, `tests/integration/`, `tests/evals/`, `tests/external/`, `tests/chaos/`; no external test can silently become a local unit test.
- `evidence/` sanitized proofs; `docs/governance/` records decisions, bugs, debt, exceptions and lessons learned.

## PR and state updates
Each PR MUST state: slice, FR/AT/RT IDs, code paths, tests run/not run, evidence hashes, model/provider/OS versions, safety impact, behavior changes, debt and rollback path. Update `docs/implementation/implementation_state.json` atomically; check its revision before writing. Keep statuses `NOT_STARTED`, `IN_PROGRESS`, `PASS`, `FAIL`, `BLOCKED` and never infer `PASS` from an assistant's verbal claim.

## Red-team requirement
Before a slice gate, simulate an adversarial attempt from an untrusted document, tool result or sender to change the policy, select the wrong capability, skip outcome verification or fabricate completion. Verify a code-level check rejects it. Do not repeat the same attack across every module when a shared enforcement point already proves the behavior.

## Cost and feedback
Use a small/tool-capable provider for benign routing and responses when it meets the published model competence profile. Escalate only for higher-risk/uncertain tasks; log tokens, errors and cost. CLI should show concise receipts and progress while the formal deliverable can be detailed.
