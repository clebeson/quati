# S00 runtime implementation contract

**Status (2026-11-16):** contract for slice S00. The deliveries of S00-T01 to S00-T04 exist in `src/`: the local identity bootstrap and the CLI boundary, the contract schemas, trusted policy and behavior compiler, the capability registry and fixture discovery, and the provider layer with the context envelope and `quati ask` / `quati chat` over the four discovery tools; the S00 form of `quati trace show|explain` (M26) was added by fix round 7. The live evaluation harness of S00-T05 is in `tests/evals/`. No S00 gate is sealed for the current code: the gate states are in `docs/implementation/implementation_state.json`, and the last accepted live run bound an earlier code digest (requalification pending, `docs/governance/LOG.md`). An earlier candidate implementation was removed as non-conforming (LOG) and replaced by these deliveries. Where this file and `docs/architecture/BOUNDARY_CONTRACTS.md`, `docs/architecture/TYPE_CATALOG.md` or `contracts/*.schema.json` disagree on a signature or wire shape, those files win.

Scope: synchronous fixture-only discovery. No job, worker, durable acceptance, external write, arbitrary plugin loading, memory or production readiness is claimed. M01/M02/M14/M15/M17/M25/M26/M30/M31 are partial contributions in S00; full module gates remain open until every applicable later-slice obligation passes.

## Interfaces and trust

- `quati chat [--jsonl]` (M01-FR-04, M01-AT-03, M01-RT-03; owned by S00-T01) is a line-based terminal session and is part of the S00 target contract: each input line is one turn through the same use case as the equivalent one-shot command, with the same identity, authorization, approval, exit-code and error-code rules; it keeps no state outside the ledger and the M31 context envelope; `--jsonl` prints exactly one Response envelope per input line on stdout. In S00 a turn is an `ask`; `/status`, `/tell`, `/approvals`, `/approve` and `/deny` return the same error as their one-shot commands until those commands exist (S02). The normative rules are in `docs/prds/M01.md` § Chat session. It is not a GUI or full-screen TUI.
- CLI commands return stable JSON Response envelopes. Exit codes are exactly the table in `docs/prds/M01.md` § Exit codes: 0 successful command execution, 1 `INTERNAL_ERROR`, 2 invalid input, 3 missing configuration, 4 `DENIED`, `BLOCKED`, `UNAVAILABLE` or `CONFLICT` not caused by a provider, 5 provider failure (`TEMPORARILY_UNAVAILABLE`, `DEADLINE_EXCEEDED` or `OUTPUT_INVALID` from a model or tool provider), 6 worker tick with remaining or failed work. Unsupported future commands are errors, never successful placeholders. Delivered in S00: `quati init`, `doctor [--probe]`, `config validate`, `ask TEXT [--synthetic-evidence]`, `chat [--jsonl]`, `models probe`, `capabilities install|install-fixture|list|search|describe|disable`, `behavior validate|render PACKAGE [--root DIR]` and `trace show|explain` (S00 form, M26). Registered but not delivered, each answering UNAVAILABLE `UNSUPPORTED` (exit 4) that names its slice and reading or changing nothing: `status`, `tell`, `approve`, `deny`, `approvals list|revoke`, `inbox`, `messages`, `worker run|tick|install|uninstall`, `trace export|replay`, `spaces describe`, `policy show|diff|edit|apply` (S02); `config validate FILE`, `config diff|simulate|propose|apply|rollback`, `behavior propose|simulate|diff|promote|rollback`, `prefs show|set|expire|history|rollback`, `artifact register|show|revise|history`, `memory search` (S03); `brains reindex` (S04); `server`, `login`, `grants list` (S05). Two refusals that are not obvious from the table: exit 2 `CONFIG_INVALID` is returned by `config validate` when a check is INVALID, by `behavior validate|render` for a rejected package, and by every `ask` or `chat` turn while the active behavior package does not compile (reason `BEHAVIOR_PACKAGE_INVALID`, decided before the request text and the provider state are looked at); exit 4 UNAVAILABLE `TEMPORARILY_UNAVAILABLE` reason `state_dir_unsafe` (with `component`) is returned by any command whose data directory chain is not a private directory chain of the user, before anything is read or changed (M01 § Data directory). Every receipt carries `digests.code_digest` and `digests.asset_digest` (M01 § Data directory rule 5).
- Local principal originates from the process identity adapter, never model arguments. The S00 catalog contains only public synthetic local fixtures. No tenant-private data is imported.
- Capability discovery, description and invocation use `DiscoveryPort` and `RegistryPort` exactly as declared in `BOUNDARY_CONTRACTS.md`. Search returns at most five permitted candidates. Invocation validates enabled lifecycle, measured binding eligibility, local scope, effect, input and output schemas. Lifecycle and assurance are never self-declared by a definition (RFC-015 REG-01). Only explicitly registered fixture handlers execute; manifests cannot load code or grant permissions.
- The model is reached only through `ModelPort` as declared in `BOUNDARY_CONTRACTS.md`. The application owns evidence and final status; a model completion is never passed through as verified work. Provider SDK types remain inside the adapter.
- For nontrivial input, a typed classification precedes discovery. Invalid output has bounded retries. Classification is advisory; no classification can bypass invocation policy. Text that is social-only by the code-owned social table, which supports English and Portuguese only in S00 ("Displayed text and social outcomes" below), is answered deterministically with no model call. Mixed greetings and work do not match that path.
- A real tool probe must precede autonomous fixture invocation on each live run. `UNKNOWN` is not `SUPPORTED`. Doctor without an explicit probe reports configuration availability separately from measured support. The probe measures `tools`, `structured_output`, `streaming`, `timeout` and `concurrency` with nonce round-trips using the schemas the ask really sends (M17 probe table); a feature that was not exercised stays `NOT_VERIFIED`.
- Provider configuration uses `QUATI_PROVIDER` (the registered transport, M17), `QUATI_BASE_URL`, `QUATI_MODEL`, `QUATI_API_KEY_ENV` naming an environment variable containing the token, and explicit `QUATI_ALLOW_LIVE=1`. Never infer authorization from unrelated session credentials. For a transport that takes an endpoint: HTTPS only; reject URL credentials, query, fragment and redirects. No automatic fallback endpoint. Fixed request/tool/output/time limits bound each run. Configuring this is authorization for those bounded synthetic model calls, not any downstream external writes.
- Evidence records structured operation IDs, hashes, timing, usage, sanitized result codes and provenance. Default evidence omits raw request, tool arguments and model text. Synthetic live evaluations may explicitly capture their synthetic arguments and outputs; secrets remain redacted. Unknown cost remains null, never zero.
- Failed/blocked requests never claim completed work. A work request with no validated execution is never a success: "no installed capability fits" is `NO_CAPABILITY` with a typed non-success (rule 7 of "Displayed text and social outcomes"). Successful fixture output is labeled `FIXTURE_RESULT`, not completed professional research. Probe-only success is not routing competence.

## Verification contract

Tests begin red against CLI, policy/catalog, compiler and adapter ports. Offline injected-model tests are L1 harness integration, not L3. Live harness launches normal `quati ask` processes with natural-language requests; expected labels stay in evaluator only. It checks ordered search/describe/invoke, exact typed arguments/outcome, confusable target discrimination, greeting without work, policy rejection and prompt identity. Missing configuration returns BLOCKED with nonzero exit. No later slice starts until every S00 gate meets its required tier.

Contract schema changes in this audit occur before a released runtime exists. Historical source evidence is retained; newly generated evidence is append-only and identifies the implementation commit and file hashes.

## Fixture registration and evidence capture

The two confusable synthetic fixtures are registered by the S00 registry task through `RegistryPort`; activation is an explicit local operator action recorded in evidence, not a claim made by the definition, and it never approves external capability effects. A newly activated definition is visible on the next ask without prompt edits.

`quati ask TEXT --synthetic-evidence` explicitly opts into recording the synthetic
model tool arguments/results for evaluation. Default receipts contain hashes only.
Do not use the opt-in for private business inputs. The S00 smoke is not the sealed
30-case competence benchmark (MOD-01). MOD-01 is a precondition for enabling autonomous
routing or role promotion (S04 or later), not for S00; promotion to a calibrated model role
remains blocked until that separate benchmark is executed and reviewed. S00-GATE-02 itself
requires CAP-01 and CAP-02 to pass in 30 of 30 repeated live runs each, with logged
trajectories and recorded provider/model identity. Each case uses 10 paraphrases × 3 runs, shuffled catalog order, zero unauthorized effects, and exact model/prompt/config/catalog digests; failed runs remain in the denominator (TEST_EXECUTION_PROTOCOL.md).

## Independent-review fail-closed refinement

S00 only displays deterministic greetings or application-owned synthetic fixture
findings. A model classification of `simple_answer` cannot make unverified work
appear complete. General model-generated informational answers and localized
professional delivery remain S01/later behavior until their evaluation gates pass.
The model's final text is hashed and can be inspected in synthetic evaluations; it
is not authoritative proof of completed work. Diagnostics and transport share the
same HTTPS endpoint validation, including port and whitespace checks.

### Displayed text and social outcomes (normative for S00; LOG-0039 F2 and F3, LOG-0041 D1 to D4, LOG-0044 X4 and D7)

These rules are code-owned. The model's classification is advisory: no label creates a social
outcome, and no label skips the work path. They replace the round 6 rules (greeting-only bag of
words, `CONVERSATION`, the no-action notice and `NO_GREETING_TEMPLATE`), which no longer exist.

1. **Application-owned text only.** Every word `quati ask` and `quati chat` display is produced by
   the application: a deterministic greeting template, a rendered `FIXTURE_RESULT`, or a fixed
   application message. Text written by the model is never displayed, in any result kind, and no
   outcome depends on it (an empty model reply has no failure mode of its own). It is recorded as
   `final_text_sha256` in the receipt (and in full only under `--synthetic-evidence`).
2. **Social-only text (D1; LOG-0044 X4).** The social table is data in `src/quati/domain/social.py`.
   A text that carries a request, a question or an instruction never matches it: every clause below
   must hold, and a text that fails any of them is not social-only (rule 3 applies to it).
   - *Table.* S00 supports **English (`en`) and Portuguese (`pt`) only** (owner decision of
     2026-11-16). Other languages are deferred and are not scheduled to a slice: a greeting,
     pleasantry, thanks or urgency phrase of any other language is ordinary text, is not social-only
     and goes to the model path (rule 3). Per language the table holds the phrases of three kinds
     (greetings, pleasantries such as "how are you", thanks) and one reply template. The English
     greetings include "good day", "howdy", "hiya", "greetings" and "yo". The phrase lists of
     `SOCIAL_TABLE` in that file are the normative table: a phrase is social only if it is listed
     there, and a phrase is added or removed only together with the review that the clauses "No
     free-standing function words" and "Cross-language review" require.
   - *Urgency.* The marker words are exactly `urgent`, `urgently` and `urgente`. The urgency
     phrases are exactly "this is urgent", "it is urgent", "isto é urgente", "isso é urgente" and
     "é urgente". They name no object and no action.
   - *No free-standing function words.* A demonstrative, a pronoun or a copula ("this", "it", "is",
     "isto", "isso", "é", "you", "do") is never a marker and never a one-word table entry. Such a
     word occurs only inside a fixed, fully listed phrase ("this is urgent", "how are you", "how do
     you do", "e você"), and a phrase matches only as a whole. "How do you do this?", "hi, is it
     urgent?", "como está isto?" and "hello, this" are therefore not social-only. The one-word
     greeting `yo` (required above) names only the speaker and no table phrase or marker gives it a
     verb or an object.
   - *Cross-language review.* No entry is an ordinary imperative or work word of the other table
     language. `salve` is not an entry: it is the Portuguese imperative "save" ("Salve isto, é
     urgente" is "Save this, it is urgent").
   - *Normalization.* Unicode NFKC, casefold, NFKC again; the casefold of the Turkish dotted capital
     I is a plain `i`. Every clause below is applied to the normalized text. Nothing is stripped
     from the input; unaccented spellings are table entries.
   - *Characters.* Every character of the normalized text is one of the following; any other
     character makes the text not social-only, so none is silently dropped:
     (a) a word character: Unicode general category letter (L), mark (M) or number (N);
     (b) whitespace: general category Zs, U+0009, U+000A or U+000D;
     (c) punctuation, exactly this set: the 32 ASCII punctuation characters
     ``! " # $ % & ' ( ) * + , - . / : ; < = > ? @ [ \ ] ^ _ ` { | } ~`` and U+00A1 ¡, U+00BF ¿,
     U+00AB «, U+00BB », U+2018 ‘, U+2019 ’, U+201A ‚, U+201C “, U+201D ”, U+201E „, U+2039 ‹,
     U+203A ›, U+2010 ‐, U+2013 –, U+2014 —, U+2015 ―, U+00B7 ·, U+3001 、, U+3002 。, U+300C 「,
     U+300D 」, U+300E 『, U+300F 』, U+30FB ・, U+060C ،, U+061B ؛, U+061F ؟ and U+0964 । (the
     ellipsis U+2026 and the full-width forms of `! ? , : ; ( )` become listed characters under
     NFKC);
     (d) an emoji of the allowlist, exactly: U+1F44B 👋, U+1F642 🙂, U+1F600 😀, U+1F603 😃,
     U+1F604 😄, U+1F601 😁, U+1F60A 😊, U+1F609 😉, U+263A ☺, U+1F64F 🙏 and U+2764 ❤. An
     allowlisted emoji may be followed by U+FE0F or by one skin-tone modifier (U+1F3FB to
     U+1F3FF), and U+200D may join two allowlisted emoji; anywhere else these three are "any other
     character". An emoji is never a phrase: a text of emoji alone is not social-only.
     Enclosed letters that NFKC does not decompose (negative squared and negative circled
     letters), regional-indicator letters, Braille, arrows and other symbols, other pictographs,
     format characters (zero-width, bidirectional and tag characters), control characters, line and
     paragraph separators, private-use and unassigned code points all fall under "any other
     character". Compatibility forms that NFKC turns into letters or digits (full-width,
     mathematical, circled, squared, parenthesized, superscript) become ordinary words and are
     matched as words, so they are never dropped either.
   - *Words and punctuation.* A word is a maximal run of word characters. A punctuation run is a
     maximal run of punctuation characters (whitespace or an emoji ends it) and has at most 3
     characters. A run is *attached* when it directly follows a word or directly precedes a word,
     and *free* otherwise. Before the first word, between two words and after the last word there
     is at most one free run (and, by definition, at most one run attached to the word before and
     one attached to the word after). "¡Olá! ¿Tudo bem?" and "hi — urgent: hi" satisfy this; a
     sequence of punctuation groups (Morse-like text such as `hello -.. . .-..`) does not.
   - *Length.* The normalized text has at most 120 characters and at most 12 words.
   - *Rule.* A text is social-only when its words, in order, can be cut completely into table
     phrases, urgency phrases and single marker words, with at least one table phrase. Matching is
     on whole phrases, never on a bag of words: any other word, and urgency alone, make the text
     not social-only.
   - *Limit of the rule.* The rule guarantees that no word and no character outside the listed sets
     is ignored. It cannot exclude a message encoded in the choice and order of listed phrases or in
     the few short punctuation runs it allows between two words; such a text names no object and no
     action to the application.
   - *Outcome.* A social-only text is answered by the application before the provider
     configuration, the feature report or the model is looked at: no model call, no tool, no
     registry read, no commitment. The Response is `SUCCEEDED`, exit 0, with no uncertainty:
     `result_kind = GREETING`, `result_status = RESPONDED`, `text` = the reply template,
     `text_source = application_template`, `display_lines = [text]`, `work_performed = false`,
     `actions_taken = []`, `provider_used = false`, `tool_calls = []`, `launched = false`. It is
     identical (apart from the request and trace identifiers and the receipt reference) in every
     provider state: no provider configured, configured but not probed, probed, model unavailable,
     invalid classification. `quati chat` gives the same Response for the same line.
   - *Reply language.* The reply templates are `Hello!` (English, also the fallback constant) and
     `Olá!` (Portuguese); there is no other. The reply is the template of the first greeting
     phrase in the text; a text without a greeting gets the template of the language of its first
     phrase. A phrase listed by both languages would belong to the first one in table order.
   - *Precedence.* The only exception to "identical in every provider state" is the M01 exit-code
     precedence: an active behavior package or statechart that does not compile is checked first
     and gives `BLOCKED` / `CONFIG_INVALID`, reason `BEHAVIOR_PACKAGE_INVALID`, exit 2, for every
     ask (social-only or not) in every provider state. Input validation (exit 2) and
     authentication (exit 4, `UNAUTHENTICATED`) precede it as for every command.
3. **Every other text goes to the model (D2).** It needs a configured provider with a current
   measured FeatureReport (`NOT_CONFIGURED` exit 3 or `UNSUPPORTED` exit 4 otherwise); then, before
   the first model call, it passes the admission check of M01 § Data directory rules 2 and 4 (see
   "Registry authorization" below); then it is classified and enters the tool loop. A text that mixes a greeting with a request
   ("Hi! What's my next appointment?") is not social-only and follows this rule. A classification
   `intent` of `social` or `simple_answer` on such a text is not an outcome: if the turn ends with
   no validated execution it is `BLOCKED` / `EVIDENCE_INSUFFICIENT`, reason
   `NO_VERIFIED_EXECUTION`, exit 4, with the `next_action` "S00 displays no model-written answers
   and no action was taken. Ask for work that an installed capability can do; the model text is
   not evidence of completion." It is never `SUCCEEDED`. The single `NO_SEARCH_ON_WORK`
   continuation is still issued whatever the label, and tool calls the model then makes are
   handled as for any work request.
4. **Greetings outside the table.** A greeting in a language or form the table does not list is
   not recognized by code. It follows rule 3: its handling is model-dependent (tier L3, measured
   live) and it cannot end `SUCCEEDED` without a validated execution. Code guarantees only that no
   write executes, that nothing claims work that was not validated and that no model text is
   displayed; which of the outcomes of rules 3 and 7 the model produces (including a read fixture
   that it searched, described and invoked, which is then a validated `FIXTURE_RESULT`) is a
   measured distribution, not a guarantee.
5. **`launched` (D3).** `data.launched` is `false` in every S00 ask and chat response, including
   when the tool loop ran and a capability executed: S00 has no ledger, so no commitment and no
   work item exists (M01-FR-02).
6. **Ids outside the shortlist (D4).** In an ask turn, `quati_describe` and `quati_invoke` of an id
   that this turn's searches did not return are refused with DENIED / `FORBIDDEN` /
   `NOT_IN_SHORTLIST`, whether the id is unknown, malformed, hidden, disabled or enabled. The
   registry is not consulted for it, so the reason cannot tell the model which ids exist
   (`docs/prds/M15.md`, invoke guard order).
7. **No capability is not a success (D7, LOG-0044 X5).** A request that is not social-only ends
   `SUCCEEDED` only as `FIXTURE_RESULT`, that is, after at least one handler executed and its
   outcome was validated (`PARTIAL` keeps its two meanings: a validated result followed by a
   refused step, or an executed handler whose outcome is unverified). When the model declares `NONE_FITS`, or its searches
   return no candidate and it invokes nothing, the result kind stays `NO_CAPABILITY` and the
   Response is a typed non-success: `UNAVAILABLE` / `UNSUPPORTED`, exit 4, `data.reason` =
   `NONE_FITS` or `NO_CANDIDATES`, `result_status` = `outcome` = `NO_CAPABILITY`,
   `work_performed = false`, `launched = false`, no `text`, `uncertainties` =
   [`NO_CAPABILITY`, reason], `error.message` "No installed capability can fulfil this request."
   and the `next_action` "No installed capability can do this and no action was taken. Run `quati
   capabilities list` to see what is installed, or ask for work that an installed capability can
   do." The status and code are those of an unusable capability in the M15 invoke guard table
   (rows 4 and 5) and of PRD_COMMON ("a missing optional integration returns typed
   `UNAVAILABLE` ...; it never returns a fabricated success"); no new status or code exists for it.

### Registry authorization (normative for S00; audit findings F4 and F5, LOG-0039)

Every registry read and write reachable from the command line or from an ask session passes
`AuthorizationPort` before any registry lookup or change, and its decision is logged as
`authz.decided`: `capabilities list|search|describe` and the `quati_search`, `quati_describe`,
`quati_invoke`, `quati_status` tools (`read`; operations `list`, `search`, `describe`, `invoke`,
`status`), the admission check of a work ask before its first model call (`read`, operation
`ask_admission`, once per work ask that has a configured provider with measured tool support),
the catalog digest of an ask receipt (`read`, operation `ask`, once per ask that reaches the model
path), `trace show|explain` (`read`, operations `trace_show`, `trace_explain`),
`capabilities install|install-fixture|disable`, including `--enable-fixture` (`manage`; operations
`install`, `install_fixture`, `disable`), and `models probe` / `doctor --probe` (`manage`,
operation `models_probe`). The resource is `registry:<tenant_id>`; the space that owns it is the
tenant's organization space, resolved from the identity directory and never from the request.
The exact rules are in `docs/rfcs/RFC-013_IDENTITY_TENANCY_SPACES.md` section 12.1 and
`docs/prds/M02.md` "S00 decisions".

A work ask checks the registry store, the audit log and the caller's `read` grant on the registry
(operation `ask_admission`, logged as `authz.decided`) before its first model call: an unusable
store is `state_dir_unsafe`, an unusable audit log is `audit_unavailable` and a missing grant is
DENIED `FORBIDDEN` with the M02 reason (`NO_SPACE_GRANT`), each with exit 4, zero model calls and no
dependence on the model (M01 § Data directory rules 2 and 4). If the catalog read at the end of an
admitted ask is nevertheless denied or cannot be logged, the receipt has
`digests.catalog_digest = null` and `catalog_access = <reason>`.
