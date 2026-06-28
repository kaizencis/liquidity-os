"""Pool repository interface for Liquidity OS.

[WHY] Defines the contract for pool persistence. The domain defines what
      operations are needed; infrastructure (database) provides the implementation.

[OWNERSHIP] Domain layer — port interface.

[DEPENDENTS] Allowed: database (implements), apps.collector, apps.analytics,
             apps.dashboard, agents.oracle, agents.navigator.
             Forbidden: infrastructure implementations in this file.

[EXAMPLE]
    from shared.ports.pool_repo import PoolRepository

    class PostgresPoolRepository(PoolRepository):
        async def get_by_address(self, address: PoolAddress) -> Pool | None:
            # SQL query here
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.entities.pool import Pool
from shared.identifiers import PoolAddress


class PoolRepository(ABC):
    """[WHY] Persists and retrieves Pool entities from the data store.

    [OWNERSHIP] Domain layer — defines the contract for pool persistence.

    [DEPENDENTS] Allowed: database (implements), collector, analytics, dashboard.
                 Forbidden: shared, agents (must go through ports).

    [EXAMPLE]
        repo = PostgresPoolRepository(session)
        pool = await repo.get_by_address(PoolAddress("7Ytt..."))
    """

    @abstractmethod
    async def get_by_address(self, address: PoolAddress) -> Pool | None:
        """Retrieve a pool by its unique address."""

    @abstractmethod
    async def save(self, pool: Pool) -> None:
        """Persist a pool (create or update)."""

    @abstractmethod
    async def list_all(self) -> list[Pool]:
        """Retrieve all pools."""

    @abstractmethod
    async def list_by_status(self, status: str) -> list[Pool]:
        """Retrieve pools filtered by status."""
