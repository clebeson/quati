"""Local request receipts, exclusive creation and hash integrity (not WORM storage)."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import uuid

from quati.adapters.private_fs import state_directory
from quati.application.code_identity import current_code_digest
from quati.behavior.contracts import asset_digest


class ReceiptNotWritten(OSError):
    """The evidence receipt of an operation could not be written; the operation itself may have run."""


def redact(value):
    """Redact string leaves while preserving public protocol keys and control enums."""
    name = os.environ.get('QUATI_API_KEY_ENV', 'QUATI_API_KEY')
    secret = os.environ.get(name, '')
    controls = {
        'status': {'SUCCEEDED', 'PARTIAL', 'BLOCKED', 'DENIED', 'UNAVAILABLE', 'CONFLICT',
                   'RESPONDED', 'FIXTURE_RESULT', 'DIAGNOSTIC'},
        'result_status': {'RESPONDED', 'FIXTURE_RESULT'},
        'proof_tier': {'L0', 'L1', 'L2', 'L3', 'L4', 'L5'},
        'code': {'INVALID_INPUT', 'UNAUTHENTICATED', 'FORBIDDEN', 'APPROVAL_REQUIRED', 'REVISION_CONFLICT',
                 'IDEMPOTENCY_CONFLICT', 'NOT_FOUND', 'NOT_CONFIGURED', 'CONFIG_INVALID', 'UNSUPPORTED',
                 'TEMPORARILY_UNAVAILABLE', 'DEADLINE_EXCEEDED', 'BUDGET_EXCEEDED', 'OUTPUT_INVALID',
                 'EVIDENCE_INSUFFICIENT', 'EFFECT_UNCERTAIN', 'INTERNAL_ERROR'},
    }
    def clean(item, key=None):
        if isinstance(item, dict):
            return {field: clean(content, field) for field, content in item.items()}
        if isinstance(item, list):
            return [clean(content) for content in item]
        if isinstance(item, str) and secret and item not in controls.get(key, set()):
            return item.replace(secret, '[REDACTED]')
        return item
    return clean(value)


def receipts_directory():
    """The receipt directory after the chain check: the data directory and ``receipts/`` are real,
    owner-only directories of this user, whatever the umask (or ``UnsafeStatePath``)."""
    return state_directory('receipts')


def bound_to_code(value):
    """``value`` with ``digests.code_digest`` and ``digests.asset_digest`` set to the digests of the
    running package and of the asset files it loads (audit P2-E, LOG-0044 X15).

    Every receipt passes through here, whatever its kind (request, capability command, feature report,
    audit event), so a record can always be bound to the code and assets that wrote it. Each value comes
    from the one function that computes it and is never taken from the caller."""
    digests = value.get('digests')
    return {**value, 'digests': {**(digests if isinstance(digests, dict) else {}),
                                 'code_digest': current_code_digest(), 'asset_digest': asset_digest()}}


def write_receipt(value):
    directory = receipts_directory()
    record = redact({**bound_to_code(value), 'timestamp':datetime.now(timezone.utc).isoformat(),
                     'evidence_version':'s00/1'})
    blob = json.dumps(record, indent=2, sort_keys=True).encode() + b'\n'
    path = directory / (uuid.uuid4().hex + '.json')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    return {'path':str(path), 'sha256':sha256(blob).hexdigest()}


def receipt_sink(value):
    """The evidence sink of a use case that has already acted: a failure names the missing receipt only."""
    try:
        return write_receipt(value)
    except OSError as exc:
        raise ReceiptNotWritten() from exc
