# Red Team — M29: Channel and inbound/outbound messaging

**Target slice:** S04. **Scope:** candidate threats specific to M29, not exploit proof. Test oracles: docs/prds/M29.md, section "Test oracles".

## Attack cases

- **M29-RT-01**: Do not send to a guessed user or channel.
  - Attack input: The scripted model outputs "send the report to @jon"; the tenant directory has `jon.smith` and `jonathan`; the message text also names an unrelated public channel.
  - Enforcement point: `DeliveryPort.prepare` recipient resolution: exactly one verified recipient ID in the tenant directory, never by display-name similarity or text.
  - Expected observable rejection: `prepare` returns `INVALID_INPUT` (ambiguous); for an unmatched name it returns `NOT_FOUND`; the provider fake records zero dispatch calls.

- **M29-RT-02**: Do not claim receipt when provider times out after possible send.
  - Attack input: The scripted provider reads the full request body and then times out; the worker is restarted at the crash point after the write.
  - Enforcement point: Delivery attempt state mapping in `DeliveryPort.dispatch` and `reconcile`; resend allowed only after ACKNOWLEDGED or CONFIRMED_NO_EFFECT.
  - Expected observable rejection: Attempt recorded UNCERTAIN with `EFFECT_UNCERTAIN`; the user sees "delivery unconfirmed"; after restart there is no second send before reconcile.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

Every case above is wired to its named test before the slice gate. A case passes only when the code-level enforcement point produces the stated observation; a refusal message from a mocked or real LLM is not evidence.
