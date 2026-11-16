"""S00 CLI use cases. Dependencies are injected; business success needs evidence."""
import hashlib
from datetime import datetime, timezone
from typing import Callable, Protocol

from quati.application.ask import ask_probe_profile, feature_gate, is_social_only, run_ask, social_reply
from quati.application.identity import AccessDenied, RequestContext, canonical_bytes
from quati.application.ports import ProviderConfig
from quati.application.providers import (
    FEATURES, PROBE_STOP_CODES, ProviderError, create_provider, diagnostics_for)
from quati.domain.diagnostics import ContractViolation

PROBE_NEXT_ACTIONS = {
    'UNAUTHENTICATED': 'Replace the provider credential or sign in to the provider executable.',
    'FORBIDDEN': 'Use a credential that is allowed to call the configured model.',
    'BUDGET_EXCEEDED': 'Raise the run budget or start a new run.',
}
# M01-FR-01: the slice that delivers each command group that is registered but not delivered yet.
UNDELIVERED = {'status': 'S02', 'tell': 'S02', 'approvals': 'S02', 'approve': 'S02', 'deny': 'S02',
               'inbox': 'S02', 'messages': 'S02', 'worker': 'S02', 'trace': 'S02',
               'config': 'S03', 'behavior': 'S03'}
# M17 configuration reasons that mean "present but invalid" (CONFIG_INVALID) rather than "absent".
PROVIDER_INVALID_REASONS = ('TRANSPORT_UNKNOWN', 'ENDPOINT_INVALID', 'MODEL_INVALID', 'API_KEY_REF_INVALID')
POLICY_ABSENT_CAUSES = ('missing', 'identity_unavailable')
FEATURE_VERDICTS = ('SUPPORTED', 'UNSUPPORTED', 'NOT_VERIFIED')
GREETINGS = {
    'hello': 'Hello!', 'hi': 'Hello!', 'hey': 'Hello!',
    'good morning': 'Hello!', 'good afternoon': 'Hello!', 'good evening': 'Hello!',
    'oi': 'Olá!', 'olá': 'Olá!', 'bom dia': 'Olá!', 'boa tarde': 'Olá!', 'boa noite': 'Olá!',
    'ola': 'Olá!', 'hola': '¡Hola!', 'buenos días': '¡Hola!', 'buenos dias': '¡Hola!', 'buenas tardes': '¡Hola!',
    'buenas noches': '¡Hola!', 'bonjour': 'Bonjour!', 'bonsoir': 'Bonsoir!', 'salut': 'Salut!',
    'hallo': 'Hallo!', 'guten tag': 'Hallo!', 'guten morgen': 'Hallo!', 'guten abend': 'Hallo!',
    'ciao': 'Ciao!', 'buongiorno': 'Buongiorno!',
}


def response(status='SUCCEEDED', data=None, code=None, message=None, next_action=None, uncertainties=()):
    return {'status': status, 'data': data, 'evidence_refs': [],
            'uncertainties': list(uncertainties), 'next_action': next_action,
            'error': None if code is None else {'code': code, 'message': message, 'retryable': False}}


def config_diagnostics(config):
    """Configuration availability is distinct from an actual provider feature probe."""
    return diagnostics_for(config)


class IdentityPort(Protocol):
    def authenticate(self) -> RequestContext: ...
    def initialize(self) -> dict: ...
    def diagnostics(self) -> dict: ...


MAX_TEXT_BYTES = 65536  # M01 cli.max_text_bytes: ask/tell TEXT and one chat input line

class CLIService:
    def __init__(self, identity: IdentityPort, config: ProviderConfig, evidence_sink: Callable[[dict], dict],
                 provider_factory=create_provider, policy_loader=None, policy_installer=None,
                 feature_reports=None, ask_runtime=None, clock=None, behavior_check=None, runtime_facts=None):
        # feature_reports / ask_runtime default to None: the model path then stays closed (fail closed).
        # behavior_check() -> the active behavior package status; runtime_facts() -> measured host facts.
        self.behavior_check = behavior_check
        self.runtime_facts = runtime_facts
        self.feature_reports = feature_reports
        self.ask_runtime = ask_runtime
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.identity = identity
        self.policy_loader = policy_loader
        self.policy_installer = policy_installer
        self.config = config
        self.evidence_sink = evidence_sink
        self.provider_factory = provider_factory

    def initialize(self):
        """Bootstrap identity, then (RFC-014 5.1) the LOCAL policy and its audited registry revision 1."""
        summary = self.identity.initialize()
        if self.policy_installer is None:
            return 0, response(data=summary)
        outcome, event = self.policy_installer(summary)
        result = response(data={**summary, 'policy': outcome})
        if event is not None:
            receipt = self.evidence_sink(event)
            result['evidence_refs'] = [f"sha256:{receipt['sha256']}:{receipt['path']}"]
        return 0, result

    def doctor(self, probe=False):
        """M01 ``DoctorReport``: read-only, no provider call, usable with no identity (M01-AT-01)."""
        provider, context = config_diagnostics(self.config), self._lazy_context()
        identity, policy, behavior = self.identity.diagnostics(), self._policy(context), self._behavior()
        facts = self._facts(context)
        checks = _config_checks(identity, policy, provider, behavior)
        provider['measured_support'] = 'NOT_VERIFIED'
        if not probe:
            self._measured(provider, context)
        data = {'scope': 'S00_T01_LOCAL_CLI', 'profile': 'LOCAL', **facts,
                'config_valid': not any(check['status'] == 'INVALID' for check in checks),
                'provider': provider, 'identity': identity,
                'live_calls_allowed': bool(self.config.allow_live),
                'worker': {'status': 'NOT_APPLICABLE', 'reason': 'worker_not_delivered'},
                'durable_worker': 'NOT_IMPLEMENTED', 'external_integrations': 'NOT_VERIFIED_EXTERNAL',
                'policy': policy, 'behavior': behavior,
                'warnings': _warnings(identity, policy, provider, behavior, facts)}
        if not probe:
            return 0, response(data=data)
        return self._probe(data)

    def _behavior(self):
        """The active behavior package as the injected compiler check reports it (path-specific diagnostics)."""
        if self.behavior_check is None:
            return {'status': 'NOT_VERIFIED', 'profile_ref': None, 'diagnostics': []}
        return self.behavior_check()

    def _lazy_context(self):
        """Authenticate at most once per report, and only when a check needs it; None when unauthenticated."""
        cache = []

        def context():
            if not cache:
                try:
                    cache.append(self.identity.authenticate())
                except AccessDenied:
                    cache.append(None)
            return cache[0]
        return context

    def _facts(self, context):
        """Measured host facts; the profile path is shown only to an authenticated identity (IDN-01)."""
        if self.runtime_facts is None:
            return {}
        facts = dict(self.runtime_facts())
        if context() is None:
            facts['config_dir'] = None
        return facts

    def _measured(self, provider, context):
        """M01 ``provider.measured_support``: the stored FeatureReport of exactly this configuration.

        Read-only and only for an authenticated identity; a report that is absent, altered, stale or
        measured for another configuration leaves every feature NOT_VERIFIED (M17-RT-01).
        """
        if self.feature_reports is None or not provider['configured'] or context() is None:
            return
        gate = feature_gate(self.feature_reports, self.provider_factory(self.config), self.clock())
        if gate['report_ref'] is None or 'STALE' in (gate['tools'], gate['structured_output']):
            return
        loaded = self.feature_reports.load(gate['config_hash'])
        if loaded is None:  # replaced between the two reads: not measured
            return
        report = loaded['report']
        features = report['features']
        provider['features'] = {name: features.get(name) if features.get(name) in FEATURE_VERDICTS
                                else 'NOT_VERIFIED' for name in FEATURES}
        provider['feature_report'] = {'ref': gate['report_ref'], 'measured_at': gate['measured_at'],
                                      'observed_model_id': gate['observed_model_id'] or None,
                                      'gate_reason': gate['reason']}
        if _probe_answered(report):
            provider['status'] = 'PROBED'
        if gate['tools'] == 'SUPPORTED':
            provider['measured_support'] = 'SUPPORTED'

    def config_validate(self, file=None):
        """M01 ``quati config validate``: the S00 configuration checks, read-only and without identity."""
        if file is not None:  # profile configuration files belong to ProfilePort (S03)
            return self.unsupported('config validate FILE')
        context = self._lazy_context()
        identity, policy = self.identity.diagnostics(), self._policy(context)
        checks = _config_checks(identity, policy, config_diagnostics(self.config), self._behavior())
        facts = self._facts(context)
        invalid = [check for check in checks if check['status'] == 'INVALID']
        data = {'valid': not invalid, 'config_dir': facts.get('config_dir'), 'checks': checks}
        open_items = [f"{check['name']}: {check['status']}" + (
            f" ({', '.join(check['reasons'])})" if check['status'] == 'INVALID' else '')
            for check in checks if check['status'] != 'OK']
        if invalid:
            return 2, response('DENIED', data, 'CONFIG_INVALID', 'The local configuration is present but invalid.',
                               'Correct the checks reported INVALID in data.checks; nothing was changed.', open_items)
        if open_items:
            return 0, response('PARTIAL', data, uncertainties=open_items, next_action=(
                'Nothing is invalid; complete the checks reported NOT_CONFIGURED (quati init, provider settings).'))
        return 0, response(data=data)

    def _policy(self, context):
        """M25-RT-01: report the policy loader's verdict as a cause code only, never file content."""
        if self.policy_loader is None:  # no loader wired: fail closed without touching identity
            return {'status': 'UNAVAILABLE', 'reason': 'loader_error'}
        authenticated = context()
        tenant_id = None if authenticated is None else authenticated.tenant_id
        try:
            state = self.policy_loader(tenant_id)
        except Exception:  # noqa: BLE001 - a raising loader fails closed (K6)
            return {'status': 'UNAVAILABLE', 'reason': 'loader_error'}
        return {'status': 'AVAILABLE' if state.available else 'UNAVAILABLE', 'reason': state.cause}

    def probe(self):
        """M17 ``quati models probe``: measure the configured provider with live nonce round-trips."""
        return self._probe({'scope': 'M17_PROVIDER_PROBE', 'provider': config_diagnostics(self.config)})

    def _probe(self, data):
        provider = data['provider']
        if not provider['configured']:
            return 3, response('BLOCKED', data, 'NOT_CONFIGURED', 'Provider configuration is incomplete.',
                               'Configure the authorized Quati model endpoint and secret reference.', provider['missing'])
        # IDN-01 / M02 authorization order row 1: authenticate before any provider call or any write under
        # the data directory (receipt, feature report). AccessDenied propagates as the typed denial (exit 4).
        self.identity.authenticate()
        try:
            report = self.provider_factory(self.config).probe(ask_probe_profile())
        except ProviderError as exc:
            return 3, response('BLOCKED', data, exc.code, exc.message,
                               'Configure the authorized Quati model endpoint and secret reference.', [exc.reason])
        receipt = self.evidence_sink({'kind': 'feature_report', **report})
        if self.feature_reports is not None:
            self.feature_reports.save(report, receipt)
        reference = f"sha256:{receipt['sha256']}:{receipt['path']}"
        report = {**report, 'evidence_refs': [reference]}
        data['feature_report'] = report
        provider['features'] = dict(report['features'])
        observations = report['observations']
        attempts = report.get('attempts') or {}
        details = report.get('details') or {}
        data['verdicts'] = {name: {'verdict': report['features'][name], 'reason': observations[name],
                                   'attempts': attempts.get(name, 0),
                                   'detail': (details.get(name) or {}).get('detail')} for name in FEATURES}
        weak = [f'{name}: {report["features"][name]} ({observations[name]})'
                for name in FEATURES if report['features'][name] != 'SUPPORTED']
        aborted = report['aborted']
        if aborted in ('UNAUTHENTICATED', 'FORBIDDEN'):
            code, result = 4, response('DENIED', data, aborted, 'The provider rejected the credential or denied access.',
                                       PROBE_NEXT_ACTIONS[aborted], weak)
        elif aborted == 'BUDGET_EXCEEDED':
            code, result = 4, response('BLOCKED', data, aborted, 'The run budget for provider calls is exhausted.',
                                       PROBE_NEXT_ACTIONS[aborted], weak)
        elif aborted == 'NOT_CONFIGURED':
            code, result = 3, response('BLOCKED', data, aborted, 'Provider configuration is incomplete.',
                                       'Configure the authorized Quati model endpoint and secret reference.', weak)
        elif not any(_exchange_completed(report, name) for name in FEATURES if name != 'timeout'):
            code, result = 5, response('UNAVAILABLE', data, 'TEMPORARILY_UNAVAILABLE',
                                       'The provider did not complete any probe exchange.',
                                       'Check the provider service and network, then probe again.', weak)
        else:
            provider['status'] = 'PROBED'
            gaps = _ask_gaps(report)
            provider['measured_support'] = 'NOT_VERIFIED' if gaps else 'SUPPORTED'
            if gaps:
                # R3: `quati ask` needs tools SUPPORTED from an observed model; anything less is never SUCCEEDED.
                code, result = 0, response('PARTIAL', data, uncertainties=[*weak, *gaps], next_action=(
                    '`quati ask` will refuse this provider until tools are SUPPORTED by an observed model; '
                    'check the provider, then probe again.'))
            else:
                code, result = 0, response(data=data, uncertainties=weak)
        result['evidence_refs'] = [reference]
        return code, result

    def ask(self, text, synthetic_evidence=False, eval_permutation_seed=None):
        if eval_permutation_seed is not None and not synthetic_evidence:
            # EVAL-PERM: an evaluator-only presentation option; never on a normal (non-synthetic) ask.
            return 2, response('DENIED', code='INVALID_INPUT', message=(
                '--eval-candidate-permutation-seed is accepted only with --synthetic-evidence.'),
                next_action='Add --synthetic-evidence (synthetic evaluations only) or drop the seed.')
        if not text.strip() or len(text.encode('utf-8')) > MAX_TEXT_BYTES:
            return 2, response('DENIED', code='INVALID_INPUT',
                               message=f'Request must contain 1 to {MAX_TEXT_BYTES} UTF-8 bytes.',
                               next_action='Provide a nonempty request within the byte limit.')
        context = self.identity.authenticate()
        greeting = GREETINGS.get(text.strip().rstrip('.! \t\r\n').casefold())
        data = {'request_id': context.request_id, 'trace_id': context.trace_id, 'commitment_id': None,
                'scope': 'S00_T01_LOCAL_CLI', 'provider_used': False, 'tool_calls': [], 'usage': {'cost_usd': None},
                'received': True, 'launched': False, 'delivered': False}
        if greeting:
            data.update(result_status='RESPONDED', result_kind='GREETING', text=greeting)
            return self._record(text, context, 0, response(data=data))
        # G1: a social-only text with a template is answered without any model or tool, so neither the
        # provider configuration nor the measured tool gate may block it. Anything else stays fail closed.
        template = social_reply(text, GREETINGS) if is_social_only(text) else None
        data['result_kind'] = 'BLOCKED'
        if not config_diagnostics(self.config)['configured'] or self.feature_reports is None or self.ask_runtime is None:
            if template is not None:
                return self._template_greeting(text, context, data, template, ['PROVIDER_PATH_UNAVAILABLE'])
            code, result = self._work_unavailable(data)
            return self._record(text, context, code, result)
        provider = self.provider_factory(self.config)
        gate = feature_gate(self.feature_reports, provider, self.clock())
        if gate['tools'] != 'SUPPORTED' and template is not None:
            return self._template_greeting(text, context, data, template, [f"TOOLS_{gate['tools']}"],
                                           extra={'feature_gate': gate})
        if gate['tools'] != 'SUPPORTED':
            # CAP-05 / M17-AT-01: UNKNOWN is never SUPPORTED; refuse before any model or binding call.
            data.update(reason='MODEL_INCOMPATIBLE', feature_support=gate['tools'])
            result = response('UNAVAILABLE', data, 'UNSUPPORTED',
                              'The configured model has no current measured tool support for this configuration.',
                              'Run `quati models probe` for this provider configuration; no work was accepted.',
                              ['MODEL_INCOMPATIBLE', f"TOOLS_{gate['tools']}",
                               *([gate['reason']] if gate['reason'] else [])])
            return self._record(text, context, 4, result, extra={'feature_gate': gate})
        try:
            runtime = self.ask_runtime(context)
        except ContractViolation as exc:
            # CMP-02 on the runtime path: the active behavior package or statechart does not compile.
            data.update(reason='BEHAVIOR_PACKAGE_INVALID', rule_class=exc.rule_class,
                        diagnostics=[item.to_json() for item in exc.diagnostics])
            result = response('BLOCKED', data, 'CONFIG_INVALID',
                              'The active behavior package or statechart failed validation.',
                              'Correct the fields named in data.diagnostics (see `quati doctor`); no work was accepted.',
                              [f'{item.code.value} {item.reason} at {item.path}' for item in exc.diagnostics])
            return self._record(text, context, 2, result, extra={'feature_gate': gate})
        code, result, receipt = run_ask(text, context, provider=provider, runtime=runtime,
                                        gate=gate, clock=self.clock, greetings=GREETINGS,
                                        synthetic=synthetic_evidence, eval_permutation_seed=eval_permutation_seed)
        return self._record(text, context, code, result, extra=receipt, proof_tier=None)

    def _template_greeting(self, text, context, data, template, uncertainties, extra=None):
        data.update(result_status='RESPONDED', result_kind='GREETING', text=template)
        return self._record(text, context, 0, response(data=data, uncertainties=[
            'DETERMINISTIC_SOCIAL_TEMPLATE', *uncertainties]), extra=extra)

    @staticmethod
    def unsupported(command):
        """M01-FR-01: a command whose owning slice is not delivered; reads and changes nothing."""
        slice_id = UNDELIVERED[command.split()[0]]
        return 4, response('UNAVAILABLE', None, 'UNSUPPORTED',
                           f'The {command} command is delivered in slice {slice_id} and is not available yet.',
                           f'No work was read or changed; this command becomes available in slice {slice_id}.')

    def _work_unavailable(self, data):
        diagnostics = config_diagnostics(self.config)
        if not diagnostics['configured']:
            return 3, response('BLOCKED', data, 'NOT_CONFIGURED', 'No configured provider can process this request.',
                               'Configure the authorized model; no durable work was accepted.', diagnostics['missing'])
        return 4, response('UNAVAILABLE', data, 'UNSUPPORTED', 'Discovery execution is not qualified in this delivery.',
                           'Complete the remaining S00 tasks; no durable work was accepted.')

    def _record(self, text, context, code, result, extra=None, proof_tier='L1'):
        record = {'request_id': context.request_id, 'trace_id': context.trace_id,
                  'principal_hash': hashlib.sha256(context.actor_id.encode()).hexdigest(),
                  'request_hash': hashlib.sha256(text.encode()).hexdigest(),
                  'output_hash': hashlib.sha256(canonical_bytes(result)).hexdigest(),
                  'status': result['status'], 'policy_version': context.policy_version,
                  'proof_tier': proof_tier, 'provider_used': False, 'cost_usd': None, **(extra or {})}
        receipt = self.evidence_sink(record)
        result['evidence_refs'] = [f"sha256:{receipt['sha256']}:{receipt['path']}"]
        return code, result


def _config_checks(identity, policy, provider, behavior):
    """M01 ``ConfigValidation.checks``: OK, NOT_CONFIGURED (absent) or INVALID (present but rejected)."""
    def check(name, status, reasons=()):
        return {'name': name, 'status': status, 'reasons': list(reasons)}

    checks = [check('identity', 'OK') if identity.get('initialized')
              else check('identity', 'NOT_CONFIGURED', ['identity_not_initialized'])]
    if policy['status'] == 'AVAILABLE':
        checks.append(check('policy', 'OK'))
    else:
        checks.append(check('policy', 'NOT_CONFIGURED' if policy['reason'] in POLICY_ABSENT_CAUSES else 'INVALID',
                            [policy['reason']]))
    if provider['configured']:
        checks.append(check('provider', 'OK'))
    else:
        invalid = any(reason in PROVIDER_INVALID_REASONS for reason in provider['reasons'])
        checks.append(check('provider', 'INVALID' if invalid else 'NOT_CONFIGURED', provider['reasons']))
    if behavior['status'] == 'INVALID':
        checks.append(check('behavior', 'INVALID', [f"{item['code']} {item['reason']} at {item['path']}"
                                                    for item in behavior['diagnostics']]))
    else:
        checks.append(check('behavior', 'OK' if behavior['status'] == 'VALID' else 'NOT_CONFIGURED',
                            [] if behavior['status'] == 'VALID' else ['behavior_not_verified']))
    return checks


def _warnings(identity, policy, provider, behavior, facts):
    """M01 ``DoctorReport.warnings``: stable tags only, never file content or a secret."""
    warnings = []
    if not identity.get('initialized'):
        warnings.append('identity_not_initialized')
    if policy['status'] != 'AVAILABLE':
        warnings.append(f"policy_unavailable:{policy['reason']}")
        if 'wrong_mode' in str(policy['reason']):
            warnings.append('config_mode_too_open')
    if not provider['configured']:
        warnings.append('provider_not_configured')
    if behavior['status'] == 'INVALID':
        warnings.append('behavior_package_invalid')
    if facts.get('os_qualification', 'QUALIFIED') != 'QUALIFIED':
        warnings.append('os_not_qualified')
    if facts.get('sqlite_ok') is False:
        warnings.append('sqlite_fts5_missing')
    if facts.get('listening_sockets'):
        warnings.append('listening_socket_open')
    return warnings


def _probe_answered(report):
    """The condition under which the probe command exits 0 (M17 probe command table) for a stored report."""
    try:
        return report.get('aborted') not in PROBE_STOP_CODES and any(
            _exchange_completed(report, name) for name in FEATURES if name != 'timeout')
    except (KeyError, TypeError):
        return False


def _ask_gaps(report):
    """Why the measured report cannot gate `quati ask` (tools verdict, observed model id); empty when it can."""
    gaps = []
    verdict = report['features']['tools']
    if verdict != 'SUPPORTED':
        gaps.append(f"TOOLS_{verdict}:{report['observations']['tools']}")
    if not report.get('observed_model_id'):
        gaps.append('MODEL_ID_UNOBSERVED')
    return gaps


def _exchange_completed(report, feature):
    """True when the provider answered the probe for this feature, whatever the verdict."""
    status, observation = report['features'][feature], report['observations'][feature]
    if observation == 'SINGLE_CHUNK':
        return True
    return status == 'SUPPORTED' or (status == 'UNSUPPORTED' and observation != 'STREAMING_UNSUPPORTED')
