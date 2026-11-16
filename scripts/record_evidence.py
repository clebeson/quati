#!/usr/bin/env python3
"""Run a local command and save append-only, redacted engineering evidence."""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--evidence-dir", type=Path, default=ROOT / "evidence/runs")
    result.add_argument("--source", action="append", default=[], type=Path, help="Source file to include by SHA-256; may be repeated")
    result.add_argument("command", nargs=argparse.REMAINDER, help="Command and arguments after --")
    return result


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_metadata():
    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False).stdout.strip()
        except OSError:
            return ""
    return {"commit": git("rev-parse", "HEAD") or None, "dirty": bool(git("status", "--porcelain"))}


def default_source_files():
    source_suffixes = {".py", ".toml", ".yaml", ".yml", ".json"}
    files = [ROOT / "pyproject.toml"]
    for directory in (ROOT / "src", ROOT / "scripts", ROOT / "tests", ROOT / "spec_tools", ROOT / "contracts"):
        if directory.is_dir():
            files.extend(path for path in directory.rglob("*")
                         if path.is_file() and path.suffix in source_suffixes
                         and "__pycache__" not in path.parts)
    return sorted(files)


def scrub(data, secret):
    if secret:
        data = data.replace(secret.encode("utf-8"), b"[REDACTED]")
    return data


def safe_write(path, content):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def create_run_dir(base):
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(base, 0o700)
    while True:
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "Z-" + secrets.token_hex(4)
        path = base / name
        try:
            path.mkdir(mode=0o700)
            return path
        except FileExistsError:
            continue


def main(argv=None):
    args = parser().parse_args(argv)
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not command:
        print("A command is required after --", file=sys.stderr)
        return 2
    secret_env_name = os.environ.get("QUATI_API_KEY_ENV", "QUATI_API_KEY")
    secret = os.environ.get(secret_env_name, "") if secret_env_name else ""
    started_at = datetime.now(timezone.utc)
    start = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        exit_code = completed.returncode
        stdout = scrub(completed.stdout, secret)
        stderr = scrub(completed.stderr, secret)
    except OSError as exc:
        exit_code = 127
        stdout = b""
        stderr = scrub(str(exc).encode("utf-8", errors="replace"), secret)
    elapsed = time.monotonic() - start
    run_dir = create_run_dir(args.evidence_dir)
    safe_write(run_dir / "stdout.txt", stdout)
    safe_write(run_dir / "stderr.txt", stderr)
    source_hashes = {}
    sources = list(dict.fromkeys(default_source_files() + [source.resolve() for source in args.source]))
    for source in sources:
        resolved = source.resolve()
        try:
            source_hashes[str(resolved.relative_to(ROOT))] = sha256(resolved.read_bytes())
        except (OSError, ValueError):
            source_hashes[str(source)] = None
    manifest = {
        "schema_version": "quati-engineering-run/1",
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(elapsed, 6),
        "runtime": {"implementation": sys.implementation.name, "version": sys.version.split()[0]},
        "git": git_metadata(),
        "command": {"executable": Path(command[0]).name, "argument_count": len(command) - 1, "arguments_omitted": True},
        "exit_code": exit_code,
        "source_sha256": source_hashes,
        "stdout_sha256": sha256(stdout),
        "stderr_sha256": sha256(stderr),
    }
    safe_write(run_dir / "manifest.json", (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(f"Evidence recorded: {run_dir}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
