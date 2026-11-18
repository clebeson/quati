"""Pure, process-only conversation ownership and revision checks (S01-T01)."""
from dataclasses import dataclass, replace

from quati.domain.capability_registry import Refusal


@dataclass(frozen=True)
class ConversationProjection:
    id: str
    tenant_id: str
    actor_id: str
    revision: int = 0

    def __post_init__(self):
        if (any(not isinstance(value, str) or not value for value in (self.id, self.tenant_id, self.actor_id))
                or type(self.revision) is not int or self.revision < 0):
            raise ValueError('Invalid conversation projection')


def advance_conversation(projection, *, tenant_id, actor_id, expected_revision):
    if (projection.tenant_id, projection.actor_id) != (tenant_id, actor_id):
        raise Refusal('DENIED', 'FORBIDDEN', 'CONVERSATION_OWNER_MISMATCH')
    if type(expected_revision) is not int or expected_revision < 0:
        raise Refusal('BLOCKED', 'INVALID_INPUT', 'CONVERSATION_REVISION_INVALID')
    if projection.revision != expected_revision:
        raise Refusal('CONFLICT', 'REVISION_CONFLICT', 'CONVERSATION_REVISION_CONFLICT')
    return replace(projection, revision=projection.revision + 1)
