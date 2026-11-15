# SECMA Test Strategy — High Assurance Without Speculative Test Explosion

## Why tests exist
Tests prove risk-bearing user outcomes, not the number of methods implemented. Each risk-invariant requires an observed public-path positive example, a meaningful negative counterexample and one failure injection only when recovery can change the result. Reuse contract suites across adapters and one integration test across combined workflow. A test that asserts a mock's chosen answer is not an LLM autonomy test.

## Proof tiers and boundaries
| Tier | What is demonstrated | What it does **not** demonstrate |
|---|---|---|
| L0 | Docs, schemas, states, references, compiled prompt hashes | Product runs or the LLM can choose correct tools |
| L1 | Real pure code enforces state, guards, authorization and routing constraints | Durable service or provider correctness |
| L2 | Actual DBOS + PostgreSQL, synthetic authenticated endpoints, crashes and reconciliation | Real Slack/Gmail/Codex/provider interoperability |
| L3 | REAL approved LLM invoked from natural-language CLI, authentic tool trace, unknown installed capabilities | Guaranteed success on every future model or task |
| L4 | Authorized live provider integration in isolated test account/workspace | Enterprise production scale |
| L5 | Measured OS/deployment/HA/soak/security controls | Future reliability forever |

`NOT_RUN`, `PASS`, `FAIL`, `BLOCKED`, `NOT_VERIFIED_EXTERNAL` must remain distinct. Gate status is worst required proof tier, not average test count.

## Essential test types
1. Pure parser/config/schema: malicious config, invalid shapes, forbidden transitions, prompt collisions and localization correctness.
2. Policy/property/state transition: each allowed edge, forbidden edge, monotonic versions and failure-safe decisions; zero unauthorized effects in enumerated safety suite.
3. Real DBOS/Postgres with deterministic clock: commit/outbox idempotency, worker SIGKILL, duplicate callbacks, network timeout after possible send, outbox retry, two concurrent jobs/versions, cancellation and clean restart. No in-memory stand-in accepted for the durability gate.
4. Real-model blind eval: seed capability definitions deliberately **not named** in user request, deploy at runtime, model must spontaneously use `search → describe → invoke`, correctly abstain for greetings, avoid unauthorized binding and respect output. Dataset/labels must not be visible in prompt or registry metadata.
5. Multi-turn ERI eval: pending work + follow-up information + delayed executor result + question-worthy ambiguity + user language + concise delivery, 30–50 realistic initial episodes then holdouts as needed.
6. External adapters: fake server for signature, retries, invalid auth, rate limit, schema drift and timeouts; one authorized live smoke per provider/feature prior to marking it validated. Mocks are not external certification.
7. Resource and portability: CLI process end vs worker, sleep/reboot, native Windows/macOS/Linux installation, low RAM, proxy/CA, offline package, and disabled provider. Benchmarks are **measured** after first executable slice.

## How not to test
- Do not pass `target_capability_id` or golden label to the tested LLM before capability choice.
- Do not call `capabilities.invoke()` directly and declare automatic capability discovery verified.
- Do not use a deterministic fake LLM and call the result real conversational judgment.
- Do not measure prompt length, star counts, schema coverage or lines of code as a proxy for task correctness.
- Do not demand every permutation of models × providers × OS × channels; use risk-based pairwise smoke plus mandatory safety invariants.
- Do not count an unauthenticated simulated webhook as a validated integration.
- Do not hold the entire project hostage to a nonexistent corporate Slack tenant; mark external smoke gated and continue safe unrelated development.
- Do not allow the judge model to grade itself as the only source of approval.

## Acceptance thresholds and calibration
Deterministic safety invariants: **zero known bypasses** in attack suites, zero lost accepted commitments in the explicit fault suite, zero confirmed cross-tenant disclosures. These are universal release blockers within tested conditions, not global mathematical guarantees. Model routing: establish confidence intervals and confusion matrix first; proposed initial success target ≥85% on balanced sealed holdout for enabled low-risk routing, but a particular smaller model failing that score must be demoted/limited, not rubber-stamped. Severe unauthorized action acceptance: 0 in safety holdout. ERI preference and interaction quality measured by blinded reviewers on a 1–5 anchored rubric plus objective timing/false-promise checks. Limit loops, tokens, retries and cost by policy.

## Test selection algorithm
For every FR: map to existing shared test; create a new test only if the requirement introduces a distinct observable failure mode. For each module: select one positive, one high-risk negative. For cross-cutting faults: one public-path combined test demonstrates the invariant for multiple modules. Validate state machine with property-based path generation rather than enumerating hundreds of redundant transcripts. For live provider support: one smoke per key feature/credential context, not every model combination.

## CI lanes and costs
- PR-fast: L0/L1 and quick fakes, under developer-friendly budget; no mandatory paid LLM calls.
- PR-integrated: DBOS/Postgres local with failure injection when database is available.
- Manual/approved LLM: secret-ref OpenRouter model, metered budget, recording and sealed holdout.
- External: only with explicit authorized account; report `NOT_VERIFIED_EXTERNAL` when absent.
- Release/enterprise: native OS, soak, backup/restore, negative security/ACL and measured footprint.

## Evidence and reporting
Every test output includes case_id, requirement IDs, git SHA, module and config/prompt versions, model/provider/profile identifiers, runtime/tool path used, start/end time, verdict, failure details, trace reference and sanitized artifact hash. Unexecuted gates must remain open. Distinguish generated config tests from executable runtime tests.
