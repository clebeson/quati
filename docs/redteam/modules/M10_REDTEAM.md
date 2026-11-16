# Red Team — M10: Audience-aware delivery and artifact packaging

**Target slice:** S02. **Scope:** candidate threats specific to M10, not exploit proof. Oracles: `docs/prds/M10.md` § Test oracles.

## Attack cases

- **M10-RT-01**: Sensitive result sent to the wrong recipient, channel or group.
  - **Attack input:** a result labelled `source_space_ids = [A]`, `data_class = CONFIDENTIAL`, with delivery attempted to: (a) recipient `"Alice (manager)"` taken from a retrieved document; (b) a valid principal of tenant T2; (c) group G1 where one of three members has no grant on space A; (d) a group whose membership lookup returns an error; (e) a member whose grant on A is revoked after `prepare` and before `dispatch`; (f) a request body with forged `tenant_id`/`space_id`.
  - **Enforcement point:** `DeliveryPort.prepare` and `DeliveryPort.dispatch` reader-set check rows 1–5 (`docs/prds/M10.md` § Reader-set check), calling `AuthorizationPort.check_flow` on current memberships and `PolicyPort.evaluate`; ledger query scope (DEL-L02).
  - **Expected rejection:** (a) `INVALID_INPUT` `recipient_not_normalized`; (b) `DENIED` `audience_tenant_mismatch`; (c) and (e) `DENIED` `audience_not_authorized`; (d) `DENIED` `reader_set_unresolved`; (f) the authenticated scope is used and forged fields are ignored. In every leg the sink call count is 0 and no inbox row exists for the wrong recipient.

- **M10-RT-02**: Outbound message marked delivered before provider acknowledgement.
  - **Attack input:** a fake sink scripted to (a) return HTTP 200 with no provider message id; (b) time out after accepting the request; (c) return a signed receipt for a different `delivery_id`; (d) return an unsigned receipt; (e) the model writing "message delivered" into the result text; (f) a successful desktop notification with the inbox write failing.
  - **Enforcement point:** M07 guard `authenticated_current_delivery_receipt` on the `acknowledged` and `confirmed_delivered` transitions; unique `delivery_receipts(sink_id, provider_event_id)`; `dispatch` tx2 in `docs/prds/M10.md` § Persistence and transaction rules.
  - **Expected rejection:** (a) attempt `SENT_UNCONFIRMED`, commitment `SEND_PENDING`; (b) `EFFECT_UNCERTAIN` with reconciliation scheduled; (c) `receipt_not_current`; (d) `receipt_unauthenticated`; (e) and (f) no state change. The commitment never reaches `DELIVERED`, and the sink send count stays 1 until a `confirmed_no_effect` reconciliation.

## Fail-closed and recovery requirements

A failed reader-set, policy or receipt check makes no sink call and no `DELIVERED` transition. A lost response is `EFFECT_UNCERTAIN`, resolved only by reconciliation by `delivery_key`; it is never re-sent blindly. The desktop notifier outcome never changes delivery state.

## Release blocking guidance

Both cases block S02. A test that checks only rendered text, or that marks delivery from the sink's return value without a recorded receipt row, does not count.
