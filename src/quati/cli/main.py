"""Typer presentation boundary; no durable work or provider qualification is implied."""
import os
import sys

import typer

from quati.adapters import private_fs, runtime_facts
from quati.adapters.capability_store import FileRegistryStore, default_registry_root
from quati.adapters.evidence import receipt_sink, receipts_directory
from quati.adapters.feature_reports import FileFeatureReportStore
from quati.adapters.local_identity import LocalIdentity
from quati.adapters.trace_store import ReceiptReader
from quati.application.behavior_commands import BehaviorCommands, active_package_status
from quati.application.cli_service import CLIService, config_diagnostics, response
from quati.application.ports import ProviderConfig
from quati.application.trace_commands import TraceCommands
from quati.cli import composition, local_policy
from quati.cli.chat import run_chat
from quati.application.conversation import ConversationSession
from quati.cli.rendering import failure, render, settled_exit

app = typer.Typer(no_args_is_help=False, add_completion=False, pretty_exceptions_enable=False,
                  help='Quati local CLI. This delivery supports init, doctor, config validate, ask, chat, '
                       'models probe, behavior validate/render, the capability registry commands and safe '
                       'local greetings. Commands of later slices are listed and answer UNSUPPORTED.')
models = typer.Typer(no_args_is_help=True, add_completion=False, help='Model provider commands.')
app.add_typer(models, name='models')
approvals = typer.Typer(no_args_is_help=True, add_completion=False, help='Approval requests (slice S02).')
app.add_typer(approvals, name='approvals')
capabilities = typer.Typer(no_args_is_help=True, add_completion=False,
                           help='Operator capability registry commands (synthetic fixtures in S00).')
app.add_typer(capabilities, name='capabilities')
behavior = typer.Typer(no_args_is_help=True, add_completion=False,
                       help='Behavior package compiler (validate and render in S00; lifecycle in slice S03).')
app.add_typer(behavior, name='behavior')
config = typer.Typer(no_args_is_help=True, add_completion=False,
                     help='Configuration checks (validate in S00; profile changes in slice S03).')
app.add_typer(config, name='config')
trace = typer.Typer(no_args_is_help=True, add_completion=False, help='Audit trace commands (show and explain in S00; export and replay in slice S02).')
app.add_typer(trace, name='trace')
worker = typer.Typer(no_args_is_help=True, add_completion=False, help='Ledger worker commands (slice S02).')
app.add_typer(worker, name='worker')
# Command groups that other PRDs name (M02, M25, M13, M12, M11, M20, RFC-013): registered, not delivered yet.
LATER_GROUPS = {'spaces': ('S02', 'Space and grant inspection', ('describe',)),
                'policy': ('S02', 'Trusted policy changes', ('show', 'diff', 'edit', 'apply')),
                'prefs': ('S03', 'Preferences', ('show', 'set', 'expire', 'history', 'rollback')),
                'artifact': ('S03', 'Artifacts', ('register', 'show', 'revise', 'history')),
                'memory': ('S03', 'Memory queries', ('search',)),
                'brains': ('S04', 'Knowledge providers', ('reindex',)),
                'grants': ('S05', 'Space grants of the SERVER profile', ('list',))}
# An undelivered command accepts any arguments and options: its only answer is the typed UNSUPPORTED.
ANY_ARGUMENTS = {'allow_extra_args': True, 'ignore_unknown_options': True}


def _config():
    """Provider configuration from the environment (the only production source)."""
    return ProviderConfig.from_environment()


def _state(*names):
    """LOG-0041 N1: the data directory and the named directories under it are private, or UnsafeStatePath.

    Each directory is verified by the one function its writer uses, so a command and its store agree.
    ``capabilities`` is the registry store as far as it is verified before an authorization decision
    (directories and the fixed files, LOG-0044 X1/X2) and ``capability_packages`` its stored packages;
    ``audit_log`` is the registry audit log (a Refusal ``audit_unavailable``; creates nothing);
    ``<name>:read`` verifies as a reader, which creates and modifies nothing."""
    for name in names:
        if name == 'receipts':
            receipts_directory()
        elif name == 'capabilities':
            FileRegistryStore(default_registry_root()).prepare()
        elif name == 'capability_packages':
            FileRegistryStore(default_registry_root()).verify_packages()
        elif name == 'audit_log':
            FileRegistryStore(default_registry_root()).verify_audit()
        elif name.endswith(':read'):
            private_fs.state_directory(name.removesuffix(':read'), create=False, tighten=False)
        else:
            private_fs.state_directory(name)


def _service(config=None, *, conversation=None):
    identity = LocalIdentity()
    return CLIService(identity, config or _config(), receipt_sink, conversation=conversation,
                      authorize=composition.registry_authorizer(identity), state_guard=_state,
                      identity_inspector=lambda: runtime_facts.identity_state(identity.directory),
                      policy_loader=lambda tenant_id: local_policy.state(identity.directory, tenant_id),
                      policy_installer=lambda summary: local_policy.install(
                          identity.directory, summary['tenant_id'], summary['principal_id']),
                      feature_reports=FileFeatureReportStore(),
                      ask_runtime=lambda context: composition.ask_runtime(identity, context),
                      behavior_check=lambda: active_package_status(
                          composition.REPOSITORY_ROOT, composition.BEHAVIOR_PROFILE, composition.MODEL_ROLE_REF),
                      runtime_facts=lambda: runtime_facts.collect(identity.directory))


def _commands(*written):
    """Capability commands for the authenticated operator; the directories the command uses are verified
    before it reads or changes anything, so no registry change is committed without its receipt directory."""
    commands = composition.capability_commands(LocalIdentity(), receipt_sink)
    commands.registry.store.prepare()
    _state(*written)
    return commands


def _trace():
    """Trace use case: authenticated context and the registry enforcement point of the capability commands."""
    commands = _commands()
    return TraceCommands(context=commands.context, authorize=commands.discovery.authorize,
                         receipts=ReceiptReader(), audit_events=commands.registry.store.audit_events)


def _emit(result):
    code, value = result
    typer.echo(render(value))
    raise typer.Exit(settled_exit(code, value))


def _undelivered(group, name, label, slice_id):
    """Register ``name`` as a command of a later slice: any syntax returns the typed UNSUPPORTED (M01-FR-01)."""
    @group.command(name, context_settings=ANY_ARGUMENTS,
                   help=f'Delivered in slice {slice_id}; returns UNSUPPORTED before then.')
    def command(arguments: list[str] = typer.Argument(None),
                json_output: bool = typer.Option(False, '--json')):
        _emit(_service().unsupported(label))
    return command


@app.command('init')
def initialize(json_output: bool = typer.Option(False, '--json', help='Return the stable JSON envelope.'),
               profile: str = typer.Option('local', '--profile')):
    """Explicitly initialize a private LOCAL identity; no provider call is made."""
    if profile != 'local':
        raise typer.BadParameter('This delivery supports only the local profile.')
    _emit(_service().initialize())


@app.command()
def doctor(json_output: bool = typer.Option(False, '--json'), probe: bool = False):
    """Report local configuration separately from measured provider support."""
    _emit(_service().doctor(probe))


@app.command()
def ask(text: str, json_output: bool = typer.Option(False, '--json'),
        synthetic_evidence: bool = typer.Option(False, '--synthetic-evidence',
                                                help='Record the full model trajectory in the receipt '
                                                     '(synthetic evaluations only).'),
        eval_permutation_seed: int = typer.Option(None, '--eval-candidate-permutation-seed', hidden=True)):
    """Greet deterministically or route work through a probed model and the discovery tools."""
    service = _service()
    if eval_permutation_seed is not None:
        # Evaluator-only (EVAL-PERM): permutes the order of search candidates shown to the model. The use
        # case owns the rule that the seed needs --synthetic-evidence (one check, LOG-0044 X16).
        _emit(service.ask(text, synthetic_evidence=synthetic_evidence, eval_permutation_seed=eval_permutation_seed))
    _emit(service.ask(text, synthetic_evidence=True) if synthetic_evidence else service.ask(text))


@app.command()
def chat(jsonl: bool = typer.Option(False, '--jsonl', help='Print exactly one JSON Response per input line.')):
    """Line-based terminal session: each line is one turn through the one-shot use cases."""
    conversation = ConversationSession(ids=composition.random_ids)
    raise typer.Exit(run_chat(lambda: _service(conversation=conversation), sys.stdin.buffer, sys.stdout, sys.stderr,
                              jsonl=jsonl, interactive=sys.stdin.isatty()))


@app.command()
def status(commitment_id: str, json_output: bool = typer.Option(False, '--json')):
    """Read a commitment (slice S02; returns UNSUPPORTED before then)."""
    _emit(_service().unsupported('status'))


@app.command()
def tell(commitment_id: str, text: str, json_output: bool = typer.Option(False, '--json')):
    """Add context to a commitment (slice S02; returns UNSUPPORTED before then)."""
    _emit(_service().unsupported('tell'))


@approvals.command('list')
def approvals_list(state: str = typer.Option(None, '--state'), json_output: bool = typer.Option(False, '--json')):
    """List approval requests (slice S02; returns UNSUPPORTED before then)."""
    _emit(_service().unsupported('approvals'))


@app.command()
def approve(approval_request_id: str, json_output: bool = typer.Option(False, '--json')):
    """Approve a request (slice S02; returns UNSUPPORTED before then)."""
    _emit(_service().unsupported('approve'))


@app.command()
def deny(approval_request_id: str, reason: str = typer.Option(None, '--reason'),
         json_output: bool = typer.Option(False, '--json')):
    """Deny a request (slice S02; returns UNSUPPORTED before then)."""
    _emit(_service().unsupported('deny'))


for _name in ('inbox', 'messages'):
    _undelivered(app, _name, _name, 'S02')
for _name in ('server', 'login'):
    _undelivered(app, _name, _name, 'S05')
_undelivered(approvals, 'revoke', 'approvals revoke', 'S02')
for _group, (_slice, _help, _names) in LATER_GROUPS.items():
    _typer = typer.Typer(no_args_is_help=True, add_completion=False, help=f'{_help} (slice {_slice}).')
    app.add_typer(_typer, name=_group)
    for _name in _names:
        _undelivered(_typer, _name, f'{_group} {_name}', _slice)
for _name in ('run', 'tick', 'install', 'uninstall'):
    _undelivered(worker, _name, f'worker {_name}', 'S02')
for _name in ('export', 'replay'):
    _undelivered(trace, _name, f'trace {_name}', 'S02')
for _name in ('diff', 'simulate', 'propose', 'apply', 'rollback'):
    _undelivered(config, _name, f'config {_name}', 'S03')
for _name in ('propose', 'simulate', 'diff', 'promote', 'rollback'):
    _undelivered(behavior, _name, f'behavior {_name}', 'S03')


@trace.command('show')
def trace_show(identifier: str = typer.Argument(None), request: str = typer.Option(None, '--request'),
               json_output: bool = typer.Option(False, '--json')):
    """Show the recorded receipt and decisions of one request (REQUEST_ID or TRACE_ID); read-only."""
    if (identifier is None) == (request is None):
        _emit((2, response('DENIED', code='INVALID_INPUT',
                           message='Give exactly one identifier: REQUEST_ID or TRACE_ID, or --request REQUEST_ID.',
                           next_action='Use the request_id or trace_id printed by `quati ask --json`.')))
    _emit(_trace().show(identifier if request is None else request))


@trace.command('explain')
def trace_explain(identifier: str, json_output: bool = typer.Option(False, '--json')):
    """Explain the capability selection of one request from its recorded data; no model call."""
    _emit(_trace().explain(identifier))


@config.command('validate')
def config_validate(file: str = typer.Argument(None), json_output: bool = typer.Option(False, '--json')):
    """Check the local configuration (identity, policy, provider, behavior package); changes nothing."""
    _emit(_service().config_validate(file))


@behavior.command('validate')
def behavior_validate(package: str, root: str = typer.Option(None, '--root', help='Package root (default: .).'),
                      json_output: bool = typer.Option(False, '--json')):
    """Compile a behavior package and its statechart; print the deterministic receipt or the diagnostics."""
    _emit(BehaviorCommands(LocalIdentity()).validate(package, root or os.getcwd()))


@behavior.command('render')
def behavior_render(package: str, root: str = typer.Option(None, '--root', help='Package root (default: .).'),
                    json_output: bool = typer.Option(False, '--json')):
    """Compile a behavior package and print its English prompt preview with the build receipt."""
    _emit(BehaviorCommands(LocalIdentity()).render(package, root or os.getcwd()))


@models.command('probe')
def models_probe(json_output: bool = typer.Option(False, '--json')):
    """Measure the configured provider with live calls; needs QUATI_ALLOW_LIVE=1."""
    _emit(_service().probe())


@capabilities.command('install')
def capabilities_install(path: str, fixture_handler: str = typer.Option(None, '--fixture-handler'),
                         enable_fixture: bool = typer.Option(False, '--enable-fixture'),
                         json_output: bool = typer.Option(False, '--json')):
    """Install a capability package; with a fixture handler and --enable-fixture it is activated."""
    _emit(_commands('receipts').install(path, fixture_handler=fixture_handler, enable_fixture=enable_fixture))


@capabilities.command('install-fixture')
def capabilities_install_fixture(name: str, enable_fixture: bool = typer.Option(False, '--enable-fixture'),
                                 json_output: bool = typer.Option(False, '--json')):
    """Install one built-in public synthetic fixture capability by name."""
    _emit(_commands('receipts', 'fixture_sources').install_fixture(name, enable_fixture=enable_fixture))


@capabilities.command('list')
def capabilities_list(enabled: bool = typer.Option(False, '--enabled'),
                      json_output: bool = typer.Option(False, '--json')):
    """List installed capabilities and their lifecycle."""
    _emit(_commands().list(enabled_only=enabled))


@capabilities.command('search')
def capabilities_search(query: str, json_output: bool = typer.Option(False, '--json')):
    """Search permitted capabilities exactly as the model's quati_search does."""
    _emit(_commands().search(query))


@capabilities.command('describe')
def capabilities_describe(capability_id: str, json_output: bool = typer.Option(False, '--json')):
    """Describe one ENABLED capability."""
    _emit(_commands().describe(capability_id))


@capabilities.command('disable')
def capabilities_disable(ref: str, json_output: bool = typer.Option(False, '--json')):
    """Disable an installed capability version (CAPABILITY_ID@VERSION)."""
    _emit(_commands('receipts').disable(ref))


def main(argv=None):
    try:
        return app(args=argv if argv is not None else sys.argv[1:], standalone_mode=False)
    except typer.Exit as exc:
        return exc.exit_code
    except typer.TyperException:
        code, value = 2, response('DENIED', code='INVALID_INPUT', message='Invalid CLI arguments; use --help for syntax.',
                                  next_action='Correct the CLI arguments.')
    except Exception as exc:  # noqa: BLE001 - mapped by the M01 exit table in quati.cli.rendering.failure
        code, value, diagnostic = failure(exc)
        if diagnostic:
            typer.echo(diagnostic, err=True)
    typer.echo(render(value))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
