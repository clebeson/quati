"""S00 CLI: no workers, durable commitments, external write tools or UI."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from urllib.parse import urlsplit

from secma.application.ports import ProviderConfig, ProviderError, valid_endpoint
from secma.application.catalog import CatalogSession, fixture_catalog, canonical_hash
from secma.domain.policy import Principal, Policy
from secma.behavior.compiler import compile_profile
from secma.adapters.evidence import write_receipt, redact
from secma.adapters.catalog_store import load_catalog, install_fixture


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('Invalid CLI arguments; use --help for command syntax')


def config_diagnostics(config):
    valid_name = bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', config.api_key_env))
    endpoint_ok = valid_endpoint(config.base_url)
    parts = urlsplit(config.base_url) if endpoint_ok else None
    missing = []
    if not endpoint_ok: missing.append('SECMA_BASE_URL: approved HTTPS endpoint required')
    if not config.model: missing.append('SECMA_MODEL')
    if not valid_name or not os.environ.get(config.api_key_env): missing.append('SECMA_API_KEY_ENV: configured secret reference required')
    if not config.allow_live: missing.append('SECMA_ALLOW_LIVE=1')
    available = importlib.util.find_spec('pydantic_ai') is not None
    if not available: missing.append('Install SECMA live optional dependency')
    return {'configured':not missing, 'missing':missing, 'adapter_installed':available,
            'model':config.model or None, 'endpoint_host':parts.hostname if endpoint_ok else None,
            'features':dict.fromkeys(['tools','structured_output','streaming','parallel_calls','usage'], 'NOT_VERIFIED'),
            'region':'NOT_VERIFIED', 'pricing':'NOT_VERIFIED'}


def ask(text, config, synthetic_evidence=False):
    if not text.strip() or len(text.encode()) > 8000:
        raise ValueError('Request must contain 1 to 8000 UTF-8 bytes')
    request_id = 'request-' + uuid.uuid4().hex
    principal = Principal('local-process-' + str(os.getuid() if hasattr(os, 'getuid') else 'user'), 'local')
    catalog = CatalogSession(load_catalog(), principal, Policy())
    result = {'request_id':request_id, 'commitment_id':None, 'scope':'S00_FIXTURE_ONLY',
              'status':'BLOCKED', 'tool_calls':[], 'uncertainties':[], 'next_action':None,
              'provider_used':False, 'usage':{'cost_usd':None}, 'evidence_refs':[]}
    greeting = re.fullmatch(r'(hello|hi|hey|good morning|good afternoon|good evening|oi|olá|bom dia|boa tarde|boa noite)[.!\s]*', text.strip(), re.I)
    code = 0
    receipt = None
    if greeting:
        result.update(status='RESPONDED', text=('Olá!' if greeting.group(1).lower() in {'oi','olá','bom dia','boa tarde','boa noite'} else 'Hello!'))
    else:
        diagnostics = config_diagnostics(config)
        if not diagnostics['configured']:
            result.update(error_code='NOT_CONFIGURED', uncertainties=diagnostics['missing'],
                          next_action='Configure an authorized model endpoint, model ID and secret reference.')
            code = 3
        else:
            compiled = compile_profile()
            receipt = compiled['receipt']
            try:
                from secma.adapters.model import ModelAdapter
                run = ModelAdapter(config).run(text, compiled['prompt'], catalog)
                result.update(classification=run.classification, provider_used=run.provider_used,
                              usage=run.usage, elapsed_seconds=run.elapsed_seconds, probe=run.probe)
                if synthetic_evidence:
                    result['synthetic_model_trace'] = run.calls
                if catalog.results:
                    result.update(status='FIXTURE_RESULT', text='Synthetic fixture result: ' + ' '.join(item['finding'] for item in catalog.results), results=catalog.results,
                                  uncertainties=['Synthetic fixtures only; no professional investigation or durable commitment.'])
                else:
                    result.update(status='BLOCKED', text='No verified fixture result was produced.',
                                  next_action='Review classification and provider/tool evidence; no work was accepted.')
                    code = 4
            except ProviderError as exc:
                result.update(error_code=exc.code, text=str(exc), provider_used=getattr(exc,'provider_used',False), usage=getattr(exc,'usage',{'cost_usd':None}), elapsed_seconds=getattr(exc,'elapsed_seconds',0), next_action='Resolve the provider gate and retry; no durable work was accepted.')
                code = 5
    result['tool_calls'] = catalog.events
    # Raw request and model text never enter stored receipts by default.
    evidence = {k:v for k,v in result.items() if k not in {'text', 'results', 'classification'}}
    evidence.update(request_hash=canonical_hash(text), output_hash=canonical_hash(result.get('text','')),
                    principal_hash=canonical_hash(principal.actor_id), tenant='local', policy_version=Policy.version,
                    prompt_receipt=receipt, model=config.model or None, config_hash=canonical_hash(config.__dict__), proof_tier='L3_CANDIDATE' if result['provider_used'] else 'L1',
                    status=result['status'])
    result['evidence_refs'] = [write_receipt(evidence)]
    return code, redact(result)


def main(argv=None):
    parser = Parser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    doctor = sub.add_parser('doctor'); doctor.add_argument('--json', action='store_true'); doctor.add_argument('--probe', action='store_true')
    query = sub.add_parser('ask'); query.add_argument('text'); query.add_argument('--json', action='store_true'); query.add_argument('--synthetic-evidence', action='store_true')
    cap = sub.add_parser('capabilities'); cap.add_argument('operation', choices=['list','search','describe','install']); cap.add_argument('value', nargs='?',default=''); cap.add_argument('--json', action='store_true'); cap.add_argument('--fixture-handler', choices=['incident','causal']); cap.add_argument('--enable-fixture', action='store_true')
    behavior = sub.add_parser('behavior'); behavior.add_argument('operation',choices=['compile']); behavior.add_argument('profile', nargs='?'); behavior.add_argument('--json',action='store_true')
    try:
        args = parser.parse_args(argv)
        config = ProviderConfig.from_environment()
        code = 0
        if args.command == 'doctor':
            value = {'status':'DIAGNOSTIC', 'scope':'S00_FIXTURE_ONLY', 'provider':config_diagnostics(config),
                     'durable_worker':'NOT_IMPLEMENTED', 'external_integrations':'NOT_VERIFIED_EXTERNAL'}
            if args.probe:
                if not value['provider']['configured']:
                    value['status']='BLOCKED'; code=3
                else:
                    from secma.adapters.model import ModelAdapter
                    value['probe'] = ModelAdapter(config).probe()
        elif args.command == 'ask':
            code,value = ask(args.text, config, args.synthetic_evidence)
        elif args.command == 'behavior':
            value = compile_profile(args.profile)
        elif args.command == 'capabilities' and args.operation == 'install':
            value = install_fixture(args.value, args.fixture_handler, args.enable_fixture)
        else:
            session = CatalogSession(load_catalog(), Principal('local-cli','local'), Policy())
            value = session.describe(args.value) if args.operation == 'describe' else session.search(args.value)
        print(json.dumps(redact(value), sort_keys=True, ensure_ascii=False))
        return code
    except ProviderError as exc:
        print(json.dumps({'status':'BLOCKED','error_code':exc.code,'message':str(exc)})); return 5
    except PermissionError:
        print(json.dumps({'status':'DENIED','message':'Operation denied by trusted policy'})); return 4
    except (ValueError, OSError, KeyError):
        print(json.dumps({'status':'ERROR','message':'Invalid input or unavailable local resource'})); return 2


if __name__ == '__main__':
    raise SystemExit(main())
