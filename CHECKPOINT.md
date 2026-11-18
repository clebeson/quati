# Quati implementation checkpoint

Implementation is authorized. Read docs/implementation/implementation_state.json first;
its revision, active task, phase and next_action are the only progress authority.
Do not trust historical PASS claims that are not backed by seal records.

Current slice: S01 (state revision 40). Slice S00 is PASS: four gates sealed on commit
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

## Latest resume checkpoint (2026-11-18, S01-T02 discovery)

Canonical revision 40 selects S01-T02 DISCOVER. S01-T01 is accepted only as a
local contribution (LOG-0064), not as a full module or S01 slice. All S01 gates
remain NOT_RUN. HEAD before this implementation checkpoint is 0b19427; inspect
Git for the actual resulting checkpoint commit and remote synchronization.

T01 delivery: docs/implementation/S01_T01_DELIVERY.md and
 evidence/S01/T01-2026-11-17/DELIVERY.json. Independent Sonnet reviews accepted
source, corrections, exact legacy assertion migration and optional-field cases.
Full deterministic run: 2285 passed, child exit 0; two supplemental public CLI
cases passed with unchanged production and all prior test files. Complementary
lanes: 56 passed, 10 explicit skips. Inventory 2353 = 2343 distinct passed + 10
skipped. All source/output hashes match. Aggregate coverage: domain and behavior
100% line/branch; overall 99.89% line / 99.79% branch; all package thresholds pass.
Both final validators passed. Repeated retests are not counted again.

Use coverage/aggregate, not the partial supplemental report. The supplemental
coverage startup reset its temporary directory; aggregation restored retained
full-run compressed data and the supplemental data on the same production code.
Both raw combined snapshots and earlier red outputs are retained. No process
remains paused. Earlier 28 legacy assertion failures and the 6-case forwarding
miss were corrected and independently retested; never rewrite those red records.

Delivered source: typed classification and advisory pure routing (not activated),
direct context serialization, receipt-coordinated process-only conversation
identity/revision. Public model strings are sanitized; hashes bind raw proposals.
No transcript persistence, worker, durable obligation or process-exit continuation.
Current changed S01 source remains NOT_RUN for real-model qualification (T04).
The nine live skips and missing setuptools wheel leg are not accepted provider,
OS or packaging proof. Preserve historical source-bound S00 seals.

Next: read the S01-T02 handoff and exact task JSON, PRD normative details/oracles,
contracts and transitive references before authoring T02 specifications/tests/code.
Only T01 is accepted. T02 source has not started. Known discovery questions to
resolve, not guess: M05 C4 excludes next_action=ask while its following paragraph
requires safe starts for that route without missing blocking fields; M05-FR-03
still names SQLite despite S01 ephemeral scope; the temporal catalog/time-zone,
request language, initial WorkSnapshot/CommunicationPlan, policy activation and
role-availability staging need exact consuming definitions. Confirm these against
all relevant sources, log specification bugs and fix them before code.

Owner requires exhaustive meaningful tests and continuous checkpoints; continue
in dependency order without unnecessary questions or stopping at a partial task.
Use Haiku runners and fresh bounded Sonnet independent audits sparingly. All
internal artifacts are English; product languages English/Portuguese; terminal first.
No production, merge, release or deployment is authorized.

State writes: scripts/checkpoint_execution.py only, revision CAS/journal.
Commit author and committer: clebeson <clebeson@users.noreply.github.com>.
PACKAGE_MANIFEST.json is stale and must remain untracked/out of commits.
Retained debt: LOG-0057 engineering helper; LOG-0061 foundation integration
preconditions, owned by T02/T03. Keep evidence immutable and honest about tiers.

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
