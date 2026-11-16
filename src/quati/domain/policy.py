"""M25 policy gate: kernel rules K2/K3/K5/K6/K8 and the RFC-014 section 4 evaluation.

Pure domain code. Authority comes only from the built-in kernel rules, the active
tenant policy document (trusted only after an audited adoption) and the identity
directory facts supplied by trusted code in ``PolicyContext``. Prompts, memory,
documents, tool results and behavior packages have no input channel here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from quati.domain.canonical import digest, is_digest
from quati.domain.diagnostics import ErrorCode, violation

EFFECTS = ("none", "read", "write", "dangerous")
DATA_CLASSES = ("PUBLIC_SYNTHETIC", "PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED")
INTEGRITY = ("TRUSTED", "UNTRUSTED")
SPACE_KINDS = ("PERSONAL", "TEAM", "ORGANIZATION", "SHARED")
PRINCIPAL_KINDS = ("HUMAN", "AGENT", "SERVICE")
RUNTIME_PROFILES = ("S00", "S01", "S02", "S03", "S04", "S05", "S06", "S07")
DEPLOYMENTS = ("LOCAL", "SERVER")
APPROVER_RANK = {"SELF": 0, "SPACE_MANAGER": 1, "TENANT_ADMIN": 2, "NAMED_PRINCIPALS": 3}
ADOPTING_ROLES = ("OWNER", "ADMIN")
DEFAULT_APPROVAL_TTL_S = 900
DEFAULT_DECISION_TTL_S = 60
DECISION_TTL_RANGE = (10, 300)

# Built-in kernel baseline (identical to the offline reference compiler TRUSTED_POLICY).
KERNEL_BASELINE_POLICY = {
    "id": "trusted_policy/default", "version": "1.0.0",
    "invariants": ["authenticated_identity", "authorization_before_effect",
                   "durable_commitment_before_receipt", "evidence_before_completion",
                   "acknowledgement_before_delivery", "no_self_granted_permissions"],
}
KERNEL_BASELINE_VERSION = digest(KERNEL_BASELINE_POLICY)

WIRE_FIELDS = ("effect_id", "actor_id", "tenant_id", "capability_id", "capability_version", "binding_id",
               "binding_version", "operation", "destination_ref", "policy_version", "idempotency_key",
               "input_digest", "effect_class", "data_class")


def policy_version(document: Any) -> str:
    """RFC-014: sha256 of the quati-json/1 canonical form of the policy document."""
    return digest(document)


def _slot_ok(slot: Any) -> bool:
    return (isinstance(slot, str) and 1 <= len(slot) <= 64 and slot[0] in "abcdefghijklmnopqrstuvwxyz"
            and all(c in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in slot))


@dataclass(frozen=True)
class TrustedPolicy:
    """A trusted policy slot and the version active in it; packages select the slot only."""

    slot: str
    policy_version: str

    def __post_init__(self) -> None:
        if not _slot_ok(self.slot):
            raise ValueError("policy slot must match [a-z][a-z0-9_-]{0,63}")
        if not is_digest(self.policy_version):
            raise ValueError("policy_version must be a sha256 hex digest")

    @property
    def ref(self) -> str:
        return f"trusted_policy/{self.slot}"


KERNEL_BASELINE = TrustedPolicy("default", KERNEL_BASELINE_VERSION)


@dataclass(frozen=True)
class PolicyContext:
    """Built by trusted code from the verified identity; never from model output."""

    tenant_id: str
    actor_id: str
    principal_kind: str
    tenant_role: str | None = None
    group_ids: tuple[str, ...] = ()


def _invalid(name: str, message: str = ""):
    return violation(ErrorCode.INVALID_INPUT, "intent_field_invalid", name, message or f"{name} is invalid")


@dataclass(frozen=True)
class EffectIntent:
    effect_id: str
    actor_id: str
    tenant_id: str
    capability_id: str
    capability_version: str
    binding_id: str
    binding_version: str
    operation: str
    destination_ref: str
    policy_version: str
    idempotency_key: str
    input_digest: str
    effect_class: str
    data_class: str
    integrity: str
    steering_args_user_confirmed: bool
    space_id: str | None = None
    space_kind: str | None = None
    declassification_space_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in WIRE_FIELDS[:12]:
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise _invalid(name)
        if not is_digest(self.input_digest):
            raise _invalid("input_digest")
        if self.effect_class not in EFFECTS:
            raise _invalid("effect_class")
        if self.data_class not in DATA_CLASSES:
            raise _invalid("data_class")
        if self.integrity not in INTEGRITY:
            raise _invalid("integrity")
        if type(self.steering_args_user_confirmed) is not bool:
            raise _invalid("steering_args_user_confirmed")
        if self.space_id is not None and (not isinstance(self.space_id, str) or not self.space_id):
            raise _invalid("space_id")
        if self.space_kind is not None and self.space_kind not in SPACE_KINDS:
            raise _invalid("space_kind")
        spaces = self.declassification_space_ids
        if not isinstance(spaces, tuple) or not all(isinstance(s, str) and s for s in spaces):
            raise _invalid("declassification_space_ids")

    def to_wire(self) -> dict:
        wire = {name: getattr(self, name) for name in WIRE_FIELDS}
        wire["data_class"] = self.data_class.lower()
        return wire

    @classmethod
    def from_wire(cls, wire: Mapping[str, Any], *, integrity: str, steering_args_user_confirmed: bool,
                  space_id: str | None = None, space_kind: str | None = None,
                  declassification_space_ids: tuple[str, ...] = ()) -> "EffectIntent":
        """Strict parse of the wire EffectIntent; provenance facts come from trusted code."""
        if not isinstance(wire, Mapping):
            raise _invalid("$", "EffectIntent must be an object")
        unknown = sorted(set(wire) - set(WIRE_FIELDS))
        if unknown:
            raise violation(ErrorCode.INVALID_INPUT, "intent_field_unknown", unknown[0], "unknown intent field")
        missing = [name for name in WIRE_FIELDS if name not in wire]
        if missing:
            raise violation(ErrorCode.INVALID_INPUT, "intent_field_missing", missing[0], "missing intent field")
        data_class = wire["data_class"]
        if not isinstance(data_class, str) or data_class.upper() not in DATA_CLASSES or data_class != data_class.lower():
            raise _invalid("data_class")
        values = {name: wire[name] for name in WIRE_FIELDS}
        values["data_class"] = data_class.upper()
        return cls(**values, integrity=integrity, steering_args_user_confirmed=steering_args_user_confirmed,
                   space_id=space_id, space_kind=space_kind, declassification_space_ids=declassification_space_ids)


def reconcile_intent(recomputed: EffectIntent, supplied: Mapping[str, Any]) -> EffectIntent:
    """A model-supplied field that differs from the trusted recomputation is refused."""
    wire = recomputed.to_wire()
    for name in sorted(supplied):
        if name not in wire:
            raise violation(ErrorCode.INVALID_INPUT, "intent_field_unknown", name, "unknown intent field")
        if supplied[name] != wire[name]:
            raise violation(ErrorCode.INVALID_INPUT, "intent_field_untrusted", name,
                            "supplied value differs from the trusted recomputation")
    return recomputed


@dataclass(frozen=True)
class PolicyFileSnapshot:
    """Bytes and metadata read from the policy file without following symlinks."""

    content: bytes | None
    mode: int | None
    owner_uid: int | None
    read_error: str | None = None


def _parse_instant(text: str) -> datetime:
    value = datetime.fromisoformat(text[:-1] + "+00:00" if text[-1:] in "Zz" else text)
    if value.tzinfo is None:
        raise ValueError("timestamp needs an offset")
    return value


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    verdict: str
    match: Mapping[str, Any]
    approver_rule: str | None
    principal_ids: tuple[str, ...]
    ttl_s: int
    expires_at: datetime | None

    @classmethod
    def from_document(cls, rule: Mapping[str, Any]) -> "PolicyRule":
        approver = rule.get("approver") or {}
        expires = rule.get("expires_at")
        return cls(rule_id=rule["rule_id"], verdict=rule["verdict"], match=dict(rule["match"]),
                   approver_rule=approver.get("rule"), principal_ids=tuple(approver.get("principal_ids", ())),
                   ttl_s=rule.get("approval_ttl_seconds", DEFAULT_APPROVAL_TTL_S),
                   expires_at=None if expires is None else _parse_instant(expires))


@dataclass(frozen=True)
class PolicyState:
    """The loader's verdict on the policy file; unavailable means K6 fail-closed."""

    available: bool
    cause: str | None
    tenant_id: str | None = None
    policy_version: str = KERNEL_BASELINE_VERSION
    observed_version: str | None = None
    document: Mapping[str, Any] | None = None
    rules: tuple[PolicyRule, ...] = ()

    @classmethod
    def unavailable(cls, cause: str) -> "PolicyState":
        return cls(False, cause)

    @classmethod
    def from_document(cls, document: Mapping[str, Any], *, tenant_id: str,
                      trusted_version: str | None) -> "PolicyState":
        """Apply the tenant and out-of-band checks to a schema-valid document."""
        if document["tenant_id"] != tenant_id:
            return cls.unavailable("wrong_tenant")
        rules = tuple(PolicyRule.from_document(rule) for rule in document["rules"])
        version = policy_version(document)
        if trusted_version is None or version != trusted_version:
            return cls(False, "out_of_band_change", tenant_id, KERNEL_BASELINE_VERSION, version, document, rules)
        return cls(True, None, tenant_id, version, version, document, rules)


@dataclass(frozen=True)
class ApprovalObligation:
    approver_rule: str
    reason_code: str
    ttl_s: int
    rule_id: str | None = None
    space_ids: tuple[str, ...] = ()
    principal_ids: tuple[str, ...] = ()


def _iso(instant: datetime) -> str:
    return instant.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class PolicyDecision:
    decision_id: str
    verdict: str
    reason_code: str
    policy_version: str
    decided_at: datetime
    valid_until: datetime
    intent_digest: str
    matched_rule_ids: tuple[str, ...] = ()
    obligations: tuple[ApprovalObligation, ...] = ()
    narrowed_scope: Mapping[str, str] | None = None

    def to_json(self) -> dict:
        return {
            "decision_id": self.decision_id, "verdict": self.verdict, "reason_code": self.reason_code,
            "policy_version": self.policy_version, "decided_at": _iso(self.decided_at),
            "valid_until": _iso(self.valid_until), "intent_digest": self.intent_digest,
            "matched_rule_ids": list(self.matched_rule_ids),
            "obligations": [{f.name: list(v) if isinstance(v := getattr(o, f.name), tuple) else v
                             for f in fields(o)} for o in self.obligations],
            "narrowed_scope": None if self.narrowed_scope is None else dict(self.narrowed_scope),
        }


def glob_match(pattern: str, value: str) -> bool:
    """Glob with only ``*`` and ``?`` (RFC-014 section 2); no regular expressions."""
    p = v = 0
    star = -1
    mark = 0
    while v < len(value):
        if p < len(pattern) and pattern[p] in ("?", value[v]) and pattern[p] != "*":
            p += 1
            v += 1
        elif p < len(pattern) and pattern[p] == "*":
            star, mark = p, v
            p += 1
        elif star >= 0:
            p = star + 1
            mark += 1
            v = mark
        else:
            return False
    while p < len(pattern) and pattern[p] == "*":
        p += 1
    return p == len(pattern)


def _matches(match: Mapping[str, Any], context: PolicyContext, intent: EffectIntent) -> bool:
    checks = {
        "capability_id": lambda m: glob_match(m, intent.capability_id),
        "effects": lambda m: intent.effect_class in m,
        "destination": lambda m: glob_match(m, intent.destination_ref),
        "max_data_class": lambda m: DATA_CLASSES.index(intent.data_class) <= DATA_CLASSES.index(m.upper()),
        "principal_ids": lambda m: context.actor_id in m,
        "group_ids": lambda m: any(group in m for group in context.group_ids),
        "tenant_roles": lambda m: context.tenant_role in m,
        "space_kinds": lambda m: intent.space_kind in m,
        "space_ids": lambda m: intent.space_id in m,
    }
    return all(checks[key](value) for key, value in match.items())


def evaluate(context: PolicyContext, intent: EffectIntent, policy_state: PolicyState, *, now: datetime,
             decision_id: str, runtime_profile: str, deployment: str = "LOCAL",
             decision_ttl_s: Any = DEFAULT_DECISION_TTL_S) -> PolicyDecision:
    """RFC-014 section 4. Deterministic, rule-order independent, default deny."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if runtime_profile not in RUNTIME_PROFILES:
        raise ValueError("unknown runtime profile")
    if deployment not in DEPLOYMENTS:
        raise ValueError("unknown deployment profile")
    intent_digest = digest(intent.to_wire())

    def deny(reason: str, version: str = policy_state.policy_version, matched=(), until=None) -> PolicyDecision:
        return PolicyDecision(decision_id, "DENY", reason, version, now, until or valid_until, intent_digest,
                              tuple(matched))

    ttl_ok = type(decision_ttl_s) is int and DECISION_TTL_RANGE[0] <= decision_ttl_s <= DECISION_TTL_RANGE[1]
    if not ttl_ok or not policy_state.available or policy_state.tenant_id != context.tenant_id:
        return deny("policy_unavailable", KERNEL_BASELINE_VERSION, until=now)   # K6
    valid_until = now + timedelta(seconds=decision_ttl_s)
    if intent.tenant_id != context.tenant_id or intent.actor_id != context.actor_id:
        return deny("intent_field_untrusted")
    if runtime_profile == "S00" and intent.effect_class in ("write", "dangerous"):
        return deny("s00_no_effects")                                            # K3
    scope = {"effect_id": intent.effect_id, "capability_id": intent.capability_id,
             "operation": intent.operation, "destination_ref": intent.destination_ref,
             "expires_at": _iso(valid_until)}
    if intent.effect_class == "none":
        return PolicyDecision(decision_id, "ALLOW", "no_effect", policy_state.policy_version, now, valid_until,
                              intent_digest, (), (), scope)

    matched = sorted((rule for rule in policy_state.rules
                      if (rule.expires_at is None or now < rule.expires_at)
                      and _matches(rule.match, context, intent)), key=lambda rule: rule.rule_id)
    matched_ids = tuple(rule.rule_id for rule in matched)
    denies = [rule for rule in matched if rule.verdict == "DENY"]
    if denies:
        return deny(denies[0].rule_id, matched=matched_ids)                      # deny wins

    required: list[ApprovalObligation] = []
    violating = intent.declassification_space_ids
    if violating:
        required.append(ApprovalObligation("SPACE_MANAGER", "declassification_required", DEFAULT_APPROVAL_TTL_S,
                                           space_ids=violating))                 # K5
    if intent.integrity == "UNTRUSTED" and not intent.steering_args_user_confirmed:
        required.append(ApprovalObligation("SELF", "untrusted_steering_argument", DEFAULT_APPROVAL_TTL_S))  # K8

    allows = [rule for rule in matched if rule.verdict == "ALLOW"]
    approvals = [ApprovalObligation(rule.approver_rule, rule.rule_id, rule.ttl_s, rule.rule_id,
                                    principal_ids=rule.principal_ids)
                 for rule in matched if rule.verdict == "APPROVAL_REQUIRED"]
    if intent.effect_class == "dangerous":                                       # K2
        allows = []
        if not approvals:
            approver = "TENANT_ADMIN" if deployment == "SERVER" else "SELF"
            approvals = [ApprovalObligation(approver, "dangerous_effect", DEFAULT_APPROVAL_TTL_S)]
    if approvals:
        required.append(min(approvals, key=lambda o: (-APPROVER_RANK[o.approver_rule], o.ttl_s, o.rule_id or "")))
    elif not allows and not violating:
        return deny("default_deny", matched=matched_ids)
    if required:
        return PolicyDecision(decision_id, "APPROVAL_REQUIRED", required[0].reason_code,
                              policy_state.policy_version, now, valid_until, intent_digest, matched_ids,
                              tuple(required))
    return PolicyDecision(decision_id, "ALLOW", allows[0].rule_id, policy_state.policy_version, now, valid_until,
                          intent_digest, matched_ids, (), scope)


# --------------------------------------------------------------------------- registry


@dataclass(frozen=True)
class PolicyVersionRecord:
    revision: int
    policy_version: str
    actor_id: str
    previous: str | None
    record_digest: str

    @staticmethod
    def seal(revision: int, version: str, actor_id: str, previous: str | None) -> "PolicyVersionRecord":
        body = {"revision": revision, "policy_version": version, "actor_id": actor_id, "previous": previous}
        return PolicyVersionRecord(revision, version, actor_id, previous, digest(body))

    def to_json(self) -> dict:
        return {"revision": self.revision, "policy_version": self.policy_version, "actor_id": self.actor_id,
                "previous": self.previous, "record_digest": self.record_digest}


def _registry_error(reason: str, message: str):
    return violation(ErrorCode.CONFIG_INVALID, reason, "$", message)


@dataclass(frozen=True)
class PolicyRegistry:
    """Immutable, append-only record of audited (adopted) policy versions for one tenant."""

    tenant_id: str
    revision: int = 0
    versions: tuple[PolicyVersionRecord, ...] = field(default=())

    @classmethod
    def empty(cls, tenant_id: str) -> "PolicyRegistry":
        return cls(tenant_id)

    @property
    def active_version(self) -> str | None:
        return self.versions[-1].policy_version if self.versions else None

    def to_json(self) -> dict:
        return {"tenant_id": self.tenant_id, "revision": self.revision,
                "versions": [record.to_json() for record in self.versions]}

    @classmethod
    def from_json(cls, document: Any) -> "PolicyRegistry":
        try:
            tenant_id, revision, raw = document["tenant_id"], document["revision"], document["versions"]
            if not isinstance(tenant_id, str) or type(revision) is not int or not isinstance(raw, list):
                raise TypeError("registry fields have the wrong type")
            records = tuple(PolicyVersionRecord(**item) for item in raw)
        except (KeyError, TypeError) as exc:
            raise _registry_error("registry_invalid", str(exc)) from None
        previous = None
        for index, record in enumerate(records):
            if record != PolicyVersionRecord.seal(index + 1, record.policy_version, record.actor_id, previous):
                raise _registry_error("registry_inconsistent", "registry history does not verify")
            previous = record.record_digest
        if revision != len(records):
            raise _registry_error("registry_inconsistent", "registry revision does not match its history")
        return cls(tenant_id, revision, records)


def adopt_policy(registry: PolicyRegistry, state: PolicyState, *, expected_revision: int, actor: PolicyContext,
                 interactive: bool, capability_context: bool) -> PolicyRegistry:
    """Trust a valid out-of-band policy: HUMAN owner/admin, interactive, outside any capability, CAS."""
    def refuse(reason: str, message: str):
        return violation(ErrorCode.FORBIDDEN, reason, "$", message)

    if actor.tenant_id != registry.tenant_id:
        raise refuse("wrong_tenant", "actor belongs to another tenant")
    if actor.principal_kind != "HUMAN":
        raise refuse("approver_not_human", "only a HUMAN principal may adopt a policy")
    if actor.tenant_role not in ADOPTING_ROLES:
        raise refuse("role_not_permitted", "only an OWNER or ADMIN may adopt a policy")
    if interactive is not True:
        raise refuse("not_interactive", "adoption requires an interactive confirmation")
    if capability_context is not False:
        raise refuse("capability_context", "adoption is refused inside a capability context")
    if state.document is None or state.tenant_id != registry.tenant_id or state.observed_version is None:
        raise refuse("policy_not_adoptable", f"policy is not adoptable: {state.cause}")
    if expected_revision != registry.revision:
        raise violation(ErrorCode.REVISION_CONFLICT, "REVISION_CONFLICT", "$", "stale registry revision")
    previous = registry.versions[-1].record_digest if registry.versions else None
    record = PolicyVersionRecord.seal(registry.revision + 1, state.observed_version, actor.actor_id, previous)
    return PolicyRegistry(registry.tenant_id, registry.revision + 1, registry.versions + (record,))
