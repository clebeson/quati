# Guard predicates and transition actions for the v2 commitment lifecycle

Status: NORMATIVE for S02-T01 (reducer) and every later consumer of
`contracts/commitment-control-v2.json`. Machine-readable registry:
`contracts/guard-registry.json`. `spec_tools/validate_readiness.py` requires the
guard and action name sets of the control table and of the registry to be equal.

## 1. Scope and v1/v2 relationship

- **v2** (`contracts/commitment-control-v2.json`, its CSV view
  `CONTROL_TRANSITIONS.csv`, and `contracts/commitment-v2.schema.json`) is the only
  lifecycle allowed for accepted durable commitments. This document defines every
  guard and action that the v2 table names. S02-T01 implements the reducer against
  this table; it does not produce a new table.
- **v1** (`contracts/commitment.schema.json`, `examples/statecharts/commitment.yaml`,
  and the v1 `GUARDS`/`ACTIONS` sets in `spec_tools/behavior_compiler.py`) is a
  legacy compiler fixture for the L0 behavior compiler and its tests. It is never
  activated for an accepted durable obligation, and no definition here applies to it.
- The table issues found while writing this document are listed in section 9 with
  their resolution. The table has 15 states and 56 transitions.

## 2. Purity rule (testable)

**R-PURE.** A guard is a pure function `guard(GuardInput) -> GuardResult`. The same
input always gives the same output. A guard reads no clock, database, network, file,
environment variable or random source, and does not change its input. Actions are
pure too: `action(GuardInput) -> TransitionRecord`. They describe the records to
write (*record intent*) and perform none of the writes.

The reducer is `next_state(input) -> Accepted(TransitionRecord) | Denied(GuardResult)`.
The application layer commits the result in one ledger transaction (section 5).

Three mandatory unit tests enforce R-PURE:

1. **PURE-01, imports.** The guard and action modules under `src/quati/domain/` import
   only the Python standard library modules `dataclasses`, `datetime` (types only),
   `decimal`, `enum`, `hashlib`, `json` and `typing`, plus `quati.domain`. A static
   import test fails on any other import.
2. **PURE-02, no clock and no I/O.** During evaluation, `datetime.datetime.now`,
   `datetime.datetime.utcnow`, `time.time`, `time.monotonic`, `builtins.open`,
   `random.random` and `socket.socket` are patched to raise. Every guard and action
   is evaluated on every row fixture, and none may raise.
3. **PURE-03, determinism.** For every row fixture, two evaluations on deep copies of
   the input return equal results, and the original input is still deep-equal to
   its copy.

`GuardResult = {allowed: bool, reason_code: ErrorCode-or-null, failed_clause: str-or-null}`.
- `reason_code` is null exactly when `allowed` is true. Otherwise it is the guard's
  registry `denial_reason_code`, or the code of the universal precondition that failed.
- `failed_clause` is the clause ID of the first false clause, for example `G05.c2`.
  It goes to the audit trail. Tests assert the clause ID, not free text.

## 3. Guard input (`GuardInput`)

The application layer loads all facts **before** evaluation, from one committed
ledger snapshot. Short names used in the predicates are given in brackets.

| Field | Type | Source |
|---|---|---|
| `commitment` [`c`] | Commitment v2 (`commitment-v2.schema.json`) | committed ledger row |
| `snapshot_committed` | bool | true iff `c` was read from a committed row in the current ledger transaction |
| `event` [`ev`] | GuardEvent: `{name: control event enum, envelope: EventEnvelope, expected_revision: Revision, payload: typed per event (section 3.1)}` | caller; `event-envelope.schema.json` (`expected_revision`, `$defs/ControlEventPayload`) |
| `context` [`ctx`] | RequestContext (`runtime-boundaries.schema.json#/$defs/RequestContext`) | identity layer |
| `token_revoked` | bool | identity port, evaluated for `ctx.token_jti` |
| `now` | Timestamp (UTC) | `Clock.now()`, called exactly once per evaluation (section 6) |
| `active_policy_version` [`apv`] | Digest-or-null | policy store; null means no current policy |
| `policy_decision` [`pd`] | PolicyDecision-or-null (TYPE_CATALOG) | RFC-014 evaluation of this transition's intent |
| `approval` [`ap`] | ApprovalRequest-or-null (`approval-request.schema.json`) | approval store |
| `effects` [`E`] | list[EffectRecord] (`runtime-boundaries.schema.json#/$defs/EffectRecord`) = EffectIntent plus `status`, `dispatch_stopped_at`, `lease_expires_at` | effect ledger rows where `effect_id ∈ c.effect_intent_refs` |
| `attempts` [`A`] | list[DeliveryAttempt] (TYPE_CATALOG) | rows where `attempt_id ∈ c.delivery_attempt_refs`, plus attempts for the current delivery not yet referenced |
| `delivery` [`d`] | DeliveryIntent-or-null (TYPE_CATALOG) | the current delivery for `c.goal_revision` |
| `assessment` [`oa`] | OutcomeAssessment-or-null (`outcome-assessment.schema.json`), including `assessor_actor_id` | assessment store |
| `candidate_producer_actor_id` | str-or-null | the actor that recorded the candidate (CandidateOutcome `producer_actor_id`, TYPE_CATALOG) |
| `evidence` [`EV`] | list[EvidenceRef] (TYPE_CATALOG) | resolved `c.evidence_refs` |
| `classification` [`rc`] | RequestClassification-or-null | classification store |
| `budget` [`b`] | Budget (TYPE_CATALOG), effective values from section 7 | configuration plus any per-commitment budget |
| `usage` [`u`] | CommitmentUsage (`runtime-boundaries.schema.json#/$defs/CommitmentUsage`): `{requests:int, tool_calls:int, output_tokens:int, cost_usd: decimal-string-or-null}`, cumulative for the commitment | ledger aggregation |
| `config` [`cfg`] | DecisionPolicy (`decision-policy.schema.json`) and the control table `budget` object [`tb`] | configuration store |

The effect ledger status vocabulary (`EffectRecord.status`) is:
- `COMMITTED`: the intent and its outbox row are committed, and no worker has claimed them.
- `CLAIMED`: `claim_dispatch` has committed, so a worker may have called the provider.
- `UNCERTAIN`: the outcome is unknown after a lost response or a timeout.
- `CONFIRMED`: an authenticated provider receipt proves the effect.
- `CONFIRMED_ABSENT`: there is proof that no effect happened, either a provider receipt or "never claimed and dispatch stopped".

`dispatch_stopped(e) := e.dispatch_stopped_at ≠ null ∧ (e.lease_expires_at = null ∨ e.lease_expires_at ≤ now)`.

The aggregate `c.effect_state` must equal `effect_state(E)`, and each case below is
checked in this order:

1. `E = ∅` gives `NONE`.
2. Any `e.status = UNCERTAIN` gives `UNCERTAIN`.
3. Any `e.status ∈ {COMMITTED, CLAIMED}` gives `PENDING`.
4. Any `e.status = CONFIRMED` gives `CONFIRMED`.
5. Otherwise the result is `CONFIRMED_ABSENT`.

The reducer rejects a snapshot that breaks this rule with `INTERNAL_ERROR` before
any guard runs.

### 3.1 Event payloads

The payloads are defined in `event-envelope.schema.json#/$defs/ControlEventPayload`.

| Event | `ev.payload` fields |
|---|---|
| `blocking_question` | `missing_fields: list[str]`, `candidate_scores: list[number 0..1]`, `question_ref: str` |
| `feedback` | `goal_revision_seen: Revision`, `new_goal: str-or-null`, `answered_question_ref: str` |
| `goal_revision` | `goal_revision_seen: Revision`, `new_goal: str` (non-empty) |
| `dispatch` | `effect_id: str` |
| `acknowledged`, `confirmed_delivered`, `confirmed_no_effect`, `confirmed_no_effect_exhausted` | `attempt_id: str` |
| `resume_execution`, `resume_delivery`, `resume_reconciliation`, `resume_cancellation`, `resume_acceptance` | `resolves_block_reason: str`, `new_deadline_at: Timestamp` |
| `candidate` | `candidate_ref: ScopedRef`, `evidence_refs: list[str]` |
| all other events | empty object |

### 3.2 Shared helper predicates

- `eff_reinv := min(tb.max_reinvestigations, cfg.behavior_policy.reinvestigation_budget, b.max_reinvestigations if present)`.
  This is the only definition of the reinvestigation limit. The control table value
  is the ceiling and the policy value may only lower it (M09). Every guard, action and
  test uses `eff_reinv` and never reads one of the three sources directly.
- `tx_ok := c.transition_count + 1 ≤ b.max_transitions`
- `fresh(EV) := ∀ r ∈ EV: now − r.observed_at ≤ cfg.behavior_policy.max_evidence_age_s.default seconds`
- `assessment_current := oa ≠ null ∧ oa.commitment_id = c.id ∧ oa.goal_revision = c.goal_revision`
- `independent := oa.assessor_actor_id ≠ null ∧ candidate_producer_actor_id ≠ null ∧ oa.assessor_actor_id ≠ candidate_producer_actor_id`
- `cur_effects := [e ∈ E : e.effect_id ∈ c.effect_intent_refs]`
- `receipt_ok(a, e) := a.provider_receipt_ref ≠ null ∧ a.provider_receipt_ref.source_ref.tenant_id = c.tenant_id ∧ a.provider_receipt_ref.source_ref.id = e.binding_id`
- `ambiguous(s) := |s| ≥ 2 ∧ s₁ ≥ cfg.routing_policy.min_candidate_score ∧ s₁ − s₂ ≤ cfg.routing_policy.ambiguity_margin`, where `s₁ ≥ s₂` are the two highest scores.

## 4. Universal preconditions and evaluation order

Event class is a function of `ev.name`:

| Class | Events |
|---|---|
| WORK | classified, accepted, start, progress, blocking_question, feedback, goal_revision, candidate, `insufficient`, `sufficient` (control-table event names), partial, dispatch |
| RESUME | resume_execution, resume_delivery, resume_reconciliation, resume_cancellation, resume_acceptance |
| REALITY | acknowledged, response_lost, confirmed_delivered, confirmed_no_effect, confirmed_no_effect_exhausted, no_effects, known_effects, unknown_effects |
| CANCEL | cancel_requested |
| TIMEOUT | deadline, budget_exhausted |

The reducer evaluates the following in this exact order and stops at the first
false item. Each item returns its code.

| ID | Applies to | Predicate | Code on false |
|---|---|---|---|
| U0 | all | `c.state ∉ table.terminal` and exactly one row with `(source = c.state, event = ev.name)` exists | `UNSUPPORTED` |
| U1 | all | `c` validates against commitment-v2, `c.control_policy_version = "2.0.0"` and `effect_state(E) = c.effect_state` | `INVALID_INPUT` (version mismatch: `UNSUPPORTED`; aggregate mismatch: `INTERNAL_ERROR`) |
| U2 | all | `ctx` validates as RequestContext, `ctx.authenticated_origin_ref ≠ ""` and `token_revoked = false` | `UNAUTHENTICATED` |
| U3 | all | `ctx.tenant_id = c.tenant_id`, `ev.envelope.tenant_id = c.tenant_id` and `ev.envelope.commitment_id = c.id` | `FORBIDDEN` |
| U4 | all | `ev.expected_revision = c.revision` (CAS precheck) | `REVISION_CONFLICT` |
| U5 | all | `apv ≠ null` (K6 fail closed) | `TEMPORARILY_UNAVAILABLE` |
| U5b | all | `ctx.policy_version = apv` | `FORBIDDEN` |
| U6 | `ev.name = deadline` | `now ≥ c.deadline_at` | `INVALID_INPUT` |
| U7 | WORK | `now < c.deadline_at` | `DEADLINE_EXCEEDED` |
| U8 | WORK, RESUME | `tx_ok` | `BUDGET_EXCEEDED` |
| PA | guards whose registry `inputs` contain `policy_decision` | P-AUTHZ (below) | `FORBIDDEN` / `APPROVAL_REQUIRED` |
| G | the row guard | section 5 | the guard's `denial_reason_code` |
| AV | the row action | the action's required inputs are non-null and valid | `INVALID_INPUT` |

**P-AUTHZ** holds when all of the following are true:
- `pd ≠ null`;
- `pd.policy_version = apv`;
- `pd.intent_digest = intent_digest(c, ev)`;
- `now < pd.valid_until`;
- either `pd.verdict = ALLOW`, or `pd.verdict = APPROVAL_REQUIRED ∧ approval_ok`.

`approval_ok` holds when all of the following are true:
- `ap ≠ null` and `ap.state = APPROVED`;
- `ap.revocation = null`;
- `now < ap.expires_at`;
- `ap.binding.input_digest` and `ap.binding.policy_version` equal the digests that `pd` binds;
- `ap.consumed_at = null`.

Failure codes:
- `APPROVAL_REQUIRED` when `pd.verdict = APPROVAL_REQUIRED ∧ ¬approval_ok`;
- `FORBIDDEN` in every other false case.

`intent_digest(c, ev)` is the PolicyDecision intent digest (RFC-014) computed:
- over the EffectIntent `e` with `e.effect_id = ev.payload.effect_id` for the `dispatch` row;
- over `{commitment_id, tenant_id, source: c.state, event: ev.name, expected_revision, goal_revision}` for every other row.

WORK, RESUME, REALITY and CANCEL rows are exempt from some preconditions:
- REALITY, CANCEL and TIMEOUT rows are exempt from U7 and U8. A provider receipt,
  a reconciliation fact, a cancellation or a timeout must always be recordable,
  including after the deadline or budget is exhausted. They still increment
  `transition_count`.
- RESUME rows are exempt from U7 only, because their payload carries the new deadline.

**Decided rules.** The following four rules are decided and binding:
1. *Exemptions.* REALITY, CANCEL and TIMEOUT rows skip U7 and U8. RESUME rows skip
   U7 only. WORK rows skip neither.
2. *Transition budget.* A block with `block_reason = "BUDGET_EXHAUSTED.transitions"`
   is not resumable in v2. U8 or G19.c4 denies every RESUME row, and the only exits
   are `cancel_requested` and the `deadline` escalation.
3. *Intent digest.* For every transition other than `dispatch`, the P-AUTHZ intent
   digest is the digest of `{commitment_id, tenant_id, source, event,
   expected_revision, goal_revision}`.
4. *Notices.* Status, question and escalation notices are `outbox` rows. They are
   not tracked in `c.effect_intent_refs` (section 6).

**Conflict rule.** The validator guarantees that one `(state, event)` pair has at most
one row, so at most one guard applies to an event. When a producer holds several
candidate events for one snapshot, it submits them in this order:
1. REALITY;
2. CANCEL;
3. `deadline`;
4. `budget_exhausted`;
5. RESUME;
6. WORK.

Ties are broken by ledger event sequence, and then by `event_id` in lexicographic
order. After the first commit, every other candidate has a stale
`expected_revision` and gets `REVISION_CONFLICT`. The producer reloads the snapshot
and decides again. It never replays a stale event. For example, a receipt that
arrives with the deadline produces DELIVERED and not EFFECT_UNCERTAIN.

Within one state, the guards over the same facts are mutually exclusive. There are
three such groups:
- In `CANCEL_REQUESTED` and `NEEDS_RECONCILIATION`, G01, G02 and G03 partition
  every case in which `∀e: dispatch_stopped(e) ∨ e.status ∈ {CLAIMED, UNCERTAIN}`.
- In `EVIDENCE_REVIEW`, G22, G15 and G14 are separated by `oa.verdict`.
- In `EFFECT_UNCERTAIN`, G21 and G25 are separated by the delivery attempt count (G21.c3 and G25.c2).

## 5. Guards

**Shared fixture.** Every guard test starts from the fixture `FX` below and changes
only what the test case names:
- `now = 2026-01-01T00:00:00Z`;
- `c.revision = 5`, `ev.expected_revision = 5`;
- `c.deadline_at = now + 3600 s`, `c.transition_count = 2`, `c.reinvestigation_count = 0`, `c.goal_revision = 1`;
- `b.max_transitions = 120`, `eff_reinv = 2`;
- `pd = ALLOW` with `valid_until = now + 60 s`;
- `cfg` = `examples/behavior/decision-policy.json`.

In each test list, T is the true case, F the false cases (one per clause) and B the
boundary cases. Every case is evaluated on the guard alone and through the full
reducer.

**G01 `all_effects_confirmed_absent_and_dispatch_stopped`**
- Rows: CANCEL_REQUESTED|no_effects and NEEDS_RECONCILIATION|no_effects.
- Code: `EFFECT_UNCERTAIN`.
- Predicate: `c1: ∀ e ∈ cur_effects: e.status ∈ {COMMITTED, CONFIRMED_ABSENT}` and `c2: ∀ e ∈ cur_effects: dispatch_stopped(e)`.
- Tests:
  - T: one effect, `CONFIRMED_ABSENT`, stopped.
  - F (c1): one effect `CLAIMED`.
  - F (c2): one effect `COMMITTED` with `dispatch_stopped_at = null`.
  - B: `E = ∅` gives true.
  - B: `lease_expires_at = now` gives true, `now + 1 µs` gives false.

**G02 `all_effects_reconciled_and_dispatch_stopped`**
- Rows: CANCEL_REQUESTED|known_effects and NEEDS_RECONCILIATION|known_effects.
- Code: `EFFECT_UNCERTAIN`.
- Predicate:
  - `c1: ∀ e ∈ cur_effects: e.status ∈ {COMMITTED, CONFIRMED, CONFIRMED_ABSENT}`
  - `c2: ∀ e: dispatch_stopped(e)`
  - `c3: ∃ e: e.status = CONFIRMED`
  - `c4: ∀ e with status CONFIRMED: ∃ a ∈ A: a.status = ACKNOWLEDGED ∧ receipt_ok(a, e)`
- Tests:
  - T: one `CONFIRMED` effect with a receipt, stopped.
  - F (c1): one `UNCERTAIN`.
  - F (c2): not stopped.
  - F (c3): all `CONFIRMED_ABSENT`.
  - F (c4): `CONFIRMED` without `provider_receipt_ref`.
  - B: one `CONFIRMED` plus one `CONFIRMED_ABSENT` gives true.

**G03 `any_effect_unknown`**
- Row: CANCEL_REQUESTED|unknown_effects.
- Code: `INVALID_INPUT`.
- Predicate: `c1: ∃ e ∈ cur_effects: e.status ∈ {CLAIMED, UNCERTAIN}`.
- Tests:
  - T: one `UNCERTAIN`.
  - F: all `CONFIRMED`.
  - B: `CLAIMED` with an expired lease and no attempt gives true; a crash after the provider call cannot be excluded.

**G04 `authenticated_current_delivery_receipt`**
- Rows: SEND_PENDING|acknowledged and EFFECT_UNCERTAIN|confirmed_delivered.
- Code: `EVIDENCE_INSUFFICIENT`.
- Let `a` be the attempt with `attempt_id = ev.payload.attempt_id`.
- Predicate:
  - `c1: a ≠ null ∧ a.status = ACKNOWLEDGED`
  - `c2: d ≠ null ∧ a.delivery_ref.id = d.delivery_id ∧ d.goal_revision = c.goal_revision`
  - `c3: d.effect_intent.effect_id ∈ c.effect_intent_refs ∧ receipt_ok(a, d.effect_intent)`
  - `c4: ctx.principal_kind = SERVICE`
- Tests:
  - T: current receipt.
  - F (c1): `SENT_UNCONFIRMED`.
  - F (c2): `d.goal_revision = 0`, which is a stale delivery.
  - F (c3): receipt source binding differs.
  - F (c4): `HUMAN` context.
  - B: the receipt arrives after `c.deadline_at` and is still accepted, because REALITY rows are exempt from U7.

**G05 `authenticated_request`**
- Row: RECEIVED|classified.
- Code: `UNAUTHENTICATED`.
- Predicate: `c1: ctx.actor_id = c.requester_id`, `c2: ctx.channel = c.channel` and `c3: ctx.principal_kind ∈ {HUMAN, AGENT, SERVICE}`.
- Tests:
  - T: the requester on the same channel.
  - F (c1): another actor.
  - F (c2): another channel.
  - B: `ctx.act` delegation chain of length 3 with `actor_id = requester` gives true; U2 already validated the chain.

**G06 `authorized_and_no_accepted_or_pending_effect`**
- Rows: RECEIVED or CLASSIFIED|cancel_requested.
- Code: `EFFECT_UNCERTAIN`; P-AUTHZ also applies.
- Predicate: `c1: E = ∅`, `c2: c.effect_intent_refs = []` and `c3: c.effect_state = NONE`.
- Tests:
  - T: no effects.
  - F (c1/c2): one `COMMITTED` effect.
  - F (PA): `pd.verdict = DENY` gives `FORBIDDEN`.
  - B: `pd.valid_until = now` gives `FORBIDDEN` (strict `<`).

**G07 `authorized_and_under_budget`**
- Row: ACKNOWLEDGED|start.
- Code: `BUDGET_EXCEEDED`; P-AUTHZ also applies.
- Predicate:
  - `c1: tx_ok`
  - `c2: u.requests < b.max_requests`
  - `c3: u.tool_calls ≤ b.max_tool_calls`
  - `c4: b.max_cost_usd = null ∨ (u.cost_usd ≠ null ∧ u.cost_usd < b.max_cost_usd)`
- Tests:
  - T: `FX`.
  - F (c2): `u.requests = b.max_requests`.
  - F (c4): `u.cost_usd = null` with a cap set (unknown pricing cannot prove the cap).
  - F (PA): `APPROVAL_REQUIRED` with no approval gives `APPROVAL_REQUIRED`.
  - B: `transition_count = 119` gives true and `120` gives false.

**G08 `authorized_current_cancel_request`**
- Rows: any accepted nonterminal state except CANCEL_REQUESTED and NEEDS_RECONCILIATION, with event cancel_requested.
- Code: `FORBIDDEN`; P-AUTHZ also applies.
- Predicate: `c1: ev.envelope.actor_id = ctx.actor_id`.
- Tests:
  - T: `FX`.
  - F (c1): the envelope actor differs from the authenticated actor.
  - F (PA): `pd.intent_digest` bound to `expected_revision = 4`.
  - B: `transition_count = 120` gives true, because CANCEL rows are exempt from U8.
  - B: `now > c.deadline_at` gives true, because CANCEL rows are exempt from U7.

**G09 `authorized_effect_intent_committed`**
- Row: READY_TO_DELIVER|dispatch.
- Code: `FORBIDDEN`; P-AUTHZ also applies, over the EffectIntent.
- Let `e` be the effect with `e.effect_id = ev.payload.effect_id`.
- Predicate:
  - `c1: e ∈ cur_effects ∧ e.status = COMMITTED ∧ e.dispatch_stopped_at = null`
  - `c2: e.tenant_id = c.tenant_id ∧ e.policy_version = apv`
  - `c3: d ≠ null ∧ d.effect_intent.effect_id = e.effect_id ∧ d.goal_revision = c.goal_revision`
  - `c4: c.assessed_goal_revision = c.goal_revision ∧ c.outcome_verdict ∈ {ACCEPT, PARTIAL}`
  - `c5: fresh(EV)`
- These clauses make up the RFC-014 §6.4 dispatch recheck, together with U2 (token not revoked) and U5b.
- Tests:
  - T: `FX` plus a committed effect.
  - F (c1): `CLAIMED`.
  - F (c2): `e.policy_version ≠ apv`.
  - F (c3): delivery for goal revision 0.
  - F (c4): `assessed_goal_revision = 0`.
  - F (c5): evidence `observed_at = now − 86401 s`.
  - F (PA): approval `consumed_at` set gives `APPROVAL_REQUIRED`.
  - B: evidence age exactly `86400 s` gives true.

**G10 `authorized_feedback_current_revision`**
- Rows: WAITING_INPUT|feedback, and EVIDENCE_REVIEW, READY_TO_DELIVER or SEND_PENDING|goal_revision.
- Code: `REVISION_CONFLICT`; P-AUTHZ also applies.
- Predicate: `c1: ev.payload.goal_revision_seen = c.goal_revision`.
- Tests:
  - T: `FX` with `goal_revision_seen = 1`.
  - F (c1): `goal_revision_seen = 0`.
  - F (PA): `pd = null` gives `FORBIDDEN`.
  - B: `new_goal ≠ null` still gives true; the action then increments `goal_revision`.
  - B: `goal_revision` in SEND_PENDING with `goal_revision_seen = 1` gives true. The
    target is CANCEL_REQUESTED, because a dispatch is in flight for the previous goal.

**G11 `budget_exhausted`**
- Rows: ACKNOWLEDGED, IN_PROGRESS, WAITING_INPUT, EVIDENCE_REVIEW or READY_TO_DELIVER|budget_exhausted.
- Code: `INVALID_INPUT`.
- Predicate: `c1: exhausted_dim ≠ null`.
- `exhausted_dim` is the first dimension that matches, checked in this order:
  1. `transitions` if `c.transition_count ≥ b.max_transitions`;
  2. `reinvestigations` if `c.state = EVIDENCE_REVIEW ∧ oa ≠ null ∧ oa.verdict = INVESTIGATE_MORE ∧ c.reinvestigation_count ≥ eff_reinv`;
  3. `requests` if `u.requests ≥ b.max_requests`;
  4. `tool_calls` if `u.tool_calls > b.max_tool_calls`;
  5. `cost` if `b.max_cost_usd ≠ null ∧ (u.cost_usd = null ∨ u.cost_usd ≥ b.max_cost_usd)`.
- Tests:
  - T: `transition_count = 120`.
  - T: reinvestigations, with `reinvestigation_count = 2` and verdict `INVESTIGATE_MORE`.
  - F: `FX`.
  - B: `transition_count = 119` gives false.
  - B: `reinvestigation_count = 2` with verdict `ACCEPT` gives false.
  - B: `c.state = WAITING_INPUT` with `u.requests = b.max_requests` gives true (`requests`).

**G12 `cancellation_not_yet_reconciled`**
- Row: CANCEL_REQUESTED|deadline.
- Code: `INVALID_INPUT`.
- Predicate: `c1: |cur_effects| ≥ 1`, `c2: ¬G01` and `c3: ¬G02`.
- Tests:
  - T: one `COMMITTED` effect that is not stopped.
  - F (c1): `E = ∅`. The NEEDS_RECONCILIATION schema requires an intent, so this row never applies to an empty effect list. The producer of `cancel_requested` emits `no_effects` in the same step when `E = ∅` (issue T4), and G01 is then true.
  - F (c2): all effects absent and stopped.
  - F (c3): reconciled.
  - B: `now = c.deadline_at` passes U6.

**G13 `critical_input_missing`**
- Row: IN_PROGRESS|blocking_question.
- Code: `INVALID_INPUT`.
- Predicate: `c1: (ev.payload.missing_fields ∩ cfg.behavior_policy.blocking_fields ≠ ∅) ∨ ambiguous(ev.payload.candidate_scores)`.
- `max_open_questions = 1` holds by construction: IN_PROGRESS has no open question.
- Tests:
  - T: `missing_fields = ["recipient"]`.
  - T: scores `[0.80, 0.70]`.
  - F: `missing_fields = ["tone"]` with scores `[0.9, 0.5]`.
  - B: scores `[0.65, 0.50]` (difference 0.15) give true.
  - B: scores `[0.49, 0.40]` give false, because the top score is below `min_candidate_score`.

**G14 `current_goal_evidenced_partial`**
- Row: EVIDENCE_REVIEW|partial.
- Code: `EVIDENCE_INSUFFICIENT`.
- Predicate:
  - `c1: assessment_current`
  - `c2: oa.verdict = PARTIAL`
  - `c3: |oa.evidence_refs| ≥ 1 ∧ |oa.gaps| ≥ 1`
  - `c4: independent`
  - `c5: fresh(EV)`
- Tests:
  - T: a current, independent PARTIAL assessment with one gap.
  - F (c1): `oa.goal_revision = 0`.
  - F (c2): `ACCEPT`.
  - F (c3): `gaps = []`.
  - F (c4): assessor equals producer.
  - F (c5): stale evidence.
  - B: evidence age of `86400 s` gives true.

**G15 `current_goal_independent_accept`**
- Row: `EVIDENCE_REVIEW|sufficient` (event name from the control table).
- Code: `EVIDENCE_INSUFFICIENT`.
- Predicate:
  - `c1: assessment_current`
  - `c2: oa.verdict = ACCEPT`
  - `c3: |oa.evidence_refs| ≥ 1 ∧ oa.gaps = []`
  - `c4: independent`
  - `c5: fresh(EV)`
- Tests:
  - T: a current, independent ACCEPT.
  - F (c1): stale `goal_revision` (invariant 6).
  - F (c2): `PARTIAL`.
  - F (c4): `assessor_actor_id = null`.
  - F (c5): `observed_at = now − 86401 s`.
  - B: `confidence = 0.0` gives true; confidence is not a guard input.

**G16 `deadline_elapsed`**
- Rows: all `deadline` rows to BLOCKED, and BLOCKED|deadline.
- Code: `INVALID_INPUT`.
- Predicate: `c1: now ≥ c.deadline_at`, the same clause as U6, kept as the row guard.
- Tests:
  - T: `now = deadline_at + 1 s`.
  - F: `now = deadline_at − 1 µs`.
  - B: `now = deadline_at` gives true.

**G17 `delivery_block_resolved_current_evidence`**
- Row: BLOCKED|resume_delivery.
- Code: `EVIDENCE_INSUFFICIENT`.
- Predicate:
  - `c1: c.blocked_from_state = READY_TO_DELIVER`
  - `c2: ev.payload.resolves_block_reason = c.block_reason ∧ ev.payload.new_deadline_at > now`
  - `c3: ∀ e ∈ cur_effects: e.status ∈ {COMMITTED, CONFIRMED_ABSENT}`
  - `c4: c.assessment_ref ≠ null ∧ c.assessed_goal_revision = c.goal_revision`
  - `c5: fresh(EV)`
- Tests:
  - T: a deadline block from READY_TO_DELIVER.
  - F (c1): `blocked_from_state = IN_PROGRESS`.
  - F (c2): `new_deadline_at = now`.
  - F (c3): `CLAIMED`.
  - F (c4): stale assessment.
  - F (c5): stale evidence.
  - B: `block_reason = "BUDGET_EXHAUSTED.transitions"` with `transition_count = 120` fails U8 and gives `BUDGET_EXCEEDED`.

**G18 `dispatch_may_have_occurred`**
- Rows: SEND_PENDING|response_lost and SEND_PENDING|deadline.
- Code: `INVALID_INPUT`.
- Predicate:
  - `c1: ∃ e ∈ cur_effects: e.status ∈ {CLAIMED, UNCERTAIN}`
  - `c2: ¬∃ a ∈ A: a.status = ACKNOWLEDGED ∧ receipt_ok(a, e)`
- Tests:
  - T: `CLAIMED` with no attempt.
  - F (c1): all `CONFIRMED_ABSENT`.
  - F (c2): an acknowledged receipt exists, so the producer must send `acknowledged`.
  - B: `CLAIMED` with an expired lease gives true (never a blind retry).

**G19 `execution_block_resolved_authorized_budget`**
- Row: BLOCKED|resume_execution.
- Code: `BUDGET_EXCEEDED`; P-AUTHZ also applies.
- Predicate:
  - `c1: c.blocked_from_state ∈ {ACKNOWLEDGED, IN_PROGRESS, WAITING_INPUT, EVIDENCE_REVIEW}`
  - `c2: ev.payload.resolves_block_reason = c.block_reason ∧ ev.payload.new_deadline_at > now`
  - `c3: c.effect_state ∈ {NONE, CONFIRMED_ABSENT}`
  - `c4: c.block_reason = DEADLINE_ELAPSED ∨ ¬(budget dimension named in c.block_reason is exhausted per G11)`
  - `c5: c.reinvestigation_count ≤ eff_reinv`
- Tests:
  - T: a deadline block from IN_PROGRESS.
  - F (c1): `RECEIVED` (acceptance must not be skipped; such a block resumes through `resume_acceptance`, G26).
  - F (c2): reason mismatch.
  - F (c3): `PENDING`.
  - F (c4): `BUDGET_EXHAUSTED.transitions` with count 119 passes U8 but the dimension is still exhausted. With a raised per-commitment `b.max_transitions` above 120, the effective minimum keeps it exhausted, so a transition block is not resumable in v2.
  - B: `new_deadline_at = now + 1 µs` gives true.

**G20 `ledger_acceptance_committed`**
- Row: CLASSIFIED|accepted.
- Code: `TEMPORARILY_UNAVAILABLE`.
- Predicate:
  - `c1: snapshot_committed = true`
  - `c2: rc ≠ null ∧ rc.commitment_ref = c.id`
  - `c3: c.responsible_actor_id ≠ "" ∧ c.next_action ≠ null ∧ c.deadline_at ≠ null`
- Tests:
  - T: `FX`.
  - F (c1): an uncommitted snapshot.
  - F (c2): `rc.commitment_ref = null` (for example `next_action = deny`).
  - F (c3): `next_action = null`.
  - B: `c.revision = 0` gives true; acceptance is the first update.

**G21 `provider_proves_no_effect_and_retry_budget`**
- Row: EFFECT_UNCERTAIN|confirmed_no_effect.
- Code: `EFFECT_UNCERTAIN`.
- Let `a` be the attempt with `attempt_id = ev.payload.attempt_id`, and `e = d.effect_intent`.
- Predicate:
  - `c1: a.status = CONFIRMED_NO_EFFECT ∧ receipt_ok(a, e)`
  - `c2: ∀ e' ∈ cur_effects \ {e}: e'.status ≠ UNCERTAIN`
  - `c3: |{a' ∈ A : a'.delivery_ref.id = d.delivery_id}| < cfg.behavior_policy.max_delivery_attempts` (default 3)
  - `c4: c.assessed_goal_revision = c.goal_revision`
- Tests:
  - T: one attempt with a no-effect receipt.
  - F (c1): no receipt.
  - F (c2): another effect is `UNCERTAIN`.
  - F (c3): 3 attempts.
  - F (c4): stale assessment.
  - B: 2 attempts give true.

**G22 `under_reinvestigation_budget`**
- Row: EVIDENCE_REVIEW|insufficient.
- Code: `BUDGET_EXCEEDED`.
- Predicate: `c1: assessment_current ∧ oa.verdict = INVESTIGATE_MORE` and `c2: c.reinvestigation_count + 1 ≤ eff_reinv`.
- Tests:
  - T: count 0.
  - F (c1): verdict `ACCEPT`.
  - F (c2): count 2.
  - B: count 1 gives true (second reinvestigation).
  - B: `decision-policy` `reinvestigation_budget = 1` with count 1 gives false (the effective minimum applies).

**G23 `under_transition_budget`**
- Rows: IN_PROGRESS|progress and IN_PROGRESS|candidate.
- Code: `BUDGET_EXCEEDED`.
- Predicate: `c1: tx_ok`, the same as U8, kept as the row guard.
- Tests:
  - T: count 2.
  - F: count 120.
  - B: count 119 gives true.

**G24 `unknown_effect_requires_reconciliation`**
- Rows: BLOCKED|resume_reconciliation and BLOCKED|resume_cancellation.
- Code: `EFFECT_UNCERTAIN`.
- Predicate:
  - `c1: (ev.name = resume_reconciliation ∧ c.blocked_from_state = EFFECT_UNCERTAIN) ∨ (ev.name = resume_cancellation ∧ c.blocked_from_state = NEEDS_RECONCILIATION)`
  - `c2: c.effect_state = UNCERTAIN ∧ ∃ e ∈ cur_effects: e.status ∈ {CLAIMED, UNCERTAIN}`
  - `c3: ev.payload.resolves_block_reason = c.block_reason ∧ ev.payload.new_deadline_at > now`
- Tests:
  - T: `resume_reconciliation`, blocked from EFFECT_UNCERTAIN.
  - T: `resume_cancellation`, blocked from NEEDS_RECONCILIATION; the target is NEEDS_RECONCILIATION, so the cancellation is kept.
  - F (c1): `resume_reconciliation` with `blocked_from_state = NEEDS_RECONCILIATION`.
  - F (c1): `resume_cancellation` with `blocked_from_state = EFFECT_UNCERTAIN`.
  - F (c2): all `CONFIRMED`.
  - F (c3): reason mismatch.
  - B: `transition_count = 120` gives `BUDGET_EXCEEDED` (U8 applies to RESUME rows).

**G25 `provider_proves_no_effect`**
- Row: EFFECT_UNCERTAIN|confirmed_no_effect_exhausted.
- Code: `EFFECT_UNCERTAIN`.
- Let `a` be the attempt with `attempt_id = ev.payload.attempt_id`, and `e = d.effect_intent`.
- Predicate:
  - `c1: a.status = CONFIRMED_NO_EFFECT ∧ receipt_ok(a, e)`
  - `c2: |{a' ∈ A : a'.delivery_ref.id = d.delivery_id}| ≥ cfg.behavior_policy.max_delivery_attempts`
- `c2` is the complement of G21.c3. The producer emits `confirmed_no_effect` while the
  attempt budget has capacity and `confirmed_no_effect_exhausted` otherwise.
- Tests:
  - T: 3 attempts, the last with a no-effect receipt.
  - F (c1): no receipt.
  - F (c2): 2 attempts.
  - B: `now > c.deadline_at` gives true, because REALITY rows are exempt from U7.
  - B: another effect is `UNCERTAIN`: true. The aggregate stays `UNCERTAIN` and the
    block resumes through `resume_reconciliation` (G24).

**G26 `acceptance_block_resolved_authorized`**
- Row: BLOCKED|resume_acceptance.
- Code: `INVALID_INPUT`; P-AUTHZ also applies.
- Predicate:
  - `c1: c.blocked_from_state ∈ {RECEIVED, CLASSIFIED}`
  - `c2: ev.payload.resolves_block_reason = c.block_reason ∧ ev.payload.new_deadline_at > now`
  - `c3: E = ∅ ∧ c.effect_intent_refs = [] ∧ c.effect_state = NONE`
  - `c4: rc ≠ null ∧ rc.commitment_ref = c.id`
- The target is CLASSIFIED and never ACKNOWLEDGED. Acceptance is still decided by
  G20 on the `accepted` row. A block from RECEIVED or CLASSIFIED can only be
  `DEADLINE_ELAPSED`, because those states have no `budget_exhausted` row.
- Tests:
  - T: a deadline block from CLASSIFIED with a recorded classification.
  - F (c1): `blocked_from_state = IN_PROGRESS`.
  - F (c2): `new_deadline_at = now`.
  - F (c3): one `COMMITTED` effect.
  - F (c4): `rc = null`. A block from RECEIVED resumes only after the classification is recorded.
  - F (PA): `pd = null` gives `FORBIDDEN`.
  - B: blocked from RECEIVED with a recorded classification gives true.
  - B: `transition_count = 120` gives `BUDGET_EXCEEDED` (U8 applies to RESUME rows).

## 6. Actions: record-intent semantics

An action is pure and returns `TransitionRecord {commitment_patch, records: list[RecordIntent]}`.
`RecordIntent.table` is one of:
- `commitments`;
- `commitment_events`;
- `effect_intents`;
- `outbox`;
- `timer_intents`;
- `workflow_refs`;
- `work_items`;
- `approval_requests`.

The ledger tables are those of BOUNDARY_CONTRACTS, plus the RFC-014 approval store.

The application commits all intents and the CAS update in **one** ledger transaction:
`UPDATE ... WHERE id = c.id AND revision = ev.expected_revision`. If zero rows are
updated, the result is `REVISION_CONFLICT` and nothing is written. No action calls
a provider, a channel or a model. Dispatch happens only in the outbox worker, after
commit, and only after the RFC-014 §6.4 recheck.

Every action has these implicit effects:
- It sets `state = target`, `revision += 1` and `transition_count += 1`.
- It appends one `commitment_events` row with `causation_id = ev.envelope.event_id`.
- For a nonterminal target, it sets a non-null `next_action` and `deadline_at`.
- It keeps `responsible_actor_id`.
- Entering BLOCKED sets `blocked_from_state = c.state` and `block_reason`. Leaving
  BLOCKED clears both.
- It never deletes or rewrites an `effect_intents` row or an attempt (invariant 5).
- Unless the action states otherwise, `deadline_at` is unchanged and the review
  interval `R = cfg.behavior_policy.default_next_contact_s` (900 s) is used.

| Action | Commitment patch, beyond the implicit effects | Additional intents |
|---|---|---|
| record_classification | `next_action = "acknowledge"` | none |
| record_receipt | `next_action = "start"`, `next_update_at = now + R` | outbox status notice to the requester |
| start_execution | `next_action = "execute"` | workflow_refs (status PENDING, idempotency_key), work_items |
| record_progress | `next_update_at = now + R` | none |
| record_blocking_question | `next_action = "await_input"` | outbox question, timer_intents FOLLOW_UP at `now + R` |
| merge_feedback | `next_action = "execute"`; if `new_goal ≠ null`: `goal`, `goal_revision += 1`, `assessment_ref = null`, `assessed_goal_revision = null`, `outcome_verdict = UNKNOWN`, `effect_state = effect_state(E)` after the effect change | timer_intents (cancel the FOLLOW_UP), work_items; if `new_goal ≠ null`, every `COMMITTED` effect gets `dispatch_stopped_at = now` and `COMMITTED→CONFIRMED_ABSENT` (never claimed and dispatch stopped) |
| record_candidate | `evidence_refs ∪= payload.evidence_refs`, `next_action = "assess"` | work_items (independent assessment) |
| request_more_evidence | `reinvestigation_count += 1`, `outcome_verdict = UNKNOWN` | work_items |
| prepare_delivery | `outcome_verdict = ACCEPT`, `assessment_ref`, `assessed_goal_revision = goal_revision`, `evidence_refs = oa.evidence_refs`, `effect_intent_refs += e.effect_id`, `effect_state = PENDING`, `next_action = "dispatch"` | effect_intents (`COMMITTED`), outbox (delivery, not claimable until claim) |
| prepare_partial_delivery | the same as prepare_delivery with `outcome_verdict = PARTIAL`; the delivery body discloses `oa.gaps` | the same as prepare_delivery |
| claim_dispatch | `effect_state = PENDING`, `next_action = "await_receipt"` | effect_intents `COMMITTED→CLAIMED`, outbox claimable, approval_requests `consumed_at = now`, `consumed_by_effect_id = e.effect_id`, timer_intents DEADLINE_CHECK at `deadline_at` |
| record_delivery | `delivery_attempt_refs += a.attempt_id`, `effect_state = CONFIRMED`, `outcome_ref`, `next_action = null` | effect_intents `→CONFIRMED`, timer_intents (cancel all) |
| schedule_reconciliation | `effect_state = UNCERTAIN`, `deadline_at = now + R`, `next_action = "reconcile"`; from BLOCKED, clear the block fields | effect_intents `CLAIMED→UNCERTAIN`; for every `COMMITTED` effect, `dispatch_stopped_at = now`; work_items (reconcile, never resend); timer_intents DEADLINE_CHECK |
| prepare_retry | `effect_state = PENDING`, `next_action = "dispatch"` | effect_intents (attested effect `→COMMITTED`, same effect_id and idempotency_key, no new key) |
| resume_execution | `deadline_at = payload.new_deadline_at`, `next_action = "execute"` | work_items |
| resume_delivery | `deadline_at = payload.new_deadline_at`, `next_action = "dispatch"` | none |
| resume_acceptance | `deadline_at = payload.new_deadline_at`, `next_action = "acknowledge"` | none |
| record_cancel_request | `deadline_at = now + R`, `next_action = "reconcile_cancellation"`; on the SEND_PENDING `goal_revision` row, `goal` and `goal_revision` are unchanged and the requested goal is kept only in the `commitment_events` payload | for every `COMMITTED` effect, `dispatch_stopped_at = now`; workflow_refs CANCEL_REQUESTED; timer_intents (cancel non-reconciliation timers) |
| record_cancelled | `effect_state = NONE` if `E = ∅`, otherwise `CONFIRMED_ABSENT`; `next_action = null` | effect_intents (stopped `COMMITTED` `→CONFIRMED_ABSENT`), workflow_refs CANCELLED, outbox status notice |
| record_effectful_cancellation | `effect_state = CONFIRMED`, `next_action = null` | outbox status notice listing receipts, workflow_refs CANCELLED |
| record_blocker_with_owner | `block_reason = "DEADLINE_ELAPSED"` for `deadline`, `"BUDGET_EXHAUSTED." + exhausted_dim` for `budget_exhausted`, or `"BUDGET_EXHAUSTED.delivery_attempts"` for `confirmed_no_effect_exhausted`; `deadline_at = now + R`; `next_action = "resolve_block"`; for `confirmed_no_effect_exhausted`, `effect_state = effect_state(E)` after the effect change | outbox notice to `responsible_actor_id`; for `confirmed_no_effect_exhausted`, effect_intents (attested effect `UNCERTAIN→CONFIRMED_ABSENT`, `dispatch_stopped_at = now`) |
| record_escalation_and_next_review | `deadline_at = now + R` | outbox escalation notice, limited by `behavior_policy.max_updates_per_hour` |

Status, question and escalation notices are `outbox` rows that the worker dispatches
under RFC-014 policy. They are not in `c.effect_intent_refs`, which tracks only
deliverable effects.

A goal revision never edits a delivery in flight. In EVIDENCE_REVIEW and
READY_TO_DELIVER, `merge_feedback` returns the commitment to IN_PROGRESS with the new
goal and stops the effect prepared for the previous goal. In SEND_PENDING the effect
may already exist, so the row enters the cancellation path, and the requester submits
the new goal as a new request after the cancellation is reconciled.

## 7. Deadline and budget handling

- **Clock.** The `Clock` port is injected. It is called once per reducer invocation,
  and its value is `GuardInput.now`. Ledger adapters back it with the database clock,
  which is the RFC-003 lease rule. Deterministic tests use a fixed clock.
- **Comparisons.** Comparisons are made on UTC instants at microsecond precision.
  - A deadline is elapsed iff `now ≥ deadline_at`.
  - Validity windows are strict: `now < valid_until` and `now < expires_at`.
  - Token clock skew of 60 s (ADR-014) belongs to the identity layer. It is already
    applied in `token_revoked` and `ctx`, and guards do not apply it again.
- **Deadline events.** A deadline is decided from `c.deadline_at`, not from the timer
  that fired. A timer that fires late within `fire_until` fires once. A timer past
  `fire_until` becomes EXPIRED, and the sweeper still emits `deadline` whenever U6
  holds, so no deadline is lost.
- **Effective budgets.** Each value names its configuration field:
  - `b.max_transitions = min(commitment-control-v2.json#/budget/max_transitions [120], per-commitment Budget.max_transitions if present)`.
  - `eff_reinv` is defined once, in section 3.2: `min(commitment-control-v2.json#/budget/max_reinvestigations [2], decision-policy behavior_policy.reinvestigation_budget [2], Budget.max_reinvestigations if present)`.
  - The evidence age limit is `behavior_policy.max_evidence_age_s.default` [86400].
  - The review interval is `behavior_policy.default_next_contact_s` [900].
  - The ambiguity limits are `routing_policy.ambiguity_margin` [0.15] and `routing_policy.min_candidate_score` [0.5].
  - The delivery attempt limit is `behavior_policy.max_delivery_attempts` [3].
- **Exhaustion.** Exhaustion is recorded through `budget_exhausted` or `deadline` to
  BLOCKED with the owner kept, as `on_exhaustion` in the table requires. A budget
  never marks work complete. An exhausted delivery attempt budget is recorded through
  `confirmed_no_effect_exhausted` in the same way.
- **Blocks that are not resumable in v2.** A `BUDGET_EXHAUSTED.transitions` block
  (decided rule 2) and a `BUDGET_EXHAUSTED.delivery_attempts` block with no remaining
  `UNCERTAIN` effect have no RESUME row that passes. Their exits are
  `cancel_requested` and the `deadline` escalation to the owner.

## 8. Schema gaps (all closed)

Every gap found while writing this document is closed. No gap is open.

| ID | Closed in | Field |
|---|---|---|
| G1 | `event-envelope.schema.json` | `expected_revision` (integer ≥ 0, required whenever `payload` is present) and `payload` typed by `$defs/ControlEventPayload` (section 3.1) |
| G2 | `runtime-boundaries.schema.json#/$defs/EffectRecord`; TYPE_CATALOG `EffectRecord` | `status` (`COMMITTED`, `CLAIMED`, `UNCERTAIN`, `CONFIRMED`, `CONFIRMED_ABSENT`), `dispatch_stopped_at`, `lease_expires_at` (date-time or null) |
| G3 | `outcome-assessment.schema.json`; TYPE_CATALOG `CandidateOutcome` | `assessor_actor_id`, `assessed_at`; CandidateOutcome `producer_actor_id` |
| G4 | `approval-request.schema.json` | `consumed_at` (date-time or null), `consumed_by_effect_id` (string or null) |
| G5 | `commitment-v2.schema.json` `block_reason` | pattern `^(DEADLINE_ELAPSED\|BUDGET_EXHAUSTED\\.(transitions\|reinvestigations\|requests\|tool_calls\|cost\|delivery_attempts))$` |
| G6 | `runtime-boundaries.schema.json#/$defs/CommitmentUsage`; TYPE_CATALOG `CommitmentUsage` | `requests`, `tool_calls`, `output_tokens` (integers ≥ 0), `cost_usd` (decimal string or null) |
| G7 | `decision-policy.schema.json` `behavior_policy` | `max_delivery_attempts` (integer ≥ 1, default 3) |
| G8 | `commitment-v2.schema.json` | `space_id` (string; RFC-013 requires it on every row; it is not a guard input) |
| G9 | TYPE_CATALOG `GuardInput` | `token_revoked: bool` from the identity port |

## 9. Control table issues

| ID | Issue | Status |
|---|---|---|
| T1 | BLOCKED from NEEDS_RECONCILIATION could resume only to EFFECT_UNCERTAIN, which lost the cancellation | RESOLVED: row `BLOCKED,resume_cancellation,NEEDS_RECONCILIATION,unknown_effect_requires_reconciliation,schedule_reconciliation`; G24.c1 binds each event to its origin state |
| T2 | EFFECT_UNCERTAIN `confirmed_no_effect` with an exhausted attempt budget had no row | RESOLVED: row `EFFECT_UNCERTAIN,confirmed_no_effect_exhausted,BLOCKED,provider_proves_no_effect,record_blocker_with_owner` (G25) |
| T3 | `budget_exhausted` was missing for WAITING_INPUT | RESOLVED: row `WAITING_INPUT,budget_exhausted,BLOCKED,budget_exhausted,record_blocker_with_owner`. RECEIVED, CLASSIFIED, SEND_PENDING, EFFECT_UNCERTAIN, CANCEL_REQUESTED and NEEDS_RECONCILIATION need no such row: they have no WORK row that consumes budget beyond acceptance, or they are driven by REALITY, CANCEL or TIMEOUT events, which are exempt from U8 |
| T4 | The `CANCEL_REQUESTED\|deadline` target NEEDS_RECONCILIATION requires at least one intent, and the deadline has no target when `E = ∅` | RESOLVED without a table change: the producer of `cancel_requested` emits `no_effects` in the same step when `E = ∅`; G12.c1 denies the `deadline` row in that case |
| T5 | BLOCKED `deadline` self-loop is unbounded | OPEN: a bound needs `behavior_policy.max_escalations`, a per-commitment escalation counter and a defined behavior after the last escalation. No PRD or RFC defines them. Until then the loop is limited only by `behavior_policy.max_updates_per_hour` |
| T6 | A SEND_PENDING cancel goes to CANCEL_REQUESTED while a dispatch is in flight | NO CHANGE: G01 is false for `CLAIMED`, so G03 leads to reconciliation |
| T7 | Resuming a commitment BLOCKED from RECEIVED or CLASSIFIED would skip acceptance | RESOLVED: row `BLOCKED,resume_acceptance,CLASSIFIED,acceptance_block_resolved_authorized,resume_acceptance` (G26) |
| T8 | The table has `max_reinvestigations` and the decision policy has `reinvestigation_budget` | RESOLVED by one definition: `eff_reinv` in section 3.2. The table value is the ceiling and the policy value may only lower it (M09) |
| T9 | A goal revision was possible only through `feedback` in WAITING_INPUT | RESOLVED for EVIDENCE_REVIEW, READY_TO_DELIVER and SEND_PENDING: rows `EVIDENCE_REVIEW,goal_revision,IN_PROGRESS,authorized_feedback_current_revision,merge_feedback`, `READY_TO_DELIVER,goal_revision,IN_PROGRESS,authorized_feedback_current_revision,merge_feedback` and `SEND_PENDING,goal_revision,CANCEL_REQUESTED,authorized_feedback_current_revision,record_cancel_request`. ACKNOWLEDGED and IN_PROGRESS have no `goal_revision` row yet (owner decision) |

Cycles through BLOCKED stay bounded. Every RESUME row is subject to U8. The cycle
BLOCKED → CANCEL_REQUESTED → NEEDS_RECONCILIATION → BLOCKED is exempt from U8, and
each lap needs a new authorized `cancel_requested` (G08) and an elapsed deadline.
