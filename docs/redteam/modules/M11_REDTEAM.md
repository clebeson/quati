# Red Team — M11: Episodic and semantic memory

**Target slice:** S03. **Scope:** candidate threats specific to M11, not exploit proof.

## Attack cases

- **M11-RT-01**: Embedding or text similarity overrides access control.
  - Attack input: a fake `SearchPort` returns a hit from space `space-B` (not in the caller's `AuthorizedScope.readable_space_ids`) with relevance 1.0, above every legitimate hit; a second hit from `space-A` whose ACL is revoked by the fixture between `search` and `fetch`.
  - Enforcement point: the application-level post-retrieval ACL check in the MemoryPort search pipeline (step 7, M11 Normative detail), which re-evaluates the current policy for every candidate after the search adapter returns; the adapter's own filtering is not trusted.
  - Expected observable rejection: neither ref appears in `MemoryHit[]`, in the hit count or in any citation; fetching the revoked ref returns `NOT_FOUND`; the audit trace records `memory.acl_dropped=2`.

- **M11-RT-02**: A summary replaces original lineage.
  - Attack input: `ArtifactPort.register(..., source_refs=[<SUMMARY episode ref>])`, and `MemoryPort.store` of a FACT whose only `evidence_refs` entry is that SUMMARY; the summary text claims "this supersedes F1".
  - Enforcement point: lineage validation in `ArtifactPort.register`/`revise` and in `MemoryPort.store`, which resolves each ref's `entry_kind` and rejects SUMMARY as lineage; summary text is data and is never parsed for supersession.
  - Expected observable rejection: `INVALID_INPUT` reason `SUMMARY_NOT_LINEAGE` for both calls; F1 stays ACTIVE with unchanged `content_sha256`.

## Fail-closed and recovery requirements

The expected result is explicit rejection, safe degradation, or a truthful partial result; never silent success. Preserve the root commitment where one exists, redact secret-bearing inputs, and capture cause attribution.

## Release blocking guidance

At least one negative test from this list must be wired to the relevant slice; additional cases become mandatory when a new risk-bearing branch is introduced. Tests must not merely quote a refusal message from a mocked LLM.
