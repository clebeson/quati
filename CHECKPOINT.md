# Quati implementation checkpoint

Implementation is authorized. Read docs/implementation/implementation_state.json first;
its revision, active task, phase and next_action are the only progress authority.
Do not trust historical PASS claims that are not backed by seal records.

Current slice: S01 (state revision 34). Slice S00 is PASS: four gates sealed on commit
5063071 and accepted by the owner (governance/seals; LOG-0049, LOG-0050, LOG-0053).
Changing src/quati, contracts/, examples/, the gate datasets or tests/evals expires the
S00 live evidence; S01 work that touches them must plan its own requalification.
S01 starts at docs/implementation/SLICES/S01.md and its work packages, and carries the
debt listed in LOG-0049 and LOG-0052 (contract RequestContext fields, trace consistency,
directory-mode handling, consent words versus the social table).
Delegate by complexity: haiku for runs and mechanical sync, sonnet for specified fixes
and first-pass review, the large model only for final verdicts and design. Commit only
on the test runner's own exit status. Product languages: English and Portuguese only.

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

## Latest resume checkpoint (2026-11-17, S01-T01)

Canonical revision 34, S01-T01 TDD_RED. HEAD before this SDD checkpoint is c5ec5b0;
S00 acceptance and helper fixes are already pushed. S01 status is IN_PROGRESS,
all S01 gates remain NOT_RUN. No S01 runtime source or new tests exist yet.

Read docs/implementation/S01_RUNTIME_CONTRACT.md and S01_T01_DESIGN.md. They
resolve G1-G10 for T01's bounded foundation: typed ingress, pure policy building
block (not activated routing) and a constant-space process-only conversation
projection in the existing CLI chat use case. T02/T03 own the explicitly deferred
behavior; T04 owns full slice proof. No new port, worker, command or UI is implied.

Fresh Sonnet SDD review accepted with eight P2 corrections, incorporated before
TDD (docs/audit/S01_T01_SDD_REVIEW_2026-11-17.md; LOG-0058/0059). Haiku ran 55 L0
regressions and both validators with child exit zero. Evidence and input hashes:
`evidence/S01/T01-2026-11-17/`. This is specification proof only.

Next: root authors tests/unit/test_s01_t01.py and
 tests/integration/cli/test_s01_conversation.py (distinct basenames). Haiku must
record actual public-path red before runtime source. Use explicit command
boundaries with no standalone trailing dot. Then implement the declared seams,
run scoped regressions and coverage, obtain independent conformity/quality review,
and CAS-checkpoint again. Do not move to T02 before accepting T01 contribution.

Current runtime-boundary assets differ from the sealed S00 source. README now
states that old live qualification is historical and current S01 qualification
is NOT_RUN. Preserve immutable S00 seals; plan affected-path requalification at
S01-T04. Product languages remain English/Portuguese; internal artifacts English.

Retained helper debt: LOG-0057 (malformed non-PASS references fail without a
checkpoint but may have an untyped diagnostic; historical seal/event timestamp
inconsistency). No production, merge, release or deployment is authorized.

State writes: scripts/checkpoint_execution.py only, with revision CAS/journal.
Commit author and committer: clebeson <clebeson@users.noreply.github.com>.
PACKAGE_MANIFEST.json is stale and must remain untracked/out of commits.

## Earlier handoff (2026-11-16, historical)

Read this section first; it is a note, not an authority. The authority is
docs/implementation/implementation_state.json (revision 29) and docs/governance/LOG.md.

1. UNCOMMITTED ACCEPTANCE OF S00. The working tree holds the S00 acceptance (seal
   governance/seals/S00-SLICE_ACCEPTED-001.json, state revisions 28 and 29, LOG-0053,
   README and CHECKPOINT edits, the checkpoint helper extension with its tests, and the
   journal events 28 and 29). HEAD is 9c8689d. The full-suite run that was to gate the
   commit was stopped at about 31% on purpose; it proved nothing. Do this first:
   `set -o pipefail; .venv/bin/python -m pytest -q -p no:cacheprovider; echo rc=$?`
   Commit and push to origin main only when pytest's own exit status is 0 and both
   `spec_tools/validate_spec.py` and `spec_tools/validate_readiness.py` pass. Use
   `git add -A && git reset -q PACKAGE_MANIFEST.json` (that file is stale and stays
   untracked), author `clebeson <clebeson@users.noreply.github.com>`. Never use the
   owner's personal email in commits or outside services.
2. S01 HAS NOT STARTED. Active work package S01-T01 (conversation envelope and intent
   reducer), phase DISCOVER. A discovery agent was started to write
   docs/implementation/S01_T01_DESIGN.md and was stopped before it wrote anything; no
   partial file exists. Redo it: read docs/implementation/SLICES/S01.md,
   docs/implementation/work_packages/S01.md, the S01-T01 entry of WORK_PACKAGES.json
   (owned IDs, local assertions, cases SOC-02, CAP-04, INT-01), the PRDs of M03, M04,
   M08 and M31, and the contracts InteractionDecision, RequestClassification and
   InteractionPort. List every specification gap and resolve it in the specification
   before any code (AGENTS.md rule 8).
3. DEPENDENCIES. The work-package DAG is a single chain S00-T05 -> S01-T01 -> T02 ->
   T03 -> T04 -> S02. The only real fork is S03 and S04, both after S02-T05. Parallelism
   inside a package: tests first (larger model), then implementers on disjoint paths,
   a runner, an independent reviewer. Whether S01-T02 and T03 may overlap is unchecked.
4. DEBT CARRIED INTO S01 (LOG-0049, LOG-0052): RequestContext in
   contracts/runtime-boundaries.schema.json requires `act` and `policy_version` (changing
   contracts changes the asset digest and expires the S00 live evidence); the trace
   consistency check misses four receipt edits; directory-mode handling differs between
   ask and probe and `fixture_sources` is unchecked; a refusal receipt is written on an
   unusable audit log; chat exit codes are inconsistent; a failed install leaves a staged
   fixture source; no command enables a STAGED fixture; consent words ("thanks",
   "obrigado", "tudo bem", "valeu") sit in the social table and matter for S02 approvals;
   the key-shape allowlist decision is open.
5. OWNER RULES THAT STAND: economy with quality, so pass `model: haiku` or `sonnet`
   explicitly on every delegated task (large model only for final verdicts and design);
   product languages English and Portuguese only; terminal first, no UI; artifacts in
   English, replies to the owner in Portuguese; do not stop to ask, decide and record in
   LOG.md; no production access, merge, release or deployment.
6. S00 RECORDED LIMITS (do not overstate S00): CAP-02 had a single eligible candidate;
   2 of 60 passes needed one continuation; paraphrases were reused during prompt
   iteration and held-out sets exist but were not run; the SOC-01 timeout leg was not run
   live; policy-gate denial is proven by test on the composed gate, not live; the
   fresh-wheel leg is skipped in the suite (no setuptools).
