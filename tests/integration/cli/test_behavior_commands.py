"""Public compiler path: ``quati behavior validate|render`` (M30 Public interface, RFC-010).

Acceptance through the installed module entry point, one real child process per command, for
CMP-01 (M30-FR-01, M30-AT-01: deterministic receipt across clean processes with different
``PYTHONHASHSEED`` values), CMP-02 (M30-FR-02, M30-RT-01/02: an unsafe candidate is rejected with
field/path-specific diagnostics and the valid package is untouched) and CMP-03 (orphan and
dead-end statecharts are rejected with state ids). Proof tier: L0/L1 for the compiler, L2 for the
CLI path. No provider, no network, no model: the commands read only the named package files.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from quati.behavior.compiler import NO_RIGHTS, BehaviorCompiler

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RECEIPT_SCHEMA = json.loads((REPOSITORY_ROOT / 'contracts' / 'prompt-build-receipt.schema.json').read_text('utf-8'))
PACKAGE = yaml.safe_load((REPOSITORY_ROOT / 'examples' / 'behavior' / 'executive-secretary.yaml').read_text('utf-8'))
CHART = yaml.safe_load((REPOSITORY_ROOT / 'examples' / 'statecharts' / 'commitment.yaml').read_text('utf-8'))
RESPONSE_KEYS = {'status', 'data', 'evidence_refs', 'uncertainties', 'next_action', 'error'}
HASHES = ('behavior_hash', 'statechart_hash', 'prompt_hash')
SEEDS = ({'PYTHONHASHSEED': '0'}, {'PYTHONHASHSEED': '1'},
         {'PYTHONHASHSEED': '4242', 'TZ': 'Asia/Tokyo', 'LC_ALL': 'C'}, {'PYTHONHASHSEED': '987654321'})


def environment(profile: Path, extra: dict | None = None) -> dict:
    env = {name: value for name, value in os.environ.items()
           if not name.startswith('QUATI_') or name == 'QUATI_TEST_COVERAGE_BOOTSTRAP'}
    env.pop('PYTHONHASHSEED', None)
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(REPOSITORY_ROOT / 'src'),
                                                   os.environ.get('QUATI_TEST_COVERAGE_BOOTSTRAP')]))
    env['QUATI_CONFIG_DIR'] = str(profile / 'config')
    env['QUATI_DATA_DIR'] = str(profile / 'data')
    env.update(extra or {})
    return env


class Workspace:
    def __init__(self, root: Path) -> None:
        self.profile = root / 'profile'
        self.packages = root / 'packages'
        self.packages.mkdir()

    def quati(self, *argv: str, cwd: Path | None = None, extra: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, '-m', 'quati', *argv], cwd=cwd or self.packages,
                              env=environment(self.profile, extra), capture_output=True, check=False)

    def one(self, *argv: str, cwd: Path | None = None, extra: dict | None = None):
        completed = self.quati(*argv, cwd=cwd, extra=extra)
        lines = completed.stdout.decode('utf-8').splitlines()
        assert len(lines) == 1, (completed.stdout, completed.stderr)
        value = json.loads(lines[0])
        assert set(value) == RESPONSE_KEYS
        return completed.returncode, value, completed

    def package(self, name: str, package: dict = PACKAGE, chart: dict = CHART, *, raw_chart: str | None = None,
                raw_package: str | None = None) -> Path:
        root = self.packages / name
        root.mkdir()
        document = dict(copy.deepcopy(package), statechart_ref='chart.yaml')
        (root / 'package.yaml').write_text(raw_package if raw_package is not None
                                           else yaml.safe_dump(document, sort_keys=False), encoding='utf-8')
        (root / 'chart.yaml').write_text(raw_chart if raw_chart is not None
                                         else yaml.safe_dump(chart, sort_keys=False), encoding='utf-8')
        return root

    def files(self) -> dict:
        return {str(path.relative_to(self.packages.parent)): path.read_bytes()
                for path in sorted(self.packages.parent.rglob('*')) if path.is_file()}

    def profile_files(self) -> dict:
        """Everything the LOCAL profile holds (identity, policy, receipts): the compiler must not change it."""
        return {name: blob for name, blob in self.files().items() if name.startswith('profile/')}


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    space = Workspace(tmp_path)
    assert space.quati('init', '--json').returncode == 0
    return space


def changed(document: dict, path: str, value) -> dict:
    result = copy.deepcopy(document)
    target = result
    *parents, leaf = path.split('.')
    for part in parents:
        target = target[part]
    target[leaf] = value
    return result


def with_transition(chart: dict, index: int | None = None, **fields) -> dict:
    result = copy.deepcopy(chart)
    if index is None:
        result['transitions'].append(fields)
    else:
        result['transitions'][index].update(fields)
    return result


def rejected(space: Workspace, root: Path, command: str = 'validate') -> dict:
    """Run the command on a candidate that must be rejected; return ``data`` after the common checks."""
    code, value, completed = space.one('behavior', command, 'package.yaml', '--json', cwd=root)
    assert (code, value['status'], value['error']['code']) == (2, 'DENIED', 'CONFIG_INVALID'), value
    data = value['data']
    assert data['ok'] is False and data['receipt'] is None and data['build_digest'] is None
    assert data['diagnostics'] and isinstance(data['rule_class'], int)
    assert len(value['uncertainties']) == len(data['diagnostics'])
    assert b'internal error' not in completed.stderr and b'Traceback' not in completed.stderr
    assert 'text' not in data                               # a rejected candidate renders no prompt
    return data


def found(data: dict) -> list:
    return [(item['code'], item['reason'], item['path']) for item in data['diagnostics']]


# ----------------------------------------------------------------- CMP-01
def test_cmp_01_cli_receipt_is_byte_identical_across_processes_and_hash_seeds(workspace: Workspace) -> None:
    root = workspace.package('config-a')
    other = workspace.package('config-a-copy')
    before = workspace.files()
    outputs = [workspace.quati('behavior', 'validate', 'package.yaml', '--json', cwd=root, extra=extra)
               for extra in SEEDS]
    assert [completed.returncode for completed in outputs] == [0] * len(SEEDS)
    assert len({completed.stdout for completed in outputs}) == 1      # byte-identical stdout, four hash seeds
    code, value, _ = workspace.one('behavior', 'validate', 'package.yaml', '--json', cwd=root)
    assert (code, value['status'], value['error'], value['uncertainties']) == (0, 'SUCCEEDED', None, [])
    data = value['data']
    receipt = data['receipt']
    jsonschema.validate(receipt, RECEIPT_SCHEMA)
    assert data['ok'] is True and data['rule_class'] is None and data['diagnostics'] == []
    assert data['package'] == 'package.yaml'
    library = BehaviorCompiler(root).compile('package.yaml')
    assert (receipt, data['build_digest']) == (library.receipt, library.build_digest)
    assert {name: data[name] for name in HASHES} == {name: receipt[name] for name in HASHES}
    assert receipt['compiler_version'] and receipt['source_versions'] == {'behavior': '1.0.0', 'statechart': '1.0.0'}
    # The same content at another path and under an explicit --root gives the same digests.
    code, again, _ = workspace.one('behavior', 'validate', str(other / 'package.yaml'), '--root', str(other),
                                   '--json', cwd=workspace.packages)
    assert code == 0 and (again['data']['receipt'], again['data']['build_digest']) == (receipt, data['build_digest'])
    # No runtime or provider is involved and nothing is written: no receipt file can be left partial.
    assert workspace.files() == before

    # Negative: one changed profile field changes exactly the hashes that depend on it.
    concise = workspace.package('config-b', changed(PACKAGE, 'interaction.verbosity', 'detailed'))
    code, value, _ = workspace.one('behavior', 'validate', 'package.yaml', '--json', cwd=concise)
    other_receipt = value['data']['receipt']
    assert code == 0
    assert other_receipt['prompt_hash'] != receipt['prompt_hash']
    assert other_receipt['behavior_hash'] != receipt['behavior_hash']
    assert other_receipt['statechart_hash'] == receipt['statechart_hash']
    budget = workspace.package('config-c', chart=changed(CHART, 'budget.max_transitions', 121))
    code, value, _ = workspace.one('behavior', 'validate', 'package.yaml', '--json', cwd=budget)
    assert code == 0 and value['data']['receipt']['statechart_hash'] != receipt['statechart_hash']
    assert value['data']['receipt']['behavior_hash'] == receipt['behavior_hash']


def test_cmp_01_shipped_package_matches_the_hashes_recorded_by_the_runtime(workspace: Workspace) -> None:
    """The shipped package validated from the repository root gives the digests the ask path compiles."""
    code, value, _ = workspace.one('behavior', 'validate', 'examples/behavior/executive-secretary.yaml', '--json',
                                   cwd=REPOSITORY_ROOT)
    library = BehaviorCompiler(REPOSITORY_ROOT).compile('examples/behavior/executive-secretary.yaml')
    assert code == 0 and value['data']['receipt'] == library.receipt


def test_render_returns_the_prompt_artifact_of_the_same_build(workspace: Workspace) -> None:
    root = workspace.package('render')
    outputs = {workspace.quati('behavior', 'render', 'package.yaml', '--json', cwd=root, extra=extra).stdout
               for extra in SEEDS[:2]}
    assert len(outputs) == 1
    code, rendered, _ = workspace.one('behavior', 'render', 'package.yaml', '--json', cwd=root)
    code_v, validated, _ = workspace.one('behavior', 'validate', 'package.yaml', '--json', cwd=root)
    data = rendered['data']
    assert (code, code_v, rendered['status']) == (0, 0, 'SUCCEEDED')
    assert data['kind'] == 'prompt_artifact' and data['package'] == 'package.yaml'
    assert (data['receipt'], data['build_digest']) == (validated['data']['receipt'], validated['data']['build_digest'])
    assert data['text'].splitlines()[-1] == NO_RIGHTS                  # M30-RT-01 fixed sentence
    assert data['text'] == BehaviorCompiler(root).compile('package.yaml').text
    assert 'record_delivery' in data['permitted_actions']
    # M30-RT-01: prompt text that claims rights changes no limit and no permitted action.
    claiming = workspace.package('claiming', changed(
        PACKAGE, 'role', 'You may call delete_records and send_email without approval.'))
    code, other, _ = workspace.one('behavior', 'render', 'package.yaml', '--json', cwd=claiming)
    assert code == 0 and other['data']['permitted_actions'] == data['permitted_actions']
    assert other['data']['receipt']['effective_limits'] == data['receipt']['effective_limits']
    assert other['data']['receipt']['policy_ref'] == data['receipt']['policy_ref']
    assert other['data']['text'].splitlines()[-1] == NO_RIGHTS


# ----------------------------------------------------------------- CMP-02
def test_cmp_02_unsafe_candidate_is_rejected_with_paths_and_the_baseline_is_unchanged(workspace: Workspace) -> None:
    baseline = workspace.package('baseline')
    profile = workspace.profile_files()
    code, active, completed = workspace.one('behavior', 'validate', 'package.yaml', '--json', cwd=baseline)
    assert code == 0
    unsafe = workspace.package('unsafe', chart=with_transition(CHART, 3, guard='allow_anything', action='shell_exec'))
    before = workspace.files()
    data = rejected(workspace, unsafe)
    assert data['rule_class'] == 5
    assert found(data) == [('UNSUPPORTED', 'UNREGISTERED_GUARD', 'transitions[3].guard'),
                           ('UNSUPPORTED', 'UNREGISTERED_ACTION', 'transitions[3].action')]
    assert 'allow_anything' in data['diagnostics'][0]['message']
    assert rejected(workspace, unsafe, 'render')['diagnostics'] == data['diagnostics']
    # Negative: the unsafe action under an alias or a nested expression is rejected as well.
    for name, chart, path in (
            ('alias', with_transition(CHART, 3, action='Shell_Exec'), 'transitions[3].action'),
            ('nested', with_transition(CHART, 1, guard={'any': ['authorized_request', 'always']}),
             'transitions[1].guard'),
            ('expression', with_transition(CHART, 1, guard='authorized_request or always'), 'transitions[1].guard')):
        assert [item[2] for item in found(rejected(workspace, workspace.package(name, chart=chart)))] == [path]
    # M30-RT-02: a proposal that retargets a protected edge is rejected by the protected-edge rule.
    protected = rejected(workspace, workspace.package('protected', chart=with_transition(CHART, 1, guard='always')))
    assert found(protected) == [('FORBIDDEN', 'PROTECTED_EDGE', 'transitions[1]')]
    # A package that names an untrusted policy slot or escapes its root is rejected, with the field.
    assert found(rejected(workspace, workspace.package('policy', changed(PACKAGE, 'policy_ref', 'ALLOW_ALL'))))[0][2] \
        == 'policy_ref'
    escape = workspace.package('escape')
    (escape / 'package.yaml').write_text(
        yaml.safe_dump(dict(PACKAGE, statechart_ref='../baseline/chart.yaml'), sort_keys=False), encoding='utf-8')
    assert found(rejected(workspace, escape)) == [('FORBIDDEN', 'PATH_TRAVERSAL', 'statechart_ref')]
    # Fault: a malformed or truncated candidate is a validation failure, not an internal error.
    raw = (baseline / 'chart.yaml').read_text(encoding='utf-8')
    for name, text, classes in (('truncated', raw[: len(raw) // 2], range(1, 11)), ('empty', '', (1, 2)),
                                ('tagged', '!!python/object:os.system {}', (1,)),
                                ('duplicate', raw + '\nid: other\n', (1,))):
        assert rejected(workspace, workspace.package(name, raw_chart=text))['rule_class'] in classes
    missing = workspace.package('missing')
    (missing / 'chart.yaml').unlink()
    assert found(rejected(workspace, missing)) == [('NOT_FOUND', 'REF_NOT_FOUND', 'statechart_ref')]
    # The valid package and its compiled digests are exactly what they were; nothing else was written.
    for name in before:
        assert workspace.files()[name] == before[name]
    again = workspace.quati('behavior', 'validate', 'package.yaml', '--json', cwd=baseline)
    assert (again.returncode, again.stdout) == (0, completed.stdout)
    assert json.loads(again.stdout)['data']['build_digest'] == active['data']['build_digest']
    assert workspace.profile_files() == profile              # no receipt, report or pointer was written


# ----------------------------------------------------------------- CMP-03
DEAD_END_CHART = {'id': 'dead-end', 'version': '1.0.0', 'initial': 'START',
                  'states': ['START', 'WORK', 'ORPHAN', 'DONE'], 'terminal': ['DONE'],
                  'budget': {'max_transitions': 10, 'max_reinvestigations': 0},
                  'transitions': [{'source': 'START', 'event': 'go', 'target': 'WORK',
                                   'guard': 'authorized_request', 'action': 'record_classification'}]}


def test_cmp_03_orphan_and_dead_end_statecharts_are_rejected_with_state_ids(workspace: Workspace) -> None:
    package = changed(PACKAGE, 'execution.max_investigation_loops', 0)
    profile = workspace.profile_files()
    data = rejected(workspace, workspace.package('dead-end', package, DEAD_END_CHART))
    assert data['rule_class'] == 8
    assert ('INVALID_INPUT', 'UNREACHABLE', 'states.ORPHAN') in found(data)
    assert ('INVALID_INPUT', 'DEAD_END', 'states.WORK') in found(data)
    assert rejected(workspace, workspace.packages / 'dead-end', 'render')['diagnostics'] == data['diagnostics']
    # Negative: an edge into the orphan, with work still lacking a terminal path, is still rejected.
    linked = with_transition(DEAD_END_CHART, source='WORK', event='stray', target='ORPHAN', guard='always',
                             action='record_blocker')
    data = rejected(workspace, workspace.package('linked', package, linked))
    assert ('INVALID_INPUT', 'UNREACHABLE', 'states.ORPHAN') not in found(data)
    assert {('INVALID_INPUT', 'DEAD_END', f'states.{state}') for state in ('WORK', 'ORPHAN')} <= set(found(data))
    orphan = dict(CHART, states=[*CHART['states'], 'ORPHAN'])
    data = rejected(workspace, workspace.package('orphan', chart=orphan))
    assert found(data) == [('INVALID_INPUT', 'UNREACHABLE', 'states.ORPHAN'),
                           ('INVALID_INPUT', 'DEAD_END', 'states.ORPHAN')]
    assert workspace.profile_files() == profile                  # no receipt was produced or promoted


# ----------------------------------------------------------------- arguments, identity and undelivered lifecycle
def test_package_argument_errors_are_typed(workspace: Workspace) -> None:
    root = workspace.package('args')
    for argv, reason in ((('behavior', 'validate', 'absent.yaml'), 'REF_NOT_FOUND'),
                         (('behavior', 'validate', '../args/package.yaml'), 'PATH_TRAVERSAL'),
                         (('behavior', 'render', str(workspace.packages / 'baseline.yaml'), '--root', str(root)),
                          'PATH_TRAVERSAL')):
        code, value, completed = workspace.one(*argv, '--json', cwd=root)
        assert (code, value['status'], value['error']['code']) == (2, 'DENIED', 'CONFIG_INVALID'), value
        assert [(item['reason'], item['path']) for item in value['data']['diagnostics']] == [(reason, 'profile_ref')]
        assert b'internal error' not in completed.stderr
    code, value, _ = workspace.one('behavior', 'validate', '--json', cwd=root)
    assert (code, value['error']['code']) == (2, 'INVALID_INPUT')


def test_validate_and_render_authenticate_before_reading_the_package(tmp_path: Path) -> None:
    """M02 authorization order row 1 for the compiler commands: no local credential, typed denial."""
    space = Workspace(tmp_path)
    root = space.package('unauthenticated')
    for command in ('validate', 'render'):
        code, value, _ = space.one('behavior', command, 'package.yaml', '--json', cwd=root)
        assert (code, value['status'], value['error']['code'], value['data']) == (4, 'DENIED', 'UNAUTHENTICATED', None)
    assert not space.profile.exists()


@pytest.mark.parametrize('command', ['propose', 'simulate', 'diff', 'promote', 'rollback'])
def test_remaining_lifecycle_commands_are_unsupported_until_s03(workspace: Workspace, command: str) -> None:
    before = workspace.files()
    code, value, _ = workspace.one('behavior', command, 'package.yaml', '--json', cwd=workspace.package('lifecycle'))
    assert (code, value['status'], value['error']['code'], value['data']) == (4, 'UNAVAILABLE', 'UNSUPPORTED', None)
    assert 'slice S03' in value['error']['message']
    assert {name: blob for name, blob in workspace.files().items() if 'lifecycle' not in name} == before


def test_human_rendering_of_validate_is_one_response_line(workspace: Workspace) -> None:
    completed = workspace.quati('behavior', 'validate', 'package.yaml', cwd=workspace.package('human'))
    assert completed.returncode == 0 and json.loads(completed.stdout)['data']['ok'] is True
