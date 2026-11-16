# RFC-009 — Professional Channels, Sources and Proactivity

**Status:** Accepted for implementation (specification v8.1, 2026-11-15). Normative where referenced by a PRD, contract or work package.

Inbound events include user/agent requests, calendar changes, email, Slack, meetings/transcripts, repository changes, telemetry alerts, scheduled checks and provider callbacks. Ingestion verifies origin, deduplicates, applies ACLs and maps information to potential commitments. A transcript that says “owner: do X” is not a valid command without authenticated speaker attribution and policy.

Proactivity has permission tiers: observe, suggest, draft, read-only investigate, execute preauthorized reversible action, and high-risk approval. Delivery is governed by expectation manager and quiet-time policy; a user speaking in a meeting is not blanket permission to send messages on their behalf. Fake provider signatures, expired subscriptions and retries are local proof; real-provider smoke remains an explicit stage.
