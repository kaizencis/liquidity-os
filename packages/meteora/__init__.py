"""Meteora DLMM Adapter Package.

[WHY] Provides Meteora API integration for Liquidity OS.
      Exports public API for consumers (collector, analytics).
[OWNERSHIP] Infrastructure layer — Meteora adapter.
[DEPENDENTS] Allowed: apps.collector, apps.analytics.
             Forbidden: shared, agents (must go through ports).
"""

from meteora.adapters import MeteoraPoolAdapter, MeteoraPositionAdapter
from meteora.client import MeteoraClient
from meteora.errors import MeteoraError, MeteoraNotFoundError
from meteora.settings import MeteoraSettings

__all__ = [
    # Settings
    "MeteoraSettings",
    # Client
    "MeteoraClient",
    # Adapters (implementing shared ports)
    "MeteoraPoolAdapter",
    "MeteoraPositionAdapter",
    # Errors
    "MeteoraError",
    "MeteoraNotFoundError",
]
