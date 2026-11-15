# S00 runtime implementation contract (audit correction)

Scope: synchronous fixture-only discovery prototype. No job, worker, durable acceptance, external write, arbitrary plugin loading, memory or production readiness is claimed. M01/M02/M14/M15/M17/M25/M26/M30/M31 are partially implemented; full module gates remain open.

## Interfaces and trust

- CLI `secma doctor --json`, `secma ask TEXT --json`, `secma capabilities list|search|describe`, and `secma behavior compile PROFILE` return stable JSON. Exit 0 is successful command execution, 2 invalid input, 3 missing configuration, 4 denied/unavailable, 5 provider failure. Unsupported future commands are errors, never successful placeholders.
- Local principal originates from the process identity adapter, never model arguments. S00 catalog contains only public synthetic local fixtures. No tenant-private data is imported.
- `CapabilityCatalog.search(query)`, `describe(capability_id)`, `invoke(capability_id, arguments)` expose definitions independently from registered executable bindings. Search returns at most five permitted candidates. Invocation validates enabled lifecycle, measured binding eligibility, local scope, effect, input and output schemas. Only explicitly registered fixture handlers execute; manifests cannot load code or grant permissions.
- The model adapter receives a catalog session port and returns `ModelRun(text, classification, calls, usage, elapsed_seconds)`. The application owns evidence and final status. Provider SDK types remain inside the adapter.
- For nontrivial input, a typed classification precedes discovery. Invalid output has bounded retries. Classification is advisory; no classification can bypass invocation policy. Exact benign greetings can use a deterministic no-tool path. Mixed greetings and work do not match that path.
- A real tool probe must precede autonomous fixture invocation on each live run. `UNKNOWN` is not `SUPPORTED`. Doctor without an explicit probe reports configuration availability separately from measured support. Probe checks a nonce round-trip through an innocuous tool; other features stay `NOT_VERIFIED`.
- Provider configuration uses `SECMA_BASE_URL`, `SECMA_MODEL`, `SECMA_API_KEY_ENV` naming an environment variable containing the token, and explicit `SECMA_ALLOW_LIVE=1`. Never infer authorization from unrelated session credentials. HTTPS only; reject URL credentials, query, fragment and redirects. No automatic fallback endpoint. Fixed request/tool/output/time limits bound each run. Configuring this is authorization for those bounded synthetic model calls, not any downstream external writes.
- Evidence records structured operation IDs, hashes, timing, usage, sanitized result codes and provenance. Default evidence omits raw request, tool arguments and model text. Synthetic live evaluations may explicitly capture their synthetic arguments and outputs; secrets remain redacted. Unknown cost remains null, never zero.
- Failed/blocked requests never claim completed work. Successful fixture output is labeled `FIXTURE_RESULT`, not completed professional research. Probe-only success is not routing competence.

## Verification contract

Tests begin red against CLI, policy/catalog, compiler and adapter ports. Offline injected-model tests are L1 harness integration, not L3. Live harness launches normal `secma ask` processes with natural-language requests; expected labels stay in evaluator only. It checks ordered search/describe/invoke, exact typed arguments/outcome, confusable target discrimination, greeting without work, policy rejection and prompt identity. Missing configuration returns BLOCKED with nonzero exit. No later slice starts until every S00 gate meets its required tier.

Contract schema changes in this audit occur before a released runtime exists. Historical source evidence is retained; newly generated evidence is append-only and identifies the implementation commit and file hashes.
