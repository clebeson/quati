# Quati implementation checkpoint

Implementation is authorized. Read docs/implementation/implementation_state.json first;
its revision, active task, phase and next_action are the only progress authority.
Do not trust historical PASS claims that are not backed by seal records.

Current slice: S00. No S00 gate is sealed. S00-GATE-02 was sealed at revision 16 on an
earlier code digest and is BLOCKED again since revision 18 (source changed). Three
independent audits (LOG-0039, LOG-0041, LOG-0044) drove fix rounds 6, 7 and 8. The live
requalification with the extended harness runs only after an independent audit says READY.
All four gates must be sealed on one commit, then SLICE_ACCEPTED. The S00-GATE-03 sentence
was amended by the owner (LOG-0043).

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
