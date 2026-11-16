"""S00 fix round 8 (LOG-0044): unit tests of the store, ask pre-check, receipt and asset rules.

Requirements and risk boundaries discriminated (proof tier L1: real code, in-process, temp stores,
injected clock and ids, scripted fake model; nothing here is evidence of a real provider):

* X1 / X2 - M01 "Data directory" rules 1-3: ``private_fs`` refuses a symlink, FIFO, directory, hard
  link, wider mode or foreign owner with ``UnsafeStatePath`` naming the path (never a bare ``OSError``,
  never a blocking open); the registry store verifies every directory and file before a read, lock or
  write; a storage failure precedes the registry commit, and a failure that can only happen after the
  commit is the typed ``store_change_incomplete`` (``operation_may_have_taken_effect``).
* X6 / X13 - the ask and probe use cases call the state guard and the AuthorizationPort before the
  provider (M01 "Data directory" rules 2 and 4; M02 authorization order rows 4 and 7).
* X8 - a request receipt records the policy version in force; no constant, no test proof tier.
* X11 - identifier shape and hard links of the LOCAL credential (contracts/identity.schema.json).
* X15 - the asset locator rule and the asset digest (docs/architecture/PROJECT_STRUCTURE.md).
* X16 - one ``--eval-candidate-permutation-seed`` check (the use case owns it).
"""

from __future__ import annotations

import base64
import json
import os
import signal
import stat
import tomllib
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from s00_t03_support import build
from s00_t04_support import CALENDAR_QUERY, Harness, Script, classified, describe, final, invoke, search

from quati.adapters import capability_store, evidence, private_fs, runtime_facts
from quati.adapters.capability_store import FileRegistryStore
from quati.adapters.fixture_capabilities import write_fixture_package
from quati.adapters.local_identity import LocalIdentity
from quati.adapters.private_fs import UnsafeStatePath
from quati.application.behavior_commands import active_package_status
from quati.application.cli_service import CLIService
from quati.application.identity import AccessDenied, RequestContext
from quati.application.ports import ProviderConfig
from quati.behavior import contracts
from quati.behavior.manifest import scan_package_dir
from quati.cli import main as cli_main
from quati.cli import rendering
from quati.domain.capability_registry import Refusal

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FILE_FAULTS = ("fifo", "symlink", "dangling_symlink", "hard_link", "mode_644", "mode_640", "directory", "foreign")
STORE_FILES = ("registry.json", "capabilities.lock", "registry.flock",
               "packages/fixtures.calendar-read/1.0.0/capability.scs.json")


@pytest.fixture(autouse=True)
def bounded():
    """A regression that blocks on a FIFO fails the test instead of hanging the suite."""
    def expired(signum, frame):
        raise AssertionError("the call blocked (hang)")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(20)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous)


def make_unsafe(path: Path, fault: str, outside: Path, monkeypatch) -> None:
    outside.mkdir(exist_ok=True)
    if fault == "fifo":
        path.unlink()
        os.mkfifo(path, 0o600)
    elif fault == "symlink":
        path.rename(outside / "moved")
        path.symlink_to(outside / "moved")
    elif fault == "dangling_symlink":
        path.unlink()
        path.symlink_to(outside / "absent")
    elif fault == "hard_link":
        os.link(path, outside / "second-name")
    elif fault.startswith("mode_"):
        path.chmod(int(fault.removeprefix("mode_"), 8))
    elif fault == "directory":
        path.unlink()
        path.mkdir(mode=0o700)
    else:                                   # simulated: the uid this process observes for that inode
        info, real_fstat, real_lstat = os.stat(path), os.fstat, os.lstat

        class Foreign:
            def __init__(self, wrapped):
                self._wrapped = wrapped

            def __getattr__(self, name):
                return os.getuid() + 1 if name == "st_uid" else getattr(self._wrapped, name)

        def observed(found):
            return Foreign(found) if (found.st_dev, found.st_ino) == (info.st_dev, info.st_ino) else found
        monkeypatch.setattr(os, "fstat", lambda descriptor: observed(real_fstat(descriptor)))
        monkeypatch.setattr(os, "lstat", lambda target, *args, **kwargs: observed(real_lstat(target, *args, **kwargs)))


def tree(base: Path) -> dict:
    return {str(path.relative_to(base)): (path.read_bytes() if path.is_file() else None)
            for path in sorted(base.rglob("*")) if not path.is_symlink()}


# ----------------------------------------------------------------- private_fs: every private-file check
@pytest.mark.parametrize("fault", FILE_FAULTS)
def test_read_private_refuses_every_unsafe_file_with_the_typed_error_naming_the_path(tmp_path, monkeypatch, fault):
    path = tmp_path / "file.json"
    path.write_bytes(b"{}")
    path.chmod(0o600)
    make_unsafe(path, fault, tmp_path / "outside", monkeypatch)
    with pytest.raises(UnsafeStatePath) as caught:
        private_fs.read_private(path)
    assert caught.value.filename == str(path)
    for check in (private_fs.check_private_file, private_fs.check_private_path):
        with pytest.raises(UnsafeStatePath) as caught:
            check(path)
        assert caught.value.filename == str(path)


@pytest.mark.parametrize("fault", FILE_FAULTS)
def test_open_private_refuses_every_unsafe_file_and_creates_nothing_through_a_symlink(tmp_path, monkeypatch, fault):
    """A wider mode is refused, never repaired: also for a content-free lock file (LOG-0044 X2)."""
    path = tmp_path / "file.lock"
    path.write_bytes(b"")
    path.chmod(0o600)
    make_unsafe(path, fault, tmp_path / "outside", monkeypatch)
    with pytest.raises(UnsafeStatePath) as caught:
        private_fs.open_private(path, os.O_RDWR)
    assert caught.value.filename == str(path)
    assert not (tmp_path / "outside" / "absent").exists()
    if fault.startswith("mode_"):
        assert stat.S_IMODE(path.stat().st_mode) == int(fault.removeprefix("mode_"), 8)


def test_private_file_helpers_accept_a_private_file_and_an_absent_one(tmp_path):
    path = tmp_path / "file.json"
    assert private_fs.read_private(path) is None and private_fs.check_private_file(path) is None
    assert private_fs.check_private_path(path) is None
    assert private_fs.verify_entry(path) is None                    # removed meanwhile: nothing to verify
    private_fs.write_private(path, b"data")
    assert private_fs.read_private(path) == b"data" and private_fs.check_private_file(path) is None
    assert private_fs.check_private_path(path) is None
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize("mode", [0o500, 0o300, 0o600, 0o000])
def test_a_writer_refuses_a_directory_without_the_owner_bits_instead_of_widening_it(tmp_path, mode):
    """M01 rule 1: a writer removes wider bits; it never adds a permission the user removed."""
    directory = tmp_path / "data"
    directory.mkdir(mode=0o700)
    directory.chmod(mode)
    try:
        with pytest.raises(UnsafeStatePath) as caught:
            private_fs.private_directory(directory)
        assert caught.value.filename == str(directory)
        assert stat.S_IMODE(directory.stat().st_mode) == mode
    finally:
        directory.chmod(0o700)


def test_a_writer_still_removes_wider_bits_and_a_reader_accepts_a_read_only_directory(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    directory.chmod(0o777)
    private_fs.private_directory(directory)
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    directory.chmod(0o500)
    assert private_fs.private_directory(directory, tighten=False) == directory
    directory.chmod(0o700)


# ----------------------------------------------------------------- the registry store: verify before use
@pytest.fixture
def installed(tmp_path):
    harness = build(tmp_path)
    assert harness.install("calendar-read")["status"] == "SUCCEEDED"
    return harness


@pytest.mark.parametrize("fault", FILE_FAULTS)
@pytest.mark.parametrize("name", STORE_FILES)
def test_the_store_refuses_every_unsafe_file_before_anything_is_read(installed, tmp_path, monkeypatch, name, fault):
    """A fixed store file is refused by ``prepare`` (before the authorization decision, by metadata, with
    no open); a package file by ``verify_packages``, which precedes the first registry read or lock."""
    store = installed.store
    path = store.root / name
    make_unsafe(path, fault, tmp_path / "outside", monkeypatch)
    before, outside = tree(store.root), tree(tmp_path / "outside")
    opened: list = []
    real_open = os.open
    monkeypatch.setattr(os, "open", lambda target, *args, **kwargs: (
        opened.append(os.fspath(target)), real_open(target, *args, **kwargs))[1])
    fresh = FileRegistryStore(store.root)
    if name.startswith("packages/"):
        fresh.prepare()
        assert not [name for name in opened if "/packages/" in name]      # nothing below packages before a decision
        for use in (fresh.verify_packages, fresh.load, fresh.transaction().__enter__):
            with pytest.raises(UnsafeStatePath) as caught:
                use()
            assert caught.value.filename == str(path)
    else:
        with pytest.raises(UnsafeStatePath) as caught:
            fresh.prepare()
        assert caught.value.filename == str(path) and str(path) not in opened
    assert (tree(store.root), tree(tmp_path / "outside")) == (before, outside)


@pytest.mark.parametrize("fault", ["fifo", "symlink", "hard_link", "mode_644", "directory", "foreign"])
def test_each_store_read_goes_through_the_private_file_helper_on_its_own(installed, tmp_path, monkeypatch, fault):
    """Not only ``prepare``: ``load``, ``lock_entries`` and the lock itself refuse the file they open."""
    store = FileRegistryStore(installed.store.root)
    for name, call in (("registry.json", store.load), ("capabilities.lock", store.lock_entries)):
        path = store.root / name
        saved = path.read_bytes()
        make_unsafe(path, fault, tmp_path / f"outside-{name}", monkeypatch)
        with pytest.raises(UnsafeStatePath) as caught:
            call()
        assert caught.value.filename == str(path)
        monkeypatch.undo()
        if path.is_dir() and not path.is_symlink():
            path.rmdir()
        else:
            path.unlink()
        private_fs.write_private(path, saved)
    flock = store.root / "registry.flock"
    make_unsafe(flock, fault, tmp_path / "outside-flock", monkeypatch)
    with pytest.raises(UnsafeStatePath) as caught:
        with store.transaction():
            pytest.fail("the lock was taken on an unsafe lock file")
    assert caught.value.filename == str(flock)


@pytest.mark.parametrize("relative", ["packages", "staging", "packages/fixtures.calendar-read",
                                      "packages/fixtures.calendar-read/1.0.0"])
@pytest.mark.parametrize("fault", ["symlink", "file", "mode_500", "foreign"])
def test_prepare_refuses_every_unsafe_sub_directory(installed, tmp_path, monkeypatch, relative, fault):
    store = installed.store
    path, outside = store.root / relative, tmp_path / "outside"
    outside.mkdir()
    if fault == "symlink":
        path.rename(outside / "moved")
        path.symlink_to(outside / "moved", target_is_directory=True)
    elif fault == "file":                           # a private regular file where a directory belongs
        path.rename(outside / "moved")
        private_fs.write_private(path, b"not a directory")
    elif fault == "mode_500":
        path.chmod(0o500)
    else:
        make_unsafe(path, "foreign", outside, monkeypatch)
    try:
        fresh = FileRegistryStore(store.root)
        with pytest.raises(UnsafeStatePath) as caught:
            if relative in ("packages", "staging"):
                fresh.prepare()                      # before the authorization decision
            else:
                fresh.prepare()
                fresh.load()                         # before the first registry read
        assert caught.value.filename == str(path)
        if relative not in ("packages", "staging"):
            FileRegistryStore(store.root).prepare()  # a package directory is not examined before a decision
    finally:
        if fault == "mode_500":
            path.chmod(0o700)


def test_prepare_accepts_a_healthy_store_and_leaves_the_audit_log_to_its_own_check(installed):
    store = FileRegistryStore(installed.store.root)
    before = tree(store.root)
    store.prepare()
    assert store.verify_packages() is None and store.verify_audit() is None and tree(store.root) == before
    store.audit_path.chmod(0o644)
    store.prepare()                                  # the log has its own typed reason (M01 rule 4)
    with pytest.raises(Refusal) as caught:
        store.verify_audit()
    assert (caught.value.code, caught.value.reason) == ("TEMPORARILY_UNAVAILABLE", "audit_unavailable")
    store.audit_path.chmod(0o600)
    store.audit_path.write_bytes(store.audit_path.read_bytes() + b'{"event": "torn')
    with pytest.raises(Refusal) as caught:
        FileRegistryStore(store.root).verify_audit()
    assert caught.value.reason == "audit_unavailable"


def test_verify_audit_of_an_absent_store_creates_nothing(tmp_path):
    store = FileRegistryStore(tmp_path / "data" / "capabilities")
    assert store.verify_audit() is None and store.verify_packages() is None and not (tmp_path / "data").exists()
    assert store.load()["revision"] == 0 and not (tmp_path / "data").exists()


# ----------------------------------------------------------------- the commit ordering (X1)
def calendar_entries(tmp_path):
    return scan_package_dir(write_fixture_package(tmp_path / "sources-direct", "mail-search"))


@pytest.mark.parametrize("target", ["packages", "packages/fixtures.mail-search", "staging"])
@pytest.mark.parametrize("fault", ["file", "symlink"])
def test_staging_fails_before_the_commit_when_the_publish_location_is_unusable(installed, tmp_path, target, fault):
    """Everything that can fail for storage reasons fails in ``stage_package``, which precedes the
    registry commit and its audit events: revision, registry file and audit log are unchanged."""
    store = installed.store
    path, outside = store.root / target, tmp_path / "outside"
    outside.mkdir()
    if path.exists():
        (path.rmdir() if not any(path.iterdir()) else path.rename(tmp_path / "set-aside"))
    if fault == "file":
        private_fs.write_private(path, b"not a directory")
    else:
        path.symlink_to(outside, target_is_directory=True)
    registry, audit = store.registry_path.read_bytes(), store.audit_path.read_bytes()
    with pytest.raises(UnsafeStatePath) as caught:
        installed.install("mail-search")
    assert caught.value.filename == str(path)
    assert (store.registry_path.read_bytes(), store.audit_path.read_bytes()) == (registry, audit)
    assert list(outside.iterdir()) == []                         # nothing was written through the symlink
    with pytest.raises(UnsafeStatePath):
        store.stage_package(calendar_entries(tmp_path))


def test_a_publish_that_fails_after_the_commit_is_typed_and_says_what_was_committed(installed, monkeypatch):
    """A late failure cannot be ruled out (for example a full disk): the Response is truthful."""
    store = installed.store
    revision = store.load()["revision"]
    real = os.replace

    def replace(source, target, *args, **kwargs):
        if "staging" in Path(source).parts:
            raise OSError(28, "No space left on device")
        return real(source, target, *args, **kwargs)
    monkeypatch.setattr(capability_store.os, "replace", replace)
    with pytest.raises(capability_store.StoreChangeIncomplete) as caught:
        installed.install("mail-search")
    assert store.load()["revision"] == revision + 1                 # the commit DID happen
    code, value, diagnostic = rendering.failure(caught.value)
    assert code == 1 and value["error"]["code"] == "INTERNAL_ERROR" and value["status"] == "BLOCKED"
    assert value["data"] == {"reason": "store_change_incomplete", "operation_may_have_taken_effect": True}
    text = json.dumps(value).lower() + (diagnostic or "").lower()
    assert "no work was accepted" not in text and "may" in value["next_action"]
    monkeypatch.undo()
    repaired = installed.install("mail-search")                     # the documented recovery: install again
    assert repaired["status"] == "SUCCEEDED" and repaired["data"]["already_installed"] is True
    assert store.package_digest("fixtures.mail-search", "1.0.0") == repaired["data"]["package_sha256"]


def test_a_lock_entry_that_fails_after_the_commit_is_the_same_typed_late_failure(installed, monkeypatch):
    store = installed.store

    def hook(point):
        if point == "lock.before_rename":
            raise OSError(28, "No space left on device")
    store.hook = hook
    with pytest.raises(capability_store.StoreChangeIncomplete):
        installed.install("mail-search")
    assert rendering.failure(capability_store.StoreChangeIncomplete())[1]["data"]["operation_may_have_taken_effect"] is True


def test_an_audit_append_that_fails_after_the_commit_is_not_reported_as_nothing_recorded(installed):
    """The registry revision advanced; the audit events of the change could not all be appended."""
    store = installed.store
    revision = store.load()["revision"]

    def hook(point):
        if point == "registry.after_rename":
            store.audit_path.chmod(0o644)                           # the log becomes unusable after the commit
    store.hook = hook
    with pytest.raises(capability_store.StoreChangeIncomplete):
        installed.install("mail-search")
    store.audit_path.chmod(0o600)
    assert store.load()["revision"] == revision + 1


def test_an_audit_append_that_fails_before_any_commit_stays_audit_unavailable(installed):
    store = FileRegistryStore(installed.store.root)
    store.audit_path.chmod(0o644)
    with pytest.raises(Refusal) as caught:
        store.append_audit({"event": "x"})
    assert caught.value.reason == "audit_unavailable"


def test_rendering_maps_an_unsafe_file_to_its_path_relative_to_the_data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("QUATI_DATA_DIR", str(tmp_path / "data"))
    error = UnsafeStatePath(1, "x", str(tmp_path / "data" / "capabilities" / "registry.json"))
    code, value, diagnostic = rendering.failure(error)
    assert (code, diagnostic) == (4, None)
    assert value["data"] == {"reason": "state_dir_unsafe", "component": "capabilities/registry.json"}
    assert "director" in value["error"]["message"] and "file" in value["error"]["message"]


# ----------------------------------------------------------------- X6 / X13: checks before the provider
READ_SCRIPT = (classified, lambda: search("next appointment calendar"), lambda: describe("fixtures.calendar-read"),
               lambda: invoke("fixtures.calendar-read", limit=1), final)


def ready(tmp_path, monkeypatch) -> Harness:
    harness = Harness(tmp_path, monkeypatch, Script())
    harness.install("calendar-read")
    assert harness.probe()[0] == 0
    harness.script.add(*(item() for item in READ_SCRIPT))
    return harness


def test_a_work_ask_verifies_storage_then_audit_then_grant_before_the_first_model_call(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch)
    order: list = []
    real_authorize = harness.service.authorize
    harness.service.state_guard = lambda *names: order.append(("state", names))
    harness.service.authorize = lambda context, operation, action: (
        order.append(("authorize", operation, action, len(harness.script.model_requests()))),
        real_authorize(context, operation, action))[1]
    code, value = harness.ask(CALENDAR_QUERY)
    assert code == 0 and value["data"]["result_kind"] == "FIXTURE_RESULT"
    assert order == [("state", ("receipts",)), ("state", ("feature_reports:read",)),
                     ("state", ("capabilities",)), ("state", ("audit_log",)),
                     ("authorize", "ask_admission", "read", 0), ("state", ("capability_packages",))]


def test_a_greeting_checks_only_the_receipt_directory_and_no_grant(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch)
    order: list = []
    harness.service.state_guard = lambda *names: order.append(names)
    harness.service.authorize = lambda *arguments: pytest.fail("a greeting uses no registry")
    assert harness.ask("hello")[0] == 0 and order == [("receipts",)]


def test_an_unusable_audit_log_refuses_the_ask_with_a_receipt_and_no_model_call(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch)
    before = len(harness.script.model_requests())

    def guard(*names):
        if names == ("audit_log",):
            raise Refusal("UNAVAILABLE", "TEMPORARILY_UNAVAILABLE", "audit_unavailable", "unreadable")
    harness.service.state_guard = guard
    harness.service.authorize = lambda *arguments: pytest.fail("no decision can be logged")
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["error"]["code"]) == (4, "UNAVAILABLE", "TEMPORARILY_UNAVAILABLE")
    assert value["data"]["reason"] == "audit_unavailable" and value["data"]["result_kind"] == "BLOCKED"
    assert value["data"]["provider_used"] is False and len(value["evidence_refs"]) == 1
    assert len(harness.script.model_requests()) == before
    receipt = json.loads(Path(value["evidence_refs"][0].split(":", 2)[2]).read_bytes())
    assert (receipt["status"], receipt["result_kind"], receipt["provider_used"]) == ("UNAVAILABLE", "BLOCKED", False)


def test_a_denied_admission_refuses_the_ask_with_the_port_reason_and_no_model_call(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch)
    before = len(harness.script.model_requests())

    class Denied:
        code, reason = "FORBIDDEN", "NO_SPACE_GRANT"

        @staticmethod
        def to_response():
            return {"status": "DENIED", "data": {"reason": "NO_SPACE_GRANT"}, "evidence_refs": [],
                    "uncertainties": [], "next_action": "Inspect the space grant.",
                    "error": {"code": "FORBIDDEN", "message": "NO_SPACE_GRANT", "retryable": False}}
    harness.service.authorize = lambda context, operation, action: Denied()
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
        4, "DENIED", "FORBIDDEN", "NO_SPACE_GRANT")
    assert value["next_action"] == "Inspect the space grant." and value["data"]["result_kind"] == "BLOCKED"
    assert value["data"]["request_id"] and len(value["evidence_refs"]) == 1
    assert len(harness.script.model_requests()) == before and harness.script.items


def test_an_admission_that_cannot_be_logged_is_audit_unavailable_with_exit_4(tmp_path, monkeypatch):
    harness = ready(tmp_path, monkeypatch)
    before = len(harness.script.model_requests())
    (tmp_path / "data" / "capabilities" / "audit.jsonl").chmod(0o644)
    code, value = harness.ask(CALENDAR_QUERY)
    assert (code, value["status"], value["data"]["reason"]) == (4, "UNAVAILABLE", "audit_unavailable")
    assert len(harness.script.model_requests()) == before


def test_without_an_authorization_port_the_tool_calls_remain_the_enforcement_point(tmp_path, monkeypatch):
    """The admission check is an early refusal; an unwired port does not open or close the ask path."""
    harness = ready(tmp_path, monkeypatch)
    harness.service.authorize = None
    code, value = harness.ask(CALENDAR_QUERY)
    assert code == 0 and value["data"]["result_kind"] == "FIXTURE_RESULT"


def test_a_probe_verifies_the_registry_store_before_it_authorizes_or_calls(tmp_path, monkeypatch):
    harness = Harness(tmp_path, monkeypatch, Script())
    order: list = []
    harness.service.state_guard = lambda *names: order.append(names)
    harness.service.authorize = lambda context, operation, action: order.append(operation)
    assert harness.probe()[0] == 0
    assert order == [("receipts", "feature_reports", "capabilities"), "models_probe"]


def test_the_composition_guard_maps_each_name_to_its_store_check(tmp_path, monkeypatch):
    monkeypatch.setenv("QUATI_DATA_DIR", str(tmp_path / "data"))
    cli_main._state("feature_reports:read", "audit_log", "capability_packages")
    assert not (tmp_path / "data").exists()                         # readers create nothing
    cli_main._state("receipts", "capabilities", "feature_reports")
    assert sorted(path.name for path in (tmp_path / "data").iterdir()) == ["capabilities", "feature_reports", "receipts"]
    (tmp_path / "data" / "feature_reports").chmod(0o755)
    with pytest.raises(UnsafeStatePath):
        cli_main._state("feature_reports:read")
    assert stat.S_IMODE((tmp_path / "data" / "feature_reports").stat().st_mode) == 0o755
    registry = tmp_path / "data" / "capabilities" / "registry.json"
    registry.write_bytes(b"{}")
    registry.chmod(0o644)
    with pytest.raises(UnsafeStatePath) as caught:
        cli_main._state("capabilities")
    assert caught.value.filename == str(registry)
    registry.unlink()
    cli_main._state("capabilities", "capability_packages")
    manifest = tmp_path / "data" / "capabilities" / "packages" / "fixtures.x" / "1.0.0" / "capability.scs.json"
    manifest.parent.mkdir(parents=True, mode=0o700)
    manifest.write_bytes(b"{}")
    manifest.chmod(0o644)
    cli_main._state("capabilities")                                 # packages are verified after the decision
    with pytest.raises(UnsafeStatePath) as caught:
        cli_main._state("capability_packages")
    assert caught.value.filename == str(manifest)
    log = tmp_path / "data" / "capabilities" / "audit.jsonl"
    log.write_bytes(b"torn")
    log.chmod(0o600)
    with pytest.raises(Refusal):
        cli_main._state("audit_log")


# ----------------------------------------------------------------- X8: policy reference and proof tier
class FixedIdentity:
    def authenticate(self):
        return RequestContext(actor_id="actor", tenant_id="tenant", space_ids=(), request_id="request-1",
                              trace_id="trace-1", session_id="s", token_jti="j", authenticated_origin_ref="o",
                              deadline_at="2026-11-16T00:00:30+00:00")


class PolicyStateStub:
    def __init__(self, available, version):
        self.available, self.cause, self.policy_version = available, None if available else "missing", version


def recorded(loader) -> dict:
    records: list = []

    def sink(record):
        records.append(record)
        return {"sha256": "0" * 64, "path": "receipt.json"}
    service = CLIService(FixedIdentity(), ProviderConfig(), sink, policy_loader=loader)
    assert service.ask("hello")[0] == 0
    return records[0]


def test_the_receipt_records_the_policy_version_in_force_from_the_trusted_loader():
    seen: list = []

    def loader(tenant_id):
        seen.append(tenant_id)
        return PolicyStateStub(True, "a" * 64)
    receipt = recorded(loader)
    assert receipt["policy_version"] == "a" * 64 and seen == ["tenant"]
    assert receipt["proof_tier"] is None             # a product receipt claims no test proof tier
    assert recorded(lambda tenant_id: PolicyStateStub(False, "b" * 64))["policy_version"] == "b" * 64


def test_the_receipt_records_null_when_no_policy_reference_can_be_determined():
    def failing(tenant_id):
        raise OSError("unreadable")
    assert recorded(None)["policy_version"] is None and recorded(failing)["policy_version"] is None
    assert recorded(lambda tenant_id: PolicyStateStub(True, 7))["policy_version"] is None


def test_the_request_context_no_longer_carries_a_policy_version_that_never_existed():
    assert FixedIdentity().authenticate().policy_version is None
    for path in (REPOSITORY_ROOT / "src" / "quati").rglob("*.py"):
        assert "s00-fixture-readonly" not in path.read_text(encoding="utf-8"), path.name


# ----------------------------------------------------------------- X11: identifier shape and hard links
def resign(identity: LocalIdentity, **changes) -> None:
    record = json.loads(identity.record_path.read_bytes())
    record.pop("signature")
    record.update(changes)
    key = Ed25519PrivateKey.from_private_bytes(identity.key_path.read_bytes())
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    record["signature"] = base64.b64encode(key.sign(canonical)).decode("ascii")
    identity.record_path.write_bytes(json.dumps(record).encode("utf-8"))


@pytest.mark.parametrize("field", ["tenant_id", "principal_id", "personal_space_id", "organization_space_id"])
@pytest.mark.parametrize("value", ["../../../x", "has a space", "x" * 10000, "01arz3ndektsv4rrffq69g5fav",
                                   "01ARZ3NDEKTSV4RRFFQ69G5FAVX", "01ARZ3NDEKTSV4RRFFQ69G5FAU"])
def test_a_signed_record_with_a_non_ulid_identifier_is_not_a_usable_identity(tmp_path, field, value):
    identity = LocalIdentity(tmp_path / "config")
    identity.initialize()
    assert identity.diagnostics()["initialized"] is True
    resign(identity, **{field: value})
    assert identity.diagnostics()["initialized"] is False
    with pytest.raises(AccessDenied):
        identity.authenticate()
    state = runtime_facts.identity_state(identity.directory)
    assert state == {"present": True, "cause": "credential_corrupt", "detail": "record_rejected"}


@pytest.mark.parametrize(("name", "detail"), [("identity.json", "identity_file_hard_link"),
                                              ("device.key", "device_key_hard_link")])
def test_a_credential_file_with_an_extra_hard_link_is_refused_like_any_private_file(tmp_path, name, detail):
    identity = LocalIdentity(tmp_path / "config")
    identity.initialize()
    os.link(identity.directory / name, tmp_path / "second-name")
    assert identity.diagnostics()["initialized"] is False
    with pytest.raises(AccessDenied):
        identity.authenticate()
    assert runtime_facts.identity_state(identity.directory) == {
        "present": True, "cause": "credential_insecure", "detail": detail}
    (tmp_path / "second-name").unlink()
    assert identity.authenticate().tenant_id


# ----------------------------------------------------------------- X15: asset locator and asset digest
def repository_layout(root: Path) -> Path:
    package = root / "src" / "quati"
    package.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'quati'\n", encoding="utf-8")
    for name in ("contracts", "examples"):
        (root / name).mkdir()
    return package


def test_an_assets_directory_beside_the_package_never_shadows_a_source_checkout(tmp_path):
    package = repository_layout(tmp_path / "checkout")
    assert contracts.asset_root(package) == tmp_path / "checkout"
    (package / "assets" / "contracts").mkdir(parents=True)          # planted beside the package
    (package / "assets" / "examples").mkdir()
    assert contracts.asset_root(package) == tmp_path / "checkout"


@pytest.mark.parametrize("missing", ["pyproject.toml", "contracts", "examples", "src"])
def test_the_packaged_assets_are_used_only_without_the_repository_layout(tmp_path, missing):
    root = tmp_path / "site"
    package = repository_layout(root)
    if missing == "src":                                            # an installed wheel: <site>/quati
        package = root / "lib" / "quati"
        package.mkdir(parents=True)
    elif missing == "pyproject.toml":
        (root / missing).unlink()
    else:
        (root / missing).rmdir()
    assert contracts.asset_root(package) == package.resolve().parents[1]     # nothing packaged: the fallback
    (package / "assets").mkdir()
    assert contracts.asset_root(package) == package / "assets"


def test_the_running_package_reads_the_repository_assets():
    assert contracts.asset_root() == contracts.ASSET_ROOT == REPOSITORY_ROOT


def packaged_copy(target: Path) -> Path:
    for directory, pattern in contracts.ASSET_FILES:
        for source in sorted((REPOSITORY_ROOT / directory).glob(pattern)):
            copy = target / directory / source.name
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(source.read_bytes())
    return target


def test_the_asset_digest_is_layout_independent_and_changes_with_any_asset_byte(tmp_path):
    expected = contracts.asset_digest()
    assert len(expected) == 64 and expected == contracts.asset_digest(REPOSITORY_ROOT)
    copy = packaged_copy(tmp_path / "quati" / "assets")
    (copy / "examples" / "behavior" / "notes.txt").write_text("not an asset", encoding="utf-8")
    (copy / "contracts" / "directory.json").mkdir()                 # only files are assets
    assert contracts.asset_digest(copy) == expected
    listed = [path for directory, pattern in contracts.ASSET_FILES for path in sorted((copy / directory).glob(pattern))
              if path.is_file()]
    assert len(listed) > 10
    for path in (listed[0], listed[-1]):
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        assert contracts.asset_digest(copy) != expected
        path.write_bytes(original)
    listed[0].rename(listed[0].with_name("renamed" + listed[0].suffix))
    assert contracts.asset_digest(copy) != expected
    assert contracts.asset_digest(tmp_path / "empty") != expected


def test_the_asset_file_list_is_the_package_data_of_the_wheel():
    setup = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["setuptools"]
    packaged = sorted((setup["package-dir"][name], pattern)
                      for name, patterns in setup["package-data"].items() for pattern in patterns)
    assert sorted(contracts.ASSET_FILES) == packaged


def test_doctor_behavior_status_and_every_receipt_carry_the_asset_digest(tmp_path):
    expected = contracts.asset_digest()
    status = active_package_status(REPOSITORY_ROOT, "examples/behavior/executive-secretary.yaml", "cheap_tool_capable")
    assert status["status"] == "VALID" and status["asset_digest"] == expected
    invalid = active_package_status(tmp_path, "examples/behavior/absent.yaml")
    assert invalid["status"] == "INVALID" and invalid["asset_digest"] == contracts.asset_digest(tmp_path)
    bound = evidence.bound_to_code({"digests": {"asset_digest": "forged", "config_hash": "c"}})
    assert bound["digests"]["asset_digest"] == expected and bound["digests"]["config_hash"] == "c"
    assert len(bound["digests"]["code_digest"]) == 64


# ----------------------------------------------------------------- X16: one seed check
def test_the_eval_seed_rule_has_one_owner_and_the_cli_prints_the_use_case_response(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUATI_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("QUATI_DATA_DIR", str(tmp_path / "data"))
    expected = CLIService(None, ProviderConfig(), None).ask("x", eval_permutation_seed=3)
    assert expected[0] == 2 and expected[1]["error"]["code"] == "INVALID_INPUT"
    code = cli_main.main(["ask", "--json", "--eval-candidate-permutation-seed", "3", "--", "x"])
    assert code == 2 and json.loads(capsys.readouterr().out) == expected[1]
    assert not (tmp_path / "data").exists() and not (tmp_path / "config").exists()
