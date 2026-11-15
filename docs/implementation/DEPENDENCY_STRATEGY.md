# Dependency and Concurrency Strategy

Dependencies in module PRDs describe semantic relationships, **not prerequisites to implement all those modules in full**. S00 provides interfaces/stubs for identity and audit; later slices replace them with persistent counterparts. Dependencies are always satisfied through a public port. Never let an optional provider import a required provider into the kernel.

`M30 BehaviorCompiler → M31 ContextEnvelope → M17 ModelProvider → M15 CapabilityResolver → M03 ERI → M07 Ledger/DBOS → M10 Delivery` is the main proof path, while `M02 Identity + M25 Policy + M26 Evidence` protect every stage. Import cycles in Python packages are forbidden; module references in PRDs may be conceptual cycles (ERI receives memory; memory indexes ERI) but code contracts are unidirectional through application ports/events.

Stage S00 should deliver sub-PRs in this order: package/CLI, schema/policy compiler, provider feature probe, SCS registry/discovery, blind model eval. Stage S01 should deliver conversation classification, context revision, conditional question, safe task kickoff. Stage S02 should deliver durable ledger, DBOS worker, inbox/outbox, quality gate. After S02, supplier-specific adapters can develop in parallel with independent smoke/eval gates.
