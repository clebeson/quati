import sys,hashlib,json
from pathlib import Path
def code_digest(root):
    entries = sorted((str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in root.rglob('*.py') if '__pycache__' not in p.parts)
    return hashlib.sha256(json.dumps(entries, separators=(',', ':')).encode()).hexdigest()
for r in sys.argv[1:]:
    print(r, code_digest(Path(r)/'src/quati') )
