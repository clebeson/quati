"""Shared CLI rendering and failure mapping for one-shot commands and chat turns (M01 exit table)."""
from quati.adapters.evidence import redact
from quati.application.cli_service import response
from quati.application.identity import AccessDenied
from quati.domain.canonical import canonical_bytes
from quati.domain.capability_registry import Refusal


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
        return 5
    return 4


def render(value):
    """One line of quati-json/1 (sorted keys, ``,``/``:``, ASCII escapes, no NaN) holding one Response."""
    return canonical_bytes(redact(value)).decode('ascii')


def failure(exc):
    """Map an exception raised by a use case to (exit code, Response, stderr diagnostic or None)."""
    if isinstance(exc, AccessDenied):
        return 4, response('DENIED', code=exc.code, message='Local identity or authorization could not be verified.',
                           next_action='Run quati init or repair the owner-only local credential.'), None
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
