"""Shared synthetic fixtures for the S00-T02 tests (M14, M25, M30).

Fixture construction uses only the canonical example files and plain PyYAML on the
test side, so the code under test never builds its own oracle.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPOSITORY_ROOT / "examples"
CONTRACTS = REPOSITORY_ROOT / "contracts"

TENANT = "01JD0000000000000000000000"
OTHER_TENANT = "01JD0000000000000000000001"
ACTOR = "01JD00000000000000000000AA"
NOW = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)


def read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def base_package() -> dict:
    """Executive-secretary package with its statechart beside it."""
    package = read_yaml(EXAMPLES / "behavior" / "executive-secretary.yaml")
    package["statechart_ref"] = "statechart.yaml"
    return package


def base_machine() -> dict:
    return read_yaml(EXAMPLES / "statecharts" / "commitment.yaml")


def base_manifest() -> dict:
    return json.loads((EXAMPLES / "capabilities" / "example_analytic_research.json").read_text())


def base_policy() -> dict:
    return json.loads((EXAMPLES / "policies" / "local-default.policy.json").read_text())


def base_decision_policy() -> dict:
    return json.loads((EXAMPLES / "behavior" / "decision-policy.json").read_text())


def write_package(root: Path, package: dict | None = None, machine: dict | None = None,
                  package_name: str = "package.yaml") -> str:
    """Write a package and its statechart as YAML under ``root``; return the profile ref."""
    root.mkdir(parents=True, exist_ok=True)
    package = base_package() if package is None else package
    machine = base_machine() if machine is None else machine
    (root / package_name).write_text(yaml.safe_dump(package, sort_keys=False), encoding="utf-8")
    if isinstance(package.get("statechart_ref"), str) and package["statechart_ref"] == "statechart.yaml":
        (root / "statechart.yaml").write_text(yaml.safe_dump(machine, sort_keys=False), encoding="utf-8")
    return package_name


def mutate(document: dict, dotted: str, value) -> dict:
    """Return a deep copy with ``dotted`` (a.b.c) set to ``value``."""
    result = copy.deepcopy(document)
    target = result
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    return result


def transition_index(machine: dict, source: str, event: str) -> int:
    for index, transition in enumerate(machine["transitions"]):
        if transition["source"] == source and transition["event"] == event:
            return index
    raise AssertionError(f"missing transition {source}/{event}")


class CounterIds:
    """Deterministic identifier generator."""

    def __init__(self, prefix: str = "dec") -> None:
        self.prefix = prefix
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return f"{self.prefix}-{self.count:04d}"
