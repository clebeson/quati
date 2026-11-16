"""Provider-neutral S00 configuration boundary; never carries credentials or vendor types."""
from dataclasses import dataclass
import os
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str = ''
    model: str = ''
    api_key_env: str = 'QUATI_API_KEY'
    allow_live: bool = False
    timeout_seconds: float = 60
    max_requests: int = 12
    max_tool_calls: int = 8
    max_output_tokens: int = 2048
    transport: str = 'anthropic'
    max_usd_per_run: float | None = None
    max_retries_429: int = 2
    retry_after_max_s: float = 30
    max_concurrency: int = 1
    ask_deadline_seconds: float | None = None  # may only lower the per-transport ask budget (S00-T04)

    @classmethod
    def from_environment(cls):
        return cls(base_url=os.environ.get('QUATI_BASE_URL', ''),
                   model=os.environ.get('QUATI_MODEL', ''),
                   api_key_env=os.environ.get('QUATI_API_KEY_ENV', 'QUATI_API_KEY'),
                   allow_live=os.environ.get('QUATI_ALLOW_LIVE') == '1',
                   transport=os.environ.get('QUATI_PROVIDER', '') or 'anthropic')


def valid_endpoint(endpoint: str) -> bool:
    """Single endpoint shape check shared by diagnostics and transport."""
    try:
        parts = urlsplit(endpoint)
        _ = parts.port
        return bool(parts.scheme == 'https' and parts.hostname and not parts.username and not parts.password
                    and not parts.query and not parts.fragment
                    and not any(c.isspace() or ord(c) < 32 for c in endpoint))
    except (ValueError, TypeError):
        return False
