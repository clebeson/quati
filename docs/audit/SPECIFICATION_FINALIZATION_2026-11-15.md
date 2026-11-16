# Specification finalization — 2026-11-15

Scope: reconcile and finish Claude's specification amendments in the exported SECMA
workspace. This is an author-performed specification/tooling review, not an independent
runtime audit. No runtime source or packaged candidate assets were changed.

## Completed corrections

| Boundary | Final contract |
|---|---|
| S00 discovery | CAP-01 and CAP-02 each require 30/30 runs (10 paraphrases × 3), shuffled catalog, zero unauthorized effects and exact provider/model/prompt/config/catalog identity. Protocol, roadmap, slice, task registry and handoff agree; MOD-01 remains S04. |
| Governance | Three mandatory seals at each slice's final task; per-task seals optional. EVIDENCE_VERIFIED requires an independent reviewer. Validator rejects missing mandatory seals, wrong scope/identity/commit and mixed source identities. |
| Evidence | Commit-bound records retain hashed test log and transcript; exported/dirty trees use the full source-snapshot form. Paths and evidence bytes are verified. Commit existence, clean tested inputs, reviewer independence and semantic coverage require review; L0 does not prove them. |
| Engineering memory | LOG.md owns new governance events. Legacy memory/index records remain readable and unresolved until supported closure; fixtures retain versioned provenance. Removed contradictory lease wording. |
| Decision thresholds | A-13 now has a closed JSON contract, explicit default sidecar, minimum blocking fields, bounds and unknown-key rejection. decision_policy_hash is distinct from authorization policy_version. S00-T02 validates; S01-T02 consumes. |
| Slack approval injection | POL-10 is an S04-specific L2 case owned by S04-T05, contributed by S04-T04 and linked to M25-AT-01. It tests signed untrusted content, fake approval, replay and dispatch expiry. POL-01 now contains only its S00 scope. No new unregistered requirement ID. |
| Planning closure | New memory-consolidation/worker cases linked to affected requirement plans and task handoffs. One full-proof task owner per case; planned paths use real test lanes. Traceability, acceptance prose and consolidated bundle regenerated from reviewed sources. |
| Checkpoint | Current catalogs: 240 requirement plans, 101 shared cases, 125 fixture recipes, 35 tasks, 31 PRDs, 15 RFCs and 16 ADRs. Historical evidence is preserved. Canonical revision advances from 6 to 7 without changing any runtime gate. |

## Validation and evidence

Both offline validators pass. The three specification suites pass **54 tests**.
Commands, output hashes, actual interpreter/dependency/OS identity, red failure,
source snapshot and tooling reports are recorded under
`evidence/specification-finalization-2026-11-15/`. The red result precedes the seal
validator correction. Synthetic seals in temporary test fixtures are not issued seals.
Adversarial negatives reject fabricated evidence, unbound transcripts, wrong source
commit/scope and an attempted unknown authorization-bypass key in decision policy.

Ripwire's Python quality delta has no gating regression after extracting seal lookup
and gate checks. Its full-tree report flags longer declarative JSON arrays/objects;
those are intentional added cases/schema fields, not executable complexity. Newly
collected pytest functions are reported as uncalled by the static graph; pytest runs
them. The edit check has no Git baseline in this export; no Git contract comparison is
claimed. The package manifest supplies current hashes; the existing Git bundle is
historical and does not contain these local amendments.

## Disposition and limits

Specification reconciliation is complete at L0. This does not qualify runtime behavior
or replace an independent implementation review. All 101 runtime scenarios and 240
requirement plans remain NOT_RUN. S00 remains BLOCKED; no implementation/release seal,
provider test, external write, merge or deployment was performed.

Candidate assets and catalog code still need reconciliation with the reviewed schemas
when implementation is authorized (LOG-0003 and historical candidate bugs). The hashed
cross-platform dependency lock is a future implementation deliverable, not a generated
artifact of this specification task. PostgreSQL qualification is required before SERVER
acceptance in S05; SQLite LOCAL on Linux is the S02 MVP gate.

This workspace has no usable Git metadata. No commit or persistent remote save receipt
is fabricated. PACKAGE_MANIFEST.json identifies the completed local package; copy it and
the evidence to an authorized persistent destination before relying on a backup.

Resume at IMPLEMENTATION_READY_INDEX.md and canonical state. Implementation still
requires explicit user authorization and the selected task's actual resources. Rollback
uses the changed-file hashes and original historical bundle/previous package; retain
old evidence and never infer runtime PASS from this report.
