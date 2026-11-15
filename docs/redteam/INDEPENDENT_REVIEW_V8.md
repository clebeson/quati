# Adversarial Design Review — SECMA v8

**Review performed:** static adversarial inspection of specification artifacts, schemas, statechart examples and reference compiler only. This is not an independent security penetration test or a live LLM evaluation.

## Reviewed surfaces
- Requirement coverage: 31 modules / 31 module-specific red-team files, 155 requirement and acceptance references and 62 module threat scenarios.
- State and prompt compilation: whitelist of guards/actions, graph reachability, terminal paths, unknown edges, generated prompt digest, policy refusal and rollback concept.
- Scope and implementation order: one normative S00–S07 roadmap and supersession notice for contradictory prior W/S waves.
- Providers and engines: DBOS caveat about SQLite vs PostgreSQL and enterprise-only suspend; model tool-support probes; Codex harness authentication separate from raw model API; local-first, no Docker or UI.
- Evidence tiers: L0–L5, blind actual-model routing tests and explicit never-claim-live-from-mock rule.

## Remaining P0 verification blockers
1. No SECMA production runtime code or real user-initiated LLM tool trajectory exists in this package.
2. No DBOS/PostgreSQL crash, data consistency, concurrency or uncertain external send has been executed on SECMA.
3. No installed real connector has passed authorized provider smoke.
4. Full protected policy engine and semantic statechart reducer are design only; whitelist validation alone is insufficient authorization proof.
5. A single small language model cannot be assumed reliable at every specialist depth without empirical profiles.

## Design gaps requiring later evidence (not fabricated blockers for documentation)
- Contact timing usefulness needs blinded real-user evaluation, not only timer unit tests.
- Resource budgets must be measured on target laptop and corporate packaging platforms.
- Exact corporate Genplat provider contract is unknown and cannot be guessed.
- Team-shared memory governance and private-personal data mixing require deployment-specific policy.
- Native Codex/Claude/Hermes harness feature support and licensing/permissions must be probed per deployed versions.
- Specialist causal output requires statistical evidence and subject-matter review.

## Red-team conclusion
**GO for S00 implementation with security guardrails; NO-GO for declaring SECMA product functionality or production readiness.** Do not promote any capability from manifest-only assurance or proceed to S02 before a genuine S00 blind tool-calling proof. The factory must fix measured defects at the owning boundary rather than add generic abstractions and a large number of shallow tests.
