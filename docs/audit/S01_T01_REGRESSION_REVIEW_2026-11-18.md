# S01-T01 S00 regression-migration review, 2026-11-18

Reviewer: independent Sonnet 5.5 session, not the implementer. No source, test, state or
LOG changes. No git mutation, delegation or provider/live access. Authored only this file.
The shell wrapper prints `/home/clebeson/tmp/claude-*-cwd: Permission denied` on every call.
That is a harness scratch-file problem, unrelated to results.

## Read
S01_RUNTIME_CONTRACT.md (read in the previous task and unchanged since; I did not re-read it);
S01_T01_DESIGN.md "S00 regression migration" (lines 109-121); DECISION_RULES.md section 3.1 (the fail-closed literal);
the full `git diff` of the 8 named test files (73 insertions, 24 deletions); the helpers
`stable` / `comparable` / `assert_social` / `chat`. I did not read the historical logs.
`git status` shows src is unchanged since the accepted retest.

## Executed command (actual child status)
`record_evidence.py --evidence-dir evidence/S01/T01-2026-11-17/regression-retest -- python -m pytest -q -p no:cacheprovider <13 selectors from regression-selectors.json>`,
run through `subprocess`.
- Recorder exit 0. Manifest `exit_code` 0 (child). Pytest: **28 passed in 27.65s**. This matches the stated 28 cases.
- Evidence: `evidence/S01/T01-2026-11-17/regression-retest/20261118T124011Z-85e2ea4e/`.
- No other suite was run. I infer nothing about the broad run or about coverage.

## Does the migration weaken safety or only implement the approved contract?
**It implements the contract; I found no weakening.**

1. **Chat vs one-shot comparison.** Previously `stable(chat) == stable(ask)`. Now `stable(chat, conversation=True)` must:
   - find the metadata with exactly the 4 keys;
   - require a nonempty string `id`, an `int` revision >= 1 (`type() is int`, so bools are rejected),
     `lifetime == PROCESS_ONLY` and `continues_after_exit is False`;
   - recompute the SHA-256 over the full response with `evidence_refs: []` and compare it to the receipt `output_hash`.

   Only after that is `conversation` popped. Everything else is still compared for equality
   (status, authorization, tool_calls, errors, evidence). The one-shot side uses the default
   `conversation=False` and now **asserts that the key is absent**, which is a new check.
2. **Session-level checks.** Both `chat()` helpers now assert a single conversation ID across the session and
   revisions exactly `1..N`. This directly exercises the contract's ownership and counter rules,
   including after failed turns, in `test_soc_01_fault_chat_jsonl_session...`.
3. **`classification is None` replaced** by the exact fail-closed literal plus `classification_stage == FAIL_CLOSED`.
   The literal is hard-coded in the tests and **matches DECISION_RULES 3.1 word for word**. It does not
   reuse the implementation's `fail_closed()`, so the check is independent. The provider error, `launched/delivered/commitment_id`,
   tool_calls=[], "text absent" and request-count assertions are all unchanged.
4. **The seven-key subset replaced by the full projection** (`dict(evil, reason_code="CLASSIFICATION_VALIDATED", commitment_ref=None)`, stage `SCHEMA_VALIDATED`).
   This is stricter. Any leaked model free text in `reason_code` or `commitment_ref`, or any extra key, now fails. The raw hash assertion is unchanged.
5. **`test_pol_01`.** The restart one-shot is still compared in full with `comparable(restarted)`. The in-session turns get
   ID/revision `[1,2]` checks. The replay-denial, `handler_calls == []` and `model_saw == 3` assertions are untouched.
6. No skip, xfail, threshold, refusal or capability expectation was edited. The `assert_social` forwarding fix is in the diff, and its tests pass.

Residual, non-blocking:
- The helper is duplicated in 3 files (`stable` x2, `comparable`). They are identical now, but could drift. Consolidation is debt, not a defect.
- A pure id/revision difference between two compared responses is normalized away by design. The session helpers cover it with the explicit `1..N` check, so it is not lost.

## Additional adversarial check (my choice; no test files changed)
Target: the changed normalization boundary, i.e. could `stable(...)` now hide a defect that the old exact comparison caught?
Method: a throwaway script at `/tmp/s01_adv/adv.py` (outside the repo, run with `python -I`) imports the real
`tests/unit/s00_fix8_support.stable`. It patches only that module's `receipt()` lookup to return a controlled hash, then feeds mutated synthetic responses.
Results (all as expected):

| Mutation | Outcome |
|---|---|
| valid metadata | accepted |
| metadata missing (`conversation=True`) | rejected (KeyError) |
| extra key in `conversation` | rejected |
| `lifetime="DURABLE"` | rejected |
| `continues_after_exit=True` | rejected |
| `revision` 0 / `True` / `"1"` | each rejected |
| empty `id` | rejected |
| receipt hash mismatch | rejected |
| one-shot response carrying `conversation` | rejected |
| other field (`reason`) differs between two responses | still unequal after normalization |
| only id/revision differ | equal (the intended normalization) |

The real hash comparison against live receipts is exercised by the 28 passing tests. My patched `receipt()` only isolates the logic. This is a helper-level check, not a re-proof of the product path.

## Omissions
No full or coverage run (root runs it next). No mutation testing. No real-model proof. Evidence binds to the dirty working tree.
My check covers the helpers only, not the `test_approval_injection` fixtures beyond the 28 passing cases.

## Narrow verdict
**ACCEPT the S00 regression migration as an implementation of the approved S01 contract changes, not a weakening of any S00 safety assertion.**
The 28 selected cases pass (child exit 0). This is limited to the 8 named files and the 13 selectors.
