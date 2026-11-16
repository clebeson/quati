# Quati implementation checkpoint

Implementation is authorized. Read docs/implementation/implementation_state.json first;
its revision, active task, phase and next_action are the only progress authority.
Do not trust historical PASS claims that are not backed by seal records.

Current slice: S00. S00-GATE-02 is PASS at state revision 16 (seals in governance/seals,
LOG-0037). S00-GATE-01, S00-GATE-03 and S00-GATE-04 are NOT_RUN: each needs evidence,
an independent audit and TESTS_VERIFIED / EVIDENCE_VERIFIED seals on one commit, then
SLICE_ACCEPTED. Open debts: LOG-0013, LOG-0014, LOG-0021, LOG-0034, LOG-0036, LOG-0037.

Entry point: IMPLEMENTATION_READY_INDEX.md, then the selected work package and
docs/governance/LOG.md. The project was renamed from SECMA to Quati (LOG-0035);
hash-frozen history keeps the old name.

State writes: scripts/checkpoint_execution.py only (revision CAS, journal and ledger).
It records active-work progress and slice patches (gate status, seal references, slice
commit, evidence references, blockers). Only root writes canonical state.

Live qualification: tests/evals/run_live_eval.py (real spend on the owner's vendor
sign-in). Any change to src/quati, the datasets, the harness or the model configuration
expires the S00-GATE-02 seals and requires a new run.

Git: the repository was re-created from source-history.bundle on 2026-11-16 and is
usable. Publication to github.com/clebeson/quati was requested by the owner; check
`git remote -v` and `git status -sb` to see whether the push has happened.
