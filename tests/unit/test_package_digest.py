"""REG-02 (RFC-015; M14-FR-03, M14-RT-01, K7): a changed installed package is refused at load."""

from __future__ import annotations

from pathlib import Path

import pytest

from s00_t03_support import build


QUERY = "weekly order volume forecast for the north region"


def _ids(turn, query=QUERY):
    return [item["capability_id"] for item in turn.search(turn.context, query).data["candidates"]]


def test_reg_02(tmp_path: Path) -> None:
    harness = build(tmp_path)
    harness.install("forecast-lime")
    harness.install("calendar-read")
    assert _ids(harness.turn()) == ["fixtures.forecast-lime"]
    stored = harness.store.package_dir("fixtures.forecast-lime", "1.0.0") / "capability.scs.json"
    data = bytearray(stored.read_bytes())
    data[-2] = data[-2] ^ 0x01  # one byte inside the stored package copy
    stored.write_bytes(bytes(data))
    restarted = harness.restart()
    turn = restarted.turn()
    assert _ids(turn) == []
    events = [event for event in restarted.store.audit_events() if event["event"] == "registry.digest_mismatch"]
    assert events and events[-1]["capability_id"] == "fixtures.forecast-lime"
    assert events[-1]["reason"] == "DIGEST_MISMATCH"
    described = turn.describe(turn.context, "fixtures.forecast-lime")
    assert (described.status, described.reason) == ("UNAVAILABLE", "DIGEST_MISMATCH")
    # Negative: the unmodified package still loads.
    assert _ids(turn, "find my next appointment in the calendar") == ["fixtures.calendar-read"]


def test_reg_02_fault_interrupted_install_is_not_loadable(tmp_path: Path) -> None:
    harness = build(tmp_path)

    def crash(point: str) -> None:
        if point == "registry.before_rename":
            raise RuntimeError("injected crash: " + point)

    harness.store.hook = crash
    with pytest.raises(RuntimeError):
        harness.install("forecast-lime")
    restarted = harness.restart()
    assert restarted.registry.records(restarted.operator) == []
    assert _ids(restarted.turn()) == []
    assert not list((restarted.store.root).glob("**/.tmp-*"))
    # A clean retry after the crash installs normally.
    assert restarted.install("forecast-lime")["data"]["lifecycle"] == "ENABLED"
    assert _ids(restarted.turn()) == ["fixtures.forecast-lime"]
