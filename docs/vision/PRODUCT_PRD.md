# PRD-000 — Quati: Executive Cognitive Secretary

**Version:** 8.0 proposed. **Status:** design only. **Audience:** implementers, auditors and product stakeholders. **Delivery shape:** headless CLI + durable worker, local-first.

## Problem
Existing AI agents can research, code, use tools or perform workflows but often fail to manage the human relationship across long-running requests. Users must remember what they asked, re-explain context, chase progress, resolve partial results and judge whether work is sufficient. Building more specialist agents is not a substitute for taking responsibility for the user outcome.

## Success definition
Quati behaves as a reliable professional secretary: it hears the actual request, discriminates greetings and questions from delegable work, clarifies selectively, starts reversible research without waiting unnecessarily, creates durable commitments, supervises multiple executors, updates the requester at useful moments, remembers prior work with evidence, audits results and delivers concise answers plus reproducible artifacts. It also serves machine requesters through typed contracts.

## User personas
- Individual professional: native CLI, own models and data, lightweight resource profile.
- Corporate employee: authorized calendar, email, Slack, internal MCPs, delegated identity and enterprise model gateway.
- Technical lead/engineer: coding agents, PRD/TRD/ADR discovery and software-project investigation.
- Analyst: data and causal investigations, reproducible hypotheses, evidence lineage and uncertainty.
- Agent or service: structured request, async callbacks, idempotent machine-readable delivery.
- Administrator: plugin catalogs, security boundaries, agent/harness profiles, budgets, diagnosis, audits and rollback.

## Primary product narratives
1. “Good morning.” → a normal concise greeting; **no job**, no executor, no fake proactive activity.
2. “What is a PRD?” → immediate informational response; optional authorized context search only if relevant.
3. “Draft a PRD for a causal measurement engine.” → concise acknowledgement; safe repository discovery starts; optional goal question does not block; a persistent commitment is created; follow-up constraints update it.
4. “Do that study from last week for Company X.” → resolve last week's method, artifact version and permission; ask one disambiguating question only if two plausible studies remain.
5. “Add a line to last week's chart.” → find editable artifact and source data, create a new version and explicitly disclose when source is unavailable.
6. “Why did Ads positions 4 and 5 fall while 1 and 3 did not?” → analytical capability, confounder-aware timeline, evidence, missing-source notices, uncertainty and selective SME escalation.
7. “The customer is missing from the dashboard.” → incident investigation across authorized docs/logs/datastores without production writes; return proof, alternative hypotheses and next steps.
8. “Contact the owner of the data source.” → explicit identity, scope and permission checks before outbound message, with receipt only after confirmed provider result.
9. “We just installed a new specialist harness for editing Excel charts.” → manifest/assurance/health/policy checks; automatic catalog discovery and provider-neutral invocation; failover or typed unavailable when removed.
10. “My company blocks public APIs and Docker.” → corporate profile uses approved model endpoint, native CLI and authorized remote state; no hidden third-party egress.

## Product invariants — release blockers
- K1: A clear work request is never silently dropped, conflated with a greeting, or falsely acknowledged as started.
- K2: Every accepted root commitment has a persistent owner, revisioned state and next responsible action until closure or explicitly blocked state.
- K3: An LLM proposes intent and action; trusted code enforces security, state transitions, deadlines and outbound effects.
- K4: No unauthorized external effects or cross-tenant data access regardless of prompt/skill/tool content.
- K5: “Delivered” requires a recorded provider/CLI delivery acknowledgement; unknown external effects are surfaced as uncertain, not retried blindly.
- K6: A specialized investigation cannot claim sufficiency merely because an executor returned text; independent evidence rules apply.
- K7: Capability definitions, runtime bindings and measured assurance are distinct. A manifest alone is not executable.
- K8: Model feature support and competence are measured per model/provider/configuration. Large context is not assumed to mean sound judgment.
- K9: User preferences influence presentation and noncritical initiative, not permissions or evidentiary standards.
- K10: User-facing responses use the user's language or explicit preference; internal prompts, contracts, logs and documentation are English.

## Scope of initial product (S00–S02)
**Included:** CLI, one actual model provider, social/simple/work classification, one real blind discovery of installable capability, safe work start, ERI relationship updates, durable ledger and ledger-driven worker (ADR-015), progress timing, outcome sufficiency and honest delivery; evidence collection, retry/rollback and basic auth/policy. **Excluded initially:** full enterprise SSO, dozens of harnesses, every brain, marketplace, production-scale HA, UI, autonomous prompt promotion, cross-tenant sharing, true external Slack/Google write integrations.

## Personalization contract
Operator profile, interaction profile, execution profile and requester preference are distinct and versioned. The system MAY learn stylistic preferences based on repeated user corrections, with confidence and scope; it MUST offer inspect/correct/delete and MUST NOT silently alter safety policy. Configuration changes are proposed, compiled, simulated, evaluated and then atomically activated with rollback.

## User expectations and attention
Users do not need heartbeat spam; they do need accurate receipts, relevant new findings, blocking questions and communicated delays before agreed contact milestones. The secretary can provide “I will update you after the next evidence checkpoint” when no supportable ETA exists. It may offer progressive depth and describe actual uncertainty, but must avoid hollow praise, speculation about timing and long unsolicited text.

## Availability and performance
Small-model operation is a **target to demonstrate**, not an assertion. Personal mode needs low idle CPU, bounded RAM, no mandatory Docker and usable offline read-only functions when external APIs are not available. Worker resumption depends on the worker actually running; sleeping laptops do not execute jobs without remote worker.

## Measurement (not vanity test counts)
- User outcome completion, correct classification and safe abstention, meaningful question ratio, notification usefulness, false-completion rate, retrieval precision, end-to-end latency, resource idle footprint, cost per completed commitment.
- Hard-blocking: known unauthorized effects, known tenant leaks, lost accepted commitments under designated fault suite, unreported uncertain send.
- Model-dependent: evaluate independent blind holdouts and record model performance before enabling autonomous operation for that profile. Do not set ungrounded universal accuracy guarantees.

## Non-goals
Quati is not a humanoid simulation, universal AGI, alternate operating system, a new universal tool protocol, a mandatory container orchestrator, a secret-sharing superagent, a browser-first app or a replacement for the domain specialist engines it delegates to.

## Traceability
All detailed product requirements are in `docs/prds/M01.md`–`M31.md` with stable FR/AT/RT identifiers and coverage in `docs/traceability/REQUIREMENTS.csv`. The implementation roadmap is normative and limits expansion despite the complete long-term vision.

## Prototype boundary before S02

S00 and S01 are restricted development prototypes, not releases satisfying the durable-commitment success definition. Their transient request/work identifiers MUST NOT be represented as persistent commitments; responses explicitly disclose in-process lifetime whenever work spans turns. They cannot promise continuation after exit/restart or accept unattended durable obligations. K2 remains an unchanged release blocker and becomes executable at S02. S00 fixture capabilities demonstrate discovery, not professional investigation outcomes.
