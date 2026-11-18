# Quati implementation checkpoint

Implementation is authorized. Read docs/implementation/implementation_state.json first;
its revision, active task, phase and next_action are the only progress authority.
Do not trust historical PASS claims that are not backed by seal records.

Current slice: S01 (state revision 43). Slice S00 is PASS: four gates sealed on commit
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

## Latest resume checkpoint (2026-11-18, S01-T02 SDD ready)

Canonical revision 43 selects S01-T02 SDD. S01-T01 is accepted/pushed at 8706018
as a local contribution only; all S01 gates remain NOT_RUN. No T02 source/tests
exist yet. Read S01_T02_RUNTIME_CONTRACT.md and S01_T02_DESIGN.md before tests.
Independent Sonnet SDD FINAL verdict SPEC_READY; earlier two NEEDS_CORRECTION
reports are preserved. Both final validators and 56 selected regressions exit 0
(evidence/S01/T02-2026-11-18/sdd-final). Frozen sdd_ready_snapshot.json binds inputs.
E1 reason follows canonical M03 DEPENDENCY_UNAVAILABLE; dependency_error is separate.

Next action: root authors discriminating tests, Haiku runs genuine red, then source
implementation and independent conformity/quality audit. Start with M05 pure
clarification and raw provider attempt/deadline budgets, then M04 locale/scoring,
M03 exact first-match table, receipt-coordinated aggregate/replay and public CLI.
A01-A03 are descriptive functions in tests/integration/test_clarify_cli.py; do not
create duplicate wrappers. No full requirement plan is owned by T02; T04 full L3
proof and T03 follow-up/fallback stay required. SDD is not implementation proof.

T02: explicit decision sidecar install/hash, real normalized policy pass, two
unpublished M05 phases with per-DiscoveryTurn deny-only invocation veto, actual
read observations retained on late veto. No unchecked model prose displayed.
Social preflight is typed/code-owned. Default provider is fixed, not EVALUATED;
missing strong role blocks. D7 mutation unavailable until T03; D6 status remains
usable. Existing S01 read-only effect ceiling is mandatory. One immutable session
aggregate publishes only after receipt acknowledgement; exact replay reuses its
original receipt/revision and checks current access before disclosure. Quotas
1000 turns/20 works never silently evict keys. Nothing survives process exit.

T01 proof: docs/implementation/S01_T01_DELIVERY.md and evidence/S01/T01-2026-11-17/DELIVERY.json.
2343 distinct passed + 10 explicit skips = 2353 inventory. Aggregate coverage:
domain/behavior 100% line/branch; overall 99.89% line/99.79% branch. Both validators
passed. Nine live skips and one missing-build-backend packaging skip remain
unverified, not provider/OS/production proof. Historical S00 seals stay immutable.

Owner: continue sequentially without unnecessary questions; meaningful exhaustive
coverage and durable checkpoints. Use economical Haiku runners / Sonnet reviews.
Internal artifacts English; product English/Portuguese; owner replies Portuguese.
No production, live writes, merge, release or deployment. State writes only through
scripts/checkpoint_execution.py with revision CAS. Git author/committer must be
clebeson <clebeson@users.noreply.github.com>. Never commit stale PACKAGE_MANIFEST.json.
Retained debts LOG-0049/0052/0057/0061 remain owned by their tasks, not silently closed.

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
