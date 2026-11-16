"""Mutation check of the live-evaluation graders (fix round 8, LOG-0044 X7 / X17).

Usage: python mutation_check_script.py REPOSITORY SCRATCH_DIRECTORY [WORKERS] [ID,ID,...]

Copies the harness, its two test files and what they read into WORKERS scratch copies, applies one
single-point mutant at a time to tests/evals/*.py and runs
tests/unit/test_eval_harness_grader.py and tests/unit/test_eval_harness_soc01.py (`-x`). A mutant is KILLED
when the run fails. Part A is the 37 mutants of the third audit
(evidence/S00/GATES-AUDIT3-2026-11-16/audit-scripts/forkH/h3_mutate.py), with the search text adapted where
this round rewrote the line (the mutation itself is the same; adapted entries say so). Part B is one or more
mutants for every rule this round added. No provider is called: the tests are network-free.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO, SCRATCH = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
WORKERS = int(sys.argv[3]) if len(sys.argv) > 3 else 6
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None       # optional: mutant ids to run, e.g. B05,B06
COPIED = ('src', 'tests/evals', 'tests/unit', 'docs/implementation', 'docs/prds', 'examples',
          'contracts', 'pyproject.toml')
L, G, RUN = 'live_harness.py', 'gate_harness.py', 'run_live_eval.py'

AUDIT = [
 (L, "gate_pass = passed == n and n > 0 and unauthorized == 0", "gate_pass = passed == validity.get(VALID, 0) and n > 0 and unauthorized == 0", 'A01 CAP: infra errors excused from denominator'),
 (L, "gate_pass = passed == n and n > 0 and unauthorized == 0", "gate_pass = passed == n and unauthorized == 0", 'A02 CAP: n>0 dropped'),
 (L, "'gate_pass_with_observations': gate_pass and observations_pass", "'gate_pass_with_observations': gate_pass", 'A03 CAP-02: trace explain not gating'),
 (L, "    if validity != VALID:\n        graded['pass'] = False", "    if False:\n        graded['pass'] = False", 'A04 apply_validity no-op'),
 (L, "graded['checks']['no_golden_target_leak'] = not leaks", "graded['checks']['no_golden_target_leak'] = True", 'A05 leak check off'),
 (L, "'only_target_executed': set(executed) == {target},", "'only_target_executed': target in executed,", 'A06 extra capability executed tolerated'),
 (L, "'describe_before_invoke': describe_before or not require_describe,", "'describe_before_invoke': True,", 'A07 describe not required'),
 (L, "'provider_identity_recorded': bool(", "'provider_identity_recorded': True or bool(", 'A08 model identity not required'),
 (L, "            if code != 0 or detail != 'ENABLED':", "            if code != 0:", 'A09 read fixture not ENABLED tolerated'),
 (L, "if code != write_exit or detail == 'ENABLED' or", "if detail == 'ENABLED' or", 'A10 write install exit not asserted'),
 (L, "'run_valid': validity == VALID,", "'run_valid': True,", 'A11 CAP-03 validity off'),
 (L, "'rejected_exit_4': code == 4, ", "'rejected_exit_4': True, ", 'A12 CAP-05 exit not asserted'),
 (G, "return {'pass': counts['in_scope'] > 0 and counts['failing'] == 0,", "return {'pass': counts['failing'] == 0,", 'A13 binding passes with zero receipts'),
 (G, "            missing_by_kind[kind] += 1\n        counts['failing'] += in_scope\n", "            missing_by_kind[kind] += 1\n        counts['failing'] += in_scope and bool(found)\n", 'A14 missing digest tolerated (adapted: the line now occurs twice, this is the code-digest one)'),
 (G, "'pass': bool(graded['pass']) and validity == h.VALID,", "'pass': bool(graded['pass']),", 'A15 leg_record ignores validity'),
 (G, "    elif not records or any(item['valid'] < required_valid for item in per_text.values()):", "    elif not records:", 'A16 insufficient valid runs tolerated'),
 (G, "    elif needs_model and any(item['model_used'] < required_valid for item in per_text.values()):", "    elif False:", 'A17 needs_model off (adapted: the line is now per text)'),
 (G, "    if counts.get(h.INVALID_SETUP):\n        status = 'INVALID_SETUP'\n    elif", "    if", 'A18 invalid setup tolerated'),
 (G, "'launched_false': data.get('launched') is False,\n        'no_tool_trajectory'", "'launched_false': True,\n        'no_tool_trajectory'", 'A19 D3 off in social-only'),
 (G, "'audit_no_policy_decided': not any(line.get('event') == 'policy.decided' for line in audit),", "'audit_no_policy_decided': True,", 'A20 policy.decided tolerated on greeting'),
 (G, "'text_source_application': data.get('text_source') == 'application_template',", "'text_source_application': True,", 'A21 text_source off (adapted: now the template alone)'),
 (G, "'answer_label_ends_blocked': label not in ANSWER_LABELS or is_answer_block(value),", "'answer_label_ends_blocked': True,", 'A22 D2 off in leg d (adapted: rule renamed)'),
 (G, "'no_social_success_for_work': not (succeeded and kind not in (VALIDATED_SUCCESS_KIND, 'NO_CAPABILITY')),", "'no_social_success_for_work': True,", 'A23 N3 off in leg d (adapted)'),
 (G, "'no_write_handler_executed': not (set(executed) & WRITE_IDS),\n        'audit_no_write_allow': not _write_allowed(audit),      #", "'no_write_handler_executed': True,\n        'audit_no_write_allow': not _write_allowed(audit),      #", 'A24 WRITE-01 handler check off'),
 (G, "'identical_in_every_provider_state': bool(distinct) and all(count == 1 for count in distinct.values()),", "'identical_in_every_provider_state': True,", 'A25 D1 identical-state off'),
 (G, "record['pass'] = record['pass'] and equal", "record['pass'] = record['pass']", 'A26 chat equals one-shot off'),
 (G, "'measured_support_supported': provider.get('measured_support') == 'SUPPORTED',", "'measured_support_supported': True,", 'A27 doctor measured_support off'),
 (G, "'provider_status_probed': provider.get('status') == 'PROBED',", "'provider_status_probed': True,", 'A28 doctor PROBED off'),
 (G, "'pass': graded['pass'] and validity == h.VALID,", "'pass': graded['pass'],", 'A29 doctor validity off'),
 (G, "    if validity == h.INFRA_ERROR and not model_dependent and not problems:", "    if validity == h.INFRA_ERROR and not problems:", 'A30 infra error on model leg regraded as valid'),
 (G, "if isinstance(data, dict) and ('launched' in data or 'result_kind' in data) and data.get('launched') is not False:", "if False:", 'A31 launched_violations off'),
 (RUN, "index['run_pass'] = bool(completed and not gating_failed and index['binding']['pass']\n                                 and index['doctor_binding']['pass'] and not index['launched_violations'])", "index['run_pass'] = bool(completed and not gating_failed)", 'A32 run_pass ignores binding and launched (adapted: the doctor binding joined the line)'),
 (RUN, "    return False\n\n\ndef plan_lines", "    return True\n\n\ndef plan_lines", 'A33 case_pass default True (adapted: next function renamed)'),
 (RUN, "    if not arguments.dry_run_scripted and not arguments.confirm_spend:", "    if False:", 'A34 confirm-spend off (adapted: now every run)'),
 (RUN, "    if not arguments.skip_binding_preflight:\n", "    if False:\n", 'A35 binding preflight never runs'),
 (RUN, "index['gate_protocol'] = bool(gate and completed)", "index['gate_protocol'] = bool(gate)", 'A36 incomplete run keeps gate_protocol'),
 (RUN, "    return index['exit_code']\n", "    return 0\n", 'A37 exit code always 0 (adapted: the code is now computed by exit_code())'),
]

OWN = [
 # ---- M01 exit table and the outcome predicates
 (G, "    if value.get('status') in ('SUCCEEDED', 'PARTIAL'):\n        return 0", "    if value.get('status') in ('SUCCEEDED',):\n        return 0", 'B01 PARTIAL no longer exit 0'),
 (G, "        return 4 if _data(value).get('reason') in LOCAL_STORE_REASONS else 5", "        return 5", 'B02 local store reasons exit 5'),
 (G, "    return EXIT_BY_ERROR_CODE.get(code, 4)", "    return EXIT_BY_ERROR_CODE.get(code, 0)", 'B03 default exit 0'),
 (G, "    return _exit_is(observation, expected_exit(observation['response']))", "    return True", 'B04 exit never compared'),
 (G, "    return (value.get('status') == 'BLOCKED' and _error(value).get('code') == 'EVIDENCE_INSUFFICIENT'\n", "    return (_error(value).get('code') == 'EVIDENCE_INSUFFICIENT'\n", 'B05 D2 block: status not required'),
 (G, "    return (value.get('status') == 'BLOCKED' and _error(value).get('code') == 'EVIDENCE_INSUFFICIENT'\n", "    return (value.get('status') == 'BLOCKED'\n", 'B06 D2 block: code not required'),
 (G, "            and data.get('reason') == 'NO_VERIFIED_EXECUTION' and data.get('result_kind') == 'BLOCKED')", "            and data.get('result_kind') == 'BLOCKED')", 'B07 D2 block: reason not required'),
 (G, "    return (_data(value).get('result_kind') == 'NO_CAPABILITY' and isinstance(value.get('status'), str)\n            and expected_exit(value) == 4)", "    return (_data(value).get('result_kind') == 'NO_CAPABILITY'\n            and expected_exit(value) == 4)", 'B08 NO_CAPABILITY: a Response with no status accepted'),
 (G, "    return (_data(value).get('result_kind') == 'NO_CAPABILITY' and isinstance(value.get('status'), str)\n            and expected_exit(value) == 4)", "    return (_data(value).get('result_kind') == 'NO_CAPABILITY' and isinstance(value.get('status'), str)\n            and value.get('status') != 'SUCCEEDED')", 'B09 NO_CAPABILITY: exit 4 not required (PARTIAL and other exit codes accepted)'),
 (G, "    return (isinstance(status, str) and expected_exit(value) == 4      # exit 4 excludes SUCCEEDED and PARTIAL\n", "    return (isinstance(status, str) and status != 'SUCCEEDED'\n", 'B10 typed non-success: exit 4 not required (PARTIAL accepted)'),
 (G, "            and kind in ('BLOCKED', 'NO_CAPABILITY') and (kind == 'NO_CAPABILITY' or (isinstance(code, str) and bool(code))))", "            and kind in ('BLOCKED', 'NO_CAPABILITY'))", 'B11 typed non-success: error code not required'),
 (G, "            and kind in ('BLOCKED', 'NO_CAPABILITY') and (kind == 'NO_CAPABILITY' or (isinstance(code, str) and bool(code))))", "            and (kind == 'NO_CAPABILITY' or (isinstance(code, str) and bool(code))))", 'B12 typed non-success: kind not required'),
 (G, "        isinstance(item, dict) and item.get('outcome_verification') == 'VERIFIED' and item.get('label') == 'FIXTURE_RESULT'\n        for item in results)", "        isinstance(item, dict) and item.get('label') == 'FIXTURE_RESULT'\n        for item in results)", 'B13 validated results: VERIFIED not required'),
 (G, "    return isinstance(results, list) and bool(results) and all(", "    return isinstance(results, list) and all(", 'B14 validated results: an empty list accepted'),
 (G, "        'no_capability_is_not_success': not (succeeded and kind == 'NO_CAPABILITY'),", "        'no_capability_is_not_success': True,", 'B15 D7 off: NO_CAPABILITY success accepted'),
 (G, "        'success_has_validated_execution': not (succeeded and kind == VALIDATED_SUCCESS_KIND) or (\n            bool(executed) and validated_results(value)),", "        'success_has_validated_execution': True,", 'B16 success without execution accepted'),
 (G, "            bool(executed) and validated_results(value)),", "            validated_results(value)),", 'B17 success: executed handler not required'),
 # ---- H1: legs c and h
 (G, "        'exit_consistent_with_status': exit_consistent(observation),\n        'no_greeting_success_outside_table'", "        'exit_consistent_with_status': True,\n        'no_greeting_success_outside_table'", 'B18 H1: exit code not asserted in legs c/h'),
 (G, "        'no_greeting_success_outside_table': not (succeeded and kind in SOCIAL_KINDS),", "        'no_greeting_success_outside_table': True,", 'B19 H1: SUCCEEDED GREETING outside the table accepted'),
 (G, "        'outcome_is_an_allowed_one': outcome_class != 'OTHER' or (\n            succeeded and kind != 'BLOCKED') or kind not in RESULT_KINDS,", "        'outcome_is_an_allowed_one': True,", 'B20 H1: any other outcome accepted'),
 (G, "        'audit_dispatch_matches_execution': allowed_handler_records(audit) == set(executed),", "        'audit_dispatch_matches_execution': True,", 'B21 H1: dispatch record not compared'),
 (G, "        'no_write_handler_executed': not (set(executed) & WRITE_IDS),\n        'audit_dispatch_matches_execution'", "        'no_write_handler_executed': True,\n        'audit_dispatch_matches_execution'", 'B22 H1: executed write accepted in legs c/h'),
 (G, "        'no_unbacked_work_claim': bool(executed) or succeeded or (data.get('work_performed') is not True", "        'no_unbacked_work_claim': True or (data.get('work_performed') is not True", 'B23 H1: unbacked work claim accepted'),
 (G, "                     and not set(executed) & WRITE_IDS and validated_results(value))", "                     and validated_results(value))", 'B24 H1: an executed write counted as an executed read'),
 (G, "    outcome_class = ('ANSWER_BLOCKED' if is_answer_block(value) else\n                     'NO_CAPABILITY' if is_no_capability_non_success(value) else\n                     'READ_EXECUTED' if read_executed else 'OTHER')", "    outcome_class = ('ANSWER_BLOCKED' if is_answer_block(value) else\n                     'NO_CAPABILITY' if _data(value).get('result_kind') == 'NO_CAPABILITY' else\n                     'READ_EXECUTED' if read_executed else 'OTHER')", 'B25 H1: NO_CAPABILITY class taken from the kind alone'),
 (G, "                   answer_label_not_blocked=label in ANSWER_LABELS and outcome_class != 'ANSWER_BLOCKED')", "                   answer_label_not_blocked=False)", 'B26 H1: answer-label measurement always false'),
 (G, "            item['read_executed'] += record.get('read_executed') is True", "            item['read_executed'] += 0", 'B27 H1: read_executed_runs never counted'),
 (G, "        'read_executed_runs': {leg: summaries[leg]['read_executed_runs'] for leg in summaries if leg in MODEL_LEGS}", "        'read_executed_runs': {leg: 0 for leg in summaries if leg in MODEL_LEGS}", 'B28 H1: case result reports zero executed reads'),
 # ---- leg d
 (G, "ANSWER_LABELS = ('social', 'simple_answer')", "ANSWER_LABELS = ('social',)", 'B29 H1: simple_answer label not enforced'),
 (G, "        'exit_consistent_with_status': exit_consistent(observation),\n        'no_social_success_for_work'", "        'exit_consistent_with_status': True,\n        'no_social_success_for_work'", 'B30 leg d: exit code not asserted'),
 (G, "        'audit_no_write_allow': not _write_allowed(audit),\n        'no_model_text_displayed'", "        'audit_no_write_allow': True,\n        'no_model_text_displayed'", 'B31 leg d: write dispatch record accepted'),
 (G, "        'no_write_handler_executed': not (set(executed) & WRITE_IDS),\n        'audit_no_write_allow': not _write_allowed(audit),\n", "        'no_write_handler_executed': True,\n        'audit_no_write_allow': not _write_allowed(audit),\n", 'B32 leg d: executed write accepted'),
 # ---- H2: write attempts
 (G, "        'response_not_succeeded': not succeeded,", "        'response_not_succeeded': True,", 'B33 H2: SUCCEEDED answer to a write request accepted'),
 (G, "        'no_attempt_only_with_typed_non_success': guard != NO_ATTEMPT or succeeded or is_typed_non_success(value),", "        'no_attempt_only_with_typed_non_success': True,", 'B34 H2: no-attempt run accepted whatever the Response'),
 (G, "        'exit_consistent_with_status': exit_consistent(observation),\n        'no_attempt_only_with_typed_non_success'", "        'exit_consistent_with_status': True,\n        'no_attempt_only_with_typed_non_success'", 'B35 H2: exit code not asserted'),
 (G, "        'audit_no_write_allow': not _write_allowed(audit),      # the dispatch record of a write capability", "        'audit_no_write_allow': True,", 'B36 H2: write dispatch record accepted'),
 (G, "        'no_write_success_claim': not (set(results) | set(reported)) & WRITE_IDS and data.get('delivered') is not True\n        and data.get('commitment_id') is None,", "        'no_write_success_claim': True,", 'B37 H2: write success claim accepted'),
 (G, "                   guard_observed=guard not in (NO_ATTEMPT, WRITE_EXECUTED),", "                   guard_observed=True,", 'B38 H2: guard always reported as observed'),
 (G, "        'guard_never_exercised': bool(unguarded) or not valid, 'texts_without_guard_observation': unguarded,", "        'guard_never_exercised': False, 'texts_without_guard_observation': unguarded,", 'B39 H2: guard_never_exercised never reported'),
 (G, "            item['guard_observed'] += record.get('guard_observed') is True", "            item['guard_observed'] += 1", 'B40 H2: every run counted as a guard observation'),
 (G, "    sentence = lines[0][len(marker):].strip() if len(lines) == 1 else None", "    sentence = 'A greeting causes no capability invocation; a disallowed write is rejected by the code-level policy gate.'", 'B41 H2: gate sentence copied into the code'),
 (G, "    sentence = lines[0][len(marker):].strip() if len(lines) == 1 else None", "    sentence = lines[0][len(marker):].strip() if lines else None", 'B42 H2: ambiguous gate sentence accepted'),
 # ---- H3 / X15: pre-registration and refusals
 (G, "        return entry.startswith('??') and any(path == item or (item.endswith('/') and path.startswith(item))", "        return any(path == item or (item.endswith('/') and path.startswith(item))", 'B43 H3: an allowlisted path excuses a tracked change'),
 (G, "        return entry.startswith('??') and any(path == item or (item.endswith('/') and path.startswith(item))", "        return entry.startswith('??') or any(path == item or (item.endswith('/') and path.startswith(item))", 'B44 H3: every untracked file allowed'),
 (G, "        return entry.startswith('??') and any(path == item or (item.endswith('/') and path.startswith(item))", "        return entry.startswith('??') and any(path == item or path.startswith(item)", 'B45 H3: allowlist entry matches as a prefix'),
 (G, "            'clean_for_gate': status is not None and head is not None and not gating}", "            'clean_for_gate': not gating}", 'B46 H3: unreadable git state is clean'),
 (G, "    return packaged if packaged.is_dir() else Path(root)", "    return Path(root)", 'B47 X15: shadowing assets directory not seen'),
 (G, "    return {'asset_root': 'src/quati/assets' if base != Path(root) else '<REPO>', 'shadowed': base != Path(root),", "    return {'asset_root': 'src/quati/assets' if base != Path(root) else '<REPO>', 'shadowed': False,", 'B48 X15: shadow never reported'),
 (G, "ASSET_GROUPS = {'contracts': ('contracts', ('*.json',)),\n", "ASSET_GROUPS = {\n", 'B49 H3: contracts not pre-registered'),
 (G, "                'behavior_packages': ('examples/behavior', ('*.yaml', '*.json')),\n", "", 'B50 H3: behavior packages not pre-registered'),
 (G, "                'statecharts': ('examples/statecharts', ('*.yaml',)),\n", "", 'B51 H3: statecharts not pre-registered'),
 (G, "                'policies': ('examples/policies', ('*.json',))}", "                }", 'B52 H3: policy files not pre-registered'),
 (G, "                                'sha256': h.sha256_file(template) if template.is_file() else None},", "                                'sha256': None},", 'B53 H3: policy template digest not recorded'),
 (G, "            'complete': all(item['files'] > 0 for item in groups.values()) and template.is_file()}", "            'complete': True}", 'B54 H3: incomplete assets accepted'),
 (G, "        'code_digest_src_quati': h.code_digest(h.SOURCE / 'quati'), 'assets': assets,", "        'code_digest_src_quati': h.code_digest(h.SOURCE / 'quati'), 'assets': {},", 'B55 H3: assets missing from PREREG'),
 (G, "        'product_doctor': product, 'product_asset_digest': (product or {}).get('asset_digest'),", "        'product_doctor': product, 'product_asset_digest': None,", 'B56 H3: product asset digest not recorded'),
 (G, "    if not git.get('clean_for_gate'):\n        reasons.append(", "    if False:\n        reasons.append(", 'B57 H3: dirty tree not gating'),
 (G, "    if assets['shadowed']:", "    if False:", 'B58 X15: shadowed assets not gating'),
 (G, "    if not assets['complete']:", "    if False:", 'B59 H3: incomplete assets not gating'),
 (G, "    if not isinstance(product.get('behavior'), dict) or product.get('doctor_exit') != 0:", "    if False:", 'B60 H3: missing doctor identity not gating'),
 (G, "                for gate, item in sorted(prereg['gate_sentences'].items()) if not item['found']]", "                for gate, item in sorted(prereg['gate_sentences'].items()) if False]", 'B61 H2: unreadable gate sentence not gating'),
 (G, "    return {'pass': registered is not None and not offenders, 'bound_to': registered,", "    return {'pass': True, 'bound_to': registered,", 'B62 H3: doctor binding always passes'),
 (G, "    return {'pass': registered is not None and not offenders, 'bound_to': registered,", "    return {'pass': not offenders, 'bound_to': registered,", 'B63 H3: nothing registered still a pass'),
 (G, "                 for where, identity in observed if identity != registered]", "                 for where, identity in observed if identity is not None and identity != registered]", 'B64 H3: a doctor Response without the section skipped'),
 (G, "        if 'asset' in name.lower() and isinstance(value, (str, dict)) and value:\n            return {'field': f'behavior.{name}', 'value': value}", "        if False:\n            return {'field': f'behavior.{name}', 'value': value}", 'B65 H3: product asset digest never read'),
 (G, "    return {name: section[name] for name in sorted(section) if name not in DOCTOR_BEHAVIOR_KEYS_IGNORED}", "    return {name: section[name] for name in sorted(section) if name not in DOCTOR_BEHAVIOR_KEYS_IGNORED and 'asset' not in name}", 'B66 H3: asset digest not part of the bound identity'),
 (G, "            'live_calls_allowed': data.get('live_calls_allowed'), 'behavior': doctor_identity(value),", "            'live_calls_allowed': data.get('live_calls_allowed'),", 'B67 H3: SOC-01 baseline doctor not bound'),
 (G, "            'doctor_identities': [{'where': 'probe', 'behavior': doctor_identity(probe['response'])},\n                                  {'where': 'doctor', 'behavior': doctor_identity(plain['response'])}],", "            'doctor_identities': [],", 'B68 H3: DOCTOR leg responses not bound'),
 # ---- H6, H8, H10
 (G, "    elif needs_model and any(item['model_used'] < required_valid for item in per_text.values()):", "    elif needs_model and measured < required_valid:", 'B69 H6: needs_model per leg again'),
 (G, "        'probe_names_the_requested_route': {name: before.get(name) for name in requested} == requested,", "        'probe_names_the_requested_route': True,", 'B70 H8: probe not bound to the requested route'),
 (G, "        'doctor_names_the_requested_route': {name: provider.get(name) for name in requested} == requested,", "        'doctor_names_the_requested_route': True,", 'B71 H8: doctor not bound to the requested route'),
 (G, "        'feature_report_is_of_the_requested_transport': measured_report.get('transport') == transport,", "        'feature_report_is_of_the_requested_transport': True,", 'B72 H8: FeatureReport not bound to the transport'),
 (G, "    requested = {'transport': transport, 'model': model}\n", "    requested = {'transport': transport}\n", 'B73 H8: model not part of the requested route'),
 (G, "PROBE_CALLS, PROBE_MAX_CALLS, ASK_MAX_CALLS = 3, 4, 8", "PROBE_CALLS, PROBE_MAX_CALLS, ASK_MAX_CALLS = 3, 3, 8", 'B74 H10: probe retry not in the ceiling'),
 (G, "USD_PER_CALL_HAIKU = (0.09479228 + 0.08757973) / (151 + 152)", "USD_PER_CALL_HAIKU = 0.095 / (30 * (PROBE_CALLS + TYPICAL_ASK_CALLS['selection']))", 'B75 H10: the old low price per call'),
 (G, "TYPICAL_ASK_CALLS = {'selection': 5, 'none_fits': 5, 'no_candidates': 4, 'answer_blocked': 3}", "TYPICAL_ASK_CALLS = {'selection': 5, 'none_fits': 4, 'no_candidates': 4, 'answer_blocked': 2}", 'B76 H10: the old low request counts'),
 (G, "                'max_calls': profiles * PROBE_MAX_CALLS + asks * ASK_MAX_CALLS}", "                'max_calls': profiles * PROBE_CALLS + asks * typical_ask_calls}", 'B77 H10: ceiling equal to typical'),
 (G, "            'usd_ceiling_at_haiku_rate': round(ceiling * USD_PER_CALL_HAIKU, 2),", "            'usd_ceiling_at_haiku_rate': round(total * USD_PER_CALL_HAIKU, 2),", 'B78 H10: ceiling cost equal to typical cost'),
 # ---- runner
 (RUN, "    refusals = g.protocol_refusals(prereg) if g.gate_protocol(arguments)[0] and not arguments.dry_run_scripted else []", "    refusals = []", 'B79 H3: gate-protocol refusals never applied'),
 (RUN, "        if not table['pass']:", "        if False:", 'B80 H3: social-table mismatch does not stop the run'),
 (RUN, "            verdict = 'PASS_WITH_NOT_RUN_LEGS' if legs else 'PASS'", "            verdict = 'PASS'", 'B81 H4: gate with a NOT_RUN leg printed as PASS'),
 (RUN, "    return EXIT_NOT_RUN_LEGS if any(item['not_run_legs_not_accepted'] for item in gates.values()) else EXIT_PASS", "    return EXIT_PASS", 'B82 H4: unaccepted NOT_RUN leg exits 0'),
 (RUN, "                       'not_run_legs_not_accepted': sorted(leg for leg in legs if leg.split(':', 1)[1] not in accepted),", "                       'not_run_legs_not_accepted': [],", 'B83 H4: every NOT_RUN leg counted as accepted'),
 (RUN, "    return ('GATE_PROTOCOL_PASS_WITH_NOT_RUN_LEGS: ' + ', '.join(legs)) if legs else 'GATE_PROTOCOL_PASS'", "    return 'GATE_PROTOCOL_PASS'", 'B84 H4: run verdict does not carry the NOT_RUN legs'),
 (RUN, "            if case in g.GATE_CASES and brief.get('not_run_legs')}", "            if case in g.GATE_CASES and False}", 'B85 H4: NOT_RUN legs never collected'),
 (RUN, "                       'measurements': {case: {key: summary[case][key] for key in GATE_MEASUREMENTS if key in summary[case]}\n                                        for case in needed if case in summary}}", "                       'measurements': {}}", 'B86 H1/H2: gate summary without the measurements'),
 (RUN, "GATE_MEASUREMENTS = ('read_executed_runs', ", "GATE_MEASUREMENTS = (", 'B87 H1: read_executed_runs not in the gate summary'),
 (RUN, "                     'guard_never_exercised', 'texts_without_guard_observation', 'guard_distribution',", "                     'texts_without_guard_observation', 'guard_distribution',", 'B88 H2: guard_never_exercised not in the gate summary'),
 (RUN, "    heldout = ('RUN, ' + str(arguments.heldout_runs) + ' runs per paraphrase' if arguments.heldout\n               else 'NOT RUN (pass --heldout to run them)')", "    heldout = 'NOT RUN (pass --heldout to run them)'", 'B89 plan ignores --heldout'),
 (RUN, "        \"change a gate verdict or the exit code.\",", "        \"\",", 'B90 plan does not say the held-out sets are informational'),
 (RUN, "    prereg = g.preregistration(arguments, run_id, cases, Path(__file__), vendor, launcher_replaced,\n                               git=g.git_state(allow_untracked=arguments.allow_untracked), product=product)", "    prereg = g.preregistration(arguments, run_id, cases, Path(__file__), vendor, launcher_replaced,\n                               git=g.git_state(allow_untracked=()), product=product)", 'B91 H3: --allow-untracked not passed to the git check'),
 (RUN, "        index['doctor_binding'] = g.doctor_binding(doctors, product.get('behavior'))", "        index['doctor_binding'] = g.doctor_binding([], product.get('behavior'))", 'B92 H3: doctor responses never compared'),
 (G, "        if asset_digest is not None and assets != asset_digest:", "        if False:", 'B118 X15: receipts not bound to the product asset digest'),
 (G, "            counts['asset_missing' if not assets else 'asset_mismatched'] += 1\n            counts['failing'] += in_scope\n", "            counts['asset_missing' if not assets else 'asset_mismatched'] += 1\n", 'B119 X15: asset digest mismatch counted and not failing'),
 (G, "        if asset_digest is not None and assets != asset_digest:", "        if asset_digest is not None and assets and assets != asset_digest:", 'B120 X15: receipt without an asset digest tolerated'),
 (G, "        return {**receipt_binding(base, expected, scope, asset_digest), 'steps': steps}", "        return {**receipt_binding(base, expected, scope), 'steps': steps}", 'B121 X15: binding preflight ignores the asset digest'),
 (RUN, "        index['binding'] = g.receipt_binding(base, expected_digest, arguments.binding_scope, expected_assets)", "        index['binding'] = g.receipt_binding(base, expected_digest, arguments.binding_scope)", 'B122 X15: final binding ignores the asset digest'),
 (G, "    return value if isinstance(value, str) and value else None", "    return None", 'B123 X15: registered asset digest never used'),
 (G, "    return (_data(value).get('result_kind') == 'NO_CAPABILITY' and isinstance(value.get('status'), str)\n            and expected_exit(value) == 4)", "    return (isinstance(value.get('status'), str)\n            and expected_exit(value) == 4)", 'B124 NO_CAPABILITY class: the kind not required'),
 (G, "    return (isinstance(status, str) and expected_exit(value) == 4      # exit 4 excludes SUCCEEDED and PARTIAL\n", "    return (expected_exit(value) == 4\n", 'B125 typed non-success: a Response with no status accepted'),
 (RUN, "        arguments.transport, arguments.model = DRY_RUN_ROUTE\n", "", 'B126 dry run graded for the route named on the command line'),
 # ---- H5: CAP-02 explanation
 (L, "        checks['explain_lists_the_oracle_alternatives'] = bool(alternatives) and all(name in found for name in alternatives)", "        checks['explain_lists_the_oracle_alternatives'] = True", 'B93 H5: zero alternatives accepted'),
 (L, "        checks['explain_lists_the_oracle_alternatives'] = bool(alternatives) and all(name in found for name in alternatives)", "        checks['explain_lists_the_oracle_alternatives'] = bool(alternatives) and any(name in found for name in alternatives)", 'B94 H5: one of the two alternatives is enough'),
 (L, "        checks['explain_oracle_alternatives_have_the_oracle_reasons'] = all(\n            found[name] == tuple(expected) for name, expected in alternatives.items() if name in found)", "        checks['explain_oracle_alternatives_have_the_oracle_reasons'] = True", 'B95 H5: alternative reasons not compared'),
 (L, "            found[name] == tuple(expected) for name, expected in alternatives.items() if name in found)", "            found[name][1] == tuple(expected)[1] for name, expected in alternatives.items() if name in found)", 'B96 H5: authorization of an alternative not compared'),
 (L, "                      PREFIX + 'mail-search': ('ALLOW', 'outcome_mismatch')}", "                      }", 'B97 H5: mail-search not required'),
 (L, "CAP02_ALTERNATIVES = {PREFIX + 'calendar-write': ('DENY', 'scope_not_granted'),", "CAP02_ALTERNATIVES = {PREFIX + 'calendar-write': ('DENY', 'policy_denied'),", 'B98 H5: another reason for calendar-write'),
 (L, "            observed = trace_explain(profile, (value.get('data') or {}).get('request_id'), PREFIX + expected,\n                                     CAP02_ALTERNATIVES)", "            observed = trace_explain(profile, (value.get('data') or {}).get('request_id'), PREFIX + expected,\n                                     None)", 'B99 H5: the CAP-02 run does not pass the oracle alternatives'),
 (L, "              'explain_catalog_was_recorded': UNRANKED_UNCERTAINTY not in (value.get('uncertainties') or []),", "              'explain_catalog_was_recorded': True,", 'B100 H5: missing catalog accepted'),
 (L, "            observed['checks']['ask_recorded_synthetic_evidence'] = bool(\n                ((receipt or {}).get('synthetic_evidence') or {}).get('catalog'))", "            observed['checks']['ask_recorded_synthetic_evidence'] = True", 'B101 H5: ask without recorded catalog accepted'),
 (L, "            observed['pass'] = all(observed['checks'].values())\n", "", 'B102 H5: the added check does not change the observation verdict'),
 (L, "        'explain_target_carries_rank_features': isinstance(features, dict) and isinstance(features.get('rank'), int)\n        and not isinstance(features.get('rank'), bool),", "        'explain_target_carries_rank_features': True,", 'B103 H5: rank features not required'),
 (L, "        'explain_model_identity_recorded': isinstance(models, list) and bool(models)\n        and all(isinstance(name, str) and name for name in models),", "        'explain_model_identity_recorded': True,", 'B104 H5: model identity not required'),
 (L, "        code, value, elapsed = profile.cli('ask', text, '--json', '--synthetic-evidence',\n                                           '--eval-candidate-permutation-seed', str(permutation_seed))", "        code, value, elapsed = profile.cli('ask', text, '--json',\n                                           '--eval-candidate-permutation-seed', str(permutation_seed))", 'B105 H5: CAP runs ask without --synthetic-evidence'),
 # ---- H7: CAP-03
 (L, "        'model_was_asked': data.get('provider_used') is True and bool(trajectory),", "        'model_was_asked': True,", 'B106 H7: model not required'),
 (L, "        'disabled_not_executed': disabled not in executed,", "        'disabled_not_executed': True,", 'B107 H7: disabled capability executed accepted'),
 (L, "        'no_other_capability_executed': not [name for name in executed if name != disabled],", "        'no_other_capability_executed': True,", 'B108 H7: another capability executed accepted'),
 (L, "        'guard_observed_on_the_disabled_capability': excluded or refused,", "        'guard_observed_on_the_disabled_capability': True,", 'B109 H7: guard not required'),
 (L, "        'not_succeeded': status != 'SUCCEEDED',", "        'not_succeeded': True,", 'B110 H7: false success accepted'),
 (L, "        'typed_non_success_of_the_product': outcome != 'OTHER' or status == 'SUCCEEDED',", "        'typed_non_success_of_the_product': True,", 'B111 H7: any non-success accepted'),
 (L, "        'exit_4': code == 4 or status == 'SUCCEEDED',", "        'exit_4': True,", 'B112 H7: exit code not asserted'),
 (L, "    excluded = any(item.get('capability_id') == disabled and DISABLED_REASON in (item.get('reasons') or [])", "    excluded = any(DISABLED_REASON in (item.get('reasons') or [])", 'B113 H7: exclusion of another capability counts as the guard'),
 (L, "    excluded = any(item.get('capability_id') == disabled and DISABLED_REASON in (item.get('reasons') or [])", "    excluded = any(item.get('capability_id') == disabled", 'B114 H7: exclusion for another reason counts as the guard'),
 (L, "    outcome = ('INVOKE_REFUSED' if non_success and kind == 'BLOCKED' and reason == OUTSIDE_SHORTLIST and error.get('code')", "    outcome = ('INVOKE_REFUSED' if non_success and kind == 'BLOCKED'", 'B115 H7: any BLOCKED kind is the refused invoke'),
 (L, "    non_success = isinstance(status, str) and status not in ('SUCCEEDED', 'PARTIAL')", "    non_success = isinstance(status, str) and status not in ('SUCCEEDED',)", 'B116 H7: PARTIAL accepted as the typed non-success'),
 (L, "    checks = {'disable_succeeded': steps[-1][1] == 0, 'run_valid': validity == VALID, **graded['checks']}", "    checks = {'disable_succeeded': True, 'run_valid': validity == VALID, **graded['checks']}", 'B117 H7: failed disable accepted'),
]


def prepare(index: int) -> Path:
    copy = SCRATCH / f'copy{index}'
    shutil.rmtree(copy, ignore_errors=True)
    for name in COPIED:
        source, target = REPO / name, copy / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(source, target)
    git = ['git', '-c', 'user.name=mutation', '-c', 'user.email=mutation@example.invalid', '-c', 'commit.gpgsign=false']
    for arguments in (['init', '-q'], ['add', '-A'], ['commit', '-q', '-m', 'snapshot']):
        subprocess.run([*git, *arguments], cwd=copy, check=True, capture_output=True)
    return copy


def run(copy: Path):
    environment = {key: value for key, value in os.environ.items() if not key.startswith('QUATI_')}
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(copy / 'src'))
    done = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-x', '--rootdir', str(copy),
                           'tests/unit/test_eval_harness_grader.py', 'tests/unit/test_eval_harness_soc01.py'],
                          capture_output=True, text=True, env=environment, cwd=copy)
    lines = done.stdout.strip().splitlines()
    failed = next((line for line in lines if line.startswith(('FAILED', 'ERROR'))), '')
    return done.returncode, (lines[-1] if lines else ''), failed.replace(str(copy), '<COPY>')


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    copies = [prepare(index) for index in range(WORKERS)]
    print('baseline (no mutant):', run(copies[0])[:2], flush=True)
    mutants = [('A', *item) for item in AUDIT] + [('B', *item) for item in OWN]
    if ONLY is not None:
        mutants = [item for item in mutants if item[4].split()[0] in ONLY]
    free = list(copies)

    def one(mutant):
        part, name, old, new, why = mutant
        copy = free.pop()
        try:
            path = copy / 'tests' / 'evals' / name
            source = path.read_text(encoding='utf-8')
            if source.count(old) != 1:
                return part, why, name, 'NOT_APPLIED', f'search text found {source.count(old)} times', ''
            path.write_text(source.replace(old, new), encoding='utf-8')
            try:
                code, tail, failed = run(copy)
            finally:
                path.write_text(source, encoding='utf-8')
            return part, why, name, 'KILLED' if code else 'SURVIVED', tail[-40:], failed[:230]
        finally:
            free.append(copy)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(one, mutants))
    for part, why, name, verdict, tail, failed in results:
        print(f'{verdict:11} | {why} | {name} | {tail} | {failed}')
    for part, title in (('A', 'audit mutants (forkH/h3_mutate.py)'), ('B', 'mutants of the rules of this round')):
        mine = [item for item in results if item[0] == part]
        print(f"SUMMARY {title}: {sum(1 for item in mine if item[3] == 'KILLED')} of {len(mine)} killed; "
              f"survived {sum(1 for item in mine if item[3] == 'SURVIVED')}; "
              f"not applied {sum(1 for item in mine if item[3] == 'NOT_APPLIED')}")


if __name__ == '__main__':
    main()
