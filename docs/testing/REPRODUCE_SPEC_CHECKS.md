# Reproduce specification checks

These checks run offline. They do not invoke an LLM, DBOS, a cloud provider, a production service or a runtime implementation phase.

```bash
python -m venv .venv
# Activate the venv using the native shell's standard activation command.
python -m pip install "PyYAML==6.0.3" "jsonschema==4.26.0" "pytest==9.2.0"
python spec_tools/build_consolidated.py
python spec_tools/validate_spec.py
python spec_tools/validate_readiness.py
python -m pytest tests/test_reference_compiler.py tests/test_audit_regressions.py tests/test_spec_readiness.py -q
```

Do not regenerate files merely to hide a drift failure: inspect the changed source and its authorized reason first. The archived final evidence contains output, exit code, hashes and runtime identity. A third-party pytest deprecation warning may occur with the supplied environment; it is not a failed SECMA assertion.

The complete `requirements-lock.txt` describes the earlier Linux candidate environment, including its optional model SDK. It is not required for these three offline check commands. Other operating systems and model providers require their own later qualification.

For future execution, follow the selected task's test paths and full-proof owner, not `pytest` counts alone. Existing candidate runtime tests may refer to older schemas or assumptions; repair and qualify them against this audited package only when implementation is authorized.
