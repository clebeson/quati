# S00 independent runtime review

Scope: local S00 L1 runtime, compiler, catalog installation, checkpoint and evidence tooling. No live provider or credentials used. These findings do not qualify the runtime for release; the S00 real-model gate remains **BLOCKED**.

## Findings

### High — CLI reports fabricated work as a successful response

`src/secma/cli/main.py:ask` sets `RESPONDED` and returns exit 0 whenever the classifier says `work_needed=false` and `next_action=respond`. It does not constrain the response text or cross-check the user's request. A classifier response can therefore cause a substantive investigation request to receive a false completion claim without any catalog call.

Reproduction (injects a local model result; no provider call):

```sh
PYTHONPATH=src ../.venv/bin/python - <<'PY'
import os, tempfile
from secma.application.ports import ModelRun, ProviderConfig
import secma.adapters.model as adapter
from secma.cli.main import ask

class Fake:
    def __init__(self, config): pass
    def run(self, text, prompt, catalog):
        return ModelRun(text='I completed the investigation and found the cause.',
            classification={'intent':'simple_answer','work_needed':False,
              'next_action':'respond','risk':'low','uncertainty':'low'})

adapter.ModelAdapter = Fake
os.environ.update(SECMA_DATA_DIR=tempfile.mkdtemp(), KEY='synthetic')
code, result = ask('Investigate why conversions fell.',
    ProviderConfig('https://example.test/v1','fixture','KEY',True))
print(code, result['status'], result['text'], result['tool_calls'])
PY
```

Observed: `0 RESPONDED I completed the investigation and found the cause. []`. Final status needs an application-owned response rule that cannot treat a work request as completed based on advisory classification alone.

### High — compiler accepts a path that bypasses the receipt stage

`src/secma/behavior/validated_reference.py:validate_machine` validates selected protected target/action edges, but it does not constrain the `start_work` action to originate from `ACKNOWLEDGED` with the `safe_to_begin` guard. Adding a distinct transition from `RECEIVED` directly to `IN_PROGRESS` with `always/start_work` is accepted. This skips classification and the durable receipt path in the compiled control graph.

Reproduction:

```sh
PYTHONPATH=src ../.venv/bin/python - <<'PY'
from secma.behavior.validated_reference import load_yaml, validate_machine
m = load_yaml('src/secma/assets/examples/statecharts/commitment.yaml')
m['transitions'].append({'source':'RECEIVED','event':'start_without_receipt',
    'target':'IN_PROGRESS','guard':'always','action':'start_work'})
print(validate_machine(m))
PY
```

Observed: validation succeeds with `transition_count: 19`. Constrain all protected actions and transitions to approved source/target/guard tuples, or enforce an equivalent semantic path invariant.

### Medium — `doctor` can report an invalid endpoint as configured

`src/secma/cli/main.py:config_diagnostics` parses the URL but does not validate the port. With `SECMA_BASE_URL=https://example.invalid:bad/v1` plus the other required env settings, `secma doctor --json` reports `provider.configured: true`; `ModelAdapter._validate` later rejects it when asked to run. This makes the diagnostic contradict the adapter and can mislead callers about readiness.

Reproduction:

```sh
PYTHONPATH=src SECMA_BASE_URL='https://example.invalid:bad/v1' \
SECMA_MODEL=x SECMA_API_KEY_ENV=SECMA_API_KEY SECMA_API_KEY=synthetic \
SECMA_ALLOW_LIVE=1 ../.venv/bin/python -m secma doctor --json
```

Observed: `configured: true`. Share one endpoint validator with the adapter and classify invalid configuration as blocked.

## Checks run

```text
../.venv/bin/python -m pytest -q tests/unit/test_runtime.py tests/unit/test_model_adapter.py
24 passed, 1 warning
```

No live provider request was made. Existing checks exercise fixture authorization, schema rejection, provider error sanitization and a request-budget limit, but do not cover the bypasses above. The checkpoint helper now rejects the downstream-slice and stale-PASS mutations observed during the review; those findings were removed after the fixes landed.
