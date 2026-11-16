# Implementation master handoff — Quati v8

## Authorization and current position

Implementation is authorized (`AGENTS.md`; canonical state `work_mode: IMPLEMENTATION_AUTHORIZED`; `docs/governance/LOG.md` LOG-0004). No production access, external write, merge, release or deployment is authorized. The active slice and task are whatever `docs/implementation/implementation_state.json` says; never infer them from this file. Source retained from earlier attempts is an unapproved candidate until its owning task requalifies it; non-conforming candidate modules were removed and the missing work is recorded in `docs/governance/LOG.md`.

Your job is to produce working, tested Python code, not more specification. Work only on the earliest slice whose gate is not `PASS`. Do not implement downstream slices or a GUI.

## Read order

`AGENTS.md` → `IMPLEMENTATION_READY_INDEX.md` → `docs/implementation/PARALLEL_EXECUTION_AND_MODEL_ROLES.md` → `docs/testing/TEST_ENGINEERING_STANDARD.md` → the selected task in `docs/implementation/work_packages/Sxx.md` → only the PRDs, RFCs and contracts that task names. In each PRD the `## Normative detail` and `## Test oracles` sections are authoritative; shared rules are in `docs/prds/PRD_COMMON.md`; lifecycle guards are in `docs/architecture/GUARD_PREDICATES.md`.

## Workflow for every task

1. **Check the specification (L0).** From `spec_tools/`: `../.venv/bin/python validate_spec.py` and `../.venv/bin/python validate_readiness.py`. These prove internal coherence of the documents only; they never promote a runtime gate.
2. **SDD.** Select the task's requirement IDs, owned paths and out-of-scope items. If two sources disagree, record a specification bug in `docs/governance/LOG.md` and fix the specification first.
3. **TDD.** A larger model writes the tests, fixtures and fakes named in the PRD test-oracle rows; a test runner records the failing run. Implementers (smaller models for simple tasks, larger models for kernel or ambiguous work) make them pass inside disjoint owned paths, in parallel where the DAG allows.
4. **EDD.** A test runner executes the suites and coverage and records redacted evidence with `scripts/record_evidence.py`. Coverage thresholds and determinism rules in `TEST_ENGINEERING_STANDARD.md` are gates.
5. **Independent review.** A fresh-context larger model audits conformity, unrequested scope and test discrimination, and adds one adversarial negative. An author never accepts its own work.
6. **Checkpoint.** Only the root coordinator updates canonical state, through `scripts/checkpoint_execution.py --expected-revision <current>`, and appends to `docs/governance/LOG.md`.

## Real-provider proof

Mocks, schema checks and scripted fakes never count as real-provider proof. S00 CAP-01 and CAP-02 each need 30/30 live runs under `docs/testing/TEST_EXECUTION_PROTOCOL.md`, starting from `quati ask` with an ordinary utterance, observing the real provider's tool calls, with no gold capability ID in the model input. If no approved provider configuration is available, ask only for the missing secret reference and report the gate as `BLOCKED`; continue with work that does not depend on it. Credentials are used only through secret references and never appear in logs, patches or evidence.

## Slice constraints

Durability, providers and specialist agents are integrated one slice at a time following `ROADMAP.md`; do not scaffold 31 services. Domain packages stay isolated from ledger backends, model SDKs and transports. Every adapter advertises its feature limits; a missing optional harness returns a typed `UNAVAILABLE` and does not take down Quati.

## Mandatory report format

`Slice`, `Task`, `Requirements covered`, `Changed files`, `Tests and proof tiers` (passed, failed, skipped, expected-failed, errored), `Coverage`, `Real LLM/provider used?`, `Red-team outcome`, `Resource/cost measurements`, `Blocked/unverified items`, `Next gate`, `Rollback`. All in English. Never report external interoperability as passed on the basis of a fake server.
