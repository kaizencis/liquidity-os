"""Configuration for Meteora DLMM adapter.

[WHY] Centralizes all configuration for the Meteora adapter.
      Uses frozen dataclass for immutability.
[OWNERSHIP] Infrastructure layer — configuration.
[DEPENDENTS] Allowed: meteora.client.
             Forbidden: shared, apps, agents.
[EXAMPLE]
    from meteora.settings import MeteoraSettings

    settings = MeteoraSettings()
    assert settings.base_url == "https://dlmm.datapi.meteora.ag"
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeteoraSettings:
    """[WHY] Configuration for Meteora API client.
    [OWNERSHIP] Infrastructure layer — settings.
    [DEPENDENTS] Allowed: meteora.client.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        settings = MeteoraSettings(base_url="https://custom.api.com")
        client = MeteoraClient(settings)
    """

    base_url: str = "https://dlmm.datapi.meteora.ag"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_rps: int = 30

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))
