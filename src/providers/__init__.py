"""Registry of supported LLM quota providers.

Add new providers here. Each entry is an instance of a ``QuotaProvider``
subclass; its ``name`` becomes the URL slug (e.g. /quota/<name>).
"""

from .base import QuotaMetrics, QuotaProvider, format_reset_info
from .zai import ZaiProvider

PROVIDERS = [
    ZaiProvider(),
]

PROVIDER_MAP = {provider.name: provider for provider in PROVIDERS}


def get_provider(name: str):
    """Return the provider instance for ``name``, or None if unknown."""
    return PROVIDER_MAP.get(name)


__all__ = [
    "PROVIDERS",
    "PROVIDER_MAP",
    "QuotaMetrics",
    "QuotaProvider",
    "format_reset_info",
    "get_provider",
]
