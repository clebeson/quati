"""Local request receipts, exclusive creation and hash integrity (not WORM storage)."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import uuid


def redact(value):
    text = json.dumps(value, sort_keys=True, ensure_ascii=True)
    name = os.environ.get('SECMA_API_KEY_ENV', 'SECMA_API_KEY')
    secret = os.environ.get(name, '')
    if secret:
        text = text.replace(json.dumps(secret)[1:-1], '[REDACTED]')
    return json.loads(text)


def write_receipt(value):
    directory = Path(os.environ.get('SECMA_DATA_DIR', str(Path.home() / '.secma'))) / 'receipts'
    if any(p.is_symlink() for p in [directory, *directory.parents]):
        raise OSError('Evidence directory cannot traverse symlinks')
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    record = redact({**value, 'timestamp':datetime.now(timezone.utc).isoformat(), 'evidence_version':'s00/1'})
    blob = json.dumps(record, indent=2, sort_keys=True).encode() + b'\n'
    path = directory / (uuid.uuid4().hex + '.json')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())
    return {'path':str(path), 'sha256':sha256(blob).hexdigest()}
