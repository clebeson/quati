# S01-T01 optional-fields focused review, 2026-11-18

Reviewer: independent Sonnet 5.5 session, not the implementer. Read-only review. Authored only this file.
No test execution, git mutation, delegation or provider/live access. No broad suite was run.
Bash was unavailable in this session, so I used file reads only. I did not re-run the 2 new cases
and I do not independently confirm the reported "passed in development" result.

## Read
- `tests/integration/cli/test_s01_optional_classification.py` (whole file, 1 test x 2 parameters).
- `src/quati/application/ask.py` lines 495-525, including `AskSession.displayed_classification` (507-515).
- `docs/implementation/S01_RUNTIME_CONTRACT.md` section 1 (public projection paragraph) and section 2
  ("Serialization preserves the input's optional-field presence").
- `tests/integration/cli/test_s01_conversation.py` lines 1-90 (fixtures `workspace`, `command`, and `test_a01`).
  Not read: `s00_t04_support.py`, so I did not see the actual contents of `WORK`.

## Contract vs. code vs. test
Contract: the public projection is schema-shaped and labelled `SCHEMA_VALIDATED`. Public `reason_code` is
`CLASSIFICATION_VALIDATED`. "Any present `commitment_ref` is null." Optional-field presence is preserved.
The raw proposal is retained only via `classification_sha256`.

Code (`ask.py:507-515`): returns None without a classification. Otherwise it copies the proposal and, only in the
`SCHEMA_VALIDATED` stage, overwrites `reason_code` and sets `commitment_ref = None` **only if the key is present**.
The guard at line 513 is exactly the branch that was uncovered. The code matches the contract.

Test expectations match the contract:
- Line 22 compares against `proposal | {'reason_code': 'CLASSIFICATION_VALIDATED'}`. This requires reason_code
  replacement, absence of an invented `commitment_ref`, no dropped or added keys, and the preserved `confidence` value.
- Lines 23-24 state the absence and the presence of `confidence` explicitly.
- Lines 26-27 hash the raw proposal, including the untrusted `reason_code`. That distinguishes the raw hash from
  the sanitized projection, as the contract says.
- Line 28 checks that the untrusted free text appears nowhere in the printed response.
- Line 29 keeps the S00 invariants (no tool calls, not launched, not delivered).

## Discrimination
Mutants I judge this test kills, by inspection (no mutation run):
- Unconditional `public["commitment_ref"] = None` (the likely pre-fix shape): fails lines 22-23. This is the target.
- `reason_code` not sanitized: fails lines 22 and 28.
- `confidence` dropped, or injected as null when absent: fails lines 22 and 24. The two parameters cover both sides.
- Hash taken over the sanitized projection: fails lines 26-27.

Gaps, non-blocking:
- The other branch, a **present** `commitment_ref` becoming null, is not asserted here. It is covered only if `WORK`
  in `test_a01` carries the key. `test_a01` expects `proposal | {reason_code}`, so `WORK`'s value must already be
  null or absent. I did not read `WORK`, so I cannot tell whether a present non-null ref is exercised anywhere.
  A one-line case with a non-null model-supplied `commitment_ref` would close it, and would also prove that
  free model strings in that field are not displayed. It is optional, since the contract sentence is
  otherwise unproven only by inspection.
- The `FAIL_CLOSED` path (stage guard false) is not in this file. It is covered by the migrated S00 tests, per my earlier review.
- This file does not run the JSON Schema validator on the output, unlike `test_a01`. Schema validity of the
  absent-field shape is therefore asserted only indirectly.
- Line 23 is implied by line 22 (equality with a dict without the key). It is redundant but harmless and explicit.

## Isolation
Good. The reused `workspace` fixture clears all `QUATI_*` variables, points config and data to `tmp_path`,
registers a scripted fake provider, seeds IDs and fixes the clock. There is no network, no sleep and no
wall-clock read in the new file, and the fixtures use monkeypatch so nothing leaks between cases.
Caveats:
- The import `from test_s01_conversation import ...` is a sibling-module import. It relies on the pytest
  import mode putting this directory on `sys.path`. It also re-imports `WORK`, `classified` and `final` through
  that module rather than from `s00_t04_support`. It works only if pytest runs from the existing layout.
  This is a coupling, not a defect, and the case ran in development. A direct import would be more robust.
- The script supplies one classification plus three finals. I did not verify that unconsumed script entries are
  tolerated, though the same shape is used by `test_a01`.
- Test tier: the docstring says L2 scripted provider. That is honest. It is not real-provider proof.

## Verdict
**ACCEPT the 2 new cases** as a discriminating, isolated, contract-matching test of the missing-optional-`commitment_ref`
branch at `ask.py:513`. Expectations match S01_RUNTIME_CONTRACT sections 1-2. No production change is needed.
The existing fresh-context review remains valid for the untouched code, as stated. Optional follow-up (not required):
add a present non-null `commitment_ref` case, and confirm that the 99.74% branch gap closes on the root's next coverage run.
Not verified by me: the 2 passes, the coverage change, and `WORK` contents.
