"""Vendor command-line transports: Claude Code, Codex CLI and Gemini CLI.

Quati holds no key for these transports. It starts the vendor's own executable, which
authenticates itself; Quati never reads, copies or forwards a vendor sign-in file. The
vendor's built-in tools are disabled or sandboxed read-only, the child runs in an empty
temporary directory, and tool calls travel as a JSON envelope that Quati validates.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile

from quati.adapters.providers._sdk import drop_optional_nulls, parse_arguments, strict_schema
from quati.application.providers import ModelResponse, Provider, ProviderError, ToolCall, Usage, register

KILL_GRACE_S = 5  # M17: after the kill, wait at most this long for the pipes to close, then abandon them
DEFAULT_SYSTEM = 'You are a precise assistant. Answer only what is asked.'
# M17: the child environment is an allow-list, never a copy of Quati's environment.
CHILD_ENV_NAMES = frozenset({
    'PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'LANGUAGE', 'TERM', 'TMPDIR', 'TZ',
    'HTTPS_PROXY', 'https_proxy', 'HTTP_PROXY', 'http_proxy', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy',
    'SSL_CERT_FILE', 'SSL_CERT_DIR', 'NODE_EXTRA_CA_CERTS'})
CHILD_ENV_PREFIXES = ('LC_', 'XDG_')


def envelope_schema(request):
    """Schema of the tool-call envelope, narrowed to this request's tools and tool requirement."""
    names = [tool.name for tool in request.tools]
    return {
        'type': 'object',
        'properties': {
            'kind': {'type': 'string', 'enum': ['tool_call'] if request.require_tool else ['tool_call', 'final']},
            'tool_name': {'type': 'string', 'enum': names if request.require_tool else names + ['']},
            'arguments_json': {'type': 'string'}, 'text': {'type': 'string'}},
        'required': ['kind', 'tool_name', 'arguments_json', 'text'], 'additionalProperties': False}


def envelope_arguments(encoded):
    """Decode an envelope's tool arguments without over-strictness on their encoding.

    Accepted: a JSON-encoded object (the declared form), an object already decoded by a lenient
    text extraction, or one extra level of JSON string encoding (a model that JSON-encodes the
    already-encoded string). Anything else is TOOL_CALL_INVALID. The values are never altered.
    """
    if isinstance(encoded, dict):
        return encoded
    try:
        return parse_arguments(encoded)
    except ProviderError:
        try:
            inner = json.loads(encoded) if isinstance(encoded, str) else None
        except ValueError:
            inner = None
        if not isinstance(inner, str):
            raise
        return parse_arguments(inner)


def run_process(argv, stdin_text, timeout_s, cwd, env):
    """Run one child process; return (returncode, stdout). Raise TimeoutError past the deadline."""
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               cwd=cwd, env=env, text=True, encoding='utf-8', errors='replace',
                               start_new_session=True)
    try:
        stdout, _ = process.communicate(stdin_text, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        pass  # handled below, outside the except block, so the TimeoutError carries no context
    else:
        return process.returncode, stdout
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        process.kill()
    try:
        process.communicate(timeout=KILL_GRACE_S)
    except subprocess.TimeoutExpired:
        # A descendant that left the process group still holds the pipes: abandon them.
        process.stdin.close()
        process.stdout.close()
    raise TimeoutError


def extract_json(text):
    """Parse a JSON value from model text, tolerating a Markdown fence or surrounding prose."""
    candidate = text.strip()
    if candidate.startswith('```'):
        candidate = candidate.split('\n', 1)[1] if '\n' in candidate else ''
        candidate = candidate.rsplit('```', 1)[0].strip()
    try:
        return json.loads(candidate)
    except ValueError:
        start, end = candidate.find('{'), candidate.rfind('}')
        if start < 0 or end <= start:
            raise
        return json.loads(candidate[start:end + 1])


def codex_model_id(stdout):
    """Model id reported in Codex ``exec --json`` events; '' when no event names one (never the configured name)."""
    for line in (stdout or '').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        for holder in (event, *(event.get(name) for name in ('msg', 'payload', 'session', 'turn_context'))):
            model = holder.get('model') if isinstance(holder, dict) else None
            if isinstance(model, str) and model:
                return model
    return ''


def _error_fields(error):
    """(code, status) found in an error object or in a JSON-encoded upstream body; never its message."""
    code = status = None
    holders = [error]
    message = error.get('message')
    if isinstance(message, str):
        try:
            decoded = json.loads(message)
        except ValueError:
            decoded = None
        if isinstance(decoded, dict):
            holders += [decoded, decoded.get('error')]
    for holder in holders:
        if isinstance(holder, dict):
            code = code if code is not None else (holder.get('code') if isinstance(holder.get('code'), str) else None)
            value = holder.get('status')
            status = status if status is not None else (value if isinstance(value, int) and
                                                         not isinstance(value, bool) else None)
    schema_hint = isinstance(message, str) and 'invalid_json_schema' in message
    return code, status, schema_hint


def codex_failure(stdout):
    """LOG-0032 S3: map a Codex ``turn.failed`` or ``error`` event to a typed ProviderError (None if absent).

    Only the upstream code and HTTP status are read; the upstream message text never enters the error.
    """
    failure = None
    for line in (stdout or '').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get('type') not in ('turn.failed', 'error'):
            continue
        error = event.get('error') if isinstance(event.get('error'), dict) else event
        code, status, schema_hint = _error_fields(error)
        if status is None and isinstance(event.get('status'), int):
            status = event['status']
        if code == 'invalid_json_schema' or schema_hint:
            return ProviderError('UNSUPPORTED', 'SCHEMA_REJECTED')
        failure = _status_failure(status) if failure is None or status is not None else failure
    return failure


def _status_failure(status):
    if status == 401:
        return ProviderError('UNAUTHENTICATED')
    if status in (402, 403):
        return ProviderError('FORBIDDEN')
    if status == 404:
        return ProviderError('NOT_FOUND', 'MODEL_NOT_FOUND')
    if status == 429:
        return ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED')
    if isinstance(status, int) and 400 <= status < 500 and status != 408:
        return ProviderError('UNSUPPORTED', 'REQUEST_REJECTED')
    if isinstance(status, int) and status >= 500 or status == 408:
        return ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
    return ProviderError('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')


def codex_usage(stdout):
    """Token usage from the last Codex ``turn.completed`` event; cost is never reported (stays None)."""
    usage = Usage()
    for line in (stdout or '').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get('type') == 'turn.completed' and isinstance(event.get('usage'), dict):
            counts = event['usage']
            usage = Usage(*(counts.get(name) if isinstance(counts.get(name), int) else None
                            for name in ('input_tokens', 'output_tokens')))
    return usage


class CliProvider(Provider):
    """Base for vendor executables. Subclasses build the command line and read the output."""

    needs_secret = False
    takes_endpoint = False
    needs_model = False
    supports_streaming = False
    native_schema = True
    child_env_extra = ()  # vendor-specific variables (for example a config directory) also passed through

    def __init__(self, config, *, runner=run_process, **dependencies):
        super().__init__(config, **dependencies)
        self._runner = runner

    def executable_identity(self):
        """Resolved path, size and modification time of the vendor executable (bound into the config hash).

        The file is not executed and not hashed (vendor executables are hundreds of megabytes); an
        upgrade changes the resolved path, size or modification time and so invalidates measured reports.
        """
        path = self._which(self.executable)
        if not path:
            return {'name': self.executable, 'path': None, 'realpath': None, 'size': None, 'mtime_ns': None}
        realpath = os.path.realpath(path)
        try:
            stat = os.stat(realpath)
        except OSError:
            return {'name': self.executable, 'path': path, 'realpath': realpath, 'size': None, 'mtime_ns': None}
        return {'name': self.executable, 'path': path, 'realpath': realpath, 'size': stat.st_size,
                'mtime_ns': stat.st_mtime_ns}

    # ----- vendor hooks ------------------------------------------------------------
    def _argv(self, executable, request, system, schema_path, output_path, cwd):
        raise NotImplementedError

    def _prepare(self, io_dir, system):
        """Write per-call input files into the private I/O directory (outside the model's directory)."""

    def _stdin(self, request, system):
        return self._transcript(request)

    def _read(self, stdout, output_path):
        """Return (text, structured, usage, model_id) or raise ProviderError CLI_FAILED."""
        raise NotImplementedError

    # ----- shared mechanics --------------------------------------------------------
    @staticmethod
    def _transcript(request):
        if len(request.messages) == 1:
            return request.messages[0].content
        return '\n\n'.join(f'{message.role.upper()}:\n{message.content}' for message in request.messages)

    @staticmethod
    def _tool_instructions(request):
        tools = [{'name': tool.name, 'description': tool.description, 'input_schema': tool.input_schema}
                 for tool in request.tools]
        rule = ('You must choose kind "tool_call".' if request.require_tool
                else 'Choose kind "tool_call" to call a tool or kind "final" to answer.')
        # R1 (T05 gate run): a negative opener ("You cannot run tools yourself") next to the disabled vendor
        # tools led the model to tell the user that the tools were unavailable. State the protocol positively.
        return ('Quati runs the tools listed below on your behalf; they are available in this conversation. To use '
                'a tool, reply with exactly one JSON object and nothing else, with the string fields kind, '
                'tool_name, arguments_json and text. For kind "tool_call", tool_name is one of the tools below, '
                'arguments_json is a JSON-encoded object matching that tool\'s input_schema and text is empty; '
                'Quati runs the tool and sends you its result. For kind "final", text is your answer, written in '
                "the language of the user's request, and tool_name and arguments_json are empty strings. "
                f'{rule}\nTools:\n{json.dumps(tools, sort_keys=True)}')

    def _system(self, request, schema):
        parts = [request.system] if request.system else []
        if request.tools:
            parts.append(self._tool_instructions(request))
        elif schema is not None and not self.native_schema:
            parts.append('Reply with exactly one JSON object and nothing else, matching this JSON Schema:\n'
                         + json.dumps(schema, sort_keys=True))
        return '\n\n'.join(parts)

    def _rendered(self, request):
        schema = envelope_schema(request) if request.tools else request.output_schema
        return schema, self._system(request, schema)

    def model_visible(self, request):
        """The exact system text and stdin this transport sends the vendor CLI for ``request`` (R5 evidence)."""
        _schema, system = self._rendered(request)
        return {'system': system, 'stdin': self._stdin(request, system)}

    def _child_environment(self):
        # Allow-list only: keys, endpoint redirects, preload hooks and Quati's own secrets never reach the child.
        return {name: value for name, value in self.environ.items()
                if name in CHILD_ENV_NAMES or name.startswith(CHILD_ENV_PREFIXES) or name in self.child_env_extra}

    def _complete(self, request):
        executable = self._which(self.executable)
        if not executable:
            raise ProviderError('NOT_CONFIGURED', 'CLI_NOT_FOUND')
        schema, system = self._rendered(request)
        with tempfile.TemporaryDirectory(prefix='quati-cli-') as root:
            cwd, io_dir = Path(root, 'cwd'), Path(root, 'io')
            cwd.mkdir(mode=0o700)
            io_dir.mkdir(mode=0o700)
            schema_path = None
            if schema is not None and self.native_schema:
                schema_path = io_dir / 'schema.json'
                schema_path.write_text(json.dumps(self._native_schema(schema)), encoding='utf-8')
            output_path = io_dir / 'output.txt'
            self._prepare(io_dir, system)
            argv = self._argv(executable, request, system, schema_path, output_path, cwd)
            try:
                returncode, stdout = self._runner(argv, self._stdin(request, system), request.timeout_s,
                                                  str(cwd), self._child_environment())
            except TimeoutError:
                raise ProviderError('DEADLINE_EXCEEDED') from None
            except OSError:
                raise ProviderError('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED') from None
            failure = self._event_failure(stdout)
            if failure is not None:
                raise failure
            if returncode != 0:
                raise ProviderError('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')
            try:
                text, structured, usage, model_id = self._read(stdout, output_path)
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                raise ProviderError('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED') from None
        if request.tools:
            return self._from_envelope(text, structured, usage, model_id)
        if request.output_schema is not None and structured is None:
            try:
                structured = extract_json(text)
            except ValueError:
                structured = None
        if structured is not None and self.strict_schemas:
            structured = drop_optional_nulls(structured, strict_schema(request.output_schema)[1])
        return ModelResponse(text=text, structured=structured, usage=usage, model_id=model_id)

    strict_schemas = False  # True: the executable enforces OpenAI-style strict structured outputs

    def _native_schema(self, schema):
        """The schema file given to the executable (strict form when the vendor requires it)."""
        return strict_schema(schema)[0] if self.strict_schemas else schema

    def _event_failure(self, stdout):
        """A typed failure reported in the executable's event stream, or None."""
        return None

    def _from_envelope(self, text, structured, usage, model_id):
        envelope = structured
        if not isinstance(envelope, dict):
            try:
                envelope = extract_json(text)
            except ValueError:
                envelope = None
        kind = envelope.get('kind') if isinstance(envelope, dict) else None
        if kind == 'final' and isinstance(envelope.get('text'), str):
            return ModelResponse(text=envelope['text'], usage=usage, model_id=model_id)
        if kind != 'tool_call':
            self._note_reply('UNPARSEABLE_REPLY', text if structured is None else json.dumps(structured, default=str))
            raise ProviderError('TEMPORARILY_UNAVAILABLE', 'CLI_FAILED')
        try:
            arguments = envelope_arguments(envelope.get('arguments_json'))
        except ProviderError:
            self._note_reply('UNPARSEABLE_REPLY', json.dumps(envelope, default=str))
            raise
        name = envelope.get('tool_name')
        return ModelResponse(tool_calls=(ToolCall(name if isinstance(name, str) else '', arguments),),
                             usage=usage, model_id=model_id, stop_reason='tool_call')


@register
class ClaudeCliProvider(CliProvider):
    """Claude through the signed-in Claude Code executable, with all built-in tools disabled."""

    transport = 'claude_cli'
    executable = 'claude'
    default_model = 'haiku'
    child_env_extra = ('CLAUDE_CONFIG_DIR',)

    def _prepare(self, io_dir, system):
        (io_dir / 'system.txt').write_text(system or DEFAULT_SYSTEM, encoding='utf-8')

    def _argv(self, executable, request, system, schema_path, output_path, cwd):
        # Customizations off (--safe-mode, no setting sources): user/project hooks, settings, memory files,
        # plugins and MCP servers are not loaded. Administrator-managed settings still apply (M17).
        argv = [executable, '-p', '--output-format', 'json', f'--model={self.model()}', '--tools', '',
                '--no-session-persistence', '--strict-mcp-config', '--disable-slash-commands', '--safe-mode',
                '--setting-sources', '', '--system-prompt-file', str(output_path.parent / 'system.txt')]
        if schema_path is not None:
            argv += ['--json-schema', schema_path.read_text(encoding='utf-8')]
        if self.config.max_usd_per_run is not None:
            argv += ['--max-budget-usd', str(self.config.max_usd_per_run)]
        return argv

    def _read(self, stdout, output_path):
        result = json.loads(stdout)
        if result.get('type') != 'result' or result.get('is_error') or result.get('subtype') != 'success':
            raise ValueError('error envelope')
        usage = result.get('usage') or {}
        counts = [usage.get(name) for name in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')]
        tokens_in = sum(count or 0 for count in counts) if any(count is not None for count in counts) else None
        cost = result.get('total_cost_usd')
        structured = result.get('structured_output')
        text = result.get('result')
        return (text if isinstance(text, str) else '', structured,
                Usage(tokens_in, usage.get('output_tokens'),
                      float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None),
                next(iter(result.get('modelUsage') or {}), ''))


@register
class CodexCliProvider(CliProvider):
    """OpenAI models through the signed-in Codex executable in its read-only sandbox."""

    transport = 'codex_cli'
    executable = 'codex'
    child_env_extra = ('CODEX_HOME',)
    strict_schemas = True  # LOG-0032: Codex sends --output-schema as an OpenAI strict response format

    def _event_failure(self, stdout):
        return codex_failure(stdout)

    def _argv(self, executable, request, system, schema_path, output_path, cwd):
        argv = [executable, 'exec', '--sandbox', 'read-only', '--skip-git-repo-check', '--ephemeral',
                '--ignore-user-config', '--color', 'never', '--json', '--cd', str(cwd), '-o', str(output_path)]
        if schema_path is not None:
            argv += ['--output-schema', str(schema_path)]
        if self.model():
            argv += ['-m', self.model()]
        return argv + ['-']

    def _stdin(self, request, system):
        return f'{system}\n\n{self._transcript(request)}' if system else self._transcript(request)

    def _read(self, stdout, output_path):
        text = output_path.read_text(encoding='utf-8')
        if not text.strip():
            raise ValueError('empty output')
        # LOG-0029: `codex exec --json` (0.169.0) names no model and --ephemeral leaves no rollout, so a
        # configured model is the requested identity (the executable refuses an unavailable model).
        # Without a configured model the id stays '' and the feature gate stays closed.
        return text, None, codex_usage(stdout), self.model() or codex_model_id(stdout)

    def model_identity_source(self):
        return 'requested' if self.model() else 'observed'


@register
class GeminiCliProvider(CliProvider):
    """Gemini through the signed-in Gemini executable in its read-only plan mode."""

    transport = 'gemini_cli'
    executable = 'gemini'
    native_schema = False

    def _argv(self, executable, request, system, schema_path, output_path, cwd):
        argv = [executable, '-o', 'json', '--approval-mode', 'plan']
        if self.model():
            argv += ['-m', self.model()]
        return argv + ['-p', 'Follow the instructions given on standard input.']

    def _stdin(self, request, system):
        return f'{system}\n\n{self._transcript(request)}' if system else self._transcript(request)

    def _read(self, stdout, output_path):
        result = json.loads(stdout)
        if result.get('error') or not isinstance(result.get('response'), str):
            raise ValueError('error envelope')
        return result['response'], None, Usage(), self.model()

    def model_identity_source(self):
        # The Gemini envelope names no model; the configured name is reported (labelled, not observed).
        return 'requested' if self.model() else 'observed'
