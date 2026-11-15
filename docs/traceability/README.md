# Traceability matrix

`FULL_REQUIREMENTS_MATRIX.csv` is a generated planning and audit index. The original module FR, AT and RT identifiers and wording are retained; product invariants and explicitly catalogued shared normative obligations are added with source locators. Shared obligations use stable `SH-*` IDs in `SHARED_OBLIGATIONS.json`.

Every matrix row has a planned case and planned test locator. These are design targets, and a locator under `tests/planned/` does not claim that an executable test exists. `executable_test` and `evidence_ref` remain empty and `verification_status` remains `NOT_RUN` until actual test and evidence records are independently added. Related cases from `docs/testing/TEST_LEDGER.csv` are pointers for reuse, not proof of coverage or execution. Regenerate with:

```sh
../.venv/bin/python docs/traceability/build_matrix.py
```

The build preserves the original FR/AT/RT rows in `REQUIREMENTS.csv`, fixes curated FR-to-AT references, adds missing red-team rows and records source snapshot hashes. Slices in the matrix distinguish the first contribution from the full verification horizon; a slice contribution cannot complete a multi-slice module.

## Current gate state

The roadmap is still at S00 and `docs/implementation/implementation_state.json` records S00 gates as `NOT_RUN`. In particular, actual blind model discovery requires the explicitly configured and authorized provider credentials described in `docs/implementation/S00_RUNTIME_CONTRACT.md`; no credential or live-provider evidence is established by this planning work. S00 gates remain unverified, and downstream implementation gates remain blocked until the earliest slice is completed. Nothing in this matrix asserts execution, implementation, or release readiness.
