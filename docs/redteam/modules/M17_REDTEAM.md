# Red Team — M17: LLM providers, routing and competence profiles

**Target slice:** S00. **Scope:** candidate threats specific to M17, not exploit proof.

## Attack cases

- **M17-RT-01**: A compatibility label is taken as proof of supported functions.
  - Attack input: provider `/models` entry `{"supported_parameters":["tools","response_format"]}`, base URL path containing `openai`, and a model named `gpt-tools-pro`, with no probe run.
  - Enforcement point: `FeatureReport` construction in `ModelPort.probe` (features only from passed nonce probes) and the M15 `MODEL_INCOMPATIBLE` hard filter.
  - Expected observable rejection: FeatureReport `tools` NOT_VERIFIED; capability requiring tools filtered and invoke returns UNAVAILABLE `UNSUPPORTED` `MODEL_INCOMPATIBLE`.

- **M17-RT-02**: Codex sign-in is used as an OpenAI API key.
  - Attack input: `QUATI_API_KEY_ENV` naming a variable whose value is the contents of a Codex/ChatGPT sign-in session file, or config `secret_ref: file:~/.codex/auth.json`.
  - Enforcement point: provider config loader secret-ref validation (env var or configured secret store only; session token shapes and session file paths rejected) and the trace redactor.
  - Expected observable rejection: `NOT_CONFIGURED` `API_KEY_REF_INVALID`, exit 3, no HTTP request sent; token canary absent from trace and output.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
