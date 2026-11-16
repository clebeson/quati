"""M17 vendor-neutral model provider base class, records and registry.

Every model call goes through ``Provider.complete``. A new vendor is added by
subclassing ``Provider``, implementing ``_complete`` and decorating the class with
``@register``; callers never change. This module imports no vendor SDK.
"""
from abc import ABC, abstractmethod
import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import re
import secrets
import shutil
import threading
import time
from urllib.parse import unquote, urlsplit

import jsonschema

from quati.application.identity import canonical_bytes
from quati.application.ports import ProviderConfig, valid_endpoint

FEATURES = ('tools', 'structured_output', 'streaming', 'timeout', 'concurrency')
PROBE_STOP_CODES = ('UNAUTHENTICATED', 'FORBIDDEN', 'NOT_CONFIGURED', 'BUDGET_EXCEEDED')
PROBE_TOOL = 'quati_probe_echo'
# Only the tool sub-check gates `quati ask`; a non-measurement miss (transport error, timeout) on it is
# retried once and recorded in the report (`attempts`, `retried`). A wrong answer is a measurement, never retried.
PROBE_RETRY_FEATURES = ('tools',)
PROBE_MAX_RETRIES = 1
STOP_REASONS = ('end', 'tool_call', 'length', 'refusal', 'other')
# A model id is passed to vendor SDKs and executables; it can never look like an option or a path trick.
MODEL_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/@\[\]-]{0,199}')
TOOL_NAME_PATTERN = re.compile(r'[A-Za-z0-9_-]{1,64}')
# JSON Schema keywords whose value is a schema, a list of schemas or a map of schemas.
_SCHEMA_VALUE = ('additionalProperties', 'items', 'contains', 'not', 'if', 'then', 'else', 'propertyNames',
                 'unevaluatedItems', 'unevaluatedProperties', 'contentSchema')
_SCHEMA_LIST = ('allOf', 'anyOf', 'oneOf', 'prefixItems')
_SCHEMA_MAP = ('properties', 'patternProperties', '$defs', 'definitions', 'dependentSchemas')
# M17-RT-02 "Key value shape": an API key is ONE opaque token a vendor issued for API access. A value
# that refers to something else (a path, a file or variable reference), that has structure (several
# tokens, a header, a cookie, a JSON document, plain or base64-encoded) or that is a sign-in session
# artifact is never an API key. The value is only classified here; it is never logged, returned or
# placed in a hint.
_KEY_NOT_ONE_TOKEN = re.compile(r'[\s\x00-\x1f\x7f]')
_KEY_PATH = re.compile(r'(?:[/~.@]|[A-Za-z]:[\\/]|file:)|.*(?:\\|/\.)|.*\.json\Z', re.IGNORECASE | re.DOTALL)
_KEY_STRUCTURED = re.compile(r'[{\[]|bearer[^A-Za-z0-9]|[A-Za-z_][A-Za-z0-9_.-]*=[^=]|.*;', re.IGNORECASE | re.DOTALL)
_KEY_SESSION_JWT = re.compile(r'eyJ[A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]*){1,4}')
_KEY_SESSION_PREFIX = re.compile(r'(?:sk-ant-(?:o[ar]t|sid)[0-9]|(?i:sess-)|rt_|ya29\.|1//|gh[ou]_'
                                 r'|IQoJb3JpZ2lu|F[Qw]oGZXIvYXdz)')
_KEY_BASE64 = re.compile(r'[A-Za-z0-9+/_-]{4,}={0,2}')
_KEY_PATH_HINT = 'QUATI_API_KEY_ENV: a file path is not an API key'
_KEY_VARIABLE_HINT = 'QUATI_API_KEY_ENV: a variable reference is not an API key'
_KEY_SESSION_HINT = 'QUATI_API_KEY_ENV: a sign-in session file or token is not an API key'
BUILTIN_ADAPTERS = 'quati.adapters.providers'
ENTRY_POINT_GROUP = 'quati.providers'

# Fixed Quati sentences; upstream text never reaches a caller.
MESSAGES = {
    'TRANSPORT_UNKNOWN': 'The configured provider transport is not registered.',
    'ENDPOINT_INVALID': 'The provider endpoint is not an approved HTTPS URL.',
    'MODEL_MISSING': 'No model is configured for this provider.',
    'MODEL_INVALID': 'The configured model name is not a valid model identifier.',
    'API_KEY_REF_INVALID': 'The provider key reference is not an environment-variable secret reference.',
    'API_KEY_MISSING': 'The provider key reference has no value.',
    'LIVE_NOT_ALLOWED': 'Live provider calls are not allowed.',
    'ADAPTER_NOT_INSTALLED': 'The provider adapter dependency is not installed.',
    'CLI_NOT_FOUND': 'The provider executable was not found.',
    'CLI_FAILED': 'The provider executable failed or returned unusable output.',
    'RATE_LIMITED': 'The provider rate limit was reached.',
    'REQUEST_REJECTED': 'The provider rejected the request.',
    'SCHEMA_REJECTED': 'The provider rejected the output schema of the request.',
    'SCHEMA_NOT_STRICT': 'The output schema cannot be expressed in the provider strict schema mode.',
    'REQUEST_INVALID': 'The model request is invalid.',
    'STREAMING_UNSUPPORTED': 'This provider transport does not support streaming.',
    'TOOL_CALL_MISSING': 'The model did not return the required tool call.',
    'TOOL_CALL_INVALID': 'The model returned an invalid tool call.',
    'SCHEMA_INVALID_OUTPUT': 'The model output does not match the required schema.',
    'OUTPUT_TRUNCATED': 'The model output was truncated.',
    'MODEL_REFUSED': 'The model declined the request.',
    'MODEL_NOT_FOUND': 'The provider does not know the configured model.',
    'MODEL_INCOMPATIBLE': 'The model has no measured support for a required feature.',
    'REDIRECT_REJECTED': 'The provider endpoint answered with a redirect.',
    'UPSTREAM_ERROR': 'The provider returned an unusable response.',
    'NETWORK_ERROR': 'The provider could not be reached.',
    'ADAPTER_FAULT': 'The provider adapter failed.',
    'UNAUTHENTICATED': 'The provider rejected the credential.',
    'FORBIDDEN': 'The provider denied access.',
    'DEADLINE_EXCEEDED': 'The provider call exceeded its deadline.',
    'BUDGET_EXCEEDED': 'The run budget for provider calls is exhausted.',
}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class ModelRequest:
    messages: tuple
    system: str = ''
    tools: tuple = ()
    require_tool: bool = False
    output_schema: dict | None = None
    stream: bool = False
    max_output_tokens: int | None = None
    timeout_s: float | None = None


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


@dataclass(frozen=True)
class ProbeProfile:
    """The schemas a probe measures (S4). The ask profile is the classification schema and the four
    discovery tools; without a profile the probe uses trivial nonce schemas and can never open the ask gate."""
    name: str
    output_schema: dict
    output_field: str
    tools: tuple
    tool_name: str
    tool_field: str

    def sha256(self):
        body = {'name': self.name, 'output_schema': self.output_schema, 'output_field': self.output_field,
                'tools': [[tool.name, tool.description, tool.input_schema] for tool in self.tools],
                'tool_name': self.tool_name, 'tool_field': self.tool_field}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ModelResponse:
    text: str = ''
    tool_calls: tuple = ()
    structured: object = None
    usage: Usage = field(default_factory=Usage)
    model_id: str = ''
    provider_id: str = ''
    stop_reason: str = 'end'
    chunk_count: int = 1


class ProviderError(Exception):
    """Typed provider failure: boundary error code, reason tag and a fixed message."""

    def __init__(self, code, reason=None, retry_after_s=None):
        self.code = code
        self.reason = reason or code
        self.message = MESSAGES.get(self.reason, MESSAGES.get(code, 'The provider call failed.'))
        self.retry_after_s = retry_after_s
        super().__init__(f'{self.code}:{self.reason}')


def _encoded_json_document(value):
    """True when ``value`` is the base64 or base64url encoding of a JSON object or array."""
    if not _KEY_BASE64.fullmatch(value):
        return False
    body = value.rstrip('=').replace('-', '+').replace('_', '/')
    try:
        document = json.loads(base64.b64decode(body + '=' * (-len(body) % 4), validate=True))
    except (ValueError, RecursionError):  # not base64, not UTF-8 or not JSON: an opaque token
        return False
    return isinstance(document, (dict, list))


def key_value_issue(value):
    """M17-RT-02: the operator hint when ``value`` is a reference, a structured value or a sign-in
    session artifact (the M17 "Key value shape" table), else None. The hint never contains the value."""
    if value.startswith('$'):
        return _KEY_VARIABLE_HINT
    if _KEY_PATH.match(value):
        return _KEY_PATH_HINT
    if (_KEY_NOT_ONE_TOKEN.search(value) or _KEY_STRUCTURED.match(value) or _KEY_SESSION_JWT.fullmatch(value)
            or _KEY_SESSION_PREFIX.match(value) or _encoded_json_document(value)):
        return _KEY_SESSION_HINT
    return None


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


class Provider(ABC):
    """Base class owning configuration checks, budgets, retries, validation and the probe."""

    transport = ''
    default_model = ''
    default_base_url = ''
    needs_secret = True
    needs_endpoint = False
    takes_endpoint = True
    needs_model = True
    sdk_module = ''
    executable = ''
    supports_streaming = True

    def __init__(self, config: ProviderConfig, *, environ=None, sleep=time.sleep, clock=_utc_now,
                 monotonic=time.monotonic, nonce=None, which=None):
        self.config = config
        self.environ = os.environ if environ is None else environ
        self._sleep = sleep
        self._clock = clock
        self._monotonic = monotonic
        self._nonce = nonce or (lambda: secrets.token_hex(16))
        self._which_override = which
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(max(1, config.max_concurrency))
        self._calls = 0
        self._cost = 0.0
        self._last_model_id = ''
        self._probe_capture = None  # raw responses of the tool sub-check (G2 diagnostics), probe only
        self._probe_note = None
        self._probe_nonce = None
        self._probe_error = None
        self._probe_target = (PROBE_TOOL, 'nonce')
        self._profile = None

    def _which(self, name):
        # Resolved at call time so a PATH change after construction is honored.
        return (self._which_override or shutil.which)(name)

    # ----- vendor hook -------------------------------------------------------------
    @abstractmethod
    def _complete(self, request: ModelRequest) -> ModelResponse:
        """Perform exactly one upstream call; raise ProviderError on failure."""

    # ----- configuration -----------------------------------------------------------
    def model(self):
        return self.config.model or self.default_model

    def base_url(self):
        return self.config.base_url or self.default_base_url

    def secret(self):
        """Return the key value for the adapter; never logged, stored or returned to callers."""
        return self.environ.get(self.config.api_key_env, '')

    def config_issues(self):
        """Ordered (reason code, operator hint) pairs; empty when a live call may be made."""
        issues = []
        if self.takes_endpoint:
            endpoint = self.config.base_url
            if (endpoint and not valid_endpoint(endpoint)) or (not endpoint and self.needs_endpoint):
                issues.append(('ENDPOINT_INVALID', 'QUATI_BASE_URL: approved HTTPS endpoint required'))
        model = self.model()
        if self.needs_model and not model:
            issues.append(('MODEL_MISSING', 'QUATI_MODEL'))
        elif model and not (isinstance(model, str) and MODEL_PATTERN.fullmatch(model)):
            issues.append(('MODEL_INVALID', 'QUATI_MODEL: letters, digits and . _ : / @ [ ] - only'))
        if self.needs_secret:
            name = self.config.api_key_env
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
                issues.append(('API_KEY_REF_INVALID', 'QUATI_API_KEY_ENV: environment-variable name required'))
            else:
                value = self.environ.get(name, '')
                if not value:
                    issues.append(('API_KEY_MISSING', 'QUATI_API_KEY_ENV: configured secret reference has no value'))
                else:
                    hint = key_value_issue(value)
                    if hint:
                        issues.append(('API_KEY_REF_INVALID', hint))
        if not self.config.allow_live:
            issues.append(('LIVE_NOT_ALLOWED', 'QUATI_ALLOW_LIVE=1'))
        if self.sdk_module and importlib.util.find_spec(self.sdk_module) is None:
            issues.append(('ADAPTER_NOT_INSTALLED', 'Install Quati live optional dependency'))
        if self.executable and not self._which(self.executable):
            issues.append(('CLI_NOT_FOUND', f'{self.executable}: executable not found on PATH'))
        return issues

    def ensure_configured(self):
        issues = self.config_issues()
        if issues:
            raise ProviderError('NOT_CONFIGURED', issues[0][0])

    def diagnostics(self):
        """Safe configuration report. Labels and metadata never mark a feature SUPPORTED."""
        issues = self.config_issues()
        reasons = [reason for reason, _ in issues]
        endpoint = self.base_url() if self.takes_endpoint else ''
        return {'configured': not issues, 'status': 'NOT_CONFIGURED' if issues else 'NOT_PROBED',
                'missing': [hint for _, hint in issues], 'reasons': reasons, 'transport': self.transport,
                'adapter_installed': not {'ADAPTER_NOT_INSTALLED', 'CLI_NOT_FOUND'} & set(reasons),
                'model': self.model() or None,
                'endpoint_host': urlsplit(endpoint).hostname if endpoint and valid_endpoint(endpoint) else None,
                'features': dict.fromkeys(FEATURES, 'NOT_VERIFIED'),
                'region': 'UNKNOWN', 'pricing': 'UNKNOWN'}

    def executable_identity(self):
        """Identity of the vendor executable a transport runs; None for transports without one."""
        return None

    def config_hash(self):
        config = self.config
        values = {
            'transport': self.transport, 'base_url': self.base_url() if self.takes_endpoint else '',
            'model': self.model(), 'timeout_seconds': config.timeout_seconds,
            'max_requests': config.max_requests, 'max_output_tokens': config.max_output_tokens,
            'max_usd_per_run': config.max_usd_per_run, 'max_retries_429': config.max_retries_429,
            'retry_after_max_s': config.retry_after_max_s, 'max_concurrency': config.max_concurrency,
        }
        identity = self.executable_identity()
        if identity is not None:
            # A measured FeatureReport never transfers to another (for example upgraded) executable.
            values['executable'] = identity
        return hashlib.sha256(canonical_bytes(values)).hexdigest()

    # ----- one model call ----------------------------------------------------------
    def reset_run(self):
        with self._lock:
            self._calls = 0
            self._cost = 0.0

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.ensure_configured()
        self._check_request(request)
        effective = replace(
            request,
            max_output_tokens=(self.config.max_output_tokens if request.max_output_tokens is None
                               else request.max_output_tokens),
            timeout_s=self.config.timeout_seconds if request.timeout_s is None else request.timeout_s)
        retries = 0
        while True:
            self._reserve_call()
            # A failure is rebuilt and raised outside the handler, so it never carries the upstream
            # exception (request headers, upstream body) as its cause or context.
            try:
                with self._slots:
                    response = self._complete(effective)
                response = self._accounted(response)
                if self._probe_capture is not None:
                    self._probe_capture.append(response)
                return replace(self._validated(request, response), provider_id=self.transport)
            except ProviderError as exc:
                failure = ProviderError(exc.code, exc.reason, exc.retry_after_s)
            except Exception:
                failure = ProviderError('INTERNAL_ERROR', 'ADAPTER_FAULT')
            if failure.reason != 'RATE_LIMITED' or retries >= self.config.max_retries_429:
                raise failure
            wait = failure.retry_after_s if failure.retry_after_s is not None else float(2 ** retries)
            if wait > self.config.retry_after_max_s or self._budget_spent():
                raise failure
            retries += 1
            self._sleep(wait)

    def _check_request(self, request):
        if not self._request_ok(request):
            raise ProviderError('INVALID_INPUT', 'REQUEST_INVALID')
        if request.stream and not self.supports_streaming:
            raise ProviderError('UNSUPPORTED', 'STREAMING_UNSUPPORTED')

    @staticmethod
    def _request_ok(request):
        if (not request.messages or (request.tools and request.output_schema is not None)
                or (request.require_tool and not request.tools)):
            return False
        for message in request.messages:
            if not (isinstance(message, Message) and message.role in ('user', 'assistant')
                    and isinstance(message.content, str)):
                return False
        names = [tool.name for tool in request.tools]
        if len(set(map(repr, names))) != len(names):
            return False
        if not all(isinstance(name, str) and TOOL_NAME_PATTERN.fullmatch(name) for name in names):
            return False
        tokens, timeout = request.max_output_tokens, request.timeout_s
        if tokens is not None and not (isinstance(tokens, int) and not isinstance(tokens, bool) and tokens > 0):
            return False
        if timeout is not None and not (isinstance(timeout, (int, float)) and not isinstance(timeout, bool)
                                        and math.isfinite(timeout) and timeout > 0):
            return False
        schemas = [tool.input_schema for tool in request.tools]
        if request.output_schema is not None:
            schemas.append(request.output_schema)
        return all(_schema_ok(schema) for schema in schemas)

    def _budget_spent(self):
        limit = self.config.max_usd_per_run
        with self._lock:
            return self._calls >= self.config.max_requests or (limit is not None and self._cost >= limit)

    def _reserve_call(self):
        if self._budget_spent():
            raise ProviderError('BUDGET_EXCEEDED')
        with self._lock:
            self._calls += 1

    def _accounted(self, response):
        """Reject a malformed adapter response, normalize its usage and charge the run budget."""
        calls = response.tool_calls if isinstance(response, ModelResponse) else None
        if not (isinstance(calls, (tuple, list))
                and all(isinstance(call, ToolCall) and isinstance(call.name, str) for call in calls)
                and isinstance(response.text, str) and isinstance(response.usage, Usage)
                and isinstance(response.model_id, str) and isinstance(response.stop_reason, str)
                and isinstance(response.chunk_count, int) and not isinstance(response.chunk_count, bool)):
            raise ProviderError('INTERNAL_ERROR', 'ADAPTER_FAULT')
        usage = Usage(_count(response.usage.input_tokens), _count(response.usage.output_tokens),
                      _amount(response.usage.cost_usd))
        with self._lock:
            if usage.cost_usd is not None:
                self._cost += usage.cost_usd
            if response.model_id:
                self._last_model_id = response.model_id
        return replace(response, tool_calls=tuple(calls), usage=usage)

    def _validated(self, request, response):
        if response.stop_reason == 'length':
            raise ProviderError('OUTPUT_INVALID', 'OUTPUT_TRUNCATED')
        if response.stop_reason == 'refusal':
            raise ProviderError('OUTPUT_INVALID', 'MODEL_REFUSED')
        if response.stop_reason not in ('end', 'tool_call'):
            raise ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
        offered = {tool.name: tool for tool in request.tools}
        for call in response.tool_calls:
            tool = offered.get(call.name)
            if tool is None or not isinstance(call.arguments, dict) or not _valid(call.arguments, tool.input_schema):
                raise ProviderError('OUTPUT_INVALID', 'TOOL_CALL_INVALID')
        if request.require_tool and not response.tool_calls:
            raise ProviderError('OUTPUT_INVALID', 'TOOL_CALL_MISSING')
        if request.output_schema is not None and not response.tool_calls:
            structured = response.structured
            if structured is None:
                structured = _parsed(response.text)
            if structured is _UNPARSEABLE or not _valid(structured, request.output_schema):
                raise ProviderError('OUTPUT_INVALID', 'SCHEMA_INVALID_OUTPUT')
            response = replace(response, structured=structured)
        return response

    def model_identity_source(self):
        """How a response's model id is known: "observed" (reported by the vendor) or "requested" (configured)."""
        return 'observed'

    def model_visible(self, request):
        """Transport-specific rendering of ``request`` when it differs from its system and messages; else None."""
        return None

    # ----- feature probe -----------------------------------------------------------
    def probe(self, profile=None):
        """Measure each feature with a live nonce round-trip; return a FeatureReport.

        ``profile`` (a ProbeProfile) names the real request schemas to measure; without it the
        report is labelled ``trivial`` and the ask feature gate treats it as not measured.
        """
        self._profile = profile
        features = dict.fromkeys(FEATURES, 'NOT_VERIFIED')
        observations = dict.fromkeys(FEATURES, 'NOT_RUN')
        attempts = dict.fromkeys(FEATURES, 0)
        retried = {}
        details = {}
        aborted = None
        with self._lock:
            self._last_model_id = ''  # only a model id observed during this probe is reported as observed
        for feature in FEATURES:
            while True:
                attempts[feature] += 1
                features[feature], observations[feature], detail = self._probe_feature(feature)
                if detail is None:
                    details.pop(feature, None)
                else:
                    details[feature] = detail
                exc = self._probe_error
                if exc is not None:
                    if exc.code in PROBE_STOP_CODES or exc.reason == 'RATE_LIMITED':
                        # A provider that denies, is out of budget or is rate limited is not hit again.
                        aborted = exc.code if exc.code in PROBE_STOP_CODES else 'RATE_LIMITED'
                        break
                    if (feature in PROBE_RETRY_FEATURES and features[feature] == 'NOT_VERIFIED'
                            and attempts[feature] <= PROBE_MAX_RETRIES):
                        # A transient miss is not a measurement: one bounded, recorded retry of the sub-check.
                        retried[feature] = exc.reason
                        continue
                break
            if aborted is not None:
                break
        return {'provider_id': self.transport, 'transport': self.transport,
                'model_or_adapter_version': self._last_model_id or self.model() or self.transport,
                'observed_model_id': self._last_model_id, 'model_identity_source': self.model_identity_source(),
                'config_hash': self.config_hash(), 'measured_at': self._clock(),
                'features': features, 'observations': observations, 'aborted': aborted,
                'attempts': attempts, 'retried': retried, 'details': details,
                'probe_profile': ({'name': profile.name, 'sha256': profile.sha256()} if profile is not None
                                  else {'name': 'trivial', 'sha256': None}),
                'evidence_refs': [], 'metadata_attestations': {'region': 'UNKNOWN', 'pricing': 'UNKNOWN'}}

    def _probe_feature(self, feature):
        """One sub-check: (verdict, reason, detail); detail is typed for a tool check that is not SUPPORTED."""
        self._probe_capture = [] if feature == 'tools' else None
        self._probe_note = self._probe_error = None
        try:
            verdict, reason = getattr(self, f'_probe_{feature}')()
        except ProviderError as exc:
            self._probe_error = exc
            verdict, reason = self._classify(exc)
        detail = self._tool_detail() if feature == 'tools' and verdict != 'SUPPORTED' else None
        self._probe_capture = None
        return verdict, reason, detail

    def _note_reply(self, detail, raw_text):
        """Adapter hook: a reply it could not decode during a probe (typed detail plus a short hash only)."""
        if self._probe_capture is not None:
            self._probe_note = (detail, _short_hash(raw_text or ''))

    def _tool_detail(self):
        """G2: why the tool sub-check failed, from the raw reply; never the reply text itself."""
        if self._probe_note is not None:
            return {'detail': self._probe_note[0], 'reply_sha256_16': self._probe_note[1], 'call_count': None}
        if not self._probe_capture:
            exc = self._probe_error
            return {'detail': f'TRANSPORT_ERROR:{exc.code}:{exc.reason}', 'reply_sha256_16': None,
                    'call_count': None}
        reply = self._probe_capture[-1]
        calls = list(reply.tool_calls)
        digest_of = _short_hash(json.dumps({'text': reply.text, 'tool_calls': [[call.name, call.arguments]
                                                                              for call in calls]},
                                           sort_keys=True, default=str))
        if not calls:
            detail = 'NO_TOOL_CALL'
        elif calls[0].name != self._probe_target[0]:
            detail = 'WRONG_TOOL_NAME'
        elif not self._target_matches(calls[0]) and any(self._target_matches(call) for call in calls[1:]):
            detail = 'EXTRA_CALLS'
        else:
            detail = 'ARGUMENTS_MISMATCH'   # wrong nonce, or the right nonce outside the declared schema
        return {'detail': detail, 'reply_sha256_16': digest_of, 'call_count': len(calls)}

    @staticmethod
    def _classify(exc):
        # Only a model answer that fails the check, or a transport without the feature, is a measurement.
        if exc.code == 'OUTPUT_INVALID' or exc.reason == 'STREAMING_UNSUPPORTED':
            return 'UNSUPPORTED', exc.reason
        return 'NOT_VERIFIED', exc.reason

    @staticmethod
    def _nonce_schema():
        return {'type': 'object', 'properties': {'nonce': {'type': 'string'}},
                'required': ['nonce'], 'additionalProperties': False}

    def _target_matches(self, call):
        name, field_name = self._probe_target
        return call.name == name and _nonce_matches(call.arguments, self._probe_nonce, field_name)

    def _probe_tools(self):
        nonce = self._probe_nonce = self._nonce()
        profile = self._profile
        if profile is None:
            tools = (ToolSpec(PROBE_TOOL, 'Echo the given nonce back to the caller.', self._nonce_schema()),)
            self._probe_target = (PROBE_TOOL, 'nonce')
        else:
            tools, self._probe_target = tuple(profile.tools), (profile.tool_name, profile.tool_field)
        name, field_name = self._probe_target
        response = self.complete(ModelRequest(
            (Message('user', f'Call the tool {name} with {field_name} set to {nonce}.'),),
            system='You are a connectivity probe. Follow the instruction exactly.',
            tools=tools, require_tool=True))
        return _nonce_result(self._target_matches(response.tool_calls[0]))

    def _probe_structured_output(self):
        nonce = self._nonce()
        profile = self._profile
        schema, field_name = ((self._nonce_schema(), 'nonce') if profile is None
                              else (profile.output_schema, profile.output_field))
        instruction = (f'Return a JSON object whose nonce field is exactly {nonce}.' if profile is None else
                       f'Return a JSON object that matches the required schema, with its {field_name} field set '
                       f'to exactly {nonce}; any valid value is acceptable for every other field.')
        response = self.complete(ModelRequest(
            (Message('user', instruction),),
            system='You are a connectivity probe. Follow the instruction exactly.',
            output_schema=schema))
        return _nonce_result(_nonce_matches(response.structured, nonce, field_name))

    def _echo_request(self, nonce, stream=False):
        return ModelRequest((Message('user', f'Reply with exactly this text and nothing else: {nonce}'),),
                            system='You are a connectivity probe. Follow the instruction exactly.', stream=stream)

    def _probe_streaming(self):
        nonce = self._nonce()
        response = self.complete(self._echo_request(nonce, stream=True))
        if response.text.strip() != nonce:
            return 'UNSUPPORTED', 'NONCE_MISMATCH'
        if response.chunk_count < 2:
            return 'NOT_VERIFIED', 'SINGLE_CHUNK'
        return 'SUPPORTED', 'PROBE_PASSED'

    def _probe_timeout(self):
        request = ModelRequest(
            (Message('user', 'Write a detailed essay of at least two thousand words about the history of timekeeping.'),),
            timeout_s=1)
        try:
            self.complete(request)
        except ProviderError as exc:
            if exc.code == 'DEADLINE_EXCEEDED':
                return 'SUPPORTED', 'PROBE_PASSED'
            if exc.code == 'OUTPUT_INVALID':
                return 'NOT_VERIFIED', 'DEADLINE_NOT_REACHED'
            if exc.code == 'UNSUPPORTED':
                return 'NOT_VERIFIED', exc.reason
            raise
        return 'NOT_VERIFIED', 'DEADLINE_NOT_REACHED'

    def _probe_concurrency(self):
        count = self.config.max_concurrency
        if count < 2:
            return 'NOT_VERIFIED', 'CONCURRENCY_NOT_EXERCISED'
        nonces = [self._nonce() for _ in range(count)]
        with ThreadPoolExecutor(max_workers=count) as pool:
            futures = [pool.submit(self.complete, self._echo_request(nonce)) for nonce in nonces]
            outcomes = []
            for future in futures:
                try:
                    outcomes.append(future.result())
                except ProviderError as exc:
                    outcomes.append(exc)
        for outcome in outcomes:
            if isinstance(outcome, ProviderError):
                raise outcome
        return _nonce_result(all(outcome.text.strip() == nonce for outcome, nonce in zip(outcomes, nonces)))


def _nonce_matches(arguments, nonce, field_name='nonce'):
    """Exact on the semantic value: surrounding whitespace and hex letter case are not part of a nonce."""
    value = arguments.get(field_name) if isinstance(arguments, dict) else None
    return isinstance(value, str) and isinstance(nonce, str) and value.strip().casefold() == nonce.casefold()


def _short_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def _nonce_result(matched):
    return ('SUPPORTED', 'PROBE_PASSED') if matched else ('UNSUPPORTED', 'NONCE_MISMATCH')


_UNPARSEABLE = object()


def _parsed(text):
    try:
        return json.loads(text)
    except (ValueError, RecursionError):
        return _UNPARSEABLE


def _valid(instance, schema):
    """True when the instance matches; a validator failure of any kind is a mismatch, never a crash."""
    try:
        jsonschema.Draft202012Validator(schema).validate(instance)
    except Exception:
        return False
    return True


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _amount(value):
    usable = (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
              and value >= 0)
    return value if usable else None


def _schema_ok(schema):
    """A request schema is a valid draft 2020-12 object whose references are local and resolve."""
    if not isinstance(schema, dict):
        return False
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception:
        return False
    return _references_ok(schema, schema)


def _references_ok(node, root):
    if not isinstance(node, dict):
        return True
    if '$dynamicRef' in node:
        return False
    if '$ref' in node and not _resolves(node['$ref'], root):
        return False
    children = [node[key] for key in _SCHEMA_VALUE if key in node]
    for key in _SCHEMA_LIST:
        children.extend(node.get(key) or ())
    for key in _SCHEMA_MAP:
        children.extend((node.get(key) or {}).values())
    return all(_references_ok(child, root) for child in children)


def _resolves(reference, root):
    if reference == '#':
        return True
    if not (isinstance(reference, str) and reference.startswith('#/')):
        return False
    target = root
    for token in unquote(reference[2:]).split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(target, dict) and token in target:
            target = target[token]
        elif isinstance(target, list) and token.isdecimal() and int(token) < len(target):
            target = target[int(token)]
        else:
            return False
    return True


def require_features(features, required):
    """Capability filter: only a measured SUPPORTED feature satisfies a requirement."""
    if any(features.get(name) != 'SUPPORTED' for name in required):
        raise ProviderError('UNSUPPORTED', 'MODEL_INCOMPATIBLE')


# ----- registry ------------------------------------------------------------------------
_REGISTRY = {}
_loaded = False


def register(cls):
    """Class decorator: make a Provider subclass selectable by its transport name."""
    name = getattr(cls, 'transport', '')
    if not (isinstance(cls, type) and issubclass(cls, Provider) and re.fullmatch(r'[a-z][a-z0-9_]*', name or '')):
        raise ValueError('A provider must subclass Provider and declare a lowercase transport name')
    existing = _REGISTRY.get(name)
    if existing is not None and existing is not cls:
        raise ValueError(f'Provider transport already registered: {name}')
    _REGISTRY[name] = cls
    return cls


def unregister(name):
    _REGISTRY.pop(name, None)


def _load_plugins():
    """Import the built-in adapters and third-party entry points once; broken plugins are skipped."""
    global _loaded
    if _loaded:
        return
    importlib.import_module(BUILTIN_ADAPTERS)
    _loaded = True
    for entry_point in importlib.metadata.entry_points(group=ENTRY_POINT_GROUP):
        try:
            entry_point.load()
        except Exception:
            continue


def transports():
    _load_plugins()
    return tuple(sorted(_REGISTRY))


def provider_class(transport):
    _load_plugins()
    cls = _REGISTRY.get(transport)
    if cls is None:
        raise ProviderError('NOT_CONFIGURED', 'TRANSPORT_UNKNOWN')
    return cls


def create_provider(config, **dependencies):
    return provider_class(config.transport)(config, **dependencies)


def diagnostics_for(config, **dependencies):
    """Configuration diagnostics for any transport name, registered or not."""
    try:
        return create_provider(config, **dependencies).diagnostics()
    except ProviderError as exc:
        return {'configured': False, 'status': 'NOT_CONFIGURED',
                'missing': ['QUATI_PROVIDER: registered transport required'],
                'reasons': [exc.reason], 'transport': config.transport, 'adapter_installed': False,
                'model': config.model or None, 'endpoint_host': None,
                'features': dict.fromkeys(FEATURES, 'NOT_VERIFIED'),
                'region': 'UNKNOWN', 'pricing': 'UNKNOWN'}
