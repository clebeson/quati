import sys; sys.path.insert(0,'<local-path>'); sys.path.insert(0,'.')
from quati.domain.social import social_match, words
from d1_texts import T
for t,e in T:
    m = social_match(t)
    got = 'S' if m else 'W'
    flag = '' if got==e else ('  <<< WORK-LOOKING TEXT ANSWERED AS GREETING' if e=='W' else '  <<< social text not in table (model path)')
    w = words(t)
    print(got, e, repr(t[:60]), (m.reply if m else None), list(w[:8]) if len(w)<12 else f'{len(w)} words', flag)
