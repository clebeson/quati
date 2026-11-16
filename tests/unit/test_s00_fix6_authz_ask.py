"""S00 fix round 6: independent audit of gates 01/03/04 (docs/audit/S00_GATES_01_03_04_AUDIT_2026-11-16.md).

Findings discriminated here (dispositions in docs/governance/LOG.md, LOG-0039):

* F2  (SOC-01 and its negative; S00-GATE-03 first half): a greeting-only text never reaches the
  tool loop, whatever the model's label says.
* F3  (S00_RUNTIME_CONTRACT "Independent-review fail-closed refinement"; M15 ask outcome kinds):
  no model-written text is displayed; a social label on a text that opens with no recognized
  greeting is not a conversation.
* F4  (RFC-013 section 12, S00 row; M02 authorization order row 7): every registry read and write
  reachable from the CLI or the ask session passes the AuthorizationPort and logs ``authz.decided``.
* F5  (RFC-013 sections 6 and 10): the port is a required constructor parameter and the check is
  bound to the space that owns the registry, never to a space named by the request.
* F15 (M14 lifecycle table): ``--enable-fixture`` never reports success for a record that is not ENABLED.

Proof tiers. F2, F3, F15 and the allowed legs of F4 are observed on the public path: real child
processes of ``python -m quati`` (L2 for the operator commands) or of the public ``main`` with a
SCRIPTED FAKE model (``s00_fix6_runner.py``, L1; the scripted model is the adversary and is never
evidence of a real provider). The denied legs of F4 that the S00 command line cannot produce run
in-process through the same composition root (L1). No network, no ``QUATI_ALLOW_LIVE``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import quati
from quati.adapters.capability_store import FileRegistryStore
from quati.adapters.fixture_capabilities import FIXTURE_HANDLERS, FixtureHandlerRegistry, StaticGrants
from quati.adapters.fts_index import Fts5CapabilityIndex
from quati.adapters.local_identity import LocalIdentity
from quati.application import ask as ask_module
from quati.application.capability_registry import RegistryService
from quati.application.discovery import DiscoveryService
from quati.application.identity import ScopeAuthorization, canonical_bytes
from quati.cli import composition

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path(quati.__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent / "s00_fix6_runner.py"
PYTHON = str(Path(sys.executable).absolute())
sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t04_support import SOCIAL, Harness, Script, classified, final, receipt_of  # noqa: E402

CAPABILITY = "fixtures.calendar-read"
HOSTILE = [["classify"], ["search", "next appointment calendar"], ["describe", CAPABILITY],
           ["invoke", CAPABILITY, {"limit": 1}], ["final", "done"]]
CLAIM = "Done. All events were deleted and the board was notified. Verified by audit record AUD-991."
SPACE_GRANT_COMMAND = "quati spaces describe <space-id>"


# ----------------------------------------------------------------- harness (real child processes)
class Profile:
    """One isolated LOCAL profile driven only through child processes of the public CLI."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.config, self.data = root / "config", root / "data"
        self.harness = root / "harness"
        self.harness.mkdir(parents=True)
        self.spy = self.harness / "spy.jsonl"
        self.runs = 0

    def environment(self) -> dict:
        environment = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(SOURCE_ROOT), "HOME": str(self.root),
                       "QUATI_CONFIG_DIR": str(self.config), "QUATI_DATA_DIR": str(self.data)}
        if "COVERAGE_PROCESS_START" in os.environ:      # opt-in subprocess coverage (tests/coverage/sitecustomize.py)
            environment["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
            environment["PYTHONPATH"] += os.pathsep + str(REPOSITORY_ROOT / "tests" / "coverage")
            for name in ("QUATI_TEST_COVERAGE_LIBRARY", "COVERAGE_FILE"):
                if name in os.environ:
                    environment[name] = os.environ[name]
        return environment

    def _run(self, command: list):
        completed = subprocess.run(command, capture_output=True, env=self.environment(), timeout=120, check=False)
        assert completed.stderr == b"", completed.stderr
        return completed.returncode, completed.stdout.decode("utf-8")

    def quati(self, *argv: str):
        """The product CLI exactly as installed; one JSON Response."""
        code, output = self._run([PYTHON, "-m", "quati", *argv])
        return code, json.loads(output)

    def model(self, script: list, *argv: str):
        """The public CLI in a fresh process whose model is the scripted adversary; raw stdout."""
        self.runs += 1
        scenario = self.harness / f"scenario-{self.runs}.json"
        scenario.write_text(json.dumps({"script": script}), encoding="utf-8")
        self.spy.unlink(missing_ok=True)
        return self._run([PYTHON, str(RUNNER), str(self.spy), str(scenario), *argv])

    def ask(self, script: list, text: str):
        code, output = self.model(script, "ask", "--json", "--", text)
        return code, json.loads(output), output

    def spied(self, kind: str) -> list:
        return [entry[1] for entry in (json.loads(line) for line in self.spy.read_text().splitlines())
                if entry[0] == kind]

    def audit(self) -> list[dict]:
        path = self.data / "capabilities" / "audit.jsonl"
        return [json.loads(line) for line in path.read_bytes().splitlines() if line] if path.exists() else []

    def identity_record(self) -> dict:
        return json.loads((self.config / "identity.json").read_text(encoding="utf-8"))


@pytest.fixture
def profile(tmp_path: Path) -> Profile:
    """``quati init``, one ENABLED read fixture and a probed scripted model (tools SUPPORTED)."""
    workspace = Profile(tmp_path / "profile")
    assert workspace.quati("init", "--json")[0] == 0
    code, value = workspace.quati("capabilities", "install-fixture", "calendar-read", "--enable-fixture", "--json")
    assert (code, value["data"]["lifecycle"]) == (0, "ENABLED")
    code, output = workspace.model([], "models", "probe", "--json")
    assert code == 0 and json.loads(output)["data"]["feature_report"]["features"]["tools"] == "SUPPORTED"
    return workspace


def receipt(value: dict) -> dict:
    _, digest, path = value["evidence_refs"][0].split(":", 2)
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    return json.loads(raw)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def decisions(events: list[dict]) -> list[tuple]:
    return [(event["operation"], event["decision"]["verdict"], event["decision"]["reason_code"],
             event["decision"]["action"]) for event in events if event["event"] == "authz.decided"]


# ----------------------------------------------------------------- F2: greeting-only text, hostile label
@pytest.mark.parametrize("text, reply", [
    ("Hi, how are you?", "Hello!"),                       # SOC-01's own phrase
    ("Olá, tudo bem?", "Olá!"),
    ("hello hello hello", "Hello!"),
    ("hello, this is urgent", "Hello!"),                  # SOC-01 negative: "urgent" in a greeting-only sentence
    ("Hi, how are you? This is urgent.", "Hello!"),
    ("URGENT: hi", "Hello!"),
    ("Bom dia! Isto é urgente.", "Olá!"),
])
def test_f2_soc_01_greeting_only_text_never_reaches_the_tool_loop_whatever_the_label(profile, text, reply):
    """The auditor's g3.py: the model labels a pure greeting as work, then searches, describes and invokes.

    Fix round 7 (LOG-0041 D1; S00_RUNTIME_CONTRACT "Displayed text and social outcomes" rule 2). Old: one
    classification request whose label was discarded (uncertainty MODEL_LABEL_NOT_SOCIAL, 4 script items
    left, one authorized catalog read for the receipt, an ask receipt with an empty trajectory). New: the
    model is not asked at all (5 items left), nothing is read from the registry and the receipt is the
    provider-free one."""
    before = len(profile.audit())
    code, value, _output = profile.ask(HOSTILE, text)
    data = value["data"]
    assert (code, value["status"], data["result_kind"], data["text"]) == (0, "SUCCEEDED", "GREETING", reply)
    assert (data["tool_calls"], data["commitment_id"], data["launched"]) == ([], None, False)
    assert value["uncertainties"] == [] and data["provider_used"] is False
    assert profile.spied("handler") == []                               # no capability executed
    assert profile.spied("request") == []                               # no model request at all
    assert profile.spied("script_left") == [5]                          # nothing of the script was requested
    assert profile.audit()[before:] == []                               # no registry read, no decision
    stored = receipt(value)
    assert stored["provider_used"] is False and "trajectory" not in stored


def test_f2_control_a_mixed_greeting_and_work_request_still_runs_the_tool_loop(profile):
    """The fix does not close the work path: the same script executes when the text asks for work."""
    code, value, _output = profile.ask(HOSTILE, "Hello, find my next appointment")
    assert (code, value["data"]["result_kind"]) == (0, "FIXTURE_RESULT")
    assert profile.spied("handler") == ["calendar-read"] and profile.spied("script_left") == [0]


@pytest.mark.parametrize("text, reply", [("How are you doing today?", "Hello!"), ("thanks!", "Hello!"),
                                         ("Wie geht es dir?", "Hallo!")])
def test_f2_f3_social_text_without_a_greeting_gets_no_tool_and_no_model_text(profile, text, reply):
    """Fix round 7 (LOG-0041 D1, reply language; replaces the NO_GREETING_TEMPLATE notice path). Old: the
    English no-action notice (text_source application_notice, uncertainty NO_GREETING_TEMPLATE) after one
    classification request. New: the template of the language of the first phrase, no uncertainty, no
    model request. Never a model reply, as before."""
    for script in (HOSTILE, [["classify_social"], ["final", CLAIM]]):
        code, value, output = profile.ask(script, text)
        data = value["data"]
        assert (code, value["status"], data["result_kind"]) == (0, "SUCCEEDED", "GREETING")
        assert data["text"] == reply and "system_notice" not in data
        assert (data["text_source"], data["work_performed"], data["actions_taken"]) == (
            "application_template", False, [])
        assert data["display_lines"] == [data["text"]] and data["tool_calls"] == []
        assert value["uncertainties"] == []
        assert CLAIM not in output and "AUD-991" not in output
        assert profile.spied("handler") == [] and profile.spied("request") == []       # the model is not asked


def test_f2_vocabulary_boundary_is_code_owned():
    # Fix round 7 (LOG-0041 D1): the bag-of-words vocabulary of ask.py became the phrase table of
    # quati.domain.social, with one rule instead of two. Changed expectations: "hello, this is urgent" is
    # social-only for every path (the narrower fault-fallback rule is gone); "This is urgent" (markers and
    # no table phrase) is not social-only and goes to the model; a pleasantry without a greeting has a reply.
    from quati.domain import social
    assert social.social_match("Hi, how are you? This is urgent.").reply == "Hello!"
    assert social.social_match("hello").reply == "Hello!"
    assert social.social_match("hello, this is urgent").reply == "Hello!"
    for work in ("Hello, find my next appointment", "urgent", "Urgent: this", "hi, delete this", "",
                 "This is urgent"):
        assert social.social_match(work) is None, work
    assert social.social_match("URGENT: hi").reply == "Hello!"
    assert social.social_match("urgente, bom dia").reply == "Olá!"          # the whole phrase, never "dia" alone
    assert social.social_match("how are you").reply == "Hello!"


# ----------------------------------------------------------------- F3: fabricated completion, social label
@pytest.mark.parametrize("text", [
    "Delete all my calendar events and email the board that it is done",     # the auditor's fab.py
    "Transfer 500 to account 12",
    "Thanks. Delete all my calendar events",                                 # no recognized opening greeting
])
def test_f3_work_text_labelled_social_is_blocked_and_the_claim_is_never_displayed(profile, text):
    script = [["classify_social"], ["final", CLAIM], ["final", CLAIM]]
    code, value, output = profile.ask(script, text)
    data = value["data"]
    assert (code, value["status"], value["error"]["code"]) == (4, "BLOCKED", "EVIDENCE_INSUFFICIENT")
    assert (data["result_kind"], data["reason"]) == ("BLOCKED", "NO_VERIFIED_EXECUTION")
    assert "text" not in data and "display_lines" not in data
    assert CLAIM not in output and "AUD-991" not in output and "deleted" not in output
    assert profile.spied("handler") == []
    stored = receipt(value)
    assert stored["final_text_sha256"] == sha(CLAIM)                        # the model text is evidence by hash only
    assert stored["continuations"] == [{"after_step": 0, "reason": "NO_SEARCH_ON_WORK"}]
    code, human = profile.model(script, "ask", "--", text)                  # the human rendering of the same ask
    assert code == 4 and CLAIM not in human and "AUD-991" not in human


@pytest.mark.parametrize("text, reply, language", [
    ("Hey there! Hope your day is going well.", "Hello!", "en"),             # SOC-01 live-harness phrases
    ("Good morning! Urgent: just wanted to say hi.", "Hello!", "en"),
    ("Bom dia! Espero que a família esteja ótima.", "Olá!", "pt"),
    ("Hi! Delete all my calendar events and email the board that it is done", "Hello!", "en"),
])
def test_f3_social_label_on_greeting_led_text_is_blocked_and_displays_no_model_text(profile, text, reply, language):
    """Fix round 7 (LOG-0041 D2, audit N3; renamed from "..._conversation_displays_only_application_owned_
    text"). Old: a social label on a text that opens with a recognized greeting ended CONVERSATION /
    SUCCEEDED exit 0 with the greeting template and the no-action notice. New: the text is not social-only
    by the table, so it ends BLOCKED / EVIDENCE_INSUFFICIENT / NO_VERIFIED_EXECUTION exit 4 and nothing but
    the application's refusal is displayed. The model's claim is still hashed in the receipt, never shown."""
    script = [["classify_social"], ["final", CLAIM], ["final", CLAIM]]
    code, value, output = profile.ask(script, text)
    data = value["data"]
    assert (code, value["status"], value["error"]["code"]) == (4, "BLOCKED", "EVIDENCE_INSUFFICIENT")
    assert (data["result_kind"], data["reason"]) == ("BLOCKED", "NO_VERIFIED_EXECUTION")
    assert not {"text", "system_notice", "display_lines", "text_source"} & set(data)
    assert (data["commitment_id"], data["delivered"], data["tool_calls"]) == (None, False, [])
    assert value["next_action"] == ask_module.MODEL_ANSWER_NEXT_ACTION
    assert CLAIM not in output and "AUD-991" not in output and "deleted" not in output
    assert profile.spied("handler") == [] and profile.spied("script_left") == [0]
    assert receipt(value)["final_text_sha256"] == sha(CLAIM)
    code, human = profile.model(script, "ask", "--", text)
    assert code == 4 and CLAIM not in human and "AUD-991" not in human


def test_f3_a_tool_call_or_a_single_reply_is_still_not_a_conversation(profile):
    code, value, output = profile.ask([["classify_social"], ["final", CLAIM]], "Hey there! Hope your day is going well.")
    assert (value["status"], value["data"]["result_kind"]) != ("SUCCEEDED", "CONVERSATION") and CLAIM not in output
    code, value, output = profile.ask([["classify_social"], ["search", "calendar"], ["final", CLAIM], ["final", CLAIM]],
                                      "Hey there! Hope your day is going well.")
    assert (code, value["data"]["result_kind"]) == (4, "BLOCKED") and CLAIM not in output


# ----------------------------------------------------------------- F4: public CLI, every registry operation
def test_f4_public_cli_registry_operations_are_authorized_and_logged(profile, tmp_path):
    record = profile.identity_record()
    package = profile.data / "fixture_sources" / "calendar-read"
    commands = [
        (("capabilities", "list", "--json"), "list", "read", 0),
        (("capabilities", "list", "--enabled", "--json"), "list", "read", 0),
        (("capabilities", "install-fixture", "mail-search", "--json"), "install_fixture", "manage", 0),
        (("capabilities", "install-fixture", "forecast-quick", "--enable-fixture", "--json"),
         "install_fixture", "manage", 0),
        (("capabilities", "install-fixture", "no-such-fixture", "--json"), "install_fixture", "manage", 2),
        (("capabilities", "install", str(package), "--json"), "install", "manage", 0),
        (("capabilities", "disable", "fixtures.mail-search@1.0.0", "--json"), "disable", "manage", 0),
        (("capabilities", "search", "next appointment calendar", "--json"), "search", "read", 0),
        (("capabilities", "describe", CAPABILITY, "--json"), "describe", "read", 0),
    ]
    for argv, operation, action, expected in commands:
        before = len(profile.audit())
        code, _value = profile.quati(*argv)
        assert code == expected, argv
        logged = [event for event in profile.audit()[before:] if event["event"] == "authz.decided"]
        assert len(logged) == 1, argv
        event = logged[0]
        assert event == profile.audit()[before]                         # decided and logged before anything else
        assert event["operation"] == operation
        assert event["decision"] == {
            "verdict": "ALLOW", "reason_code": "OK", "tenant_id": record["tenant_id"],
            "principal_id": record["principal_id"], "action": action,
            "resource_ref": f"registry:{record['tenant_id']}"}
        assert event["owner_space_id"] == record["organization_space_id"]     # the owner, not the request's space
        assert event["authorized_scope"]["readable_space_ids"] == [
            record["personal_space_id"], record["organization_space_id"]]
        assert (event["actor_id"], event["tenant_id"]) == (record["principal_id"], record["tenant_id"])


def test_f4_ask_session_catalog_read_is_authorized_once_per_ask(profile):
    before = len(profile.audit())
    code, value, _output = profile.ask(HOSTILE, "Find my next appointment")
    assert (code, value["data"]["result_kind"]) == (0, "FIXTURE_RESULT")
    # LOG-0044 X6: the grant is checked once before the first model call (operation ask_admission); the
    # catalog read of the receipt is still authorized once (operation ask).
    assert decisions(profile.audit()[before:]) == [
        ("ask_admission", "ALLOW", "OK", "read"),
        ("search", "ALLOW", "OK", "read"), ("describe", "ALLOW", "OK", "read"), ("invoke", "ALLOW", "OK", "read"),
        ("ask", "ALLOW", "OK", "read")]
    assert receipt(value)["digests"]["catalog_digest"] is not None


# ----------------------------------------------------------------- F4/F5: public CLI, signed GUEST record
def resign(profile: Profile, **changes) -> dict:
    """Rewrite the installation record with the real device key (the local trust anchor): a state a
    public CLI process can be in, without touching any code path."""
    record = profile.identity_record()
    record.pop("signature")
    record.update(changes)
    key = Ed25519PrivateKey.from_private_bytes((profile.config / "device.key").read_bytes())
    signed = dict(record, signature=base64.b64encode(key.sign(canonical_bytes(record))).decode("ascii"))
    path = profile.config / "identity.json"
    path.write_bytes(canonical_bytes(signed))
    os.chmod(path, 0o600)
    return record


def assert_denied(code: int, value: dict, reason: str) -> None:
    assert code == 4
    assert (value["status"], value["error"]["code"], value["error"]["message"]) == ("DENIED", "FORBIDDEN", reason)
    assert value["data"] == {"reason": reason} and value["evidence_refs"] == []
    assert SPACE_GRANT_COMMAND in value["next_action"]


def protected(profile: Profile) -> dict:
    """Registry state, packages, lock and fixture sources: unchanged by any denied operation."""
    return {str(path.relative_to(profile.data)): path.read_bytes() for path in sorted(profile.data.rglob("*"))
            if path.is_file() and path.name != "audit.jsonl" and "receipts" not in path.parts}


def test_f4_f5_public_cli_denies_a_principal_without_a_grant_on_the_registry_space(profile):
    """RFC-013 section 2.1: a GUEST holds no ORGANIZATION grant. The registry belongs to the tenant's
    organization space, so every registry read and write of the public CLI is denied and logged."""
    record = resign(profile, tenant_role="GUEST")
    state, receipts = protected(profile), sorted((profile.data / "receipts").iterdir())
    package = profile.data / "fixture_sources" / "calendar-read"
    denied = [
        (("capabilities", "list", "--json"), "list", "read"),
        (("capabilities", "search", "next appointment calendar", "--json"), "search", "read"),
        (("capabilities", "describe", CAPABILITY, "--json"), "describe", "read"),
        (("capabilities", "install-fixture", "mail-search", "--enable-fixture", "--json"), "install_fixture", "manage"),
        (("capabilities", "install-fixture", "no-such-fixture", "--json"), "install_fixture", "manage"),
        (("capabilities", "install", str(package), "--json"), "install", "manage"),
        (("capabilities", "disable", f"{CAPABILITY}@1.0.0", "--json"), "disable", "manage"),
    ]
    for argv, operation, action in denied:
        before = len(profile.audit())
        code, value = profile.quati(*argv)
        assert_denied(code, value, "NO_SPACE_GRANT")
        output = json.dumps(value)
        assert CAPABILITY not in output and record["organization_space_id"] not in output
        appended = profile.audit()[before:]
        assert [event["event"] for event in appended] == ["authz.decided"], argv      # nothing else happened
        event = appended[0]
        assert event["operation"] == operation and event["owner_space_id"] == record["organization_space_id"]
        assert event["decision"] == {
            "verdict": "DENY", "reason_code": "NO_SPACE_GRANT", "tenant_id": record["tenant_id"],
            "principal_id": record["principal_id"], "action": action,
            "resource_ref": f"registry:{record['tenant_id']}"}
        assert event["authorized_scope"]["readable_space_ids"] == [record["personal_space_id"]]
    assert protected(profile) == state and sorted((profile.data / "receipts").iterdir()) == receipts

    # The ask of the same principal (LOG-0044 X6, M01 "Data directory" rule 2): refused by the
    # AuthorizationPort before the first model call, so no tool call exists, nothing executes and no
    # catalog is read. Before, the model was called and each of its three tool calls was denied.
    before = len(profile.audit())
    code, value, output = profile.ask(HOSTILE, "Find my next appointment")
    assert code == 4 and value["status"] == "DENIED" and value["data"]["reason"] == "NO_SPACE_GRANT"
    assert value["data"]["tool_calls"] == [] and value["data"]["provider_used"] is False
    assert profile.spied("handler") == [] and profile.spied("request") == []
    assert decisions(profile.audit()[before:]) == [("ask_admission", "DENY", "NO_SPACE_GRANT", "read")]
    stored = receipt(value)
    assert "catalog_digest" not in stored["digests"] and stored["provider_used"] is False
    assert protected(profile) == state

    # Control: the OWNER record of the same installation is allowed again (the denial was the grant).
    resign(profile, tenant_role="OWNER")
    code, value = profile.quati("capabilities", "list", "--json")
    assert code == 0 and [item["capability_id"] for item in value["data"]["capabilities"]] == [CAPABILITY]


@pytest.mark.parametrize("role, reads, reason", [("MEMBER", 0, "ROLE_INSUFFICIENT"), ("ADMIN", 0, None),
                                                 ("SUPERUSER", 4, "NO_SPACE_GRANT"), (7, 4, "NO_SPACE_GRANT")])
def test_f4_registry_writes_need_the_owner_or_admin_tenant_role(profile, role, reads, reason):
    """RFC-013 section 6 (admin separation): capabilities are managed by OWNER/ADMIN; a MEMBER reads only.
    An unknown role value is no membership at all: no grant, default deny."""
    resign(profile, tenant_role=role)
    state = protected(profile)
    code, value = profile.quati("capabilities", "list", "--json")
    assert code == reads
    for argv in (("capabilities", "install-fixture", "mail-search", "--enable-fixture", "--json"),
                 ("capabilities", "disable", f"{CAPABILITY}@1.0.0", "--json")):
        before = len(profile.audit())
        code, value = profile.quati(*argv)
        if reason is None:
            assert code == 0 and decisions(profile.audit()[before:])[0][1:] == ("ALLOW", "OK", "manage")
            continue
        assert_denied(code, value, reason)
        assert [event["event"] for event in profile.audit()[before:]] == ["authz.decided"]
        assert decisions(profile.audit()[before:]) == [(argv[1].replace("-", "_"), "DENY", reason, "manage")]
    if reason is not None:
        assert protected(profile) == state


# ----------------------------------------------------------------- F4/F5: in-process (auditor's partb.py)
class NoGrants(LocalIdentity):
    """The auditor's directory: the real verified principal with an empty SpaceGrant directory."""

    def space_grants(self, context):
        return ()


class FixedClock:
    def __call__(self) -> datetime:
        return datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)


def test_f4_partb_principal_with_zero_grants_cannot_use_any_registry_command(profile, monkeypatch):
    monkeypatch.setenv("QUATI_DATA_DIR", str(profile.data))
    monkeypatch.delenv("QUATI_CAPABILITY_CONTEXT", raising=False)
    receipts: list[dict] = []

    def sink(record: dict) -> dict:
        receipts.append(record)
        return {"sha256": "0" * 64, "path": "memory"}

    commands = composition.capability_commands(NoGrants(profile.config), sink, clock=FixedClock())
    reads: list[str] = []
    for name in ("catalog", "record", "records", "install", "transition"):
        original = getattr(commands.registry, name)
        setattr(commands.registry, name, lambda *a, _n=name, _o=original, **k: (reads.append(_n), _o(*a, **k))[1])
    state, before = protected(profile), len(profile.audit())
    calls = [("search", lambda: commands.search("next appointment calendar")),
             ("describe", lambda: commands.describe(CAPABILITY)),
             ("list", lambda: commands.list()),
             ("install_fixture", lambda: commands.install_fixture("mail-search", enable_fixture=True)),
             ("install", lambda: commands.install(str(profile.data / "fixture_sources" / "calendar-read"))),
             ("disable", lambda: commands.disable(f"{CAPABILITY}@1.0.0"))]
    for _operation, call in calls:
        code, value = call()
        assert_denied(code, value, "NO_SPACE_GRANT")
    assert reads == [] and receipts == [] and protected(profile) == state
    assert decisions(profile.audit()[before:]) == [
        (operation, "DENY", "NO_SPACE_GRANT", "read" if operation in ("search", "describe", "list") else "manage")
        for operation, _call in calls]


def test_f4_ask_session_never_reads_the_catalog_without_the_grant(tmp_path, monkeypatch):
    """AskSession.digests()/finish(): the receipt's catalog read is authorized like any other read.

    Fix round 7 (LOG-0041 D1, setup and outcome): the greeting "Bom dia, tudo bem com você?" no longer
    reaches the ask session (it was GREETING "Olá!" after one classification), so the same catalog-read
    assertions are made on a text that is not social-only, which ends BLOCKED NO_VERIFIED_EXECUTION."""
    harness = Harness(tmp_path, monkeypatch, Script(classified(SOCIAL), final("x"), final("x")))
    harness.install("calendar-read")
    assert harness.probe()[0] == 0
    harness.identity = NoGrants(tmp_path / "config")          # the same installation, an empty grant directory
    harness.service = harness.build_service()
    reads: list[str] = []
    runtime = harness.runtime

    def counted(context):
        built = runtime(context)
        original = built.registry.catalog
        built.registry.catalog = lambda *a, **k: (reads.append("catalog"), original(*a, **k))[1]
        return built

    harness.service.ask_runtime = counted
    store = FileRegistryStore(tmp_path / "data" / "capabilities")
    before = len(store.audit_events())
    code, value = harness.ask("Bom dia, como está o projeto?", synthetic=True)
    # LOG-0044 X6: without the grant the ask is refused before the first model call (operation
    # ask_admission), so the model is never asked and no catalog read is even attempted; before, the turn
    # ran, ended NO_VERIFIED_EXECUTION and its catalog read (operation ask) was denied.
    assert (code, value["data"]["result_kind"], value["data"]["reason"]) == (4, "BLOCKED", "NO_SPACE_GRANT")
    assert (value["status"], value["error"]["code"]) == ("DENIED", "FORBIDDEN")
    assert reads == [] and harness.script.model_requests() == []
    stored = receipt_of(value)
    assert "catalog_digest" not in stored["digests"] and "synthetic_evidence" not in stored
    assert decisions(store.audit_events()[before:]) == [("ask_admission", "DENY", "NO_SPACE_GRANT", "read")]


def test_f4_ask_catalog_read_is_refused_when_its_decision_cannot_be_logged(tmp_path, monkeypatch):
    # Fix round 7 (LOG-0041 D1, setup and outcome): as above, a text that is not social-only (the greeting
    # was answered "Olá!" by the session; it is now answered before the session and reads no catalog).
    harness = Harness(tmp_path, monkeypatch, Script(classified(SOCIAL), final("x"), final("x")))
    harness.install("calendar-read")
    assert harness.probe()[0] == 0
    runtime = harness.runtime

    def unlogged(context):
        built = runtime(context)

        def failing(event: dict) -> None:
            raise OSError("audit store down")
        built.discovery.audit_sink = failing
        return built

    harness.service.ask_runtime = unlogged
    code, value = harness.ask("Bom dia, como está o projeto?")
    stored = receipt_of(value)
    assert (code, value["data"]["reason"]) == (4, "NO_VERIFIED_EXECUTION")
    assert stored["digests"]["catalog_digest"] is None and stored["catalog_access"] == "audit_unavailable"


# ----------------------------------------------------------------- F5: the port is required
class Directory:
    """A synthetic S00 directory for the port-level tests."""

    def __init__(self, grants=("SPACE-P", "SPACE-O"), role="OWNER", owner="SPACE-O") -> None:
        self.grants, self.role, self.owner = grants, role, owner

    def space_grants(self, context):
        return self._value(self.grants)

    def tenant_role(self, context):
        return self._value(self.role)

    def registry_space(self, tenant_id):
        return self._value(self.owner)

    @staticmethod
    def _value(value):
        if isinstance(value, Exception):
            raise value
        return value


def service(tmp_path: Path, **options) -> DiscoveryService:
    handlers = FixtureHandlerRegistry(FIXTURE_HANDLERS)
    registry = RegistryService(FileRegistryStore(tmp_path / "capabilities"), handlers, clock=FixedClock(),
                               ids=lambda prefix: f"{prefix}-1")
    return DiscoveryService(registry, Fts5CapabilityIndex(), handlers, policy_gate=None,
                            grants=StaticGrants(frozenset()), clock=FixedClock(), ids=lambda prefix: f"{prefix}-1",
                            **options)


def test_f5_the_authorization_port_is_required_and_never_replaced(tmp_path, profile, monkeypatch):
    with pytest.raises(TypeError):
        service(tmp_path / "a")                                           # no self-asserting fallback
    with pytest.raises(TypeError):
        service(tmp_path / "b", authorization=None)

    class Falsy:
        """A port object that is falsy must still be the port that decides."""
        calls = 0

        def __bool__(self) -> bool:
            return False

        def decide(self, context, action, resource_ref):
            type(self).calls += 1
            return ScopeAuthorization(Directory(grants=()), FixedClock()).decide(context, action, resource_ref)

    port = Falsy()
    built = service(tmp_path / "c", authorization=port)
    assert built.authorization is port
    context = LocalIdentity(profile.config).authenticate()
    result = built.begin_turn(context).search(context, "calendar")
    assert (result.status, result.reason, Falsy.calls) == ("DENIED", "NO_SPACE_GRANT", 1)


def test_f5_a_self_asserted_space_in_the_request_context_grants_nothing(profile):
    """The auditor's repro: a context that names a made-up space is not evidence of a grant, and the
    space named by the request never selects the resource that is checked."""
    from dataclasses import replace
    identity = LocalIdentity(profile.config)
    record = profile.identity_record()
    authorization = ScopeAuthorization(identity, FixedClock())
    forged = replace(identity.authenticate(), space_ids=("SPACE-I-MADE-UP",))
    evaluation = authorization.decide(forged, "read", "space:SPACE-I-MADE-UP")
    assert (evaluation.decision.verdict, evaluation.decision.reason_code) == ("DENY", "NO_SPACE_GRANT")
    assert "SPACE-I-MADE-UP" not in evaluation.scope.readable_space_ids
    resource = f"registry:{record['tenant_id']}"
    for context in (forged, replace(forged, space_ids=()), replace(forged, space_ids=(record["personal_space_id"],))):
        evaluation = authorization.decide(context, "read", resource)
        assert (evaluation.decision.verdict, evaluation.space_id) == ("ALLOW", record["organization_space_id"])


def test_f5_port_decision_table_for_the_registry_resource(profile):
    context = LocalIdentity(profile.config).authenticate()
    resource = f"registry:{context.tenant_id}"

    def decide(directory, action="read", ref=resource):
        evaluation = ScopeAuthorization(directory, FixedClock()).decide(context, action, ref)
        decision = evaluation.decision
        assert decision.to_json() == {
            "verdict": "ALLOW" if decision.reason_code == "OK" else "DENY", "reason_code": decision.reason_code,
            "tenant_id": context.tenant_id, "principal_id": context.actor_id, "action": action, "resource_ref": ref}
        return decision.reason_code, evaluation.space_id

    assert decide(Directory()) == ("OK", "SPACE-O")
    assert decide(Directory(), "manage") == ("OK", "SPACE-O")
    assert decide(Directory(role="ADMIN"), "manage") == ("OK", "SPACE-O")
    for role in ("MEMBER", "GUEST", None, "", "owner", OSError("directory down")):
        assert decide(Directory(role=role), "manage") == ("ROLE_INSUFFICIENT", "SPACE-O"), role
        assert decide(Directory(role=role)) == ("OK", "SPACE-O")                # reads need the grant only
    for action in ("write", "update", "delete", "READ", ""):
        assert decide(Directory(), action) == ("ROLE_INSUFFICIENT", "SPACE-O"), action
    # The grant on the owning space is checked first, for reads and writes alike.
    for grants in (("SPACE-P",), (), None, OSError("directory down"), "SPACE-O"):
        assert decide(Directory(grants=grants)) == ("NO_SPACE_GRANT", "SPACE-O"), grants
        assert decide(Directory(grants=grants), "manage") == ("NO_SPACE_GRANT", "SPACE-O"), grants
    # An owner that cannot be resolved is no grant: default deny.
    for owner in (None, "", 7, OSError("directory down")):
        assert decide(Directory(owner=owner)) == ("NO_SPACE_GRANT", None), owner
        assert decide(Directory(owner=owner), "manage") == ("NO_SPACE_GRANT", None), owner
    # Another tenant's registry is never this principal's resource (M02 authorization order row 4).
    other = "registry:01JD00000000000000000000TT"
    assert decide(Directory(), "read", other) == ("TENANT_MISMATCH", None)
    assert decide(Directory(), "manage", other) == ("TENANT_MISMATCH", None)
    assert decide(Directory(), "read", "registry:") == ("TENANT_MISMATCH", None)
    assert ScopeAuthorization(Directory(), FixedClock()).check(context, "read", resource).verdict == "ALLOW"


def test_f5_local_directory_reads_role_grants_and_registry_owner_from_the_signed_record(profile):
    from dataclasses import replace
    identity = LocalIdentity(profile.config)
    context, record = identity.authenticate(), profile.identity_record()
    personal, organization = record["personal_space_id"], record["organization_space_id"]
    assert "tenant_role" not in record                                   # `quati init` writes the OWNER default
    assert identity.tenant_role(context) == "OWNER"
    assert identity.space_grants(context) == (personal, organization)
    assert identity.registry_space(record["tenant_id"]) == organization
    assert identity.registry_space("01JD00000000000000000000TT") is None
    stranger = replace(context, actor_id="01JD00000000000000000000ZZ")
    assert identity.tenant_role(stranger) is None and identity.space_grants(stranger) == ()
    for role, grants in (("ADMIN", (personal, organization)), ("MEMBER", (personal, organization)),
                         ("GUEST", (personal,)), ("ROOT", ()), (None, ())):
        resign(profile, tenant_role=role)
        assert identity.tenant_role(context) == (role if role in ("ADMIN", "MEMBER", "GUEST") else None)
        assert identity.space_grants(context) == grants
        assert identity.registry_space(record["tenant_id"]) == organization


# ----------------------------------------------------------------- F15: --enable-fixture tells the truth
def summary(value: dict) -> tuple:
    return (value["status"], (value["error"] or {}).get("code"), value["data"].get("reason"),
            value["data"].get("lifecycle"))


def test_f15_enable_fixture_never_reports_success_for_a_record_that_is_not_enabled(profile):
    def enabled() -> list[str]:
        return [item["capability_id"] for item in profile.quati("capabilities", "list", "--enabled", "--json")[1][
            "data"]["capabilities"]]

    # A write fixture under the read ceiling: the same refusal every time (the auditor's repro).
    for attempt in range(3):
        code, value = profile.quati("capabilities", "install-fixture", "forecast-publish", "--enable-fixture", "--json")
        assert (code, summary(value)) == (4, ("DENIED", "FORBIDDEN", "EFFECT_ABOVE_CEILING", "DRAFT")), attempt
        assert value["data"].get("already_installed", False) is (attempt > 0)
    # An install with no handler cannot be enabled: refused on the first call and on every repeat.
    package = profile.root / "package"
    package.mkdir()
    source = (profile.data / "fixture_sources" / "calendar-read" / "capability.scs.json").read_text()
    (package / "capability.scs.json").write_text(source.replace(CAPABILITY, "evil.nohandler"))
    for attempt in range(2):
        code, value = profile.quati("capabilities", "install", str(package), "--enable-fixture", "--json")
        assert (code, summary(value)) == (2, ("BLOCKED", "INVALID_INPUT", "BINDING_CHECK_FAILED", "VALIDATED")), attempt
    # Naming a handler on the repeat does not help when it is not this capability's trusted handler.
    code, value = profile.quati("capabilities", "install", str(package), "--fixture-handler", "calendar-read",
                                "--enable-fixture", "--json")
    assert (code, summary(value)) == (4, ("DENIED", "FORBIDDEN", "HANDLER_IDENTITY_MISMATCH", "VALIDATED"))
    # A STAGED record is not enabled by a repeated install: typed conflict, nothing changed.
    code, value = profile.quati("capabilities", "install-fixture", "mail-search", "--json")
    assert (code, summary(value)) == (0, ("SUCCEEDED", None, None, "STAGED"))
    registry = (profile.data / "capabilities" / "registry.json").read_bytes()
    code, value = profile.quati("capabilities", "install-fixture", "mail-search", "--enable-fixture", "--json")
    assert (code, summary(value)) == (4, ("CONFLICT", "REVISION_CONFLICT", "INSTALLED_NOT_ENABLED", "STAGED"))
    assert value["data"]["already_installed"] is True and value["next_action"]
    assert (profile.data / "capabilities" / "registry.json").read_bytes() == registry
    # A DISABLED record is not re-enabled either.
    assert profile.quati("capabilities", "install-fixture", "forecast-quick", "--enable-fixture", "--json")[0] == 0
    assert profile.quati("capabilities", "disable", "fixtures.forecast-quick@1.0.0", "--json")[0] == 0
    code, value = profile.quati("capabilities", "install-fixture", "forecast-quick", "--enable-fixture", "--json")
    assert (code, summary(value)) == (2, ("BLOCKED", "INVALID_INPUT", "TRANSITION_NOT_ALLOWED", "DISABLED"))
    assert enabled() == [CAPABILITY]
    # Controls: the idempotent repeats that ARE true stay successful.
    code, value = profile.quati("capabilities", "install-fixture", "calendar-read", "--enable-fixture", "--json")
    assert (code, summary(value), value["data"]["already_installed"]) == (0, ("SUCCEEDED", None, None, "ENABLED"), True)
    code, value = profile.quati("capabilities", "install-fixture", "mail-search", "--json")
    assert (code, summary(value), value["data"]["already_installed"]) == (0, ("SUCCEEDED", None, None, "STAGED"), True)
    refused = [event for event in profile.audit() if event["event"] == "registry.install_refused"]
    assert [event["reason"] for event in refused] == [
        "EFFECT_ABOVE_CEILING", "EFFECT_ABOVE_CEILING", "BINDING_CHECK_FAILED", "HANDLER_IDENTITY_MISMATCH",
        "INSTALLED_NOT_ENABLED", "TRANSITION_NOT_ALLOWED"]
