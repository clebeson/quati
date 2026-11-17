# S01-T01 discovery checkpoint

Status: DISCOVER; not specification-ready and no S01 source implemented.
Canonical progress remains `implementation_state.json`.

## Scope and authoritative inputs

Read: README, IMPLEMENTATION_READY_INDEX, project structure, delivery governance,
persistent-state protocol, parallel model roles, S01 slice and handoff, the
S01-T01 task in WORK_PACKAGES, PRDs M03/M04/M08/M31, PRD_COMMON, DECISION_RULES,
InteractionPort, TYPE_CATALOG, classification/interaction schemas, the three
acceptance cases, test engineering rules and legacy DEC-001/LESSON-001.
The S00 debt is recorded in LOG-0049/LOG-0052 and CHECKPOINT.

Dependency chain: S00-T05 -> S01-T01 -> S01-T02 -> S01-T03 -> S01-T04.
T02/T03 cannot overlap under the current DAG. T01 is single-owner by default.

T01 owns domain/application foundation and unit tests. Its exact assertions are
S01-T01-A01 (separate intent/risk/complexity), A02 (model text grants no authority)
and A03 (explicit non-durable lifetime). SOC-02, CAP-04 and INT-01 are
CONTRIBUTION_ONLY here; S01-T04 owns their real-model full proof. T01 has no
owned_requirement_plan_ids or final_acceptance_plan_ids; related IDs are not
completed requirements. Full module tables must not silently expand this task.

## Reusable source and limits

- `application/context_envelope.py`: existing immutable envelope and protected
  segment/trimming logic; reuse rather than introduce a competing envelope.
- `application/ask.py`: current schema-bound classification ladder and provider
  budgets, but no complete S01 routing reducer.
- `domain/decision_policy.py` and `behavior/trusted_config.py`: existing sidecar
  validation and digest; consume validated policy rather than duplicate it.
- `domain/canonical.py`: canonical JSON and hashes.
- `application/identity.py`: trusted RequestContext. Its act/policy_version
  contract mismatch remains open; never derive identity from model text.
- `cli/chat.py`: S00 intentionally builds a service per turn and keeps no history.
  `LocalIdentity` mints a fresh authentication session per turn. Neither gives a
  stable conversation identity for S01 without explicit composition work.

## Specification gaps to resolve before source

| ID | Gap | Required resolution |
|---|---|---|
| G1 | The S01 handoff still says SPECIFICATION_ONLY, contrary to canonical authorization. | Update the stale handoff to defer to canonical state. |
| G2 | S01 oracles name SQLite/CommitmentLedger but the slice explicitly has only in-process state until S02. | Define the S01 equivalents and keep real durability proof in S02; do not count an in-memory fake as ledger proof. |
| G3 | Public CLI acceptance is required but T01/T02 owned paths omit CLI composition and integration tests. | Assign the exact wiring and public-path test ownership without introducing a new CLI surface. |
| G4 | WorkSnapshot exists in TYPE_CATALOG but state/binding/revision semantics and prototype work identity need executable precision. | Specify ephemeral conversation ownership, expected conversation versus work revision, and unavailable event types for this package. |
| G5 | InteractionPort.apply lacks a conversation locator and idempotency input; RequestContext.session_id changes per authenticated turn. | Specify trusted conversation binding and replay body/key scope without treating text or a model reference as authority. |
| G6 | M03 consumes M05/M06 verdicts before their S01 tasks and later modules exist. | Specify the bounded T01 input contract and fail-closed unavailable decisions; do not invent timers, outcomes or delivery acknowledgements. |
| G7 | M03's totality oracle forbids D0 for every enum tuple although its table leaves valid-vocabulary combinations unmatched. | Define valid cross-field combinations or correct the exhaustive oracle before implementation. |
| G8 | M04's social/simple-answer negative conflicts with unconditional candidate scoring when a title matches. | Specify the intent guard before candidate retrieval/scoring. |
| G9 | S00 never displays model-authored answers; S01 SOC-02/CAP-04 require direct answers. | Define the S01 ANSWER boundary, output validation and evidence without weakening progress/completion guards. |
| G10 | RequestContext act/policy_version schema mismatch is carried explicitly from S00. | Choose and document the contract-compatible representation; any asset change invalidates applicable S00 live evidence. |

Gaps are discovery findings, not silently adopted design decisions. Resolve only
the obligations consumed by T01, with explicit follow-up ownership for later
ones. Consult transitive references as needed and record the visited scope.

## Next actions

First finish the S00 acceptance commit validation and correct acceptance helper
findings H1-H3 in the independent review. Then finalize this design and amend the
specific normative documents before any S01 test or implementation. Tests are
written by the larger model, run by Haiku, and reviewed independently. Record red,
green, requirement portions, evidence digests and a revision-CAS checkpoint.
Only English and Portuguese product output is in scope. No UI, production,
external write, merge, release or deployment is authorized.
