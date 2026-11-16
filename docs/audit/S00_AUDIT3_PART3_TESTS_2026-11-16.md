# Third independent audit, part 3 (tests): mutation and changed expectations at a5a3af3

Addendum to docs/audit/S00_AUDIT3_2026-11-16.md. This part of the audit finished after the main
report was handed back. Measured on a scratch copy of commit a5a3af3 (code digest 96d07082...).
The report follows unedited except that local absolute paths are replaced. Session transcript
sha256 (local file, not published): d908e71103484f2b98a8ee7195ce8eab88c98987965e1ca00dbc7def87b49318.

Task: part 3 of the audit (tests) — mutation testing on a scratch copy, review of changed test expectations, and tier/determinism check of the new tests. I did not modify the repository and made no live call.

**The repository moved while I worked (not by me).** `git log` now shows commit c232241 "Record the third independent audit (LOG-0044)" on top of a5a3af3, and about 57 files are modified and uncommitted (most of `src/quati/*`, new `test_s00_fix8_*` tests). The live code digest is now 8c383a4c…, not 96d07082…. Everything below was measured on a scratch copy taken before that; its `src/quati` digest is the claimed 96d0708298d5ff21013ed03c1972f34d41e37b01f4fb47f115b0641493d74d65. Anything run against `src` now is not the audited commit.

**Baseline on the copy (full suite):** 1621 passed, 10 skipped, 1 failed. The failure is `tests/unit/test_eval_harness_soc01.py::test_pilot_run_writes_the_preregistration_and_is_never_gate_protocol` (line 644), which needs its tree to be a git checkout. It is deselected in all mutant runs. This is consistent with 1622/10 in the repository.

## (a) Mutation results

- **Product code:** 149 single-point mutants, 126 killed, 23 survive the full suite. The sanity mutant was killed.
- **Harness graders:** 44 mutants against `tests/unit/test_eval_harness_*.py`, 38 killed, 6 survive.

### Survivors of the full suite (file:line at a5a3af3)

| id | location | mutation | verdict |
|---|---|---|---|
| W01 | `adapters/runtime_facts.py:71` | `SO_ACCEPTCONN` → `SO_KEEPALIVE` | Real gap, introduced this round (finding T1). |
| P23 | `adapters/capability_store.py:100` | lock file opened with plain `os.open` instead of `open_private` | Real gap: no test at any tier puts a symlink, FIFO, hard link, foreign owner or directory at `capabilities/registry.flock` (finding T2). |
| P23b | `capability_store.py:100` | `tighten=True` dropped for the lock | Real gap, same area. |
| P06 | `adapters/private_fs.py:146` | `O_NOFOLLOW` dropped in `open_private` | Real gap for the lock file; the audit-log use is masked by the preceding `read_private`. |
| T10 | `application/trace_commands.py:105` | list items copied without the per-item shape check | Real gap for D6: forged list fields of a receipt (`executed_capabilities`, `candidate_ids`, `observed_model_ids`, `excluded[].reasons`, `filter_results`) would be displayed verbatim. The forged-receipt test (`test_trace_commands.py:460`) forges scalars only. The code is correct; it is unproven. |
| T14, T15, T16 | `trace_commands.py:218-221` | explain picks `selected` without `handler_executed is True` / without `verdict == "ALLOW"` / without `status == "SUCCEEDED"` | Real gap on the CAP-02 / M26-AT-01 oracle: no test has a refused or non-executed invoke of another capability in the explained receipt. |
| S17 | `domain/social.py:107` | "please" added to MARKERS | Real gap: no test pins the MARKERS set. A work-carrying word added there is caught only if it happens to be in a negative sample. |
| S05c | `social.py:128-133` | zero-width/format characters dropped inside a word | Gap: no test with such characters. At a5a3af3 "he\u200bllo" and "hello\u200b" are not social (checked directly), which is the safe direction. |
| T05, T06 | `trace_commands.py:186-187` | audit events not filtered by tenant / actor | Low: reachable only with a forged or shared audit log. |
| P17 | `adapters/trace_store.py:32` | reader with `tighten=True` | Low: nothing proves `trace show` leaves directory modes alone. |
| I05 | `adapters/local_identity.py` (`_load`) | `owner_uid` not compared | Pre-existing gap, not from this round. |
| T03, T04, T11 | `trace_commands.py:170, 179` | identifier shape check off / prefix match; receipt id shape check off | Each masks the other; the identifier is only compared, never used as a path. Not a defect. |
| S02b, S12, S15, P10b, X07, C05 | `social.py:120, 146, 165`; `private_fs.py:57`; `cli/main.py:100`; `behavior/contracts.py:48` | single NFKC; last language wins; shortest phrase first; tighten only on group/other bits; `_emit` without `settled_exit`; `is_dir()` → `exists()` | Equivalent or near-equivalent in outcome. |

### Killed only by in-process tests
I ran 68 key mutants against the child-process tests alone (the three public files plus the child-process tests of `tests/unit/test_s00_fix7_social_authz.py`). Twelve survive there:

- **S06** markers alone are social (`social.py:178-179`): no public text is marker-only.
- **P11** symlinked ancestor of the data dir accepted (`private_fs.py:93`): public tests symlink the data dir itself, not a parent.
- **P10** reader accepts group/other bits (`private_fs.py:59`).
- **P19, P20** feature report save without the chain check; pointer read follows a symlink (`adapters/feature_reports.py:39, 53`).
- **P24** `audit_events` plain read (`capability_store.py:230`).
- **P32b** probe authenticates before the configured check (`cli_service.py`).
- **X03** `audit_store_unavailable` not a local-store reason (`domain/diagnostics.py:11`).
- **I02** empty identifier accepted (`local_identity.py`, the `IDENTIFIER_FIELDS` check).
- **I08** identity state shown under `QUATI_CAPABILITY_CONTEXT` (`runtime_facts.py:123`).
- **X06** is equivalent at the boundary; **P10b** also survives the full suite (above).

The other 56 are killed by child-process tests: D1 placement, the D2 block, D3, D4, the rest of the chain checks, the rest of the probe order, evidence-writer stamping, trace authorization and principal filtering, the rest of the exit rule, identity field validation, and the asset locator. The code-digest and key-shape mutants were not in the child-process run: 5 of 5 code-digest and all 23 key-shape mutants were killed in the subset phase, tier not determined.

### Harness grader survivors
- **H28** `grade_selection` `provider_identity_recorded` → True (`tests/evals/live_harness.py`): real gap. No test shows a CAP-01/CAP-02 run without observed model ids failing, although S00-GATE-02 requires model identity.
- **H24** unreadable receipt not counted as failing (`gate_harness.py:514-515`): real gap. `test_binding_fails_on_another_digest_an_unreadable_receipt_or_no_receipt` (`test_eval_harness_soc01.py:502`) asserts only `['unreadable'] == 1`, never `pass is False`.
- **H29** `exit_0_succeeded` → True: gap. The check is also misnamed; it never looks at the exit code.
- **H30** `only_target_executed` loosened: redundant with `every_invoke_attempt_is_target`.
- **H11, H11b** write leg ignores receipt-reported write execution / `launched_false`: low. H11 is backed by the trajectory check (H09, killed); H11b by the run-level launched scan (H26, killed).

The graders do fail on bad inputs in general: per-rule negative tests exist and kill 38 of 44.

Three observations for part 5, read from the code and not run:
- `live_harness.infra_error` (lines 59, 220-229) treats every `TEMPORARILY_UNAVAILABLE` as a provider outage. Since round 7 the product's own local-store refusals carry that code with exit 4, so on a model-dependent run a product storage failure is classified INFRA_ERROR and excluded rather than failed.
- `grade_write_attempt` passes with guard `NO_WRITE_ATTEMPT_OBSERVED`, a vacuous pass when the model never tries the write.
- `grade_mislabel.social_label_ends_blocked` tests only the label `social`, not `simple_answer`; D2 covers both.

## Findings from this part

**T1 (P2/P3, test weakened this round).** The N17 fix replaced the real listening socket with a scripted descriptor table.
- `test_f10_listening_sockets_and_the_live_allowance_are_measured_not_constants` and the runtime-facts test in `tests/unit/test_s00_fix6_cli_surface.py` now use `fake_descriptors` (line 812). Its `FakeSocket.getsockopt` returns 1 exactly when the test says "listening", and `socket.socket` itself is patched.
- No test in the repository opens a real listening socket any more.
- W01 survives the full suite; the pre-round test (real `bind/listen`, `== 1`) would have killed it.
- M01-AT-01 "no listening socket" is therefore proven against a self-fulfilling mock (AGENTS.md "No self-fulfilling mocks").

**T2 (product behavior at a5a3af3, found while classifying P23).** Repro: with `PYTHONPATH=<forkT>/base/src` in an isolated profile, run `init`, `capabilities install-fixture calendar-read --enable-fixture`, replace `data/capabilities/registry.flock`, then run `capabilities install-fixture mail-search --enable-fixture --json`.

| `registry.flock` is | observed | required (M01 § Data directory rule 2) |
|---|---|---|
| symlink | exit 1 `INTERNAL_ERROR` (stderr `internal error (OSError)`) | typed `state_dir_unsafe`, exit 4 |
| directory | exit 1 `INTERNAL_ERROR` (`IsADirectoryError`) | typed `state_dir_unsafe`, exit 4 |
| hard link, FIFO | typed `state_dir_unsafe`, exit 4 | as observed |
| mode 0644 | tightened to 0600, install succeeds | — |

- In all four refused cases one audit line is appended before the refusal, although the Response says "nothing was read or changed" and rule 2 says "no audit line is written". I counted the line but did not inspect it; presumably the `authz.decided`.
- The registry was unchanged and the symlink victim untouched in every case.
- The uncommitted round-8 tree answers `state_dir_unsafe` for all five (I ran the same probe against it by accident first), so this looks already known as LOG-0044 X1/X2. I did not read LOG-0044.

**T3 (P3).** `test_pilot_run_writes_the_preregistration...` depends on the tree being a git checkout and fails on any export or copy.

**T4 (P3, record keeping).** LOG-0042 says the changed expectations are "listed with citations in the agents' reports (27 rows … 6 rows)". Those lists are not in `evidence/S00/T05-fix7-*/green.txt` nor in `T05-integration7`; only the in-test comments carry the citations.

## (b) Changed expectations in pre-existing tests

Scope: `git diff 5225cb2 a5a3af3 -- tests/`, the 23 modified files.

No test function was deleted without a replacement, no skip or xfail was added, and no equality was loosened to membership. The behavior changes I read carry an in-test comment naming the decision. The normative text I checked (S00_RUNTIME_CONTRACT "Displayed text and social outcomes", M01 exit rows and § Data directory, ACCEPTANCE_CASES SOC-01/IDN-02/POL-01) was written in the same round, and M14/M15 were also amended in it. The independent anchor is LOG-0041 (D1-D6, N1, N7, N15, N17), committed before the round.

| Change | Files | Verdict |
|---|---|---|
| D1: social-only text answered with zero model requests, `provider_used` false, no uncertainty; a pleasantry without a greeting gets its language template | `test_s00_t04_ask.py`, `_edges.py`, `_fixes.py`, `_fixes3.py`, `_fixes4.py`, `test_s00_fix6_authz_ask.py` | Justified (D1). Mostly stricter. |
| D2: social label on non-table text goes from CONVERSATION exit 0 to BLOCKED / `NO_VERIFIED_EXECUTION` exit 4; several tests renamed to what they assert | `test_s00_t04_fixes.py`, `_fixes2.py`, `_fixes3.py`, `test_s00_fix6_authz_ask.py` | Justified (D2, N3). Stricter. |
| SOC-01 fault: "Hi, urgent, how are you?" on model timeout goes from exit 5 to GREETING exit 0; the timeout is now asserted on greeting-plus-work text | `test_s00_t04_ask.py:84-101` | Justified by D1. It removes the only deterministic "timeout during a greeting" case, consistent with the live timeout leg being NOT_RUN. |
| D3: `launched` True → False | `test_s00_t04_ask.py:131` | Justified (M01-FR-02). |
| D4: invoke of an unknown or hidden id now `FORBIDDEN` / `NOT_IN_SHORTLIST`; in-turn describe likewise | `test_approval_injection.py`, `test_gateway_binding.py`, `test_s00_t03_registry.py` | Justified (D4). In the last two files describe still answers `NOT_A_CAPABILITY_ID`, because the rule at `application/discovery.py:231` applies only when `require_describe` is set (ask turns). |
| Invalid active behavior package: greeting exit 0 → exit 2 | `test_s00_fix6_cli_surface.py` | Justified by M01 row precedence; stricter. |
| `audit_unavailable` exit 5 → 4 | `test_identity.py:744`, `test_s00_fix6_cli_surface.py` (3 places) | Justified only by LOG-0041 N15 (a P3 item) and the M01 row 4/5 rewrite of this round. An exit-code contract change, not a weakening. |
| Unusable receipts path: `INTERNAL_ERROR` exit 1 → `state_dir_unsafe` exit 4 | `test_s00_t01.py:187` | Justified (N1); stricter. |
| Symlinked store root now refused | `test_s00_fix6_cli_surface.py` | Justified (N1); stricter. |
| Listening-socket tests: real socket → fake descriptor table | `test_s00_fix6_cli_surface.py` | Weakened (T1). |
| trace S02-UNSUPPORTED cases removed for show/explain | `test_s00_fix6_cli_surface.py` | Justified (D6); replaced by `test_trace_commands.py`. |
| Setup only: `authorize=` port for probe; gate `directory=` | `test_cli_service.py`, `test_m17.py`, `s00_t04_support.py`, `s00_t03_support.py`, two policy/approval tests | Setup; see the note below. |
| Integration step: receipts must carry exactly the code digest; fixture_sources modes no longer excluded | `test_s00_fix7_social_authz.py`, `test_s00_fix7_public_surface.py` | Stricter. |
| `tests/evals/test_social.py` now calls the 10-runs-per-text gate | — | Stricter; still skipped without `QUATI_LIVE_EVAL`. |
| Wheel leg builds from a temp copy and asserts packaged assets, hashes, init, greeting | `tests/packaging/test_fresh_install.py` | Stricter, but still skipped here (no setuptools). |

Note on the setup-only row: `SyntheticDirectory` (`tests/unit/s00_t03_support.py:75-88`) returns OWNER and both grants unconditionally and is now also the policy gate's role source, so every test built on `build()` exercises an allow-all directory. Role denial is proven separately with real re-signed records in child processes (`test_s00_fix7_social_authz.py:552-580`). `test_cli_service.py:22` and `test_m17.py:829` use an allow-all `authorize` lambda.

## (c) Tier and determinism

- **"121 public child-process tests" is exact.** `test_s00_fix7_public_surface.py` collects 121 cases. Each runs `python -m quati`, or the public `main` through `fixtures/fix7_public_runner.py`, in a child process with isolated dirs. `test_s00_integration7_public.py` collects 7 and `test_trace_commands.py` 35. All are child processes; 163 passed at baseline.
- **Caveats on the tier.** Foreign ownership is simulated by overriding the uid the child observes (stated in the file header). The scripted-model legs register a fake transport inside the child; `test_s00_fix7_social_authz.py:19-21` calls these L1 while the public-surface header calls them L2. These children set `QUATI_ALLOW_LIVE=1` with the scripted fake transport only, and the runner refuses and records every socket use.
- **Determinism.** No sleep, wall-clock read, random or socket use in the new test files or runners. `test_trace_commands.py` in fully reversed order: 35 passed.
- **Shared stores.** Module-scoped profiles (`recorded` in `test_trace_commands.py:145`; `probed`, `unprobed`, `catalog` in `test_s00_fix7_social_authz.py:194-201, 477`) are written to by the tests that use them. I saw no order failure, but they are not isolated stores in the sense of AGENTS.md rule 4.
- `tests/unit/test_s00_fix7_social_authz.py` lives in `tests/unit` but is mostly child-process integration (122 cases).

## Not verified
- Mutants are hand-chosen single points, not exhaustive. Equivalence verdicts are by reasoning, except S12 (table duplicates checked) and S05c (behavior checked directly).
- I did not review LOG-0044, commit c232241 or the uncommitted round-8 changes.
- Coverage percentages and the round's own mutation claims (21/21, 38/38, 22/22, 16/16) were read, not re-run.

The final hand-off tool was unavailable in this session, so this report is delivered as plain text.

Files are in `evidence/S00/GATES-AUDIT3-2026-11-16/audit-scripts/forkT`:
- `mutate.py` (phases `subset`, `l2`, `full`, `harness`)
- `out/subset.tsv`
- `out/l2.tsv`
- `out/full.tsv`
- `out/fullbase.txt`
- `base/` (pristine copy of the audited tree)
