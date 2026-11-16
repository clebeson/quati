"""Every shipped example statechart passes the M30 semantic validator (regression for LOG-0019)."""
from pathlib import Path

import pytest
import yaml

from quati.domain.statechart import validate_statechart_semantics

EXAMPLES = sorted((Path(__file__).resolve().parents[2] / 'examples' / 'statecharts').glob('*.yaml'))


def test_examples_exist():
    assert {path.name for path in EXAMPLES} >= {'commitment.yaml', 'interaction.yaml'}


@pytest.mark.parametrize('path', EXAMPLES, ids=lambda path: path.name)
def test_example_statechart_is_semantically_valid(path):
    summary = validate_statechart_semantics(yaml.safe_load(path.read_text(encoding='utf-8')))
    assert summary.state_count >= 2 and len(summary.statechart_hash) == 64
