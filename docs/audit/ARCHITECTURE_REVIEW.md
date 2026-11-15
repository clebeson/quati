# Independent Architecture and Specification Review

Date: 2026-11-15. Scope: original v8 design, before runtime implementation. This review is independent of implementation; it is not release certification.

## Verdict

NO-GO for declaring SECMA implemented or release ready. The modular Python monolith, provider-neutral SCS contracts, trusted policy boundary, DBOS adapter and staged evidence gates are coherent. The package needs contract reconciliation and explicit partial-module milestones before S00 implementation. No additional infrastructure or GUI is warranted.

## Findings

| ID | Severity | Evidence | Deficiency and required correction |
|---|---|---|---|
| ARCH-01 | P1 | `contracts/commitment.schema.json`, `examples/statecharts/commitment.yaml`, RFC-011 | Persisted state enum and reference reducer vocabulary differ. Align them; separate outcome assessment from lifecycle state. |
| ARCH-02 | P1 | RFC-002 vs `contracts/interaction-decision.schema.json` | Social/question/progress action enums conflict. Select one wire vocabulary and explicit question-blocking boolean semantics. |
| ARCH-03 | P1 | M01/M02/M17/M30 PRDs vs S00 and roadmap | Whole-module requirements are attributed to earliest slices although dependencies arrive later. Distinguish first partial implementation from complete module acceptance; track deferred cases individually. |
| ARCH-04 | P1 | Product K2 vs S01 prototype and roadmap | S01 permits non-durable in-process work despite universal persistent-commitment language. Label S00/S01 prototype requests explicitly, prohibit durable/background promises and retain K2 as release blocker. Do not introduce DBOS early merely to hide this distinction. |
| ARCH-05 | P1 | RFC-011 vs reference commitment chart | Cancellation after possible effects lacks reconciliation state; nonterminal timeout paths and budget-exhaustion behavior are incomplete. Fix before production activation; static terminal reachability alone does not prove runtime recovery. |
| ARCH-06 | P1 | RFC-001, ADR-012 vs SCS schema | Lifecycle omits VALIDATED and assurance omits C0; definition carries assurance/lifecycle claims without independent provenance. Reconcile vocabulary and require trusted binding/assurance records; manifest claims cannot grant activation. |
| ARCH-07 | P1 | M25, RFC-007, M19 | Authorization binding, revocation timing and operation-signature semantics are prose only. Specify exact immutable actor/tenant/operation/destination/input-digest/policy scope binding before implementing external effects. Read-only S00 must deny effects rather than infer approval. |
| ARCH-08 | P1 | `REQUIREMENTS.csv`, PRDs | FR rows generally link only AT-01 and RT-01; generic public-path wording does not prove each requirement. Add FR/AT/RT/contract/slice/test/evidence mapping with explicit gaps, including shared-section obligations and product invariants. |
| ARCH-09 | P2 | M08 module map and PRD vs roadmap S01 | M08 first appears in S01 but is labelled S03. Identify S01 foundations and S03 completion. |
| ARCH-10 | P2 | README package contents | Claims a deployment/packaging RFC but only RFC-001 through RFC-012 exist and none is deployment-specific. Remove unsupported inventory claim; existing TRD/M28/S07 cover intended scope. |
| ARCH-11 | P1 | M17-FR-02, RFC-004 | Region and pricing cannot be established merely by successful transport probes. Distinguish observed protocol features from operator/provider-attested metadata and unknown values; never imply verified residency from tool-call success. |
| ARCH-12 | P2 | Consolidated spec | Duplicated normative content risks drift. Source files are authoritative; regenerate aggregate after corrections and verify source inclusion. |
| ARCH-13 | P1 | Live benchmark, holdout policy | Public seeds do not constitute independent sealed holdout; no universal model threshold exists. Require predeclared per-role metrics, sample counts, confidence intervals/baseline and zero observed critical safety failures; S00 discovery alone is not general competence certification. |
| ARCH-14 | P2 | RFC-006, M21 | Transitive discovery has scope/budget controls, but coverage must expose unresolved external references. No downloading/executing dependency code as a side effect of documentation traversal. Technology claims remain unverified until pinned SDK qualification. |

## Architecture and integration conclusions

Keep domain and application ports free of provider SDK types. One reference adapter per boundary is sufficient initially. No 31-service decomposition, new distributed broker, obligatory Docker or mandatory graph framework is justified. DBOS state and SECMA business state have distinct ownership; no automatic engine-history portability or universal exactly-once external effects may be claimed.

CLI delivery acknowledgement must mean successful output to the configured sink, not proof that a human read it. A failed/broken output pipe must not silently count as successful delivery. External adapters need recipient checks and explicit uncertain-effect reconciliation at their actual dispatch boundary. Artifact and memory access must retain tenant/actor scope before retrieval and after source fetch. Profile text, tool descriptions, transcripts and imported repositories remain untrusted data.

## Read coverage and limitations

Reviewed AGENTS/README; all 31 module PRDs; product, module and stakeholder coverage documents; all 12 ADRs and 12 RFCs; all 11 diagrams; TRD; roadmap and S00–S07 handoffs; relevant contracts; benchmark/holdout policy; research register and risk coverage report. The consolidated document was checked by exact source inclusion: 39 source documents are embedded verbatim, with module-map links rebased; remaining text consists of headings/separators and that map. Repeated PRD boilerplate was reviewed once and module-specific sections individually. Referenced public technology pages were inventoried, not live-qualified in this architecture review; no compatibility claim is certified by their presence. Runtime/security/test-tool audit is a separate review workstream.

## Required phase evidence

S00 requires actual authorized provider tool trajectories plus local policy/compiler negatives. S01 requires real multi-turn behavior and explicit prototype limits. S02 requires PostgreSQL/DBOS interruption and concurrency evidence before durable commitments. S03 requires lineage/access-controlled retrieval and profile rollback. S04 needs a real harness plus separately classified simulated connector tests. S05 needs real reasoning over controlled evidence. S06 needs independent holdouts and promotion checks. S07 needs actual supported-OS and enterprise policy measurements. None can be declared complete from this review.
