# State of the art: capability selection, evals, routing, injection defense, provenance (2026-11-15)

Status: WORKING NOTES for RFC-001 / RFC-006 / RFC-008 and audit items A-08, A-13..A-21. Specification-only; no code touched. Claims not confirmed from a primary source are marked UNVERIFIED. MVP = S00-S02, single user, Linux.

Verdict legend: KEEP (spec already right), ADOPT (add as is), CHANGE (adjust spec), REJECT.

## 1. Tool and capability selection at scale

| Item | Evidence and maturity | Verdict |
|---|---|---|
| Anthropic tool search tool (`defer_loading: true`; regex and BM25 variants; custom search such as embeddings allowed). Beta header `advanced-tool-use-2025-11-20`. https://www.anthropic.com/engineering/advanced-tool-use | Vendor-reported: ~77K to ~8.7K tokens; MCP-eval accuracy Opus 4 49% to 74%, Opus 4.5 79.5% to 88.1%. Guidance: useful above ~10K tokens of definitions or 10+ tools. Vendor numbers, single source. Beta. | KEEP the search to describe to invoke shape (CAP-01/02). ADOPT the 10-tool / 10K-token threshold as a documented "no search needed below this" rule. Do not depend on the beta API: SECMA's own search is provider-neutral. |
| Programmatic tool calling (model writes code that calls tools in a sandbox; intermediates stay out of context). Same source. | 37% token reduction (43,588 to 27,297) on research tasks. Beta, needs a code sandbox. | REJECT for S00-S02. Over-engineering for a single-user secretary with a 2-fixture catalog; it also adds a code-execution surface that conflicts with "authorization before effects". Revisit only if chains of 3+ dependent calls dominate. |
| Tool-use examples (`input_examples`, 1 to 5 per tool): 72% to 90% on complex parameter handling. Same source. | Vendor-reported. | ADOPT: SCS `intents.positive_examples` already exists; add one concrete valid example input to the manifest (see deltas). |
| RAG-MCP (retrieve tools from an index before prompting). https://arxiv.org/abs/2505.03275 | Prompt tokens down >50%; selection accuracy 43.13% vs 13.62% baseline. Preprint, MCP-specific stress setting. | ADOPT the principle: shortlist then LLM chooses. This matches A-15's fix. |
| Retrieval method: BM25 vs embeddings vs LLM re-rank. | Anthropic ships BM25 and regex built in, embeddings as custom. I found no primary head-to-head showing embeddings reliably beat BM25 on small, well-described catalogs: UNVERIFIED. Embeddings add a model dependency, an index and drift. | KEEP FTS5/BM25 first (A-15). REJECT embeddings and LLM re-rank in S00-S02. Make the retriever a port so embeddings can be added after measured recall@K failure. |
| Skills in Claude Code and the Agent Skills standard (SKILL.md; name and description always in context ~100 tokens per skill; body under ~5K tokens loaded on trigger; scripts executed, not loaded; description max 1,024 chars, name max 64). https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview and https://agentskills.io/specification | Stable in Anthropic products. Selection is by the model matching the request against descriptions; there is no separate retriever. Adoption by Codex and Gemini CLI: UNVERIFIED (already flagged in CAPABILITY_ECOSYSTEM). | KEEP progressive disclosure (search = metadata, describe = full contract, invoke). CHANGE: Anthropic's own guidance is that the description must say what it does and when to use it; SCS requires only `description` of 40+ chars plus intent examples. Add an optional `when_not_to_use` handled through `negative_examples` (already present: KEEP). Cap description length at 1,024 to stay interoperable. |
| Accuracy versus number of tools. | Practitioner blogs cite BFCL-style drops (e.g. 43% to 2% on a calendar task as domains grow) and a "safe zone" of 10 to 20 tools; these are secondhand, UNVERIFIED. A counter-report (Fullstory blog, Gemini 3 Flash, 1 to 100 tools, two-step tasks) shows no degradation, so the effect is model- and task-specific. | CHANGE: do not hard-code a universal tool limit. Declare `max_shortlist_k` (default 5 to 8) per model profile and measure it in MOD-01. |

MVP over-engineering flags for section 1: embeddings, re-rank, programmatic tool calling, deferred-loading beta API. None is needed for a 2-fixture S00 catalog; the real S00 risk is confusable-pair selection, which BM25 plus negative examples and a real model test cover.

## 2. Evaluating agent tool use

| Item | Evidence and maturity | Verdict |
|---|---|---|
| BFCL V4 (holistic agentic evaluation; multi-turn from V3; FC vs Prompt modes; accuracy, cost, latency). https://gorilla.cs.berkeley.edu/leaderboard.html (page dated 2026-04-12) | Mature, widely used. It measures function-call correctness, not catalog discovery or SECMA's outcome verification. | ADOPT as a model-competence pre-screen (does this local model emit valid tool calls?), not as the S00 gate. |
| tau-bench and pass^k. https://arxiv.org/abs/2406.12045 | Abstract: gpt-4o under 50% of tasks; pass^8 below 25% in retail. pass^k is the probability that all k i.i.d. trials succeed; this is the definition I used (the abstract itself does not give the formula). | ADOPT pass^k as the reliability metric for write-adjacent or repeated behavior. |
| tau2-bench / tau-3 line (domains incl. banking_knowledge, intake; voice; 2.0 scores not comparable with 1.x). https://github.com/sierra-research/tau2-bench | Active; versions are not comparable, so version-pin everything. | KEEP as inspiration for "pin scenario and grader versions in evidence". Do not run it: customer-service domains, not SECMA's. |
| ToolBench / StableToolBench (simulated API server to stabilize results). | Not re-verified this session: UNVERIFIED. | REJECT for S00-S02. The idea (cached or simulated tool responses to isolate selection from API flakiness) is the same as SECMA's fixture handlers. |
| MCPMark (127 tasks, 5 MCP environments; best model 52.56% pass@1, 33.86% pass^4). https://arxiv.org/abs/2509.24002 | ICLR 2026 poster. Shows pass^4 is far below pass@1 for realistic MCP work. MCP-Universe (GPT-5 43.72%) and MCP-Bench: only a secondhand snippet or nothing found, UNVERIFIED. | KEEP as evidence that single-run pass rates overstate reliability. REJECT running them. |
| LLM-as-judge pitfalls (self-preference, position and verbosity bias, judge drift). | Not fetched this session; known from the literature but UNVERIFIED here. | ADOPT the rule that selection and outcome checks are deterministic (compare chosen capability id, arguments against schema, resulting state or evidence hash). Use a model judge only for free text, with a different model family than the system under test. |
| OpenTelemetry GenAI semantic conventions (`invoke_agent`, `chat`, `execute_tool {name}` spans; `gen_ai.tool.name`, `gen_ai.tool.call.id`). Moved to https://github.com/open-telemetry/semantic-conventions-genai | Still Development stability as of mid-2026 per secondary sources (Dash0, Greptime, DEV posts); no tagged release found. The primary spec page I fetched only confirmed the move. | CHANGE: keep SECMA's own immutable trace schema as the source of truth; add an optional exporter mapping to `execute_tool` / `invoke_agent` names, pinned by version. REJECT making OTel a gate dependency. |

### Statistical thresholds (A-21 and MOD-01)

Wilson 95% interval, computed here by hand with z = 1.96:

| Observed | Wilson lower bound | Meaning |
|---|---|---|
| 9/10 | about 0.60 | "9 of 10" is compatible with a true rate near 60%. It is NOT meaningful as a reliability gate. |
| 10/10 | about 0.72 | Even a perfect 10 only supports "at least ~72%". |
| 26/30 | about 0.70 | The current MOD-01 floor; weak, as A-21 already notes. |
| 30/30 | about 0.89 | Zero failures in 30 supports about 89%. |
| zero failures in n | upper bound on failure about 3/n | Rule of three. For "zero critical failures", 30 cases only bound the critical rate under about 10%. |

Consequences:
- pass@k (at least one success in k) rewards luck and is wrong for a secretary that acts; use pass^k. If the per-trial rate is 0.9, pass^10 is about 0.35. A "9 of 10" rule hides this.
- A discriminating, honest framing for S00: report the interval and label it a smoke qualification ("no evidence of failure at this N"), not a reliability claim. Do not lower thresholds after a run (already in MOD-01: KEEP).
- Live repeated runs are non-deterministic even at temperature 0 on many providers (UNVERIFIED for specific providers); log the exact model identifier and system fingerprint when exposed.
- CAP-01/02 are scenario checks (does the real model choose capability X over its confusable twin): use at least 10 paraphrased prompts per scenario with the full catalog order shuffled, and require zero unauthorized effects, not a percentage.

## 3. Model routing and competence

- RouteLLM (strong/weak router trained on preference data; >2x cost reduction at similar quality; routers transfer when the model pair changes). https://arxiv.org/abs/2406.18665. Research-grade, trained routers. Verdict: REJECT learned routers for MVP. KEEP the A-18 plan: one configured model, operator `RoutingPolicy`, escalation disabled until benchmarked.
- Cost-aware cascades (try small model, escalate on low confidence or failed verification): conceptually standard; I did not verify a specific primary source: UNVERIFIED. For SECMA the escalation trigger should be a code-level signal (schema-invalid call, abstention, risk tier), never the model's self-reported confidence.
- Reproducible "model competence" declaration: no accepted standard found (UNVERIFIED). Practical form is a signed-off record, not a claim: `{role, exact model id and revision, provider, prompt hash, config hash, catalog snapshot digest, case-set digest, N, successes, Wilson 95%, critical failures, cost and latency, date, evaluator}`. This is what MOD-01 already asks for. KEEP, and add the digests and a validity expiry (re-qualify when any digest changes).
- BFCL FC-mode score is a useful input for the `probe` fields in A-18 (tool_choice, parallel calls, structured output support), flagged "attested" or "unknown".

## 4. Prompt-injection-safe tool use

| Defense | Evidence and maturity | Verdict |
|---|---|---|
| CaMeL (control and data flow extracted from the trusted query; capabilities enforce policy on tool args). https://arxiv.org/abs/2503.18813 | AgentDojo: 77% of tasks solved with provable security vs 84% undefended. Research prototype; requires a custom interpreter and policies. | REJECT the full system for MVP. ADOPT its core idea, which SECMA's kernel already approximates: authorization and effect decisions come from trusted code and the trusted user request, never from text read in a tool result. |
| Design patterns for securing agents (Beurer-Kellner et al.). https://arxiv.org/abs/2506.08837 | Peer-reviewed-style analysis; I could not fetch the pattern list from the abstract page, so the pattern names are UNVERIFIED here. Commonly cited as plan-then-execute, dual LLM, action selector, context minimization. | ADOPT plan-then-execute plus "quarantined reader" for any capability that reads untrusted content: a reader returns typed, schema-bounded output (no free instructions), and the planner never sees raw untrusted text when it can choose effectful tools. |
| Spotlighting (delimit or encode untrusted text). https://arxiv.org/abs/2403.14720 | Attack success from over 50% to under 2% in the authors' GPT-family experiments; weak against adaptive attackers (general knowledge, UNVERIFIED here). | ADOPT as cheap defense in depth, not as a control. |
| AgentDojo (97 tasks, 629 security cases). https://arxiv.org/abs/2406.13352 | Standard benchmark; shows attacks break some security properties but not all, and that utility is limited even without attack. | REJECT adopting it as a gate. A handful of local red-team fixtures at the shared enforcement point satisfy AGENTS.md, which already says not to repeat attacks per module. |

Practical small-runtime SOTA: (1) taint every tool output as untrusted; (2) deterministic deny of any effectful call whose arguments are derived only from tainted data without user confirmation; (3) no capability combining private-data read, untrusted read and outbound write in one run without approval (the "lethal trifecta" combination, a widely used framing, UNVERIFIED primary source); (4) typed outputs from untrusted readers; (5) spotlighting as a hint. All five are code-level, which matches the kernel invariants.

## 5. Capability packaging and provenance

- Sigstore/cosign signing, SLSA provenance, in-toto attestations. Mature for containers and packages (PyPI PEP 740 and npm provenance use Sigstore per secondary sources; cosign 3 stores signatures as OCI 1.1 referrers). Sources: https://docs.sigstore.dev, https://slsa.dev (not re-fetched; secondary blogs only), UNVERIFIED for agent skills specifically. I found no standard for signing agent skills or MCP servers. Verdict: REJECT Sigstore/SLSA/in-toto for MVP (keyless signing needs network identity infrastructure and a trusted publisher). ADOPT a lockfile with content digests: `capabilities.lock` with `id`, `version`, `sha256` of the whole directory (canonical file list), source URI, and installed-by approval id; verify the digest at every load and refuse on mismatch. Keep the manifest format open so a signature field can be added later.
- Skill supply-chain threat is real: Snyk ToxicSkills scanned 3,984 skills, 76 confirmed malicious, 13.4% with a critical issue (https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/); a USENIX Security 2026 paper reports 157 malicious skills among 98,380 (https://www.usenix.org/conference/usenixsecurity26/presentation/liu-yi); a further study reports 26.1% of 31,132 skills with at least one vulnerability (secondary result, UNVERIFIED). Datasets and detection methods differ; numbers are not comparable.
- Anthropic's own guidance: use skills only from trusted sources, audit all bundled files, and be wary of skills that fetch external content (https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview). Verdict: ADOPT a local static lint at install (flag network calls, shell exec, writes outside the state dir, instructions to hide behavior, external URLs fetched at runtime) as an advisory report, plus default-deny permissions declared in the manifest. This is not proof of safety; say so in the report.

## Review of current SECMA spec against this

- Schema: `lifecycle` and `assurance` are required self-declared manifest fields (A-16). Confirmed as contrary to provenance best practice: a package must not vouch for itself. CHANGE as A-16 proposes.
- Schema lacks a content digest, a source and an example input. `description` minLength 40 is a weak proxy for routing quality; add maxLength 1024 for interoperability.
- MOD-01 at 26/30 is correct to report Wilson; additionally record N, digests and make the claim "smoke qualification".
- MVP over-engineering to defer: embeddings, rerank, learned routers, Sigstore, SLSA, OTel export, AgentDojo/tau2/MCPMark runs, programmatic tool calling.

## Recommended deltas

| Target file | Change | Priority | Slice |
|---|---|---|---|
| contracts/scs-capability.schema.json | Remove self-declared `lifecycle` and `assurance` from required manifest fields (registry-owned); add `maxLength: 1024` on `description`; add optional `examples[]` of valid input; tighten `id` to a namespaced pattern | High | S00 |
| docs/rfcs/RFC-001_SCS_PORTABLE_CAPABILITY.md | State that integrity is a directory sha256 recorded in a lockfile, signatures are a future optional field | High | S00 |
| docs/rfcs/RFC-006_DISCOVERY_AND_REUSE.md | Specify retrieval: hard filters, BM25/FTS5, shortlist K, LLM chooses; retriever is a port; embeddings deferred until measured recall@K failure | High | S00 |
| docs/testing/TEST_EXECUTION_PROTOCOL.md (MOD-01) | Label as smoke qualification; require recorded digests (model, prompt, config, catalog, case set); add validity expiry on digest change; add pass^k for repeated runs | High | S00 |
| docs/testing/TEST_EXECUTION_PROTOCOL.md (CAP-01/02) | Require at least 10 paraphrased prompts per scenario, shuffled catalog order, deterministic checks of chosen id, arguments and evidence; zero unauthorized effects | High | S00 |
| docs/testing/TEST_EXECUTION_PROTOCOL.md | Add a statistics note with the Wilson table above, and ban "9 of 10" style gates | Medium | S00 |
| docs/audit/GENERAL_AUDIT_2026-11-15.md (A-18) | Add `max_shortlist_k`, tool-choice and parallel-call probe fields; escalation triggers are code-level signals only | Medium | S01 |
| docs/rfcs/RFC-007_POLICY_AUDIT_EVENTS.md | Add output-taint rule: effectful args derived only from untrusted tool output need confirmation; typed outputs for untrusted readers | High | S01 |
| docs/rfcs/RFC-008_EVALUATION_AND_EVOLUTION.md | Add judge rules: deterministic checks first; judge model different from system under test; pin grader and scenario versions | Medium | S01 |
| docs/rfcs/RFC-004_ADAPTER_PROVIDER_CONTRACTS.md | Optional trace exporter mapping to OTel GenAI names, version pinned, Development stability noted | Low | S02 |
| docs/research/CAPABILITY_ECOSYSTEM_2026-11-15.md | Add install-time static lint requirements and default-deny permission model with Snyk/USENIX references | Medium | S02 |
