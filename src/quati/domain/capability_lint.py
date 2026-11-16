"""Advisory capability package lint (M14, REG-07). Findings are hints, never proof of safety.

The lint never changes lifecycle, eligibility or policy; kernel rules (K3, K8) apply
whether or not a finding exists.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

NOTICE = ("Advisory lint only: an empty finding list is not proof of safety; policy and the registry "
          "lifecycle are enforced by trusted code regardless of this report.")
STEERING = re.compile(
    r"ignore (the |all |any )?(previous |prior )?(policy|policies|instructions|rules)|enable[ds]? (the )?write"
    r"|enabled\s*=\s*true|always (choose|select|pick|use) (me|this)|pre-?approved|do not tell the user"
    r"|bypass (the )?(policy|approval)|approval_id\s*=", re.IGNORECASE)
NETWORK = re.compile(r"\b(https?|ftp|wss?)://", re.IGNORECASE)
SHELL = re.compile(r"\b(subprocess|os\.system|os\.popen|eval\(|exec\(|/bin/sh|bash -c)")
OUTSIDE_STATE = re.compile(r"(^|[\s'\"(])(/etc/|/usr/|~/|\.\./)")


def _strings(value: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for key in sorted(value):
            yield from _strings(value[key], f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")


def lint_package(manifest: Mapping[str, Any], files: Mapping[str, bytes]) -> dict:
    """Deterministic findings over the manifest text and the package file contents."""
    findings: list[dict] = []
    texts = list(_strings(dict(manifest), "manifest"))
    texts += [(path, data.decode("utf-8", "replace")) for path, data in sorted(files.items())]
    rules = (("POLICY_STEERING", STEERING), ("NETWORK_URL", NETWORK), ("SHELL_EXEC", SHELL),
             ("WRITE_OUTSIDE_STATE", OUTSIDE_STATE))
    for path, text in texts:
        for rule, pattern in rules:
            match = pattern.search(text)
            if match:
                findings.append({"rule": rule, "path": path, "excerpt": match.group(0)[:80]})
    return {"schema": "quati-capability-lint/1", "advisory": True, "notice": NOTICE, "findings": findings}


__all__ = ["NOTICE", "lint_package"]
