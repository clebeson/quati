"""M14-FR-01 manifest validation order and the RFC-015 package digest (S00-T02 scope).

Registry records, lifecycle and assurance (M14-FR-02/03) belong to later tasks.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from s00_t02_support import base_manifest, mutate
from quati.behavior.manifest import (
    MANIFEST_REASON_ORDER,
    PackageEntry,
    load_capability_package,
    package_sha256,
    scan_package_dir,
    validate_manifest,
)
from quati.domain.diagnostics import ContractViolation, ErrorCode


def _reason(manifest) -> str:
    with pytest.raises(ContractViolation) as caught:
        validate_manifest(manifest)
    assert caught.value.code is ErrorCode.INVALID_INPUT
    return caught.value.reason


def write_manifest(**overrides) -> dict:
    manifest = base_manifest()
    manifest.update(effects="write", requires_approval=True, destinations=["fs:state_dir"],
                    outcome_verification={"mode": "read_after_write"})
    manifest.update(overrides)
    return manifest


def _without(document: dict, dotted: str) -> dict:
    result = copy.deepcopy(document)
    target = result
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target[part]
    del target[parts[-1]]
    return result


MUTANTS = [
    ("unknown lifecycle field", lambda: dict(base_manifest(), lifecycle="ENABLED", assurance="C5"),
     "MANIFEST_SCHEMA_INVALID"),
    ("missing required name", lambda: _without(base_manifest(), "name"), "MANIFEST_SCHEMA_INVALID"),
    ("description too short", lambda: mutate(base_manifest(), "description", "Investigate."),
     "MANIFEST_SCHEMA_INVALID"),
    ("wrong schema version", lambda: mutate(base_manifest(), "schema_version", "scs/1.0"), "MANIFEST_SCHEMA_INVALID"),
    ("malformed nested type", lambda: mutate(base_manifest(), "output_schema.properties.status",
                                             {"type": ["string", 7]}), "MANIFEST_SCHEMA_INVALID"),
    ("non-mapping manifest", lambda: ["not", "a", "manifest"], "MANIFEST_SCHEMA_INVALID"),
    ("id without namespace", lambda: mutate(base_manifest(), "id", "research"), "ID_INVALID"),
    ("id upper case", lambda: mutate(base_manifest(), "id", "Research.Analytical"), "ID_INVALID"),
    ("id too long", lambda: mutate(base_manifest(), "id", "a." + "b" * 127), "ID_INVALID"),
    ("version two parts", lambda: mutate(base_manifest(), "version", "1.0"), "VERSION_NOT_SEMVER"),
    ("version leading zero", lambda: mutate(base_manifest(), "version", "01.0.0"), "VERSION_NOT_SEMVER"),
    ("one positive intent", lambda: mutate(base_manifest(), "intents.positive_examples", ["only one"]),
     "INTENTS_INSUFFICIENT"),
    ("no negative intent", lambda: mutate(base_manifest(), "intents.negative_examples", []), "INTENTS_INSUFFICIENT"),
    ("intents missing", lambda: _without(base_manifest(), "intents.negative_examples"), "INTENTS_INSUFFICIENT"),
    ("input schema without properties", lambda: _without(base_manifest(), "input_schema.properties"),
     "SCHEMA_NO_PROPERTIES"),
    ("output schema empty properties", lambda: mutate(base_manifest(), "output_schema.properties", {}),
     "SCHEMA_NO_PROPERTIES"),
    ("input schema not an object", lambda: mutate(base_manifest(), "input_schema.type", "array"),
     "SCHEMA_NO_PROPERTIES"),
    ("remote ref", lambda: mutate(base_manifest(), "input_schema.properties.scope",
                                  {"$ref": "http://example.invalid/x.json"}), "REMOTE_REF"),
    ("remote dynamic ref", lambda: mutate(base_manifest(), "output_schema.properties.findings",
                                          {"type": "array", "items": {"$dynamicRef": "file:///etc/x"}}), "REMOTE_REF"),
    ("relative file ref", lambda: mutate(base_manifest(), "input_schema.properties.scope", {"$ref": "other.json"}),
     "REMOTE_REF"),
    ("empty criteria", lambda: mutate(base_manifest(), "outcomes.criteria", []), "OUTCOME_CONTRACT_MISSING"),
    ("empty evaluation", lambda: mutate(base_manifest(), "evaluation", []), "OUTCOME_CONTRACT_MISSING"),
    ("write without destinations", lambda: _without(write_manifest(), "destinations"), "DESTINATIONS_MISSING"),
    ("write with empty destinations", lambda: write_manifest(destinations=[]), "DESTINATIONS_MISSING"),
    ("write without verification", lambda: _without(write_manifest(), "outcome_verification"),
     "OUTCOME_VERIFICATION_MISSING"),
    ("dangerous verification none", lambda: write_manifest(effects="dangerous",
                                                           outcome_verification={"mode": "none"}),
     "OUTCOME_VERIFICATION_MISSING"),
    ("write without approval flag", lambda: write_manifest(requires_approval=False), "APPROVAL_FLAG_INCONSISTENT"),
    ("evaluation escapes package", lambda: mutate(base_manifest(), "evaluation", ["../evals/x.jsonl"]),
     "PATH_TRAVERSAL"),
    ("evaluation absolute", lambda: mutate(base_manifest(), "evaluation", ["/etc/evals.jsonl#A"]), "PATH_TRAVERSAL"),
    # Several failures at once: the earliest reason in the table wins.
    ("unknown field and bad id", lambda: dict(mutate(base_manifest(), "id", "bad"), lifecycle="ENABLED"),
     "MANIFEST_SCHEMA_INVALID"),
    ("bad id and bad version", lambda: mutate(mutate(base_manifest(), "id", "bad"), "version", "1"), "ID_INVALID"),
    ("approval flag and destinations", lambda: _without(write_manifest(requires_approval=False), "destinations"),
     "DESTINATIONS_MISSING"),
    ("remote ref and empty criteria", lambda: mutate(
        mutate(base_manifest(), "input_schema.properties.scope", {"$ref": "https://x.invalid/s"}),
        "outcomes.criteria", []), "REMOTE_REF"),
    ("traversal and approval flag", lambda: write_manifest(requires_approval=False, evaluation=["../x"]),
     "APPROVAL_FLAG_INCONSISTENT"),
]


@pytest.mark.parametrize("label, build, reason", MUTANTS, ids=[m[0] for m in MUTANTS])
def test_m14_fr_01_manifest_validation_order(label: str, build, reason: str) -> None:
    assert _reason(build()) == reason, label


def test_m14_fr_01_valid_confusable_manifests_and_reason_table() -> None:
    first = base_manifest()
    confusable = mutate(base_manifest(), "id", "research.analytical-investigations")
    confusable["name"] = "Analytical investigations"
    assert validate_manifest(first) is None and validate_manifest(confusable) is None
    assert validate_manifest(write_manifest()) is None
    local_ref = mutate(base_manifest(), "input_schema.properties.scope", {"$ref": "#/properties/research_question"})
    assert validate_manifest(local_ref) is None
    assert MANIFEST_REASON_ORDER == (
        "MANIFEST_SCHEMA_INVALID", "ID_INVALID", "VERSION_NOT_SEMVER", "INTENTS_INSUFFICIENT",
        "SCHEMA_NO_PROPERTIES", "REMOTE_REF", "OUTCOME_CONTRACT_MISSING", "DESTINATIONS_MISSING",
        "OUTCOME_VERIFICATION_MISSING", "APPROVAL_FLAG_INCONSISTENT", "SYMLINK_IN_PACKAGE", "PATH_TRAVERSAL")
    # The manifest value is not mutated by validation.
    snapshot = json.dumps(first, sort_keys=True)
    validate_manifest(first)
    assert json.dumps(first, sort_keys=True) == snapshot


def _reference_digest(files: dict[str, bytes]) -> str:
    joined = b"".join(path.encode() + b"\0" + hashlib.sha256(data).hexdigest().encode() + b"\n"
                      for path, data in sorted(files.items(), key=lambda item: item[0].encode()))
    return hashlib.sha256(joined).hexdigest()


def _make_package(root: Path, manifest: dict | None = None) -> dict[str, bytes]:
    files = {
        "capability.scs.json": json.dumps(base_manifest() if manifest is None else manifest).encode(),
        "SKILL.md": b"---\nname: Analytical investigation\n---\n",
        "evals/seed_eri.jsonl": b'{"case": "CASE-07"}\n',
        "Z-upper.txt": b"z",
        "a-lower.txt": b"a",
    }
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return files


def test_package_digest_matches_rfc_015(tmp_path: Path) -> None:
    files = _make_package(tmp_path / "pkg")
    package = load_capability_package(tmp_path / "pkg")
    assert package.package_sha256 == _reference_digest(files)
    assert package.manifest == base_manifest()
    assert [entry.path for entry in package.entries] == sorted(files, key=str.encode)
    entries = scan_package_dir(tmp_path / "pkg")
    assert package_sha256(entries) == package.package_sha256
    assert package_sha256(list(reversed(entries))) == package.package_sha256
    # A one-byte change changes the digest.
    (tmp_path / "pkg" / "a-lower.txt").write_bytes(b"b")
    assert load_capability_package(tmp_path / "pkg").package_sha256 != package.package_sha256


def test_package_rejects_symlinks_specials_size_and_missing_manifest(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    _make_package(root)
    (root / "evals" / "link.jsonl").symlink_to(root / "SKILL.md")
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(root)
    assert (caught.value.code, caught.value.reason) == (ErrorCode.INVALID_INPUT, "SYMLINK_IN_PACKAGE")
    (root / "evals" / "link.jsonl").unlink()

    os.mkfifo(root / "pipe")
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(root)
    assert caught.value.reason == "NOT_REGULAR_FILE"
    (root / "pipe").unlink()

    total = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    load_capability_package(root, max_package_bytes=total)
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(root, max_package_bytes=total - 1)
    assert (caught.value.code, caught.value.reason) == (ErrorCode.INVALID_INPUT, "PACKAGE_TOO_LARGE")

    linked_root = tmp_path / "linked"
    linked_root.symlink_to(root)
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(linked_root)
    assert caught.value.reason == "SYMLINK_IN_PACKAGE"

    with pytest.raises(ContractViolation) as caught:
        load_capability_package(tmp_path / "absent")
    assert (caught.value.code, caught.value.reason) == (ErrorCode.NOT_FOUND, "PACKAGE_NOT_FOUND")

    (root / "capability.scs.json").unlink()
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(root)
    assert (caught.value.code, caught.value.reason) == (ErrorCode.INVALID_INPUT, "MANIFEST_MISSING")
    (root / "capability.scs.json").symlink_to(root / "SKILL.md")
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(root)
    assert caught.value.reason == "SYMLINK_IN_PACKAGE"


def test_package_manifest_reasons_precede_package_reasons(tmp_path: Path) -> None:
    root = tmp_path / "pkg"
    _make_package(root, mutate(base_manifest(), "version", "1.0"))
    (root / "link").symlink_to(root / "SKILL.md")
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(root)
    assert caught.value.reason == "VERSION_NOT_SEMVER"
    (root / "capability.scs.json").write_bytes(b'{"id": "a", "id": "b"}')
    with pytest.raises(ContractViolation) as caught:
        load_capability_package(root)
    assert (caught.value.code, caught.value.reason) == (ErrorCode.INVALID_INPUT, "DUPLICATE_KEY")


@pytest.mark.parametrize("path", ["", "a//b", "./a", "a/./b", "a\\b", "a/", "a/../b", "..", "/abs"])
def test_package_entry_paths_must_be_normalized(path: str) -> None:
    with pytest.raises(ContractViolation) as caught:
        package_sha256([PackageEntry(path, "file", b"x")])
    assert caught.value.reason == "PATH_TRAVERSAL"


def test_package_entries_are_unique_and_typed() -> None:
    with pytest.raises(ContractViolation) as caught:
        package_sha256([PackageEntry("a", "file", b"x"), PackageEntry("a", "file", b"y")])
    assert caught.value.reason == "DUPLICATE_PATH"
    with pytest.raises(ValueError):
        PackageEntry("a", "device", b"")
    assert package_sha256([]) == hashlib.sha256(b"").hexdigest()
