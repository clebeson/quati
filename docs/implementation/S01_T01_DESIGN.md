# S01-T01 design

Status: SDD candidate, before runtime code and TDD red. Canonical progress is
implementation_state.json. Normative realization: S01_RUNTIME_CONTRACT.md.

## Scope

Deliver typed RequestContext/RequestClassification boundaries, a pure M08 policy
building block and an application-owned, constant-space conversation projection
through existing quati chat. T01 does not activate the policy or implement the
full InteractionPort. S00 dispatch guards remain until T02 consumes the new
policy. No new command, UI, transport, dependency, ledger or worker is introduced.

Local assertions S01-T01-A01/A02/A03 remain the exact completion conditions.
SOC-02, CAP-04 and INT-01 are CONTRIBUTION_ONLY; T04 owns their real-model proof.
No owned requirement plan or full module is completed by this package.

## Gap dispositions before source

| Gap | Resolution for T01 | Later owner / source |
|---|---|---|
| G1 stale authorization | Handoff now defers to canonical authority. | work_packages/S01.md |
| G2 SQLite before S02 | S01 prototype work semantics explicitly separated from real S02 ledger proof; T01 creates no work. | M03/M04; runtime contract section 5; T02/T03 |
| G3 CLI ownership | T01 owns main.py composition and focused public chat tests; business projection stays in application. Existing chat/one-shot comparisons allow only declared metadata differences. | WORK_PACKAGES.json; M01 state rule |
| G4 work snapshot precision | T01 has only ConversationProjection (ID/owner/revision), not WorkSnapshot. Snapshot construction and later-module fields belong to T02/T03 before those implementations. | TYPE_CATALOG; runtime contract sections 4-5 |
| G5 conversation and idempotency binding | Conversation is application-owned, separate from authentication session_id. Future InteractionPort is instance-bound; request_id is its scoped key; conversation and work revisions are distinct. T01 promises no decision replay. | BOUNDARY_CONTRACTS; runtime contract section 5; T02/T03 |
| G6 missing M05/M06/M09 | No fabricated verdicts or placeholder decisions. Full port consumption explicitly scheduled to T02/T03. | M03/M08 staged realization |
| G7 impossible totality oracle | M03 Cartesian combinations may select fail-closed D0; every tuple still selects exactly one first-match row and every WAIT has a next contact. | M03-FR-02 oracle; T02 |
| G8 coincidental references | Social/simple_answer return NO_REFERENCE before retrieval/scoring, without changing classification. | M04 normative detail and DECISION_RULES section 4; T02 |
| G9 model ANSWER boundary | S00 text boundary retained through T01; bounded direct ANSWER is T02 and full L3 proof T04. | runtime contract section 6 |
| G10 RequestContext mismatch | Wire retains required fields; direct act=null; policy_version may be null without granting authority. Typed serializer adds direct act and JSON arrays. | runtime-boundaries schema; TYPE_CATALOG |

These are resolved T01 boundaries, not claims that the deferred behaviors exist.
Read M05/M06/M09 and their transitive references before T02/T03 consume them.

## Structure and seams

Reuse canonical JSON/digest in domain/canonical.py, Refusal for typed failures,
existing DecisionPolicy loader/hash, existing Provider structured-output ladder,
and CLIService._record for the receipt/output-hash transaction boundary.

New domain classification module: immutable contract value, schema-equivalent
validation/serialization, fail-closed factory and pure route/role/priority reducer.
No I/O or vendor/schema-library dependency. Policy input is loaded/validated;
reducer output is advisory and dispatches nothing.

New domain conversation module: immutable owner/ID/revision projection and pure
expected-revision advance. New application ConversationSession coordinates owner
admission, prepared metadata and commit after receipt success. It stores no
transcript, credentials or jobs. Production IDs reuse composition.random_ids;
tests inject a seeded generator. Main.chat constructs one session and passes it
to per-turn CLIService instances. Ask authenticates anew on every turn.

AskSession exposes the full schema-validated proposal (including required reason_code) with classification_stage=SCHEMA_VALIDATED; it is not the activated step-5 M08 output yet
and stores fail-closed classification after classifier failure. It does not change
the discovery tool loop or display model text. CLIService verifies conversation
ownership before effects, decorates response before computing output_hash, and
commits the revision after the sink returns. Receipt failure leaves revision
unchanged. The projection is single-owner/synchronous; work concurrency is T03.

## Test plan, before implementation

- tests/integration/cli/test_s01_conversation.py::test_a01: public CLI fake-provider classification satisfies the
  complete schema, with independently varied intent/risk/complexity; pure reducer
  exhaustively covers 1344 tuples, restrictive routes, effect floors, missing
  capability, roles and priority boundaries against fixed policy/clock.
- tests/integration/cli/test_s01_conversation.py::test_a02: hostile model extra privilege/identity fields exhaust
  the real structured-output ladder, publish fail-closed classification and cause
  zero discovery effects; untrusted text never alters authenticated conversation
  owner. State projection rejects another tenant/actor and stale revisions.
- tests/integration/cli/test_s01_conversation.py::test_a03: public quati chat keeps one opaque ID, increments only
  receipted ask turns and explicitly reports PROCESS_ONLY/no continuation after
  exit; one-shot requests have no conversation metadata. Verify output_hash and
  zero durable job/commitment claims.
- Unit lane tests/unit/test_s01_t01.py covers the typed values, pure reducer and revision/owner guards; integration/cli/test_s01_conversation.py owns all public CLI assertions A01-A03 and the receipt failure path.
- Fault: injected ReceiptNotWritten leaves projection unchanged; M01 maps exit 1 / receipt_not_written / operation_may_have_taken_effect=true with no conversation metadata, and chat ends before the next line. A retried application turn uses the unchanged revision. Authentication/owner failures cannot bind/advance the session; owner mismatch writes no receipt and performs no effects.
- Policy-boundary tests: null context policy version plus missing trusted policy denies; forged context versions do not change decisions; EffectIntent uses only its trusted version argument. Direct act serializes null. Full audit act_chain emission belongs to S02; T01 does not invent it.
- Assert that pure reducer recommendations do not alter current dispatch before T02 activation; expose SCHEMA_VALIDATED versus FAIL_CLOSED stages explicitly.
- Remaining M08 oracle responsibilities, reachable D0 checks and ModelResult construction are assigned in the runtime contract to T02/T03/T04.
- Schema equivalence: required/extra keys, booleans, all vocabularies, optional
  fields, confidence boundaries/nonfinite inputs and direct context serialization.
- Existing chat framing/injection and equivalent one-shot content assertions stay;
  add only the normative S01 metadata normalization and verify it independently.

Root (larger model) authors tests before source. Haiku runs explicit test-file
commands with record_evidence.py, no trailing standalone dot. Independent Sonnet
review checks conformity/quality and chooses a fresh adversarial negative. Source
checks use ripwire change-check and quality-delta. Domain/behavior coverage is
100% line/branch, overall thresholds unchanged. Record all missing/failed proof.

## Discovery scope and evidence plan

Visited: AGENTS, README, canonical state/checkpoint, implementation-ready index,
project layout, governance/state/model-role documents, S01 slice/task/DAG, PRDs
M01/M02/M03/M04/M08/M31, PRD_COMMON, DECISION_RULES, TYPE_CATALOG,
BOUNDARY_CONTRACTS, runtime/classification/interaction schemas, test engineering
standard, three acceptance cases, existing CLI/ask/context/composition seams and
LOG-0049 through LOG-0057. Earlier legacy DEC-001/LESSON-001 are historical inputs;
LOG-0004 supersedes specification-only authority. No provider or production access.

Changing runtime source/assets expires old live-digest reuse on the current tree.
Preserve historical S00 seals; mark current S01 live qualification NOT_RUN. T04
must requalify affected old paths plus its ERI cases on the current snapshot.
T01 accepts only its deterministic contribution, not S01 gate PASS.

Rollback: revert the package source/config changes, retain immutable evidence and
journal history. No durable product data migration or external effect exists here.
