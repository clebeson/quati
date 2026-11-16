# RFC-012 — Context Engineering, Weak-Model Routing and Decision Quality

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

**Problem:** A large context window does not imply deep reasoning, reliable tool choice or sustained goal tracking. Quati must remain helpful on inexpensive models without pretending they match high-capability models on scientific investigations.

## Two-stage classification
Trusted fast preflight handles explicit greeting and local command shortcuts only when high confidence and no hidden side-effect intent. Otherwise a small tool-capable model returns a typed `RequestClassification`: intention family, risk/effect, expected complexity, missing critical info, candidate domain, provisional depth, whether safe work can start, and confidence/abstain. Policy then decides allowed actions. `DEEP_ANALYSIS`, high uncertainty, sensitive work or repeated failures trigger a stronger approved model or a bounded clarification.

## Progressive context layers
A minimal envelope includes role constraints, active commitment summary, short recent interaction, target schema, available action enum and top ranked capability descriptions; source details/skills expand only after selection. Artifact and knowledge retrieval must attach provenance, ACL and freshness. User preferences affect phrasing, not security or result proof. Stable prompt prefix enables caching where supported; retrieval snippets go into explicitly lower-trust sections.

## Model competence profiles
A provider descriptor contains observed tool-calling reliability, JSON validity, intentional abstention, routing/top-k recall, tool-result continuation, evidence judgment and cost per task class, all with model version, provider, prompt digest and sample sizes. An unsupported feature is never inferred from “OpenAI-compatible”. A cheap model may handle greetings, status and low-risk routing even if not competent for independent causal inference. Escalation is a configured policy decision, not an agent’s claimed confidence alone.

## Evaluation
Blind holdouts include paraphrases, novel installed capabilities, near-match distractors, disabled providers, greetings, long-context interruption, contradictions and adversarial tool descriptions. Record actual tool calls and rejected attempts. No role is called “supported” until behavior has been measured under that exact provider configuration; test with multiple seeds/trials as variance requires, rather than arbitrary 100% model success claims.
