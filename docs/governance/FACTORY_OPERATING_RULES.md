# Software Factory Rules — SDD, TDD, EDD and Scope Control

## Roles and artifacts
**Specification agent:** identifies stakeholder intent and produces bounded PRD/TRD/ADR and specific FR/AT/RT IDs, no fictitious results. **Implementer:** writes production code and tests against public entries. **Red-team reviewer:** derives adversarial tests from stakeholder requirements without trusting implementation shortcuts. **Release owner:** checks evidence, risk, permissions and rollback before promotion.

## Work package template
- Problem and in-scope user outcome
- Exact FR/AT/RT identifiers, dependencies and ownership
- Public interface/schema changes with backward compatibility
- Implementation sketch (avoid code-level overprescription)
- Positive and negative acceptance paths, fault injections if relevant
- Authorization/data/secret effects
- Evidence commands and expected output fields
- Defer/rollback/compatibility decisions
- Timebox and stop condition

## Definition of Ready
No contradictory docs; contracts can be validated; access to LLM provider or explicit blocking condition is known; test data may be synthesized without confidentiality violations; no unstated enterprise API assumptions. Optional credentials should not block unconnected domains.

## Definition of Done
Real code, passing relevant tests, observable CLI behavior, sanitized evidence and known limitations. A module PRD without code is NOT implemented. Tests in `tests/evals` cannot hardcode a capability ID or inject the gold answer into the prompt. Reviewer must identify at least one plausible failure not already tested in the happy path.

## Prevent infinite implementation
- One active vertical slice at a time until S02 gate; bounded PR scope.
- Hard stop after two unsuccessful attempts to fix a failing gate without new evidence: produce a blocker report and request architectural review.
- No speculative abstraction, no full-capability boilerplate generation and no requirement to cover all 31 modules before users see a functioning secretary.
- An adapter operation can expand only when a concrete domain use case proves it necessary; extension requires interface evolution tests and ADR if semantically breaking.
- Contract changes require deprecation window or explicit migration. Preserve existing user commitment identifiers.

## Prompt and workflow generation
An autonomous coding/spec agent MAY propose `behavior.yaml`, statechart YAML, templates and evals. It MUST NOT edit protected policy logic or auto-promote its own proposal. Run offline schema/semantic checks, render preview, run deterministic tests and (when routing/communication changes) blind actual-model eval against holdout. Only then can authorized owner apply.

## Evidence classification
`L0` package/docs/schema; `L1` pure functions/policy; `L2` DBOS/Postgres + fakes + crash; `L3` real tool-capable LLM discovery and ERI dialogue; `L4` real authorized provider smoke; `L5` real deployment operational evidence. A lower tier cannot be relabeled as higher. `BLOCKED` and `NOT_VERIFIED_EXTERNAL` are permitted truthful outcomes.
