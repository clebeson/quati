"""MCP tool description to SCS draft manifest (M14-FR-02, REG-03).

Vendor annotations are stored as untrusted hints and never lower the enforced effect:
an imported tool is ``dangerous`` with approval required until a HUMAN review.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from quati.domain.capability_registry import CAPABILITY_ID_PATTERN, VERSION_PATTERN, Refusal

_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def _refuse(message: str) -> Refusal:
    return Refusal("BLOCKED", "INVALID_INPUT", "MCP_TOOL_INVALID", message)


def mcp_tool_manifest(tool: Mapping[str, Any], *, server: str, server_version: str,
                      intents: Mapping[str, Any]) -> tuple[dict, dict, bytes]:
    """Return (manifest, vendor_hints, raw tool bytes); intents come from the operator, not the tool."""
    if not isinstance(tool, Mapping):
        raise _refuse("the MCP tool description must be an object")
    name, description = tool.get("name"), tool.get("description")
    capability_id = f"{server}.{name}" if isinstance(name, str) and isinstance(server, str) else ""
    if not (isinstance(name, str) and _NAME.fullmatch(name) and CAPABILITY_ID_PATTERN.fullmatch(capability_id)):
        raise _refuse("the MCP server or tool name cannot form a namespaced capability id")
    if not (isinstance(server_version, str) and VERSION_PATTERN.fullmatch(server_version)):
        raise _refuse("the MCP server version is not semantic")
    schema = tool.get("inputSchema")
    if not (isinstance(schema, Mapping) and schema.get("type") == "object"):
        raise _refuse("the MCP input schema must be an object schema")
    text = description if isinstance(description, str) else ""
    manifest = {
        "schema_version": "scs/1.1", "id": capability_id, "version": server_version, "name": name,
        "description": f"Imported MCP tool {name} from server {server}. Vendor text: {text}"[:1024],
        "intents": {"positive_examples": list(intents.get("positive_examples", [])),
                    "negative_examples": list(intents.get("negative_examples", []))},
        "input_schema": {"properties": {}, **dict(schema)},
        "output_schema": {"type": "object", "properties": {"result": {"description": "untrusted MCP result"}}},
        "outcomes": {"criteria": ["The MCP tool returned a result for the requested input."]},
        "permissions": [f"mcp:{server}:{name}"], "effects": "dangerous", "requires_approval": True,
        "dependencies": [], "evaluation": ["operator review of the imported tool is required"],
        "destinations": [f"mcp:{server}"],
        "outcome_verification": {"mode": "evidence_check", "description": "unverified import"},
    }
    annotations = tool.get("annotations")
    hints = {"mcp_annotations": dict(annotations) if isinstance(annotations, Mapping) else {}}
    raw = json.dumps(dict(tool), sort_keys=True, indent=2).encode("utf-8") + b"\n"
    return manifest, hints, raw


__all__ = ["mcp_tool_manifest"]
