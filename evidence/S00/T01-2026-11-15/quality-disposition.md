# Quality-tool disposition — S00-T01

The raw quality delta is preserved in quality-delta-final.txt. It is NOT a clean
static-gate result: thirteen major rows remain, all consciously reviewed below.
No complexity/nesting regression row remains after checkpoint-helper refactoring.
There is no Git HEAD baseline in this export; the measured floor is a local sidecar
captured at the start of implementation, including an early helper draft.

| Finding group | Disposition and evidence |
|---|---|
| ask marked dead | Registered Typer callback. Actual CLI subprocess tests and coverage execute it. Removing it would remove the public command. Static caller resolution does not model Typer registration. |
| write_receipt marked dead | Injected EvidenceSink callable. Real receipt/hash/privacy tests and retained smoke receipt bytes execute it; no filesystem write is mocked. |
| _create_private / engineering safe_write | Intentional small exclusive-write sequence at separate runtime and engineering boundaries. Runtime adds descriptor/non-symlink handling and must not import scripts. A cross-layer utility would join unrelated trust boundaries. |
| parser / parser | Argparse option registration in engineering tools. Shared parser state would couple distinct command contracts; their arguments differ. No application algorithm is duplicated. |
| independent make_state / author's state_fixture | Independent reviewer constructs a minimal state fixture rather than sharing the author's assumptions. This duplication is deliberate test independence, not runtime duplication. |
| remaining crash/conflict/corruption/CLI test clones | Similar fixture and subprocess setup with discriminating, different state/fault assertions. The crash windows must remain distinct or parameterized without merging their oracles. Existing tests are small; no new generic test harness is justified by a token match alone. |

Static test-gate/contract reports are conservative for dynamic callbacks and injected
ports; a zero static caller count is not executable coverage. The edit-check reports
no Git baseline, so no Git contract-compatibility comparison is claimed. Actual tests,
coverage, independent adversarial reproduction and source hashes remain the acceptance
evidence. No quality acknowledgment silently suppresses the raw findings.
