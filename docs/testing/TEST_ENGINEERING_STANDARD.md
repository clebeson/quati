# Test engineering standard

Normative for every slice. `TEST_EXECUTION_PROTOCOL.md` defines tiers, gates and statistics; this file defines how tests are written, how deterministic they must be, how much they must cover, and which model role does what.

## 1. Coverage targets ("maximum coverage")

Coverage has two dimensions and both are gated.

**Requirement coverage (gate: 100%).** Every FR, AT, RT, INVARIANT and DERIVED ID in `docs/traceability/FULL_REQUIREMENTS_MATRIX.csv` owned by the slice has at least one executed test whose name matches the PRD `## Test oracles` row, with a positive and a negative observation. An ID with no executed test is `NOT_RUN` and blocks the slice seal `TESTS_VERIFIED`.

**Code coverage (measured with `coverage` in branch mode over the deterministic lanes `tests/unit` and `tests/integration` only).**

| Package | Line | Branch |
|---|---|---|
| `src/quati/domain/` | 100% | 100% |
| `src/quati/behavior/` | 100% | 100% |
| `src/quati/application/` | ≥ 95% | ≥ 95% |
| `src/quati/adapters/` (code reachable without a real provider) | ≥ 90% | ≥ 85% |
| `src/quati/cli/` | ≥ 90% | ≥ 85% |
| Whole package | ≥ 95% | ≥ 90% |

Rules:
- Every guard in `contracts/guard-registry.json` and every row of `contracts/commitment-control-v2.json` has a unit test for its true case and for each distinct false case. Every decision table in a PRD is tested by exhaustive enumeration of its input combinations.
- A line may be excluded only with `# pragma: no cover` plus a reason on the same line, and only for code that is unreachable without a real provider or another OS. Each exclusion is listed in the slice evidence. Unexplained exclusions fail review.
- Thresholds are never lowered to make a slice pass. A shortfall is recorded as `FAIL` with the uncovered lines.
- Coverage numbers come from an actual run recorded through `scripts/record_evidence.py`; they are never estimated.

## 2. Determinism rules

A test in `tests/unit`, `tests/integration`, `tests/chaos` or `tests/packaging` must give the same result on every run and on any machine. Specifically:

1. **Time.** Code under test reads time only through an injected clock port. Tests use a fake clock and advance it explicitly. No `time.sleep`, no wall-clock reads, no timing-based assertions.
2. **Identifiers and randomness.** IDs come from an injected generator; tests use a seeded or counter-based generator. Any randomness takes an explicit seed that is recorded in the test.
3. **Ordering.** Never assert on dict, set, filesystem or query order unless the code sorts explicitly. Concurrency tests use barriers or explicit interleaving hooks, not sleeps.
4. **Isolation.** Each test uses its own `tmp_path` and its own SQLite file. No shared global state, no dependence on test order, no network. Environment variables and the home directory are set per test.
5. **Faults.** Crashes are injected at named points (see the fault matrix in `TEST_EXECUTION_PROTOCOL.md`); the chaos lane kills a real subprocess at that named point. Network and provider faults come from a scripted local stub with recorded responses.
6. **Models.** Deterministic lanes never call a real model. They use a scripted `ModelPort` fake that returns fixed, schema-valid outputs. A fake proves the code path only; it is never evidence of model behavior or of a provider integration.
7. **Assertions.** Assert exact state, exact reason codes, exact call counts and exact persisted rows. Do not assert on free text produced by a model. A test must fail when the behavior it names is removed (no self-fulfilling mocks: the fake must not contain the logic under test).
8. **Subprocesses.** Invoke the interpreter by absolute path (`sys.executable` resolved with `Path(...).resolve()`), with an explicit working directory and environment.

Non-deterministic lanes:
- `tests/evals` calls a real model. It is blind, thresholded and statistical under `TEST_EXECUTION_PROTOCOL.md` ("Statistics note"). Everything except the model's own output is still fixed: prompts, paraphrase set, catalog digest, seeds for shuffling, and code-only graders.
- `tests/external` calls a real provider, channel or other OS. Without approved configuration the result is `BLOCKED` or `NOT_VERIFIED_EXTERNAL`, never a mock-based `PASS`.

A flaky deterministic test is a bug: keep the first failure, open a `BUG-` record, and fix the cause. Do not add retries.

## 3. Lane selection

Choose the most deterministic lane that can observe the requirement:

| Question | Lane |
|---|---|
| Decidable by pure code (guard, reducer, validator, decision table, compiler)? | `tests/unit` |
| Needs the real ledger, worker, outbox or CLI process with fake ports? | `tests/integration` |
| Needs kill/restart or concurrent processes? | `tests/chaos` |
| Needs install, wheel content, assets or OS behavior? | `tests/packaging` |
| Depends on what a real model chooses or writes? | `tests/evals` |
| Depends on a real provider, channel or account? | `tests/external` |

A requirement that mixes deterministic and model-dependent parts is split: the code-decidable part is tested in a deterministic lane, and only the residue goes to `tests/evals`.

## 4. Who writes and who runs tests

| Activity | Role |
|---|---|
| Design test oracles; write test code, fixtures, fakes and crash hooks; write graders for evals | Larger model (test author) |
| Review that a test discriminates (fails when the behavior is removed) | Larger model, different context from the author |
| Run test suites, coverage and validators; collect output; record evidence; report counts | Smaller model (test runner) |
| Diagnose a failure | Smaller model reports the exact failing test and output; a larger model diagnoses when the cause is not a one-line fix inside the runner's owned paths |
| Decide `PASS`, issue seals, write canonical state | Root coordinator only |

Rules for the test runner:
- Run exactly the commands in the work package; report passed, failed, skipped, expected-failed and errored counts separately, with the full failing output.
- Never edit a test, fixture, threshold, skip marker or coverage configuration to obtain a green result. Never delete a failing test. If a test looks wrong, report it and stop.
- A skipped, expected-failed or lower-tier run is not `PASS`.

Rules for the test author:
- Write the tests before the implementation and confirm they fail for the right reason (red), then hand the implementation task over (green). Record the red and the green run.
- One test function per oracle row, named exactly as in the PRD. Additional edge-case tests are welcome and must also be deterministic.

## 5. Standard commands

Run from the repository root with the project interpreter by absolute path:

```
.venv/bin/python -m pytest -q tests/unit tests/integration
.venv/bin/python -m coverage run --branch -m pytest -q tests/unit tests/integration
.venv/bin/python -m coverage report --show-missing
(cd spec_tools && ../.venv/bin/python validate_spec.py && ../.venv/bin/python validate_readiness.py)
```

Lanes `tests/evals` and `tests/external` run only with an approved provider configuration supplied by secret reference, and only when the work package calls for them.
