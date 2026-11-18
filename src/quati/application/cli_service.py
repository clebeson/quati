"""S00 CLI use cases. Dependencies are injected; business success needs evidence."""
import hashlib
from datetime import datetime, timezone
from typing import Callable, Protocol

from quati.application.ask import ask_probe_profile, feature_gate, run_ask, social_outcome
from quati.application.identity import AccessDenied, RequestContext, canonical_bytes
from quati.application.ports import ProviderConfig
from quati.application.providers import (
    FEATURES, PROBE_STOP_CODES, ProviderError, create_provider, diagnostics_for)
from quati.domain.capability_registry import Refusal
from quati.domain.diagnostics import ContractViolation, settled_exit

PROBE_NEXT_ACTIONS = {
    'UNAUTHENTICATED': 'Replace the provider credential or sign in to the provider executable.',
    'FORBIDDEN': 'Use a credential that is allowed to call the configured model.',
    'BUDGET_EXCEEDED': 'Raise the run budget or start a new run.',
}
# M01-FR-01: the slice that delivers each command group that is registered but not delivered yet.
UNDELIVERED = {'status': 'S02', 'tell': 'S02', 'approvals': 'S02', 'approve': 'S02', 'deny': 'S02',
               'inbox': 'S02', 'messages': 'S02', 'worker': 'S02', 'trace': 'S02',
               'config': 'S03', 'behavior': 'S03',
               # Commands that other PRDs, an M02 next_action or RFC-013 name (LOG-0041 N15): M25 policy and
               # approvals (S02), M02 spaces (S02), M13 prefs, M12 artifact, M11 memory (S03), M20 brains (S04),
               # RFC-013 SERVER profile: server, login, grants (S05).
               'spaces': 'S02', 'policy': 'S02', 'prefs': 'S03', 'artifact': 'S03', 'memory': 'S03',
               'brains': 'S04', 'server': 'S05', 'login': 'S05', 'grants': 'S05'}
# M02 "Reason -> next_action" (LOCAL column) for a credential that is present but rejected: `quati doctor`.
IDENTITY_NEXT_ACTIONS = {
    'credential_insecure': ('Make the Quati configuration directory (mode 0700) and its credential files (mode 0600) '
                            'real paths owned by you, not symlinks, then run `quati doctor` again; nothing was changed.'),
    'credential_corrupt': ('The local credential is present but was rejected; restore the installation record and '
                           'the device key from your backup, then run `quati doctor` again; nothing was changed.'),
}
# M17 configuration reasons that mean "present but invalid" (CONFIG_INVALID) rather than "absent".
PROVIDER_INVALID_REASONS = ('TRANSPORT_UNKNOWN', 'ENDPOINT_INVALID', 'MODEL_INVALID', 'API_KEY_REF_INVALID')
POLICY_ABSENT_CAUSES = ('missing', 'identity_unavailable')
FEATURE_VERDICTS = ('SUPPORTED', 'UNSUPPORTED', 'NOT_VERIFIED')


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
ADMISSION_NEXT_ACTION = ('No model was called and no work was accepted; resolve the reported reason '
                         '(see `quati doctor`), then retry.')

class CLIService:
    def __init__(self, identity: IdentityPort, config: ProviderConfig, evidence_sink: Callable[[dict], dict],
                 provider_factory=create_provider, policy_loader=None, policy_installer=None,
                 feature_reports=None, ask_runtime=None, clock=None, behavior_check=None, runtime_facts=None,
                 authorize=None, state_guard=None, identity_inspector=None, conversation=None):
        # feature_reports / ask_runtime default to None: the model path then stays closed (fail closed).
        # behavior_check() -> the active behavior package status; runtime_facts() -> measured host facts.
        # authorize(context, operation, action) -> None or a denial with to_response(): the AuthorizationPort
        # enforcement point of the tenant registry; None (not wired) refuses every probe (fail closed).
        # state_guard(*names) raises unless those data directories are private directories of this user:
        # 'capabilities' is the registry store as verified before an authorization decision (directories
        # and fixed files), 'capability_packages' its stored packages (verified after the decision),
        # '<name>:read' verifies as a reader, and 'audit_log' raises the Refusal audit_unavailable for an
        # unusable registry audit log.
        # identity_inspector() -> {present, cause, detail}: why an unaccepted credential is not accepted.
        self.conversation = conversation
        self.authorize = authorize
        self.state_guard = state_guard
        self.identity_inspector = identity_inspector
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
        self._require_state('receipts')  # the policy receipt must be writable before a credential is created
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
        identity, policy, behavior = self._identity(), self._policy(context), self._behavior()
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
            return 0, response(data=data, next_action=IDENTITY_NEXT_ACTIONS.get(identity.get('reason')))
        return self._probe(data)

    def _require_state(self, *names):
        """LOG-0041 N1: the named data directories are verified before anything is read, called or changed."""
        if self.state_guard is not None:
            self.state_guard(*names)

    def _identity(self):
        """The identity block: an unaccepted credential is NOT_CONFIGURED only when none exists (M02 reasons)."""
        identity = dict(self.identity.diagnostics())
        if identity.get('initialized') or self.identity_inspector is None:
            return identity
        state = self.identity_inspector()
        identity.update(status='INVALID' if state['present'] else 'NOT_CONFIGURED',
                        reason=state['cause'], detail=state['detail'])
        return identity

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
        identity, policy = self._identity(), self._policy(context)
        checks = _config_checks(identity, policy, config_diagnostics(self.config), self._behavior())
        facts = self._facts(context)
        invalid = [check for check in checks if check['status'] == 'INVALID']
        data = {'valid': not invalid, 'config_dir': facts.get('config_dir'), 'checks': checks}
        open_items = [f"{check['name']}: {check['status']}" + (
            f" ({', '.join(check['reasons'])})" if check['status'] == 'INVALID' else '')
            for check in checks if check['status'] != 'OK']
        if invalid:
            repair = ' Run `quati doctor` for the identity cause.' if identity.get('status') == 'INVALID' else ''
            return 2, response('DENIED', data, 'CONFIG_INVALID', 'The local configuration is present but invalid.',
                               'Correct the checks reported INVALID in data.checks; nothing was changed.' + repair,
                               open_items)
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
        context = self.identity.authenticate()
        # LOG-0041 N7: nothing is spent on a provider before the result can be stored and the caller may
        # replace the report that gates `ask` (`manage` on the tenant registry, logged as authz.decided).
        # LOG-0044 X13: the registry store, whose audit log records the decision, is verified as well, so
        # an unsafe ``capabilities`` has the reason every other command gives for it.
        self._require_state('receipts', 'feature_reports', 'capabilities')
        denied = self._authorized(context, 'models_probe', 'manage')
        if denied is not None:
            return denied
        try:
            report = self.provider_factory(self.config).probe(ask_probe_profile())
        except ProviderError as exc:
            return 3, response('BLOCKED', data, exc.code, exc.message,
                               'Configure the authorized Quati model endpoint and secret reference.', [exc.reason])
        stored, references = {'receipt': False, 'feature_report': False}, []
        try:
            receipt = self.evidence_sink({'kind': 'feature_report', **report})
            stored['receipt'] = True
            references.append(f"sha256:{receipt['sha256']}:{receipt['path']}")
            if self.feature_reports is not None:
                self.feature_reports.save(report, receipt)
            stored['feature_report'] = True
        except OSError:
            # The directories were verified before the call, so this is a late failure (for example a full
            # disk). The call was made: say so, and say that nothing gates `ask` (never INTERNAL_ERROR).
            data.update(reason='feature_report_not_stored', provider_call_made=True, stored=stored,
                        feature_report=report)
            result = response('UNAVAILABLE', data, 'TEMPORARILY_UNAVAILABLE',
                              'The provider answered the probe, but the measured report could not be stored.',
                              'Check the free space and the permissions of the data directory, then probe again; '
                              '`quati ask` keeps refusing this provider until a report is stored.',
                              ['FEATURE_REPORT_NOT_STORED'])
            result['evidence_refs'] = references
            return settled_exit(5, result), result      # a local store, not the provider: 4 by the shared rule
        reference = references[0]
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

    def _authorized(self, context, operation, action):
        """None when the AuthorizationPort allows and logged the action; otherwise the typed denial (exit 4)."""
        if self.authorize is None:
            return 4, response('DENIED', {'reason': 'AUTHORIZATION_UNAVAILABLE'}, 'FORBIDDEN',
                               'No authorization port is available for this command.',
                               'Nothing was called or changed; this command needs the registry authorization port.')
        blocked = self.authorize(context, operation, action)
        return None if blocked is None else (4, blocked.to_response())

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
        if self.conversation is not None:
            self.conversation.admit(context)
        self._require_state('receipts')  # LOG-0041 N1: before any read, handler or receipt
        data = {'request_id': context.request_id, 'trace_id': context.trace_id, 'commitment_id': None,
                'scope': 'S00_T01_LOCAL_CLI', 'provider_used': False, 'tool_calls': [], 'usage': {'cost_usd': None},
                'received': True, 'launched': False, 'delivered': False}
        # M01 exit precedence (2 before 3, 4 and 5): an active behavior package that does not compile
        # is CONFIG_INVALID for every ask, before the text or the provider state is looked at.
        behavior = self._behavior()
        if behavior['status'] == 'INVALID':
            result = self._behavior_invalid(data, behavior['rule_class'], behavior['diagnostics'])
            return self._record(text, context, 2, result)
        # LOG-0041 D1: text that is social-only by the code-owned table is answered by the application
        # here, before the provider configuration, the feature report or the model is looked at, so the
        # outcome is the same in every provider state. Anything else stays fail closed.
        social = social_outcome(text)
        if social is not None:
            data.update(social)
            return self._record(text, context, 0, response(data=data))
        data['result_kind'] = 'BLOCKED'
        if not config_diagnostics(self.config)['configured'] or self.feature_reports is None or self.ask_runtime is None:
            code, result = self._work_unavailable(data)
            return self._record(text, context, code, result)
        # LOG-0044 X13: the FeatureReport store is verified (as a reader) before it is read, so an unsafe
        # directory is state_dir_unsafe and never "no measured support, run a probe".
        self._require_state('feature_reports:read')
        provider = self.provider_factory(self.config)
        gate = feature_gate(self.feature_reports, provider, self.clock())
        if gate['tools'] != 'SUPPORTED':
            # CAP-05 / M17-AT-01: UNKNOWN is never SUPPORTED; refuse before any model or binding call.
            data.update(reason='MODEL_INCOMPATIBLE', feature_support=gate['tools'])
            result = response('UNAVAILABLE', data, 'UNSUPPORTED',
                              'The configured model has no current measured tool support for this configuration.',
                              'Run `quati models probe` for this provider configuration; no work was accepted.',
                              ['MODEL_INCOMPATIBLE', f"TOOLS_{gate['tools']}",
                               *([gate['reason']] if gate['reason'] else [])])
            return self._record(text, context, 4, result, extra={'feature_gate': gate})
        # M01 "Data directory" rules 2 and 4 (LOG-0044 X6): the registry store, its audit log and the
        # caller's grant are verified before the registry, a handler or the model is used, so each refusal
        # costs zero model calls and does not depend on the model.
        self._require_state('capabilities')
        refused = self._admission(context)
        if refused is not None:
            status, code, reason, message, next_action = refused
            data.update(reason=reason)
            result = response(status, data, code, message, next_action, [reason])
            return self._record(text, context, 4, result, extra={'feature_gate': gate})
        self._require_state('capability_packages')  # after the allowed decision, before any registry read
        try:
            runtime = self.ask_runtime(context)
        except ContractViolation as exc:
            # CMP-02 on the runtime path: the active behavior package or statechart does not compile.
            result = self._behavior_invalid(data, exc.rule_class, [item.to_json() for item in exc.diagnostics])
            return self._record(text, context, 2, result, extra={'feature_gate': gate})
        code, result, receipt = run_ask(text, context, provider=provider, runtime=runtime, gate=gate, clock=self.clock,
                                        synthetic=synthetic_evidence, eval_permutation_seed=eval_permutation_seed)
        return self._record(text, context, code, result, extra=receipt)

    def _admission(self, context):
        """None when a work ask may use the registry; otherwise (status, code, reason, message, next_action).

        The audit log must be usable (``audit_unavailable``) and the AuthorizationPort must allow, and log,
        ``read`` on the tenant's registry (operation ``ask_admission``; M02 authorization order rows 4 and 7).
        The tool calls of the turn stay the enforcement point: an unwired port only skips this early check."""
        try:
            self._require_state('audit_log')
        except Refusal as exc:
            return exc.status, exc.code, exc.reason, exc.message, ADMISSION_NEXT_ACTION
        blocked = None if self.authorize is None else self.authorize(context, 'ask_admission', 'read')
        if blocked is None:
            return None
        value = blocked.to_response()
        return (value['status'], value['error']['code'], value['data']['reason'],
                'The request was refused before any model call.', value['next_action'] or ADMISSION_NEXT_ACTION)

    @staticmethod
    def _behavior_invalid(data, rule_class, diagnostics):
        """``ask`` with an active behavior package that does not compile (M01 exit table, row 2)."""
        data.update(result_kind='BLOCKED', reason='BEHAVIOR_PACKAGE_INVALID', rule_class=rule_class,
                    diagnostics=diagnostics)
        return response('BLOCKED', data, 'CONFIG_INVALID',
                        'The active behavior package or statechart failed validation.',
                        'Correct the fields named in data.diagnostics (see `quati doctor`); no work was accepted.',
                        [f"{item['code']} {item['reason']} at {item['path']}" for item in diagnostics])

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

    def _record(self, text, context, code, result, extra=None):
        # Prepare metadata before hashing; only an acknowledged receipt advances the projection.
        prepared = None
        if self.conversation is not None:
            prepared, result = self.conversation.prepare(context, result)
        # ``proof_tier`` is null: proof tiers classify tests, and a product receipt proves none (LOG-0044 X8).
        record = {'request_id': context.request_id, 'trace_id': context.trace_id,
                  'principal_hash': hashlib.sha256(context.actor_id.encode()).hexdigest(),
                  'request_hash': hashlib.sha256(text.encode()).hexdigest(),
                  'output_hash': hashlib.sha256(canonical_bytes(result)).hexdigest(),
                  'status': result['status'], 'result_kind': result['data'].get('result_kind'),
                  'policy_version': self._policy_version(context),
                  'proof_tier': None, 'provider_used': False, 'cost_usd': None, **(extra or {})}
        try:
            receipt = self.evidence_sink(record)
            result['evidence_refs'] = [f"sha256:{receipt['sha256']}:{receipt['path']}"]
            if prepared is not None:
                self.conversation.commit(context, expected_revision=prepared.revision - 1, candidate=prepared)
        finally:
            if self.conversation is not None:
                self.conversation.discard()
        return code, result

    def _policy_version(self, context):
        """The policy version in force for the tenant, as the trusted loader reports it: the adopted
        policy, or the kernel baseline when none is adopted - the value a policy decision of this request
        carries. None when it cannot be determined (no loader, or the loader failed)."""
        if self.policy_loader is None:
            return None
        try:
            version = self.policy_loader(context.tenant_id).policy_version
        except Exception:  # noqa: BLE001 - an unreadable policy is recorded as "not determined", never guessed
            return None
        return version if isinstance(version, str) else None


def _config_checks(identity, policy, provider, behavior):
    """M01 ``ConfigValidation.checks``: OK, NOT_CONFIGURED (absent) or INVALID (present but rejected)."""
    def check(name, status, reasons=()):
        return {'name': name, 'status': status, 'reasons': list(reasons)}

    if identity.get('initialized'):
        checks = [check('identity', 'OK')]
    elif identity.get('status') == 'INVALID':  # present but rejected (M02 reason and its detail)
        checks = [check('identity', 'INVALID', [identity['reason'], identity['detail']])]
    else:
        checks = [check('identity', 'NOT_CONFIGURED', ['identity_not_initialized'])]
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
    if identity.get('status') == 'INVALID':
        warnings.append(f"identity_invalid:{identity['reason']}")
        if str(identity['detail']).endswith('_mode'):
            warnings.append('config_mode_too_open')
    elif not identity.get('initialized'):
        warnings.append('identity_not_initialized')
    if policy['status'] != 'AVAILABLE':
        warnings.append(f"policy_unavailable:{policy['reason']}")
        if 'wrong_mode' in str(policy['reason']) and 'config_mode_too_open' not in warnings:
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
