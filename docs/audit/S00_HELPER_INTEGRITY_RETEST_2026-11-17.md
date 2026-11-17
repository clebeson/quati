# Acceptance helper integrity correction

Scope: LOG-0054 H1/H2/H3/H5/H6, engineering checkpoint only. The S00 runtime,
contracts, provider configuration, gate datasets and live harness are unchanged.
No new runtime/provider qualification or slice seal is issued.

## Specification and implementation

The persistent-state specification now states the promotion checks and the
snapshot/commit distinction. A snapshot does not prove a Git commit identity.
Changing a recorded commit while retaining snapshot references is rejected,
including a patch that downgrades every gate. Replacement commit-form seals must
bind the new commit. The consolidated specification was regenerated.

The helper validates the candidate state before writing its journal: every PASS
gate re-resolves retained and new seal references, verifies verdict and source
identity, rejects superseded records and compares commit-form evidence with the
recorded commit. Slice acceptance requires all gates PASS, no blockers and an
acceptance seal per gate. Advance rechecks earlier accepted slices and cannot
move backwards. Rejected transitions preserve state, ledger and journal bytes.

## Executed proof

All paths below are relative to
`evidence/S00/HELPER-INTEGRITY-2026-11-17/`.

| Stage | Evidence directory | Actual observation |
|---|---|---|
| Original adversarial red, Haiku runner | red/20261117T210641Z-dcad681a | Exit 1; 21 failed, 33 passed. All failures were missing safety rejections, not syntax errors. |
| Reviewer-selected snapshot rebind and malformed PASS reference | independent-negative-red/20261117T211204Z-47a94d60 | Exit 1; 2 failed. |
| Two-step downgrade/rebind negative | reconciliation-red/20261117T211603Z-0227dfe3 | Exit 1; 1 failed, 1 passed. |
| Intermediate index-load defect, retained as failure evidence | final-green/20261117T211718Z-b4cda276 | Exit 1; 1 failed, 141 passed; missing index load on the all-gates-downgraded path. |
| Final seven-file suite, Haiku runner, frozen source | final-runner/20261117T212051Z-3859e46d | Exit 0; 144 passed, no failures or skips, 6.74s. |
| Final specification validator | final-validators/20261117T212042Z-2a7fe32a | Exit 0; L0 PASS. |
| Final readiness validator | final-validators/20261117T212043Z-5477087a | Exit 0; L0 PASS, runtime_qualified false. |

The seven files are the four checkpoint suites plus test_reference_compiler.py,
test_audit_regressions.py and test_spec_readiness.py. Final runtime: CPython 3.13.7.
The final manifest binds the source files, amended governance document and
consolidated specification. Its recorded child exit code is authoritative:
Claude's shell wrapper separately failed to write its cwd scratch file.

The earlier Haiku green command accidentally included a standalone `.` and ran
the broader suite (2275 passed, 10 skipped, exit 0; green/20261117T211840Z-57e2c56f).
It began before the final added negatives and source corrections, so it is not
the acceptance proof for the final helper. The explicit final seven-file run is.
No further full runtime repetition was needed for this engineering-only change.

## Independent review and quality

Fresh Sonnet reviews read the normative rules before source. They confirmed the
original H1/H2/H5/H6 correction, selected the snapshot rebind negative, then found
the downgrade variant and the missing index-load path. These findings were
reproduced and corrected rather than waived. The last fresh, read-only review
accepted the final correction, explicitly confirming that `needs_index` covers
both PASS gates and commit changes with retained references. It ran no tests and
did not claim full provenance verification. An earlier reviewer executed the
single materialized negative and observed it passing, but its shell-wrapper
exit status was unreliable; final runner manifests supply executed exit proof.

`ripwire scripts --quality-delta --json` exited zero with no regressions against
1f77060. `--edit-check` found the intentional optional index/root parameters on
apply_advance and no incompatible caller. The wider repository scan also reports
recent churn and pytest-discovered functions as dead code; those are not new
structural source regressions and no metric suppression was added.

## Remaining limits and debt

- H4: the historical acceptance seal's issued_at postdates event 28. Preserve and
  disclose that chronology inconsistency; do not rewrite immutable history.
- The final reviewer retains P2 debt for malformed references on non-PASS gates:
  commit-change/supersession paths can raise an untyped exception on manually
  corrupted references. No checkpoint is written. The typed malformed PASS-gate
  case is covered; this does not claim general state-schema validation.
- Rebinding with stale or superseded references is deliberately strict and can
  block cleanup until valid replacement records exist. It never preserves a
  false PASS to make cleanup easier.
- Full evidence/snapshot provenance and issuer independence remain separate
  readiness-validator and process-review duties. Synthetic helper seals prove
  transition enforcement, not provider integration or human identity.

The root coordinator accepts this bounded engineering correction with those
limits. S01-T01 remains DISCOVER; its specification gaps are not resolved by it.
