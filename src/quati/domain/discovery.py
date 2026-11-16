"""Bounded capability discovery rules (M15): hard filters before ranking, deterministic
ranking, invoke guard order, and the honest no-capability choice.

Ranking scores come from an index port; everything else here is pure. Capability text
never takes part in a filter decision.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping

from quati.domain.capability_registry import CAPABILITY_ID_PATTERN, effect_above, semver_key
from quati.domain.policy import DATA_CLASSES

SEARCH_DEFAULT_LIMIT = 5
SEARCH_MAX_LIMIT = 5
MAX_SHORTLIST_K = 8
EFFECTIVE_SHORTLIST_K = min(MAX_SHORTLIST_K, SEARCH_MAX_LIMIT)   # 5 in S00 (M15 ranking)
QUERY_MAX_CHARS = 512
MAX_BINDING_FALLBACKS = 1
MAX_TOOL_CALLS_PER_TURN = 6
NONE_FITS = "NONE_FITS"
REPORT_NO_CAPABILITY = "report_no_capability"
FILTERS = ("NOT_ENABLED", "DIGEST_MISMATCH", "NOT_AUTHORIZED", "EFFECT_ABOVE_CEILING",
           "DATA_CLASS_ABOVE_CEILING", "BINDING_UNHEALTHY", "MODEL_INCOMPATIBLE", "COST_ABOVE_CAP")
# reason -> (response status, error code); the M15 invoke guard table.
REFUSALS = {
    "TOOL_CALL_MALFORMED": ("BLOCKED", "OUTPUT_INVALID"),
    "CONTEXT_MISMATCH": ("DENIED", "FORBIDDEN"),
    "BUDGET_EXCEEDED": ("BLOCKED", "BUDGET_EXCEEDED"),
    "QUERY_TOO_LONG": ("BLOCKED", "INVALID_INPUT"),
    "NOT_A_CAPABILITY_ID": ("DENIED", "NOT_FOUND"),
    "NOT_IN_SHORTLIST": ("DENIED", "FORBIDDEN"),
    "DESCRIBE_REQUIRED": ("BLOCKED", "INVALID_INPUT"),
    "NOT_ENABLED": ("UNAVAILABLE", "UNSUPPORTED"),
    "DIGEST_MISMATCH": ("UNAVAILABLE", "CONFIG_INVALID"),
    "MODEL_INCOMPATIBLE": ("UNAVAILABLE", "UNSUPPORTED"),
    "NOT_AUTHORIZED": ("DENIED", "FORBIDDEN"),
    "EFFECT_ABOVE_CEILING": ("DENIED", "FORBIDDEN"),
    "DATA_CLASS_ABOVE_CEILING": ("DENIED", "FORBIDDEN"),
    "BINDING_UNHEALTHY": ("UNAVAILABLE", "TEMPORARILY_UNAVAILABLE"),
    "COST_ABOVE_CAP": ("DENIED", "BUDGET_EXCEEDED"),
    "ARGUMENTS_SCHEMA_INVALID": ("BLOCKED", "INVALID_INPUT"),
    "BINDING_UNAVAILABLE": ("UNAVAILABLE", "TEMPORARILY_UNAVAILABLE"),
    "RESULT_SCHEMA_INVALID": ("BLOCKED", "OUTPUT_INVALID"),
    "HANDLER_FAILED": ("UNAVAILABLE", "INTERNAL_ERROR"),
    "OUTCOME_UNVERIFIED": ("PARTIAL", "EVIDENCE_INSUFFICIENT"),
    "EXECUTION_NOT_FOUND": ("DENIED", "NOT_FOUND"),
    "audit_unavailable": ("UNAVAILABLE", "TEMPORARILY_UNAVAILABLE"),
    "narrowed_scope_missing": ("DENIED", "FORBIDDEN"),
    "narrowed_scope_violation": ("DENIED", "FORBIDDEN"),
}
STOPWORDS = frozenset((
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "have", "how",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "our", "please", "should", "that", "the", "their", "this",
    "to", "us", "was", "we", "what", "when", "where", "which", "who", "will", "with", "you", "your"))
_TOKEN = re.compile(r"\w+")


@dataclass(frozen=True)
class ScopeGrant:
    """The authenticated principal's granted permissions and space, from trusted code only."""

    permissions: frozenset[str]
    space_id: str
    space_kind: str = "PERSONAL"
    input_data_class: str = "PUBLIC_SYNTHETIC"
    data_class_ceiling: str = "CONFIDENTIAL"


@dataclass(frozen=True)
class SearchScope:
    grant: ScopeGrant
    effect_ceiling: str = "read"
    model_features: frozenset[str] | None = None
    cost_cap: int | None = None


@dataclass(frozen=True)
class CatalogEntry:
    capability_id: str
    capability_version: str
    lifecycle: str
    loadable: bool
    enforced_effect: str
    permissions: tuple[str, ...]
    data_class_ceiling: str
    requires_models: tuple[str, ...]
    bindings_healthy: bool
    manifest: Mapping[str, Any] = field(compare=False, repr=False)
    cost_units: int = 0

    @property
    def key(self) -> str:
        return f"{self.capability_id}@{self.capability_version}"

    @property
    def search_text(self) -> str:
        manifest = self.manifest
        parts = [manifest["name"], manifest["description"], *manifest["intents"]["positive_examples"]]
        return "\n".join(parts)


def filter_reasons(entry: CatalogEntry, scope: SearchScope) -> tuple[str, ...]:
    """Every failing hard filter, in the fixed FILTERS order; empty means eligible."""
    grant = scope.grant
    features = scope.model_features
    failed = {
        "NOT_ENABLED": entry.lifecycle != "ENABLED",
        "DIGEST_MISMATCH": not entry.loadable,
        "NOT_AUTHORIZED": not set(entry.permissions) <= grant.permissions,
        "EFFECT_ABOVE_CEILING": effect_above(entry.enforced_effect, scope.effect_ceiling),
        "DATA_CLASS_ABOVE_CEILING": DATA_CLASSES.index(entry.data_class_ceiling)
        > DATA_CLASSES.index(grant.data_class_ceiling),
        "BINDING_UNHEALTHY": not entry.bindings_healthy,
        "MODEL_INCOMPATIBLE": bool(entry.requires_models) and (
            features is None or not set(entry.requires_models) <= features),
        "COST_ABOVE_CAP": scope.cost_cap is not None and entry.cost_units > scope.cost_cap,
    }
    return tuple(name for name in FILTERS if failed[name])


def latest_per_id(entries: list[CatalogEntry]) -> list[CatalogEntry]:
    """One eligible version per capability id: the highest semantic version."""
    best: dict[str, CatalogEntry] = {}
    for entry in entries:
        current = best.get(entry.capability_id)
        if current is None or semver_key(entry.capability_version) > semver_key(current.capability_version):
            best[entry.capability_id] = entry
    return [best[key] for key in sorted(best)]


def clamp_limit(limit: Any) -> int:
    if type(limit) is not int:
        return SEARCH_DEFAULT_LIMIT
    return max(1, min(limit, SEARCH_MAX_LIMIT))


def fold_text(text: str) -> str:
    """Unicode NFKD, combining marks (diacritics) removed, casefolded (amended M15 ranking rule)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def query_terms(query: str) -> tuple[str, ...]:
    seen: list[str] = []
    for token in _TOKEN.findall(fold_text(query)):
        if token not in STOPWORDS and token not in seen:
            seen.append(token)
    return tuple(seen)


def rank(survivors: list[CatalogEntry], scores: Mapping[str, float], limit: int) -> list[tuple[CatalogEntry, float]]:
    """bm25 ascending (lower is better), then capability id; unmatched survivors are dropped."""
    matched = [(entry, round(float(scores[entry.key]), 6)) for entry in survivors if entry.key in scores]
    matched.sort(key=lambda pair: (pair[1], pair[0].capability_id))
    return matched[:limit]


def rank_reasons(position: int, bm25: float, shortlist_k: int) -> dict:
    return {"filter_results": [f"{name}:PASS" for name in FILTERS], "bm25": bm25, "rank": position,
            "shortlist_k": shortlist_k}


def is_capability_id(value: Any) -> bool:
    return isinstance(value, str) and len(value) <= 128 and bool(CAPABILITY_ID_PATTERN.fullmatch(value))


@dataclass(frozen=True)
class Choice:
    verdict: str          # SELECTED | NO_CAPABILITY | SELECTION_ERROR
    capability_id: str | None = None
    arguments: Mapping[str, Any] | None = None
    reason: str | None = None


def resolve_choice(choice: Any, shortlist: tuple[str, ...]) -> Choice:
    """A model's choice is honoured only inside the trusted shortlist; NONE_FITS is honest."""
    if not isinstance(choice, Mapping) or not isinstance(choice.get("capability_id"), str) or not isinstance(
            choice.get("arguments", {}), Mapping):
        return Choice("SELECTION_ERROR", reason="TOOL_CALL_MALFORMED")
    capability_id = choice["capability_id"]
    if capability_id == NONE_FITS or not shortlist:
        return Choice("NO_CAPABILITY", reason=NONE_FITS if capability_id == NONE_FITS else "NO_CANDIDATES")
    if capability_id not in shortlist:
        return Choice("SELECTION_ERROR", capability_id, reason="NOT_IN_SHORTLIST")
    return Choice("SELECTED", capability_id, dict(choice.get("arguments", {})))


__all__ = ["EFFECTIVE_SHORTLIST_K", "fold_text", "CatalogEntry", "Choice", "FILTERS", "MAX_BINDING_FALLBACKS", "MAX_SHORTLIST_K",
           "MAX_TOOL_CALLS_PER_TURN", "NONE_FITS", "QUERY_MAX_CHARS", "REFUSALS", "REPORT_NO_CAPABILITY",
           "SEARCH_MAX_LIMIT", "ScopeGrant", "SearchScope", "clamp_limit", "filter_reasons",
           "is_capability_id", "latest_per_id", "query_terms", "rank", "rank_reasons", "resolve_choice"]
