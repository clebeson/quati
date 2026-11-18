"""LOCAL identity records and guards; request text never grants authority."""
from dataclasses import asdict, dataclass
import json
import re
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from quati.domain.capability_registry import iso


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
    policy_version: str | None = None
    schema_version: str = 'quati-context/2'
    channel: str = 'cli'
    principal_kind: str = 'HUMAN'
    profile: str = 'LOCAL'
    act: None = None

    def to_wire(self) -> dict:
        """Serialize the complete direct context; an unknown policy never grants authority."""
        if self.policy_version is not None and (
                not isinstance(self.policy_version, str) or not self.policy_version):
            raise ValueError('Context policy version must be null or a nonempty string')
        wire = asdict(self)
        # Delegation is unavailable in direct LOCAL contexts.
        wire['act'] = None
        return json.loads(canonical_bytes(wire))


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


@dataclass(frozen=True)
class AuthorizedScope:
    """``contracts/identity.schema.json#/$defs/AuthorizedScope``; valid for one transaction only."""
    tenant_id: str
    principal_id: str
    purpose: str
    readable_space_ids: tuple[str, ...]
    computed_at: str
    valid_for_transaction: str

    def to_json(self):
        return {**asdict(self), 'readable_space_ids': list(self.readable_space_ids)}


@dataclass(frozen=True)
class AuthzDecision:
    """``contracts/identity.schema.json#/$defs/AuthzDecision``; valid for one transaction only."""
    verdict: str
    reason_code: str
    tenant_id: str
    principal_id: str
    action: str
    resource_ref: str

    def to_json(self):
        return asdict(self)


@dataclass(frozen=True)
class AuthzEvaluation:
    """One decision, the AuthorizedScope it was evaluated against (or None) and the space that owns
    the resource as the directory resolved it (or None). Valid for one transaction only."""
    decision: AuthzDecision
    scope: AuthorizedScope | None
    space_id: str | None


REGISTRY_MANAGER_ROLES = ('OWNER', 'ADMIN')


class ScopeAuthorization:
    """S00 AuthorizationPort (RFC-013 sections 6 and 10; M02 authorization order rows 4 and 7).

    Default deny. ``directory`` is the S00 identity directory (LOCAL: the signed installation
    record). It is read again at every check, so a removed grant takes effect at the next check:

    * ``space_grants(context)`` - the space ids the context's principal may read;
    * ``tenant_role(context)`` - the principal's tenant role, or None when it has no membership;
    * ``registry_space(tenant_id)`` - the space that OWNS the tenant's capability registry.

    Nothing is taken from the request: ``RequestContext.space_ids`` is not an authorization input.
    Resources and actions that can be allowed (everything else is denied):

    * ``registry:<tenant_id>`` - ``read`` needs a grant on the owning space; ``manage`` (install,
      enable, disable) needs that grant and the tenant role OWNER or ADMIN (RFC-013 section 6);
    * ``space:<space_id>`` - ``read`` needs a grant on that space.

    One principal goes through the same code as many.
    """

    def __init__(self, directory, clock):
        self.directory = directory
        self.clock = clock

    def authorized_scope(self, context, purpose):
        """The readable spaces for this transaction, or None when no valid scope can be resolved."""
        try:
            granted = self.directory.space_grants(context)
        except Exception:  # noqa: BLE001 - an unreadable grant source is a missing scope: deny by default
            return None
        if not isinstance(granted, (tuple, list)) or not all(isinstance(item, str) and item for item in granted):
            return None
        return AuthorizedScope(context.tenant_id, context.actor_id, purpose, tuple(dict.fromkeys(granted)),
                               iso(self.clock()), context.request_id)

    def _registry_space(self, tenant_id):
        try:
            space_id = self.directory.registry_space(tenant_id)
        except Exception:  # noqa: BLE001 - an unresolvable owner is in no scope: deny by default
            return None
        return space_id if isinstance(space_id, str) and space_id else None

    def _tenant_role(self, context):
        try:
            return self.directory.tenant_role(context)
        except Exception:  # noqa: BLE001 - an unreadable membership is no role: deny by default
            return None

    def decide(self, context, action, resource_ref):
        """Return the AuthzEvaluation of ``action`` on ``resource_ref`` for the context's principal."""
        scope = self.authorized_scope(context, action)
        readable = () if scope is None else scope.readable_space_ids
        kind, _, name = resource_ref.partition(':') if isinstance(resource_ref, str) else ('', '', '')
        space_id = None
        if kind == 'registry':
            if name != context.tenant_id:
                reason = 'TENANT_MISMATCH'
            else:
                space_id = self._registry_space(name)
                if space_id is None or space_id not in readable:
                    reason = 'NO_SPACE_GRANT'
                elif action == 'read' or (action == 'manage'
                                          and self._tenant_role(context) in REGISTRY_MANAGER_ROLES):
                    reason = 'OK'
                else:
                    reason = 'ROLE_INSUFFICIENT'
        elif kind != 'space' or name not in readable:
            reason = 'NO_SPACE_GRANT'
        else:
            space_id = name
            reason = 'OK' if action == 'read' else 'ROLE_INSUFFICIENT'
        decision = AuthzDecision('ALLOW' if reason == 'OK' else 'DENY', reason, context.tenant_id, context.actor_id,
                                 action, resource_ref)
        return AuthzEvaluation(decision, scope, space_id)

    def check(self, context, action, resource_ref):
        return self.decide(context, action, resource_ref).decision
