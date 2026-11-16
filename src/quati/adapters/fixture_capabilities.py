"""Public synthetic fixture capabilities for S00 discovery (CAP-01, CAP-02, CAP-03).

Only handlers registered in this module's source can execute. A binding names one by
``fixture:<name>``; a package or manifest can never add or load code. Handlers are
deterministic: fixed synthetic data and the injected clock. Every result is labelled
``FIXTURE_RESULT`` and is never evidence of a real provider integration.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

import jsonschema

from quati.adapters.private_fs import private_tree
from quati.domain.canonical import digest
from quati.domain.discovery import ScopeGrant

FIXTURE_NAMESPACE = "fixtures"
LABEL = "FIXTURE_RESULT"
LOCAL_READ_GRANTS = frozenset({"calendar.read", "mail.read", "forecast.read"})

ORDERS_DATASET = "fixture-dataset:orders-weekly/v1"
CALENDAR_DATASET = "fixture-dataset:calendar-personal/v1"
MAILBOX_DATASET = "fixture-dataset:mailbox-personal/v1"
ORDER_HISTORY = {"north": (120, 132, 128, 141, 150, 147, 158, 163), "south": (80, 78, 85, 83, 90, 88, 92, 95)}
CALENDAR = (
    ("Dentist appointment", "2026-11-16T09:00:00Z", "2026-11-16T09:45:00Z", "Clinic, room 2"),
    ("Quarterly planning meeting", "2026-11-17T14:00:00Z", "2026-11-17T15:00:00Z", "Room Atlas"),
    ("Lunch with the design team", "2026-11-18T12:30:00Z", "2026-11-18T13:30:00Z", "Cafeteria"),
    ("Project review", "2026-11-20T10:00:00Z", "2026-11-20T11:00:00Z", "Video call"),
    ("Physiotherapy appointment", "2026-11-23T08:00:00Z", "2026-11-23T08:45:00Z", "Health centre"),
)
MAILBOX = (
    ("clinic@example.test", "Appointment reminder: dentist on 16 November", "2026-11-10",
     "This is a reminder of your dentist appointment."),
    ("finance@example.test", "Invoice 2026-11 for the design work", "2026-11-12", "Please find the invoice attached."),
    ("ana@example.test", "Meeting notes: quarterly planning", "2026-11-13", "Notes from the planning meeting."),
)

_REGION = {"type": "string", "enum": ["north", "south"]}
_EVIDENCE = {"type": "array", "items": {"type": "string"}}
_LABEL = {"const": LABEL}


def _manifest(name: str, description: str, positive: list[str], negative: list[str], input_schema: dict,
              output_properties: dict, criteria: list[str], permissions: list[str], effects: str,
              verification: str, destinations: list[str] | None = None) -> dict:
    manifest = {
        "schema_version": "scs/1.1", "id": f"{FIXTURE_NAMESPACE}.{name}", "version": "1.0.0", "name": name,
        "description": description,
        "intents": {"positive_examples": positive, "negative_examples": negative},
        "input_schema": {"type": "object", "additionalProperties": False, **input_schema},
        "output_schema": {"type": "object", "additionalProperties": False,
                          "properties": {**output_properties, "evidence_refs": _EVIDENCE, "label": _LABEL},
                          "required": sorted([*output_properties, "evidence_refs", "label"])},
        "outcomes": {"criteria": criteria}, "permissions": permissions, "effects": effects,
        "requires_approval": effects in ("write", "dangerous"), "dependencies": [],
        "evaluation": ["tests/unit/test_s00_t03_discovery.py"], "data_class_ceiling": "PUBLIC",
        "outcome_verification": {"mode": verification},
    }
    if destinations:
        manifest["destinations"] = destinations
    return manifest


_FORECAST_WEEK = {"type": "object", "additionalProperties": False, "required": ["week", "point", "low", "high"],
                  "properties": {"week": {"type": "integer"}, "point": {"type": "integer"},
                                 "low": {"type": "integer"}, "high": {"type": "integer"}}}
_APPOINTMENT = {"type": "object", "additionalProperties": False, "required": ["title", "start", "end", "location"],
                "properties": {key: {"type": "string"} for key in ("title", "start", "end", "location")}}
_MESSAGE = {"type": "object", "additionalProperties": False, "required": ["sender", "subject", "date"],
            "properties": {key: {"type": "string"} for key in ("sender", "subject", "date")}}

FIXTURE_MANIFESTS: dict[str, dict] = {
    "forecast-lime": _manifest(
        "forecast-lime",
        "Forecast the weekly order volume of a sales region for the coming one to four weeks from a fixed "
        "synthetic order history, with a point estimate and a ten percent band.",
        ["Forecast weekly order volume for the north region",
         "How many orders should the south region expect over the coming two weeks?"],
        ["Publish the forecast to the sales dashboard"],
        {"properties": {"region": _REGION, "horizon_weeks": {"type": "integer", "minimum": 1, "maximum": 4}},
         "required": ["horizon_weeks", "region"]},
        {"region": _REGION, "method": {"const": "least_squares_linear_trend"},
         "forecast": {"type": "array", "items": _FORECAST_WEEK}},
        ["One forecast row per requested week", "Every row cites the synthetic order history"],
        ["forecast.read"], "read", "evidence_check"),
    "forecast-quick": _manifest(
        "forecast-quick",
        "Quick rough estimate of the weekly order volume of a sales region, using only the last observed week "
        "of the synthetic order history.",
        ["Give me a rough order estimate for the north region", "Quick weekly order guess for the south region"],
        ["Forecast four weeks with a confidence band"],
        {"properties": {"region": _REGION}, "required": ["region"]},
        {"region": _REGION, "estimate": {"type": "integer"}},
        ["The estimate equals the last observed week"], ["forecast.read"], "read", "evidence_check"),
    "forecast-publish": _manifest(
        "forecast-publish",
        "Publish a weekly order volume forecast for a sales region to the synthetic sales dashboard, replacing "
        "the previously published figure.",
        ["Publish the north region forecast to the dashboard", "Update the dashboard with the new forecast"],
        ["Show me the forecast"],
        {"properties": {"region": _REGION, "point": {"type": "integer"}}, "required": ["point", "region"]},
        {"published": {"type": "boolean"}},
        ["The dashboard shows the published figure"], ["forecast.write"], "write", "read_after_write",
        ["dashboard:sales"]),
    "calendar-read": _manifest(
        "calendar-read",
        "List the next upcoming appointments and meetings in the synthetic personal calendar that start after "
        "the current time, with title, start, end and location. Read only.",
        ["Find my next appointment", "What meetings do I have this week?"],
        ["Create a meeting with Ana on Friday"],
        {"properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 5}}},
        {"appointments": {"type": "array", "items": _APPOINTMENT}},
        ["Only appointments that start after the current time", "Ordered by start time"],
        ["calendar.read"], "read", "evidence_check"),
    "calendar-write": _manifest(
        "calendar-write",
        "Create a new appointment in the synthetic personal calendar with a title, a start time and an end "
        "time.",
        ["Book an appointment with the dentist on Monday", "Create a meeting tomorrow at nine"],
        ["When is my next appointment?"],
        {"properties": {"title": {"type": "string", "minLength": 1, "maxLength": 120},
                        "start": {"type": "string", "format": "date-time"},
                        "end": {"type": "string", "format": "date-time"}},
         "required": ["end", "start", "title"]},
        {"created": {"type": "boolean"}, "event_id": {"type": "string"}},
        ["The calendar contains the created appointment"], ["calendar.write"], "write", "read_after_write",
        ["calendar:personal"]),
    "mail-search": _manifest(
        "mail-search",
        "Search the synthetic mailbox for email messages whose subject or body matches a text query, and return "
        "sender, subject and date.",
        ["Search my email for the invoice", "Look for messages from Ana"],
        ["Send an email to Ana"],
        {"properties": {"query": {"type": "string", "minLength": 1, "maxLength": 200},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10}},
         "required": ["query"]},
        {"messages": {"type": "array", "items": _MESSAGE}},
        ["Every returned message matches the query"], ["mail.read"], "read", "evidence_check"),
}
FIXTURE_NAMES = tuple(FIXTURE_MANIFESTS)
_FIXTURE_BY_ID = {manifest["id"]: manifest for manifest in FIXTURE_MANIFESTS.values()}


def fixture_manifest(name: str) -> dict:
    return copy.deepcopy(FIXTURE_MANIFESTS[name])


# ---------------------------------------------------------------------------- handlers

def _round(value: float) -> int:
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)


def forecast_lime(arguments: Mapping[str, Any], *, now: datetime) -> dict:
    history = ORDER_HISTORY[arguments["region"]]
    count = len(history)
    mean_x = (count - 1) / 2
    mean_y = sum(history) / count
    slope = (sum((x - mean_x) * (y - mean_y) for x, y in enumerate(history))
             / sum((x - mean_x) ** 2 for x in range(count)))
    rows = []
    for week in range(1, arguments["horizon_weeks"] + 1):
        point = _round(mean_y + slope * (count - 1 + week - mean_x))
        rows.append({"week": week, "point": point, "low": _round(point * 0.9), "high": _round(point * 1.1)})
    return {"region": arguments["region"], "method": "least_squares_linear_trend", "forecast": rows,
            "evidence_refs": [ORDERS_DATASET], "label": LABEL}


def forecast_quick(arguments: Mapping[str, Any], *, now: datetime) -> dict:
    return {"region": arguments["region"], "estimate": ORDER_HISTORY[arguments["region"]][-1],
            "evidence_refs": [ORDERS_DATASET], "label": LABEL}


def forecast_publish(arguments: Mapping[str, Any], *, now: datetime) -> dict:
    return {"published": False, "evidence_refs": [], "label": LABEL}       # never a real side effect


def calendar_read(arguments: Mapping[str, Any], *, now: datetime) -> dict:
    current = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    upcoming = [event for event in CALENDAR if event[1] > current][: arguments.get("limit", 1)]
    return {"appointments": [dict(zip(("title", "start", "end", "location"), event)) for event in upcoming],
            "evidence_refs": [CALENDAR_DATASET], "label": LABEL}


def calendar_write(arguments: Mapping[str, Any], *, now: datetime) -> dict:
    return {"created": False, "event_id": "fixture-not-created", "evidence_refs": [], "label": LABEL}


def mail_search(arguments: Mapping[str, Any], *, now: datetime) -> dict:
    terms = [term for term in arguments["query"].lower().split() if term]
    found = [message for message in MAILBOX
             if any(term in (message[1] + " " + message[3]).lower() for term in terms)]
    return {"messages": [dict(zip(("sender", "subject", "date"), message[:3]))
                         for message in found[: arguments.get("limit", 5)]],
            "evidence_refs": [MAILBOX_DATASET], "label": LABEL}


@dataclass(frozen=True)
class FixtureHandler:
    """In-source fixture handler with a TRUSTED identity (audit P1-1/P1-2).

    ``default_capability_id`` is the only capability id this handler may be bound to;
    ``effect_class`` and ``required_permissions`` are its trusted floor: a bound manifest must
    declare at least this effect and at least these permissions. When omitted, the floor is
    taken from the in-source fixture manifest of ``default_capability_id``; an unknown id
    gets the fail-closed floor ``dangerous``.
    """

    name: str
    default_capability_id: str
    function: Callable[..., dict]
    self_test_input: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    effect_class: str | None = None
    required_permissions: tuple[str, ...] | None = None

    @property
    def trusted_capability_id(self) -> str:
        return self.default_capability_id

    @property
    def trusted_effect(self) -> str:
        if self.effect_class is not None:
            return self.effect_class
        source = _FIXTURE_BY_ID.get(self.default_capability_id)
        return source["effects"] if source is not None else "dangerous"

    @property
    def trusted_permissions(self) -> tuple[str, ...]:
        if self.required_permissions is not None:
            return tuple(self.required_permissions)
        source = _FIXTURE_BY_ID.get(self.default_capability_id)
        return tuple(source["permissions"]) if source is not None else ()


FIXTURE_HANDLERS: dict[str, FixtureHandler] = {
    "forecast-lime": FixtureHandler("forecast-lime", "fixtures.forecast-lime", forecast_lime,
                                    {"region": "north", "horizon_weeks": 1}, (ORDERS_DATASET,)),
    "forecast-quick": FixtureHandler("forecast-quick", "fixtures.forecast-quick", forecast_quick,
                                     {"region": "north"}, (ORDERS_DATASET,)),
    "forecast-publish": FixtureHandler("forecast-publish", "fixtures.forecast-publish", forecast_publish,
                                       {"region": "north", "point": 1}, ()),
    "calendar-read": FixtureHandler("calendar-read", "fixtures.calendar-read", calendar_read, {"limit": 1},
                                    (CALENDAR_DATASET,)),
    "calendar-write": FixtureHandler("calendar-write", "fixtures.calendar-write", calendar_write,
                                     {"title": "Self-test", "start": "2026-01-01T09:00:00Z",
                                      "end": "2026-01-01T10:00:00Z"}, ()),
    "mail-search": FixtureHandler("mail-search", "fixtures.mail-search", mail_search,
                                  {"query": "invoice", "limit": 1}, (MAILBOX_DATASET,)),
}


def _valid(instance: Any, schema: Mapping[str, Any]) -> bool:
    try:
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(instance)
    except Exception:  # noqa: BLE001 - any validator failure is a mismatch
        return False
    return True


class FixtureHandlerRegistry:
    """The only code a binding can reach. Counts real invocations, not self-tests."""

    def __init__(self, handlers: Mapping[str, FixtureHandler]) -> None:
        self._handlers = dict(handlers)
        self._calls: dict[str, int] = {}

    def resolve(self, name: str) -> FixtureHandler | None:
        return self._handlers.get(name)

    def self_test(self, name: str, manifest: Mapping[str, Any], *, now: datetime) -> str | None:
        """Run the handler on its fixed input against the bound manifest contract (C2 evidence digest)."""
        handler = self._handlers[name]
        if not _valid(dict(handler.self_test_input), manifest["input_schema"]):
            return None
        try:
            output = handler.function(dict(handler.self_test_input), now=now)
        except Exception:  # noqa: BLE001 - a failing fixture is not bindable
            return None
        if not _valid(output, manifest["output_schema"]):
            return None
        return digest({"handler": name, "capability_id": manifest["id"], "input": dict(handler.self_test_input),
                       "output": output})

    def execute(self, name: str, arguments: Mapping[str, Any], *, now: datetime) -> dict:
        self._calls[name] = self._calls.get(name, 0) + 1
        return self._handlers[name].function(dict(arguments), now=now)

    def invocations(self) -> dict[str, int]:
        return dict(sorted(self._calls.items()))

    def total_invocations(self) -> int:
        return sum(self._calls.values())


class StaticGrants:
    """Local single-user grants: the permission set comes from trusted configuration."""

    def __init__(self, permissions: frozenset[str]) -> None:
        self.permissions = frozenset(permissions)

    def resolve(self, context) -> ScopeGrant:
        return ScopeGrant(self.permissions, space_id=context.space_ids[0])


def write_package(root: Path, manifest: Mapping[str, Any], extra_files: Mapping[str, str] | None = None) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "capability.scs.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    for relative, text in (extra_files or {}).items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text)
    return root


def write_fixture_package(sources_dir: Path, name: str) -> Path:
    """Write one built-in fixture package below ``sources_dir`` and make the written tree owner-only
    (directories 0700, files 0600, whatever the umask), like every other path under the data directory.
    A symlink, special file, extra hard link or foreign owner inside it raises ``UnsafeStatePath``."""
    return private_tree(write_package(Path(sources_dir) / name, FIXTURE_MANIFESTS[name]))


def install_fixture(registry, context, name: str, sources_dir: Path, *, enable_fixture: bool = True,
                    fixture_handler: str | None = "default") -> dict:
    handler = name if fixture_handler == "default" else fixture_handler
    return registry.install(context, write_fixture_package(sources_dir, name), source=f"fixture:{name}",
                            fixture_handler=handler, enable_fixture=enable_fixture, import_kind="fixture")


__all__ = ["FIXTURE_HANDLERS", "FIXTURE_MANIFESTS", "FIXTURE_NAMES", "FixtureHandler", "FixtureHandlerRegistry",
           "LABEL", "LOCAL_READ_GRANTS", "StaticGrants", "fixture_manifest", "install_fixture",
           "write_fixture_package", "write_package"]
