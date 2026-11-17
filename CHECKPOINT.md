# Quati implementation checkpoint

Implementation is authorized. Read docs/implementation/implementation_state.json first;
its revision, active task, phase and next_action are the only progress authority.
Do not trust historical PASS claims that are not backed by seal records.

Current slice: S00. All four S00 gates are PASS at state revision 27, sealed on commit
5063071 (governance/seals/S00-GATES-*-002.json; LOG-0049, LOG-0050). Slice acceptance
(SLICE_ACCEPTED) is not issued yet: sync the specification debt of LOG-0048 first
(documents only). Do not change src/quati, contracts/, examples/, the gate datasets or
tests/evals without a new live run: that expires the seals. S01 starts after acceptance.
Delegate by complexity: haiku for runs and mechanical sync, sonnet for specified fixes
and first-pass review, the large model only for final verdicts and design.

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
