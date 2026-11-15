"""Explicit local fixture-definition installation, never plugin code execution."""
from pathlib import Path
import copy
import json
import os

from secma.application.catalog import fixture_catalog, canonical_hash
from secma.behavior.validated_reference import validate_schema
from secma.domain.policy import Policy, Principal


def _directory(data_dir=None):
    path = Path(data_dir or os.environ.get('SECMA_DATA_DIR', str(Path.home() / '.secma'))) / 'catalog'
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise PermissionError('Catalog path cannot traverse symlinks')
    return path


def _prepare(definition, handler):
    if handler not in {'incident','causal'}:
        raise PermissionError('Only measured local fixture implementations can be bound in S00')
    validate_schema(definition, 'scs-capability.schema.json')
    base = fixture_catalog()
    template = base.definitions['secma.fixture.' + handler]
    if definition['input_schema'] != template['input_schema'] or definition['output_schema'] != template['output_schema']:
        raise ValueError('Installed fixture schema must match the measured implementation')
    if definition['dependencies']:
        raise ValueError('Fixture bindings cannot load dependencies')
    promoted = copy.deepcopy(definition)
    promoted.update(lifecycle='enabled', assurance='C2')
    binding = copy.deepcopy(base.bindings['secma.fixture.' + handler])
    binding.update(id=promoted['id']+'.binding', capability_id=promoted['id'], capability_version=promoted['version'])
    if not Policy().authorize(Principal('local-operator','local'), promoted, binding):
        raise PermissionError('Fixture definition requests unavailable authority')
    return promoted, binding, base.handlers[binding['implementation_ref']]


def install_fixture(source, handler, enable_fixture=False, data_dir=None):
    if not enable_fixture:
        raise PermissionError('Explicit fixture activation is required')
    path = Path(source)
    if path.stat().st_size > 65536:
        raise ValueError('Manifest exceeds S00 size budget')
    definition = json.loads(path.read_text())
    promoted, binding, _ = _prepare(definition, handler)
    directory = _directory(data_dir)
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    target = directory / (canonical_hash(promoted['id']) + '.json')
    payload = {'definition':definition, 'fixture_handler':handler, 'explicit_fixture_activation':True,
               'assurance_scope':'SYNTHETIC_LOCAL_IMPLEMENTATION_ONLY'}
    with os.fdopen(os.open(target, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600), 'w') as f:
        json.dump(payload, f, indent=2); f.flush(); os.fsync(f.fileno())
    return {'status':'FIXTURE_ENABLED', 'capability_id':promoted['id'], 'assurance':'LOCAL_FIXTURE_ONLY',
            'manifest_hash':canonical_hash(definition)}


def load_catalog(data_dir=None):
    catalog = fixture_catalog()
    directory = _directory(data_dir)
    files = sorted(directory.glob('*.json'))
    if len(files) > 20:
        raise ValueError('S00 fixture catalog limit exceeded')
    for path in files:
        if path.is_symlink() or path.stat().st_size > 65536:
            raise ValueError('Invalid installed fixture file')
        record = json.loads(path.read_text())
        if record.get('explicit_fixture_activation') is not True:
            raise PermissionError('Missing local fixture activation')
        definition,binding,handler = _prepare(record['definition'], record['fixture_handler'])
        catalog.register(definition,binding,handler)
    return catalog
