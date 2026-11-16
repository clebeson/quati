# AGENTS.md — Normative coding-agent instructions for Quati

These instructions apply to Codex Work and any other implementation agent. Read `README.md` and the **specific** slice handoff before modifying source. Every artifact, prompt, test fixture, report and code comment authored for the project MUST be in English; the Quati product must answer end users in their selected or detected language.

## Current execution authorization

Current mode is IMPLEMENTATION_AUTHORIZED, following explicit user authorization.
Implement sequentially from S00 using SDD → TDD → EDD, independent conformity and
quality audits before accepting each delivery, and continuous durable checkpoints.
Parallel agents may handle bounded disjoint work; canonical state, policy and ledger
writes remain single-owner. Mocks cannot replace mandatory real-provider proof.
Retained source requires task-specific review and requalification before acceptance.
No production access, external writes, merge, release or deployment is authorized.

Before future implementation, read `IMPLEMENTATION_READY_INDEX.md`, project layout,
`DELIVERY_GOVERNANCE.md`, `PERSISTENT_STATE_AND_MEMORY.md`, the work-package DAG and
its selected handoff. English is mandatory for every authored internal artifact.

## Standing operating rules (binding for every agent)

1. **English only.** Code, comments, tests, fixtures, prompts, reports, evidence, ledger
   entries and agent-to-agent messages are written in English, unless the project owner
   explicitly asks for another language for a specific artifact. Product output to end
   users, and fixtures that exercise multilingual behavior, use the language under test.
2. **Implement in parallel; use smaller models for simple tasks.** Independent tasks inside
   the current slice run in parallel on disjoint owned paths. Simple, fully specified tasks
   go to smaller models; kernel, ambiguous or design work goes to larger models. Roles,
   the definition of "simple" and the single-writer rule are in
   `docs/implementation/PARALLEL_EXECUTION_AND_MODEL_ROLES.md`.
3. **Maximum coverage.** 100% of the slice's requirement IDs have an executed test; code
   coverage thresholds (100% line and branch for `domain/` and `behavior/`, ≥95% overall)
   are gates. See `docs/testing/TEST_ENGINEERING_STANDARD.md`.
4. **Deterministic tests.** Injected clock, seeded IDs, isolated temp stores, named
   crash-injection points, scripted fakes; no sleeps, wall-clock reads, network or
   order dependence in deterministic lanes. Only genuinely model-dependent behavior goes
   to `tests/evals`; real providers go to `tests/external`.
5. **Larger models write tests; smaller models run them.** Test design, test code,
   fixtures and graders are authored by a larger model before implementation. Smaller
   models run suites, coverage and validators and report exact results. A runner never
   edits a test, threshold or skip marker to get a green result.
6. **Authoritative detail.** Each PRD's `## Normative detail` and `## Test oracles`
   sections, `docs/prds/PRD_COMMON.md`, `docs/architecture/GUARD_PREDICATES.md` and the
   JSON contracts are the implementation source of truth. If they disagree, record a
   specification bug in `docs/governance/LOG.md` and fix the specification first.
7. **Terminal first; no UI yet.** Every capability is exercised and accepted through the
   `quati` command line, including the conversational terminal session (`quati chat`,
   M01). No GUI, web UI or full-screen TUI work starts until every slice gate S00–S07 is
   `PASS`, the exhaustive test and correction cycle is complete, and the project owner
   explicitly authorizes it.
8. **Right the first time.** This project has a low tolerance for rework. Do not guess:
   when a specification is silent or contradictory, stop and resolve it in the
   specification. Do not hand over work that has not been run through its tests from the
   public command-line entry path.

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
- **Test Driven:** design discriminating behavior tests first; use small deterministic unit tests for guards and reducers, integration tests for the ledger/worker and blind real-LLM tests for dynamic capability choice. No self-fulfilling mocks.
- **Evidence Driven:** store immutable, redacted test result, scenario, exact model and config identity, trace, exceptions, resource measurements when applicable and all unsatisfied gates. An implementation cannot declare itself independently audited.

## Code organization and defaults
- `src/quati/domain/` for typed core business concepts and pure reducers.
- `src/quati/application/` for use cases and ports.
- `src/quati/adapters/` for ledger backends (SQLite, PostgreSQL), LLMs, harnesses, channels, skills and knowledge providers.
- `src/quati/cli/` for Typer/argparse presentation only.
- `src/quati/behavior/` for compilation of prompts, context envelopes and declarative statecharts.
- `tests/unit/`, `tests/integration/`, `tests/evals/`, `tests/external/`, `tests/chaos/`, `tests/packaging/`; planned test locators always use these real lane directories (never `tests/planned/`); no external test can silently become a local unit test.
- `evidence/` sanitized proofs; `docs/governance/` records decisions, bugs, debt, exceptions and lessons learned.

## PR and state updates
Each PR MUST state: slice, FR/AT/RT IDs, code paths, tests run/not run, evidence hashes, model/provider/OS versions, safety impact, behavior changes, debt and rollback path. Update `docs/implementation/implementation_state.json` atomically; check its revision before writing. Keep statuses `NOT_STARTED`, `IN_PROGRESS`, `PASS`, `FAIL`, `BLOCKED` and never infer `PASS` from an assistant's verbal claim.

## Red-team requirement
Before a slice gate, simulate an adversarial attempt from an untrusted document, tool result or sender to change the policy, select the wrong capability, skip outcome verification or fabricate completion. Verify a code-level check rejects it. Do not repeat the same attack across every module when a shared enforcement point already proves the behavior.

## Cost and feedback
Use a small/tool-capable provider for benign routing and responses when it meets the published model competence profile. Escalate only for higher-risk/uncertain tasks; log tokens, errors and cost. CLI should show concise receipts and progress while the formal deliverable can be detailed.
