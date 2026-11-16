"""Typer presentation boundary; no durable work or provider qualification is implied."""
import os
import sys

import typer

from quati.adapters import runtime_facts
from quati.adapters.evidence import write_receipt
from quati.adapters.feature_reports import FileFeatureReportStore
from quati.adapters.local_identity import LocalIdentity
from quati.application.behavior_commands import BehaviorCommands, active_package_status
from quati.application.cli_service import CLIService, config_diagnostics, response
from quati.application.ports import ProviderConfig
from quati.cli import composition, local_policy
from quati.cli.chat import run_chat
from quati.cli.rendering import failure, render

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
trace = typer.Typer(no_args_is_help=True, add_completion=False, help='Audit trace commands (slice S02).')
app.add_typer(trace, name='trace')
worker = typer.Typer(no_args_is_help=True, add_completion=False, help='Ledger worker commands (slice S02).')
app.add_typer(worker, name='worker')
# An undelivered command accepts any arguments and options: its only answer is the typed UNSUPPORTED.
ANY_ARGUMENTS = {'allow_extra_args': True, 'ignore_unknown_options': True}


def _config():
    """Provider configuration from the environment (the only production source)."""
    return ProviderConfig.from_environment()


def _service(config=None):
    identity = LocalIdentity()
    return CLIService(identity, config or _config(), write_receipt,
                      policy_loader=lambda tenant_id: local_policy.state(identity.directory, tenant_id),
                      policy_installer=lambda summary: local_policy.install(
                          identity.directory, summary['tenant_id'], summary['principal_id']),
                      feature_reports=FileFeatureReportStore(),
                      ask_runtime=lambda context: composition.ask_runtime(identity, context),
                      behavior_check=lambda: active_package_status(
                          composition.REPOSITORY_ROOT, composition.BEHAVIOR_PROFILE, composition.MODEL_ROLE_REF),
                      runtime_facts=lambda: runtime_facts.collect(identity.directory))


def _commands():
    return composition.capability_commands(LocalIdentity(), write_receipt)


def _emit(result):
    code, value = result
    typer.echo(render(value))
    raise typer.Exit(code)


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
    if eval_permutation_seed is not None:
        # Evaluator-only (EVAL-PERM): permutes the order of search candidates shown to the model.
        if not synthetic_evidence:
            _emit((2, response('DENIED', code='INVALID_INPUT',
                               message='--eval-candidate-permutation-seed requires --synthetic-evidence.',
                               next_action='Add --synthetic-evidence (synthetic evaluations only) or drop the seed.')))
        _emit(_service().ask(text, synthetic_evidence=True, eval_permutation_seed=eval_permutation_seed))
    service = _service()
    _emit(service.ask(text, synthetic_evidence=True) if synthetic_evidence else service.ask(text))


@app.command()
def chat(jsonl: bool = typer.Option(False, '--jsonl', help='Print exactly one JSON Response per input line.')):
    """Line-based terminal session: each line is one turn through the one-shot use cases."""
    raise typer.Exit(run_chat(lambda: _service(), sys.stdin.buffer, sys.stdout, sys.stderr,
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
for _name in ('run', 'tick', 'install', 'uninstall'):
    _undelivered(worker, _name, f'worker {_name}', 'S02')
for _name in ('show', 'explain', 'export', 'replay'):
    _undelivered(trace, _name, f'trace {_name}', 'S02')
for _name in ('diff', 'simulate', 'propose', 'apply', 'rollback'):
    _undelivered(config, _name, f'config {_name}', 'S03')
for _name in ('propose', 'simulate', 'diff', 'promote', 'rollback'):
    _undelivered(behavior, _name, f'behavior {_name}', 'S03')


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
    _emit(_commands().install(path, fixture_handler=fixture_handler, enable_fixture=enable_fixture))


@capabilities.command('install-fixture')
def capabilities_install_fixture(name: str, enable_fixture: bool = typer.Option(False, '--enable-fixture'),
                                 json_output: bool = typer.Option(False, '--json')):
    """Install one built-in public synthetic fixture capability by name."""
    _emit(_commands().install_fixture(name, enable_fixture=enable_fixture))


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
    _emit(_commands().disable(ref))


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
