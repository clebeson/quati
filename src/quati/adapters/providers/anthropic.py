"""Claude through the official Anthropic SDK (Messages API)."""
from quati.adapters.providers._sdk import TOOL_STEERING, map_error
from quati.application.providers import ModelResponse, Provider, ProviderError, ToolCall, Usage, register

STOP_REASONS = {'end_turn': 'end', 'stop_sequence': 'end', 'tool_use': 'tool_call', 'max_tokens': 'length',
                'model_context_window_exceeded': 'length', 'refusal': 'refusal'}


@register
class AnthropicProvider(Provider):
    transport = 'anthropic'
    default_model = 'claude-haiku-5-5'
    default_base_url = 'https://api.anthropic.com'
    sdk_module = 'anthropic'

    def __init__(self, config, *, http_transport=None, **dependencies):
        super().__init__(config, **dependencies)
        self._http_transport = http_transport

    def _client(self, sdk, timeout_s):
        # Explicit key and base URL: SDK environment fallbacks cannot redirect the call.
        return sdk.Anthropic(api_key=self.secret(), base_url=self.base_url(), max_retries=0, timeout=timeout_s,
                             http_client=sdk.DefaultHttpxClient(follow_redirects=False, timeout=timeout_s,
                                                                transport=self._http_transport))

    def _arguments(self, request):
        system = request.system
        arguments = {'model': self.model(), 'max_tokens': request.max_output_tokens,
                     'messages': [{'role': message.role, 'content': message.content} for message in request.messages]}
        if request.tools:
            arguments['tools'] = [{'name': tool.name, 'description': tool.description,
                                   'input_schema': tool.input_schema} for tool in request.tools]
            if request.require_tool:
                system = f'{system}\n\n{TOOL_STEERING}'.strip()
        if request.output_schema is not None:
            arguments['output_config'] = {'format': {'type': 'json_schema', 'schema': request.output_schema}}
        if system:
            arguments['system'] = system
        return arguments

    def _complete(self, request):
        import anthropic as sdk
        arguments = self._arguments(request)
        chunks = 1
        try:
            with self._client(sdk, request.timeout_s) as client:
                if request.stream:
                    started, chunks = self._monotonic(), 0
                    with client.messages.stream(**arguments) as stream:
                        for _ in stream.text_stream:
                            chunks += 1
                            if self._monotonic() - started > request.timeout_s:
                                raise ProviderError('DEADLINE_EXCEEDED')
                        message = stream.get_final_message()
                else:
                    message = client.messages.create(**arguments)
        except ProviderError:
            raise
        except Exception as exc:
            failure = map_error(sdk, exc)
        else:
            return self._response(message, chunks)
        raise failure  # raised outside the except block: no upstream exception (or its headers) is attached

    @staticmethod
    def _response(message, chunks):
        content, stop = getattr(message, 'content', None), getattr(message, 'stop_reason', None)
        if not isinstance(content, list) or stop is None:
            raise ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
        text = ''.join(block.text for block in content if block.type == 'text')
        calls = tuple(ToolCall(block.name, block.input) for block in content if block.type == 'tool_use')
        usage = getattr(message, 'usage', None)
        tokens_in = None if usage is None else sum(
            getattr(usage, name, None) or 0
            for name in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'))
        return ModelResponse(text=text, tool_calls=calls,
                             usage=Usage(tokens_in, getattr(usage, 'output_tokens', None)),
                             model_id=getattr(message, 'model', None) or '',
                             stop_reason=STOP_REASONS.get(stop, 'other'), chunk_count=chunks)
