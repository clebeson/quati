"""S00 integration step after fix round 7 (LOG-0042 "open for the integration step"): in-process proof.

Boundaries covered, each with its requirement or decision:

* A  - every receipt the evidence sink writes carries ``digests.code_digest`` (audit P2-E; LOG-0041 N4
  "code-digest binding"): the sink is the one place a receipt passes, the digest function is the one source.
* B2 - ``LocalIdentity`` itself rejects a signed installation record whose tenant, principal or space id
  is not a non-empty string (LOG-0041 N10; RFC-013 section 4), so no caller needs a subclass.
* B3 - the registry enforcement point is a public composition function (RFC-013 section 6).
* B4 - a local-store refusal exits 4 inside the use cases (M01 "Exit codes (stable)" row 4), through the
  one mapping the presentation boundary uses.
* D  - packaged assets: the asset root is the packaged copy when present, else the source checkout; a
  missing contract schema is a typed diagnostic (M01 exit table rows 1 and 2), never an unhandled error.

Proof tier: L1 (deterministic, in process, SCRIPTED FAKE model: fake-provider compatibility only). The
public child-process legs are in tests/integration/cli/test_s00_integration7_public.py.
"""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from test_s00_fix6_cli_surface import WORK_TEXT, Cli, _audit_fault, cli, read_script  # noqa: F401 - fixture

from quati.adapters import evidence, runtime_facts
from quati.adapters.local_identity import LocalIdentity
from quati.application import capability_commands
from quati.application.code_identity import current_code_digest
from quati.application.identity import AccessDenied
from quati.behavior import contracts
from quati.behavior.compiler import BehaviorCompiler
from quati.cli import composition, rendering
from quati.cli import main as cli_main
from quati.domain import diagnostics
from quati.domain.diagnostics import ContractViolation

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_FIELDS = ('tenant_id', 'principal_id', 'personal_space_id', 'organization_space_id')
# Integration step 8: `feature_report_not_stored` joined the list (it always exited 4 through a literal in the
# probe use case; M01 exit table row 4 now names the four reasons and one rule settles them).
LOCAL_REASONS = ('audit_unavailable', 'audit_store_unavailable', 'state_dir_unsafe', 'feature_report_not_stored')
ASSETS = contracts.asset_digest()      # LOG-0044 X15: set on every receipt next to the code digest (M01 rule 5)


def _independent_code_digest() -> str:
    """The documented algorithm, recomputed here: sha256 over the sorted (relative path, file sha256) list."""
    root = REPOSITORY_ROOT / 'src' / 'quati'
    entries = sorted((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
                     for path in root.rglob('*.py') if path.is_file())
    return hashlib.sha256(json.dumps(entries, separators=(',', ':')).encode('utf-8')).hexdigest()


def _resign(config: Path, **changes) -> None:
    """Rewrite the installation record with ``changes`` (``...`` removes a field), signed by the device key."""
    record = json.loads((config / 'identity.json').read_bytes())
    record.pop('signature')
    for name, value in changes.items():
        if value is ...:
            record.pop(name, None)
        else:
            record[name] = value
    key = Ed25519PrivateKey.from_private_bytes((config / 'device.key').read_bytes())

    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    record['signature'] = base64.b64encode(key.sign(canonical(record))).decode('ascii')
    (config / 'identity.json').write_bytes(canonical(record))


# ----------------------------------------------------------------- A: the code digest on every receipt
def test_a_the_evidence_sink_stamps_the_code_digest_on_every_record(tmp_path, monkeypatch) -> None:
    """Audit P2-E: a receipt of any kind names the code that wrote it; the caller cannot choose the value."""
    monkeypatch.setenv('QUATI_DATA_DIR', str(tmp_path / 'data'))
    assert current_code_digest() == _independent_code_digest()
    for kind in ('audit_event', 'capability_command', 'feature_report'):
        written = evidence.receipt_sink({'kind': kind, 'status': 'SUCCEEDED'})
        raw = Path(written['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == written['sha256']
        assert json.loads(raw)['digests'] == {'code_digest': current_code_digest(), 'asset_digest': ASSETS}, kind
    forged = evidence.receipt_sink({'kind': 'ask_receipt', 'digests': {'config_hash': 'a' * 64, 'code_digest': '0' * 64}})
    assert json.loads(Path(forged['path']).read_bytes())['digests'] == {
        'config_hash': 'a' * 64, 'code_digest': current_code_digest(), 'asset_digest': ASSETS}
    malformed = evidence.receipt_sink({'kind': 'ask_receipt', 'digests': 'not-an-object'})
    assert json.loads(Path(malformed['path']).read_bytes())['digests'] == {
        'code_digest': current_code_digest(), 'asset_digest': ASSETS}


def test_a_every_receipt_of_an_in_process_session_carries_the_same_code_digest(cli: Cli) -> None:
    """init, install, probe, greeting, up-front refusal, model-path ask and disable: one digest on all."""
    cli.ready(*read_script())
    assert cli.one('ask', 'Hello', '--json')[0] == 0
    code, value, _ = cli.one('ask', WORK_TEXT, '--json')
    assert (code, value['data']['result_kind']) == (0, 'FIXTURE_RESULT'), value
    assert cli.one('capabilities', 'disable', 'fixtures.calendar-read@1.0.0', '--json')[0] == 0
    cli.monkeypatch.setattr(cli_main, '_config', cli_main.ProviderConfig.from_environment)
    code, value, _ = cli.one('ask', WORK_TEXT, '--json')       # no provider: refused before any model call
    assert (code, value['data']['result_kind']) == (3, 'BLOCKED'), value
    receipts = [json.loads(path.read_bytes()) for path in sorted((cli.data / 'receipts').glob('*.json'))]
    kinds = sorted(str(receipt.get('kind')) for receipt in receipts)
    assert kinds == ['None', 'None', 'ask_receipt', 'audit_event', 'capability_command', 'capability_command',
                     'feature_report']
    assert {receipt['digests']['code_digest'] for receipt in receipts} == {_independent_code_digest()}


# ----------------------------------------------------------------- B2: the identity adapter validates its record
@pytest.mark.parametrize('field', IDENTITY_FIELDS)
@pytest.mark.parametrize('value', ['', ..., 7, None, ['x'], {'id': 'x'}], ids=['empty', 'absent', 'int', 'null', 'list',
                                                                           'object'])
def test_b2_a_signed_record_with_an_unusable_identifier_is_a_rejected_credential(tmp_path, field, value) -> None:
    """LOG-0041 N10 at the adapter: typed AccessDenied from every entry, never a KeyError mid-command."""
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    context = identity.authenticate()
    _resign(identity.directory, **{field: value})
    for call in (identity.authenticate, identity.issue_token, identity.initialize,
                 lambda: identity.tenant_role(context), lambda: identity.space_grants(context),
                 lambda: identity.registry_space(context.tenant_id)):
        with pytest.raises(AccessDenied):
            call()
    assert identity.diagnostics()['initialized'] is False
    # doctor's cause for the same record (M02 reason table): present, corrupt, the field detail; no path.
    assert runtime_facts.identity_state(identity.directory) == {
        'present': True, 'cause': 'credential_corrupt', 'detail': 'record_field_missing'}


def test_b2_a_complete_signed_record_is_still_accepted_and_the_cli_uses_the_adapter_directly(tmp_path, monkeypatch) -> None:
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    _resign(identity.directory, tenant_role='MEMBER')              # an optional field does not reject the record
    context = identity.authenticate()
    assert identity.tenant_role(context) == 'MEMBER' and identity.diagnostics()['initialized'] is True
    monkeypatch.setenv('QUATI_CONFIG_DIR', str(tmp_path / 'config'))
    assert type(cli_main._service().identity) is LocalIdentity
    assert not hasattr(cli_main, '_Identity')


# ----------------------------------------------------------------- B3: public registry enforcement point
def test_b3_registry_authorizer_decides_and_logs_through_the_public_composition_function(cli: Cli) -> None:
    """RFC-013 section 6: one enforcement point; injected clock and ids; allowed and denied are both logged."""
    assert cli.one('init', '--json')[0] == 0
    identity = LocalIdentity()
    context = identity.authenticate()
    moment = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
    authorize = composition.registry_authorizer(identity, clock=lambda: moment, ids=lambda prefix: f'{prefix}-fixed')
    assert authorize(context, 'models_probe', 'manage') is None
    _resign(cli.config, tenant_role='GUEST')
    denied = authorize(context, 'models_probe', 'manage')
    assert (denied.status, denied.code) == ('DENIED', 'FORBIDDEN')
    events = [json.loads(line) for line in (cli.data / 'capabilities' / 'audit.jsonl').read_text().splitlines()]
    decided = [event for event in events if event['event'] == 'authz.decided']
    assert [(event['operation'], event['decision']['action'], event['decision']['verdict']) for event in decided] == [
        ('models_probe', 'manage', 'ALLOW'), ('models_probe', 'manage', 'DENY')]
    assert all(event['at'].startswith('2026-11-16T12:00:00') and event['request_id'] == context.request_id
               for event in decided)
    assert 'registry_authorizer' in composition.__all__
    assert 'composition._parts' not in inspect.getsource(cli_main)


# ----------------------------------------------------------------- B4: exit 4 inside the use cases
def _unavailable(reason: str | None) -> dict:
    return {'status': 'UNAVAILABLE', 'error': {'code': 'TEMPORARILY_UNAVAILABLE'},
            'data': None if reason is None else {'reason': reason}}


@pytest.mark.parametrize('reason', LOCAL_REASONS)
def test_b4_a_local_store_refusal_is_exit_4_in_the_shared_mapping_and_in_the_capability_use_case(reason) -> None:
    """M01 exit table row 4: UNAVAILABLE caused by the audit log or the data directory is not a provider failure."""
    value = _unavailable(reason)
    assert diagnostics.local_store_failure(value) is True
    assert diagnostics.settled_exit(5, value) == 4 and diagnostics.settled_exit(1, value) == 1
    assert capability_commands._exit(value) == 4
    assert rendering.exit_code(value) == 4


def test_b4_a_provider_failure_stays_exit_5_and_the_boundary_has_one_mapping() -> None:
    for value in (_unavailable('BINDING_UNAVAILABLE'), _unavailable(None)):
        assert diagnostics.local_store_failure(value) is False
        assert diagnostics.settled_exit(5, value) == 5 and capability_commands._exit(value) == 5
        assert rendering.exit_code(value) == 5
    assert tuple(diagnostics.LOCAL_STORE_REASONS) == LOCAL_REASONS
    assert rendering.settled_exit is diagnostics.settled_exit
    assert rendering.LOCAL_STORE_REASONS is diagnostics.LOCAL_STORE_REASONS


def test_b4_the_ask_use_case_itself_returns_exit_4_for_an_unusable_audit_log(cli: Cli) -> None:
    """The use case and the presentation boundary agree: no code is corrected after the fact."""
    cli.ready(*read_script())
    _audit_fault(cli, 'symlink')
    code, value = cli_main._service().ask(WORK_TEXT)
    assert (code, value['status'], value['error']['code'], value['data']['reason']) == (
        4, 'UNAVAILABLE', 'TEMPORARILY_UNAVAILABLE', 'audit_unavailable')
    assert not any(call['handler_executed'] for call in value['data']['tool_calls'])


# ----------------------------------------------------------------- D: packaged assets and typed diagnostics
def test_d_asset_root_is_the_packaged_copy_when_present_and_the_checkout_otherwise(tmp_path) -> None:
    package = tmp_path / 'site-packages' / 'quati'
    package.mkdir(parents=True)
    assert contracts.asset_root(package) == tmp_path            # source layout: <root>/src/quati -> <root>
    (package / 'assets').mkdir()
    assert contracts.asset_root(package) == package / 'assets'
    assert contracts.asset_root() == REPOSITORY_ROOT == contracts.ASSET_ROOT == composition.REPOSITORY_ROOT
    assert contracts.CONTRACTS_DIR == REPOSITORY_ROOT / 'contracts'


def test_d_the_explicit_package_list_of_the_wheel_matches_the_source_tree() -> None:
    """pyproject.toml lists packages explicitly (the asset mapping needs it): no code package may be forgotten."""
    import tomllib
    setup = tomllib.loads((REPOSITORY_ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['tool']['setuptools']
    source = REPOSITORY_ROOT / 'src'
    code = sorted('.'.join(path.parent.relative_to(source).parts) for path in source.rglob('__init__.py'))
    assets = sorted(name for name in setup['package-dir'] if name.startswith('quati.assets.'))
    assert sorted(setup['packages']) == sorted(code + assets) and setup['package-dir'][''] == 'src'
    assert sorted(setup['package-data']) == assets
    for name in assets:
        directory = REPOSITORY_ROOT / setup['package-dir'][name]
        # The published layout mirrors the repository: quati/assets/<repository relative path>.
        assert name.removeprefix('quati.assets.').split('.') == list(directory.relative_to(REPOSITORY_ROOT).parts)
        assert not list(directory.glob('*.py')) and any(directory.glob(setup['package-data'][name][0]))


def test_d_a_missing_contract_schema_is_a_typed_diagnostic_without_a_path(tmp_path) -> None:
    """A broken installation is reported, not raised: NOT_FOUND / CONTRACT_NOT_FOUND naming the schema file only."""
    catalog = contracts.ContractCatalog(tmp_path / 'absent')
    with pytest.raises(ContractViolation) as caught:
        catalog.schema('behavior-package.schema.json')
    diagnostic = caught.value.diagnostics[0].to_json()
    assert (diagnostic['code'], diagnostic['reason'], diagnostic['path']) == (
        'NOT_FOUND', 'CONTRACT_NOT_FOUND', 'contracts/behavior-package.schema.json')
    assert str(tmp_path) not in json.dumps(diagnostic) and caught.value.rule_class == 1


def test_d_the_reference_hashes_of_the_active_package_are_unchanged() -> None:
    """The asset locator changes where files are found, never what is compiled."""
    reference = json.loads((REPOSITORY_ROOT / 'examples' / 'behavior' / 'compiled_receipt.reference.json').read_bytes())
    artifact = BehaviorCompiler(composition.REPOSITORY_ROOT).compile(composition.BEHAVIOR_PROFILE,
                                                                    model_role_ref=composition.MODEL_ROLE_REF)
    assert {name: artifact.receipt[name] for name in ('behavior_hash', 'statechart_hash', 'prompt_hash')} == {
        name: reference[name] for name in ('behavior_hash', 'statechart_hash', 'prompt_hash')}


# ----------------------------------------------------------------- C3: the installation record contract
def _record_validator():
    from jsonschema import Draft202012Validator
    contract = json.loads((REPOSITORY_ROOT / 'contracts' / 'identity.schema.json').read_text(encoding='utf-8'))
    return contract, Draft202012Validator({'$ref': '#/$defs/LocalInstallationRecord', '$defs': contract['$defs']})


def test_c3_the_record_written_by_init_is_valid_against_the_installation_record_contract(tmp_path) -> None:
    """LOG-0041 N12: contracts/identity.schema.json describes the signed LOCAL record, ``tenant_role`` included."""
    from quati.adapters.local_identity import TENANT_ROLES
    contract, validator = _record_validator()
    identity = LocalIdentity(tmp_path / 'config')
    identity.initialize()
    written = json.loads(identity.record_path.read_bytes())
    assert list(validator.iter_errors(written)) == [] and 'tenant_role' not in written
    definition = contract['$defs']['LocalInstallationRecord']
    assert tuple(definition['properties']['tenant_role']['enum']) == TENANT_ROLES
    assert 'tenant_role' not in definition['required']
    assert set(definition['required']) == set(written)
    for role in TENANT_ROLES:
        assert validator.is_valid({**written, 'tenant_role': role}), role
    for broken in ({**written, 'tenant_role': 'AUDITOR'}, {**written, 'tenant_id': ''}, {**written, 'owner_uid': '1000'},
                   {name: value for name, value in written.items() if name != 'organization_space_id'},
                   {**written, 'signature': 'not-base64'}):
        assert not validator.is_valid(broken), broken
    # What the contract requires as identifiers is what the adapter refuses to load without (B2).
    for field in IDENTITY_FIELDS:
        assert field in definition['required']
