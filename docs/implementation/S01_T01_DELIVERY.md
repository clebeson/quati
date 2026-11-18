# S01-T01 contribution delivery

Status: accepted by the root coordinator for the bounded T01 contribution.
This record closes no S01 gate and no full requirement plan.

## User-visible change and boundaries

Existing `quati chat` now carries one process-only conversation ID and a revision
that advances only after receipt acknowledgement. A principal change is refused
before model, audit or receipt effects. A failed receipt leaves the projection
unchanged and ends chat. Restart creates a new conversation; there is no background
worker, retained transcript, accepted durable obligation or continuation after exit.

Classification ingress is immutable and schema-validated, including optional-field
presence, closed enums and bounded confidence. A failed classifier yields a
code-owned fail-closed classification while preserving the provider error.
The public projection uses code-owned reason text and hides model references;
its proposal hash binds the original classification. The pure policy reducer is
advisory until T02: it cannot dispatch a model, authorize an effect or create work.

Direct RequestContext serialization emits required act=null and JSON arrays, and
rejects malformed informational policy versions. Trusted policy remains the only
source of authorization. The serializer has L1 proof only and no runtime caller.

## Exact local assertion coverage

| Assertion | Executed test locator | Observation / negative |
|---|---|---|
| S01-T01-A01 | tests/integration/cli/test_s01_conversation.py::test_a01 | Independently varied intent/risk/complexity; complete schema-shaped public value and raw proposal hash. Pure tests enumerate all 1344 routing tuples and restrictive effect floors. |
| S01-T01-A02 | tests/integration/cli/test_s01_conversation.py::test_a02 | Privilege/identity/effect/role additions exhaust structured repair, fail closed and trigger zero discovery effects. Principal-switch and free-model-text negatives add separate guard proof. |
| S01-T01-A03 | tests/integration/cli/test_s01_conversation.py::test_a03 | Same ID across receipted turns, exact revisions and output hashes, explicit PROCESS_ONLY lifetime, fresh restart identity and no durable jobs. Receipt failures do not advance state. |

SOC-02, CAP-04 and INT-01 are CONTRIBUTION_ONLY. Owned/final requirement-plan
lists are empty for this package. The responsibility table in S01_RUNTIME_CONTRACT
assigns the remaining M03/M04/M08/M31 obligations to T02/T03/T04 explicitly.
Scripted fake-provider tests do not qualify a real model or real integration.

## Independent review and corrections

Initial review: docs/audit/S01_T01_CODE_REVIEW_2026-11-18.md. Eight new tests
failed before correction. Fresh retest: docs/audit/S01_T01_RETEST_2026-11-18.md,
ACCEPT for the contribution, 61 scoped tests passed, child exit zero. All 205
hashed inputs and both output hashes matched the inspected working tree.
Historical evidence is immutable. Final results and aggregate coverage are recorded below.

Ripwire edit-check for CLIService.ask: unchanged public contract, no incompatible
caller. Quality-delta exits 2 with four gating structural warnings: two unchanged
registry prepare/commit methods affected by name resolution, and modest growth in
legacy AskSession/CLIService classes. Independent review found no actual collision
or unrelated responsibility. The advisory reducer and dataclass hooks are reported
as dead by the source-only graph; deterministic tests exercise them. No baseline,
threshold, source exclusion or test was weakened to silence the tool.

## Safety, debt and rollback

No model recommendation grants identity or effect authority. LOG-0061 records
future input/error mapping and concurrency preconditions; LOG-0057 retains
engineering-helper debt. Single-owner synchronous receipt coordination must be
reviewed before T03 adds concurrency. Historical S00 qualification is source-bound;
the current changed S01 source is not yet live-qualified.

Rollback: revert these source/config/test changes while retaining immutable evidence
and engineering journal history. There is no durable product-data migration.
No production, external write, merge, release or deployment is included.

## Final observed verification

- Full deterministic lanes: 2285 passed, zero failures, child exit 0 in 1026.21 s
  (coverage/final/runs/20261118T125826Z-3e3f0532).
- Two additional public CLI optional-field cases passed with no change to
  production code or any prior test file. Original source hashes still match.
  coverage/supplemental/runs/20261118T130213Z-6f35c5f6 records child exit 0.
  Independent scoped review: S01_T01_OPTIONAL_FIELDS_REVIEW_2026-11-18.md.
- Complementary lanes: 56 passed, 10 explicit skips (seven real-model evaluations,
  two real-provider smokes, one wheel build missing setuptools). These remain
  unverified and are not mandatory T01 contribution proof.
- Current deterministic requirement contribution: A01/A02/A03 observed passing,
  no owned requirement plan or complete S01 gate accepted.
- Aggregate branch-mode coverage: domain 100% line/branch, behavior 100% line/branch;
  application 99.96%/99.87%; overall 99.89%/99.79%. All package thresholds pass.
  Evidence: coverage/aggregate/summary.json, coverage.json and data.coverage.gz.
  Starting the supplemental run reset its temporary parallel data; aggregation
  restored retained full-run data plus the supplemental data on unchanged code.
  The partial supplemental report is not the full-package report.
- Reference host: Linux 6.17.0-41-generic, CPython 3.13.7, scripted fake providers.
  No current real-model or other-OS qualification is claimed.

All paths above are under evidence/S01/T01-2026-11-17 unless a docs/audit report
is named. Final validator manifests and exact evidence hashes are in DELIVERY.json.
There are 2343 distinct passing tests across the full deterministic, supplemental
and complementary runs, plus 10 explicit skips; repeated retests are not added.

Root accepts T01 local assertions only and authorizes continuation to T02 discovery
within the standing implementation scope. Remaining full-case gates are T04-owned.
