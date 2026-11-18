"""``quati chat``: line-based read-dispatch-print loop (M01-FR-04, M01-AT-03, M01-RT-03).

Presentation only. Each input line is classified from its first character before any use-case,
model, tool or ledger call; nothing the session prints is ever parsed again. A turn calls the
same application function as its one-shot command, through a service built per turn exactly as
a one-shot invocation builds it. The loop keeps no history or business state. S01 composition passes an application-owned
process-only conversation projection into those use cases; the loop never interprets it.

Session exit rule (docs/prds/M01.md, Chat session rules 7 and 8): end of input or ``/quit`` -> 0;
a failed turn is reported in its own Response and the loop continues; a line over
``cli.max_text_bytes``, a non-UTF-8 line or (fail-closed, M01 is silent) a line holding a NUL
byte -> ``INVALID_INPUT`` Response, then exit 2; an identity failure -> its Response, then exit 4;
an internal error -> its Response, then exit 1; SIGINT -> exit 130 with nothing printed.
"""
import re

import typer

from quati.application.cli_service import MAX_TEXT_BYTES, response
from quati.cli.rendering import failure, render

MAX_LINE_BYTES = MAX_TEXT_BYTES  # M01 cli.max_text_bytes: the limit for one chat input line
PROMPT = 'quati> '
HELP_ROWS = (
    ('', 'none: empty or only spaces and tabs; no turn and no output', 'S00'),
    ('TEXT', 'quati ask TEXT (the whole line is TEXT)', 'S00'),
    ('/status COMMITMENT_ID', 'quati status COMMITMENT_ID', 'S02'),
    ('/tell COMMITMENT_ID TEXT', 'quati tell COMMITMENT_ID TEXT', 'S02'),
    ('/approvals [STATE]', 'quati approvals list [--state STATE]', 'S02'),
    ('/approve APPROVAL_REQUEST_ID', 'quati approve APPROVAL_REQUEST_ID', 'S02'),
    ('/deny APPROVAL_REQUEST_ID [REASON]', 'quati deny APPROVAL_REQUEST_ID [--reason REASON]', 'S02'),
    ('/help', 'none: lists these commands', 'S00'),
    ('/quit', 'none: ends the session with exit 0', 'S00'),
    ('/OTHER', 'none: INVALID_INPUT chat_unknown_command or chat_bad_arguments', 'S00'),
)
# Argument-count rule per command word: (minimum, maximum or None when the rest is free text).
ARITY = {'status': (1, 1), 'tell': (2, None), 'approvals': (0, 1), 'approve': (1, 1), 'deny': (1, None),
         'help': (0, 0), 'quit': (0, 0)}
DELIVERED_IN_S02 = {'status', 'tell', 'approvals', 'approve', 'deny'}
COMMAND = re.compile(r'/([^ \t]*)(.*)', re.DOTALL)


def _invalid(reason, message, next_action):
    return response('DENIED', {'reason': reason}, 'INVALID_INPUT', message, next_action)


def _decode(raw):
    """Frame one raw line; return (text or None, Response or None, session exit or None)."""
    content = raw[:-2] if raw.endswith(b'\r\n') else raw[:-1] if raw.endswith(b'\n') else raw
    if len(content) > MAX_LINE_BYTES:
        return None, _invalid('chat_line_too_long', f'A chat line must not exceed {MAX_LINE_BYTES} bytes.',
                              'Shorten the line; the session ended because line framing cannot be trusted.'), 2
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        return None, _invalid('chat_invalid_utf8', 'A chat line must be valid UTF-8.',
                              'Send UTF-8 text; the session ended because line framing cannot be trusted.'), 2
    if '\x00' in text:
        return None, _invalid('chat_nul_byte', 'A chat line must not contain a NUL byte.',
                              'Remove the NUL byte; the session ended because the input cannot be trusted.'), 2
    return text, None, None


def _command(line, service_factory):
    """Dispatch one ``/`` line; return (Response, session exit or None)."""
    word, rest = COMMAND.fullmatch(line).groups()
    if word not in ARITY:
        return _invalid('chat_unknown_command', 'Unknown chat command.', 'Type /help to list the chat commands.'), None
    rest = rest.strip(' \t')
    count = len(re.split(r'[ \t]+', rest)) if rest else 0
    low, high = ARITY[word]
    if count < low or (high is not None and count > high):
        return _invalid('chat_bad_arguments', f'Wrong arguments for /{word}.',
                        'Type /help to see the arguments of each chat command.'), None
    if word == 'help':
        return response(data={'commands': [{'input': row, 'equivalent': equivalent, 'first_slice': first}
                                           for row, equivalent, first in HELP_ROWS]}), None
    if word == 'quit':
        return response(data={'result_kind': 'SESSION_ENDED'}), 0
    return service_factory().unsupported(word)[1], None


def _turn(line, service_factory, stderr):
    """Run one non-blank turn; return (Response, session exit or None)."""
    try:
        if line.startswith('/'):
            return _command(line, service_factory)
        return service_factory().ask(line)[1], None
    except Exception as exc:  # the use case failed: report it in this turn, then end the session
        code, value, diagnostic = failure(exc)
        if diagnostic:
            typer.echo(diagnostic, file=stderr)
        return value, code


def run_chat(service_factory, stdin, stdout, stderr, *, jsonl, interactive):
    """Read binary lines from ``stdin`` until end of input, ``/quit`` or a session-ending turn."""
    try:
        while True:
            if interactive and not jsonl:
                typer.echo(PROMPT, file=stderr, nl=False)
            raw = stdin.readline(MAX_LINE_BYTES + 3)
            if not raw:
                return 0
            line, value, end = _decode(raw)
            if value is None:
                if not line.strip(' \t'):
                    continue
                value, end = _turn(line, service_factory, stderr)
            typer.echo(render(value), file=stdout)
            stdout.flush()
            if end is not None:
                return end
    except KeyboardInterrupt:
        return 130
