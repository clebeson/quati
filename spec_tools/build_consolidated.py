"""Rebuild the reading bundle from authoritative source documents."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = [
    ('0. Execution and Governance Index', 'IMPLEMENTATION_READY_INDEX.md'),
    ('0.1 Project Structure', 'docs/architecture/PROJECT_STRUCTURE.md'),
    ('0.2 Boundary Contracts', 'docs/architecture/BOUNDARY_CONTRACTS.md'),
    ('0.3 Delivery Governance', 'docs/governance/DELIVERY_GOVERNANCE.md'),
    ('0.4 Persistent State and Memory', 'docs/governance/PERSISTENT_STATE_AND_MEMORY.md'),
    ('0.5 Test Execution Protocol', 'docs/testing/TEST_EXECUTION_PROTOCOL.md'),
    ('1. Product Definition', 'docs/vision/PRODUCT_PRD.md'),
    ('2. Technical Reference', 'docs/trd/TECHNICAL_REFERENCE.md'),
    ('3. Module Inventory', 'docs/vision/MODULE_MAP.md'),
    ('4. Implementation Roadmap', 'docs/implementation/ROADMAP.md'),
    ('5. Test Coverage Rationale', 'docs/testing/RISK_COVERAGE_REPORT.md'),
    ('6. Prompt and Statechart Compiler', 'docs/rfcs/RFC-010_BEHAVIOR_COMPILER.md'),
    ('7. Statechart Invariants', 'docs/rfcs/RFC-011_STATECHART_MODEL.md'),
    ('8. Small Model Context Engineering', 'docs/rfcs/RFC-012_SMALL_MODEL_CONTEXT.md'),
    ('9. Technology Evidence', 'docs/research/SOURCE_EVIDENCE.md'),
]


def build() -> str:
    sections = SECTIONS + [(f'Module M{n:02}', f'docs/prds/M{n:02}.md') for n in range(1, 32)]
    result = ['# Quati v8 — Consolidated English Product and Technical Specification',
              '> Generated reading bundle. Canonical detail remains in source files and their IDs. '
              'Design requirements do not constitute runtime evidence. Rebuild with '
              '`python spec_tools/build_consolidated.py`.']
    for title, path in sections:
        content = (ROOT / path).read_text(encoding='utf-8').strip()
        if path.endswith('MODULE_MAP.md'):
            content = content.replace('(../prds/', '(docs/prds/')
        result.append(f'## {title}\n\nSource: `{path}`\n\n{content}')
    return '\n\n---\n\n'.join(result) + '\n'


if __name__ == '__main__':
    (ROOT / 'QUATI_CONSOLIDATED_SPEC_V8_EN.md').write_text(build(), encoding='utf-8')
