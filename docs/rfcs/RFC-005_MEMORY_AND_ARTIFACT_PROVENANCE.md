# RFC-005 — Long-Term Memory, Artifact Lineage and Knowledge Boundaries

Memory stores are not authoritative security boundaries. SECMA maintains scope-aware `Episode`, `Commitment`, `Decision`, `Preference`, `ArtifactVersion`, `SourceRef` and `Claim` records with original sources, authorizations, timestamps and correction history. Retrieval proceeds through ACL and tenant filters both before similarity search and after source fetch. A brain may be Markdown/Obsidian, Git repo, GBrain, future LLM Wiki or remote knowledge service. A provider can be read-only.

A request such as “recreate last week's study for Company X” must identify the original task's analysis method and evidence, or ask a focused disambiguation question. A chart modification must locate the original editable source and version; if only a screenshot is found, the secretary must not invent underlying data. Preference learning has source and confidence and never modifies policy privileges.

Every contribution to a shared/team brain needs an approved scope and provenance; information does not silently move from private to organization-wide. No prompt retrieved from a document can override trusted instructions. Indexing and original artifact content may have different retention policies.
