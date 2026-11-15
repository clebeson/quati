# Independent Threat and Failure Review — All 31 Modules

## Global verdict at design time
**GO to implement S00 with controls; NO-GO to claim production-ready assistant.** The design covers high-priority stakeholder scenarios but has unresolved empirical questions about model quality, durable worker behavior, provider-specific features, timing usefulness and resource footprint. Each of the 31 module-specific threat sheets remains required input to the relevant implementation slice.

## Top failure modes that can kill the product
1. **Illusion of autonomy:** tests directly invoke the target capability and claim a small LLM chose it. **Defense:** blind natural-language entry test, real provider tool trace, hidden labels.
2. **Prompt/graph compiler becomes an unsafe code generator:** LLM-produced YAML executes arbitrary guards, changes permissions or creates unbounded loops. **Defense:** whitelisted pure guards, data-only DSL, reachability/budget checks, separate policy gate, staged promotion.
3. **State explosion and infinite architecture:** 31 modules become 31 services/agents and tests multiply. **Defense:** modular monolith, slices, timeboxed gates, ADR for new runtime/service.
4. **Cheap model overconfidence:** accepts wrong tool, infers missing facts and signals done. **Defense:** competence-profile gating, output schemas, independent sufficiency, bounded escalation.
5. **False asynchronous promise:** says “I started” before ledger commit or “delivered” before provider ACK. **Defense:** receipt/outbox state machine, transaction and reconciliation.
6. **Long-wait resource explosion:** open-source DBOS waiting/sleep workflows consume resources. **Defense:** durable due-time table and bounded sweeper, load benchmark, avoid naive one-wait-per-job.
7. **Identity confused with content:** untrusted transcript claims to be the owner. **Defense:** source authentication and per-operation delegation scope.
8. **Hidden provider coupling:** vendor SDK auth, model feature assumptions or harness lifecycle leak into domain. **Defense:** feature probed adapter, conformance suite, typed unsupported state.
9. **Memory becomes private-data exfiltration:** retrieval by embedding similarity bypasses ACLs; team brain inherits personal notes. **Defense:** scope filter before + after retrieval, provenance and consent for promotion.
10. **Causality hallucination:** analytical capability claims cause from data association. **Defense:** evidence categories, alternative hypotheses and identified confounders.
11. **False provider test:** fake HTTP response shows success but no real Slack/Gmail account was verified. **Defense:** L2 local vs L4 provider distinction, honest `NOT_VERIFIED_EXTERNAL` status.
12. **Self-improvement self-certifies:** proposes revised prompt and grades it itself on copied examples. **Defense:** independent holdouts, reviewer, rollback and diff-based deployment.
13. **No user value:** more complexity than using Hermes directly. **Defense:** comparator baseline on follow-up continuity, expectation timing and quality of final response.
14. **Bad model escalation:** safety-sensitive task goes to cheap, incompetent model because of price. **Defense:** prerequisite competence matrix and policy-driven restrictions.
15. **Model provider outage:** whole secretary becomes unavailable rather than degraded. **Defense:** local deterministic status/queue/retrieval and truthful waiting state, retries/fallback if permitted.

## How to red-team without overspecification
Risk review operates on enforcement boundaries: auth gateway, durable state, model selection, outcome assessment, delivery, compiler and artifact provenance. Each module sheet offers two unique cases. Execute one representative candidate per distinct shared invariant, expanding only after a real failure or new branch. No self-generated test fixture may secretly contain the answer in visible prompt metadata.

## Unresolved assumptions requiring measured evidence
Small model can perform dynamic SCS discovery at acceptable price/quality; approved provider supports required tool-calling; low idle RAM under local profile; DBOS open-source waiting behavior under 100+ jobs; real users value planned communication cadence; corporate API/harness auth pathways; native Windows/macOS dependencies. All remain unproven.
