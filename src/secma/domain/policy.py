"""Trusted fixture policy. Text and manifests cannot grant authority."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    actor_id: str
    tenant_id: str


class Policy:
    version = 's00-fixture-readonly/1'

    def authorize(self, principal: Principal, definition: dict, binding: dict) -> bool:
        return bool(
            principal.actor_id and principal.tenant_id == 'local'
            and definition.get('lifecycle') == 'enabled'
            and definition.get('effects') in {'none', 'read'}
            and definition.get('requires_approval') is False
            and set(definition.get('permissions', [])) <= {'fixture:read'}
            and binding.get('enabled') is True
            and binding.get('verification') == 'LOCAL'
            and binding.get('capability_id') == definition.get('id')
            and binding.get('capability_version') == definition.get('version')
            and binding.get('adapter_type') == 'mock'
        )
