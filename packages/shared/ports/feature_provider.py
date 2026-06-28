"""Feature provider interface for Liquidity OS.

[WHY] Defines the contract for computing and retrieving derived market features.
      The domain defines what features are needed; infrastructure (Redis, etc.)
      provides the caching and computation implementation.

[OWNERSHIP] Domain layer — port interface.

[DEPENDENTS] Allowed: feature-store (implements), apps.analytics,
             agents.oracle, agents.navigator.
             Forbidden: infrastructure implementations in this file.

[EXAMPLE]
    from shared.ports.feature_provider import FeatureProvider

    class RedisFeatureProvider(FeatureProvider):
        async def get_volatility(self, pool: PoolAddress) -> float | None:
            # Redis query here
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.identifiers import PoolAddress


class FeatureProvider(ABC):
    """[WHY] Provides computed market features for pool analysis and rule evaluation.

    [OWNERSHIP] Domain layer — defines the contract for feature computation.

    [DEPENDENTS] Allowed: feature-store (implements), analytics, oracle, navigator.
                 Forbidden: shared, database (must go through ports).

    [EXAMPLE]
        provider = RedisFeatureProvider(redis_client)
        volatility = await provider.get_volatility(PoolAddress("7Ytt..."))
    """

    @abstractmethod
    async def get_volatility(self, pool: PoolAddress) -> float | None:
        """Get 24h volatility for a pool (0.0 - 1.0+)."""

    @abstractmethod
    async def get_volume_change(self, pool: PoolAddress) -> float | None:
        """Get volume change percentage (e.g., 0.15 = +15%)."""

    @abstractmethod
    async def get_liquidity_concentration(self, pool: PoolAddress) -> float | None:
        """Get liquidity concentration ratio (0.0 - 1.0)."""

    @abstractmethod
    async def get_spread(self, pool: PoolAddress) -> float | None:
        """Get bid-ask spread (e.g., 0.001 = 0.1%)."""

    @abstractmethod
    async def get_features(self, pool: PoolAddress) -> dict[str, float | None]:
        """Get all available features for a pool."""

    @abstractmethod
    async def invalidate(self, pool: PoolAddress) -> None:
        """Invalidate cached features for a pool (trigger recomputation)."""
