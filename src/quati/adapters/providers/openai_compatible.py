"""OpenAI-compatible Chat Completions endpoints (OpenRouter and others) and OpenAI itself.

A new OpenAI-compatible vendor is a small subclass: set ``transport``, ``default_base_url``
and, when the vendor differs, ``token_limit_field``; then decorate it with ``@register``.
"""

from dataclasses import replace
import json

from quati.adapters.providers._sdk import drop_optional_nulls, map_error, parse_arguments, strict_schema
from quati.application.providers import ModelResponse, Provider, ProviderError, ToolCall, Usage, register

FINISH_REASONS = {'stop': 'end', 'tool_calls': 'tool_call', 'function_call': 'tool_call', 'length': 'length',
                  'content_filter': 'refusal'}


@register
class OpenAICompatibleProvider(Provider):
    transport = 'openai_compatible'
    needs_endpoint = True
    sdk_module = 'openai'
    token_limit_field = 'max_tokens'
    send_account_headers = False
    stream_usage = False

    def __init__(self, config, *, http_transport=None, **dependencies):
        super().__init__(config, **dependencies)
        self._http_transport = http_transport

    def _client(self, sdk, timeout_s):
        # Explicit key and base URL; OpenAI account headers taken from the environment are
        # withheld from third-party endpoints.
        headers = None if self.send_account_headers else {'OpenAI-Organization': sdk.Omit(),
                                                          'OpenAI-Project': sdk.Omit()}
        return sdk.OpenAI(api_key=self.secret(), base_url=self.base_url(), max_retries=0, timeout=timeout_s,
                          default_headers=headers,
                          http_client=sdk.DefaultHttpx2Client(follow_redirects=False, timeout=timeout_s,
                                                              transport=self._http_transport))

    def _arguments(self, request):
        messages = [{'role': message.role, 'content': message.content} for message in request.messages]
        if request.system:
            messages.insert(0, {'role': 'system', 'content': request.system})
        arguments = {'model': self.model(), 'messages': messages,
                     self.token_limit_field: request.max_output_tokens}
        if request.tools:
            arguments['tools'] = [{'type': 'function', 'function': {
                'name': tool.name, 'description': tool.description, 'parameters': tool.input_schema}}
                for tool in request.tools]
            if request.require_tool:
                arguments['tool_choice'] = 'required'
        if request.output_schema is not None:
            arguments['response_format'] = {'type': 'json_schema', 'json_schema': {
                'name': 'quati_output', 'schema': strict_schema(request.output_schema)[0], 'strict': True}}
        if request.stream:
            arguments['stream'] = True
            if self.stream_usage:
                arguments['stream_options'] = {'include_usage': True}
        return arguments

    def _complete(self, request):
        import openai as sdk
        arguments = self._arguments(request)
        try:
            with self._client(sdk, request.timeout_s) as client:
                result = client.chat.completions.create(**arguments)
                response = self._collect(result, request.timeout_s) if request.stream else self._response(result)
                return self._normalized(request, response)
        except ProviderError:
            raise
        except Exception as exc:
            failure = map_error(sdk, exc)
        raise failure  # raised outside the except block: no upstream exception (or its headers) is attached

    @staticmethod
    def _normalized(request, response):
        """LOG-0032 S2: strict mode returns optional fields as null; restore the original schema shape."""
        if request.output_schema is None or response.tool_calls:
            return response
        try:
            structured = json.loads(response.text)
        except ValueError:
            return response   # the base class reports unparseable output
        return replace(response, structured=drop_optional_nulls(structured, strict_schema(request.output_schema)[1]))

    def _collect(self, stream, timeout_s):
        started, chunks = self._monotonic(), 0
        text, fragments, finish, usage, model, refused, last = [], {}, None, None, '', False, 0
        for chunk in stream:
            if self._monotonic() - started > timeout_s:
                raise ProviderError('DEADLINE_EXCEEDED')
            model = getattr(chunk, 'model', None) or model
            usage = getattr(chunk, 'usage', None) or usage
            for choice in getattr(chunk, 'choices', None) or ():
                finish = choice.finish_reason or finish
                delta = choice.delta
                if delta is None:
                    continue
                if delta.content:
                    text.append(delta.content)
                    chunks += 1
                refused = refused or bool(getattr(delta, 'refusal', None))
                for part in delta.tool_calls or ():
                    # Some gateways omit the fragment index; such a fragment continues the last call.
                    index = getattr(part, 'index', None)
                    last = index if isinstance(index, int) else last
                    slot = fragments.setdefault(last, {'name': '', 'arguments': ''})
                    if part.function is not None:
                        slot['name'] += part.function.name or ''
                        slot['arguments'] += part.function.arguments or ''
        if finish is None:
            raise ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
        calls = tuple(_tool_call(slot['name'], slot['arguments']) for _, slot in sorted(fragments.items()))
        return ModelResponse(text=''.join(text), tool_calls=calls, usage=_usage(usage), model_id=model,
                             stop_reason='refusal' if refused else FINISH_REASONS.get(finish, 'other'),
                             chunk_count=chunks)

    @staticmethod
    def _response(completion):
        choices = getattr(completion, 'choices', None)
        if not choices or choices[0].message is None or choices[0].finish_reason is None:
            raise ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
        message = choices[0].message
        calls = tuple(_tool_call(call.function.name, call.function.arguments)
                      for call in message.tool_calls or () if getattr(call, 'function', None) is not None)
        stop = 'refusal' if getattr(message, 'refusal', None) else FINISH_REASONS.get(choices[0].finish_reason, 'other')
        content = message.content
        if content is not None and not isinstance(content, str):
            raise ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
        return ModelResponse(text=content or '', tool_calls=calls,
                             usage=_usage(getattr(completion, 'usage', None)),
                             model_id=getattr(completion, 'model', None) or '', stop_reason=stop)


def _tool_call(name, arguments):
    return ToolCall(name or '', parse_arguments(arguments))


def _usage(usage):
    if usage is None:
        return Usage()
    cost = getattr(usage, 'cost', None)
    return Usage(getattr(usage, 'prompt_tokens', None), getattr(usage, 'completion_tokens', None),
                 float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None)


@register
class OpenAIProvider(OpenAICompatibleProvider):
    transport = 'openai'
    needs_endpoint = False
    default_base_url = 'https://api.openai.com/v1'
    token_limit_field = 'max_completion_tokens'
    send_account_headers = True
    stream_usage = True
