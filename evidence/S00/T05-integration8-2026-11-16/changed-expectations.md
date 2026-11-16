# Changed expectations of existing tests — integration step 8 (2026-11-16)

Every assertion of a test that existed at commit a3fb55a and that this step changed, with the old value, the
new value and the citation. Line numbers are those of the file after this step. New tests (the files
`tests/unit/test_s00_integration8.py`, `tests/integration/cli/test_s00_integration8_public.py` and the tests
appended to the two harness test files) are not listed: they change no existing expectation. No test was deleted,
no skip or xfail was added and no equality was loosened to membership, with the one exception of row 22, which
is a consistency check of the test's own data and is stated as such.

Citation "OD" = owner decision 2026-11-16: English and Portuguese only (the S00 social table supports no other
language; text of another language is not social-only and goes to the model path).

## Owner decision: English and Portuguese only

| # | file:line | old expectation | new expectation | citation |
|---|---|---|---|---|
| 1 | tests/unit/test_cli_service.py:27 | case `('hola', '¡Hola!')`: exit 0, GREETING text `¡Hola!` | case replaced by `('boa noite', 'Olá!')`; `hola` is asserted to be BLOCKED `NOT_CONFIGURED`, exit 3, with no `text` (lines 35-37) | OD |
| 2 | tests/unit/test_s00_fix6_authz_ask.py:189-190 | case `("Wie geht es dir?", "Hallo!")` | case `("Tudo bem?", "Olá!")` | OD |
| 3 | tests/unit/test_s00_t04_edges.py:41-49 | `ask("Wie geht es dir?")` is `(0, "Hallo!")` | `ask("Como vai você?")` is `(0, "Olá!")` with no model request; `ask("Wie geht es dir?")` is a non-success with no `text`, and the model was asked | OD |
| 4 | tests/unit/test_s00_t04_fixes.py:74-83 | `social_match` replies: "Buenos días, ¿qué tal?" → `¡Hola!`; "Salut, ça va ?" → `Salut!`; "Guten Tag, wie geht es Ihnen?" → `Hallo!`; "Wie geht es dir?" → `Hallo!` | the same four texts → `None`; the localized-reply rule is asserted on "Bom dia, tudo bem?", "Boa tarde, como vai?", "Tudo bem com você?" → `Olá!`; one assertion added for a marker after a Portuguese pleasantry | OD |
| 5 | tests/unit/test_s00_t04_fixes.py:88-90 | `ask("Buenos días, ¿qué tal?")` is `(0, "GREETING", "¡Hola!")` | `ask("Bom dia, tudo bem?")` is `(0, "GREETING", "Olá!")` | OD |
| 6 | tests/unit/test_s00_t04_fixes.py:103-106 | parameter `("Wie geht es dir?", "Hallo!")` | parameter `("Tudo bem com você?", "Olá!")` | OD |
| 7 | tests/unit/test_s00_t04_fixes.py:121-127 (`test_p1_1_social_only_text_cannot_fail_on_the_provider`) | `ask("Wie geht es dir?")` → SUCCEEDED `Hallo!` (twice: empty model reply, provider failure) | `ask("Tudo bem com você?")` → SUCCEEDED `Olá!` (twice); the typed provider failure of "Wie geht es dem Projekt?" is unchanged | OD |
| 8 | tests/unit/test_s00_t04_fixes.py:134-137 (`test_p1_1_a_model_timeout_cannot_reach_social_only_text_...`) | `ask("Wie geht es dir?")` → SUCCEEDED `Hallo!` | `ask("Tudo bem com você?")` → SUCCEEDED `Olá!`; the DEADLINE_EXCEEDED of the other text is unchanged | OD |
| 9 | tests/unit/test_s00_t04_fixes4.py:53-55 | `ask("Wie geht es dir?")` → `(0, "SUCCEEDED", "Hallo!", [])` | `ask("Como vai você?")` → `(0, "SUCCEEDED", "Olá!", [])` | OD |
| 10 | tests/integration/cli/test_s00_fix8_social_timeout.py:31-35 | `("こんにちは", "Hello!")` is a table greeting unaffected by a model timeout (exit 0) | table greeting `("Boa noite, obrigado", "Olá!")`; "こんにちは" is in `SOCIAL_LOOKING`: a text outside the table whose classification timeout is DEADLINE_EXCEEDED, exit 5 | OD |
| 11 | tests/unit/test_s00_fix7_social_authz.py:60-97 (`SAMPLES`, `REQUIRED_LANGUAGES`) | 41 samples of 14 languages, each answered by the table with the reply listed; `REQUIRED_LANGUAGES` = 14 languages | `SAMPLES` keeps the 17 English and Portuguese samples and gains 3 Portuguese ones; the 24 samples of the other twelve languages are `REMOVED_SAMPLES` and are asserted NOT social (rows 12 and 15); `REQUIRED_LANGUAGES == {"en", "pt"}` | OD |
| 12 | tests/unit/test_s00_fix7_social_authz.py:269-292 (new test beside the changed table: `test_e_a_sample_of_a_removed_language_is_never_answered_by_the_table`) | each removed sample: GREETING, exit 0, zero model requests, in six provider states | each removed sample: BLOCKED `NOT_CONFIGURED` (exit 3) with no provider; BLOCKED `EVIDENCE_INSUFFICIENT` / `NO_VERIFIED_EXECUTION` (exit 4) under a scripted social label; never a GREETING | OD |
| 13 | tests/unit/test_s00_fix7_social_authz.py:98-99 (`ONE_SHOT`) | last two texts "こんにちは", "Merhaba!" (reply `Hello!`) | "Bom dia!", "Obrigado!" (reply `Olá!`) | OD |
| 14 | tests/unit/test_s00_fix7_social_authz.py:325 and :335 | reply map with `{"Merhaba!": "Hello!"}`; chat line "こんにちは" equals its one-shot ask | reply map with `{"Obrigado!": "Olá!"}`; chat line "Boa tarde" | OD |
| 15 | tests/unit/test_s00_fix7_social_authz.py:688-710 (`test_d1_table_is_data_with_unicode_aware_matching`) | table languages `>= REQUIRED_LANGUAGES` (14); "İyi günler" → language `tr`; "नमस्ते!" → language `hi`; "merci" → `Bonjour!`; "спасибо" → `DEFAULT_REPLY` | table languages `== {"en", "pt"}`; every removed sample → `None`; "İyi günler" → `None` while `fold("İ") == "i"` and "Hİ" → `Hello!`; "नमस्ते!" → `None`; "merci", "спасибо" → `None`; "obrigada" → `Olá!`; "thank you" → `DEFAULT_REPLY` | OD |
| 16 | tests/unit/test_s00_fix7_social_authz.py:735-736 | `MARKERS == {"urgent", "urgently", "urgente", "dringend"}` | `MARKERS == {"urgent", "urgently", "urgente"}` | OD |
| 17 | tests/unit/test_s00_fix8_social_outcomes.py:44-49 | `MARKER_WORDS` with "dringend"; ten `URGENCY_PHRASES` | three marker words; five urgency phrases; the six removed ones are `REMOVED_URGENCY` and asserted not social next to a greeting (lines 124-127) | OD |
| 18 | tests/unit/test_s00_fix8_social_outcomes.py:58 | `LANGUAGES` = 14 codes (so `SOCIAL_TABLE` order equals them, line 91) | `LANGUAGES = ("en", "pt")` | OD |
| 19 | tests/unit/test_s00_fix8_social_outcomes.py:136-138 | `is_social("Ciao!") and is_social("Buongiorno, come stai?")` | `not is_social("Ciao!") and not is_social("Buongiorno, come stai?")` | OD |
| 20 | tests/unit/test_s00_fix8_social_outcomes.py:180-188 (`AUDIT_SOCIAL_NOW_NOT_SOCIAL`) | four audit texts expected social by the audit are not social (length, format characters) | nine: plus "İyi günler", "MERHABA", "こんにちは", "你好", "Привет, как дела?" | OD |
| 21 | tests/unit/test_s00_fix8_social_outcomes.py:308-312 | `("hallo ☺️", "Hallo!")`, `("merci 😄😁😃", "Bonjour!")` | `("olá ☺️", "Olá!")`, `("obrigado 😄😁😃", "Olá!")`; the two old texts are asserted not social in the new test at lines 317-319 | OD |
| 22 | tests/unit/test_s00_fix8_social_outcomes.py:166-168 | `set(WORK_FRAGMENTS) == set(LANGUAGES)` (a check of the test's own data) | `set(LANGUAGES) < set(WORK_FRAGMENTS) and len(WORK_FRAGMENTS) == 14`: the work fragments of the twelve removed languages are kept and still asserted not social after every table phrase | OD |
| 23 | tests/unit/test_s00_fix8_social_outcomes.py:328-343 (punctuation table) | twelve rows whose phrase is of a removed language are `True`: "¡Hola!", "¿Qué tal?", "こんにちは。", "你好！", "你好、谢谢。", "¡Hola! ¿Qué tal?", "Buenos días, ¿qué tal?", "Hello! — ¿Qué tal?", "مرحبا، شكرا؟", "नमस्ते।", "«Bonjour»", "„Hallo“" | the same twelve texts are `False` (their language, not their punctuation); twelve rows with the same punctuation around a Portuguese phrase are `True`: "¡Olá!", "¿Tudo bem?", "olá。", "oi！", "olá、obrigado。", "¡Olá! ¿Tudo bem?", "Bom dia, ¿tudo bem?", "Hello! — ¿Tudo bem?", "olá، obrigado؟", "olá।", "«Bom dia»", "„Olá“" | OD |
| 24 | tests/unit/test_s00_fix8_social_outcomes.py:373-382 (`test_x4_reply_selection_is_unchanged`) | "merci" → `Bonjour!`; "das ist dringend, hallo" → `Hallo!`; "es ist dringend. Danke!" → language `de`; "спасибо" → `DEFAULT_REPLY` | those four → `None`; the same rules on "obrigado" → `Olá!`, "isto é urgente, olá" → `Olá!`, "é urgente. Obrigada!" → language `pt`, "thanks" → `DEFAULT_REPLY` | OD |
| 25 | tests/unit/test_s00_fix8_social_outcomes.py:388-394 (`SOCIAL_SAMPLE`, `WORK_SAMPLE`) | `("Hallo, es ist dringend", "Hallo!")` and `("Ciao, come stai?", "Ciao!")` answered identically by ask and chat, exit 0 | both are the first entries of `WORK_SAMPLE`: NOT_CONFIGURED (exit 3) without a provider, BLOCKED / `NO_VERIFIED_EXECUTION` (exit 4) under a social label; `SOCIAL_SAMPLE` holds "Olá, tudo bem?" and "Boa noite, como vai?" instead | OD |
| 26 | tests/unit/test_eval_harness_soc01.py:842-843 | printed leg c summary `valid 6 of 6` (3 texts × 2 runs) | `valid 10 of 10` (5 texts × 2 runs) | OD (dataset `soc01_gate.json`: "Hola, buenos días" and "Guten Morgen, wie geht es dir?" moved from leg a to leg c) |
| 27 | tests/unit/test_eval_harness_soc01.py:1059-1064 | SOC-01 estimate: 9 table texts, `profiles_probed == 9 + 60 + 1`, `asks_with_model == 60 + 2`, typical ask calls `30*3 + 20*5 + 10*3 + 3 + 5`, `max_calls == 70*4 + 62*8` | 8 table texts, `8 + 80 + 1`, `80 + 3`, `50*3 + 20*5 + 10*3 + 3 + 5 + 3`, `89*4 + 83*8` | OD (same dataset change) |
| 28 | tests/unit/test_eval_harness_soc01.py:1503-1504 | printed estimate `typical 1115, ceiling 1791`, `US$0.67`, `US$1.08` | `typical 1235, ceiling 2035`, `US$0.74`, `US$1.22` | OD (same dataset change) |
| 29 | tests/unit/test_eval_harness_soc01.py:1937-1939 | social-table preflight on the real product: `table_texts 9`, `model_texts 8` | `table_texts 8`, `model_texts 10` | OD (same dataset change) |

## LOG-0044 decision D7, LOG-0045 and LOG-0046 open items

| # | file:line | old expectation | new expectation | citation |
|---|---|---|---|---|
| 30 | tests/unit/test_selection_none_fits.py:36-49 (REG-08 fault step) | `honest_no_capability("MODEL_TIMEOUT")` (a helper no product path called) is SUCCEEDED with `outcome NO_CAPABILITY`, `next_action report_no_capability` | the helper is removed; the fault is observed on the ask path: a model timeout after the search is BLOCKED `DEADLINE_EXCEEDED`, exit 5, `result_kind BLOCKED`, `launched` false, no fixture result, one non-executed step, zero handler invocations | LOG-0044 decision D7 (no SUCCEEDED answer without a validated execution); LOG-0046 open item "unused honest_no_capability helper"; docs/testing/ACCEPTANCE_CASES.json REG-08 `fault_case` amended in this step |
| 31 | tests/unit/test_eval_harness_grader.py:75-76 | a non-SUCCEEDED Response fails exactly `['exit_0_succeeded']` | fails exactly `['status_succeeded_no_error']` (the rule is renamed for what it reads; the exit code keeps its own rule `exit_code_0`) | LOG-0045, harness finding H29 |
| 32 | tests/unit/test_eval_harness_soc01.py:1240-1245 | `product_asset_digest` accepts the fields `asset_digest`, `assets_digest` and `asset_digests` (a string or an object) | only `behavior.asset_digest`; the other two fields give `None` | LOG-0046 X15 (one `asset_digest` exposed by `doctor`); M01 `DoctorReport.behavior.asset_digest` |
| 33 | tests/unit/test_eval_harness_soc01.py:1197-1202 (`_prereg_facts`, setup) | a registrable tree needs no product asset digest | the registrable facts carry the product asset digest and `asset_tree_equals_product_asset_digest: True` | LOG-0046 X15 |
| 34 | tests/unit/test_eval_harness_soc01.py:1530-1543 | with a clean tree and a doctor identity (no asset digest) the gate-protocol refusal is gone | the run is refused when the doctor identity has no asset digest and when its digest differs from the evaluator's digest of the asset files; the refusal is gone only with the real digest | LOG-0046 X15 |
| 35 | tests/unit/test_s00_integration7.py:47-49 (`LOCAL_REASONS`) | `LOCAL_STORE_REASONS == ('audit_unavailable', 'audit_store_unavailable', 'state_dir_unsafe')` | plus `'feature_report_not_stored'` (the probe refusal always exited 4 through a literal; it is now settled by the shared rule, and M01 exit table row 4 names the four reasons) | M01 "Exit codes (stable)" rows 4 and 5; M17 probe table; LOG-0045 (local-store refusals are not provider outages) |

## Dataset

`tests/evals/datasets/soc01_gate.json` (never used live): leg a holds "Hi, how are you?", "Olá, tudo bem?",
"Good morning", "Bom dia, como vai?", "Thank you!", "Obrigado!" (was: with "Hola, buenos días", "Bonjour, comment
allez vous", "Guten Morgen, wie geht es dir?", "Ciao, come stai?"); leg b is unchanged; leg c gains "Hola, buenos
días" and "Guten Morgen, wie geht es dir?"; the last chat turn "Guten Morgen, wie geht es dir?" is graded as leg c
(was leg a). Citation: OD. The cap01, cap02, behavior and held-out datasets are byte-identical
(`test_new_datasets_have_the_declared_schema_and_the_sealed_sets_are_unchanged` pins their hashes).
