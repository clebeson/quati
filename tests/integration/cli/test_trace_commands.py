"""Public ``quati trace show|explain`` in S00 (LOG-0041 finding N11, decision D6; M26 Public interface).

Requirements discriminated: M26-AT-01 (the S00 form of ``CapabilityExplanation``, built only from
recorded data with zero model calls; CAP-02 oracle: the selected read capability, the excluded write
capability ``scope_not_granted`` and the unranked decoy ``outcome_mismatch``), M26-RT-02 in its S00
form (authenticate, then the AuthorizationPort, before any receipt is read; another principal's
record and an unknown id are the same NOT_FOUND; an unreadable receipt or audit log is
``audit_store_unavailable`` and an unsafe data directory ``state_dir_unsafe``, with no fallback), M01-FR-01 (``trace export|replay`` stay UNSUPPORTED naming slice S02) and the
S00 runtime contract rule that no model-written text, request text or secret is displayed.

Every command under test is a real child process of ``python -m quati`` with an isolated
``QUATI_CONFIG_DIR`` / ``QUATI_DATA_DIR`` (proof tier L2 for the trace commands). The asks whose
records are read were produced by the public ``main`` in a child process whose model is the
SCRIPTED FAKE of ``tests/unit/s00_fix6_runner.py``: no network, no vendor CLI, no credential,
never evidence of a real provider. ``QUATI_ALLOW_LIVE`` and ``QUATI_LIVE_EVAL`` are never set.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import quati
from quati.application.identity import canonical_bytes

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = Path(quati.__file__).resolve().parents[1]
RUNNER = REPOSITORY_ROOT / "tests" / "unit" / "s00_fix6_runner.py"
PYTHON = str(Path(sys.executable).absolute())

READ, WRITE, DECOY = "fixtures.calendar-read", "fixtures.calendar-write", "fixtures.mail-search"
REQUEST_MARK, MODEL_MARK, TOOL_MARK, ID_MARK = "REQMARK7391", "MODELMARK5512", "TOOLMARK8804", "IDMARK6627"
KEY_CANARY = "sk-trace-CANARY-4471-do-not-print"
WORK_TEXT = f"what is my next appointment {REQUEST_MARK}"
SCRIPT = [["classify"], ["search", "next appointment calendar"], ["describe", f"{ID_MARK}.capability"],
          ["describe", READ], ["invoke", READ, {"limit": 1}], ["final", f"{MODEL_MARK} all done"]]
MARKS = (REQUEST_MARK, MODEL_MARK, TOOL_MARK, ID_MARK, KEY_CANARY)
RESPONSE_KEYS = {"status", "data", "evidence_refs", "uncertainties", "next_action", "error"}
UNKNOWN_REQUEST, UNKNOWN_TRACE = "request-" + "0" * 32, "f" * 32


class Profile:
    """One isolated LOCAL profile driven only through child processes of the public CLI."""

    def __init__(self, root: Path) -> None:
        self.root, self.config, self.data = root, root / "config", root / "data"
        self.harness = root / "harness"
        self.runs = 0

    def environment(self, extra: dict | None = None) -> dict:
        environment = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(SOURCE_ROOT), "HOME": str(self.root),
                       "QUATI_CONFIG_DIR": str(self.config), "QUATI_DATA_DIR": str(self.data),
                       "QUATI_API_KEY": KEY_CANARY}
        if "COVERAGE_PROCESS_START" in os.environ:      # opt-in subprocess coverage (tests/coverage/sitecustomize.py)
            environment["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
            environment["PYTHONPATH"] += os.pathsep + str(REPOSITORY_ROOT / "tests" / "coverage")
            for name in ("QUATI_TEST_COVERAGE_LIBRARY", "COVERAGE_FILE"):
                if name in os.environ:
                    environment[name] = os.environ[name]
        environment.update(extra or {})
        return environment

    def raw(self, *argv: str, extra: dict | None = None) -> tuple[int, str]:
        """The product CLI exactly as installed: (exit code, stdout); stderr must be empty."""
        completed = subprocess.run([PYTHON, "-m", "quati", *argv], capture_output=True,
                                   env=self.environment(extra), timeout=120, check=False)
        assert completed.stderr == b"", completed.stderr
        return completed.returncode, completed.stdout.decode("utf-8")

    def quati(self, *argv: str, extra: dict | None = None) -> tuple[int, dict]:
        code, output = self.raw(*argv, extra=extra)
        lines = output.splitlines()
        assert len(lines) == 1, output
        value = json.loads(lines[0])
        assert set(value) == RESPONSE_KEYS
        return code, value

    def model(self, script: list, *argv: str) -> tuple[int, dict]:
        """The public CLI in a fresh process whose model is the scripted fake; one JSON Response."""
        self.runs += 1
        self.harness.mkdir(exist_ok=True)
        scenario = self.harness / f"scenario-{self.runs}.json"
        scenario.write_text(json.dumps({"script": script}), encoding="utf-8")
        completed = subprocess.run([PYTHON, str(RUNNER), str(self.harness / "spy.jsonl"), str(scenario), *argv],
                                   capture_output=True, env=self.environment(), timeout=120, check=False)
        assert completed.stderr == b"", completed.stderr
        return completed.returncode, json.loads(completed.stdout.decode("utf-8"))

    def audit(self) -> list[dict]:
        path = self.data / "capabilities" / "audit.jsonl"
        return [json.loads(line) for line in path.read_bytes().splitlines() if line] if path.exists() else []

    def files(self) -> dict:
        """Every file and symlink under the profile (harness excluded) with its content digest."""
        found = {}
        for base in (self.config, self.data):
            for path in sorted(base.rglob("*")) if base.exists() else []:
                name = str(path.relative_to(self.root))
                if path.is_symlink():
                    found[name] = "symlink"
                elif path.is_file():
                    found[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return found

    def copy(self, target: Path) -> "Profile":
        shutil.copytree(self.root, target, symlinks=True)
        return Profile(target)


class Recorded:
    def __init__(self, profile: Profile, work: dict, synthetic: dict, greeting: dict) -> None:
        self.profile, self.work, self.synthetic, self.greeting = profile, work, synthetic, greeting


def build(root: Path) -> Recorded:
    """init; read fixture and decoy ENABLED, write fixture refused; probed scripted model; three asks."""
    profile = Profile(root)
    root.mkdir(parents=True)
    assert profile.quati("init", "--json")[0] == 0
    for name in ("calendar-read", "mail-search"):
        code, value = profile.quati("capabilities", "install-fixture", name, "--enable-fixture", "--json")
        assert (code, value["data"]["lifecycle"]) == (0, "ENABLED")
    code, value = profile.quati("capabilities", "install-fixture", "calendar-write", "--json")
    assert code == 4 and value["data"]["lifecycle"] != "ENABLED"
    code, value = profile.model([], "models", "probe", "--json")
    assert code == 0 and value["data"]["feature_report"]["features"]["tools"] == "SUPPORTED"
    code, work = profile.model(SCRIPT, "ask", "--json", "--", WORK_TEXT)
    assert (code, work["data"]["result_kind"]) == (0, "FIXTURE_RESULT")
    code, synthetic = profile.model(SCRIPT, "ask", "--json", "--synthetic-evidence", "--", WORK_TEXT)
    assert (code, synthetic["data"]["result_kind"]) == (0, "FIXTURE_RESULT")
    code, greeting = profile.quati("ask", "--json", "--", "Hello")
    assert (code, greeting["data"]["result_kind"]) == (0, "GREETING")
    return Recorded(profile, work, synthetic, greeting)


@pytest.fixture(scope="module")
def recorded(tmp_path_factory) -> Recorded:
    """Shared by the tests that only read; a test that changes the profile works on ``scratch``."""
    return build(tmp_path_factory.mktemp("trace") / "profile")


@pytest.fixture
def scratch(recorded: Recorded, tmp_path: Path) -> Recorded:
    """A private profile with its own asks (receipt and report paths are absolute, so it is rebuilt)."""
    return build(tmp_path / "profile")


def receipt_file(value: dict) -> tuple[str, Path]:
    _, digest, path = value["evidence_refs"][0].split(":", 2)
    return digest, Path(path)


def stored(value: dict) -> dict:
    digest, path = receipt_file(value)
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    return json.loads(raw)


def ids(value: dict) -> tuple[str, str]:
    return value["data"]["request_id"], value["data"]["trace_id"]


def no_marks(text: str) -> None:
    for mark in MARKS:
        assert mark not in text, mark


# ----------------------------------------------------------------- trace show
def test_show_returns_the_recorded_receipt_and_decisions_of_one_request(recorded: Recorded) -> None:
    """D6: status, result kind, digests, usage, tool trajectory, policy and authz decisions, evidence ref."""
    request_id, trace_id = ids(recorded.work)
    receipt = stored(recorded.work)
    code, value = recorded.profile.quati("trace", "show", request_id, "--json")
    assert (code, value["status"], value["error"]) == (0, "SUCCEEDED", None)
    data = value["data"]
    assert (data["request_id"], data["trace_id"], data["commitment_id"]) == (request_id, trace_id, None)
    assert data["source"] == "S00_RECEIPTS_AND_REGISTRY_AUDIT_LOG"
    shown = data["receipt"]
    assert value["evidence_refs"] == recorded.work["evidence_refs"] == [shown["ref"]]
    assert shown["sha256"] == receipt_file(recorded.work)[0] and shown["integrity"] == "UNSIGNED_LOCAL_FILE"
    assert (shown["kind"], shown["status"], shown["result_kind"], shown["reason"]) == (
        "ask_receipt", "SUCCEEDED", "FIXTURE_RESULT", None)
    assert shown["executed_capabilities"] == [f"{READ}@1.0.0"]
    assert shown["digests"] == receipt["digests"] and shown["usage"] == receipt["usage"]
    assert shown["provider"] == receipt["provider"] and shown["timestamp"] == receipt["timestamp"]
    for name in ("request_hash", "output_hash", "final_text_sha256", "classification_sha256", "policy_version"):
        assert shown[name] == receipt[name], name
    assert shown["synthetic_evidence_recorded"] is False
    steps = shown["trajectory"]
    assert [(step["step"], step["operation"], step["status"], step["handler_executed"]) for step in steps] == [
        (1, "search", "SUCCEEDED", False), (2, "describe", "DENIED", False), (3, "describe", "SUCCEEDED", False),
        (4, "invoke", "SUCCEEDED", True)]
    assert steps[3]["capability_ref"] == f"{READ}@1.0.0" and steps[3]["policy_verdict"] == "ALLOW"
    assert steps[1]["capability_ref"].startswith("sha256:")          # a model-supplied id is only ever a digest
    for step, source in zip(steps, receipt["trajectory"]):
        assert "context" not in step and "arguments" not in step
        assert (step["arguments_digest"], step["result_sha256"]) == (source["arguments_digest"], source["result_sha256"])
    assert [(item["operation"], item["verdict"], item["reason_code"]) for item in data["authz_decisions"]] == [
        ("ask_admission", "ALLOW", "OK"),      # LOG-0044 X6: the grant is checked before the first model call
        ("search", "ALLOW", "OK"), ("describe", "ALLOW", "OK"), ("describe", "ALLOW", "OK"),
        ("invoke", "ALLOW", "OK"), ("ask", "ALLOW", "OK")]
    recorded_policy = [event for event in recorded.profile.audit()
                       if event["event"] == "policy.decided" and event["request_id"] == request_id]
    assert len(recorded_policy) == 1 and len(data["policy_decisions"]) == 1
    decision = data["policy_decisions"][0]
    assert (decision["decision_id"], decision["verdict"], decision["capability_ref"]) == (
        recorded_policy[0]["decision"]["decision_id"], "ALLOW", f"{READ}@1.0.0")
    assert decision["policy_version"] == recorded_policy[0]["decision"]["policy_version"]
    assert set(data["not_recorded"]) == {"commitment_id", "event_ids"}


def test_show_by_trace_id_and_by_request_option_return_the_same_record(recorded: Recorded) -> None:
    request_id, trace_id = ids(recorded.work)
    by_request = recorded.profile.raw("trace", "show", request_id, "--json")
    assert recorded.profile.raw("trace", "show", trace_id, "--json") == by_request
    assert recorded.profile.raw("trace", "show", "--request", request_id, "--json") == by_request
    assert by_request[0] == 0


def test_show_of_a_greeting_has_no_trajectory_and_no_decision(recorded: Recorded) -> None:
    request_id, trace_id = ids(recorded.greeting)
    code, value = recorded.profile.quati("trace", "show", trace_id, "--json")
    assert (code, value["status"]) == (0, "SUCCEEDED")
    shown = value["data"]["receipt"]
    assert value["data"]["request_id"] == request_id
    assert (shown["status"], shown["provider_used"], shown["trajectory"]) == ("SUCCEEDED", False, [])
    assert shown["sha256"] == receipt_file(recorded.greeting)[0]
    assert value["data"]["authz_decisions"] == [] and value["data"]["policy_decisions"] == []


def test_trace_commands_are_read_only_and_log_one_authorization_each(scratch: Recorded) -> None:
    """Nothing but one ``authz.decided`` line is written; no receipt, no provider, no handler."""
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    for position, operation in enumerate(("show", "explain")):
        before, events = profile.files(), profile.audit()
        assert profile.quati("trace", operation, request_id, "--json")[0] == 0
        after, added = profile.files(), profile.audit()[len(events):]
        changed = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
        assert changed == {"data/capabilities/audit.jsonl"}, position
        assert [(event["event"], event["operation"], event["decision"]["action"], event["decision"]["verdict"])
                for event in added] == [("authz.decided", f"trace_{operation}", "read", "ALLOW")]


# ----------------------------------------------------------------- trace explain
def test_explain_names_the_selected_capability_and_why_each_alternative_was_excluded(recorded: Recorded) -> None:
    """M26-AT-01 / CAP-02 in the S00 form: built from the receipt and the audit log, no model call."""
    request_id, trace_id = ids(recorded.synthetic)
    receipt = stored(recorded.synthetic)
    policy = [event for event in recorded.profile.audit()
              if event["event"] == "policy.decided" and event["request_id"] == request_id][0]
    code, value = recorded.profile.quati("trace", "explain", request_id, "--json")
    assert (code, value["status"], value["error"]) == (0, "SUCCEEDED", None)
    data = value["data"]
    assert (data["request_id"], data["trace_id"], data["commitment_id"]) == (request_id, trace_id, None)
    assert data["selected"] == {"capability_id": READ, "version": "1.0.0",
                                "binding_hash": policy["intent"]["binding_version"]}
    candidates = {item["capability_id"]: item for item in data["candidates"]}
    assert sorted(candidates) == [READ, WRITE, DECOY] and len(data["candidates"]) == 3
    chosen = candidates[READ]
    assert (chosen["version"], chosen["authorization"], chosen["excluded_reason"], chosen["filter_reasons"]) == (
        "1.0.0", "ALLOW", None, [])
    assert chosen["rank_features"] == receipt["trajectory"][0]["rank_reasons"][0]
    assert chosen["rank_features"]["rank"] == 1
    write = candidates[WRITE]
    assert (write["version"], write["authorization"], write["excluded_reason"], write["rank_features"]) == (
        "1.0.0", "DENY", "scope_not_granted", None)
    assert "NOT_AUTHORIZED" in write["filter_reasons"] and "EFFECT_ABOVE_CEILING" in write["filter_reasons"]
    decoy = candidates[DECOY]
    assert (decoy["version"], decoy["authorization"], decoy["excluded_reason"], decoy["rank_features"]) == (
        "1.0.0", "ALLOW", "outcome_mismatch", None)
    assert data["policy_decision_id"] == policy["decision"]["decision_id"]
    assert (data["model_id"], data["provider_id"]) == ("fake-model-1", receipt["provider"]["provider_id"])
    assert data["effective_prompt_hash"] == receipt["digests"]["effective_prompt_hash"]
    assert data["model_rationale"] is None and data["model_rationale_sha256"] == receipt["final_text_sha256"]
    assert data["event_ids"] == [] and set(data["not_recorded"]) == {"commitment_id", "event_ids", "model_rationale"}
    assert value["evidence_refs"] == recorded.synthetic["evidence_refs"]
    assert recorded.profile.raw("trace", "explain", trace_id, "--json")[1] == canonical(value)


def canonical(value: dict) -> str:
    return canonical_bytes(value).decode("ascii") + "\n"


def test_explain_without_a_recorded_catalog_says_that_unranked_candidates_are_unknown(recorded: Recorded) -> None:
    """The default receipt holds only the catalog digest: the unranked decoy is not invented."""
    code, value = recorded.profile.quati("trace", "explain", ids(recorded.work)[0], "--json")
    assert (code, value["status"]) == (0, "PARTIAL")
    assert [item["capability_id"] for item in value["data"]["candidates"]] == [READ, WRITE]
    assert "unranked_candidates_not_recorded" in value["uncertainties"]
    assert value["data"]["selected"]["capability_id"] == READ


def test_explain_of_a_greeting_selects_nothing(recorded: Recorded) -> None:
    code, value = recorded.profile.quati("trace", "explain", ids(recorded.greeting)[0], "--json")
    assert (code, value["status"]) == (0, "PARTIAL")
    data = value["data"]
    assert (data["selected"], data["candidates"], data["policy_decision_id"], data["model_id"]) == (None, [], None, None)
    assert "no_capability_selected" in value["uncertainties"]


# ----------------------------------------------------------------- displayed content
@pytest.mark.parametrize("operation", ["show", "explain"])
def test_no_request_text_model_text_or_secret_is_displayed(recorded: Recorded, operation: str) -> None:
    """S00 runtime contract: hashes only. The synthetic receipt FILE holds both texts; the output never does."""
    raw = receipt_file(recorded.synthetic)[1].read_text(encoding="utf-8")
    assert REQUEST_MARK in raw and MODEL_MARK in raw and ID_MARK in raw      # the markers really are on disk
    for value in (recorded.work, recorded.synthetic, recorded.greeting):
        for identifier in ids(value):
            code, output = recorded.profile.raw("trace", operation, identifier, "--json")
            assert code == 0
            no_marks(output)
            assert str(recorded.profile.config) not in output


@pytest.mark.parametrize("operation", ["show", "explain"])
def test_output_is_byte_identical_across_processes(recorded: Recorded, operation: str) -> None:
    request_id = ids(recorded.synthetic)[0]
    outputs = {recorded.profile.raw("trace", operation, request_id, "--json", extra=extra)
               for extra in ({"PYTHONHASHSEED": "0"}, {"PYTHONHASHSEED": "4242", "TZ": "Asia/Tokyo", "LC_ALL": "C"})}
    assert len(outputs) == 1 and next(iter(outputs))[0] == 0


# ----------------------------------------------------------------- unknown id, identity, authorization
@pytest.mark.parametrize("operation", ["show", "explain"])
@pytest.mark.parametrize("identifier", [UNKNOWN_REQUEST, UNKNOWN_TRACE, "c-1", "../receipts", "request-"])
def test_unknown_id_is_a_typed_not_found(recorded: Recorded, operation: str, identifier: str) -> None:
    code, value = recorded.profile.quati("trace", operation, "--json", "--", identifier)
    assert (code, value["status"], value["error"]["code"]) == (4, "DENIED", "NOT_FOUND")
    assert value["data"] == {"reason": "trace_not_found"} and value["evidence_refs"] == []


def test_show_needs_exactly_one_identifier(recorded: Recorded) -> None:
    for argv in (("trace", "show", "--json"),
                 ("trace", "show", UNKNOWN_TRACE, "--request", UNKNOWN_REQUEST, "--json")):
        code, value = recorded.profile.quati(*argv)
        assert (code, value["status"], value["error"]["code"]) == (2, "DENIED", "INVALID_INPUT")


def test_another_principals_record_is_the_same_not_found_as_an_unknown_id(recorded: Recorded, tmp_path: Path) -> None:
    """M26-RT-02: a receipt of another LOCAL principal copied into this data directory is not visible."""
    other = Profile(tmp_path / "other")
    other.root.mkdir()
    assert other.quati("init", "--json")[0] == 0
    assert other.quati("ask", "--json", "--", "Hello")[0] == 0             # creates the receipts directory
    source = receipt_file(recorded.work)[1]
    target = other.data / "receipts" / source.name
    target.write_bytes(source.read_bytes())
    target.chmod(0o600)
    answers = {other.raw("trace", operation, identifier, "--json")
               for operation in ("show",) for identifier in (ids(recorded.work)[0], UNKNOWN_REQUEST)}
    assert len(answers) == 1
    code, output = next(iter(answers))
    assert code == 4 and json.loads(output)["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("operation", ["show", "explain"])
def test_unauthenticated_caller_reads_nothing(recorded: Recorded, tmp_path: Path, operation: str) -> None:
    """Authentication precedes every read: same answer for a known and an unknown id, nothing written."""
    profile = recorded.profile
    before = profile.files()
    cases = [{"QUATI_CONFIG_DIR": str(tmp_path / "absent")}, {"QUATI_CAPABILITY_CONTEXT": "1"}]
    for extra in cases:
        answers = {profile.raw("trace", operation, identifier, "--json", extra=extra)
                   for identifier in (ids(recorded.work)[0], UNKNOWN_REQUEST)}
        assert len(answers) == 1
        code, output = next(iter(answers))
        value = json.loads(output)
        assert (code, value["status"], value["error"]["code"], value["data"]) == (4, "DENIED", "UNAUTHENTICATED", None)
        assert str(profile.root) not in output
    assert profile.files() == before and not (tmp_path / "absent").exists()


def resign(profile: Profile, **changes) -> None:
    """Re-sign the installation record with the profile's own device key (a valid, different membership)."""
    path = profile.config / "identity.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("signature")
    record.update(changes)
    key = Ed25519PrivateKey.from_private_bytes((profile.config / "device.key").read_bytes())
    signed = dict(record, signature=base64.b64encode(key.sign(canonical_bytes(record))).decode("ascii"))
    path.write_bytes(canonical_bytes(signed))


@pytest.mark.parametrize("operation", ["show", "explain"])
def test_principal_without_a_grant_is_forbidden_before_any_receipt_is_read(scratch: Recorded, operation: str) -> None:
    """RFC-013 section 6: DENY is logged; the answer is the same for a known and an unknown id."""
    profile = scratch.profile
    resign(profile, tenant_role="GUEST")
    events = profile.audit()
    answers = [profile.quati("trace", operation, identifier, "--json")
               for identifier in (ids(scratch.work)[0], UNKNOWN_REQUEST)]
    assert answers[0] == answers[1]
    code, value = answers[0]
    assert (code, value["status"], value["error"]["code"]) == (4, "DENIED", "FORBIDDEN")
    assert value["data"] == {"reason": "NO_SPACE_GRANT"} and value["evidence_refs"] == []
    added = profile.audit()[len(events):]
    assert [(event["event"], event["operation"], event["decision"]["verdict"], event["decision"]["reason_code"])
            for event in added] == [("authz.decided", f"trace_{operation}", "DENY", "NO_SPACE_GRANT")] * 2


# ----------------------------------------------------------------- unusable store: fail closed
def assert_store_unavailable(profile: Profile, identifier: str, data: dict) -> None:
    """Exit 4 (M01 exit table row 4: UNAVAILABLE not caused by a provider), typed reason, no content."""
    for operation in ("show", "explain"):
        code, value = profile.quati("trace", operation, identifier, "--json")
        assert (code, value["status"], value["error"]["code"]) == (4, "UNAVAILABLE", "TEMPORARILY_UNAVAILABLE"), value
        assert value["data"] == data and value["evidence_refs"] == []


FILE_UNSAFE = {"reason": "audit_store_unavailable"}


def test_symlinked_receipts_directory_fails_closed(scratch: Recorded, tmp_path: Path) -> None:
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    moved = tmp_path / "elsewhere"
    (profile.data / "receipts").rename(moved)
    (profile.data / "receipts").symlink_to(moved, target_is_directory=True)
    before = sorted(path.name for path in moved.iterdir())
    assert_store_unavailable(profile, request_id, {"reason": "state_dir_unsafe", "component": "receipts"})
    assert sorted(path.name for path in moved.iterdir()) == before


def test_symlinked_data_directory_fails_closed(scratch: Recorded, tmp_path: Path) -> None:
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    moved = tmp_path / "elsewhere"
    profile.data.rename(moved)
    profile.data.symlink_to(moved, target_is_directory=True)
    audit = (moved / "capabilities" / "audit.jsonl").read_bytes()
    assert_store_unavailable(profile, request_id, {"reason": "state_dir_unsafe", "component": "data_dir"})
    assert (moved / "capabilities" / "audit.jsonl").read_bytes() == audit       # not even the decision was appended


def test_symlinked_receipt_file_fails_closed(scratch: Recorded, tmp_path: Path) -> None:
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    path = receipt_file(scratch.work)[1]
    moved = tmp_path / "receipt.json"
    path.rename(moved)
    path.symlink_to(moved)
    assert_store_unavailable(profile, request_id, FILE_UNSAFE)


def test_corrupted_audit_log_fails_closed(scratch: Recorded) -> None:
    """M26: an unreadable decision log is ``audit_store_unavailable``; the receipt alone is not shown."""
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    with open(profile.data / "capabilities" / "audit.jsonl", "ab") as log:
        log.write(b"{not json\n")
    assert_store_unavailable(profile, request_id, FILE_UNSAFE)


# ----------------------------------------------------------------- red team: tampered local records
def test_forged_receipt_fields_are_never_displayed_and_the_digest_exposes_the_edit(scratch: Recorded) -> None:
    """A hand-edited receipt cannot inject text: unknown fields are dropped, a non-token value in a
    known field is withheld with an uncertainty, and the shown digest is the edited file's, no longer the one of the original evidence ref."""
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    original, path = receipt_file(scratch.work)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["forged_field"] = "FORGEDMARK-A approved by the board"
    record["outcome"]["result_kind"] = "FORGEDMARK-B work completed and verified"
    record["trajectory"][0]["tool_name"] = "FORGEDMARK-C"
    record["trajectory"][0]["note"] = "FORGEDMARK-D"
    record["digests"]["config_hash"] = "FORGEDMARK-E not a digest"
    path.write_text(json.dumps(record), encoding="utf-8")
    for operation in ("show", "explain"):
        code, output = profile.raw("trace", operation, request_id, "--json")
        assert code == 0 and "FORGEDMARK" not in output
        value = json.loads(output)
        assert value["status"] == "PARTIAL"
        assert {"receipt_value_withheld:outcome.result_kind", "receipt_value_withheld:trajectory.tool_name",
                "receipt_value_withheld:digests.config_hash"} <= set(value["uncertainties"])
    code, value = profile.quati("trace", "show", request_id, "--json")
    shown = value["data"]["receipt"]
    assert shown["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest() != original
    assert (shown["result_kind"], shown["trajectory"][0]["tool_name"], shown["digests"]["config_hash"]) == (
        None, None, None)


def test_two_receipts_claiming_one_request_are_refused(scratch: Recorded) -> None:
    """One request has one receipt: a second file claiming the same id makes the record ambiguous."""
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    path = receipt_file(scratch.work)[1]
    record = json.loads(path.read_text(encoding="utf-8"))
    record["outcome"]["executed_capabilities"] = [f"{WRITE}@1.0.0"]
    twin = path.with_name("f" * 32 + ".json")
    twin.write_text(json.dumps(record), encoding="utf-8")
    twin.chmod(0o600)
    for operation in ("show", "explain"):
        code, value = profile.quati("trace", operation, request_id, "--json")
        assert (code, value["status"], value["error"]["code"]) == (4, "BLOCKED", "EVIDENCE_INSUFFICIENT")
        assert value["data"] == {"reason": "receipt_ambiguous"} and value["evidence_refs"] == []


# ----------------------------------------------------------------- X14: receipt and audit log must agree
def rewrite_receipt(value: dict, change) -> None:
    path = receipt_file(value)[1]
    record = json.loads(path.read_text(encoding="utf-8"))
    change(record)
    path.write_text(json.dumps(record), encoding="utf-8")


def assert_partial_with(profile: Profile, request_id: str, *expected: str) -> None:
    for operation in ("show", "explain"):
        code, value = profile.quati("trace", operation, request_id, "--json")
        assert (code, value["status"], value["error"]) == (0, "PARTIAL", None), value
        assert set(expected) <= set(value["uncertainties"]), (operation, value["uncertainties"])
        assert value["next_action"]


def test_an_unedited_record_agrees_with_the_audit_log(recorded: Recorded) -> None:
    """Negative control of the X14 checks: the recorded asks show no consistency uncertainty."""
    for item in (recorded.work, recorded.synthetic, recorded.greeting):
        code, value = recorded.profile.quati("trace", "show", ids(item)[0], "--json")
        assert code == 0 and not {"audit_receipt_mismatch", "receipt_inconsistent"} & set(value["uncertainties"])


def test_a_forged_executed_capability_without_its_policy_decision_is_partial(scratch: Recorded) -> None:
    """LOG-0044 X14: an executed capability with no ``policy.decided ALLOW`` line is never a clean SUCCEEDED."""
    def forge(record: dict) -> None:
        record["outcome"]["executed_capabilities"] = [f"{WRITE}@1.0.0"]
        step = record["trajectory"][-1]
        step["capability_ref"] = f"{WRITE}@1.0.0"
    rewrite_receipt(scratch.work, forge)
    assert_partial_with(scratch.profile, ids(scratch.work)[0], "audit_receipt_mismatch")


def test_a_forged_executing_step_without_its_policy_decision_is_partial(scratch: Recorded) -> None:
    """A step that claims an executed handler for a capability the audit log never allowed; the outcome
    list is left alone, so only the step itself contradicts the log."""
    def forge(record: dict) -> None:
        record["trajectory"].append(dict(record["trajectory"][-1], capability_ref=f"{WRITE}@1.0.0",
                                         step=len(record["trajectory"]) + 1))
    rewrite_receipt(scratch.work, forge)
    assert_partial_with(scratch.profile, ids(scratch.work)[0], "audit_receipt_mismatch")
    code, value = scratch.profile.quati("trace", "show", ids(scratch.work)[0], "--json")
    assert "receipt_inconsistent" not in value["uncertainties"]


def test_an_executed_capability_that_the_trajectory_does_not_hold_is_partial(scratch: Recorded) -> None:
    def forge(record: dict) -> None:
        record["outcome"]["executed_capabilities"].append(f"{DECOY}@1.0.0")
    rewrite_receipt(scratch.work, forge)
    assert_partial_with(scratch.profile, ids(scratch.work)[0], "receipt_inconsistent", "audit_receipt_mismatch")


def test_a_flipped_status_without_an_execution_is_partial(scratch: Recorded) -> None:
    """A receipt that claims SUCCEEDED / FIXTURE_RESULT while no step executed a handler."""
    def forge(record: dict) -> None:
        record["outcome"]["executed_capabilities"] = []
        for step in record["trajectory"]:
            step["handler_executed"] = False
    rewrite_receipt(scratch.work, forge)
    assert_partial_with(scratch.profile, ids(scratch.work)[0], "receipt_inconsistent")

    def blocked_as_success(record: dict) -> None:
        record["outcome"]["result_kind"] = "BLOCKED"
    rewrite_receipt(scratch.synthetic, blocked_as_success)
    assert_partial_with(scratch.profile, ids(scratch.synthetic)[0], "receipt_inconsistent")


def test_a_removed_policy_decision_line_is_partial(scratch: Recorded) -> None:
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    log = profile.data / "capabilities" / "audit.jsonl"
    lines = log.read_bytes().splitlines(keepends=True)
    kept = [line for line in lines
            if not (json.loads(line)["event"] == "policy.decided" and json.loads(line)["request_id"] == request_id)]
    assert len(kept) == len(lines) - 1
    log.write_bytes(b"".join(kept))
    assert_partial_with(profile, request_id, "audit_receipt_mismatch")


def test_a_forged_policy_decision_line_is_partial(scratch: Recorded) -> None:
    """An ALLOW line for a capability that no trajectory step invoked (audit script d6.py)."""
    profile, request_id = scratch.profile, ids(scratch.work)[0]
    log = profile.data / "capabilities" / "audit.jsonl"
    genuine = next(event for event in profile.audit()
                   if event["event"] == "policy.decided" and event["request_id"] == request_id)
    forged = {**genuine, "capability_id": WRITE}
    with open(log, "ab") as handle:
        handle.write(canonical_bytes(forged) + b"\n")
    assert_partial_with(profile, request_id, "audit_receipt_mismatch")


# ----------------------------------------------------------------- export and replay stay S02
@pytest.mark.parametrize("argv", [("trace", "export", "trace-1", "--out", "trace.json"), ("trace", "replay", "trace-1")])
def test_export_and_replay_are_typed_unsupported_naming_slice_s02(recorded: Recorded, tmp_path: Path, argv) -> None:
    profile = Profile(tmp_path / "empty")
    profile.root.mkdir()
    code, value = profile.quati(*argv, "--json")
    assert (code, value["status"], value["error"]["code"], value["data"]) == (4, "UNAVAILABLE", "UNSUPPORTED", None)
    assert "slice S02" in value["error"]["message"] and "S02" in value["next_action"]
    assert profile.files() == {} and not Path("trace.json").exists()
