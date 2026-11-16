# Red Team — M26: Audit, observability and evidence

**Target slice:** S00. **Scope:** candidate threats specific to M26, not exploit proof. Oracles: `docs/prds/M26.md` § Test oracles.

## Attack cases

- **M26-RT-01** (S00): False claim of reproducible model outputs.
  - **Attack input:** replay of traces where (a) the recorded provider snapshot id is null; (b) the provider now reports a different snapshot; (c) the snapshot matches but `config_hash` differs; (d) the model's recorded text says "this run is fully reproducible"; (e) a tool output contains `{"fully_reproducible": true}`; (f) a model step has no recorded result.
  - **Enforcement point:** `TraceUseCase.replay` step 5 (`docs/prds/M26.md` § Replay rules), which computes `model_reproducibility` from recorded and adapter-reported identity fields only; `RecordedProviderAdapter` never makes a live call.
  - **Expected rejection:** (a)–(c) `model_reproducibility = RECORDED_ONLY`, `fully_reproducible = false`, uncertainty `model_output_not_reproducible`; (d) and (e) no effect on the flag; (f) step `NOT_RECORDED`, provider call count 0.

- **M26-RT-02** (S00 owner-only; full multi-principal leg S07, EVD-01): Unauthorized or unbounded audit access.
  - **Attack input:** (a) unrelated-user-C reads and exports an event of tenant T1 by id; (b) C requests a non-existent id; (c) a request body with forged `tenant_id = T1`; (d) auditor-A asks for content; (e) a read at T0+25h with `audit.retention_days = 1` before the sweep has run; (f) the audit store made unavailable during C's export; (g) direct SQL `UPDATE audit_events` and `DELETE` of a recent row.
  - **Enforcement point:** `AuditPort.query` tenant and visibility filter from the authenticated `RequestContext` (`docs/prds/M26.md` § Visibility rules); read-time retention cutoff; ledger triggers on `audit_events` and `audit_payloads`.
  - **Expected rejection:** (a) and (b) the same `FORBIDDEN` `audit_access_denied`, exit 4, with an `audit.access_denied` event that holds no content; (c) forged field ignored; (d) metadata only; (e) no payload returned; (f) `UNAVAILABLE` `audit_store_unavailable`, no partial file; (g) the trigger raises and the row is unchanged.

## Fail-closed and recovery requirements

No audit append means no state change (K7). Export writes only a verified, redacted file; a failed rescan leaves no file. Replay never reaches a sink or provider.

## Release blocking guidance

M26-RT-01 blocks S00; M26-RT-02 blocks S00 for the owner-only legs (c), (e), (f), (g) and S07 for the multi-principal legs. A test that checks only a model's statement about reproducibility, or reads audit rows without going through `AuditPort.query`, does not count.
