"""LOCAL identity records and guards; request text never grants authority."""
from dataclasses import dataclass
import json
import re
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class AccessDenied(Exception):
    """A safe, typed authentication or authorization failure."""

    def __init__(self, code='UNAUTHENTICATED'):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class LocalToken:
    claims: dict
    signature: bytes


@dataclass(frozen=True)
class RequestContext:
    actor_id: str
    tenant_id: str
    space_ids: tuple[str, ...]
    request_id: str
    trace_id: str
    session_id: str
    token_jti: str
    authenticated_origin_ref: str
    deadline_at: str
    policy_version: str = 's00-fixture-readonly/1'
    schema_version: str = 'quati-context/2'
    channel: str = 'cli'
    principal_kind: str = 'HUMAN'
    profile: str = 'LOCAL'


def _check_json_keys(value):
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError('Canonical JSON requires string keys')
        for item in value.values():
            _check_json_keys(item)
    elif isinstance(value, list):
        for item in value:
            _check_json_keys(item)


def canonical_bytes(value):
    _check_json_keys(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def _valid_local_claims(claims, audience, current):
    strings = {'iss', 'sub', 'tid', 'pkind', 'aud', 'scope', 'jti', 'sid', 'client_id'}
    integers = {'exp', 'iat', 'nbf', 'auth_time'}
    if set(claims) != strings | integers | {'amr'}:
        return False
    if not all(isinstance(claims[name], str) and claims[name] for name in strings):
        return False
    if not all(type(claims[name]) is int for name in integers):
        return False
    if not all(re.fullmatch(r'[0-9A-HJKMNP-TV-Z]{26}', claims[name]) for name in ('sub', 'tid')):
        return False
    return (claims['iss'] == 'quati-local' and claims['aud'] == audience
            and claims['pkind'] == 'HUMAN' and claims['nbf'] <= current < claims['exp']
            and claims['iat'] <= current and 0 < claims['exp'] - claims['iat'] <= 600
            and isinstance(claims['amr'], list) and set(claims['amr']) == {'local_os', 'device_key'}
            and claims['scope'] == 'quati:converse quati:work.read'
            and claims['client_id'] == 'quati-cli' and len(claims['jti']) >= 16
            and claims['auth_time'] <= current)


def verify_token(token, public_key, audience='quati-local', now=None):
    """Verify the actual device signature and the bounded in-process token claims."""
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(token.signature, canonical_bytes(token.claims))
        if not _valid_local_claims(token.claims, audience, int(time.time() if now is None else now)):
            raise AccessDenied()
        return dict(token.claims)
    except (InvalidSignature, ValueError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        raise AccessDenied() from exc


def authorize_read(context, tenant_id, space_id):
    """Apply the same tenant/space guard for one principal as for many."""
    if (not isinstance(context, RequestContext) or not context.actor_id
            or context.tenant_id != tenant_id or space_id not in context.space_ids):
        raise AccessDenied('FORBIDDEN')
    return True
