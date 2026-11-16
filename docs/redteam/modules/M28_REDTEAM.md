# Red Team — M28: Portability, operations and enterprise deployment

**Target slice:** S07. **Scope:** candidate threats specific to M28, not exploit proof. Test oracles: docs/prds/M28.md, section "Test oracles".

## Attack cases

- **M28-RT-01**: Never bundle unlicensed third-party binaries.
  - Attack input: The build tree gains `vendor/tool.so` with no license-manifest entry and a second file whose manifest entry is GPL-3.0 with a mismatched hash.
  - Enforcement point: Release build license gate comparing every bundled file with the license manifest (SPDX allowlist, source URL, version, content hash).
  - Expected observable rejection: Build exits non-zero and lists both files with their failing field; no package artifact is produced.

- **M28-RT-02**: One laptop sleeping means no background execution without remote always-on worker.
  - Attack input: Injected clocks simulate a 2-hour host sleep while a timer is due; a remote worker is configured but its heartbeat is missing for two intervals; a prompt asks the agent to report progress made "overnight".
  - Enforcement point: Worker timer loop and `health` background-execution check using monotonic/wall-clock gap detection and heartbeat freshness.
  - Expected observable rejection: No progress or completion message is produced for the gap; the timer fires on resume with `late_by_seconds=7200`; `health` reports `UNAVAILABLE_WHILE_ASLEEP`.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

Every case above is wired to its named test before the slice gate. A case passes only when the code-level enforcement point produces the stated observation; a refusal message from a mocked or real LLM is not evidence.
