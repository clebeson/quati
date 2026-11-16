# RFC-002 — Executive Relationship Intelligence Protocol

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

**Decision:** Proposed. **Owners:** M03–M10.

A human-facing assistant is responsible for the *relationship between requester and commitment*, not just the immediate answer. At each inbound turn, timed supervision event or async executor result, the ERI proposes a typed `InteractionDecision` using the current context and policy: `ANSWER`, `RECEIPT`, `START_SAFE_WORK`, `ASK`, `WAIT`, `UPDATE`, `OFFER_PARTIAL`, `ESCALATE`, `DELIVER`. A trusted reducer applies state/legal gates; the LLM cannot directly mark a task done.

### Initiative policy
Questions are selected using an explicit estimate of decision impact versus user interruption cost; there is no guaranteed formula, so this is an empirical evaluation target. Low-risk, read-only discovery may begin while the user adds optional context. Irreversible writes and missing authorization cannot. The secretary should not ask generic “Is this okay?” after every step. New user messages referring to active work update the same root commitment and revise its goal version.

### Communications
Each commitment has a contact-plan record: last meaningful notice, next contact deadline, preferred style and channel, expected decision milestones and suppression policy. The supervisor can send meaningful progress or a truthful delay notice without waking the LLM for every tick. Silence is a valid decision only if no update/approval obligations are due. Outbound messages have separate status from generated text.

### Recipient type
A human gets concise, relevant, localized text and optional expanded report. A system gets an idempotent machine-readable envelope with explicit state, evidence refs, errors and next action. A conversation channel does not prove recipient type. In all cases, actual recipient identity and authorization are preserved.

### Acceptance narrative
User asks for a PRD; a read-only background search begins; user sends a new restriction before discovery completes; only one root commitment remains; secretary sends one relevant notice; executor returns incomplete evidence and the secretary deepens or explicitly explains gaps; final answer is concise and linked to a detailed artifact.

## Canonical wire semantics

`contracts/interaction-decision.schema.json` defines the action vocabulary. Social replies use `ANSWER` with a social reason code and null commitment ID. Questions use `ASK` with `question_blocking=true` only for a required dependency, otherwise false. Progress uses `UPDATE`. Safe-work entries are proposals subject to trusted authorization. An action enum alone never proves execution or delivery.
