"""Position repository interface for Liquidity OS.

[WHY] Defines the contract for position persistence. The domain defines what
      operations are needed; infrastructure (database) provides the implementation.

[OWNERSHIP] Domain layer — port interface.

[DEPENDENTS] Allowed: database (implements), apps.collector, apps.dashboard,
             agents.navigator.
             Forbidden: infrastructure implementations in this file.

[EXAMPLE]
    from shared.ports.position_repo import PositionRepository

    class PostgresPositionRepository(PositionRepository):
        async def get_by_address(self, address: PositionAddress) -> Position | None:
            # SQL query here
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.entities.position import Position
from shared.identifiers import PoolAddress, PositionAddress


class PositionRepository(ABC):
    """[WHY] Persists and retrieves Position entities from the data store.

    [OWNERSHIP] Domain layer — defines the contract for position persistence.

    [DEPENDENTS] Allowed: database (implements), collector, dashboard, navigator.
                 Forbidden: shared, agents (must go through ports).

    [EXAMPLE]
        repo = PostgresPositionRepository(session)
        position = await repo.get_by_address(PositionAddress("AJ6z..."))
    """

    @abstractmethod
    async def get_by_address(self, address: PositionAddress) -> Position | None:
        """Retrieve a position by its unique address."""

    @abstractmethod
    async def get_by_pool(self, pool_address: PoolAddress) -> list[Position]:
        """Retrieve all positions for a specific pool."""

    @abstractmethod
    async def save(self, position: Position) -> None:
        """Persist a position (create or update)."""

    @abstractmethod
    async def list_active(self) -> list[Position]:
        """Retrieve all active positions."""
