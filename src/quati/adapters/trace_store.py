"""Read-only access to the S00 request receipts for ``quati trace show|explain`` (M26, S00 form).

Receipts are the private files ``<data dir>/receipts/<name>.json`` written by
``quati.adapters.evidence.write_receipt``. The directory chain is verified before any file is
read (real owner-only directories, no symlink) and every file is read without following a
symlink; nothing is created or modified. An unsafe directory raises ``UnsafeStatePath`` (the typed
``state_dir_unsafe`` refusal of every command); a receipt file that is not a private regular file
raises ``TraceStoreUnavailable``. Either way nothing is shown. S00 has no index: a lookup scans
the directory (S02 replaces this with the ledger tables).
"""

from __future__ import annotations

import json
import os
from hashlib import sha256

from quati.adapters.private_fs import read_private, state_directory
from quati.application.trace_commands import TraceStoreUnavailable

RECEIPTS = "receipts"


class ReceiptReader:
    def find(self, identifier: str) -> list[dict]:
        """Every receipt whose ``request_id`` or ``trace_id`` equals ``identifier``.

        Each item is ``{"sha256", "ref", "record"}``: the digest of the file bytes, the evidence
        reference in the form the writer returned it, and the parsed JSON object. Sorted by file
        name. A file that is not a JSON object carries no identifier and is skipped.
        """
        directory = state_directory(RECEIPTS, create=False, tighten=False)
        if directory is None:
            return []
        found = []
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".json"):
                continue
            path = directory / name
            try:
                raw = read_private(path)
            except OSError:
                raise TraceStoreUnavailable(name) from None
            if raw is None:                 # removed between the listing and the read
                continue
            try:
                record = json.loads(raw)
            except (ValueError, RecursionError):
                continue
            if isinstance(record, dict) and identifier in (record.get("request_id"), record.get("trace_id")):
                digest = sha256(raw).hexdigest()
                found.append({"sha256": digest, "ref": f"sha256:{digest}:{path}", "record": record})
        return found


__all__ = ["ReceiptReader"]
