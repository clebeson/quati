"""L1 adapter-loop tests; FunctionModel is never live-provider evidence.

Requirements: M17-AT-01/02, M17-RT-01/02, M15-RT-02, M26-AT-02.
"""
from __future__ import annotations

import json

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from secma.application.ports import ProviderConfig, ProviderError
from secma.adapters.model import ModelAdapter


CLASSIFICATION = {
    "intent": "professional_work", "work_needed": True, "complexity": "short",
    "risk": "low", "uncertainty": "low", "safe_work_allowed": True,
    "next_action": "start_safe_work", "reason_code": "fixture_read",
}


def config(**changes):
    return ProviderConfig(**({"base_url": "https://example.invalid/v1", "model": "fixture-model",
                             "api_key_env": "SECMA_TEST_TOKEN", "allow_live": False} | changes))


class Catalog:
    def __init__(self):
        self.calls = []

    def search(self, query):
        self.calls.append("search")
        return [{"id": "fixture.timeline", "description": "Read synthetic incident timeline"}]

    def describe(self, capability_id):
        self.calls.append("describe")
        return {"id": capability_id, "input_schema": {"type": "object"}}

    def invoke(self, capability_id, arguments):
        self.calls.append("invoke")
        return {"status": "FIXTURE_RESULT", "summary": "Synthetic fixture result"}


def probe_response(messages, info):
    returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
    if returns:
        return ModelResponse(parts=[TextPart(str(returns[-1].content))])
    text = " ".join(str(getattr(p, "content", "")) for m in messages for p in m.parts)
    nonce = text.split("NONCE=", 1)[1].split()[0]
    return ModelResponse(parts=[ToolCallPart("probe_echo", {"nonce": nonce})])


def routed_model(messages, info):
    tools = [tool.name for tool in info.function_tools]
    if "probe_echo" in tools:
        return probe_response(messages, info)
    if info.output_tools:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, CLASSIFICATION)])
    returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
    if not returns:
        return ModelResponse(parts=[ToolCallPart("search", {"query": "incident timeline"})])
    if returns[-1].tool_name == "search":
        return ModelResponse(parts=[ToolCallPart("describe", {"capability_id": "fixture.timeline"})])
    if returns[-1].tool_name == "describe":
        return ModelResponse(parts=[ToolCallPart("invoke", {"capability_id": "fixture.timeline", "arguments": {}})])
    return ModelResponse(parts=[TextPart("Synthetic fixture result")])


def test_m17_m15_loop_records_real_sdk_calls_but_not_live_proof():
    catalog = Catalog()
    result = ModelAdapter(config(), model=FunctionModel(routed_model)).run("Find the incident timeline", "Trusted test policy.", catalog)
    assert catalog.calls == ["search", "describe", "invoke"]
    assert [call["tool_name"] for call in result.calls] == ["search", "describe", "invoke"]
    assert result.classification["intent"] == "professional_work"
    assert result.provider_used is False
    assert result.probe["features"]["tools"] == "SUPPORTED"
    assert result.probe["provenance"] == "INJECTED_TEST_MODEL"
    assert result.usage["cost_usd"] is None


def test_m17_failed_probe_prevents_catalog_use():
    catalog = Catalog()
    model = FunctionModel(lambda messages, info: ModelResponse(parts=[TextPart("No tools available")]))
    with pytest.raises(ProviderError) as error:
        ModelAdapter(config(), model=model).run("Research", "Trusted test policy.", catalog)
    assert error.value.code == "PROBE_FAILED"
    assert catalog.calls == []


def test_m17_bad_classification_has_bounded_repairs():
    calls = 0

    def invalid(messages, info):
        nonlocal calls
        if any(tool.name == "probe_echo" for tool in info.function_tools):
            return probe_response(messages, info)
        calls += 1
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"intent": "invented"})])

    catalog = Catalog()
    with pytest.raises(ProviderError) as error:
        ModelAdapter(config(), model=FunctionModel(invalid)).run("Research", "Policy.", catalog)
    assert error.value.code == "CLASSIFICATION_FAILED"
    assert calls <= 2
    assert catalog.calls == []


def test_m17_high_risk_request_does_not_get_catalog_tools():
    def risky(messages, info):
        if any(tool.name == "probe_echo" for tool in info.function_tools):
            return probe_response(messages, info)
        assert info.output_tools
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, CLASSIFICATION | {"risk": "high", "next_action": "escalate"})])

    catalog = Catalog()
    result = ModelAdapter(config(), model=FunctionModel(risky)).run("Delete all data", "Policy.", catalog)
    assert catalog.calls == []
    assert result.calls == []
    assert result.classification["next_action"] == "escalate"


def test_m17_missing_authorization_is_blocked_before_transport(monkeypatch):
    monkeypatch.setenv("SECMA_TEST_TOKEN", "never-print-this-secret")
    with pytest.raises(ProviderError) as error:
        ModelAdapter(config()).probe()
    assert error.value.code == "NOT_AUTHORIZED"
    assert "never-print" not in str(error.value)


@pytest.mark.parametrize("url", ["http://example.invalid/v1", "https://u:p@example.invalid/v1", "https://example.invalid/v1?secret=x", "https://example.invalid/v1#fragment"])
def test_m17_invalid_endpoints_fail_closed(url):
    with pytest.raises(ProviderError) as error:
        ModelAdapter(config(base_url=url), model=FunctionModel(routed_model)).probe()
    assert error.value.code == "INVALID_ENDPOINT"
    assert url not in str(error.value)


def test_m26_provider_exception_is_sanitized():
    def fails(messages, info):
        raise RuntimeError("Authorization: Bearer never-print-this-secret")

    with pytest.raises(ProviderError) as error:
        ModelAdapter(config(), model=FunctionModel(fails)).probe()
    assert "never-print" not in str(error.value)
    assert "Authorization" not in str(error.value)
    assert error.value.code == "PROVIDER_FAILED"


def test_m17_shared_request_budget_stops_loop_without_outcome():
    catalog = Catalog()
    with pytest.raises(ProviderError) as error:
        ModelAdapter(config(max_requests=3), model=FunctionModel(routed_model)).run("Find timeline", "Policy.", catalog)
    assert error.value.code == "LIMIT_EXCEEDED"
    assert catalog.calls == []


def test_m17_transport_retries_redirects_and_environment_proxies_are_disabled(monkeypatch):
    import asyncio
    import secma.adapters.model as module

    monkeypatch.setenv("SECMA_TEST_TOKEN", "synthetic-test-token")
    seen = {}
    real_client = module.AsyncOpenAI

    def capture_client(**kwargs):
        seen.update(kwargs)
        return real_client(**kwargs)

    monkeypatch.setattr(module, "AsyncOpenAI", capture_client)

    async def inspect_configured_model():
        adapter = ModelAdapter(config(allow_live=True))
        async with adapter._model():
            assert seen["base_url"] == "https://example.invalid/v1"
            assert seen["max_retries"] == 0
            assert seen["http_client"].follow_redirects is False
            assert seen["http_client"].trust_env is False

    # Construction and closing only: no request is sent or provider proof claimed.
    asyncio.run(inspect_configured_model())


def test_m17_unconfigured_provider_reports_missing_configuration():
    with pytest.raises(ProviderError) as error:
        ModelAdapter(ProviderConfig()).probe()
    assert error.value.code == "NOT_CONFIGURED"
