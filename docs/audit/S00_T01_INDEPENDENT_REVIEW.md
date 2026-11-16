# Independent S00-T01 conformity, security and quality review

Reviewer: fresh-context review agent `/root/s00_t01_independent_audit`.
Scope: S00-T01 local CLI and identity delivery only; requirements and negative cases were
read before runtime source. The reviewer did not author runtime changes. No provider,
production system, real secret or external account was used. Tests are L1 contribution
proof, not full SOC-01/IDN-01/IDN-02, slice acceptance or independent product qualification.

**Current disposition: ACCEPTED for the reviewed S00-T01 contribution scope after the recheck below.**

## Initial disposition

**NOT ACCEPTED pending the reproduced corrections below.** The initial task tests pass,
but independently chosen local credential and typed-contract faults expose omitted cases.
The reports and tests are not runtime fixes; canonical state remains owned by the lead.

| ID | Severity | Boundary and reproduction | Required correction |
|---|---|---|---|
| T01-R1 | P1 | Replace the owner-only identity.json with a FIFO; public `doctor --json` blocks in os.open before fstat can reject the nonregular file. The independent test times out after three seconds. | Open safely without blocking and verify a regular owner-only descriptor; retain symlink rejection. Add the public-path regression. |
| T01-R2 | P2 | Replace identity.json with valid JSON null, a number or a string. `_load` calls `.pop` on the scalar, raises uncaught AttributeError and causes traceback/empty JSON output for doctor and ask. | Reject non-object credential JSON and malformed fields with typed authentication failure; doctor remains a safe diagnostic. |
| T01-R3 | P2 | canonical_bytes emits raw Unicode and permits NaN/Infinity. This disagrees with secma-json/1's ASCII escapes and finite-number requirement. | Implement the canonical boundary bytes and retain independent Unicode/nonfinite regressions. |
| T01-R4 | P2 | Real valid Ed25519 signatures over an invalid principal ID, numeric tenant ID, fractional expiry or unknown property pass verify_token. | Enforce the declared AccessTokenClaims field/type/identifier contract in addition to signature/time/audience checks. This is a typed-contract defect, not evidence of a remotely forgeable signature. |
| T01-R5 | P2 | Set an isolated synthetic model-key value to SUCCEEDED and invoke doctor. Serialized-JSON string replacement redacts the structural status enum into [REDACTED], breaking the stable envelope. | Redact secret-bearing free values without rewriting structural keys or trusted control enums; retain the public-path regression. |

Initial evidence: `evidence/S00/T01-2026-11-15/review/adversarial-initial.txt`
(**12 failed**) and `review/redaction-initial.txt` (**1 failed**). These failures were
observed before the lead's fixes. All test data/keys are synthetic and created in
temporary directories; no device private-key bytes were read by this review.

## Positive observations and scope limits

- New CLI tests call the actual module subprocess, validate the declared Response schema,
  distinguish no-provider configuration from measured support, and require explicit init.
- Runtime uses real Ed25519 signatures, process UID and private file permissions; no mock
  provider is relabeled as a genuine LLM integration. The local actor comes from the adapter.
- Exact greetings create no commitment or tool call. Mixed requests return truthful
  NOT_CONFIGURED, and later unqualified discovery execution is blocked explicitly.
- Application dependencies are injected, while CLI composes identity and receipt adapters.
  No provider SDK type was introduced into domain code.
- Local authorization is an explicit tenant/space guard, exercised even at N=1. There is
  no business repository in T01, so repository counter assertions and full IDN case proof
  remain assigned to S00-T05 rather than claimed here.
- The documented owner-only-file fallback is the tested POSIX path. Keyring preference,
  other operating systems and future SERVER token/network flows are not qualified here.
- The new CLI intentionally removes access to unqualified legacy candidate discovery and
  compiler commands until their owning tasks pass. This transition must remain explicit
  in release/handoff notes; it is not a claim that those commands are implemented now.
- Existing candidate compiler/package drift and missing optional model SDK still affect
  broader retained suites. Their failures must be retained and scoped to later tasks;
  a passing T01 suite cannot turn them into slice PASS.

No live model/provider, durable product ledger/worker, native install, release gate or
external integration was tested. The lead's initial coverage report describes the four
newly delivered modules only and does not qualify downstream retained code. An unchanged
full-suite failure must remain visible in the task receipt.

## Recheck

The fresh-context reviewer reran the independent negative suite plus T01 CLI and identity
suites after correction: **36 passed** (15 independently selected adversarial instances).
The additional redaction sentinels `false` and `status` also preserve valid protocol output.
The only warning observed was an unrelated installed pytest-asyncio fixture-loop-scope
deprecation; it is not a SECMA assertion failure.

- R1 resolved: nonblocking credential open plus descriptor regular-file/mode/owner check;
  the real FIFO fault returns a diagnostic within the test's bounded subprocess timeout.
- R2 resolved: non-object identity JSON is rejected as an authentication failure; all
  three scalar-corruption CLI paths are typed and have no traceback.
- R3 resolved: canonical bytes use ASCII escapes, reject nonfinite numbers and validate
  string object keys recursively.
- R4 resolved: local typed claims require exact keys, string/integer types, ULID IDs and
  existing signature/audience/time/scope checks; all real-signature malformed variants deny.
- R5 resolved: recursive leaf redaction preserves structural keys and trusted protocol
  control enums, avoiding serialized-JSON replacement and its syntax/enum corruption.

**Accepted for this contribution scope.** No remaining P0/P1 finding was observed in the
reviewed T01 code. Before recording completion, the lead must bind these hashes into its
final receipt and record the adapter ownership refinement. The current tests now use
the exact declared test_a01/a02/a03 node IDs; the reviewer verified the mapping.
Those closeout steps are not a
new runtime acceptance claim from this reviewer.

The reviewed source/test hashes, exact fresh command and output digest are in
`evidence/S00/T01-2026-11-15/review/recheck.json`. Initial red evidence remains intact.
No slice seals, full SOC/IDN case closure or whole-requirement PASS are issued here.
Remaining candidate asset/optional-SDK qualification belongs to subsequent bounded work;
its observed failures must remain visible in the lead's handoff.


## Final profile and ownership recheck

After the documented `init --profile local` option and matching negative case landed,
the reviewer independently reran the three suites: **37 passed**, including all 15
reviewer-selected adversarial instances. `--profile server` returns typed INVALID_INPUT
before initialization; the default/local path succeeds. The declared A01/A02/A03 node
IDs now resolve, and the task ownership registry includes the two reviewed adapters
and package metadata. Source/test/registry hashes and exact observed output are in
`review/final-profile-recheck.json` and `review/final-profile-recheck.txt`.

Final disposition remains **ACCEPTED for the reviewed S00-T01 contribution scope**.
No remaining material finding was observed after this recheck. The lead's delivery
receipt must preserve the broader candidate failures and later mandatory runtime gates;
this report does not authorize skipping any of them. No runtime source or canonical
state was edited by the reviewer.


## Final delivery test-snapshot recheck

The lead added an actual CLI receipt-path filesystem fault and portable, opt-in coverage
bootstrap/configuration. The reviewer confirmed all five runtime source hashes are
unchanged from the accepted profile recheck, inspected the new test/infrastructure and
reran the complete four-file delivery lane: **45 passed**, including the 15 independent
adversarial instances. Occupying the receipt parent path with a real file produces typed
BLOCKED/INTERNAL_ERROR, no traceback and no fabricated evidence reference.

Final source/test/infrastructure hashes, exact observed command/output and environment
are retained in `review/final-delivery-recheck.json`; previous evidence is preserved.
The lead's coverage report was inspected: **96% combined delivery-scope coverage** for
five runtime modules, including the active evidence adapter. That measurement was not
repeated by this bounded review and does not describe retained candidate modules.

Final acceptance remains limited to **S00-T01 contribution scope**. There is no new
runtime finding, no live provider proof, no whole-case closure and no slice PASS claim.
