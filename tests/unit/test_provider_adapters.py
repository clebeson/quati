"""Adapter contract tests: wire shape, error mapping and isolation, with no network and no child process.

The SDK adapters talk to an in-memory HTTP transport; the CLI adapters talk to a scripted
runner. These prove Quati's side of each contract only. A passing test here is fake-provider
compatibility, never evidence that a real provider works (see tests/external).
"""
import json
import subprocess
import sys

import httpx2
import pytest

from quati.adapters.providers import (AnthropicProvider, ClaudeCliProvider, CodexCliProvider, GeminiCliProvider,
                                      OpenAICompatibleProvider, OpenAIProvider)
from quati.adapters.providers import cli as cli_module
from quati.adapters.providers._sdk import map_error, retry_after_seconds
from quati.application.ports import ProviderConfig
from quati.application.providers import Message, ModelRequest, ProviderError, ToolSpec

KEY = 'synthetic-never-log'
SCHEMA = {'type': 'object', 'properties': {'nonce': {'type': 'string'}}, 'required': ['nonce'],
          'additionalProperties': False}
ECHO = ToolSpec('echo', 'Echo.', SCHEMA)
USER = (Message('user', 'hello'),)


def error_of(callable_, *args):
    with pytest.raises(ProviderError) as caught:
        callable_(*args)
    assert KEY not in caught.value.message
    return caught.value.code, caught.value.reason


class Wire:
    """In-memory HTTP endpoint that records requests and replays queued responses."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.transport = httpx2.MockTransport(self.handle)

    def handle(self, request):
        self.requests.append(request)
        outcome = self.responses.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def body(self, index=-1):
        return json.loads(self.requests[index].content)


def reply(payload, status=200, headers=None):
    return httpx2.Response(status, json=payload, headers=headers)


def sse(events):
    lines = []
    for event in events:
        if isinstance(event, str):
            lines.append(f'data: {event}\n\n')
        else:
            name = f"event: {event['type']}\n" if 'type' in event else ''
            lines.append(f'{name}data: {json.dumps(event)}\n\n')
    return httpx2.Response(200, content=''.join(lines).encode(), headers={'content-type': 'text/event-stream'})


def make(cls, wire, environ=None, **changes):
    values = dict(base_url='https://synthetic.invalid/v1', model='synthetic', api_key_env='SYNTHETIC_KEY',
                  allow_live=True, transport=cls.transport)
    values.update(changes)
    slept = []
    provider = cls(ProviderConfig(**values), http_transport=wire.transport,
                   environ=dict({'SYNTHETIC_KEY': KEY}, **(environ or {})), sleep=slept.append)
    provider.slept = slept
    return provider


# ----- Anthropic -----------------------------------------------------------------------
def anthropic_message(content, stop='end_turn', **extra):
    return dict({'id': 'msg_1', 'type': 'message', 'role': 'assistant', 'model': 'claude-test', 'content': content,
                 'stop_reason': stop, 'stop_sequence': None,
                 'usage': {'input_tokens': 3, 'output_tokens': 2, 'cache_read_input_tokens': 4}}, **extra)


def test_anthropic_request_shape_and_text_answer(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'ambient-key-must-not-be-used')
    monkeypatch.setenv('ANTHROPIC_AUTH_TOKEN', 'ambient-token-must-not-be-used')
    monkeypatch.setenv('ANTHROPIC_BASE_URL', 'https://redirected.invalid')
    wire = Wire(reply(anthropic_message([{'type': 'text', 'text': 'hi'}])))
    provider = make(AnthropicProvider, wire, base_url='')
    answer = provider.complete(ModelRequest(USER, system='Be brief.', max_output_tokens=50))
    assert (answer.text, answer.stop_reason, answer.model_id, answer.provider_id) == (
        'hi', 'end', 'claude-test', 'anthropic')
    assert (answer.usage.input_tokens, answer.usage.output_tokens, answer.usage.cost_usd) == (7, 2, None)
    request = wire.requests[0]
    assert str(request.url) == 'https://api.anthropic.com/v1/messages'
    # SDK 2.x carries the explicit key as a bearer credential; no ambient credential may appear anywhere.
    assert request.headers['authorization'] == f'Bearer {KEY}' and 'x-api-key' not in request.headers
    assert not any('ambient' in value for value in request.headers.values())
    assert wire.body() == {'model': 'synthetic', 'max_tokens': 50, 'system': 'Be brief.',
                           'messages': [{'role': 'user', 'content': 'hello'}]}


def test_anthropic_tools_and_structured_output():
    wire = Wire(reply(anthropic_message([{'type': 'tool_use', 'id': 't1', 'name': 'echo', 'input': {'nonce': 'n'}}],
                                        'tool_use')),
                reply(anthropic_message([{'type': 'text', 'text': '{"nonce": "n"}'}])))
    provider = make(AnthropicProvider, wire)
    answer = provider.complete(ModelRequest(USER, tools=(ECHO,), require_tool=True))
    assert answer.stop_reason == 'tool_call' and answer.tool_calls[0].arguments == {'nonce': 'n'}
    body = wire.body()
    assert body['tools'] == [{'name': 'echo', 'description': 'Echo.', 'input_schema': SCHEMA}]
    assert 'calling one of the provided tools' in body['system'] and 'tool_choice' not in body
    assert str(wire.requests[0].url) == 'https://synthetic.invalid/v1/v1/messages'
    assert provider.complete(ModelRequest(USER, output_schema=SCHEMA)).structured == {'nonce': 'n'}
    assert wire.body()['output_config'] == {'format': {'type': 'json_schema', 'schema': SCHEMA}}


def anthropic_stream(texts, stop='end_turn'):
    start = anthropic_message([], None)
    return sse([{'type': 'message_start', 'message': start},
                {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}},
                *({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': text}}
                  for text in texts),
                {'type': 'content_block_stop', 'index': 0},
                {'type': 'message_delta', 'delta': {'stop_reason': stop, 'stop_sequence': None},
                 'usage': {'output_tokens': 5}},
                {'type': 'message_stop'}])


def test_anthropic_streaming_counts_chunks_and_enforces_total_deadline():
    wire = Wire(anthropic_stream(['ab', 'cd', 'ef']), anthropic_stream(['ab', 'cd']))
    provider = make(AnthropicProvider, wire)
    answer = provider.complete(ModelRequest(USER, stream=True))
    assert (answer.text, answer.chunk_count, answer.stop_reason) == ('abcdef', 3, 'end')
    assert wire.body()['stream'] is True
    ticks = iter([0.0, 0.5, 99.0])
    provider._monotonic = lambda: next(ticks)
    assert error_of(provider.complete, ModelRequest(USER, stream=True, timeout_s=5)) == (
        'DEADLINE_EXCEEDED', 'DEADLINE_EXCEEDED')


@pytest.mark.parametrize(('stop', 'expected'), [('max_tokens', 'OUTPUT_TRUNCATED'), ('refusal', 'MODEL_REFUSED'),
                                                ('model_context_window_exceeded', 'OUTPUT_TRUNCATED')])
def test_anthropic_stop_reasons(stop, expected):
    provider = make(AnthropicProvider, Wire(reply(anthropic_message([{'type': 'text', 'text': 'x'}], stop))))
    assert error_of(provider.complete, ModelRequest(USER)) == ('OUTPUT_INVALID', expected)


def test_anthropic_unknown_stop_reason_and_unusable_body():
    # M17: a stop reason Quati does not know is an unusable answer, never read as a normal end.
    wire = Wire(reply(anthropic_message([{'type': 'text', 'text': 'x'}], 'pause_turn')), reply({}))
    provider = make(AnthropicProvider, wire)
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')


@pytest.mark.parametrize('cls', [AnthropicProvider, OpenAICompatibleProvider])
def test_mapped_errors_carry_no_upstream_exception(cls):
    wire = Wire(reply({'error': {'message': f'upstream detail {KEY}'}}, 400))
    with pytest.raises(ProviderError) as caught:
        make(cls, wire).complete(ModelRequest(USER))
    assert caught.value.__cause__ is None and caught.value.__context__ is None


HTTP_ERRORS = [
    (401, ('UNAUTHENTICATED', 'UNAUTHENTICATED')), (403, ('FORBIDDEN', 'FORBIDDEN')),
    (402, ('FORBIDDEN', 'FORBIDDEN')), (408, ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')),
    (404, ('NOT_FOUND', 'MODEL_NOT_FOUND')), (400, ('UNSUPPORTED', 'REQUEST_REJECTED')),
    (422, ('UNSUPPORTED', 'REQUEST_REJECTED')), (500, ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')),
    (529, ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')), (302, ('TEMPORARILY_UNAVAILABLE', 'REDIRECT_REJECTED')),
]


@pytest.mark.parametrize('cls', [AnthropicProvider, OpenAICompatibleProvider])
@pytest.mark.parametrize(('status', 'expected'), HTTP_ERRORS)
def test_http_status_mapping_never_retries_or_follows(cls, status, expected):
    wire = Wire(reply({'error': {'message': f'upstream detail {KEY}'}}, status,
                      {'location': 'https://elsewhere.invalid/v1'}))
    provider = make(cls, wire)
    assert error_of(provider.complete, ModelRequest(USER)) == expected
    assert len(wire.requests) == 1 and provider.slept == []


@pytest.mark.parametrize('cls', [AnthropicProvider, OpenAICompatibleProvider])
def test_rate_limit_honours_retry_after_then_gives_up(cls):
    limited = lambda headers=None: reply({'error': {'message': 'slow down'}}, 429, headers)  # noqa: E731
    wire = Wire(limited({'retry-after': '3'}), limited(), limited({'retry-after': 'soon'}))
    provider = make(cls, wire)
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    assert len(wire.requests) == 3 and provider.slept == [3.0, 2.0]
    wire = Wire(limited({'retry-after': '31'}))
    provider = make(cls, wire)
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    assert len(wire.requests) == 1 and provider.slept == []


@pytest.mark.parametrize('cls', [AnthropicProvider, OpenAICompatibleProvider])
def test_connection_and_timeout_failures(cls):
    wire = Wire(httpx2.ConnectError('refused'), httpx2.ReadTimeout('slow'))
    provider = make(cls, wire)
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'NETWORK_ERROR')
    assert error_of(provider.complete, ModelRequest(USER)) == ('DEADLINE_EXCEEDED', 'DEADLINE_EXCEEDED')
    assert len(wire.requests) == 2


def test_sdk_error_mapping_fallbacks():
    import anthropic

    class Shaped:
        def __init__(self, headers):
            self.response = type('R', (), {'headers': headers})()

    assert retry_after_seconds(Shaped({'retry-after': '4'})) == 4.0
    # retry-after-ms (milliseconds) wins over retry-after (seconds) when present and numeric.
    assert retry_after_seconds(Shaped({'retry-after-ms': '1500', 'retry-after': '9'})) == 1.5
    assert retry_after_seconds(Shaped({'retry-after-ms': 'soon', 'retry-after': '9'})) == 9.0
    assert retry_after_seconds(Shaped({'retry-after-ms': '-5'})) is None
    assert retry_after_seconds(Shaped({'retry-after': '-1'})) is None
    assert retry_after_seconds(Shaped({})) is None and retry_after_seconds(object()) is None
    generic = anthropic.APIError('x', httpx2.Request('POST', 'https://synthetic.invalid'), body=None)
    assert map_error(anthropic, generic).reason == 'UPSTREAM_ERROR'
    assert map_error(anthropic, RuntimeError('x')).reason == 'ADAPTER_FAULT'


# ----- OpenAI-compatible ---------------------------------------------------------------
def completion(message, finish='stop', **extra):
    return dict({'id': 'c1', 'object': 'chat.completion', 'created': 1, 'model': 'vendor/model-1',
                 'choices': [{'index': 0, 'message': dict({'role': 'assistant'}, **message),
                              'finish_reason': finish}],
                 'usage': {'prompt_tokens': 5, 'completion_tokens': 2, 'total_tokens': 7}}, **extra)


def test_openai_compatible_request_shape_and_environment_isolation(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'ambient-key-must-not-be-used')
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://redirected.invalid/v1')
    monkeypatch.setenv('OPENAI_ORG_ID', 'org-ambient')
    monkeypatch.setenv('OPENAI_PROJECT_ID', 'proj-ambient')
    payload = completion({'content': 'hi'})
    payload['usage']['cost'] = 0.002
    wire = Wire(reply(payload))
    provider = make(OpenAICompatibleProvider, wire)
    answer = provider.complete(ModelRequest(USER, system='Be brief.', max_output_tokens=50))
    assert (answer.text, answer.model_id, answer.provider_id) == ('hi', 'vendor/model-1', 'openai_compatible')
    assert (answer.usage.input_tokens, answer.usage.output_tokens, answer.usage.cost_usd) == (5, 2, 0.002)
    request = wire.requests[0]
    assert str(request.url) == 'https://synthetic.invalid/v1/chat/completions'
    assert request.headers['authorization'] == f'Bearer {KEY}'
    assert 'openai-organization' not in request.headers and 'openai-project' not in request.headers
    assert wire.body() == {'model': 'synthetic', 'max_tokens': 50,
                           'messages': [{'role': 'system', 'content': 'Be brief.'},
                                        {'role': 'user', 'content': 'hello'}]}


def test_openai_transport_keeps_account_headers_and_uses_completion_tokens(monkeypatch):
    monkeypatch.setenv('OPENAI_ORG_ID', 'org-ambient')
    monkeypatch.setenv('OPENAI_PROJECT_ID', 'proj-ambient')
    wire = Wire(reply(completion({'content': 'hi'})),
                sse([{'id': 'c1', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'm',
                      'choices': [{'index': 0, 'delta': {'content': 'ok'}, 'finish_reason': 'stop'}]}, '[DONE]']))
    provider = make(OpenAIProvider, wire, base_url='')
    provider.complete(ModelRequest(USER, max_output_tokens=50))
    request = wire.requests[0]
    assert str(request.url) == 'https://api.openai.com/v1/chat/completions'
    assert request.headers['openai-organization'] == 'org-ambient'
    assert request.headers['openai-project'] == 'proj-ambient'
    assert wire.body()['max_completion_tokens'] == 50 and 'max_tokens' not in wire.body()
    provider.complete(ModelRequest(USER, stream=True))
    assert wire.body()['stream_options'] == {'include_usage': True}


def test_openai_compatible_tools_and_structured_output():
    call = {'id': 'call_1', 'type': 'function', 'function': {'name': 'echo', 'arguments': '{"nonce": "n"}'}}
    wire = Wire(reply(completion({'content': None, 'tool_calls': [call]}, 'tool_calls')),
                reply(completion({'content': '{"nonce": "n"}'})),
                reply(completion({'content': None, 'tool_calls': [dict(call, function={
                    'name': 'echo', 'arguments': '{not json'})]}, 'tool_calls')))
    provider = make(OpenAICompatibleProvider, wire)
    answer = provider.complete(ModelRequest(USER, tools=(ECHO,), require_tool=True))
    assert answer.stop_reason == 'tool_call' and answer.tool_calls[0].arguments == {'nonce': 'n'}
    body = wire.body()
    assert body['tool_choice'] == 'required'
    assert body['tools'] == [{'type': 'function', 'function': {'name': 'echo', 'description': 'Echo.',
                                                               'parameters': SCHEMA}}]
    assert provider.complete(ModelRequest(USER, output_schema=SCHEMA)).structured == {'nonce': 'n'}
    assert wire.body()['response_format'] == {'type': 'json_schema', 'json_schema': {
        'name': 'quati_output', 'schema': SCHEMA, 'strict': True}}
    assert error_of(provider.complete, ModelRequest(USER, tools=(ECHO,))) == ('OUTPUT_INVALID', 'TOOL_CALL_INVALID')


@pytest.mark.parametrize(('payload', 'expected'), [
    (completion({'content': 'x'}, 'length'), ('OUTPUT_INVALID', 'OUTPUT_TRUNCATED')),
    (completion({'content': 'x'}, 'content_filter'), ('OUTPUT_INVALID', 'MODEL_REFUSED')),
    (completion({'content': None, 'refusal': 'no'}), ('OUTPUT_INVALID', 'MODEL_REFUSED')),
    ({}, ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')),
    ({'choices': []}, ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')),
    (completion({'content': 'x'}, None), ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')),
    (completion({'content': 'x'}, 'vendor_specific'), ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')),
    (completion({'content': None, 'tool_calls': [{'id': 'c', 'type': 'function', 'function': {
        'name': 'echo', 'arguments': ''}}]}, 'tool_calls'), ('OUTPUT_INVALID', 'TOOL_CALL_INVALID')),
    (completion({'content': None, 'tool_calls': [{'id': 'c', 'type': 'function', 'function': {
        'name': 'echo', 'arguments': '[1]'}}]}, 'tool_calls'), ('OUTPUT_INVALID', 'TOOL_CALL_INVALID')),
    # Some gateways send content parts instead of a string; Quati does not guess how to join them.
    (completion({'content': [{'type': 'text', 'text': 'x'}]}), ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')),
])
def test_openai_compatible_unusable_answers(payload, expected):
    provider = make(OpenAICompatibleProvider, Wire(reply(payload)))
    assert error_of(provider.complete, ModelRequest(USER)) == expected


def chunk(delta, finish=None, **extra):
    return dict({'id': 'c1', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'vendor/model-1',
                 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}, **extra)


def test_openai_compatible_streaming():
    usage_only = {'id': 'c1', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'vendor/model-1',
                  'choices': [], 'usage': {'prompt_tokens': 5, 'completion_tokens': 2, 'total_tokens': 7}}
    fragment = lambda **function: {'index': 0, 'function': function}  # noqa: E731
    wire = Wire(sse([chunk({'role': 'assistant', 'content': ''}), chunk({'content': 'ab'}), chunk({'content': 'cd'}),
                     chunk({}, 'stop'), usage_only, '[DONE]']),
                sse([chunk({'tool_calls': [dict(fragment(name='echo', arguments='{"non'), id='call_1',
                                                type='function')]}),
                     chunk({'tool_calls': [fragment(arguments='ce": "n"}')]}), chunk({}, 'tool_calls'), '[DONE]']),
                sse([chunk({'content': 'ab'}), '[DONE]']),
                sse([chunk({'content': 'ab'}), chunk({'content': 'cd'}, 'stop'), '[DONE]']))
    provider = make(OpenAICompatibleProvider, wire)
    answer = provider.complete(ModelRequest(USER, stream=True))
    assert (answer.text, answer.chunk_count, answer.stop_reason, answer.model_id) == (
        'abcd', 2, 'end', 'vendor/model-1')
    assert answer.usage.input_tokens == 5
    assert wire.body()['stream'] is True and 'stream_options' not in wire.body()
    answer = provider.complete(ModelRequest(USER, tools=(ECHO,), stream=True))
    assert answer.tool_calls[0].name == 'echo' and answer.tool_calls[0].arguments == {'nonce': 'n'}
    # A stream that ends without a finish reason is an unusable answer, not a short one.
    assert error_of(provider.complete, ModelRequest(USER, stream=True)) == ('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
    ticks = iter([0.0, 99.0])
    provider._monotonic = lambda: next(ticks)
    assert error_of(provider.complete, ModelRequest(USER, stream=True, timeout_s=5)) == (
        'DEADLINE_EXCEEDED', 'DEADLINE_EXCEEDED')


def test_openai_compatible_stream_without_fragment_index_and_with_refusal():
    # Some gateways omit the index on the first tool-call fragment; it joins the same call, never a crash.
    wire = Wire(sse([chunk({'tool_calls': [{'id': 'call_1', 'type': 'function',
                                            'function': {'name': 'echo', 'arguments': '{"non'}}]}),
                     chunk({'tool_calls': [{'index': 0, 'function': {'arguments': 'ce": "n"}'}}]}),
                     chunk({}, 'tool_calls'), '[DONE]']),
                sse([chunk({'refusal': 'I will not'}), chunk({}, 'stop'), '[DONE]']),
                sse([chunk({'content': 'ab'}), chunk({'content': 'cd'}, 'vendor_specific'), '[DONE]']))
    provider = make(OpenAICompatibleProvider, wire)
    answer = provider.complete(ModelRequest(USER, tools=(ECHO,), stream=True))
    assert len(answer.tool_calls) == 1 and answer.tool_calls[0].arguments == {'nonce': 'n'}
    assert error_of(provider.complete, ModelRequest(USER, stream=True)) == ('OUTPUT_INVALID', 'MODEL_REFUSED')
    assert error_of(provider.complete, ModelRequest(USER, stream=True)) == ('TEMPORARILY_UNAVAILABLE',
                                                                             'UPSTREAM_ERROR')


# ----- vendor command-line transports --------------------------------------------------
class Runner:
    """Scripted child process: records the call and returns (returncode, stdout) or raises."""

    def __init__(self, *outcomes, write=None):
        self.outcomes = list(outcomes)
        self.calls = []
        self.write = write

    def __call__(self, argv, stdin_text, timeout_s, cwd, env):
        from pathlib import Path
        call = {'argv': argv, 'stdin': stdin_text, 'timeout_s': timeout_s, 'cwd': cwd, 'env': env}
        if '--system-prompt-file' in argv:
            # The prompt file lives only for the duration of the call, so it is captured now.
            path = argv[argv.index('--system-prompt-file') + 1]
            call['system_path'], call['system'] = path, Path(path).read_text(encoding='utf-8')
        self.calls.append(call)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        if self.write is not None and '-o' in argv:
            Path(argv[argv.index('-o') + 1]).write_text(self.write.pop(0), encoding='utf-8')
        return outcome


BASE_ENVIRON = {'SYNTHETIC_KEY': KEY, 'PATH': '/usr/bin', 'HOME': '/home/synthetic'}


def make_cli(cls, runner, environ=None, **changes):
    values = dict(allow_live=True, transport=cls.transport, api_key_env='SYNTHETIC_KEY')
    values.update(changes)
    return cls(ProviderConfig(**values), runner=runner, which=lambda name: f'/opt/bin/{name}',
               environ=dict(BASE_ENVIRON, **(environ or {})))


def claude_result(**changes):
    result = {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'hi', 'total_cost_usd': 0.0003,
              'usage': {'input_tokens': 2, 'cache_creation_input_tokens': 3, 'cache_read_input_tokens': 5,
                        'output_tokens': 7}, 'modelUsage': {'claude-haiku-test': {}}}
    result.update(changes)
    return 0, json.dumps(result)


def test_claude_cli_command_line_isolation_and_answer():
    runner = Runner(claude_result())
    provider = make_cli(ClaudeCliProvider, runner, max_usd_per_run=0.05)
    answer = provider.complete(ModelRequest(USER, system='Be brief.', timeout_s=30))
    assert (answer.text, answer.model_id, answer.provider_id) == ('hi', 'claude-haiku-test', 'claude_cli')
    assert (answer.usage.input_tokens, answer.usage.output_tokens, answer.usage.cost_usd) == (10, 7, 0.0003)
    call = runner.calls[0]
    argv = call['argv']
    assert argv[:2] == ['/opt/bin/claude', '-p']
    assert '--model=haiku' in argv and '--model' not in argv  # one token: a model id is never read as an option
    assert argv[argv.index('--tools') + 1] == ''  # every built-in tool disabled
    # Customizations off: no user/project/local settings, hooks, memory files, plugins or MCP servers.
    assert '--safe-mode' in argv and argv[argv.index('--setting-sources') + 1] == ''
    assert '--system-prompt' not in argv and call['system'] == 'Be brief.'
    assert not call['system_path'].startswith(call['cwd'])  # the prompt file is outside the model's directory
    assert argv[argv.index('--max-budget-usd') + 1] == '0.05'
    assert {'--no-session-persistence', '--strict-mcp-config', '--disable-slash-commands'} <= set(argv)
    assert '--bare' not in argv and '--json-schema' not in argv
    assert (call['stdin'], call['timeout_s']) == ('hello', 30)
    assert call['env'] == {'PATH': '/usr/bin', 'HOME': '/home/synthetic'}  # the Quati key never reaches the child
    assert KEY not in json.dumps(call['argv']) and '/quati-cli-' in call['cwd']
    import os
    assert not os.path.exists(call['cwd'])  # the scratch directory is removed after the call
    assert not os.path.exists(call['system_path'])


STRAY = {'ANTHROPIC_API_KEY': 'stray-1', 'ANTHROPIC_BASE_URL': 'https://redirect.invalid', 'OPENAI_API_KEY': 'stray-2',
         'OPENAI_BASE_URL': 'https://redirect.invalid', 'AWS_SECRET_ACCESS_KEY': 'stray-3', 'QUATI_API_KEY': 'stray-4',
         'GEMINI_API_KEY': 'stray-5', 'NODE_OPTIONS': '--require /tmp/x.js', 'LD_PRELOAD': '/tmp/x.so'}
KEPT = {'USER': 'u', 'LOGNAME': 'u', 'SHELL': '/bin/sh', 'LANG': 'C.UTF-8', 'LANGUAGE': 'en', 'LC_ALL': 'C.UTF-8',
        'LC_CTYPE': 'C.UTF-8', 'TERM': 'dumb', 'TMPDIR': '/tmp', 'TZ': 'UTC', 'XDG_CONFIG_HOME': '/x',
        'HTTPS_PROXY': 'http://proxy.invalid', 'https_proxy': 'http://proxy.invalid', 'HTTP_PROXY': 'h',
        'http_proxy': 'h', 'ALL_PROXY': 'a', 'all_proxy': 'a', 'NO_PROXY': 'n', 'no_proxy': 'n',
        'SSL_CERT_FILE': '/ca', 'SSL_CERT_DIR': '/cadir', 'NODE_EXTRA_CA_CERTS': '/ca.pem'}


@pytest.mark.parametrize(('cls', 'own'), [(ClaudeCliProvider, {'CLAUDE_CONFIG_DIR': '/c'}),
                                          (CodexCliProvider, {'CODEX_HOME': '/x'}), (GeminiCliProvider, {})])
def test_cli_child_environment_is_an_allow_list(cls, own):
    foreign = {'CLAUDE_CONFIG_DIR': '/c', 'CODEX_HOME': '/x'}
    outcome = (0, json.dumps({'response': 'hi'})) if cls is GeminiCliProvider else claude_result()
    runner = Runner(outcome, write=['hi'])
    make_cli(cls, runner, environ=dict(STRAY, **KEPT, **foreign)).complete(ModelRequest(USER))
    assert runner.calls[0]['env'] == dict({'PATH': '/usr/bin', 'HOME': '/home/synthetic'}, **KEPT, **own)


@pytest.mark.parametrize('cls', [ClaudeCliProvider, CodexCliProvider, GeminiCliProvider])
@pytest.mark.parametrize('model', ['--dangerously-skip-permissions', '-c', 'has space', 'semi;colon'])
def test_cli_option_shaped_model_is_rejected_before_any_process(cls, model):
    runner = Runner()
    provider = make_cli(cls, runner, model=model)
    assert error_of(provider.complete, ModelRequest(USER)) == ('NOT_CONFIGURED', 'MODEL_INVALID')
    assert runner.calls == []


def test_claude_cli_structured_output_and_tool_envelope():
    envelope = {'kind': 'tool_call', 'tool_name': 'echo', 'arguments_json': '{"nonce": "n"}', 'text': ''}
    runner = Runner(claude_result(result='', structured_output={'nonce': 'n'}),
                    claude_result(result='```json\n{"nonce": "m"}\n```', structured_output=None),
                    claude_result(result='', structured_output=envelope),
                    claude_result(result='Here: ' + json.dumps(dict(envelope, kind='final', text='done')) + ' ok',
                                  structured_output=None, total_cost_usd=None, usage=None, modelUsage=None))
    provider = make_cli(ClaudeCliProvider, runner, model='sonnet')
    assert provider.complete(ModelRequest(USER, output_schema=SCHEMA)).structured == {'nonce': 'n'}
    argv = runner.calls[0]['argv']
    assert json.loads(argv[argv.index('--json-schema') + 1]) == SCHEMA
    assert '--model=sonnet' in argv and '--max-budget-usd' not in argv
    assert 'precise assistant' in runner.calls[0]['system']
    assert provider.complete(ModelRequest(USER, output_schema=SCHEMA)).structured == {'nonce': 'm'}
    answer = provider.complete(ModelRequest((Message('user', 'a'), Message('assistant', 'b'), Message('user', 'c')),
                                            tools=(ECHO,), require_tool=True))
    assert answer.stop_reason == 'tool_call' and answer.tool_calls[0].arguments == {'nonce': 'n'}
    call = runner.calls[2]
    sent = json.loads(call['argv'][call['argv'].index('--json-schema') + 1])
    assert sent == cli_module.envelope_schema(ModelRequest(USER, tools=(ECHO,), require_tool=True))
    assert sent['properties']['kind']['enum'] == ['tool_call']
    assert sent['properties']['tool_name']['enum'] == ['echo']
    optional = cli_module.envelope_schema(ModelRequest(USER, tools=(ECHO,)))
    assert optional['properties']['kind']['enum'] == ['tool_call', 'final']
    assert optional['properties']['tool_name']['enum'] == ['echo', '']
    assert sent['required'] == ['kind', 'tool_name', 'arguments_json', 'text']
    assert sent['additionalProperties'] is False
    system = call['system']
    assert 'You must choose kind "tool_call"' in system and '"name": "echo"' in system
    assert call['stdin'] == 'USER:\na\n\nASSISTANT:\nb\n\nUSER:\nc'
    final = provider.complete(ModelRequest(USER, tools=(ECHO,)))
    assert (final.text, final.tool_calls, final.model_id, final.usage.cost_usd) == ('done', (), '', None)
    assert (final.usage.input_tokens, final.usage.output_tokens) == (None, None)  # absent usage is unknown, not 0
    assert 'or kind "final"' in runner.calls[3]['system']


@pytest.mark.parametrize(('outcome', 'expected'), [
    ((1, ''), ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    ((0, 'not json'), ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    ((0, '[1]'), ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    (claude_result(is_error=True), ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    (claude_result(subtype='error_max_budget_usd'), ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    (claude_result(type='system'), ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    (TimeoutError(), ('DEADLINE_EXCEEDED', 'DEADLINE_EXCEEDED')),
    (OSError('exec format error'), ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
])
def test_claude_cli_failures(outcome, expected):
    assert error_of(make_cli(ClaudeCliProvider, Runner(outcome)).complete, ModelRequest(USER)) == expected


@pytest.mark.parametrize(('result', 'expected'), [
    ('no json here', ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    ('{"kind": "other"}', ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    ('{"kind": "final", "text": 5}', ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    ('[1, 2]', ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')),
    ('{"kind": "tool_call", "tool_name": "echo", "arguments_json": "{bad"}', ('OUTPUT_INVALID', 'TOOL_CALL_INVALID')),
    ('{"kind": "tool_call", "tool_name": "echo", "arguments_json": 5}', ('OUTPUT_INVALID', 'TOOL_CALL_INVALID')),
    ('{"kind": "tool_call", "tool_name": 7, "arguments_json": "{}"}', ('OUTPUT_INVALID', 'TOOL_CALL_INVALID')),
    ('{"kind": "tool_call", "tool_name": "echo", "arguments_json": ""}', ('OUTPUT_INVALID', 'TOOL_CALL_INVALID')),
])
def test_cli_envelope_rejections(result, expected):
    provider = make_cli(ClaudeCliProvider, Runner(claude_result(result=result, structured_output=None)))
    assert error_of(provider.complete, ModelRequest(USER, tools=(ECHO,))) == expected


def test_cli_unparsable_structured_text_is_schema_invalid_and_missing_executable_blocks():
    provider = make_cli(ClaudeCliProvider, Runner(claude_result(result='plain', structured_output=None)))
    assert error_of(provider.complete, ModelRequest(USER, output_schema=SCHEMA)) == (
        'OUTPUT_INVALID', 'SCHEMA_INVALID_OUTPUT')
    assert error_of(provider.complete, ModelRequest(USER, stream=True)) == ('UNSUPPORTED', 'STREAMING_UNSUPPORTED')
    runner = Runner()
    present = iter(['/opt/bin/claude', None])
    gone = ClaudeCliProvider(ProviderConfig(allow_live=True, transport='claude_cli'), runner=runner,
                             which=lambda name: next(present), environ={})
    assert error_of(gone.complete, ModelRequest(USER)) == ('NOT_CONFIGURED', 'CLI_NOT_FOUND')
    assert runner.calls == []


def test_codex_cli_read_only_sandbox_and_output_file():
    runner = Runner((0, 'progress noise'), (0, ''), (0, ''), (0, ''), write=['hi', '{"nonce": "n"}', '  ', None])
    provider = make_cli(CodexCliProvider, runner)
    answer = provider.complete(ModelRequest(USER, system='Be brief.'))
    assert (answer.text, answer.model_id, answer.usage.cost_usd) == ('hi', '', None)
    call = runner.calls[0]
    argv = call['argv']
    assert argv[:2] == ['/opt/bin/codex', 'exec'] and argv[-1] == '-'
    assert argv[argv.index('--sandbox') + 1] == 'read-only'
    assert {'--skip-git-repo-check', '--ephemeral', '--ignore-user-config'} <= set(argv)
    assert argv[argv.index('--cd') + 1] == call['cwd'] and '-m' not in argv and '--output-schema' not in argv
    assert call['stdin'] == 'Be brief.\n\nhello' and 'SYNTHETIC_KEY' not in call['env']
    provider = make_cli(CodexCliProvider, runner, model='gpt-test')
    runner.outcomes, runner.write = [(0, '')], ['{"nonce": "n"}']
    answer = provider.complete(ModelRequest(USER, output_schema=SCHEMA))
    # S00-T04 fix round 3 (LOG-0029 root decision, supersedes the P2-3 expectation ''): codex exec --json
    # names no model, so an explicitly configured model is the requested identity; with no configured
    # model (the first call above) the id stays ''. tests/unit/test_s00_t04_fixes3.py covers both.
    assert answer.structured == {'nonce': 'n'} and answer.model_id == 'gpt-test'
    assert provider.model_identity_source() == 'requested'
    argv = runner.calls[1]['argv']
    assert argv[argv.index('-m') + 1] == 'gpt-test' and argv[argv.index('--output-schema') + 1].endswith('schema.json')
    assert runner.calls[1]['stdin'] == 'hello'
    runner.outcomes, runner.write = [(0, '')], ['  ']
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')
    runner.outcomes, runner.write = [(0, '')], None  # no output file written at all
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')


def test_gemini_cli_plan_mode_and_prompted_schema():
    runner = Runner((0, json.dumps({'response': 'hi'})), (0, json.dumps({'response': '{"nonce": "n"}'})),
                    (0, json.dumps({'error': {'message': 'quota'}, 'response': 'x'})), (0, json.dumps({'stats': {}})))
    provider = make_cli(GeminiCliProvider, runner)
    assert provider.complete(ModelRequest(USER)).text == 'hi'
    argv = runner.calls[0]['argv']
    assert argv[0] == '/opt/bin/gemini' and argv[argv.index('--approval-mode') + 1] == 'plan'
    assert argv[argv.index('-o') + 1] == 'json' and '-m' not in argv
    assert runner.calls[0]['stdin'] == 'hello'
    provider = make_cli(GeminiCliProvider, runner, model='gemini-test')
    answer = provider.complete(ModelRequest(USER, system='Be brief.', output_schema=SCHEMA))
    assert answer.structured == {'nonce': 'n'} and answer.model_id == 'gemini-test'
    call = runner.calls[1]
    assert call['argv'][call['argv'].index('-m') + 1] == 'gemini-test'
    assert call['stdin'].startswith('Be brief.\n\nReply with exactly one JSON object')
    assert json.dumps(SCHEMA, sort_keys=True) in call['stdin'] and call['stdin'].endswith('\n\nhello')
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')
    assert error_of(provider.complete, ModelRequest(USER)) == ('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')


def test_extract_json_variants():
    assert cli_module.extract_json(' {"a": 1} ') == {'a': 1}
    assert cli_module.extract_json('```json\n{"a": 1}\n```') == {'a': 1}
    assert cli_module.extract_json('Sure: {"a": {"b": 2}} done') == {'a': {'b': 2}}
    for bad in ('```', 'nothing', '} {', '{broken}'):
        with pytest.raises(ValueError):
            cli_module.extract_json(bad)


def test_run_process_passes_stdin_environment_and_directory(tmp_path):
    script = ('import os, sys; sys.stderr.write("noise"); '
              'print(sys.stdin.read() + "|" + os.environ.get("MARK", "") + "|" + os.getcwd())')
    code, out = cli_module.run_process([sys.executable, '-c', script], 'in', 30, str(tmp_path), {'MARK': 'm'})
    assert (code, out.strip()) == (0, f'in|m|{tmp_path}')
    assert cli_module.run_process([sys.executable, '-c', 'import sys; sys.exit(3)'], '', 30, str(tmp_path), {})[0] == 3


def test_run_process_kills_the_process_group_at_the_deadline(tmp_path, monkeypatch):
    killed, waits, never_closes, streams = [], [], False, []

    class Stuck:
        pid = 4242
        returncode = None

        def __init__(self, *args, **kwargs):
            import io
            self.kwargs = kwargs
            self.calls = 0
            self.stdin, self.stdout = io.StringIO(), io.StringIO()
            streams.append(self)

        def communicate(self, *args, **kwargs):
            self.calls += 1
            waits.append(kwargs.get('timeout'))
            if self.calls == 1 or never_closes:
                raise subprocess.TimeoutExpired('x', 1)
            return '', None

        def kill(self):
            killed.append('kill')

    monkeypatch.setattr(cli_module.subprocess, 'Popen', Stuck)
    monkeypatch.setattr(cli_module.os, 'killpg', lambda pid, sig: killed.append(('killpg', pid)))
    with pytest.raises(TimeoutError):
        cli_module.run_process(['x'], '', 1, str(tmp_path), {})
    assert killed == [('killpg', 4242)]
    assert waits == [1, cli_module.KILL_GRACE_S]  # the pipes are drained for a bounded grace only

    def refuse(pid, sig):
        raise ProcessLookupError

    monkeypatch.setattr(cli_module.os, 'killpg', refuse)
    with pytest.raises(TimeoutError):
        cli_module.run_process(['x'], '', 1, str(tmp_path), {})
    assert killed[-1] == 'kill'

    # A descendant that escaped the group keeps the pipes open: Quati abandons them after the grace.
    never_closes = True
    with pytest.raises(TimeoutError) as caught:
        cli_module.run_process(['x'], '', 1, str(tmp_path), {})
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert streams[-1].stdin.closed and streams[-1].stdout.closed
    assert not streams[0].stdin.closed  # pipes that closed within the grace are left to communicate()


def test_run_process_abandons_pipes_held_by_an_escaped_descendant(tmp_path, monkeypatch):
    import os
    import signal
    import time
    pid_file = tmp_path / 'grandchild.pid'
    script = ('import subprocess, sys\n'
              f'child = subprocess.Popen(["sleep", "60"], start_new_session=True)\n'
              f'open({str(pid_file)!r}, "w").write(str(child.pid))\n'
              'sys.stdout.flush()\n'
              'import time; time.sleep(60)\n')
    monkeypatch.setattr(cli_module, 'KILL_GRACE_S', 0.5)
    started = time.monotonic()
    try:
        with pytest.raises(TimeoutError):
            cli_module.run_process([sys.executable, '-c', script], '', 1, str(tmp_path), {'PATH': '/usr/bin:/bin'})
        assert time.monotonic() - started < 10
    finally:
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGKILL)
            except (OSError, ValueError):
                pass


def test_remaining_adapter_branches():
    # Optional tool use on Anthropic adds no steering text.
    wire = Wire(reply(anthropic_message([{'type': 'text', 'text': 'hi'}])))
    assert make(AnthropicProvider, wire).complete(ModelRequest(USER, tools=(ECHO,))).text == 'hi'
    assert 'system' not in wire.body() and len(wire.body()['tools']) == 1
    # A stream chunk with no delta, and a tool-call fragment with no function part, are skipped.
    no_delta = {'id': 'c1', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'm',
                'choices': [{'index': 0, 'delta': None, 'finish_reason': None}]}
    wire = Wire(sse([no_delta, chunk({'tool_calls': [{'index': 0}]}),
                     chunk({'tool_calls': [{'index': 0, 'function': {'name': 'echo', 'arguments': '{"nonce": "n"}'}}]}),
                     chunk({}, 'tool_calls'), '[DONE]']))
    answer = make(OpenAICompatibleProvider, wire).complete(ModelRequest(USER, tools=(ECHO,), stream=True))
    assert answer.tool_calls[0].arguments == {'nonce': 'n'}

    # A vendor subclass that forgets a hook fails closed as an adapter fault, never as a fake answer.
    class NoArgv(cli_module.CliProvider):
        transport = 'incomplete_cli'
        executable = 'incomplete'

    class NoRead(NoArgv):
        def _argv(self, *arguments):
            return ['incomplete']

    for cls in (NoArgv, NoRead):
        assert error_of(make_cli(cls, Runner((0, ''))).complete, ModelRequest(USER)) == (
            'INTERNAL_ERROR', 'ADAPTER_FAULT')
