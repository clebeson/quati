"""Receipt-coordinated conversation projection; no transcript, worker or durable work."""
from copy import deepcopy

from quati.application.identity import AccessDenied, RequestContext
from quati.domain.capability_registry import Refusal
from quati.domain.conversation import ConversationProjection, advance_conversation


class ConversationSession:
    def __init__(self, *, ids):
        self._ids = ids
        self._projection = None
        self._prepared = None

    @property
    def projection(self):
        return self._projection

    def admit(self, context):
        if (not isinstance(context, RequestContext) or not all(isinstance(value, str) and value for value in (context.tenant_id, context.actor_id))):
            raise AccessDenied()
        if self._projection is not None:
            if (context.tenant_id, context.actor_id) != (self._projection.tenant_id, self._projection.actor_id):
                raise Refusal('DENIED', 'FORBIDDEN', 'CONVERSATION_OWNER_MISMATCH')

    def prepare(self, context, response):
        self.admit(context)
        if not isinstance(response, dict) or not isinstance(response.get('data'), dict):
            raise Refusal('BLOCKED', 'INVALID_INPUT', 'CONVERSATION_RESPONSE_INVALID')
        if self._projection is None:
            candidate = ConversationProjection(self._ids('conversation'), context.tenant_id, context.actor_id, 1)
        else:
            candidate = advance_conversation(self._projection, tenant_id=context.tenant_id,
                                             actor_id=context.actor_id, expected_revision=self._projection.revision)
        decorated = deepcopy(response)
        decorated['data']['conversation'] = dict(id=candidate.id, revision=candidate.revision,
                                                 lifetime='PROCESS_ONLY', continues_after_exit=False)
        self._prepared = candidate
        return candidate, decorated

    def commit(self, context, *, expected_revision, candidate):
        self.admit(context)
        if type(expected_revision) is not int or expected_revision < 0:
            raise Refusal('BLOCKED', 'INVALID_INPUT', 'CONVERSATION_REVISION_INVALID')
        current_revision = 0 if self._projection is None else self._projection.revision
        if current_revision != expected_revision:
            raise Refusal('CONFLICT', 'REVISION_CONFLICT', 'CONVERSATION_REVISION_CONFLICT')
        if self._prepared is None or candidate != self._prepared:
            raise Refusal('BLOCKED', 'INVALID_INPUT', 'CONVERSATION_PREPARE_MISMATCH')
        if (candidate.tenant_id, candidate.actor_id) != (context.tenant_id, context.actor_id):
            raise Refusal('DENIED', 'FORBIDDEN', 'CONVERSATION_OWNER_MISMATCH')
        self._projection = candidate
        self._prepared = None

    def discard(self):
        self._prepared = None
