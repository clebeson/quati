import json, sys, re, hashlib, itertools
from pathlib import Path
R = Path('<local-path>')
sys.path.insert(0, str(R/'src')); sys.path.insert(0, str(R/'tests/evals'))
from quati.application.code_identity import current_code_digest
from quati.domain.social import social_match
import live_harness as h
print('product digest', current_code_digest()); print('harness digest', h.code_digest(h.SOURCE/'quati'))
D = R/'tests/evals/datasets'
soc = json.loads((D/'soc01_gate.json').read_text())
for leg, v in soc['legs'].items():
    for t in v['texts']:
        print(leg, repr(t), 'TABLE' if social_match(t) else 'model')
for t in [u['text'] for u in json.loads((D/'write_attempts.json').read_text())['utterances']]:
    print('write', repr(t), 'TABLE' if social_match(t) else 'model')
def norm(s): return re.sub(r'\s+', ' ', s.lower().strip())
def toks(s): return set(re.findall(r'\w+', s.lower()))
def texts(name):
    d = json.loads((D/name).read_text()); return [u['text'] if isinstance(u, dict) else u for u in d['utterances']]
for c in ('cap01', 'cap02'):
    g, ho = texts(f'{c}_paraphrases.json'), texts(f'{c}_heldout.json')
    print(c, 'gate n', len(g), 'heldout n', len(ho), 'exact overlap', set(map(norm, g)) & set(map(norm, ho)))
    best = sorted(((len(toks(a)&toks(b))/len(toks(a)|toks(b)), a, b) for a in ho for b in g), reverse=True)[:4]
    for j, a, b in best: print('  jaccard %.2f | %s | %s' % (j, a, b))
    for t in ho + g:
        for term in ('lime', 'quick', 'publish', 'calendar-read', 'calendar', 'mail', 'fixture', 'forecast-', 'quati', 'capabilit'):
            if term in t.lower(): print('  TERM', term, '|', t)
