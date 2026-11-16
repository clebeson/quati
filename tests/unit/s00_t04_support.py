"""Deterministic S00-T04 setup (M17, M31, M26 contribution).

``ScriptedFakeProvider`` is a SCRIPTED FAKE model used only by tests. It is a ``Provider``
subclass so the real base-class budgets, validation and probe logic run, but it makes no
network or subprocess call and is never proof of a real provider. It is never imported by
product code; the in-process CLI tests register it under a test-only transport name for
the duration of one test and unregister it afterwards.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quati.adapters.evidence import write_receipt
from quati.adapters.feature_reports import FileFeatureReportStore
from quati.adapters.fixture_capabilities import FIXTURE_HANDLERS, FixtureHandlerRegistry
from quati.adapters.local_identity import LocalIdentity
from quati.application.cli_service import CLIService
from quati.application.ports import ProviderConfig
from quati.application.providers import (
    PROBE_TOOL, ModelResponse, Provider, ProviderError, ToolCall, Usage)
from quati.cli import composition, local_policy

FAKE_TRANSPORT = "scripted_fake_t04"
START = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
NONCE = re.compile(r"[0-9a-f]{32}")
# Fix round 5 (S4): probes name their target tool and field; the trivial profile keeps quati_probe_echo/nonce.
TARGET = re.compile(r"Call the tool (\S+) with (\S+) set to ([0-9a-f]{32})")

WORK = {"intent": "context_lookup", "work_needed": True, "complexity": "short", "risk": "low",
        "uncertainty": "low", "safe_work_allowed": True, "next_action": "search_context",
        "reason_code": "LOOKUP_REQUEST", "commitment_ref": None, "confidence": 0.9}
SOCIAL = {"intent": "social", "work_needed": False, "complexity": "trivial", "risk": "none",
          "uncertainty": "low", "safe_work_allowed": False, "next_action": "respond",
          "reason_code": "SOCIAL_GREETING", "commitment_ref": None, "confidence": 0.95}
CALENDAR_QUERY = "Find my next appointment"
FORECAST_QUERY = "What will weekly order volume look like for the north region over the next four weeks?"


class FakeClock:
    def __init__(self, start: datetime = START) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


class SeededIds:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, prefix: str) -> str:
        self.count += 1
        return f"{prefix}-{self.count:05d}"


class Script:
    """Ordered scripted answers; probe requests are answered by the probe rules below."""

    def __init__(self, *items, probe_tools: str = "echo", probe_structured: bool = True,
                 probe_model_id: str = "fake-model-1") -> None:
        self.items = list(items)
        self.requests: list = []
        self.probe_tools = probe_tools
        self.probe_structured = probe_structured
        self.probe_model_id = probe_model_id
        self.before_call = None

    def add(self, *items) -> None:
        self.items.extend(items)

    def model_requests(self) -> list:
        return [request for request in self.requests if not _is_probe(request)]

    def answer(self, request):
        self.requests.append(request)
        if _is_probe(request):
            return self._probe(request)
        if self.before_call is not None:
            self.before_call(request)
        if not self.items:
            raise ProviderError("TEMPORARILY_UNAVAILABLE", "UPSTREAM_ERROR")
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item(request)
        return item

    def _probe(self, request):
        text = request.messages[0].content
        nonce = NONCE.findall(text)[-1] if NONCE.findall(text) else ""
        if request.tools:
            found = TARGET.search(text)
            target, field = (found.group(1), found.group(2)) if found else (PROBE_TOOL, "nonce")
            if self.probe_tools == "flaky":            # one transient miss, then a correct echo
                self.probe_tools = "echo"
                raise ProviderError("TEMPORARILY_UNAVAILABLE", "CLI_FAILED")
            if self.probe_tools == "echo":
                return ModelResponse(tool_calls=(ToolCall(target, {field: nonce}),), stop_reason="tool_call",
                                     model_id=self.probe_model_id)
            # Fix round 4 (G2) diagnostic modes; each is a distinct malformed or tolerated tool reply.
            calls = {"spaced": ((target, {field: f"  {nonce.upper()} "}),),
                     "name": (("quati_other_tool", {field: nonce}),),
                     "extra_key": ((target, {field: nonce, "note": "x"}),),
                     "second": ((target, {field: "0" * 32}), (target, {field: nonce}))}
            if self.probe_tools in calls:
                return ModelResponse(tool_calls=tuple(ToolCall(name, arguments)
                                                      for name, arguments in calls[self.probe_tools]),
                                     stop_reason="tool_call", model_id=self.probe_model_id)
            if self.probe_tools == "text":
                return ModelResponse(text="I would call the tool now.", model_id=self.probe_model_id)
            if self.probe_tools == "wrong":
                return ModelResponse(tool_calls=(ToolCall(target, {field: "0" * 32}),),
                                     stop_reason="tool_call", model_id=self.probe_model_id)
            raise ProviderError("TEMPORARILY_UNAVAILABLE", "UPSTREAM_ERROR")
        if request.output_schema is not None:
            if self.probe_structured:
                if "reason_code" in request.output_schema.get("properties", {}):   # the ask profile (S4)
                    return ModelResponse(structured=dict(SOCIAL, reason_code=nonce), model_id=self.probe_model_id)
                return ModelResponse(structured={"nonce": nonce}, model_id=self.probe_model_id)
            return ModelResponse(text="not json", model_id=self.probe_model_id)
        raise ProviderError("DEADLINE_EXCEEDED")


def _is_probe(request) -> bool:
    return "connectivity probe" in (request.system or "") or (
        request.timeout_s == 1 and not request.tools and request.output_schema is None
        and "history of timekeeping" in request.messages[0].content)


class ScriptedFakeProvider(Provider):
    """SCRIPTED FAKE provider: answers from a ``Script``; tests only; no network."""

    transport = FAKE_TRANSPORT
    default_model = "fake-model-1"
    needs_secret = False
    takes_endpoint = False
    needs_model = False
    supports_streaming = False
    active_script: Script | None = None

    def __init__(self, config, *, script: Script | None = None, **dependencies) -> None:
        super().__init__(config, **dependencies)
        self.script = script or type(self).active_script

    def _complete(self, request):
        return self.script.answer(request)


# ----------------------------------------------------------------- response builders
def classified(value: dict = WORK, **usage) -> ModelResponse:
    return ModelResponse(structured=dict(value), model_id="fake-model-1", usage=Usage(**usage))


def tool(name: str, model_id: str = "fake-model-1", **arguments) -> ModelResponse:
    return ModelResponse(tool_calls=(ToolCall(name, arguments),), stop_reason="tool_call", model_id=model_id)


def final(text: str = "Here is the answer.") -> ModelResponse:
    return ModelResponse(text=text, model_id="fake-model-1")


def search(query: str) -> ModelResponse:
    return tool("quati_search", query=query)


def describe(capability_id: str) -> ModelResponse:
    return tool("quati_describe", capability_id=capability_id)


def invoke(capability_id: str, **arguments) -> ModelResponse:
    return tool("quati_invoke", capability_id=capability_id, input=arguments)


def status_of(request) -> ModelResponse:
    """Call quati_status with the execution id found in the last tool result."""
    last = request.messages[-1].content
    found = re.search(r'"execution_id": "([^"]+)"', last)
    return tool("quati_status", execution_id=found.group(1) if found else "missing")


# ----------------------------------------------------------------- service harness
class Harness:
    def __init__(self, root: Path, monkeypatch, script: Script, *, clock: FakeClock | None = None,
                 config: ProviderConfig | None = None) -> None:
        monkeypatch.setenv("QUATI_DATA_DIR", str(root / "data"))
        monkeypatch.delenv("QUATI_ALLOW_LIVE", raising=False)
        # Test-only registration, undone by monkeypatch at the end of the test.
        from quati.application import providers
        providers.transports()
        monkeypatch.setitem(providers._REGISTRY, FAKE_TRANSPORT, ScriptedFakeProvider)
        self.root = root
        self.script = script
        self.clock = clock or FakeClock()
        self.ids = SeededIds()
        self.identity = LocalIdentity(root / "config")
        summary = self.identity.initialize()
        local_policy.install(self.identity.directory, summary["tenant_id"], summary["principal_id"])
        self.config = config or ProviderConfig(transport=FAKE_TRANSPORT, allow_live=True)
        self.handlers = FixtureHandlerRegistry(FIXTURE_HANDLERS)
        self.reports = FileFeatureReportStore(root / "data" / "feature_reports")
        self.providers: list = []
        self.service = self.build_service()

    def factory(self, config):
        provider = ScriptedFakeProvider(config, script=self.script, clock=lambda: self.clock().isoformat())
        self.providers.append(provider)
        return provider

    def runtime(self, context):
        return composition.ask_runtime(self.identity, context, clock=self.clock, ids=self.ids, handlers=self.handlers)

    def build_service(self) -> CLIService:
        identity = self.identity
        return CLIService(identity, self.config, write_receipt, provider_factory=self.factory,
                          policy_loader=lambda tenant_id: local_policy.state(identity.directory, tenant_id),
                          feature_reports=self.reports, ask_runtime=self.runtime, clock=self.clock)

    def commands(self):
        return composition.capability_commands(self.identity, write_receipt, clock=self.clock, ids=self.ids,
                                               handlers=self.handlers)

    def install(self, *names: str, enable: bool = True) -> None:
        commands = self.commands()
        for name in names:
            code, value = commands.install_fixture(name, enable_fixture=enable)
            assert value["status"] in ("SUCCEEDED", "DENIED"), value

    def probe(self):
        return self.service.probe()

    def ask(self, text: str, synthetic: bool = False):
        return self.service.ask(text, synthetic_evidence=True) if synthetic else self.service.ask(text)


def receipt_of(value: dict) -> dict:
    reference = value["evidence_refs"][0]
    _, digest, path = reference.split(":", 2)
    raw = Path(path).read_bytes()
    import hashlib
    assert hashlib.sha256(raw).hexdigest() == digest
    return json.loads(raw)


def receipt_bytes(value: dict) -> bytes:
    return Path(value["evidence_refs"][0].split(":", 2)[2]).read_bytes()


__all__ = ["CALENDAR_QUERY", "FAKE_TRANSPORT", "FORECAST_QUERY", "FakeClock", "Harness", "SOCIAL", "START",
           "Script", "ScriptedFakeProvider", "SeededIds", "WORK", "classified", "describe", "final", "invoke",
           "receipt_bytes", "receipt_of", "search", "status_of", "tool"]
