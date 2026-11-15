# AGENTS.md — Testing and Proof

The tests delivered in v8 are **L0 specification/compiler tests only**. Use `docs/testing/TEST_STRATEGY.md` for new runtime tests. New tests MUST name the requirement or risk boundary, call the public path for behavior claims, record proof tier, avoid gold-label leakage in LLM prompts, and distinguish fake provider compatibility from live authenticated provider smoke. Don't add tests merely to increase counts. Keep logs and fixtures secret-free.
