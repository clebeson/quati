"""Shared adapter helpers: vendor SDK exception mapping and tool-argument decoding.

Both official SDKs expose the same exception class names, so one mapping serves both.
The upstream message is never copied into the result.
"""
import json

from quati.application.providers import ProviderError

TOOL_STEERING = 'You must answer by calling one of the provided tools. Do not answer in plain text.'


def _header_number(exc, name):
    try:
        return float(exc.response.headers.get(name, ''))
    except (AttributeError, TypeError, ValueError):
        return None


def retry_after_seconds(exc):
    """Retry delay of a rate-limit response in seconds: numeric ``retry-after-ms`` first, else
    numeric ``retry-after``; None when absent, unparsable or negative."""
    milliseconds = _header_number(exc, 'retry-after-ms')
    value = milliseconds / 1000 if milliseconds is not None else _header_number(exc, 'retry-after')
    return value if value is not None and value >= 0 else None


def map_error(sdk, exc):
    """Return the ProviderError for an SDK exception; unknown exceptions are adapter faults."""
    if isinstance(exc, sdk.APITimeoutError):
        return ProviderError('DEADLINE_EXCEEDED')
    if isinstance(exc, sdk.APIConnectionError):
        return ProviderError('TEMPORARILY_UNAVAILABLE', 'NETWORK_ERROR')
    if isinstance(exc, sdk.APIStatusError):
        status = exc.status_code
        if status == 401:
            return ProviderError('UNAUTHENTICATED')
        if status in (402, 403):  # 402: billing or credit exhausted
            return ProviderError('FORBIDDEN')
        if status == 408:
            return ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
        if status == 404:
            return ProviderError('NOT_FOUND', 'MODEL_NOT_FOUND')
        if status == 429:
            return ProviderError('TEMPORARILY_UNAVAILABLE', 'RATE_LIMITED', retry_after_seconds(exc))
        if 300 <= status < 400:
            return ProviderError('TEMPORARILY_UNAVAILABLE', 'REDIRECT_REJECTED')
        if status >= 500:
            return ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
        return ProviderError('UNSUPPORTED', 'REQUEST_REJECTED')
    if isinstance(exc, sdk.APIError):
        return ProviderError('TEMPORARILY_UNAVAILABLE', 'UPSTREAM_ERROR')
    return ProviderError('INTERNAL_ERROR', 'ADAPTER_FAULT')


def parse_arguments(encoded):
    """Decode a tool call's JSON-encoded arguments; anything but a JSON object is TOOL_CALL_INVALID."""
    if not isinstance(encoded, str) or not encoded.strip():
        raise ProviderError('OUTPUT_INVALID', 'TOOL_CALL_INVALID')
    try:
        arguments = json.loads(encoded)
    except ValueError:
        arguments = None
    if not isinstance(arguments, dict):
        raise ProviderError('OUTPUT_INVALID', 'TOOL_CALL_INVALID')
    return arguments


# ----------------------------------------------------------------- strict structured outputs
_ITEM = '[]'
_COMPOSITE = ('anyOf', 'oneOf', 'allOf')


def _is_object(schema):
    kind = schema.get('type')
    return kind == 'object' or (isinstance(kind, list) and 'object' in kind) or 'properties' in schema


def _nullable(schema):
    """The same constraint, also admitting null; never a duplicate null."""
    kind = schema.get('type')
    if isinstance(kind, str):
        return {**schema, 'type': [kind, 'null']} if kind != 'null' else schema
    if isinstance(kind, list):
        return schema if 'null' in kind else {**schema, 'type': [*kind, 'null']}
    if 'enum' in schema:
        return schema if None in schema['enum'] else {**schema, 'enum': [*schema['enum'], None]}
    if 'anyOf' in schema and len(schema) == 1:
        branches = schema['anyOf']
        return schema if {'type': 'null'} in branches else {'anyOf': [*branches, {'type': 'null'}]}
    return {'anyOf': [schema, {'type': 'null'}]}


def _strict(schema, path, optional):
    if not isinstance(schema, dict):
        return schema
    result = dict(schema)
    if _is_object(schema):
        properties = schema.get('properties')
        extra = schema.get('additionalProperties', True)
        if not isinstance(properties, dict) or not properties or (extra is not False and extra is not True):
            # A free-form object or a map cannot be expressed in strict mode; narrowing it would
            # change its meaning, so the transform refuses instead.
            raise ProviderError('UNSUPPORTED', 'SCHEMA_NOT_STRICT')
        required = set(schema.get('required', ()))
        rebuilt = {}
        for name, child in properties.items():
            converted = _strict(child, (*path, name), optional)
            if name not in required:
                optional.add((*path, name))
                converted = _nullable(converted)
            rebuilt[name] = converted
        result.update(properties=rebuilt, required=list(properties), additionalProperties=False)
    if isinstance(schema.get('items'), dict):
        result['items'] = _strict(schema['items'], (*path, _ITEM), optional)
    for keyword in _COMPOSITE:
        if isinstance(schema.get(keyword), list):
            result[keyword] = [_strict(branch, path, optional) for branch in schema[keyword]]
    return result


def strict_schema(schema):
    """Return (strict schema, optional paths) for OpenAI-style strict structured outputs.

    Every object lists all its properties in ``required`` and sets ``additionalProperties``
    false; a property that was optional becomes nullable and its path (property names, with
    ``[]`` for array items) is returned so ``drop_optional_nulls`` can restore the original
    shape. Enums, consts and every other constraint are kept. Pure: the input is not changed.
    A free-form object or a map is refused with UNSUPPORTED SCHEMA_NOT_STRICT.
    """
    optional = set()
    return _strict(schema, (), optional), frozenset(optional)


def drop_optional_nulls(value, optional_paths):
    """Remove keys that were optional in the original schema and came back null (strict-mode filler)."""
    return _drop(value, (), frozenset(optional_paths))


def _drop(value, path, optional):
    if isinstance(value, dict):
        return {key: _drop(child, (*path, key), optional) for key, child in value.items()
                if not (child is None and (*path, key) in optional)}
    if isinstance(value, list):
        return [_drop(child, (*path, _ITEM), optional) for child in value]
    return value
