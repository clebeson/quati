# Test Coverage Justification and Gap Report (Design v8)

**Truth statement:** This package specifies tests; the only executed checks included in it are L0 documentation/schema/reference-compiler tests. No claims of tested live LLM, ledger-worker recovery, native OS portability or external Slack/Gmail/model enterprise APIs are made.

## Why we do not create thousands of tests
Requirement count is not risk count. Multiple PRDs share a single authorization gate, a single ledger integrity rule and one model discovery mechanism. Duplicate tests that only assert identical mocks increase CI cost without reducing risk. Instead, choose tests at each unique failure boundary, prefer property/state tests over enumerated messages, and test integrations through their public entry paths. Add new cases when a production incident, architectural change or unique negative scenario reveals an uncovered boundary.

## Risk-weighted coverage by layer
| Risk area | Impact | First mandatory proof | Justification for tests | Current proof |
|---|---|---|---|---|
| Unauthorized external effects | Critical | L1 policy + L2 gateway negative | Consequence irreversible; cannot rely on LLM refusal | NOT_RUN |
| Wrong tenant/identity | Critical | L1/L2 identity + retrieval ACL | Avoid privacy breaches and forged commands | NOT_RUN |
| Lost/duplicated commitment | Critical | L2 ledger-worker fault suite (SQLite; PostgreSQL conformance) | Core product promise; worker restart/two workers | NOT_RUN |
| Wrong capability selection | High | L3 blind real-model holdout | SCS's central hypothesis is empirical | NOT_RUN |
| False completed investigation | High | L2 evidence gate + L3 multi-turn | Prevent misleading confident findings | NOT_RUN |
| Bad update timing/spam | Medium–high | virtual clock + L3 ERI eval | Core differentiation over plain specialist CLI | NOT_RUN |
| Forgotten previous artifact | High | provenance fixture + L3 dialogue | Must identify correct work, not hallucinate | NOT_RUN |
| Compiler allows unsafe state/prompt | Critical | L0 compiler negative + L1 activation gate | Configuration is externally adjustable and agent-proposable | L0 ONLY |
| Weak model/tool incompatibility | High | model probe + L3 targeted eval | Tool support differs across models even within same gateway | NOT_RUN |
| Long-wait RAM/resource | Medium–high | L2 load test with due-time policy (DUR-05) | Waiting commitments are ledger rows, not live processes (ADR-015) | NOT_RUN |
| Adapter provider removed mid-job | Medium–high | L2 fake executor kill | Server must remain responsive and obligations persist | NOT_RUN |
| Prompt injection from repo/skill | Critical | L1 tool gate + L2 injected source | Untrusted text must not become authority | NOT_RUN |
| External provider quirks | Medium–high | local HTTP fake + L4 authorized smoke | Local compatibility is not live integration guarantee | NOT_VERIFIED_EXTERNAL |
| Windows/macOS/Linux install | Medium–high | L5 native OS smoke | Pure Python is insufficient evidence for SDK/executable support | NOT_RUN |
| Self-improvement regression | High | evaluator gate + sealed holdout | Avoid automatic weakening or overfitting | NOT_RUN |

## Coverage measures
1. **Requirements coverage** = FR IDs with a linked observable acceptance case / total FR IDs. This is traceability, not test pass.
2. **Risk coverage** = unique P0/P1 failure boundaries with executing negative/fault proofs / required boundaries.
3. **Transition coverage** = (valid edges exercised and invalid edges rejected) / declared statechart edges + forbidden candidate transitions. Pure reducer/property tests are suitable.
4. **Behavior coverage** = held-out multi-turn episodes across intent, context, action, pause, user follow-up, executor callback, update and final delivery.
5. **External evidence coverage** = provider features with authorized live smoke / features claimed validated; unsupported/unavailable remain explicit.
6. **Code coverage** is a supporting signal, not a gate by itself; aim 90% deterministic policy/reducer branch coverage and ~80% other core domain where useful, but approve on risk scenarios, not an arbitrary global number.

## Phase exit hierarchy
S00: actual supported-model tool choice and safe abstention; S01: human dialogue/optional clarification while safe research progresses; S02: ledger-recovered commitment + honest delivery; S03: old-work reference/prefs; S04: new harness or brain removed without global outage; S05: evidence-based deep investigation; S06: prompt improvement cannot self-approve; S07: native/enterprise deployment security and resources measured.

## Coverage audit procedure
Auditor reads each module's PRD AT/RT without looking at its implementation, checks one public-entry proof and one nonredundant negative, then identifies missing safety branches. Audit status is `NO-GO` if a required L2/L3/L4 proof was substituted by L0/L1 or if a P0 invariant is knowingly violated. Record gaps in `OPEN_RISKS.md`, not a fabricated “pass rate.”
