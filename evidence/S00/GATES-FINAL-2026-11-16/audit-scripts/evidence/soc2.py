import json,collections
EV='<local-path>'
d=json.load(open(EV+'SOC-01.json'))
r=d['legs']['c_outside_table_greeting']['records'][0]
for k in ['answer_label_not_blocked','audit','checks','error_code','executed','exit','label','model_text_hits','outcome','outcome_class','provider_used','read_executed','response','usage','receipt']:
    print(k,json.dumps(r[k])[:1500])
r=d['legs']['d_greeting_led_work']['records'][0]
for k in ['audit','response','outcome','label','executed']:
    print('D',k,json.dumps(r[k])[:1500])
