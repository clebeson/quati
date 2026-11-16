"""Owner-only LOCAL bootstrap and real Ed25519 device proof (RFC-013)."""
from datetime import datetime, timedelta, timezone
import base64
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
import uuid

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from platformdirs import user_config_path

from quati.application.identity import AccessDenied, LocalToken, RequestContext, canonical_bytes, verify_token


TENANT_ROLES = ('OWNER', 'ADMIN', 'MEMBER', 'GUEST')      # contracts/identity.schema.json LocalInstallationRecord
# The identifiers every command reads from the signed record (RFC-013 section 4); each is a non-empty string.
IDENTIFIER_FIELDS = ('tenant_id', 'principal_id', 'personal_space_id', 'organization_space_id')
ULID = re.compile(r'[0-9A-HJKMNP-TV-Z]{26}')              # contracts/identity.schema.json #/$defs/Ulid


def _ulid():
    alphabet = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
    value = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    return ''.join(alphabet[(value >> shift) & 31] for shift in range(125, -1, -5))


def _no_symlinks(path):
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AccessDenied()


def _private_stat(info, directory=False):
    valid_kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not valid_kind or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise AccessDenied()
    if not directory and info.st_nlink != 1:              # a second name for a credential file (LOG-0044 X11)
        raise AccessDenied()


def _read_private(path):
    _no_symlinks(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        _private_stat(os.fstat(stream.fileno()))
        value = stream.read(16385)
    if len(value) > 16384:
        raise AccessDenied()
    return value


def _create_private(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


class LocalIdentity:
    """POSIX reference adapter; other operating systems require their own qualification."""

    def __init__(self, directory=None):
        self.directory = Path(directory or os.environ.get('QUATI_CONFIG_DIR') or user_config_path('quati')).absolute()
        self.key_path = self.directory / 'device.key'
        self.record_path = self.directory / 'identity.json'

    def _check_process(self):
        if not hasattr(os, 'getuid') or not hasattr(os, 'O_NOFOLLOW') or os.environ.get('QUATI_CAPABILITY_CONTEXT'):
            raise AccessDenied()
        _no_symlinks(self.directory)

    def diagnostics(self):
        try:
            self._load()
        except AccessDenied:
            return {'initialized': False, 'authenticator': 'local-os', 'secret_store': 'owner_only_file',
                    'status': 'NOT_CONFIGURED', 'qualification': 'POSIX_LOCAL_ONLY'}
        return {'initialized': True, 'authenticator': 'local-os', 'secret_store': 'owner_only_file',
                'status': 'AVAILABLE', 'qualification': 'POSIX_LOCAL_ONLY'}

    def initialize(self):
        self._check_process()
        if self.record_path.exists():
            record, _ = self._load()
            return self._summary(record)
        try:
            self.directory.mkdir(parents=True, mode=0o700, exist_ok=True)
            _private_stat(self.directory.stat(), directory=True)
            if self.key_path.exists():
                raise AccessDenied()
            key = Ed25519PrivateKey.generate()
            record = {'schema_version': 'quati-local-identity/1', 'owner_uid': os.getuid(),
                      'tenant_id': _ulid(), 'principal_id': _ulid(),
                      'personal_space_id': _ulid(), 'organization_space_id': _ulid(),
                      'public_key': base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')}
            signed = dict(record, signature=base64.b64encode(key.sign(canonical_bytes(record))).decode('ascii'))
            _create_private(self.key_path, key.private_bytes(serialization.Encoding.Raw,
                            serialization.PrivateFormat.Raw, serialization.NoEncryption()))
            _create_private(self.record_path, canonical_bytes(signed))
            descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return self._summary(record)
        except (OSError, ValueError) as exc:
            raise AccessDenied() from exc

    @staticmethod
    def _summary(record):
        return {'initialized': True, 'tenant_id': record['tenant_id'], 'principal_id': record['principal_id'],
                'secret_store': 'owner_only_file', 'profile': 'LOCAL'}

    def _load(self):
        self._check_process()
        try:
            _private_stat(self.directory.stat(), directory=True)
            signed = json.loads(_read_private(self.record_path))
            if not isinstance(signed, dict):
                raise AccessDenied()
            signature = base64.b64decode(signed.pop('signature'), validate=True)
            key = Ed25519PrivateKey.from_private_bytes(_read_private(self.key_path))
            public = base64.b64decode(signed['public_key'], validate=True)
            Ed25519PublicKey.from_public_bytes(public).verify(signature, canonical_bytes(signed))
            if signed['owner_uid'] != os.getuid() or key.public_key().public_bytes_raw() != public:
                raise AccessDenied()
            # A correctly signed record is still a rejected credential when an identifier it must carry is
            # absent, not a string or not a ULID (LOG-0041 N10, LOG-0044 X11): typed here, never a KeyError
            # in a command, and consistent with the token check every command applies.
            if not all(isinstance(signed.get(name), str) and ULID.fullmatch(signed[name])
                       for name in IDENTIFIER_FIELDS):
                raise AccessDenied()
            return signed, key
        except (OSError, ValueError, KeyError, TypeError, InvalidSignature, RecursionError) as exc:
            raise AccessDenied() from exc

    @staticmethod
    def _mint_token(record, key):
        now = int(time.time())
        claims = {'iss': 'quati-local', 'sub': record['principal_id'], 'tid': record['tenant_id'],
                  'pkind': 'HUMAN', 'aud': 'quati-local', 'scope': 'quati:converse quati:work.read',
                  'exp': now + 600, 'iat': now, 'nbf': now, 'jti': uuid.uuid4().hex,
                  'sid': uuid.uuid4().hex, 'amr': ['local_os', 'device_key'], 'auth_time': now,
                  'client_id': 'quati-cli'}
        token = LocalToken(claims, key.sign(canonical_bytes(claims)))
        return token, key.public_key().public_bytes_raw()

    def issue_token(self):
        return self._mint_token(*self._load())

    def _membership(self, context):
        """(signed record, tenant role) of the context's principal; the role is None without a membership.

        ``quati init`` creates the tenant OWNER and writes no role; an absent ``tenant_role`` is OWNER.
        A record that carries another RFC-013 tenant role is honoured (1<=>N rule); any other value is
        no membership at all."""
        record, _key = self._load()
        if (context.actor_id, context.tenant_id) != (record['principal_id'], record['tenant_id']):
            return record, None
        role = record.get('tenant_role', 'OWNER')
        return record, role if isinstance(role, str) and role in TENANT_ROLES else None

    def tenant_role(self, context):
        """RFC-013 section 2 Membership of the LOCAL principal, read live from the signed record."""
        return self._membership(context)[1]

    def space_grants(self, context):
        """RFC-013 section 2.1 default grants, read live from the signed record: the personal space,
        and the organization space for OWNER, ADMIN and MEMBER (a GUEST gets no ORGANIZATION grant)."""
        record, role = self._membership(context)
        if role is None:
            return ()
        if role == 'GUEST':
            return (record['personal_space_id'],)
        return record['personal_space_id'], record['organization_space_id']

    def registry_space(self, tenant_id):
        """The space that owns the tenant's capability registry: the tenant's ORGANIZATION space, as
        recorded in the signed installation record. Never derived from a request."""
        record, _key = self._load()
        return record['organization_space_id'] if record['tenant_id'] == tenant_id else None

    def authenticate(self):
        record, key = self._load()
        token, public = self._mint_token(record, key)
        claims = verify_token(token, public)
        return RequestContext(actor_id=claims['sub'], tenant_id=claims['tid'],
                              space_ids=(record['personal_space_id'], record['organization_space_id']),
                              request_id='request-' + uuid.uuid4().hex, trace_id=uuid.uuid4().hex,
                              session_id=claims['sid'], token_jti=claims['jti'],
                              authenticated_origin_ref='local-os:device-key',
                              deadline_at=(datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat())
