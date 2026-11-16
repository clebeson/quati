# Factory Instruction: Extending Durable Ports, Capabilities and Prompts

**Extension trigger:** an actual Quati use case requires an operation that cannot be expressed through the existing contract, with a test showing why. A new general operation must have domain semantics and a typed contract; implement in the active ledger-backed DurableRunner implementation (SQLite LOCAL, PostgreSQL contract-tested; ADR-015/016) and verify under retries/crash. A future DBOS or Temporal adapter may map differently. Do not pre-implement a generic engine pass-through; yet do not forbid backend-specific power inside a ledger backend or future adapter when it is required for correctness/performance.

**Capability addition:** write an SCS contract defining desired outcome, inputs/outputs, safety and evidence; create provider binding with feature flags; verify positive/negative intent descriptions, policy and provider health; stage/enable after relevant test tier. The LLM's visible catalog updates without root-prompt editing. Evidence success belongs to the user outcome, not manifest creation.

**Prompt change:** change a versioned role or interaction profile in declarative YAML or propose it via a coding agent. Compiler validates and renders, checks security invariants, runs deterministic eval and live-model holdout if communication/routing changes; an authorized owner then promotes. Default behavior is no permanent modification after a single piece of feedback.

**Statechart change:** begin by identifying a missing/incorrect transition, add it to the DSL with existing registered pure guard/action. If a new guard is necessary, write and test it in protected code (L1) with security review and expose only the guard ID to YAML. Do not put executable expressions in configuration. Generate transition diagram and a machine digest; prevent mid-flight statechart version switching unless migration is defined.

**Model role change:** benchmark candidate on relevant blind tasks and cost. If cheap model fails deeper reasoning but works for greetings, restrict it to that role. Do not extrapolate API functionality from model/vendor brand.
