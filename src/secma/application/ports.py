"""Provider-neutral S00 boundary; never carries credentials or vendor types."""
from dataclasses import dataclass, field
import os
from typing import Protocol


class ProviderError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str = ''
    model: str = ''
    api_key_env: str = 'SECMA_API_KEY'
    allow_live: bool = False
    timeout_seconds: float = 30
    max_requests: int = 8
    max_tool_calls: int = 8
    max_output_tokens: int = 2048

    @classmethod
    def from_environment(cls):
        return cls(base_url=os.environ.get('SECMA_BASE_URL', ''),
                   model=os.environ.get('SECMA_MODEL', ''),
                   api_key_env=os.environ.get('SECMA_API_KEY_ENV', 'SECMA_API_KEY'),
                   allow_live=os.environ.get('SECMA_ALLOW_LIVE') == '1')


@dataclass
class ModelRun:
    text: str = ''
    classification: dict = field(default_factory=dict)
    calls: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    elapsed_seconds: float = 0
    provider_used: bool = False
    probe: dict = field(default_factory=dict)


class ModelPort(Protocol):
    def run(self, text: str, prompt: str, catalog) -> ModelRun: ...
    def probe(self) -> dict: ...
