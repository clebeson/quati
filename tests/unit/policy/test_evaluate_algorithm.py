"""M25-FR-02 oracle locator (docs/prds/M25.md, Test oracles).

The discriminating body lives in ``tests/unit/test_s00_t02_policy.py`` next to its shared
fixtures; this locator collects that exact test function under the planned path.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_s00_t02_policy import test_decision_table_rows_and_rule_order_invariance  # noqa: E402,F401
