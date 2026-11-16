"""S00 fix round 7: second independent audit (docs/audit/S00_FIX6_REAUDIT_2026-11-16.md).

Binding decisions discriminated here (docs/governance/LOG.md, LOG-0041):

* D1 (N3, N5, N6; SOC-01; S00-GATE-03 first half; M31-AT-01): a text that is social-only by the
  code-owned multilingual table is answered by application-owned text with no model call, and the
  outcome is identical in every provider state. An invalid active behavior package is the only
  exception, by the M01 exit-code precedence (CONFIG_INVALID, exit 2, before everything below it).
* D2 (N3): every other text is classified by the model; a social or simple-answer label on it ends
  BLOCKED / EVIDENCE_INSUFFICIENT / NO_VERIFIED_EXECUTION, exit 4, never SUCCEEDED.
* D3 (N9; M01-FR-02): ``data.launched`` is false in every S00 ask and chat response.
* D4 (N2; M15 invoke guard table): an id outside this turn's shortlist gets one reason whether it
  is unknown, malformed, hidden, disabled or merely not searched (no existence oracle).
* N17: the policy gate takes the tenant role from the identity directory (RFC-013 sections 6 and
  12.1; RFC-014 default deny), never an assumed OWNER; an empty model reply has no failure mode.

Proof tiers. Every behavior claim is observed on the public path in real child processes:
``python -m quati`` (L2 for the provider-free legs) or the public ``main`` with a SCRIPTED FAKE
model (``s00_fix7_runner.py``, L1; the scripted model is the adversary and is never evidence of a
real provider). The table and gate unit tests at the end are L1. No network, no ``QUATI_ALLOW_LIVE``.
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
from quati.application.code_identity import current_code_digest
from quati.application.identity import canonical_bytes
from quati.domain.canonical import digest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = Path(quati.__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent / "s00_fix7_runner.py"
PYTHON = str(Path(sys.executable).absolute())
sys.path.insert(0, str(Path(__file__).resolve().parent))

from s00_t03_support import ACTOR, TENANT, FakeClock, SeededIds, context, trusted_policy_state  # noqa: E402

CAPABILITY = "fixtures.calendar-read"
READ = [["search", "next appointment calendar"], ["describe", CAPABILITY], ["invoke", CAPABILITY, {"limit": 1}],
        ["final", "done"]]
HOSTILE = [["classify"], *READ]
CLAIM = "Done. All events were deleted and the board was notified. Verified by audit record AUD-991."
INVALID_CLASSIFICATION = [["classify_raw", {"intent": "x"}]] * 4
NO_MODEL_ANSWER = "S00 displays no model-written answers and no action was taken"

# (language, text, the deterministic reply). Languages without a reply template answer in English.
SAMPLES = [
    ("en", "hello", "Hello!"), ("en", "Hi, how are you?", "Hello!"), ("en", "Good day", "Hello!"),
    ("en", "Howdy", "Hello!"), ("en", "Hiya!", "Hello!"), ("en", "Greetings", "Hello!"), ("en", "yo", "Hello!"),
    ("en", "thanks", "Hello!"), ("en", "hello, this is urgent", "Hello!"), ("en", "URGENT: hi", "Hello!"),
    ("en", "Hi, how are you? This is urgent.", "Hello!"), ("en", "How are you doing today?", "Hello!"),
    ("pt", "Olá, tudo bem?", "Olá!"), ("pt", "tudo bem?", "Olá!"), ("pt", "Olá, isto é urgente", "Olá!"),
    ("pt", "Bom dia!", "Olá!"), ("pt", "Obrigado!", "Olá!"),
    ("es", "¡Hola! ¿Qué tal?", "¡Hola!"), ("es", "Buenos días", "¡Hola!"),
    ("fr", "Bonjour, ça va ?", "Bonjour!"), ("fr", "Salut", "Salut!"), ("fr", "Bonsoir", "Bonsoir!"),
    ("de", "Moin", "Hallo!"), ("de", "Guten Tag, wie geht es Ihnen?", "Hallo!"),
    ("de", "das ist dringend, hallo", "Hallo!"), ("de", "Wie geht es dir?", "Hallo!"),
    ("it", "Ciao, come stai?", "Ciao!"), ("it", "Buongiorno", "Buongiorno!"),
    ("nl", "Goedemorgen", "Hello!"), ("nl", "Hoi, hoe gaat het?", "Hello!"),
    ("tr", "Merhaba!", "Hello!"),
    ("ru", "Привет, как дела?", "Hello!"), ("ru", "Здравствуйте", "Hello!"),
    ("ja", "こんにちは", "Hello!"), ("ja", "おはよう", "Hello!"),
    ("zh", "你好", "Hello!"),
    ("ko", "안녕하세요", "Hello!"),
    ("hi", "Namaste", "Hello!"), ("hi", "नमस्ते", "Hello!"),
    ("ar", "مرحبا", "Hello!"), ("ar", "السلام عليكم", "Hello!"),
]
REQUIRED_LANGUAGES = {"en", "pt", "es", "fr", "de", "it", "nl", "tr", "ru", "ja", "zh", "ko", "hi", "ar"}
# Provider states of decision D1; each is (profile fixture name, script or None for no provider).
STATES = {
    "no_provider_configured": ("probed", None),
    "configured_not_probed": ("unprobed", HOSTILE),
    "probed_work_label": ("probed", HOSTILE),
    "probed_social_label": ("probed", [["classify_social"], ["final", CLAIM], ["final", CLAIM]]),
    "probed_model_unavailable": ("probed", []),
    "probed_invalid_classification": ("probed", INVALID_CLASSIFICATION),
}
ONE_SHOT = ["hello", "Hi, how are you?", "hello, this is urgent", "thanks", "tudo bem?", "こんにちは", "Merhaba!"]


def social_data(reply: str) -> dict:
    """The whole ``data`` object of a social-only answer, without the request and trace ids."""
    return {"commitment_id": None, "scope": "S00_T01_LOCAL_CLI", "provider_used": False, "tool_calls": [],
            "usage": {"cost_usd": None}, "received": True, "launched": False, "delivered": False,
            "result_status": "RESPONDED", "result_kind": "GREETING", "text": reply,
            "text_source": "application_template", "display_lines": [reply], "work_performed": False,
            "actions_taken": []}


# ----------------------------------------------------------------- harness (real child processes)
class Profile:
    """One isolated LOCAL profile driven only through child processes of the public CLI."""

    def __init__(self, root: Path, source_root: Path = SOURCE_ROOT) -> None:
        self.root, self.source_root = root, source_root
        self.config, self.data = root / "config", root / "data"
        self.harness = root / "harness"
        self.harness.mkdir(parents=True)
        self.spy = self.harness / "spy.jsonl"
        self.runs = 0

    def environment(self) -> dict:
        environment = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(self.source_root), "HOME": str(self.root),
                       "QUATI_CONFIG_DIR": str(self.config), "QUATI_DATA_DIR": str(self.data),
                       "PYTHONDONTWRITEBYTECODE": "1"}
        if "COVERAGE_PROCESS_START" in os.environ:      # opt-in subprocess coverage (tests/coverage/sitecustomize.py)
            environment["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
            environment["PYTHONPATH"] += os.pathsep + str(REPOSITORY_ROOT / "tests" / "coverage")
            for name in ("QUATI_TEST_COVERAGE_LIBRARY", "COVERAGE_FILE"):
                if name in os.environ:
                    environment[name] = os.environ[name]
        return environment

    def _run(self, command: list, stdin: bytes | None = None):
        completed = subprocess.run(command, capture_output=True, env=self.environment(), timeout=180, check=False,
                                   input=stdin)
        assert completed.stderr == b"", completed.stderr
        return completed.returncode, completed.stdout.decode("utf-8")

    def quati(self, *argv: str, stdin: bytes | None = None):
        """The product CLI exactly as installed; raw stdout."""
        return self._run([PYTHON, "-m", "quati", *argv], stdin)

    def command(self, *argv: str):
        code, output = self.quati(*argv)
        return code, json.loads(output)

    def model(self, script: list, *argv: str, stdin: bytes | None = None):
        """The public CLI in a fresh process whose model is the scripted adversary; raw stdout."""
        self.runs += 1
        scenario = self.harness / f"scenario-{self.runs}.json"
        scenario.write_text(json.dumps({"script": script}), encoding="utf-8")
        self.spy.unlink(missing_ok=True)
        return self._run([PYTHON, str(RUNNER), str(self.spy), str(scenario), *argv], stdin)

    def run(self, script: list | None, *argv: str, stdin: bytes | None = None):
        """``script`` None: no provider is configured at all (the plain product CLI)."""
        if script is None:
            self.spy.unlink(missing_ok=True)
            return self.quati(*argv, stdin=stdin)
        return self.model(script, *argv, stdin=stdin)

    def ask(self, script: list | None, text: str, *options: str):
        code, output = self.run(script, "ask", "--json", *options, "--", text)
        return code, json.loads(output), output

    def chat(self, script: list | None, lines: list[str]):
        """One ``quati chat --jsonl`` session: one Response per input line."""
        code, output = self.run(script, "chat", "--jsonl", stdin="".join(f"{line}\n" for line in lines).encode())
        values = [json.loads(line) for line in output.splitlines()]
        assert len(values) == len(lines), output
        return code, values, output

    def spied(self, kind: str) -> list:
        if not self.spy.exists():
            return []
        return [entry[1] for entry in (json.loads(line) for line in self.spy.read_text().splitlines())
                if entry[0] == kind]

    def audit(self) -> list[dict]:
        path = self.data / "capabilities" / "audit.jsonl"
        return [json.loads(line) for line in path.read_bytes().splitlines() if line] if path.exists() else []

    def install(self, name: str, *options: str) -> dict:
        return self.command("capabilities", "install-fixture", name, *options, "--json")[1]

    def probe(self) -> None:
        code, output = self.model([], "models", "probe", "--json")
        assert code == 0 and json.loads(output)["data"]["feature_report"]["features"]["tools"] == "SUPPORTED"


def new_profile(root: Path, *, probed: bool = True, source_root: Path = SOURCE_ROOT) -> Profile:
    """``quati init``, one ENABLED read fixture and (``probed``) a probed scripted model (tools SUPPORTED)."""
    workspace = Profile(root, source_root)
    assert workspace.command("init", "--json")[0] == 0
    assert workspace.install(CAPABILITY.split(".")[1], "--enable-fixture")["data"]["lifecycle"] == "ENABLED"
    if probed:
        workspace.probe()
    return workspace


@pytest.fixture(scope="module")
def probed(tmp_path_factory) -> Profile:
    """Shared by the tests that change neither the identity nor the registry."""
    return new_profile(tmp_path_factory.mktemp("probed") / "profile")


@pytest.fixture(scope="module")
def unprobed(tmp_path_factory) -> Profile:
    return new_profile(tmp_path_factory.mktemp("unprobed") / "profile", probed=False)


@pytest.fixture
def profile(tmp_path: Path) -> Profile:
    return new_profile(tmp_path / "profile")


def receipt(value: dict) -> dict:
    _, sha256, path = value["evidence_refs"][0].split(":", 2)
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha256
    return json.loads(raw)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable(value: dict) -> dict:
    """A Response without the per-request identifiers and the receipt reference."""
    data = {key: item for key, item in value["data"].items() if key not in ("request_id", "trace_id")}
    return {**value, "data": data, "evidence_refs": []}


def steps(value: dict) -> list[tuple]:
    return [(step["operation"], step["status"], step["reason"], step["handler_executed"])
            for step in value["data"]["tool_calls"]]


def assert_social(value: dict, reply: str) -> None:
    assert stable(value) == {"status": "SUCCEEDED", "data": social_data(reply), "evidence_refs": [],
                             "uncertainties": [], "next_action": None, "error": None}
    stored = receipt(value)
    assert (stored["provider_used"], stored["status"], stored["cost_usd"]) == (False, "SUCCEEDED", None)
    # Integration step A (LOG-0042 open item): every receipt carries the code digest, and a social receipt
    # carries no other digest (it was `"digests" not in stored` while only model-path receipts were bound).
    assert "trajectory" not in stored and "feature_gate" not in stored
    assert stored["digests"] == {"code_digest": current_code_digest()} and stored["result_kind"] == "GREETING"


def assert_no_model_and_no_registry_use(workspace: Profile, script: list | None, audit_before: int) -> None:
    assert workspace.audit()[audit_before:] == []           # no registry read, no policy decision, no tool
    if script is not None:
        assert workspace.spied("request") == [] and workspace.spied("handler") == []
        assert workspace.spied("script_left") == [len(script)]      # the model was never asked anything


# ----------------------------------------------------------------- D1: one outcome in every provider state
def test_d1_sample_table_covers_the_required_languages():
    assert {language for language, _text, _reply in SAMPLES} == REQUIRED_LANGUAGES
    assert len({text for _language, text, _reply in SAMPLES}) == len(SAMPLES)


@pytest.mark.parametrize("state", STATES)
def test_d1_chat_jsonl_answers_every_social_only_sample_identically_in_every_provider_state(state, request):
    """The whole sample table through ``quati chat --jsonl``: one process per provider state."""
    fixture, script = STATES[state]
    workspace = request.getfixturevalue(fixture)
    before = len(workspace.audit())
    code, values, output = workspace.chat(script, [text for _language, text, _reply in SAMPLES])
    assert code == 0
    for (_language, text, reply), value in zip(SAMPLES, values):
        assert stable(value)["data"] == social_data(reply), text
        assert_social(value, reply)
    assert CLAIM not in output
    assert_no_model_and_no_registry_use(workspace, script, before)


@pytest.mark.parametrize("language, text, reply", SAMPLES)
def test_d1_one_shot_ask_is_deterministic_whatever_a_probed_model_would_label(probed, language, text, reply):
    """The auditor's g3.py and a3_paths.py: a probed model that labels the greeting as work and then
    searches, describes and invokes is never asked anything."""
    before = len(probed.audit())
    code, value, _output = probed.ask(HOSTILE, text)
    assert code == 0
    assert_social(value, reply)
    assert_no_model_and_no_registry_use(probed, HOSTILE, before)


@pytest.mark.parametrize("state", [name for name in STATES if name != "probed_work_label"])
def test_d1_one_shot_ask_has_one_outcome_in_every_provider_state(state, request):
    fixture, script = STATES[state]
    workspace = request.getfixturevalue(fixture)
    replies = {text: reply for _language, text, reply in SAMPLES} | {"Merhaba!": "Hello!"}
    for text in ONE_SHOT:
        before = len(workspace.audit())
        code, value, _output = workspace.ask(script, text)
        assert code == 0, (state, text)
        assert_social(value, replies[text])
        assert_no_model_and_no_registry_use(workspace, script, before)


def test_d1_chat_jsonl_turn_equals_the_one_shot_ask(probed):
    lines = ["Hi, how are you?", "Olá, isto é urgente", "こんにちは"]
    _code, turns, _output = probed.chat(HOSTILE, lines)
    for line, turn in zip(lines, turns):
        assert stable(turn) == stable(probed.ask(HOSTILE, line)[1])


@pytest.fixture(scope="module")
def broken_tree(tmp_path_factory):
    """A scratch copy of the source tree (the repository is never modified) with a probed profile;
    returns (profile, statechart path, valid statechart text)."""
    tree = tmp_path_factory.mktemp("tree")
    for name in ("src", "examples", "contracts"):
        shutil.copytree(REPOSITORY_ROOT / name, tree / name, ignore=shutil.ignore_patterns("__pycache__"))
    workspace = new_profile(tree / "profile", source_root=tree / "src")
    chart = tree / "examples" / "statecharts" / "commitment.yaml"
    return workspace, chart, chart.read_text(encoding="utf-8")


def test_d1_n6_invalid_behavior_package_wins_by_the_m01_precedence_in_every_provider_state(broken_tree):
    """M01 exit table: CONFIG_INVALID (exit 2) precedes NOT_CONFIGURED (3), UNSUPPORTED (4) and the
    provider failures (5). The active behavior package is checked before the provider state is
    looked at, so a greeting and a work request get the same answer with and without a provider."""
    workspace, chart, valid = broken_tree
    invalid = valid.replace("guard: authorized_request, action: commit_receipt", "guard: always, action: commit_receipt")
    assert invalid != valid
    chart.write_text(invalid, encoding="utf-8")
    try:
        for text in ("hello", "Hi, how are you?", "Find my next appointment"):
            answers = []
            for script in (None, HOSTILE, [], INVALID_CLASSIFICATION):
                code, value, _output = workspace.ask(script, text)
                assert (code, value["status"], value["error"]["code"]) == (2, "BLOCKED", "CONFIG_INVALID"), (text, script)
                data = value["data"]
                assert (data["result_kind"], data["reason"]) == ("BLOCKED", "BEHAVIOR_PACKAGE_INVALID")
                assert data["diagnostics"] and all(item["path"] for item in data["diagnostics"])
                assert (data["provider_used"], data["launched"], data["tool_calls"]) == (False, False, [])
                assert "text" not in data
                if script is not None:
                    assert workspace.spied("request") == [] and workspace.spied("script_left") == [len(script)]
                answers.append(stable(value))
            assert all(answer == answers[0] for answer in answers), text     # identical in every provider state
    finally:
        chart.write_text(valid, encoding="utf-8")
    code, value, _output = workspace.ask(None, "hello")                      # control: the valid package again
    assert code == 0
    assert_social(value, "Hello!")


def test_d1_n6_runtime_compile_failure_is_the_same_typed_refusal(tmp_path, monkeypatch):
    """L1, in-process: a service built without the behavior check (the product always wires it) still
    refuses a work request with the same typed CONFIG_INVALID when the runtime cannot compile the
    active package, and still answers social-only text without building the runtime at all."""
    from quati.domain.diagnostics import ErrorCode, violation
    from s00_t04_support import Harness, Script, receipt_of
    script = Script()
    harness = Harness(tmp_path, monkeypatch, script)
    harness.install("calendar-read")
    assert harness.probe()[0] == 0
    asked, built = len(script.requests), []

    def failing(request_context):
        built.append(request_context.request_id)
        raise violation(ErrorCode.FORBIDDEN, "PROTECTED_EDGE", "transitions[1]", "the protected edge is unguarded", 3)

    harness.service.ask_runtime = failing
    code, value = harness.ask("Find my next appointment")
    data = value["data"]
    assert (code, value["status"], value["error"]["code"]) == (2, "BLOCKED", "CONFIG_INVALID")
    assert (data["result_kind"], data["reason"], data["launched"]) == ("BLOCKED", "BEHAVIOR_PACKAGE_INVALID", False)
    assert [(item["reason"], item["path"]) for item in data["diagnostics"]] == [("PROTECTED_EDGE", "transitions[1]")]
    assert value["uncertainties"] == ["FORBIDDEN PROTECTED_EDGE at transitions[1]"]
    assert receipt_of(value)["feature_gate"]["tools"] == "SUPPORTED" and len(built) == 1
    code, value = harness.ask("hello")
    assert (code, stable(value)["data"]) == (0, social_data("Hello!")) and len(built) == 1
    assert len(script.requests) == asked                                    # no model call in either ask


# ----------------------------------------------------------------- D2: no model-written answer in S00
@pytest.mark.parametrize("label", ["classify_social", "classify_simple"])
@pytest.mark.parametrize("text", [
    "Hey there! Hope your day is going well.",                               # round 6 CONVERSATION phrase
    "Hi! Delete all my calendar events and tell the board it is done",       # the auditor's a3_ask.py (N3)
    "Hello, investigate conversions",                                        # M01-AT-02 negative
    "Olá! Apague todos os eventos da minha agenda e avise a diretoria",
    "What is the capital of France?",
    "Hyvää päivää",                                                          # a greeting outside the table (N5)
    "Sawubona",
])
def test_d2_social_or_simple_answer_label_on_other_text_is_blocked_never_succeeded(probed, text, label):
    script = [[label], ["final", CLAIM], ["final", CLAIM]]
    before = len(probed.audit())
    code, value, output = probed.ask(script, text)
    data = value["data"]
    assert (code, value["status"], value["error"]["code"]) == (4, "BLOCKED", "EVIDENCE_INSUFFICIENT")
    assert (data["result_kind"], data["reason"], data["launched"]) == ("BLOCKED", "NO_VERIFIED_EXECUTION", False)
    assert NO_MODEL_ANSWER in value["next_action"]
    assert value["uncertainties"] == ["NO_VERIFIED_EXECUTION"]
    assert not {"text", "display_lines", "system_notice", "text_source"} & set(data)
    assert CLAIM not in output and "AUD-991" not in output and "deleted" not in output
    assert probed.spied("handler") == [] and probed.spied("script_left") == [0]
    assert not [event for event in probed.audit()[before:] if event["event"] == "policy.decided"]
    stored = receipt(value)
    assert stored["final_text_sha256"] == sha(CLAIM)                        # the model text is evidence by hash only
    assert stored["continuations"] == [{"after_step": 0, "reason": "NO_SEARCH_ON_WORK"}]
    assert stored["outcome"]["executed_capabilities"] == []


def test_d2_human_rendering_and_chat_jsonl_agree_with_the_one_shot_ask(probed):
    text = "Hi! Delete all my calendar events and tell the board it is done"
    script = [["classify_social"], ["final", CLAIM], ["final", CLAIM]]
    code, human = probed.model(script, "ask", "--", text)
    assert code == 4 and CLAIM not in human and "AUD-991" not in human
    one_shot = stable(probed.ask(script, text)[1])
    mixed = "Hi! What's my next appointment?"
    lines = ["Hi, how are you?", text, mixed]
    _code, turns, output = probed.chat([*script, *HOSTILE], lines)
    assert CLAIM not in output
    assert stable(turns[0])["data"] == social_data("Hello!")
    assert stable(turns[1]) == one_shot
    assert (turns[2]["status"], turns[2]["data"]["result_kind"]) == ("SUCCEEDED", "FIXTURE_RESULT")
    assert probed.spied("handler") == ["calendar-read"] and probed.spied("script_left") == [0]


def test_d2_mixed_greeting_and_work_labelled_work_continues_to_the_tool_loop(probed):
    code, value, _output = probed.ask(HOSTILE, "Hi! What's my next appointment?")
    assert (code, value["status"], value["data"]["result_kind"]) == (0, "SUCCEEDED", "FIXTURE_RESULT")
    assert steps(value) == [("search", "SUCCEEDED", None, False), ("describe", "SUCCEEDED", None, False),
                            ("invoke", "SUCCEEDED", None, True)]
    assert probed.spied("handler") == ["calendar-read"]
    assert value["data"]["launched"] is False                                # D3


def test_d2_work_label_without_an_execution_keeps_the_generic_next_action(probed):
    code, value, _output = probed.ask([["classify"], ["final", CLAIM], ["final", CLAIM]], "Find my next appointment")
    assert (code, value["data"]["reason"]) == (4, "NO_VERIFIED_EXECUTION")
    assert NO_MODEL_ANSWER not in value["next_action"]


@pytest.mark.parametrize("reply", ["", "   "])
def test_n17_an_empty_model_reply_has_no_failure_mode_of_its_own(probed, reply):
    """Round 6: an empty reply under a social label was exit 5 OUTPUT_INVALID EMPTY_SOCIAL_REPLY although
    the reply is never displayed. No outcome depends on the model's reply text any more."""
    script = [["classify_social"], ["final", reply], ["final", reply]]
    code, value, output = probed.ask(script, "Hey there! Hope your day is going well.")
    assert (code, value["status"], value["error"]["code"]) == (4, "BLOCKED", "EVIDENCE_INSUFFICIENT")
    assert value["data"]["reason"] == "NO_VERIFIED_EXECUTION" and "EMPTY_SOCIAL_REPLY" not in output
    full = [["classify_social"], ["final", CLAIM], ["final", CLAIM]]
    assert stable(value) == stable(probed.ask(full, "Hey there! Hope your day is going well.")[1])


# ----------------------------------------------------------------- D3: launched is false in S00
@pytest.mark.parametrize("script, text, kind", [
    (HOSTILE, "Find my next appointment", "FIXTURE_RESULT"),
    ([["classify"], ["search", "next appointment calendar"], ["invoke", "NONE_FITS", {}], ["final", "none"]],
     "Find my next appointment", "NO_CAPABILITY"),
    ([["classify"], ["final", CLAIM], ["final", CLAIM]], "Find my next appointment", "BLOCKED"),
    ([["classify"], ["search", "next appointment calendar"], ["describe", CAPABILITY],
      ["invoke", CAPABILITY, {"limit": "many"}], ["final", "x"]], "Find my next appointment", "BLOCKED"),
    ([], "Find my next appointment", "BLOCKED"),
])
def test_d3_launched_is_false_in_every_ask_and_chat_response(probed, script, text, kind):
    """M01-FR-02: S00 has no ledger, so no commitment and no work item can exist."""
    _code, value, _output = probed.ask(script, text)
    assert (value["data"]["result_kind"], value["data"]["launched"]) == (kind, False)
    assert (value["data"]["received"], value["data"]["delivered"], value["data"]["commitment_id"]) == (
        True, False, None)
    _code, turns, _output = probed.chat(script, [text])
    assert (turns[0]["data"]["result_kind"], turns[0]["data"]["launched"]) == (kind, False)


# ----------------------------------------------------------------- D4: one reason outside the shortlist
OUTSIDE = {
    "disabled": "fixtures.mail-search",              # installed, enabled, then disabled
    "staged_hidden": "fixtures.forecast-quick",      # installed without --enable-fixture
    "draft_hidden_write": "fixtures.forecast-publish",   # refused at install (EFFECT_ABOVE_CEILING), stays DRAFT
    "enabled_not_searched": "fixtures.forecast-lime",
    "unknown": "fixtures.does-not-exist",
    "malformed": "Not A Capability Id!",
}


@pytest.fixture(scope="module")
def catalog(tmp_path_factory) -> Profile:
    workspace = new_profile(tmp_path_factory.mktemp("catalog") / "profile")
    assert workspace.install("mail-search", "--enable-fixture")["data"]["lifecycle"] == "ENABLED"
    assert workspace.command("capabilities", "disable", "fixtures.mail-search@1.0.0", "--json")[0] == 0
    assert workspace.install("forecast-quick")["data"]["lifecycle"] == "STAGED"
    assert workspace.install("forecast-publish", "--enable-fixture")["data"]["lifecycle"] == "DRAFT"
    assert workspace.install("forecast-lime", "--enable-fixture")["data"]["lifecycle"] == "ENABLED"
    return workspace


def outside_script(capability_id: str) -> list:
    return [["classify"], ["search", "next appointment calendar"], ["describe", capability_id],
            ["invoke", capability_id, {"limit": 1}], ["final", "done"]]


def test_d4_invoke_and_describe_outside_the_shortlist_give_one_reason_whatever_the_id_is(catalog):
    """The auditor's a3_hidden.py: NOT_IN_SHORTLIST for a hidden id against NOT_A_CAPABILITY_ID for an
    unknown one told the model which hidden ids exist."""
    lifecycles = {item["capability_id"]: item["lifecycle"]
                  for item in catalog.command("capabilities", "list", "--json")[1]["data"]["capabilities"]}
    assert lifecycles == {CAPABILITY: "ENABLED", "fixtures.forecast-lime": "ENABLED",
                          "fixtures.forecast-publish": "DRAFT", "fixtures.forecast-quick": "STAGED",
                          "fixtures.mail-search": "DISABLED"}
    seen = {}
    for case, capability_id in OUTSIDE.items():
        before = len(catalog.audit())
        code, value, _output = catalog.ask(outside_script(capability_id), "Find my next appointment",
                                           "--synthetic-evidence")
        assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
            4, "DENIED", "FORBIDDEN", "NOT_IN_SHORTLIST"), case
        assert steps(value) == [("search", "SUCCEEDED", None, False), ("describe", "DENIED", "NOT_IN_SHORTLIST", False),
                                ("invoke", "DENIED", "NOT_IN_SHORTLIST", False)], case
        reference = "sha256:" + digest(capability_id)          # what the model supplied, never a registry key
        assert [step["capability_ref"] for step in value["data"]["tool_calls"]] == [None, reference, reference]
        assert catalog.spied("handler") == [] and catalog.spied("script_left") == [0]
        appended = catalog.audit()[before:]
        assert not [event for event in appended if event["event"] == "policy.decided"]
        errors = [event for event in appended if event["event"] == "discovery.selection_error"]
        logged = capability_id if case != "malformed" else reference     # free text is logged as a digest only
        assert [(event["reason"], event["capability_id"]) for event in errors] == [("NOT_IN_SHORTLIST", logged)]
        trajectory = receipt(value)["synthetic_evidence"]["trajectory"]
        assert [step["policy_verdict"] for step in trajectory] == [None, None, None]
        # What the model sees for the describe and the invoke, and the Response without the id digest.
        seen[case] = ([step["result"] for step in trajectory[1:]],
                      {**stable(value), "data": {**stable(value)["data"], "tool_calls": steps(value)}})
    assert all(view == seen["unknown"] for view in seen.values()), seen


def test_d4_control_a_shortlisted_id_still_executes_and_the_operator_describe_is_unchanged(catalog):
    code, value, _output = catalog.ask(outside_script(CAPABILITY), "Find my next appointment")
    assert (code, value["data"]["result_kind"]) == (0, "FIXTURE_RESULT") and catalog.spied("handler") == ["calendar-read"]
    # The operator command has no shortlist; a hidden id and an unknown id are equally not found.
    answers = [catalog.command("capabilities", "describe", OUTSIDE[case], "--json")
               for case in ("staged_hidden", "draft_hidden_write", "unknown", "malformed")]
    assert all(code == 4 and value["data"] == {"reason": "NOT_A_CAPABILITY_ID"} for code, value in answers)
    assert all(value == answers[0][1] for _code, value in answers)
    assert catalog.command("capabilities", "describe", "fixtures.forecast-lime", "--json")[0] == 0


# ----------------------------------------------------------------- N17: the policy gate reads the role
def resign(workspace: Profile, **changes) -> dict:
    """Rewrite the installation record with the real device key (the local trust anchor): a state a
    public CLI process can be in, without touching any code path."""
    path = workspace.config / "identity.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("signature")
    record.update(changes)
    key = Ed25519PrivateKey.from_private_bytes((workspace.config / "device.key").read_bytes())
    signed = dict(record, signature=base64.b64encode(key.sign(canonical_bytes(record))).decode("ascii"))
    path.write_bytes(canonical_bytes(signed))
    os.chmod(path, 0o600)
    return record


@pytest.mark.parametrize("role", ["MEMBER", "ADMIN"])
def test_n17_invoke_by_a_principal_that_is_not_the_owner_follows_the_policy_default_deny(profile, role):
    """RFC-013 section 12.1: a MEMBER or ADMIN holds the organization grant, so the registry reads pass
    the AuthorizationPort. RFC-014: the LOCAL default policy allows read effects to the tenant role
    OWNER only and denies everything else; the gate must see the principal's real role."""
    record = resign(profile, tenant_role=role)
    before = len(profile.audit())
    code, value, _output = profile.ask(HOSTILE, "Find my next appointment")
    assert (code, value["status"], value["error"]["code"], value["data"]["reason"]) == (
        4, "DENIED", "FORBIDDEN", "default_deny")
    assert steps(value) == [("search", "SUCCEEDED", None, False), ("describe", "SUCCEEDED", None, False),
                            ("invoke", "DENIED", "default_deny", False)]
    assert profile.spied("handler") == [] and value["data"]["launched"] is False
    decided = [event for event in profile.audit()[before:] if event["event"] == "policy.decided"]
    assert [(event["decision"]["verdict"], event["decision"]["reason_code"], event["actor_id"])
            for event in decided] == [("DENY", "default_deny", record["principal_id"])]

    resign(profile, tenant_role="OWNER")                                    # control: the denial was the role
    code, value, _output = profile.ask(HOSTILE, "Find my next appointment")
    assert (code, value["data"]["result_kind"]) == (0, "FIXTURE_RESULT") and profile.spied("handler") == ["calendar-read"]


def test_n17_guest_is_stopped_by_the_authorization_port_before_the_policy_gate(profile):
    resign(profile, tenant_role="GUEST")
    before = len(profile.audit())
    code, value, _output = profile.ask(HOSTILE, "Find my next appointment")
    assert code == 4 and steps(value)[-1] == ("invoke", "DENIED", "NO_SPACE_GRANT", False)
    assert not [event for event in profile.audit()[before:] if event["event"] == "policy.decided"]
    assert profile.spied("handler") == []


class Directory:
    def __init__(self, role) -> None:
        self.role, self.asked = role, []

    def tenant_role(self, request_context):
        self.asked.append(request_context.actor_id)
        if isinstance(self.role, Exception):
            raise self.role
        return self.role


def read_intent(gate, request_context):
    from quati.adapters.fixture_capabilities import LOCAL_READ_GRANTS, StaticGrants
    from quati.application.discovery import build_effect_intent
    return build_effect_intent(
        request_context, StaticGrants(LOCAL_READ_GRANTS).resolve(request_context), capability_id=CAPABILITY,
        capability_version="1.0.0", binding_id="b1", binding_version="0" * 64, effect_class="read", destinations=(),
        arguments={}, idempotency_key="k", effect_id="effect-1", policy_version=gate.policy_version())


@pytest.mark.parametrize("role, kind, verdict, reason", [
    ("OWNER", "HUMAN", "ALLOW", "read-own-spaces"),
    ("ADMIN", "HUMAN", "DENY", "default_deny"),
    ("MEMBER", "HUMAN", "DENY", "default_deny"),
    ("GUEST", "HUMAN", "DENY", "default_deny"),
    (None, "HUMAN", "DENY", "default_deny"),
    (OSError("unreadable"), "HUMAN", "DENY", "default_deny"),       # an unreadable membership is no role
    ("OWNER", "AGENT", "DENY", "default_deny"),                     # agents and services hold no tenant role
])
def test_n17_policy_gate_takes_the_tenant_role_from_the_directory(role, kind, verdict, reason):
    """L1 on the composed gate: the role is read from the directory at every decision."""
    from quati.adapters.policy_gate import LocalPolicyGate
    directory = Directory(role)
    state = trusted_policy_state()
    gate = LocalPolicyGate(lambda: state, clock=FakeClock(), ids=SeededIds(), directory=directory)
    request_context = context(kind=kind)
    decision = gate.decide(request_context, read_intent(gate, request_context))
    assert (decision.verdict, decision.reason_code) == (verdict, reason)
    assert directory.asked == ([ACTOR] if kind == "HUMAN" else [])


def test_n17_policy_gate_has_no_directory_free_construction():
    from quati.adapters.policy_gate import LocalPolicyGate
    state = trusted_policy_state()
    with pytest.raises(TypeError):
        LocalPolicyGate(lambda: state, clock=FakeClock(), ids=SeededIds())
    with pytest.raises(TypeError):
        LocalPolicyGate(lambda: state, clock=FakeClock(), ids=SeededIds(), directory=None)
    with pytest.raises(TypeError):
        LocalPolicyGate.from_config_dir(Path("."), tenant_id=TENANT, installation_uid=os.getuid(), clock=FakeClock(),
                                        ids=SeededIds())


# ----------------------------------------------------------------- D1: the code-owned table (L1)
def test_d1_table_is_data_with_unicode_aware_matching():
    from quati.domain import social
    for _language, text, reply in SAMPLES:
        found = social.social_match(text)
        assert found is not None and found.reply == reply, text
    assert {language for language, _reply, _phrases in social.SOCIAL_TABLE} >= REQUIRED_LANGUAGES
    assert social.social_match("ＨＥＬＬＯ").reply == "Hello!"                 # compatibility forms, any case
    assert social.social_match("BOM DIA").reply == "Olá!"
    assert social.social_match("İyi günler").language == "tr"                # Turkish dotted capital I
    assert social.social_match("hello 👋").reply == "Hello!"                 # symbols are separators
    assert social.social_match("नमस्ते!").language == "hi"                    # combining marks stay in the word
    assert social.words("c'est urgent, नमस्ते") == ("c", "est", "urgent", "नमस्ते")
    assert social.social_match("merci").reply == "Bonjour!"                  # no greeting: the language's template
    assert social.social_match("thanks, bom dia").reply == "Olá!"            # the first greeting decides
    assert social.social_match("bom dia, hello").reply == "Olá!"
    assert social.social_match("спасибо").reply == social.DEFAULT_REPLY == "Hello!"


@pytest.mark.parametrize("text", [
    "", "!!!", "urgent", "This is urgent", "Urgent: this",                   # markers alone ask for nothing social
    "Hello, find my next appointment", "hi, delete this", "Hi! What's my next appointment?",
    "Thanks. Delete all my calendar events", "Hey there! Hope your day is going well.",
    "que é isso?", "como é isso", "how is it", "is it going", "good", "you", "how",   # words of phrases, not phrases
    "hello, how is it", "oi, que é isso?", "hi you", "thanks, good", "bom dia, como é isso",    # a phrase plus such words
    "hello 5", "hello_world", "Hyvää päivää", "Sawubona", "こんにちは元気",
])
def test_d1_table_boundary_any_other_word_is_not_social_only(text):
    from quati.domain import social
    assert social.social_match(text) is None


def test_d1_table_invariants():
    from quati.domain import social
    phrases = social.PHRASES
    assert all(phrase and all(word == social.fold(word) for word in phrase) for phrase in phrases)
    assert not [phrase for phrase in phrases if all(word in social.MARKERS for word in phrase)]
    assert max(len(phrase) for phrase in phrases) == social.MAX_PHRASE_WORDS
    assert social.MARKERS >= {"urgent", "urgently", "urgente", "dringend", "this", "isto", "isso", "é", "esto",
                              "c", "est", "das", "ist", "è", "questo"}
    # A long text is segmented iteratively (no recursion limit) and still decided exactly.
    assert social.social_match("hello " * 20000).reply == "Hello!"
    assert social.social_match("hello " * 20000 + "delete everything") is None
