"""Shared CLI rendering and failure mapping for one-shot commands and chat turns (M01 exit table)."""
from pathlib import Path

from quati.adapters.evidence import ReceiptNotWritten, redact
from quati.adapters.private_fs import UnsafeStatePath, data_root
from quati.application.cli_service import response
from quati.application.identity import AccessDenied
from quati.domain.canonical import canonical_bytes
from quati.domain.capability_registry import Refusal
from quati.domain.diagnostics import LOCAL_STORE_REASONS, settled_exit  # noqa: F401 - the shared exit rule


# M01 exit table rows 4 and 5: UNAVAILABLE caused by the local stores (the audit log, the data
# directory) is "not caused by a provider" and exits 4; only a model or tool provider failure exits 5.
# The rule itself (``LOCAL_STORE_REASONS``, ``settled_exit``) is shared with the use cases.


def exit_code(value):
    """M01 "Exit codes (stable)": the exit code of one Response."""
    if value['status'] in ('SUCCEEDED', 'PARTIAL'):
        return 0
    code = (value.get('error') or {}).get('code')
    if code == 'INTERNAL_ERROR':
        return 1
    if code in ('INVALID_INPUT', 'CONFIG_INVALID'):
        return 2
    if code == 'NOT_CONFIGURED':
        return 3
    if code in ('TEMPORARILY_UNAVAILABLE', 'DEADLINE_EXCEEDED', 'OUTPUT_INVALID'):
        return settled_exit(5, value)
    return 4


def _component(exc):
    """The unsafe directory relative to the data directory (never an absolute path), or None outside it."""
    try:
        relative = Path(exc.filename).relative_to(data_root())
    except (TypeError, ValueError):
        return None
    return relative.as_posix() if relative.parts else 'data_dir'


def render(value):
    """One line of quati-json/1 (sorted keys, ``,``/``:``, ASCII escapes, no NaN) holding one Response."""
    return canonical_bytes(redact(value)).decode('ascii')


def failure(exc):
    """Map an exception raised by a use case to (exit code, Response, stderr diagnostic or None)."""
    if isinstance(exc, AccessDenied):
        return 4, response('DENIED', code=exc.code, message='Local identity or authorization could not be verified.',
                           next_action='Run quati init or repair the owner-only local credential.'), None
    if isinstance(exc, ReceiptNotWritten):  # after the use case acted: say what may have been committed
        diagnostic = 'quati: the evidence receipt could not be written; the operation itself may have taken effect.'
        return 1, response('BLOCKED', {'reason': 'receipt_not_written', 'operation_may_have_taken_effect': True},
                           'INTERNAL_ERROR', 'The evidence receipt of this operation could not be written.',
                           'The operation may already have taken effect: inspect the current state (for example '
                           '`quati capabilities list`) before retrying, and check the data directory.'), diagnostic
    if isinstance(exc, UnsafeStatePath):  # verified before any read or change (LOG-0041 N1)
        value = response('UNAVAILABLE', {'reason': 'state_dir_unsafe', 'component': _component(exc)},
                         'TEMPORARILY_UNAVAILABLE',
                         'A Quati data directory is not a private directory of this user; nothing was read or changed.',
                         'Make the data directory and the Quati directories under it real directories owned by '
                         'you (no symlink, mode 0700), then retry.')
        return exit_code(value), value, None
    if isinstance(exc, Refusal):  # a typed registry or store refusal (for example ``audit_unavailable``)
        value = response(exc.status, {'reason': exc.reason}, exc.code, exc.message,
                         'No work was accepted or changed; resolve the reported reason and retry.')
        return exit_code(value), value, None
    diagnostic = f'quati: internal error ({type(exc).__name__}); no work was accepted.'
    if isinstance(exc, (ValueError, OSError)):  # M01: INTERNAL_ERROR always exits 1
        return 1, response('BLOCKED', code='INTERNAL_ERROR', message='A local resource could not be read or saved.',
                           next_action='Check local configuration and file permissions; no work was accepted.'), diagnostic
    # last resort (M01 exit 1): only the exception class name is ever shown
    return 1, response('BLOCKED', code='INTERNAL_ERROR', message='An unexpected internal error occurred.',
                       next_action='Retry; if it persists, report the error class shown on stderr.'), diagnostic
