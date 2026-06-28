"""Ports for reading pool and position data from external sources.

[WHY] Defines read-only interfaces for fetching pool and position data.
      Domain defines the contract; infrastructure (meteora) provides implementation.
[OWNERSHIP] Domain layer — port interfaces.
[DEPENDENTS] Allowed: meteora (implements), apps.collector, apps.analytics.
             Forbidden: shared (must go through ports).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.entities.pool import Pool
from shared.entities.position import Position
from shared.identifiers import PoolAddress, PositionAddress


class PoolReader(ABC):
    """[WHY] Port for reading pool data from external source.
    [OWNERSHIP] Domain layer — defines the contract for pool reading.
    [DEPENDENTS] Allowed: meteora (implements), collector, analytics.
                 Forbidden: shared, agents (must go through ports).
    [EXAMPLE]
        reader = MeteoraPoolAdapter(client)
        pool = await reader.get_pool(PoolAddress(value="7Ytt..."))
    """

    @abstractmethod
    async def get_pool(self, address: PoolAddress) -> Pool | None:
        """Fetch a single pool by address.

        Returns None if not found. Does not raise PoolNotFoundError.
        """

    @abstractmethod
    async def list_pools(self, limit: int = 100, page: int = 1) -> list[Pool]:
        """Fetch multiple pools.

        Args:
            limit: Number of pools per page (max 1000)
            page: Page number (1-based)
        """


class PositionReader(ABC):
    """[WHY] Port for reading position data from external source.
    [OWNERSHIP] Domain layer — defines the contract for position reading.
    [DEPENDENTS] Allowed: meteora (implements), collector, dashboard.
                 Forbidden: shared, agents (must go through ports).
    [EXAMPLE]
        reader = MeteoraPositionAdapter(client)
        positions = await reader.get_positions_by_pool(PoolAddress(value="7Ytt..."))
    """

    @abstractmethod
    async def get_positions_by_pool(self, pool_address: PoolAddress) -> list[Position]:
        """Fetch all positions for a pool."""
