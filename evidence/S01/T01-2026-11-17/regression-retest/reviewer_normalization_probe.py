import sys, copy, json, hashlib
sys.path.insert(0, '/home/clebeson/dev/SECMA/tests/unit'); sys.path.insert(0, '/home/clebeson/dev/SECMA/src')
import s00_fix8_support as s
def resp():
    return {"status":"SUCCEEDED","data":{"request_id":"r","trace_id":"t","reason":"X","launched":False,
        "conversation":{"id":"c1","revision":1,"lifetime":"PROCESS_ONLY","continues_after_exit":False}},
        "evidence_refs":["e"],"uncertainties":[],"next_action":None,"error":None}
def good_hash(v):
    return hashlib.sha256(json.dumps({**v,"evidence_refs":[]},sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
state={}
s.receipt=lambda v:{"output_hash":state["h"]}
def attempt(name, mutate, conv=True, tamper_hash=False, expect_reject=True):
    v=resp(); mutate(v); state["h"]=good_hash(resp()) if not tamper_hash else "0"*64
    if tamper_hash is False and name!="baseline": state["h"]=good_hash(v)
    try: s.stable(v, conversation=conv); ok=True
    except AssertionError: ok=False
    res = "PASS" if ok != expect_reject else "WRONG"
    print(f"{res:5} {name}: {'accepted' if ok else 'rejected'}")
    return res
r=[]
r.append(attempt("baseline valid metadata", lambda v:None, expect_reject=False))
r.append(attempt("missing conversation", lambda v:v["data"].pop("conversation")) ) if False else None
def miss(v): v["data"].pop("conversation")
try:
    v=resp(); miss(v); s.stable(v,conversation=True); print("WRONG missing metadata accepted")
except KeyError: print("PASS  missing metadata: rejected (KeyError)")
r.append(attempt("extra conversation key", lambda v:v["data"]["conversation"].update(work_id="w")))
r.append(attempt("lifetime DURABLE", lambda v:v["data"]["conversation"].update(lifetime="DURABLE")))
r.append(attempt("continues_after_exit true", lambda v:v["data"]["conversation"].update(continues_after_exit=True)))
r.append(attempt("revision 0", lambda v:v["data"]["conversation"].update(revision=0)))
r.append(attempt("revision bool True", lambda v:v["data"]["conversation"].update(revision=True)))
r.append(attempt("revision str", lambda v:v["data"]["conversation"].update(revision="1")))
r.append(attempt("empty id", lambda v:v["data"]["conversation"].update(id="")))
r.append(attempt("receipt hash mismatch", lambda v:None, tamper_hash=True))
r.append(attempt("one-shot carrying conversation", lambda v:None, conv=False))
# content preserved: metadata normalization must not hide other differences
state["h"]=good_hash(resp()); a=resp(); b=resp(); b["data"]["reason"]="Y"; b["data"]["conversation"]["id"]="c2"
state["h"]=good_hash(a); sa=s.stable(a,conversation=True)
state["h"]=good_hash(b); sb=s.stable(b,conversation=True)
print("PASS  other-content difference survives normalization" if sa!=sb else "WRONG content difference hidden")
# different id/revision alone are normalized away (intended)
c=resp(); c["data"]["conversation"].update(id="zz",revision=7); state["h"]=good_hash(c); sc=s.stable(c,conversation=True)
print("INFO  id/revision-only difference normalized:", sa==sc)
# classification shape: fail_closed literal vs tampered
