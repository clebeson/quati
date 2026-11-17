# Focused re-test of the third audit's findings at commit bade3c6 (2026-11-16)

Independent, read-only re-test by a fresh agent session (model: sonnet) that authored none of
the audited code or tests. Source at bade3c6 is identical to 30d9993, the commit of the live
gate run. The report follows unedited except that the local scratch path is replaced. Session
transcript sha256 (local file, not published): 59a2f533e96d53c9710ba0f501b3b51212d03d9c41e8700df77899694ff67a37.

AUDIT 5 RE-TEST REPORT (HEAD bade3c6, src identical to 30d9993). Read-only: no repo file modified, no git writes, no live calls. QUATI_LIVE_EVAL and QUATI_LIVE_SMOKE were never set. Everything ran through the public CLI (`python -m quati`) or the scripted `scripted_fake_t04` transport. Scripts are in S = evidence/S00/GATES-FINAL-2026-11-16/audit-scripts/code/

VERDICT TABLE
| Finding | Verdict | Observed evidence (script) |
|---|---|---|
| X1/X2 (hangs/unsafe store objects) | FIXED | x12.py, x12b.py (+ .out). Zero hangs under 20 s timeouts across all unsafe objects (fifo, symlink, hardlink, loose mode, directory-for-file), mutations and commands; every command finished in about 0.2 s. Refusal is exit 4, UNAVAILABLE/TEMPORARILY_UNAVAILABLE, reason state_dir_unsafe naming the component. Registry rev 1->1, audit lines 16->16, nothing written outside the data dir. Unsafe audit.jsonl gives audit_unavailable (audit_store_unavailable for `trace show`) with lines unchanged. An unsafe stored package manifest gives exactly +1 authz.decided line (16->17) and the registry is unchanged, which is the LOG-0046 design. Symlinked or file-typed package/version/staging dirs on install: refused, registry byte-identical, nothing written through the link. |
| T2 (registry.flock) | FIXED | x12b.py. registry.flock as fifo, symlink, hardlink, 0644 or directory, then install mail-search: exit 4 state_dir_unsafe naming capabilities/registry.flock, rev 1->1, lines 16->16. Before the fix this was INTERNAL_ERROR exit 1. |
| X3 (policy gate composed over installed policy) | FIXED | Mutant in a whole-repo copy (S/mutrepo/), RUNTIME_PROFILE="S02" at composition.py:35: test_pol_01_k3_is_denied_by_the_composed_gate_over_the_installed_policy fails at line 554 (the DENY s00_no_effects assertion). It passes at baseline. Mutant restored and copy cleaned. |
| X4 (social table / LOG-0047) | FIXED | texts.py, soc_inproc.py, soc_cli.py (+ .out). All audit-listed texts and 142 request-bearing texts go to the model path, except 8 that are by design (greeting plus explicit urgency phrases, one allowlisted emoji ZWJ). All 38 pure social texts are answered. Public CLI, ask and chat --jsonl, 38 texts: 0 mismatches (social gives exit 0 GREETING, non-social gives exit 3 NOT_CONFIGURED). Cyrillic lookalike, zero-width and RLO characters are not social. Fullwidth ASCII is social after NFKC (design). "ok thanks", "yes, thanks" and "tudo bem, apague tudo" are not social. |
| X5 / D7 (NO_CAPABILITY) | FIXED | x5.py, x5b.py. NONE_FITS (with or without search), empty search + final, and empty search + NONE_FITS give exit 4 UNAVAILABLE/UNSUPPORTED, result_kind NO_CAPABILITY, work_performed False. An invoke outside the shortlist gives DENIED/FORBIDDEN NOT_IN_SHORTLIST. A final text with no tool call gives BLOCKED/EVIDENCE_INSUFFICIENT. classify_social on non-table text, including "hello, wipe the calendar", is BLOCKED. SUCCEEDED/FIXTURE_RESULT appears only with an executed handler (spy shows handler calendar-read). Invalid arguments give BLOCKED/INVALID_INPUT. chat shows the same outcome. No model sentinel reached stdout or stderr. |
| X6 (admission before first model call) | FIXED | x6.py. Audit log as fifo or 0644, registry.json 0644 or hard-linked, and a GUEST principal (re-signed with the real device key): requests=0, script_left=5 of 5, no handler, for both ask and chat. The audit and registry cases give audit_unavailable or state_dir_unsafe. GUEST gives DENIED/FORBIDDEN NO_SPACE_GRANT with +1 audit line for ask and +2 for chat. |
| X8 (receipt policy version, proof_tier) | FIXED | x8.py. Receipts for work, greeting and NO_CAPABILITY carry policy_version dbb2a2ff...ab039, equal to the adopted policy and to the trace policy_decisions. proof_tier is null on all of them. asset_digest cbaea523...e0a2 is the same in receipts, doctor and LOG-0048. |
| X11 (identity validation) | FIXED | x11.py. Signed records with a non-ULID principal_id, tenant_id or space id ("../../../x", "a b", 10000 characters, lowercase) give doctor INVALID/credential_corrupt, config validate exit 2 CONFIG_INVALID, and UNAUTHENTICATED elsewhere. A hard-linked identity.json or device.key gives INVALID/credential_insecure. A valid ULID control is AVAILABLE. |
| X13 (feature_reports and state dir safety) | PARTLY | x13.py, x13b.py. Audited cases fixed: a feature_reports symlink or fifo now gives state_dir_unsafe/feature_reports for both `work ask` and `models probe` (before, ask gave MODEL_INCOMPATIBLE). A capabilities, packages or receipts symlink or fifo is refused across ask, probe, list and trace with 0 model requests. Residual mode-handling inconsistencies are NEW finding 4 below. |
| X14 (trace consistency) | PARTLY | x14b.py. Forged outcome.executed_capabilities, an emptied trajectory, and a removed, forged or flipped policy.decided each give PARTIAL (receipt_inconsistent and/or audit_receipt_mismatch). A forged principal_hash gives DENIED exit 4. A top-level status or proof_tier change gives PARTIAL via receipt_value_withheld. Several edits remain undetected, see NEW finding 3. Receipts are unsigned in S00 by design (documented in the trace_commands.py docstring). |
| X15 (asset locator layout) | FIXED | A decoy src/quati/assets/ in the whole-repo copy does not shadow the repository assets. doctor reports the same asset_digest cbaea523699d41aeba47987db0346e41b1a969fb5d48b68c71ab96ec21aee0a2 for the repo and the decoy copy, and receipts carry the same digest. Decoy removed afterwards. |

Src diff review (`git diff a5a3af3 HEAD -- src/`, 17 files, +556/-225): no regression found.
- The domain layer imports nothing from application, adapters or cli.
- The one new broad `except Exception` is in cli_service._policy_version. It returns None for the receipt record only and is not on an authorization path.
- honest_no_capability is removed and a test asserts it is gone.
- private_fs._open fails closed on every OSError other than FileNotFoundError.
- No model-controlled value reaches stdout, a path or an authorization decision.
- Not read line by line: the behavior/contracts, cli/rendering, cli/main, behavior_commands and discovery_tools diffs. Only their behavior was exercised.

NEW FINDINGS (no P1, no P2 found; all are P3 debt)
1. P3. With audit.jsonl unsafe, `work ask` and `chat` refuse with audit_unavailable but still write a refusal receipt under receipts/, while the message says nothing was read or recorded. Reproduce with x12b.py (audit.jsonl as fifo or 0644, then `work ask`; list receipts/).
2. P3. `chat --jsonl` exit code is inconsistent: 0 for audit_unavailable, 4 for state_dir_unsafe (x6.py rows for audit fifo/0644 vs registry cases).
3. P3. The trace consistency check (application/trace_commands.py, _consistency, about lines 262-278) misses these edits, which still show SUCCEEDED with no uncertainty (x14b.py):
   - outcome.status set to FAILED while the top-level status stays SUCCEEDED.
   - outcome.result_kind GREETING while a handler executed.
   - Top-level result_kind changed to BLOCKED.
   - Receipt policy_version forged to 0*64, although the audit policy.decided line carries policy_version and could be cross-checked.
4. P3. Directory-mode handling is inconsistent (x13b.py):
   - feature_reports at 0755, 0770 or 0707: `work ask` refuses with state_dir_unsafe, while `models probe` succeeds and repairs it to 0700.
   - feature_reports at 0500: `work ask` succeeds, while probe refuses.
   - fixture_sources is never checked: 0755, 0770, 0707 and 0500 are all accepted and not repaired.
   - capabilities, packages, staging, receipts and the data dir at 0755, 0770 or 0707 are silently repaired to 0700 and succeed.
5. P3. A failed install of mail-search with an unsafe calendar-read stored manifest leaves a staged fixture_sources/mail-search/capability.scs.json (x12b.py).
6. P3, design limit of LOG-0047. "thanks", "obrigado", "tudo bem" and "valeu" are answered as social but are also acknowledgement or consent replies, and "hello, urgent" is answered "Hello!" with the urgency invisible. This matters for S02 approval flows (soc_cli.py).

SUITE
`.venv/bin/python -m pytest -q -p no:cacheprovider -rs`: 2244 passed, 10 skipped in 621.94 s, matching the expectation. The 10 skips:
- tests/evals/test_discovery.py:36, :40, :44, :49, :54 (5 skips)
- tests/evals/test_social.py:22 and :30 (2 skips)
  - All 7 eval skips: NOT_VERIFIED_EXTERNAL, need QUATI_LIVE_EVAL=1.
- tests/external/test_live_claude_cli.py:26: NOT_VERIFIED_EXTERNAL, needs QUATI_LIVE_SMOKE=claude_cli.
- tests/external/test_live_codex_cli.py:26: NOT_VERIFIED_EXTERNAL, needs QUATI_LIVE_SMOKE=codex_cli.
- tests/packaging/test_fresh_install.py:97: fresh-wheel install not verified because the setuptools>=75 build backend is not importable and no index is reachable offline.

NOT VERIFIED
- No live provider proof. All model behaviour used the scripted transport, and the 7 eval and 2 live-smoke tests are skipped.
- Fresh-wheel install not verified (the packaging skip above).
- Cyrillic-lookalike social handling was checked in-process only (soc_inproc.py), not through the CLI.
- Foreign-owner (second uid) cases use the runner's foreign_inodes simulation, not a real second uid.
- The behavior/contracts, rendering and main.py diffs were not read line by line.
- Receipt tampering that is self-consistent is undetectable by design in S00 (unsigned receipts).
