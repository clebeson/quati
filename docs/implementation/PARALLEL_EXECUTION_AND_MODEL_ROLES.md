# Parallel execution and model roles

Normative for implementation of every slice. It complements `AGENTS.md`, `docs/governance/DELIVERY_GOVERNANCE.md` and `docs/testing/TEST_ENGINEERING_STANDARD.md`.

## 1. Language

Every internal artifact is written in English: code, identifiers, comments, tests, fixtures, prompts, commit and PR text, reports, evidence, ledger entries and agent-to-agent messages. The only exceptions are (a) content the project owner explicitly asks for in another language, and (b) product output to end users and test fixtures that exercise multilingual behavior, which use the language under test. An agent that receives instructions in another language still writes its artifacts in English.

## 2. Roles

| Role | Model class | Does | Does not |
|---|---|---|---|
| Root coordinator | Largest available | Selects the task from the DAG, writes briefs, integrates results, decides gate status, writes canonical state, `docs/governance/LOG.md`, `memory/` and seals | Delegate canonical writes |
| Designer / test author | Larger model | Resolves specification questions, designs interfaces inside the work package, writes tests, fixtures, fakes and eval graders first | Mark its own work accepted |
| Implementer | Smaller model for simple tasks; larger model for kernel or ambiguous tasks | Makes the failing tests pass inside the task's owned paths with the smallest change | Edit tests, thresholds, contracts or files outside owned paths |
| Test runner | Smaller model | Runs suites, coverage and validators; records evidence; reports exact counts and output | Change tests or interpret a failure as acceptable |
| Independent reviewer | Larger model with fresh context (not the author) | Checks omissions, unrequested scope, test discrimination and one new adversarial negative | Fix what it reviews in the same pass |

**Simple task (smaller model):** a single module or file set, a complete test-oracle row for every behavior, no change to a contract, port or schema, and no protected-kernel invariant in play. Examples: implementing a pure function against written tests, adding a schema-validated adapter method, wiring a CLI flag, running suites, regenerating derived artifacts, mechanical renames.

**Not simple (larger model):** anything touching identity or tenant, authorization, the commitment reducer and guards, the ledger transaction or outbox, evidence integrity, audit, behavior-policy compilation; anything where the specification is silent or contradictory; all test design; all failure diagnosis beyond an obvious local fix.

When a smaller model is unsure whether its task is still simple, it stops and reports rather than guessing. Escalation is cheap; a wrong kernel change is not.

## 3. Parallel work

Work runs in parallel whenever tasks are independent. Rules:

1. **Disjoint ownership.** Every parallel task has an explicit list of owned paths from its work package. Two tasks running at the same time never share an owned path. A needed change outside owned paths is reported to the root coordinator, not made.
2. **DAG order.** Only tasks whose `depends_on` are accepted may start. Work stays inside the earliest slice whose gate is not `PASS`; parallelism is within a slice, not across failed gates.
3. **Single writer.** Only the root coordinator writes `docs/implementation/implementation_state.json` (revision compare-and-set through `scripts/checkpoint_execution.py`), `docs/governance/LOG.md`, `memory/`, seals, and generated artifacts (`docs/traceability/*`, `QUATI_CONSOLIDATED_SPEC_V8_EN.md`, `PACKAGE_MANIFEST.json`, packaged assets).
4. **Typical fan-out for one work package.** One test author writes the tests for the package (or several authors on disjoint test files); after red is recorded, implementers work in parallel on disjoint source paths; a test runner executes the suites; an independent reviewer audits; the root coordinator integrates and checkpoints.
5. **Briefs.** Each delegated task receives: task ID, requirement IDs, owned paths, files to read, the exact tests to satisfy or commands to run, what is out of scope, and the report format. A brief never asks an agent to confirm a conclusion.
6. **Reports.** Each agent reports files changed, commands run with exact results, anything skipped, and anything it could not decide. Claims are verified by the test runner or reviewer before integration; an agent's statement is never evidence.
7. **Conflicts.** If two results conflict, the root coordinator resolves against the specification, records the decision, and reruns the affected tests.

## 4. Order of work inside a task (SDD → TDD → EDD)

1. Read the work package, the PRDs' `## Normative detail` and `## Test oracles`, and the named contracts.
2. Test author writes the tests; test runner records the failing run (red).
3. Implementer makes them pass in owned paths; test runner records the passing run and coverage (green).
4. Independent reviewer audits conformity and quality and adds one adversarial negative.
5. Root coordinator records evidence, updates canonical state by compare-and-set, and appends to `docs/governance/LOG.md`.

## 5. Things no role may do

- Claim `PASS` from a mock, a schema check or a verbal statement; replace a real-provider proof with a fake.
- Lower a threshold, delete or skip a failing test, or widen a coverage exclusion to get a green run.
- Access production, perform external writes, merge, release or deploy without separate explicit authorization.
- Put credentials in logs, patches, evidence or prompts; credentials are used only through secret references.
