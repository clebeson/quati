# S00-T01 — CLI boundary delivery design

Authority: explicit user instruction, recorded in evidence/S00/T01-2026-11-15/authorization.json.
Current work is S00 only. This delivery implements local CLI contribution tests; it does
not close SOC-01, IDN-01, IDN-02, whole module plans or slice gates.

## Requirements and boundary

M01-FR-01/02, M01-RT-02: doctor and ask use the normative Response envelope and stable
exit codes, with no durable-work claim. S00-T01-A01 reports missing provider configuration;
A02 exact greeting invokes no model/capability and creates no commitment; A03 mixed
work/greeting returns truthful NOT_CONFIGURED when no provider exists, never a social
success. M02-FR-01/02/03 and M02-RT-01: bind identity to OS owner/device proof; text cannot
supply actor/tenant/space authority. M26-FR-01 and M26-AT-02: sanitized local receipts with
hashes, no keys/request bodies in default records.

All CLI JSON results have exactly status, data, evidence_refs, uncertainties, next_action
and typed error. S00 diagnostic/result-specific markers are inside data, including
result_status=RESPONDED or FIXTURE_RESULT; they cannot conflict with the normative status.
Missing provider is exit 3; unauthenticated/forbidden exit 4; invalid input exit 2;
provider failure exit 5. Doctor without probe inspects local configuration only.
Unsupported commands fail; they never simulate later slices.

## Identity and ownership refinement

RFC-013 is more specific than the earlier public-fixture exemption: ask requires an
initialized LOCAL installation and verified local-os/device proof, even at N=1.
Doctor/help/init are bootstrap diagnostics and do not read business repositories.
`quati init` explicitly bootstraps the local tenant, HUMAN principal, personal and
organization spaces. It creates Ed25519 device material in a private owner-only file
when no usable keyring backend is installed. The path is based on platformdirs with
QUATI_CONFIG_DIR as an explicit override. No key is output or placed in a receipt.
Use real OS identity and cryptography for device proof and in-process claims verification;
network JWT, SERVER identity, team management, approval and grants persistence belong to
later slices. Scope checks remain explicit before reads.

Task ownership is refined to include src/quati/adapters/local_identity.py and pure
identity types/guards under src/quati/application. This adapter is necessary to implement
the task's existing local principal obligation; it adds no downstream feature.
The CLI uses Typer (ADR-015) and a composition root. Use cases receive ports/callables;
application code does not import provider, database or receipt filesystem adapters.
Existing candidate discovery/provider components remain unqualified and are gated from
use until their owning tasks pass; this delivery must never use them to fake completion.

## Test lanes and evidence

L1 public process tests use actual CLI subprocesses, temporary local identity/receipt
files, real Ed25519 signatures and installed dependency versions. Deterministic injected
clock and unavailable-provider configurations are controls, not fake integration proof.
Test missing/corrupt/symlinked/world-readable/wrong-owner credentials; forged actor/tenant
claims; modified/expired/wrong-audience tokens; out-of-scope resource rejection before
repository lookup; localized exact greeting; mixed work; parse errors and input bounds.
Evidence records actual red/green, command/exit, source hashes, environment and scope.
Coverage measurement covers this delivery; it cannot qualify retained unreviewed code.

Independent fresh-context reviewer reads this design/spec/tests before source, chooses a
new adversarial negative, and audits conformity, quality and evidence. Open material
findings prevent acceptance and the next task. No mandatory real LLM case is mocked.

## Resume and rollback

Canonical state is authoritative; engineering events are stored incrementally in a
hash-chained execution journal. Preserve old evidence. The workspace is an exported tree
with protected/unusable .git metadata: use source snapshots and package hashes, not a
fabricated commit. A local checkpoint is available to another harness but no external
backup/save receipt is claimed. Rollback restores the prior candidate snapshot and keeps
all authorization, audit and test records.
