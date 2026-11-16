"""S00-T04 fix round 5, from live gate4 codex_cli gpt-6-luna (LOG-0032).

OpenAI strict structured outputs rejected the classification schema (``invalid_json_schema``,
400: every property must be required), the failure surfaced as TEMPORARILY_UNAVAILABLE
CLI_FAILED, and the probe passed only because it measured a trivial schema.

S1 strict_schema transform, S2 codex_cli (and openai_compatible) send it and normalize nulls,
S3 typed ``turn.failed`` mapping, S4 the probe measures the real ask schemas.
Proof tier L1: scripted child-process runner, scripted HTTP wire or SCRIPTED FAKE model; no network.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import jsonschema
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import CALENDAR_QUERY, Harness, Script  # noqa: E402
from test_provider_adapters import Runner, Wire, completion, make, make_cli, reply  # noqa: E402
from quati.adapters.evidence import write_receipt  # noqa: E402
from quati.adapters.providers._sdk import drop_optional_nulls, strict_schema  # noqa: E402
from quati.adapters.providers.cli import CodexCliProvider, envelope_schema  # noqa: E402
from quati.adapters.providers.openai_compatible import OpenAICompatibleProvider  # noqa: E402
from quati.application.ask import CLASSIFY_TOOL_NAME, ask_probe_profile, classification_schema  # noqa: E402
from quati.application.discovery_tools import DISCOVERY_TOOLS  # noqa: E402
from quati.application.providers import Message, ModelRequest, ProviderError, ToolSpec  # noqa: E402

USER = (Message("user", "hello"),)
ROOT = Path(__file__).resolve().parents[2]


def assert_strict(schema, where="$"):
    """OpenAI strict rules: every object lists all properties in required and forbids other keys."""
    assert isinstance(schema, dict), where
    types = schema.get("type")
    is_object = types == "object" or (isinstance(types, list) and "object" in types) or "properties" in schema
    if is_object:
        assert schema.get("additionalProperties") is False, where
        assert isinstance(schema.get("properties"), dict), where
        assert sorted(schema.get("required", [])) == sorted(schema["properties"]), where
        for name, child in schema["properties"].items():
            assert_strict(child, f"{where}.{name}")
    if isinstance(schema.get("items"), dict):
        assert_strict(schema["items"], f"{where}[]")
    for keyword in ("anyOf", "oneOf", "allOf"):
        for index, branch in enumerate(schema.get(keyword, ())):
            assert_strict(branch, f"{where}.{keyword}[{index}]")


def ask_sent_contracts():
    """Every contracts/*.schema.json the ask sends to a model (as output schema or tool input schema)."""
    # The ask sends exactly one contract: the classification (native output schema, or the
    # quati_classify tool input). classification_schema() is that file minus its annotations.
    path = ROOT / "contracts" / "request-classification.schema.json"
    assert path.is_file()
    return {path.name: classification_schema()}


# --------------------------------------------------------------- S1 strict_schema
@pytest.mark.parametrize("name", sorted(ask_sent_contracts()))
def test_s1_every_contract_schema_the_ask_sends_becomes_strict(name):
    original = ask_sent_contracts()[name]
    before = copy.deepcopy(original)
    strict, optional = strict_schema(original)
    assert_strict(strict)
    assert original == before                                            # pure: the input is not mutated
    assert optional == frozenset({("commitment_ref",), ("confidence",)})
    assert strict["properties"]["intent"]["enum"] == original["properties"]["intent"]["enum"]
    assert strict["properties"]["confidence"] == {"type": ["number", "null"], "minimum": 0, "maximum": 1}
    assert strict["properties"]["commitment_ref"] == {"type": ["string", "null"]}
    assert strict["properties"]["reason_code"] == {"type": "string", "minLength": 3}


@pytest.mark.parametrize("tool", [tool for tool in DISCOVERY_TOOLS if tool.name != "quati_invoke"],
                         ids=lambda tool: tool.name)
def test_s1_discovery_tool_input_schemas_become_strict(tool):
    strict, optional = strict_schema(tool.input_schema)
    assert_strict(strict)
    if tool.name == "quati_search":
        assert optional == frozenset({("limit",)})
        assert strict["properties"]["limit"] == {"type": ["integer", "null"], "minimum": 1, "maximum": 50}


def test_s1_a_free_form_object_cannot_be_made_strict_and_is_refused_not_narrowed():
    invoke = next(tool for tool in DISCOVERY_TOOLS if tool.name == "quati_invoke")
    for schema in (invoke.input_schema, {"type": "object"},
                   {"type": "object", "properties": {"a": {"type": "string"}}, "additionalProperties": {}}):
        with pytest.raises(ProviderError) as caught:
            strict_schema(schema)
        assert (caught.value.code, caught.value.reason) == ("UNSUPPORTED", "SCHEMA_NOT_STRICT")


def test_s1_envelopes_and_the_classify_tool_are_strict():
    classify = ToolSpec(CLASSIFY_TOOL_NAME, "Record the request classification.", classification_schema())
    for tools in (DISCOVERY_TOOLS, (classify,)):
        for require in (True, False):
            strict, optional = strict_schema(envelope_schema(ModelRequest(USER, tools=tools, require_tool=require)))
            assert_strict(strict)
            assert optional == frozenset()
    assert_strict(strict_schema(classify.input_schema)[0])


NESTED = {"type": "object", "required": ["a", "r", "f"], "properties": {
    "a": {"type": "string", "minLength": 2},
    "r": {"type": ["string", "null"]},
    "b": {"type": "integer", "minimum": 1},
    "c": {"enum": ["x", "y"]},
    "k": {"const": "fixed"},
    "d": {"type": "object", "properties": {"e": {"type": "string", "pattern": "^q"}}},
    "f": {"type": "array", "items": {"type": "object", "required": ["g"], "properties": {
        "g": {"const": "k"}, "h": {"anyOf": [{"type": "string"}, {"type": "integer"}]}}}},
    "n": {"type": ["string", "null"]}}}


def test_s1_nested_table_optional_paths_nullability_and_constraints():
    strict, optional = strict_schema(NESTED)
    assert_strict(strict)
    assert optional == frozenset({("b",), ("c",), ("k",), ("d",), ("d", "e"), ("f", "[]", "h"), ("n",)})
    p = strict["properties"]
    assert p["a"] == {"type": "string", "minLength": 2} and p["r"] == {"type": ["string", "null"]}
    assert p["b"] == {"type": ["integer", "null"], "minimum": 1}
    assert p["c"] == {"enum": ["x", "y", None]}
    assert p["k"] == {"anyOf": [{"const": "fixed"}, {"type": "null"}]}
    assert p["d"]["type"] == ["object", "null"] and p["d"]["properties"]["e"] == {"type": ["string", "null"],
                                                                                 "pattern": "^q"}
    assert p["f"]["items"]["properties"]["h"] == {"anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "null"}]}
    assert p["n"] == {"type": ["string", "null"]}                         # already nullable: no duplicate


# --------------------------------------------------------------- S2 null normalization round trip
@pytest.mark.parametrize("instance", [
    {"a": "hi", "r": None, "f": [{"g": "k"}]},
    {"a": "hi", "r": "v", "b": 3, "c": "y", "k": "fixed", "d": {"e": "qq"}, "f": [{"g": "k", "h": 2}], "n": "s"},
    {"a": "hi", "r": None, "d": {}, "f": [{"g": "k", "h": "t"}, {"g": "k"}]},
])
def test_s2_null_normalization_round_trips(instance):
    strict, optional = strict_schema(NESTED)
    filled = copy.deepcopy(instance)
    for key in ("b", "c", "k", "d", "n"):
        filled.setdefault(key, None)
    if isinstance(filled["d"], dict):
        filled["d"].setdefault("e", None)
    for item in filled["f"]:
        item.setdefault("h", None)
    jsonschema.validate(filled, strict)
    normalized = drop_optional_nulls(filled, optional)
    expected = copy.deepcopy(instance)
    assert normalized == expected
    jsonschema.validate(normalized, NESTED)
    assert drop_optional_nulls(None, optional) is None and drop_optional_nulls("x", optional) == "x"


class SchemaRunner(Runner):
    """Captures the --output-schema file the child would read (it lives only for the call)."""

    def __call__(self, argv, stdin_text, timeout_s, cwd, env):
        if "--output-schema" in argv:
            self.schemas = [*getattr(self, "schemas", []),
                            json.loads(Path(argv[argv.index("--output-schema") + 1]).read_text(encoding="utf-8"))]
        return super().__call__(argv, stdin_text, timeout_s, cwd, env)


CLASSIFIED = {"intent": "social", "work_needed": False, "complexity": "trivial", "risk": "none",
              "uncertainty": "low", "safe_work_allowed": False, "next_action": "respond",
              "reason_code": "SOCIAL_GREETING"}


def test_s2_codex_sends_the_strict_classification_schema_and_normalizes_optional_nulls():
    output = dict(CLASSIFIED, commitment_ref=None, confidence=None)
    runner = SchemaRunner((0, ""), (0, ""), write=[json.dumps(output), json.dumps(dict(output, confidence=0.5))])
    provider = make_cli(CodexCliProvider, runner, model="gpt-test")
    answer = provider.complete(ModelRequest(USER, output_schema=classification_schema()))
    assert runner.schemas[0] == strict_schema(classification_schema())[0]
    assert_strict(runner.schemas[0])
    assert answer.structured == CLASSIFIED
    assert provider.complete(ModelRequest(USER, output_schema=classification_schema())).structured == dict(
        CLASSIFIED, confidence=0.5)


def test_s2_codex_tool_envelope_schema_is_strict():
    envelope = {"kind": "tool_call", "tool_name": "quati_search", "arguments_json": '{"query": "calendar"}', "text": ""}
    runner = SchemaRunner((0, ""), write=[json.dumps(envelope)])
    provider = make_cli(CodexCliProvider, runner, model="gpt-test")
    answer = provider.complete(ModelRequest(USER, tools=DISCOVERY_TOOLS))
    assert answer.tool_calls[0].arguments == {"query": "calendar"}
    assert_strict(runner.schemas[0])


def test_s2_openai_compatible_strict_response_format_and_null_normalization():
    content = json.dumps(dict(CLASSIFIED, commitment_ref=None, confidence=None))
    wire = Wire(reply(completion({"content": content})))
    provider = make(OpenAICompatibleProvider, wire)
    answer = provider.complete(ModelRequest(USER, output_schema=classification_schema()))
    assert answer.structured == CLASSIFIED
    sent = wire.body()["response_format"]["json_schema"]
    assert sent["strict"] is True and sent["schema"] == strict_schema(classification_schema())[0]


# --------------------------------------------------------------- S3 typed turn.failed
UPSTREAM = ("Invalid schema for response_format 'codex_output_schema': 'schema.required' is required to include "
            "every key in properties. Missing 'commitment_ref'.")
LIVE_LINES = "\n".join([
    json.dumps({"type": "thread.started", "thread_id": "synthetic-thread"}),
    json.dumps({"type": "turn.started"}),
    json.dumps({"type": "turn.failed", "error": {"message": UPSTREAM, "code": "invalid_json_schema", "status": 400}}),
])


@pytest.mark.parametrize("returncode", [1, 0])
def test_s3_codex_turn_failed_schema_rejection_is_typed_without_upstream_text(returncode):
    runner = SchemaRunner((returncode, LIVE_LINES), write=[""])
    provider = make_cli(CodexCliProvider, runner, model="gpt-test")
    with pytest.raises(ProviderError) as caught:
        provider.complete(ModelRequest(USER, output_schema=classification_schema()))
    error = caught.value
    assert (error.code, error.reason) == ("UNSUPPORTED", "SCHEMA_REJECTED")
    for text in (str(error), error.message, repr(error.args)):
        assert "commitment_ref" not in text and "Invalid schema" not in text
    assert error.__cause__ is None and error.__context__ is None


@pytest.mark.parametrize(("event", "expected"), [
    ({"type": "error", "message": json.dumps({"error": {"code": "invalid_json_schema", "message": UPSTREAM}}),
      "status": 400}, ("UNSUPPORTED", "SCHEMA_REJECTED")),
    ({"type": "turn.failed", "error": {"message": "x", "status": 401}}, ("UNAUTHENTICATED", "UNAUTHENTICATED")),
    ({"type": "turn.failed", "error": {"message": "x", "status": 403}}, ("FORBIDDEN", "FORBIDDEN")),
    ({"type": "turn.failed", "error": {"message": "x", "status": 404}}, ("NOT_FOUND", "MODEL_NOT_FOUND")),
    ({"type": "turn.failed", "error": {"message": "x", "status": 429}}, ("TEMPORARILY_UNAVAILABLE", "RATE_LIMITED")),
    ({"type": "turn.failed", "error": {"message": "x", "status": 503}}, ("TEMPORARILY_UNAVAILABLE", "UPSTREAM_ERROR")),
    ({"type": "turn.failed", "error": {"message": "x", "status": 400}}, ("UNSUPPORTED", "REQUEST_REJECTED")),
    ({"type": "turn.failed", "error": {"message": "stream disconnected"}}, ("TEMPORARILY_UNAVAILABLE", "CLI_FAILED")),
    ({"type": "error", "message": "invalid_json_schema somewhere"}, ("UNSUPPORTED", "SCHEMA_REJECTED")),
    ({"type": "turn.failed", "status": 401, "error": {"message": json.dumps({"detail": "x"})}},
     ("UNAUTHENTICATED", "UNAUTHENTICATED")),                       # status on the event, body without error
    ({"type": "turn.failed", "error": {"status": 500}}, ("TEMPORARILY_UNAVAILABLE", "UPSTREAM_ERROR")),  # no message
    ({"type": "error", "message": json.dumps({"error": {"status": 408}})}, ("TEMPORARILY_UNAVAILABLE",
                                                                             "UPSTREAM_ERROR")),
])
def test_s3_codex_error_events_map_to_typed_errors(event, expected):
    runner = SchemaRunner((1, "noise\n" + json.dumps(event)), write=[""])
    provider = make_cli(CodexCliProvider, runner, model="gpt-test", max_retries_429=0)
    with pytest.raises(ProviderError) as caught:
        provider.complete(ModelRequest(USER))
    assert (caught.value.code, caught.value.reason) == expected


# --------------------------------------------------------------- S4 probe measures the ask schemas
def test_s4_probe_exercises_the_real_classification_schema_and_discovery_tools(tmp_path, monkeypatch):
    script = Script()
    harness = Harness(tmp_path, monkeypatch, script)
    code, probe = harness.probe()
    assert (code, probe["status"]) == (0, "SUCCEEDED")
    report = probe["data"]["feature_report"]
    profile = ask_probe_profile()
    assert report["probe_profile"] == {"name": "ask", "sha256": profile.sha256()}
    structured = [r for r in script.requests if r.output_schema is not None]
    tooled = [r for r in script.requests if r.tools]
    assert structured and all(r.output_schema == classification_schema() for r in structured)
    assert tooled and all(r.tools == DISCOVERY_TOOLS for r in tooled)
    assert report["features"]["tools"] == report["features"]["structured_output"] == "SUPPORTED"


def test_s4_a_trivial_schema_probe_never_opens_the_ask_gate(tmp_path, monkeypatch):
    script = Script()
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    report = harness.factory(harness.config).probe()                    # no profile: trivial schemas only
    assert report["probe_profile"] == {"name": "trivial", "sha256": None}
    assert report["features"]["tools"] == "SUPPORTED"
    harness.reports.save(report, write_receipt({"kind": "feature_report", **report}))
    before = len(script.requests)
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["data"]["feature_support"]) == (4, "UNAVAILABLE", "NOT_VERIFIED")
    assert "PROBE_PROFILE_MISMATCH" in value["uncertainties"] and len(script.requests) == before


def test_s1_boolean_subschemas_pass_through():
    strict, optional = strict_schema({"type": "object", "required": ["a"], "properties": {"a": True}})
    assert strict["properties"]["a"] is True and optional == frozenset()


def test_s2_openai_unparseable_structured_output_is_still_reported_by_the_base_class():
    wire = Wire(reply(completion({"content": "not json"})))
    provider = make(OpenAICompatibleProvider, wire)
    with pytest.raises(ProviderError) as caught:
        provider.complete(ModelRequest(USER, output_schema=classification_schema()))
    assert (caught.value.code, caught.value.reason) == ("OUTPUT_INVALID", "SCHEMA_INVALID_OUTPUT")
