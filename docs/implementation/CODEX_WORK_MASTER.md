# Authorization precondition

This is a FUTURE implementation handoff. Current user instruction is specification
audit only. Do not execute runtime implementation from this file until explicitly
authorized. Use WORK_PACKAGES.json and SMALL_MODEL_EXECUTION_PROMPT.md for bounded
steps, seals, evidence and persistent resume. Retained code is an unapproved candidate.

# Codex Work Master Handoff — SECMA v8

Implement SECMA from this English-only authoritative specification. Your job is to produce working, testable Python code, not merely to recreate more PRDs. Start exclusively with `S00`; do not implement downstream slices or a GUI. The canonical order is `README.md` → `AGENTS.md` → `docs/vision/PRODUCT_PRD.md` → `docs/trd/TECHNICAL_REFERENCE.md` → `docs/rfcs/RFC-010_BEHAVIOR_COMPILER.md` → `docs/rfcs/RFC-011_STATECHART_MODEL.md` → `docs/implementation/SLICES/S00.md`.

## Initial workflow
1. Run `python spec_tools/validate_spec.py` and `python -m pytest tests/test_reference_compiler.py` to check that source specification is internally coherent; note these are L0 checks only.
2. Confirm which model transport has authorized credentials for **real** tool calling; ask only for the minimum missing secret reference if required. Use `secma doctor` to report endpoint/model/feature gates.
3. Create a Python module structure matching package boundaries; implement only the CLI, safe policy, Pydantic AI provider, typed intent router, behavior compiler, and SCS search/describe/invoke with two confusable fake capabilities.
4. Create the L3 harness that starts from `secma ask` with an ordinary natural-language utterance, observes the real provider's actual tool calls, captures arguments and final output, and verifies no gold capability ID was given in model input. Also test a greeting that MUST not create a job.
5. Store redacted traces, artifacts and a realistic cost/latency report. Update state to `PASS` only when all S00 gates are proven. Record `BLOCKED` rather than faking tool capability if your provider/model does not support it.
6. Produce PR-ready diff and an independent audit report. Do not merge or deploy without approval; do not obtain production tokens unprompted.

## Future slice constraints
ERI, durability, providers and specialist agents are integrated one slice at a time, following roadmap; don't scaffold 31 services. Once DBOS is introduced, domain packages must remain isolated from DBOS. Every new adapter advertises feature limitations; a missing harness does not take down SECMA. The user values short, helpful progress and context continuity more than a wall of implementation logs.

## Mandatory reporting format
`Slice`, `Commit`, `Requirements covered`, `Changed files`, `Tests and proof tiers`, `Real LLM/provider used?`, `Red-team outcome`, `Resource/cost measurements`, `Blocked/unverified items`, `Next gate`, `Rollback`. All in English. Do not report external interoperability as passed based on a fake HTTP server.
