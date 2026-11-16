"""Local index of measured FeatureReports (M17), one pointer per provider config hash.

A pointer names the sealed evidence receipt written by ``quati models probe``; the ask use
case re-reads and re-hashes that receipt before it trusts any measured feature. The pointer
itself is not evidence: a pointer whose receipt is missing or altered proves nothing.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from quati.behavior.fsutil import atomic_write

_HASH = re.compile(r"[0-9a-f]{64}")


def default_feature_report_root() -> Path:
    return Path(os.environ.get("QUATI_DATA_DIR", str(Path.home() / ".quati"))) / "feature_reports"


class FileFeatureReportStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_feature_report_root()

    def _path(self, config_hash: str) -> Path | None:
        return self.root / f"{config_hash}.json" if isinstance(config_hash, str) and _HASH.fullmatch(
            config_hash) else None

    def save(self, report: dict, receipt: dict) -> None:
        """Newest measurement wins for its config hash; the receipt digest binds the pointer."""
        path = self._path(report.get("config_hash"))
        if path is None:
            return
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        pointer = {"config_hash": report["config_hash"], "transport": report["transport"],
                   "measured_at": report["measured_at"], "receipt_path": receipt["path"],
                   "receipt_sha256": receipt["sha256"]}
        atomic_write(path, (json.dumps(pointer, sort_keys=True) + "\n").encode())

    def load(self, config_hash: str) -> dict | None:
        """The stored report and its reference, or None when absent, unreadable or altered."""
        path = self._path(config_hash)
        try:
            pointer = json.loads(path.read_bytes())
            raw = Path(pointer["receipt_path"]).read_bytes()
        except (AttributeError, OSError, ValueError, KeyError, TypeError):
            return None
        from hashlib import sha256
        if sha256(raw).hexdigest() != pointer.get("receipt_sha256"):
            return None
        try:
            report = json.loads(raw)
        except ValueError:
            return None
        if not isinstance(report, dict):
            return None
        return {"report": report, "ref": f"sha256:{pointer['receipt_sha256']}:{pointer['receipt_path']}"}


__all__ = ["FileFeatureReportStore", "default_feature_report_root"]
