import json, sys
from quati.behavior.compiler import BehaviorCompiler
root, ref = sys.argv[1], sys.argv[2]
try:
    a = BehaviorCompiler(root).compile(ref)
    print(json.dumps({'ok': True, 'receipt': a.receipt, 'build_digest': a.build_digest, 'text_sha': __import__('hashlib').sha256(a.text.encode()).hexdigest()}, sort_keys=True))
except Exception as exc:
    d = {'ok': False, 'type': type(exc).__name__}
    for k in ('code', 'reason', 'path', 'message', 'diagnostics'):
        v = getattr(exc, k, None)
        d[k] = str(v) if v is not None and not isinstance(v, (list, tuple)) else ([str(x) for x in v] if v else None)
    d['str'] = str(exc)[:500]
    print(json.dumps(d, sort_keys=True))
