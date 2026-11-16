# Decision rules and ownership (resolves audit A-13)

Scope: only terms a gate or a runtime decision depends on. Thresholds live in the decision-policy sidecar (not code), are
versioned with `decision_policy_hash`, and the value used is recorded in the decision `reason_code`/trace. "Gate oracle" =
a deterministic code or test check may fail a slice on it. "EDD rubric" = scored quality metric reported as evidence; it
never fails a gate. Usefulness, tone, concision and "good judgment" are always EDD rubric metrics.

## 1. Ownership table

| Output (contract or type) | Owner (sole producer) | Consumers | Persisted by |
|---|---|---|---|
| RequestClassification (`request-classification.schema.json`, the single classification vocabulary) | **M08** (`ModelPort.classify` output or trusted preflight, then the §3 policy pass) | M03, M04, M05, M06 | M07 inside the turn/commitment record |
| Reference resolution: candidates, feature vectors, scores, verdict `RESOLVED`/`AMBIGUOUS`/`UNRESOLVED`/`NO_REFERENCE` (§4) | **M04** | M03, M05 | not persisted alone; verdict and top-two scores go into the decision trace |
| Clarification eligibility verdict (§5 of M05 PRD), a pure function result, not a catalog type | **M05** | M03 only | not persisted |
| Communication kind and timing (`kind`, `next_contact_at`, suppression verdict) | **M06** | M03 | `next_contact_at` stored by M07; timer via `DurableRunner.schedule` |
| **InteractionDecision** (`interaction-decision.schema.json`) | **M03 only**, via `InteractionPort.decide` | M06, M07, M10, CLI/channels | M07 via `InteractionPort.apply` -> TurnResult |
| OutcomeAssessment | M09 (`OutcomeJudge`) | M03, M10 | M07 |
| Delivery attempts/ack | M10 | M03, M06 | M10 through the ledger |

**Single owner of the final InteractionDecision: M03.** M08 alone classifies and recommends (`next_action`); M04 does not
classify intent, it resolves references against an existing classification; M05 permits or vetoes `ASK` and
`START_SAFE_WORK`; M06 supplies communication kind and timing. None of M04, M05, M06 or M08 emits an InteractionDecision.
M03 MAY choose a more restrictive action than the recommendation but MUST NOT lower `risk`, skip an M05 `ASK_BLOCKING`
verdict, or ignore a `deny`/`escalate` classification. M07 persists; M02/M25 authorization is checked before any effect
regardless of any decision.

Restrictiveness order (used by §3 and M03): `respond` < `search_context` < `start_safe_work` < `ask` < `escalate` < `deny`.

## 2. Term rules

| Term | PRD ids | Operational rule | Config field (default) | Kind |
|---|---|---|---|---|
| "materially affect scope, risk, cost or outcome" (blocking question) | M05-FR-02 | `ASK` with `question_blocking=true` only if a field in the blocking set is missing (detectors in M05 normative detail): `{target_resource, destructive_or_external_effect_confirmation, recipient, deadline_if_stated_relative_and_unresolvable, authorization_scope}`, or M04 returns `AMBIGUOUS`. Otherwise `START_SAFE_WORK`, and an optional question has `question_blocking=false`. | `behavior_policy.blocking_fields` (the five above); `routing_policy.ambiguity_margin` (0.15) | Gate oracle |
| "interruption cost" | M05-FR-02, M23-FR-03 | At most one question per turn and at most `max_open_questions` open non-blocking questions per commitment; a further question is allowed only if its field is in the blocking set. A field with an open question is never asked again; an answered field is re-asked at most `max_reasks_per_field` times and only after its answer failed validation. SME contact (M23) requires a blocking field missing AND no local evidence source. | `behavior_policy.max_open_questions` (1); `behavior_policy.max_reasks_per_field` (1) | Gate oracle |
| "ambiguous" / "plausible" candidates | M04-FR-02, M04-AT-02, M08-AT-02, M17-FR-03 | A candidate is plausible when its §4 score >= `min_candidate_score`. Ambiguous means at least two plausible candidates and top-two gap < `ambiguity_margin`, or classification `uncertainty=high` together with at least one plausible candidate. Ambiguous never routes to a write capability. | `routing_policy.min_candidate_score` (0.5), `routing_policy.ambiguity_margin` (0.15), `routing_policy.candidate_score_weights`, `routing_policy.recency_horizon_s` (2592000), `routing_policy.max_reference_candidates` (5) | Gate oracle |
| "meaningful progress" | M06-FR-02 | `UPDATE` with kind `progress` only when a new ledger-recorded state change occurred since the last contact: a state transition, a new evidence_ref or a completed step. Elapsed time or model chatter alone never counts. Anti-spam: no more than one unsolicited `UPDATE` per recipient per `min_update_interval_s`, counted across all of that recipient's commitments (M06 §4.4), unless the state is terminal or blocked. | `behavior_policy.min_update_interval_s` (60 local, 300 channel) | Gate oracle |
| "spam / silent abandonment" | M06 purpose, M06-FR-01 | No commitment in a non-terminal state may lack a non-null `next_contact_at`; no more than `max_updates_per_hour` unsolicited messages per recipient, across all of that recipient's commitments, in any rolling 3600 s window (M06 §4.4). | `behavior_policy.max_updates_per_hour` (6); `behavior_policy.default_next_contact_s` (900; the floor of `delay_interval_s = max(default_next_contact_s, horizon_s / 8)`, M06 §4.3) | Gate oracle |
| "justified urgent alerts" | M06-FR-03 | Overrides quiet hours only when classification `risk` is `high` or the commitment `priority` is `P0`, or a deadline is within `urgent_deadline_s`. The override reason is recorded. | `behavior_policy.urgent_deadline_s` (3600) | Gate oracle |
| "useful moments" / "right moment" for proactive contact | M03-FR-02, M06 | Not a runtime concept. Proactive contact is permitted only through the three rules above (`next_contact_at`, progress, urgent). Whether the timing was useful is scored later. | none | EDD rubric |
| "choose message, silence, question, ... based on context" | M03-FR-02 | Deterministic first-match table in M03 normative detail over (event source, classification.next_action, M05 verdict, M06 kind, commitment state) to one schema action; silence is `WAIT` with non-null `next_contact_at`. A greeting never creates a commitment. | none (table versioned with the behavior statechart) | Gate oracle |
| "likely changes the decision" (further investigation) | M09-FR-01 | `INVESTIGATE_MORE` only if a counted gap exists (a claim without evidence_ref, or conflicting evidence unresolved) AND remaining `reinvestigation_budget` > 0. Otherwise `ACCEPT` or `PARTIAL` with the gaps listed. The model's guess about the likelihood is not an input. | `behavior_policy.reinvestigation_budget` (2 rounds) | Gate oracle |
| "recency" / "stale" | M09-FR-01, M13-AT-02, M20-RT-02 | An evidence item is stale when `observed_at` is older than `max_evidence_age_s` for its class (key `default` when the class has no entry), or its source version is superseded. Stale evidence cannot back a "current" claim. | `behavior_policy.max_evidence_age_s` (per class; `default` 86400) | Gate oracle |
| "nontrivial work" | M09-FR-02, M01 and others (results clause) | Classification `complexity` in {multi_step, investigative} or `intent` in {professional_work, deep_investigation, external_action} or `risk` >= medium. | none (derived from classification) | Gate oracle |
| "relevant decision information", "concise summary", "excessive verbosity" | M10 purpose, M10-FR-02, M10-AT-01, M03-RT-02 | Mechanical part: every human-facing message (M03 non-DELIVER messages and the M10 summary) is at most `max_summary_chars` characters; the M10 summary includes `status`, one `next_action` and at least one evidence link when evidence exists. Whether it is relevant or well-judged is rubric only. | `behavior_policy.max_summary_chars` (1200) | Gate oracle (shape); EDD rubric (relevance) |
| "appropriately informed", "appropriate", "meaningful" in purposes | M06, M24-FR-02, M29 purpose | Prose only; the enforceable parts are the rows above. | none | EDD rubric |
| "small model for safe simple work, escalate on ambiguity" | M17-FR-03, M08-FR-03 | Model role rule of §3.3 (total by construction): `small` iff risk in {none, low} AND uncertainty in {low, medium} AND complexity rank <= rank(`small_model_max_complexity`) AND effect class in {none, read}; otherwise `strong`. A schema-repair failure on `small` re-routes once to `strong`. | `routing_policy.small_model_max_complexity` (short) | Gate oracle |
| "unknown-risk escalation" | M08-FR-03 | A classification that fails the structured-output ladder, or any missing or out-of-vocabulary `risk`, is replaced by the fail-closed classification of §3.1 (risk `high`, next_action `escalate`). | none | Gate oracle |

## 3. Classification policy pass and routing table (owner M08)

### 3.1 Inputs and normalization

The policy pass is a pure function `route(classification_raw, effect_class) -> (next_action, model_role, reason_code)`
evaluated by M08 after `ModelPort.classify` (or trusted preflight) and before the classification is published.

1. If `classification_raw` failed schema validation after the ModelPort structured-output ladder, M08 substitutes the
   fail-closed classification `{intent: professional_work, work_needed: true, complexity: investigative, risk: high,
   uncertainty: high, safe_work_allowed: false, next_action: escalate, reason_code: CLASSIFICATION_INVALID_ESCALATE}`.
2. Effect class is computed by M08, never taken from model text: `effect_class = max(intent_floor(intent),
   max(trusted effects of capabilities named in the proposed action set))` with order none < read < write < dangerous,
   `intent_floor` = none for social/simple_answer/status_query, read for context_lookup/professional_work/
   deep_investigation, write for external_action. Effects come only from the registry `CandidateSummary.effects`; a
   capability absent from the registry counts as `dangerous`. Before a capability is chosen the proposed action set is
   empty, so `effect_class = intent_floor(intent)`.
3. The table below is evaluated on the normalized effect `max(effect_class, intent_floor(intent))`.

### 3.2 Route table (first match wins; table id `route-table/1`)

| Row | Condition | Route (`next_action`) | reason_code |
|---|---|---|---|
| R1 | risk = high | escalate | ROUTE_RISK_HIGH |
| R2 | effect = dangerous | escalate | ROUTE_EFFECT_DANGEROUS |
| R3 | effect = write | ask | ROUTE_EFFECT_NEEDS_CONFIRMATION |
| R4 | intent in {social, simple_answer} AND uncertainty in {low, medium} AND complexity in {trivial, short} | respond | ROUTE_DIRECT_ANSWER |
| R5 | intent = status_query | search_context | ROUTE_STATUS_LOOKUP |
| R6 | intent = context_lookup | search_context | ROUTE_CONTEXT_LOOKUP |
| R7 | intent = simple_answer AND complexity in {multi_step, investigative} | start_safe_work | ROUTE_SIMPLE_BUT_NONTRIVIAL |
| R8 | intent in {social, simple_answer} | search_context | ROUTE_UNCERTAIN_SHORT_REQUEST |
| R9 | intent in {professional_work, deep_investigation} | start_safe_work | ROUTE_SAFE_WORK |
| R0 | default (any tuple not matched above) | escalate | ROUTE_DEFAULT_FAIL_CLOSED |

R3 and R1 cover every `external_action` tuple after normalization. Rows R4–R9 are reached only with effect in
{none, read} and risk in {none, low, medium}. R0 is unreachable for the current vocabulary and exists so that a future
enum value fails closed.

**Published values.** `next_action = more restrictive of (model next_action, table route)` per §1 order; a model `deny`
is kept. `reason_code` = the table reason_code when the table route is strictly more restrictive, else the model's.
`safe_work_allowed = model value AND effect in {none, read} AND risk != high AND next_action not in {escalate, deny}`.
`work_needed = model value OR nontrivial(classification)`. Trusted preflight output is accepted only when it has
intent `social` or a local command, risk `none`, complexity `trivial` and next_action `respond`; it still passes this table.

### 3.3 Model role (total by construction)

`model_role = small` iff risk in {none, low} AND uncertainty in {low, medium} AND rank(complexity) <=
rank(`routing_policy.small_model_max_complexity`) AND effect in {none, read}, with rank trivial=0, short=1,
multi_step=2, investigative=3; otherwise `strong`. Low-risk multi_step and investigative work is therefore `strong`.
Escalation to `strong` is available only when `model-competence.schema.json#/$defs/RoutingPolicy.escalation_order` is
non-empty and names a role qualified for the task class; otherwise (MVP default, pre-MOD-01) a `strong` route returns
response status `BLOCKED` with error code `NOT_CONFIGURED` and reason_code `ESCALATION_UNAVAILABLE`.

### 3.4 Totality oracle

`tests/unit/test_route_table.py::test_route_table_is_total_and_first_match_unique` enumerates all 7 intents x 4 risks x
4 effect classes x 4 complexities x 3 uncertainties = 1344 tuples and asserts: each tuple yields exactly one row and one
`(next_action, model_role)`; R0 is matched by zero in-vocabulary tuples; no tuple with effect in {write, dangerous} or
risk = high yields `start_safe_work`, `respond` or `search_context`; no tuple yields `small` with risk >= medium. A second
test feeds an out-of-vocabulary value and asserts R0.

## 4. Reference candidate score (owner M04)

For each candidate reference `c` (prior commitment, turn artifact or memory episode already filtered by the current ACL
and tenant before scoring), M04 computes five features in [0,1] from the request text `q`, the injected clock `now` and
the requester time zone:

| Feature | Definition |
|---|---|
| `exact_id` | 1 if `q` contains `c.ref`, `c.commitment_id` or the exact normalized title of `c` in quotes; else 0 |
| `title_overlap` | `|T(q) ∩ T(c.title)| / |T(c.title)|`, 0 if `T(c.title)` is empty; `T` = set of NFKC-casefolded tokens split on non-alphanumerics, tokens shorter than 3 characters dropped |
| `time_window` | 1 if `q` contains a supported temporal expression and `c.observed_at` is inside its window; 0 if it contains one and `c` is outside; 0.5 if it contains none. Supported: ISO date, today, yesterday, this/last week (ISO weeks, Monday 00:00 local), this/last month; English plus the request language's catalog entries in the behavior policy |
| `ownership` | 1 if `c` was created by the same actor; 0.5 if visible to the actor through a shared ACL; 0 otherwise |
| `recency` | `max(0, 1 - (now - c.observed_at) / recency_horizon_s)` |

`score(c) = round_half_even(Σ w_f · feature_f, 4)` using decimal arithmetic, with weights
`routing_policy.candidate_score_weights` (defaults exact_id 0.35, title_overlap 0.25, time_window 0.20, ownership 0.10,
recency 0.10). The config validator rejects weights whose sum differs from 1 by more than 1e-9 (CONFIG_INVALID).
Candidates are ordered by score descending, then `observed_at` descending, then `ref` ascending (code-point order); at
most `max_reference_candidates` are kept. Verdict: `NO_REFERENCE` if no candidate is plausible and
`classification.commitment_ref` is null; `UNRESOLVED` if none is plausible and `commitment_ref` is non-null;
`AMBIGUOUS` per §2; otherwise `RESOLVED` to the first candidate. Gap = score(1st) - score(2nd), computed on rounded scores.

## 5. Rules for adding terms

A new subjective term in a PRD needs a row here (owner, rule, config field, kind) before it can appear in an AT or gate.
If no machine check is possible, label it EDD rubric and keep it out of gate oracles.

## 6. Exact configuration contract

`contracts/decision-policy.schema.json` defines every `behavior_policy.*` and `routing_policy.*` field named above, with
type, range and default; every object has `additionalProperties: false`. The complete synthetic default is
`examples/behavior/decision-policy.json`. Store the operator-owned sidecar at `<config_dir>/decision-policy.json`;
validate it before use, reject unknown keys, apply the cross-field checks (weights sum to 1; `blocking_fields` is exactly
the five-field minimum set) and hash canonical sorted-key UTF-8 JSON (quati-json/1) as `decision_policy_hash` in decision
traces. `policy_version` continues to identify authorization policy only. The route table id (`route-table/1`) is a code
constant recorded beside the hash.
It is separate from the authorization policy (`policy.schema.json`) and the model
selection configuration (`model-competence.schema.json#/$defs/RoutingPolicy`). It cannot
grant authority or disable a kernel check. Missing/unreadable/invalid configured bytes
produce CONFIG_INVALID, with no dispatch; initial setup explicitly copies the defaults.
The compiler receipt/config evidence must bind its digest before runtime use (S00-T02
contract validation; S01-T02 decision consumption; later slices consume their fields).
No runtime or packaged compiler support for this new sidecar is claimed by this spec.

The five blocking fields are a minimum set and cannot be removed by an operator.
Model escalation recommendations never enable autonomous routing before MOD-01; with
escalation disabled, a request requiring an unqualified role returns BLOCKED.
