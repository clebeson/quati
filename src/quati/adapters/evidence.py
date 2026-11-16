"""Local request receipts, exclusive creation and hash integrity (not WORM storage)."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import uuid

from quati.adapters.private_fs import private_directory


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


def write_receipt(value):
    directory = Path(os.environ.get('QUATI_DATA_DIR', str(Path.home() / '.quati'))) / 'receipts'
    if any(p.is_symlink() for p in [directory, *directory.parents]):
        raise OSError('Evidence directory cannot traverse symlinks')
    private_directory(directory.parent)  # the data directory itself is owner-only, whatever the umask
    private_directory(directory)
    record = redact({**value, 'timestamp':datetime.now(timezone.utc).isoformat(), 'evidence_version':'s00/1'})
    blob = json.dumps(record, indent=2, sort_keys=True).encode() + b'\n'
    path = directory / (uuid.uuid4().hex + '.json')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    return {'path':str(path), 'sha256':sha256(blob).hexdigest()}
