# RFC-011 — Statechart Contract Compiler and Controlled Agency

Every nontrivial SCS capability MUST have a **control policy** with allowed lifecycle states, obligations, legal transitions, guards, deadlines and failure handling. This does **not** mean every capability requires LangGraph or a static graph of reasoning. Simple capabilities may have a single terminal result; long-running investigations can have complex internal workflows owned by their executor.

## Proposed mechanism
Represent control states and transitions in declarative YAML conforming to a JSON Schema. A pure-Python compiler validates all states exist, initial/terminal reachability, forbidden back-edges, known guard/action registry, transition uniqueness and bounded revisit counts. It emits a deterministic transition table, Mermaid diagram and semantic digest. In MVP use a simple trusted `next_state(current, event, policy_context)` reducer persisted to the commitment ledger. `transitions` (MIT) is optional if future hierarchical/parallel complexity justifies it; LangGraph is optional inside specialist harnesses rather than part of the Quati protected kernel.

## Hard state constraints
- State changes are transactional and compare expected revision.
- External side effects occur only after authorization; guards must be pure and deterministic.
- `DELIVERED` requires outcome evidence and delivery acknowledgement, not only model text.
- `CANCEL_REQUESTED` can transition to cancelled, complete-with-effects, or needs-reconciliation, not pretend past effects reversed.
- Waiting for optional user input must not block safe parallel read-only steps.
- Every nonterminal state must have a recovery/timeout/escalation path; all cycles need explicit attempt/cost/time budgets.

## Normative v2 artifacts
The durable commitment lifecycle is the v2 control table `contracts/commitment-control-v2.json` (CSV view `docs/architecture/CONTROL_TRANSITIONS.csv`). Its guards and actions are defined in `docs/architecture/GUARD_PREDICATES.md` and registered in `contracts/guard-registry.json`; S02-T01 implements the reducer against them. The v1 chart (`examples/statecharts/commitment.yaml`, `contracts/commitment.schema.json`) is a legacy compiler fixture and is never activated for accepted durable commitments.

## Complexity thresholds
Use an enum/reducer for five to ten predictable states; add declarative `transitions` only when more than one stateful workflow actually benefits. Do not generate arbitrary Python workflow code from a natural-language prompt and trust it. Agent-produced machine drafts must be reviewed for changed authority and tested before promotion.
