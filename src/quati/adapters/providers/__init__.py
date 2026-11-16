"""Built-in M17 provider adapters. Importing this package registers every built-in transport.

To add a vendor: subclass ``quati.application.providers.Provider`` (or one of the
adapters here), implement ``_complete`` and decorate the class with ``@register``.
"""
from quati.adapters.providers.anthropic import AnthropicProvider
from quati.adapters.providers.cli import ClaudeCliProvider, CliProvider, CodexCliProvider, GeminiCliProvider
from quati.adapters.providers.openai_compatible import OpenAICompatibleProvider, OpenAIProvider

__all__ = ['AnthropicProvider', 'ClaudeCliProvider', 'CliProvider', 'CodexCliProvider', 'GeminiCliProvider',
           'OpenAICompatibleProvider', 'OpenAIProvider']
