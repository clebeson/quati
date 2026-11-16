"""M17 provider base class, registry, probe and command oracles with scripted providers only.

Nothing here contacts a model. A scripted provider proves Quati's own rules (configuration
order, budgets, retries, validation, classification); it is never proof of a real provider.
"""
import json

import pytest

from quati.application import providers
from quati.application.cli_service import CLIService
from quati.application.ports import ProviderConfig
from quati.application.providers import (FEATURES, Message, ModelRequest, ModelResponse, Provider, ProviderError,
                                         ToolCall, ToolSpec, Usage, create_provider, diagnostics_for,
                                         provider_class, register, require_features, transports, unregister)

ENV = {'SYNTHETIC_KEY': 'synthetic-never-log'}
NONCE_SCHEMA = {'type': 'object', 'properties': {'nonce': {'type': 'string'}}, 'required': ['nonce'],
                'additionalProperties': False}
ECHO = ToolSpec('echo', 'Echo.', NONCE_SCHEMA)


def config(**changes):
    values = dict(base_url='https://synthetic.invalid/v1', model='synthetic', api_key_env='SYNTHETIC_KEY',
                  allow_live=True, transport='scripted')
    values.update(changes)
    return ProviderConfig(**values)


class Scripted(Provider):
    """Returns queued outcomes; an exception instance in the queue is raised."""

    transport = 'scripted'

    def __init__(self, cfg=None, script=(), **dependencies):
        dependencies.setdefault('environ', ENV)
        self.slept = []
        dependencies.setdefault('sleep', self.slept.append)
        dependencies.setdefault('clock', lambda: '2026-01-01T00:00:00+00:00')
        super().__init__(cfg or config(), **dependencies)
        self.script = list(script)
        self.requests = []

    def _complete(self, request):
        self.requests.append(request)
        outcome = self.script.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def user(text='hello'):
    return (Message('user', text),)


def error_of(callable_, *args):
    with pytest.raises(ProviderError) as caught:
        callable_(*args)
    # M17: a ProviderError never carries the upstream exception as its cause or context.
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    return caught.value.code, caught.value.reason


# ----- M17-FR-01: configuration -------------------------------------------------------
def test_m17_fr_01_openai_compatible_config():
    environ = {'SYNTHETIC_KEY': 'synthetic-never-log'}
    good = create_provider(config(transport='openai_compatible'), environ=environ)
    assert good.config_issues() == []
    report = good.diagnostics()
    assert report['configured'] and report['endpoint_host'] == 'synthetic.invalid'
    assert report['transport'] == 'openai_compatible' and report['model'] == 'synthetic'
    assert set(report['features'].values()) == {'NOT_VERIFIED'}
    assert report['status'] == 'NOT_PROBED'
    assert 'synthetic-never-log' not in json.dumps(report)

    def reasons(**changes):
        env = changes.pop('environ', environ)
        return create_provider(config(transport='openai_compatible', **changes), environ=env).diagnostics()['reasons']

    assert reasons(base_url='') == ['ENDPOINT_INVALID']
    assert reasons(base_url='http://synthetic.invalid/v1') == ['ENDPOINT_INVALID']
    assert reasons(base_url='https://user:pw@synthetic.invalid') == ['ENDPOINT_INVALID']
    assert reasons(model='') == ['MODEL_MISSING']
    # A model id can never be read as a command-line option or carry shell or path tricks.
    for bad in ('--dangerously-skip-permissions', '-m', 'a b', 'a\nb', 'a;b', '$(id)', '.hidden', 'x' * 201, 'é'):
        assert reasons(model=bad) == ['MODEL_INVALID'], bad
    for good in ('sonnet[1m]', 'anthropic/claude-haiku-5-5', 'us.anthropic.claude-haiku-5-5-v1:0', 'gpt-x@2026',
                 'x' * 200, '7b'):
        assert reasons(model=good) == [], good
    assert reasons(api_key_env='BAD-NAME') == ['API_KEY_REF_INVALID']
    assert reasons(environ={}) == ['API_KEY_MISSING']
    assert reasons(allow_live=False) == ['LIVE_NOT_ALLOWED']
    # Every failing check is reported, in the normative order.
    assert reasons(base_url='', model='', environ={}, allow_live=False) == [
        'ENDPOINT_INVALID', 'MODEL_MISSING', 'API_KEY_MISSING', 'LIVE_NOT_ALLOWED']
    assert reasons(base_url='', model='-x', api_key_env='BAD-NAME', allow_live=False) == [
        'ENDPOINT_INVALID', 'MODEL_INVALID', 'API_KEY_REF_INVALID', 'LIVE_NOT_ALLOWED']
    failed = create_provider(config(transport='openai_compatible', allow_live=False), environ=environ).diagnostics()
    assert failed['status'] == 'NOT_CONFIGURED' and not failed['configured']
    assert error_of(create_provider(config(transport='openai_compatible', model='-x'), environ=environ)
                    .complete, ModelRequest(user())) == ('NOT_CONFIGURED', 'MODEL_INVALID')
    assert ProviderError('NOT_CONFIGURED', 'MODEL_INVALID').message == providers.MESSAGES['MODEL_INVALID']
    assert error_of(create_provider(config(transport='openai_compatible', allow_live=False), environ=environ)
                    .complete, ModelRequest(user())) == ('NOT_CONFIGURED', 'LIVE_NOT_ALLOWED')


def test_transport_defaults_and_unknown_transport():
    assert set(transports()) >= {'anthropic', 'openai', 'openai_compatible', 'claude_cli', 'codex_cli', 'gemini_cli'}
    anthropic = create_provider(ProviderConfig(api_key_env='SYNTHETIC_KEY', allow_live=True), environ=ENV)
    assert anthropic.config_issues() == []
    assert anthropic.diagnostics()['model'] == 'claude-haiku-5-5'
    assert anthropic.diagnostics()['endpoint_host'] == 'api.anthropic.com'
    openai = create_provider(ProviderConfig(model='m', api_key_env='SYNTHETIC_KEY', allow_live=True,
                                            transport='openai'), environ=ENV)
    assert openai.config_issues() == [] and openai.base_url() == 'https://api.openai.com/v1'
    assert error_of(provider_class, 'no_such') == ('NOT_CONFIGURED', 'TRANSPORT_UNKNOWN')
    unknown = diagnostics_for(ProviderConfig(transport='no_such'))
    assert unknown['reasons'] == ['TRANSPORT_UNKNOWN'] and not unknown['configured']
    assert (unknown['status'], unknown['region'], unknown['pricing']) == ('NOT_CONFIGURED', 'UNKNOWN', 'UNKNOWN')
    assert set(unknown['features']) == set(FEATURES)


def test_missing_adapter_dependency_and_executable(monkeypatch):
    monkeypatch.setattr(providers.importlib.util, 'find_spec', lambda name: None)
    assert create_provider(config(transport='openai_compatible'), environ=ENV).diagnostics()['reasons'] == [
        'ADAPTER_NOT_INSTALLED']
    cli = create_provider(ProviderConfig(allow_live=True, transport='claude_cli'), environ={}, which=lambda name: None)
    report = cli.diagnostics()
    assert report['reasons'] == ['CLI_NOT_FOUND'] and not report['adapter_installed']
    assert report['endpoint_host'] is None and report['model'] == 'haiku'
    # The executable lookup is resolved at call time, so a test or operator PATH change is honored.
    monkeypatch.setattr(providers.shutil, 'which', lambda name: f'/late/{name}')
    late = create_provider(ProviderConfig(allow_live=True, transport='claude_cli'), environ={})
    assert late.config_issues() == []
    monkeypatch.setattr(providers.shutil, 'which', lambda name: None)
    assert late.diagnostics()['reasons'] == ['CLI_NOT_FOUND']
    for transport in ('claude_cli', 'codex_cli', 'gemini_cli'):
        flagged = create_provider(ProviderConfig(model='--yolo', allow_live=True, transport=transport), environ={},
                                  which=lambda name: f'/bin/{name}')
        assert flagged.diagnostics()['reasons'] == ['MODEL_INVALID']


def test_new_vendor_is_a_subclass_plus_register():
    """Owner rule: adding a vendor means inheriting Provider and implementing one method."""
    try:
        @register
        class Grok(Provider):
            transport = 'grok_test'
            default_model = 'grok-test'
            default_base_url = 'https://grok.invalid/v1'

            def _complete(self, request):
                return ModelResponse(text='pong', model_id='grok-test')

        assert register(Grok) is Grok
        made = create_provider(ProviderConfig(api_key_env='SYNTHETIC_KEY', allow_live=True, transport='grok_test'),
                               environ=ENV)
        answer = made.complete(ModelRequest(user()))
        assert (answer.text, answer.provider_id, answer.model_id) == ('pong', 'grok_test', 'grok-test')
        assert 'grok_test' in transports()

        class Impostor(Provider):
            transport = 'grok_test'

            def _complete(self, request):
                raise AssertionError

        with pytest.raises(ValueError):
            register(Impostor)
    finally:
        unregister('grok_test')
    with pytest.raises(ValueError):
        register(object)

    class Nameless(Provider):
        def _complete(self, request):
            raise AssertionError

    with pytest.raises(ValueError):
        register(Nameless)


def test_broken_plugin_entry_point_is_skipped(monkeypatch):
    class Broken:
        def load(self):
            raise RuntimeError('broken plugin')

    class Good:
        loaded = False

        def load(self):
            Good.loaded = True

    monkeypatch.setattr(providers, '_loaded', False)
    monkeypatch.setattr(providers.importlib.metadata, 'entry_points', lambda group: [Broken(), Good()])
    assert 'anthropic' in transports()
    assert Good.loaded


def test_failed_builtin_adapter_import_is_retried(monkeypatch):
    """A built-in import failure must not leave the registry marked as loaded and empty."""
    real = providers.importlib.import_module
    attempts = []

    def flaky(name):
        attempts.append(name)
        if len(attempts) == 1:
            raise ImportError('synthetic')
        return real(name)

    monkeypatch.setattr(providers, '_loaded', False)
    monkeypatch.setattr(providers.importlib, 'import_module', flaky)
    monkeypatch.setattr(providers.importlib.metadata, 'entry_points', lambda group: [])
    with pytest.raises(ImportError):
        transports()
    assert 'anthropic' in transports() and len(attempts) == 2
    transports()
    assert len(attempts) == 2


# ----- M17-FR-02: one call, budgets, retries -------------------------------------------
def test_m17_fr_02_probe_and_budgets():
    ok = ModelResponse(text='ok')
    provider = Scripted(script=[ok] * 12)
    for _ in range(12):
        assert provider.complete(ModelRequest(user())).text == 'ok'
    assert error_of(provider.complete, ModelRequest(user())) == ('BUDGET_EXCEEDED', 'BUDGET_EXCEEDED')
    assert len(provider.requests) == 12
    provider.reset_run()
    provider.script = [ok]
    assert provider.complete(ModelRequest(user())).provider_id == 'scripted'

    denied = Scripted(script=[ProviderError('UNAUTHENTICATED'), ok])
    assert error_of(denied.complete, ModelRequest(user())) == ('UNAUTHENTICATED', 'UNAUTHENTICATED')
    assert len(denied.requests) == 1 and denied.slept == []

    limited = ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    always = Scripted(script=[limited] * 5)
    assert error_of(always.complete, ModelRequest(user())) == ('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    assert len(always.requests) == 3 and always.slept == [1.0, 2.0]

    recovered = Scripted(script=[ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED', 7), ok])
    assert recovered.complete(ModelRequest(user())).text == 'ok'
    assert recovered.slept == [7]

    too_long = Scripted(script=[ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED', 31), ok])
    assert error_of(too_long.complete, ModelRequest(user())) == ('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    assert too_long.slept == [] and len(too_long.requests) == 1

    # Every attempt, including a retry, consumes the call budget.
    # When the budget has no room for the retry, the rate-limit error is returned at once, without waiting.
    tight = Scripted(config(max_requests=2), script=[limited] * 3)
    assert error_of(tight.complete, ModelRequest(user())) == ('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    assert len(tight.requests) == 2 and tight.slept == [1.0]
    single = Scripted(config(max_requests=1), script=[limited] * 3)
    assert error_of(single.complete, ModelRequest(user())) == ('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    assert len(single.requests) == 1 and single.slept == []
    assert error_of(single.complete, ModelRequest(user())) == ('BUDGET_EXCEEDED', 'BUDGET_EXCEEDED')

    paid = Scripted(config(max_usd_per_run=0.01), script=[ModelResponse(text='a', usage=Usage(1, 1, 0.01)), ok])
    assert paid.complete(ModelRequest(user())).usage.cost_usd == 0.01
    assert error_of(paid.complete, ModelRequest(user())) == ('BUDGET_EXCEEDED', 'BUDGET_EXCEEDED')
    assert len(paid.requests) == 1


def test_request_defaults_and_rejections():
    provider = Scripted(script=[ModelResponse(text='ok')])
    provider.complete(ModelRequest(user()))
    assert provider.requests[0].max_output_tokens == 2048 and provider.requests[0].timeout_s == 60
    def tool(name):
        return ToolSpec(name, 'Tool.', NONCE_SCHEMA)

    def schema(value):
        return ModelRequest(user(), output_schema=value)

    for bad in (ModelRequest(()), ModelRequest(user(), require_tool=True),
                ModelRequest(user(), tools=(ECHO,), output_schema=NONCE_SCHEMA),
                ModelRequest(user(), output_schema={'type': 'no-such-type'}),
                ModelRequest(user(), tools=(ToolSpec('bad', 'Bad.', {'type': 'no-such-type'}),)),
                # Messages: only user and assistant turns with string content.
                ModelRequest((Message('system', 'x'),)), ModelRequest((Message('user', 5),)),
                ModelRequest(('plain text',)), ModelRequest(user() + (Message('tool', 'x'),)),
                # Tool names: nonempty, unique, vendor-safe characters.
                ModelRequest(user(), tools=(tool(''),)), ModelRequest(user(), tools=(tool('bad name'),)),
                ModelRequest(user(), tools=(tool('x' * 65),)), ModelRequest(user(), tools=(tool(5),)),
                ModelRequest(user(), tools=(ECHO, ECHO)),
                # Limits: a set value must be positive.
                ModelRequest(user(), max_output_tokens=0), ModelRequest(user(), max_output_tokens=-1),
                ModelRequest(user(), max_output_tokens='many'), ModelRequest(user(), timeout_s=0),
                ModelRequest(user(), timeout_s=-0.5), ModelRequest(user(), timeout_s=float('nan')),
                # Schemas: no dynamic or remote references, and every reference resolves.
                schema({'$dynamicRef': '#node'}), schema({'$ref': 'https://synthetic.invalid/schema.json'}),
                schema({'$ref': 'other.json#/x'}), schema({'$ref': '#/$defs/missing'}),
                schema({'type': 'object', 'properties': {'a': {'$ref': '#/$defs/missing'}}}),
                schema({'anyOf': [{'type': 'string'}, {'$ref': '#/anyOf/9'}]}),
                schema({'anyOf': [{'type': 'string'}, {'$ref': '#/anyOf/x'}]}),
                schema({'type': 'object', 'properties': {'a': {'$ref': '#/type/x'}}}),
                # A schema must be a JSON object, not a list or a string.
                schema(['not', 'a', 'schema']), schema('{"type": "object"}'),
                ModelRequest(user(), tools=(ToolSpec('listy', 'List.', ['type', 'object']),)),
                ModelRequest(user(), tools=(ToolSpec('remote', 'Remote.', {'$ref': 'https://synthetic.invalid/s'}),))):
        assert error_of(provider.complete, bad) == ('INVALID_INPUT', 'REQUEST_INVALID'), bad
    assert len(provider.requests) == 1

    accepted = (
        {'$defs': {'n': {'type': 'string'}}, 'type': 'object', 'properties': {'nonce': {'$ref': '#/$defs/n'}}},
        {'$defs': {'a/b~c': {'type': 'string'}, 'sp ace': {'type': 'object'}}, 'type': 'object',
         'properties': {'nonce': {'$ref': '#/$defs/a~1b~0c'}, 'more': {'$ref': '#/$defs/sp%20ace'}}},
        {'anyOf': [{'type': 'object'}, {'$ref': '#/anyOf/0'}]},
        {'type': 'object', 'properties': {'child': {'$ref': '#'}, 'nonce': {'type': 'string'}}},
        # Reference-shaped data inside a literal value is data, not a reference.
        {'type': 'object', 'properties': {'nonce': {'type': 'string'}, 'k': {'const': {'$ref': 'elsewhere'}},
                                          '$ref': {'enum': [{'$dynamicRef': 'x'}]}}},
    )
    for good in accepted:
        ok = Scripted(script=[ModelResponse(text='{"nonce": "n"}')])
        assert ok.complete(schema(good)).structured == {'nonce': 'n'}, good
    limits = Scripted(script=[ModelResponse(text='ok')])
    limits.complete(ModelRequest(user() + (Message('assistant', 'earlier'),), max_output_tokens=7, timeout_s=0.5))
    assert (limits.requests[0].max_output_tokens, limits.requests[0].timeout_s) == (7, 0.5)

    class NoStream(Scripted):
        supports_streaming = False

    assert error_of(NoStream().complete, ModelRequest(user(), stream=True)) == ('UNSUPPORTED', 'STREAMING_UNSUPPORTED')
    assert len(provider.requests) == 1


@pytest.mark.parametrize(('response', 'request_changes', 'reason'), [
    (ModelResponse(stop_reason='length'), {}, 'OUTPUT_TRUNCATED'),
    (ModelResponse(stop_reason='refusal'), {}, 'MODEL_REFUSED'),
    (ModelResponse(tool_calls=(ToolCall('other', {'nonce': 'n'}),)), {'tools': (ECHO,)}, 'TOOL_CALL_INVALID'),
    (ModelResponse(tool_calls=(ToolCall('echo', {'nonce': 1}),)), {'tools': (ECHO,)}, 'TOOL_CALL_INVALID'),
    (ModelResponse(tool_calls=(ToolCall('echo', ['n']),)), {'tools': (ECHO,)}, 'TOOL_CALL_INVALID'),
    (ModelResponse(tool_calls=(ToolCall('echo', {'nonce': 'n'}),)), {}, 'TOOL_CALL_INVALID'),
    (ModelResponse(text='plain'), {'tools': (ECHO,), 'require_tool': True}, 'TOOL_CALL_MISSING'),
    (ModelResponse(text='not json'), {'output_schema': NONCE_SCHEMA}, 'SCHEMA_INVALID_OUTPUT'),
    (ModelResponse(text='{"nonce": 5}'), {'output_schema': NONCE_SCHEMA}, 'SCHEMA_INVALID_OUTPUT'),
    (ModelResponse(structured={'other': 1}), {'output_schema': NONCE_SCHEMA}, 'SCHEMA_INVALID_OUTPUT'),
])
def test_invalid_model_output_is_typed(response, request_changes, reason):
    provider = Scripted(script=[response])
    assert error_of(provider.complete, ModelRequest(user(), **request_changes)) == ('OUTPUT_INVALID', reason)


@pytest.mark.parametrize(('response', 'request_changes'), [
    (ModelResponse(stop_reason='other'), {}),
    (ModelResponse(stop_reason='vendor_new_reason'), {}),
    (ModelResponse(stop_reason=''), {}),
    # Stop-reason rows are checked before the tool and schema rows.
    (ModelResponse(stop_reason='other', tool_calls=(ToolCall('nope', {}),)), {'tools': (ECHO,)}),
    (ModelResponse(stop_reason='other', text='not json'), {'output_schema': NONCE_SCHEMA}),
])
def test_unknown_stop_reason_is_an_upstream_error(response, request_changes):
    provider = Scripted(script=[response])
    assert error_of(provider.complete, ModelRequest(user(), **request_changes)) == (
        'TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')


def test_stop_reason_rows_come_before_tool_and_schema_rows():
    truncated = ModelResponse(stop_reason='length', tool_calls=(ToolCall('nope', {}),))
    assert error_of(Scripted(script=[truncated]).complete, ModelRequest(user(), tools=(ECHO,), require_tool=True)) == (
        'OUTPUT_INVALID', 'OUTPUT_TRUNCATED')
    refused = ModelResponse(stop_reason='refusal', text='not json')
    assert error_of(Scripted(script=[refused]).complete, ModelRequest(user(), output_schema=NONCE_SCHEMA)) == (
        'OUTPUT_INVALID', 'MODEL_REFUSED')


@pytest.mark.parametrize('malformed', [
    ModelResponse(text=5), ModelResponse(text=None), ModelResponse(tool_calls='echo'),
    ModelResponse(tool_calls=({'name': 'echo'},)), ModelResponse(tool_calls=(ToolCall(5, {}),)),
    ModelResponse(usage={'cost_usd': 1}), ModelResponse(usage=None), ModelResponse(model_id=None),
    ModelResponse(stop_reason=None), ModelResponse(chunk_count='3'), ModelResponse(chunk_count=True),
])
def test_malformed_adapter_response_is_an_adapter_fault(malformed):
    provider = Scripted(script=[malformed])
    assert error_of(provider.complete, ModelRequest(user(), tools=(ECHO,))) == ('INTERNAL_ERROR', 'ADAPTER_FAULT')


def test_fault_while_validating_is_an_adapter_fault(monkeypatch):
    def boom(instance, schema):
        raise RuntimeError('upstream secret detail')

    monkeypatch.setattr(providers, '_valid', boom)
    provider = Scripted(script=[ModelResponse(text='{"nonce": "n"}')])
    assert error_of(provider.complete, ModelRequest(user(), output_schema=NONCE_SCHEMA)) == (
        'INTERNAL_ERROR', 'ADAPTER_FAULT')


def test_unparseable_or_unvalidatable_output_is_schema_invalid():
    deep = ModelResponse(text='[' * 100000)
    assert error_of(Scripted(script=[deep]).complete, ModelRequest(user(), output_schema=NONCE_SCHEMA)) == (
        'OUTPUT_INVALID', 'SCHEMA_INVALID_OUTPUT')
    # A self-referential schema is accepted as a request, and a validator failure is never a crash.
    looping = Scripted(script=[ModelResponse(structured={'nonce': 'n'})])
    assert error_of(looping.complete, ModelRequest(user(), output_schema={'$ref': '#'})) == (
        'OUTPUT_INVALID', 'SCHEMA_INVALID_OUTPUT')


def test_usage_is_normalized_before_cost_accounting():
    nan, inf = float('nan'), float('inf')
    cases = [(Usage(3, 4, 0.5), (3, 4, 0.5)), (Usage(0, 0, 0), (0, 0, 0)), (Usage(-1, True, nan), (None, None, None)),
             (Usage('7', 2.0, -0.1), (None, None, None)), (Usage(1, 2, inf), (1, 2, None)),
             (Usage(1, 2, True), (1, 2, None)), (Usage(1, 2, '0.1'), (1, 2, None)), (Usage(), (None, None, None))]
    provider = Scripted(config(max_requests=50), script=[ModelResponse(text='ok', usage=usage) for usage, _ in cases])
    for _, expected in cases:
        usage = provider.complete(ModelRequest(user())).usage
        assert (usage.input_tokens, usage.output_tokens, usage.cost_usd) == expected
    # An unusable cost can neither poison nor bypass the run budget.
    capped = Scripted(config(max_usd_per_run=0.01), script=[ModelResponse(text='a', usage=Usage(1, 1, nan)),
                                                             ModelResponse(text='b', usage=Usage(1, 1, -5)),
                                                             ModelResponse(text='c', usage=Usage(1, 1, 0.01))])
    for _ in range(3):
        capped.complete(ModelRequest(user()))
    assert error_of(capped.complete, ModelRequest(user())) == ('BUDGET_EXCEEDED', 'BUDGET_EXCEEDED')


def test_valid_output_and_adapter_fault():
    provider = Scripted(script=[ModelResponse(tool_calls=(ToolCall('echo', {'nonce': 'n'}),), stop_reason='tool_call'),
                                ModelResponse(text='{"nonce": "n"}'), ModelResponse(structured={'nonce': 'm'}),
                                RuntimeError('upstream secret detail'), 'not a response'])
    assert provider.complete(ModelRequest(user(), tools=(ECHO,), require_tool=True)).tool_calls[0].name == 'echo'
    assert provider.complete(ModelRequest(user(), output_schema=NONCE_SCHEMA)).structured == {'nonce': 'n'}
    assert provider.complete(ModelRequest(user(), output_schema=NONCE_SCHEMA)).structured == {'nonce': 'm'}
    with pytest.raises(ProviderError) as caught:
        provider.complete(ModelRequest(user()))
    assert (caught.value.code, caught.value.reason) == ('INTERNAL_ERROR', 'ADAPTER_FAULT')
    assert 'secret' not in caught.value.message and caught.value.__cause__ is None
    assert error_of(provider.complete, ModelRequest(user())) == ('INTERNAL_ERROR', 'ADAPTER_FAULT')
    assert ProviderError('NO_SUCH_CODE').message == 'The provider call failed.'


# ----- probe ---------------------------------------------------------------------------
class Echoing(Provider):
    """Answers the probe prompts from the request itself; ``faults`` overrides one feature."""

    transport = 'echoing'

    def __init__(self, cfg=None, faults=None, **dependencies):
        nonces = iter(f'nonce-{index}' for index in range(100))
        dependencies.setdefault('environ', ENV)
        dependencies.setdefault('nonce', lambda: next(nonces))
        dependencies.setdefault('clock', lambda: '2026-01-01T00:00:00+00:00')
        super().__init__(cfg or config(transport='echoing'), **dependencies)
        self.faults = faults or {}
        self.kinds = []

    def _complete(self, request):
        kind = ('tools' if request.tools else 'structured_output' if request.output_schema else
                'streaming' if request.stream else 'timeout' if request.timeout_s == 1 else 'concurrency')
        self.kinds.append(kind)
        fault = self.faults.get(kind)
        if isinstance(fault, BaseException):
            raise fault
        if fault is not None:
            return fault
        nonce = request.messages[0].content.rstrip('.').split()[-1]
        if kind == 'tools':
            return ModelResponse(tool_calls=(ToolCall(request.tools[0].name, {'nonce': nonce}),), model_id='echo-1')
        if kind == 'structured_output':
            return ModelResponse(text=json.dumps({'nonce': nonce}))
        if kind == 'timeout':
            raise ProviderError('DEADLINE_EXCEEDED')
        return ModelResponse(text=f' {nonce}\n', chunk_count=3)


def test_probe_all_supported_report_shape():
    provider = Echoing(config(transport='echoing', max_concurrency=3))
    report = provider.probe()
    assert report['features'] == dict.fromkeys(FEATURES, 'SUPPORTED')
    assert report['observations'] == dict.fromkeys(FEATURES, 'PROBE_PASSED')
    assert provider.kinds == ['tools', 'structured_output', 'streaming', 'timeout'] + ['concurrency'] * 3
    assert report['aborted'] is None and report['evidence_refs'] == []
    assert report['model_or_adapter_version'] == 'echo-1' and report['provider_id'] == 'echoing'
    assert report['measured_at'] == '2026-01-01T00:00:00+00:00'
    assert report['metadata_attestations'] == {'region': 'UNKNOWN', 'pricing': 'UNKNOWN'}
    assert len(report['config_hash']) == 64
    assert report['config_hash'] == Echoing(config(transport='echoing', max_concurrency=3)).config_hash()
    assert report['config_hash'] != Echoing(config(transport='echoing', model='other')).config_hash()
    assert 'synthetic-never-log' not in json.dumps(report)


@pytest.mark.parametrize(('faults', 'feature', 'expected'), [
    ({'tools': ModelResponse(tool_calls=(ToolCall('quati_probe_echo', {'nonce': 'wrong'}),))}, 'tools',
     ('UNSUPPORTED', 'NONCE_MISMATCH')),
    ({'tools': ModelResponse(text='plain')}, 'tools', ('UNSUPPORTED', 'TOOL_CALL_MISSING')),
    ({'structured_output': ModelResponse(text='{"nonce": "wrong"}')}, 'structured_output',
     ('UNSUPPORTED', 'NONCE_MISMATCH')),
    # A rejected request proves nothing about the feature.
    ({'structured_output': ProviderError('UNSUPPORTED', 'REQUEST_REJECTED')}, 'structured_output',
     ('NOT_VERIFIED', 'REQUEST_REJECTED')),
    ({'tools': ProviderError('UNSUPPORTED', 'REQUEST_REJECTED')}, 'tools', ('NOT_VERIFIED', 'REQUEST_REJECTED')),
    ({'structured_output': ModelResponse(stop_reason='other')}, 'structured_output',
     ('NOT_VERIFIED', 'UPSTREAM_ERROR')),
    ({'streaming': ModelResponse(text='wrong', chunk_count=4)}, 'streaming', ('UNSUPPORTED', 'NONCE_MISMATCH')),
    ({'streaming': ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')}, 'streaming',
     ('NOT_VERIFIED', 'UPSTREAM_ERROR')),
    ({'timeout': ModelResponse(text='done')}, 'timeout', ('NOT_VERIFIED', 'DEADLINE_NOT_REACHED')),
    ({'timeout': ModelResponse(stop_reason='length')}, 'timeout', ('NOT_VERIFIED', 'DEADLINE_NOT_REACHED')),
    ({'timeout': ProviderError('UNSUPPORTED', 'REQUEST_REJECTED')}, 'timeout', ('NOT_VERIFIED', 'REQUEST_REJECTED')),
    ({'timeout': ProviderError('TEMPORARILY_UNAVAILABLE', 'NETWORK_ERROR')}, 'timeout',
     ('NOT_VERIFIED', 'NETWORK_ERROR')),
    ({'concurrency': ModelResponse(text='wrong')}, 'concurrency', ('UNSUPPORTED', 'NONCE_MISMATCH')),
    ({'concurrency': ProviderError('TEMPORARILY_UNAVAILABLE', 'NETWORK_ERROR')}, 'concurrency',
     ('NOT_VERIFIED', 'NETWORK_ERROR')),
])
def test_probe_classifies_each_failure(faults, feature, expected):
    report = Echoing(config(transport='echoing', max_concurrency=2), faults=faults).probe()
    assert (report['features'][feature], report['observations'][feature]) == expected
    assert report['aborted'] is None
    others = [name for name in FEATURES if name != feature]
    assert all(report['features'][name] == 'SUPPORTED' for name in others)


def test_probe_stops_at_an_exhausted_rate_limit():
    """A rate-limited provider is not hit again by the rest of the probe."""
    provider = Echoing(faults={'structured_output': ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED', 99)})
    report = provider.probe()
    assert report['aborted'] == 'RATE_LIMITED' and provider.kinds == ['tools', 'structured_output']
    assert (report['features']['structured_output'], report['observations']['structured_output']) == (
        'NOT_VERIFIED', 'RATE_LIMITED')
    assert [report['observations'][name] for name in FEATURES[2:]] == ['NOT_RUN'] * 3
    assert [report['features'][name] for name in FEATURES[2:]] == ['NOT_VERIFIED'] * 3
    last = Echoing(config(transport='echoing', max_concurrency=2),
                   faults={'concurrency': ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED', 99)}).probe()
    assert last['aborted'] == 'RATE_LIMITED' and last['observations']['concurrency'] == 'RATE_LIMITED'


@pytest.mark.parametrize('limit', [1, 0])
def test_probe_does_not_exercise_concurrency_below_two(limit):
    provider = Echoing(config(transport='echoing', max_concurrency=limit))
    report = provider.probe()
    assert (report['features']['concurrency'], report['observations']['concurrency']) == (
        'NOT_VERIFIED', 'CONCURRENCY_NOT_EXERCISED')
    assert provider.kinds == ['tools', 'structured_output', 'streaming', 'timeout'] and report['aborted'] is None


def test_probe_single_chunk_and_non_streaming_transport():
    class OneChunk(Echoing):
        def _complete(self, request):
            response = super()._complete(request)
            return response if not request.stream else ModelResponse(text=response.text, chunk_count=1)

    report = OneChunk().probe()
    assert (report['features']['streaming'], report['observations']['streaming']) == ('NOT_VERIFIED', 'SINGLE_CHUNK')

    class NoStream(Echoing):
        supports_streaming = False

    provider = NoStream()
    report = provider.probe()
    assert (report['features']['streaming'], report['observations']['streaming']) == (
        'UNSUPPORTED', 'STREAMING_UNSUPPORTED')
    assert 'streaming' not in provider.kinds
    assert report['model_or_adapter_version'] == 'echo-1'


@pytest.mark.parametrize('code', ['UNAUTHENTICATED', 'FORBIDDEN'])
def test_probe_stops_at_first_credential_failure(code):
    provider = Echoing(faults={'structured_output': ProviderError(code)})
    report = provider.probe()
    assert report['aborted'] == code and provider.kinds == ['tools', 'structured_output']
    assert report['features']['tools'] == 'SUPPORTED'
    assert report['observations']['structured_output'] == code
    assert [report['observations'][name] for name in FEATURES[2:]] == ['NOT_RUN'] * 3
    assert [report['features'][name] for name in FEATURES[1:]] == ['NOT_VERIFIED'] * 4


def test_probe_stops_on_budget_and_configuration():
    report = Echoing(config(transport='echoing', max_requests=1)).probe()
    assert report['aborted'] == 'BUDGET_EXCEEDED' and report['features']['tools'] == 'SUPPORTED'
    report = Echoing(config(transport='echoing', allow_live=False)).probe()
    assert report['aborted'] == 'NOT_CONFIGURED' and report['observations']['tools'] == 'LIVE_NOT_ALLOWED'
    assert report['model_or_adapter_version'] == 'synthetic'


# ----- M17-RT-01: labels and metadata never prove support ------------------------------
def test_m17_rt_01_label_not_proof():
    provider = create_provider(ProviderConfig(model='claude-opus-supports-tools-streaming', transport='anthropic',
                                              api_key_env='SYNTHETIC_KEY', allow_live=True), environ=ENV)
    report = provider.diagnostics()
    assert set(report['features'].values()) == {'NOT_VERIFIED'}
    assert (report['region'], report['pricing']) == ('UNKNOWN', 'UNKNOWN')
    assert error_of(require_features, report['features'], ('tools',)) == ('UNSUPPORTED', 'MODEL_INCOMPATIBLE')
    measured = Echoing(faults={'tools': ModelResponse(text='I support tools, trust me')}).probe()['features']
    assert measured['tools'] == 'UNSUPPORTED'
    assert error_of(require_features, measured, ('tools',)) == ('UNSUPPORTED', 'MODEL_INCOMPATIBLE')
    assert error_of(require_features, {}, ('streaming',)) == ('UNSUPPORTED', 'MODEL_INCOMPATIBLE')
    assert require_features(measured, ('structured_output', 'streaming')) is None
    assert require_features(measured, ()) is None


# ----- M17-RT-02: a vendor sign-in file is never an API key ----------------------------
@pytest.mark.parametrize('value', ['/home/someone/.codex/auth.json', '~/.codex/auth.json', './auth.json',
                                   '../auth.json', 'auth.json'])
def test_m17_rt_02_codex_signin_not_api_key(value):
    calls = []

    class Recording(Scripted):
        def _complete(self, request):
            calls.append(request)
            return ModelResponse(text='must not happen')

    provider = Recording(environ={'SYNTHETIC_KEY': value})
    assert provider.diagnostics()['reasons'] == ['API_KEY_REF_INVALID']
    assert value not in json.dumps(provider.diagnostics())
    with pytest.raises(ProviderError) as caught:
        provider.complete(ModelRequest(user()))
    assert (caught.value.code, caught.value.reason) == ('NOT_CONFIGURED', 'API_KEY_REF_INVALID')
    assert value not in caught.value.message and value not in str(caught.value)
    assert calls == []
    assert provider.probe()['aborted'] == 'NOT_CONFIGURED'
    assert calls == []


def test_cli_transports_take_no_key_and_no_endpoint():
    for transport in ('claude_cli', 'codex_cli', 'gemini_cli'):
        provider = create_provider(ProviderConfig(base_url='not-a-url', api_key_env='BAD-NAME', allow_live=True,
                                                  transport=transport), environ={}, which=lambda name: f'/bin/{name}')
        assert provider.config_issues() == []
        assert provider.diagnostics()['endpoint_host'] is None


# ----- probe command -------------------------------------------------------------------
class Identity:
    def diagnostics(self):
        return {'configured': True}


def service_for(report_or_error, cfg=None):
    stored = []

    class Fixed:
        def __init__(self, cfg):
            self.config = cfg

        def probe(self, profile=None):  # S00-T04 fix round 5 (S4): probe() now takes the ask ProbeProfile; stub signature updated.
            if isinstance(report_or_error, BaseException):
                raise report_or_error
            return report_or_error

    def sink(record):
        stored.append(record)
        return {'sha256': 'ab' * 32, 'path': '/receipts/x.json'}

    service = CLIService(Identity(), cfg or ProviderConfig(allow_live=True, transport='claude_cli'), sink, Fixed)
    return service, stored


@pytest.fixture
def cli_present(monkeypatch):
    monkeypatch.setattr(providers.shutil, 'which', lambda name: f'/bin/{name}')


def test_probe_command_success_lists_unverified_features(cli_present):
    report = Echoing(faults={'timeout': ModelResponse(text='done')}).probe()
    service, stored = service_for(report)
    code, result = service.probe()
    assert code == 0 and result['status'] == 'SUCCEEDED' and result['error'] is None
    assert result['uncertainties'] == ['timeout: NOT_VERIFIED (DEADLINE_NOT_REACHED)',
                                       'concurrency: NOT_VERIFIED (CONCURRENCY_NOT_EXERCISED)']
    assert result['data']['provider']['status'] == 'PROBED'
    assert result['evidence_refs'] == ['sha256:' + 'ab' * 32 + ':/receipts/x.json']
    assert result['data']['feature_report']['evidence_refs'] == result['evidence_refs']
    assert result['data']['provider']['features'] == report['features']
    assert result['data']['scope'] == 'M17_PROVIDER_PROBE'
    assert stored[0]['kind'] == 'feature_report' and stored[0]['features'] == report['features']
    code, result = service.doctor(probe=True)
    assert code == 0 and result['data']['scope'] == 'S00_T01_LOCAL_CLI' and 'feature_report' in result['data']
    assert service.doctor()[0] == 0 and len(stored) == 2


@pytest.mark.parametrize(('faults', 'cfg', 'expected'), [
    ({'tools': ProviderError('UNAUTHENTICATED')}, None, (4, 'DENIED', 'UNAUTHENTICATED')),
    ({'tools': ProviderError('FORBIDDEN')}, None, (4, 'DENIED', 'FORBIDDEN')),
    ({}, config(transport='echoing', max_requests=1), (4, 'BLOCKED', 'BUDGET_EXCEEDED')),
    ({}, config(transport='echoing', allow_live=False), (3, 'BLOCKED', 'NOT_CONFIGURED')),
    ({name: ProviderError('TEMPORARILY_UNAVAILABLE', 'NETWORK_ERROR') for name in FEATURES}, None,
     (5, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE')),
    # A probe stopped by the rate limit before any completed exchange proves nothing.
    ({'tools': ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED', 99)}, None,
     (5, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE')),
    # A deadline that fires proves nothing about a completed exchange.
    ({name: ProviderError('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED') for name in FEATURES if name != 'timeout'}, None,
     (5, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE')),
])
def test_probe_command_failure_exits(cli_present, faults, cfg, expected):
    service, stored = service_for(Echoing(cfg, faults=faults).probe())
    code, result = service.probe()
    assert (code, result['status'], result['error']['code']) == expected
    assert result['next_action'] and result['error']['message'] and result['evidence_refs']
    assert result['data']['provider']['status'] == 'NOT_PROBED'
    assert len(stored) == 1


def test_probe_command_counts_answered_exchanges(cli_present):
    class NoStream(Echoing):
        supports_streaming = False

    down = {name: ProviderError('TEMPORARILY_UNAVAILABLE', 'NETWORK_ERROR')
            for name in ('tools', 'structured_output', 'concurrency')}
    # A locally refused streaming request is not an exchange.
    assert service_for(NoStream(faults=down).probe())[0].probe()[0] == 5
    # A wrong answer and a single-chunk answer are both completed exchanges.
    wrong = dict(down, tools=ModelResponse(text='plain'))
    assert service_for(Echoing(faults=dict(wrong, streaming=ProviderError('DEADLINE_EXCEEDED'))).probe())[0].probe()[0] == 0

    class OneChunk(Echoing):
        def _complete(self, request):
            response = super()._complete(request)
            return response if not request.stream else ModelResponse(text=response.text, chunk_count=1)

    assert service_for(OneChunk(faults=down).probe())[0].probe()[0] == 0
    # A probe stopped by the rate limit after a completed exchange still succeeds, listing what it did not measure.
    limited = {'structured_output': ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED', 99)}
    code, result = service_for(Echoing(faults=limited).probe())[0].probe()
    assert code == 0 and result['status'] == 'SUCCEEDED' and result['data']['provider']['status'] == 'PROBED'
    assert result['uncertainties'][:2] == ['structured_output: NOT_VERIFIED (RATE_LIMITED)',
                                           'streaming: NOT_VERIFIED (NOT_RUN)']
    assert result['data']['feature_report']['aborted'] == 'RATE_LIMITED'


def test_probe_command_blocks_before_any_call_when_not_configured():
    service, stored = service_for(AssertionError('factory must not run'), ProviderConfig())
    code, result = service.probe()
    assert (code, result['status'], result['error']['code']) == (3, 'BLOCKED', 'NOT_CONFIGURED')
    assert result['data']['provider']['reasons'] == ['API_KEY_MISSING', 'LIVE_NOT_ALLOWED']
    assert result['data']['provider']['status'] == 'NOT_CONFIGURED'
    assert result['uncertainties'] and stored == []
    unknown, stored = service_for(AssertionError('factory must not run'), ProviderConfig(transport='no_such'))
    code, result = unknown.probe()
    assert code == 3 and result['data']['provider']['reasons'] == ['TRANSPORT_UNKNOWN'] and stored == []
