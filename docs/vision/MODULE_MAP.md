# SECMA v8 — Module Inventory

The architecture contains **31 responsibility modules** but deliberately starts as a modular Python monolith, not 31 services or LLM agents. Each module has a detailed normative PRD and an independent red-team sheet.

| ID | Module | Earliest slice | Related modules |
|---|---|---|---|
| M01 | [CLI, packaging and local lifecycle](../prds/M01.md) | S00 | M02 M17 M26 |
| M02 | [Identity, requester and authorization context](../prds/M02.md) | S00 | M25 |
| M03 | [Executive Relationship Intelligence (ERI)](../prds/M03.md) | S01 | M04 M05 M06 M07 M09 M10 M30 M31 |
| M04 | [Intent, reference and ambiguity resolution](../prds/M04.md) | S01 | M11 M31 |
| M05 | [Initiative and clarification economy](../prds/M05.md) | S01 | M04 M25 M30 |
| M06 | [Expectation and communication management](../prds/M06.md) | S02 | M07 M10 M13 M30 |
| M07 | [Commitment ledger and durable execution](../prds/M07.md) | S02 | M02 M25 M26 |
| M08 | [Triage, prioritization and task planning](../prds/M08.md) | S03 | M04 M05 M14 M15 M30 M31 |
| M09 | [Sufficiency, evidence and stopping judgment](../prds/M09.md) | S02 | M07 M10 M26 |
| M10 | [Audience-aware delivery and artifact packaging](../prds/M10.md) | S02 | M06 M07 M12 |
| M11 | [Episodic and semantic memory](../prds/M11.md) | S03 | M02 M07 M25 M26 |
| M12 | [Versioned artifacts and reproducible edits](../prds/M12.md) | S03 | M11 M26 |
| M13 | [Personalization and relationship preferences](../prds/M13.md) | S03 | M02 M03 M11 |
| M14 | [SCS capability manifest and registry](../prds/M14.md) | S00 | M02 M25 M26 |
| M15 | [Capability discovery, resolver and execution controller](../prds/M15.md) | S00 | M14 M17 M25 M31 |
| M16 | [Agent Skills discovery and packaging](../prds/M16.md) | S03 | M14 M19 M25 |
| M17 | [LLM providers, routing and competence profiles](../prds/M17.md) | S00 | M25 M26 M31 |
| M18 | [Agent and harness adapters](../prds/M18.md) | S04 | M14 M15 M25 M26 |
| M19 | [MCP and action gateway](../prds/M19.md) | S04 | M02 M25 M26 |
| M20 | [Second-brain provider adapters](../prds/M20.md) | S04 | M02 M11 M25 |
| M21 | [Knowledge, ecosystem and repository discovery](../prds/M21.md) | S05 | M19 M20 M25 |
| M22 | [Software engineering discovery and specifications](../prds/M22.md) | S05 | M21 M12 M09 |
| M23 | [Incident investigation and root-cause analysis](../prds/M23.md) | S05 | M21 M19 M09 |
| M24 | [Data analysis and causal inquiry](../prds/M24.md) | S05 | M19 M20 M09 |
| M25 | [Preventive policy and approvals](../prds/M25.md) | S00 | M02 |
| M26 | [Audit, observability and evidence](../prds/M26.md) | S00 | M02 |
| M27 | [Evaluation-driven improvement and self-evolution](../prds/M27.md) | S06 | M09 M13 M14 M25 M26 M30 |
| M28 | [Portability, operations and enterprise deployment](../prds/M28.md) | S07 | M01 M07 M17 M18 M25 |
| M29 | [Channel and inbound/outbound messaging](../prds/M29.md) | S04 | M02 M06 M07 M10 M25 |
| M30 | [Behavior package, prompt and statechart compiler](../prds/M30.md) | S00 | M14 M25 M26 |
| M31 | [Context engineering and model competence calibration](../prds/M31.md) | S00 | M17 M30 M15 |

Modules M30 and M31 are **new canonical additions**: configuration-to-behavior compilation and competence-aware context engineering. The previous 29-module inventory is retained as M01–M29, with each PRD rewritten in English and updated to fit the new controller design.
