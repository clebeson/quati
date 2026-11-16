# S00 runtime implementation contract

**Status (2026-11-15):** target contract for slice S00. Only S00-T01 (local identity bootstrap and the CLI boundary: `quati init`, `quati doctor`, `quati ask` returning normative Response envelopes) exists in `src/`. The earlier candidate policy, catalog, model adapter, packaged-asset copy, runtime compiler and live-eval harness were removed as non-conforming (see `docs/governance/LOG.md`); they are delivered again by their owning S00 tasks in `docs/implementation/work_packages/S00.md`. Where this file and `docs/architecture/BOUNDARY_CONTRACTS.md`, `docs/architecture/TYPE_CATALOG.md` or `contracts/*.schema.json` disagree on a signature or wire shape, those files win.

Scope: synchronous fixture-only discovery. No job, worker, durable acceptance, external write, arbitrary plugin loading, memory or production readiness is claimed. M01/M02/M14/M15/M17/M25/M26/M30/M31 are partial contributions in S00; full module gates remain open until every applicable later-slice obligation passes.

## Interfaces and trust

- `quati chat [--jsonl]` (M01-FR-04, M01-AT-03, M01-RT-03; owned by S00-T01, not yet in `src/`) is a line-based terminal session and is part of the S00 target contract: each input line is one turn through the same use case as the equivalent one-shot command, with the same identity, authorization, approval, exit-code and error-code rules; it keeps no state outside the ledger and the M31 context envelope; `--jsonl` prints exactly one Response envelope per input line on stdout. In S00 a turn is an `ask`; `/status`, `/tell`, `/approvals`, `/approve` and `/deny` return the same error as their one-shot commands until those commands exist (S02). The normative rules are in `docs/prds/M01.md` § Chat session. It is not a GUI or full-screen TUI.
- CLI commands return stable JSON Response envelopes. Exit codes are exactly the table in `docs/prds/M01.md` § Exit codes: 0 successful command execution, 1 `INTERNAL_ERROR`, 2 invalid input, 3 missing configuration, 4 `DENIED`, `BLOCKED`, `UNAVAILABLE` or `CONFLICT` not caused by a provider, 5 provider failure (`TEMPORARILY_UNAVAILABLE`, `DEADLINE_EXCEEDED` or `OUTPUT_INVALID` from a model or tool provider), 6 worker tick with remaining or failed work. Unsupported future commands are errors, never successful placeholders. Discovery and behavior-compile commands stay unavailable until their owning tasks pass.
- Local principal originates from the process identity adapter, never model arguments. The S00 catalog contains only public synthetic local fixtures. No tenant-private data is imported.
- Capability discovery, description and invocation use `DiscoveryPort` and `RegistryPort` exactly as declared in `BOUNDARY_CONTRACTS.md`. Search returns at most five permitted candidates. Invocation validates enabled lifecycle, measured binding eligibility, local scope, effect, input and output schemas. Lifecycle and assurance are never self-declared by a definition (RFC-015 REG-01). Only explicitly registered fixture handlers execute; manifests cannot load code or grant permissions.
- The model is reached only through `ModelPort` as declared in `BOUNDARY_CONTRACTS.md`. The application owns evidence and final status; a model completion is never passed through as verified work. Provider SDK types remain inside the adapter.
- For nontrivial input, a typed classification precedes discovery. Invalid output has bounded retries. Classification is advisory; no classification can bypass invocation policy. Exact benign greetings can use a deterministic no-tool path. Mixed greetings and work do not match that path.
- A real tool probe must precede autonomous fixture invocation on each live run. `UNKNOWN` is not `SUPPORTED`. Doctor without an explicit probe reports configuration availability separately from measured support. Probe checks a nonce round-trip through an innocuous tool; other features stay `NOT_VERIFIED`.
- Provider configuration uses `QUATI_BASE_URL`, `QUATI_MODEL`, `QUATI_API_KEY_ENV` naming an environment variable containing the token, and explicit `QUATI_ALLOW_LIVE=1`. Never infer authorization from unrelated session credentials. HTTPS only; reject URL credentials, query, fragment and redirects. No automatic fallback endpoint. Fixed request/tool/output/time limits bound each run. Configuring this is authorization for those bounded synthetic model calls, not any downstream external writes.
- Evidence records structured operation IDs, hashes, timing, usage, sanitized result codes and provenance. Default evidence omits raw request, tool arguments and model text. Synthetic live evaluations may explicitly capture their synthetic arguments and outputs; secrets remain redacted. Unknown cost remains null, never zero.
- Failed/blocked requests never claim completed work. Successful fixture output is labeled `FIXTURE_RESULT`, not completed professional research. Probe-only success is not routing competence.

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

### Displayed text and social outcomes (normative for S00; audit findings F2 and F3, LOG-0039)

These rules are code-owned. The model's classification is advisory: it can withhold a social
outcome, it can never create one, and it never selects the tool path for a greeting.

1. **Application-owned text only.** Every word `quati ask` and `quati chat` display is produced by
   the application: a deterministic greeting template, the deterministic localized no-action
   notice, a rendered `FIXTURE_RESULT`, or a fixed application message. Text written by the model
   is never displayed, in any result kind. It is recorded as `final_text_sha256` in the receipt
   (and in full only under `--synthetic-evidence`).
2. **Greeting-only text.** A text is greeting-only when every word (Unicode `\w+`, casefolded) is
   in the code-owned social vocabulary or in the code-owned urgency markers, and at least one word
   is in the social vocabulary. The urgency markers are the words `urgent`, `urgently`, `urgente`,
   `dringend` and the demonstrative or copula that carries them (`this`, `isto`, `isso`, `é`, `esto`,
   `c`, `est`, `das`, `ist`, `è`, `questo`); they name no object and no action. A greeting-only text
   never reaches the tool loop, whatever the model's label says: no tool is offered, no capability
   can be invoked and no commitment is created (SOC-01 and its negative, "urgent" in a greeting-only
   sentence). Its result is `GREETING` / `SUCCEEDED` with the localized template of the greeting it
   contains (the opening greeting, else the first greeting in the text). When it contains no
   recognized greeting the reply is the no-action notice alone, in English (no template names a
   language), with uncertainty `NO_GREETING_TEMPLATE`. A label other than social / no work /
   respond adds uncertainty `MODEL_LABEL_NOT_SOCIAL` and changes nothing else.
3. **Conversation.** Any other text goes through the tool loop. A label `intent=social`,
   `work_needed=false`, `next_action=respond` ends the turn as `CONVERSATION` / `SUCCEEDED` only
   when all of these hold: (a) the text opens with a recognized greeting (a greeting template
   matches its opening words); (b) the loop made zero tool calls; (c) the model still made zero
   tool calls after the single `NO_SEARCH_ON_WORK` continuation. The displayed text is the greeting
   template followed by the localized no-action notice (`display_lines`), with
   `text_source=application_template`, `work_performed=false`, `actions_taken=[]`, no commitment,
   and a `next_action` stating that no work was accepted.
4. **Work labelled social fails closed.** A social or simple-answer label on a text that opens with
   no recognized greeting is not a social outcome. The turn ends `BLOCKED` / `EVIDENCE_INSUFFICIENT`
   reason `NO_VERIFIED_EXECUTION` (exit 4), exactly as a work label without a validated execution;
   nothing the model wrote is displayed.
5. **Fallbacks keep the narrower rule.** The deterministic fallback after a model timeout or
   provider unavailability during classification, and the provider-free path, apply only to text
   made of social vocabulary alone that opens with a recognized greeting (urgency markers excluded).
6. A greeting in a language without a template is not recognized by code; its handling stays
   model-dependent (tier L3) and, by rule 4, it cannot end as a `CONVERSATION`.

### Registry authorization (normative for S00; audit findings F4 and F5, LOG-0039)

Every registry read and write reachable from the command line or from an ask session passes
`AuthorizationPort` before any registry lookup or change, and its decision is logged as
`authz.decided`: `capabilities list|search|describe` and the `quati_search`, `quati_describe`,
`quati_invoke`, `quati_status` tools (`read`), the catalog digest of an ask receipt (`read`,
operation `ask`, once per ask), and `capabilities install|install-fixture|disable`, including
`--enable-fixture` (`manage`). The resource is `registry:<tenant_id>`; the space that owns it is the
tenant's organization space, resolved from the identity directory and never from the request.
The exact rules are in `docs/rfcs/RFC-013_IDENTITY_TENANCY_SPACES.md` section 12.1 and
`docs/prds/M02.md` "S00 decisions". When the catalog read of an ask is denied or cannot be
logged, the receipt has `digests.catalog_digest = null` and `catalog_access = <reason>`.
