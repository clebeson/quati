# Red Team — M18: Agent and harness adapters

**Target slice:** S04. **Scope:** candidate threats specific to M18, not exploit proof.

## Attack cases

- **M18-RT-01**: An agent inherits tenant-wide credentials.
  - Attack input: a harness that reads `os.environ` for `QUATI_API_KEY`/`OPENROUTER_API_KEY`, requests scope `workspace.admin`, and replays its token against a different binding id.
  - Enforcement point: HarnessPort.start environment builder (`harness_policy.env_allowlist`), scope intersection, and token audience/expiry verification at the gateway.
  - Expected observable rejection: secrets absent from child environment; scope request `FORBIDDEN` `SCOPE_NOT_GRANTED`; replayed token `UNAUTHENTICATED` (audience mismatch); canary absent from logs.

- **M18-RT-02**: Unsupported resume is silently emulated.
  - Attack input: `resume(execution_ref)` against a harness descriptor with `does_not_support: [resume]` after a crash, and a descriptor that claims resume but fails the resume contract probe.
  - Enforcement point: HarnessPort feature gate reading the probed FeatureReport before dispatch.
  - Expected observable rejection: BLOCKED `UNSUPPORTED` `RESUME_UNSUPPORTED` in both cases; no new start recorded; execution remains UNCERTAIN.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
