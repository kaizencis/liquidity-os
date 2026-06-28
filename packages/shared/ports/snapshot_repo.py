"""Snapshot repository interface for Liquidity OS.

[WHY] Defines the contract for time-series snapshot persistence. Snapshots
      are the primary data units — append-only, immutable, queried by time range.

[OWNERSHIP] Domain layer — port interface.

[DEPENDENTS] Allowed: database (implements), apps.collector, apps.analytics,
             agents.oracle, agents.navigator.
             Forbidden: infrastructure implementations in this file.

[EXAMPLE]
    from shared.ports.snapshot_repo import SnapshotRepository

    class PostgresSnapshotRepository(SnapshotRepository):
        async def get_latest(self, pool: PoolAddress) -> Snapshot | None:
            # SQL query here
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from shared.entities.pool import Pool
from shared.identifiers import PoolAddress
from shared.value_objects.snapshot import Snapshot


class SnapshotRepository(ABC):
    """[WHY] Persists and retrieves Snapshot records from the data store.

    [OWNERSHIP] Domain layer — defines the contract for time-series persistence.

    [DEPENDENTS] Allowed: database (implements), collector, analytics,
                 oracle, navigator.
                 Forbidden: shared (must go through ports).

    [EXAMPLE]
        repo = PostgresSnapshotRepository(session)
        latest = await repo.get_latest(PoolAddress("7Ytt..."))
    """

    @abstractmethod
    async def append(self, snapshot: Snapshot) -> None:
        """Append a new snapshot (immutable — no update)."""

    @abstractmethod
    async def get_latest(self, pool: PoolAddress) -> Snapshot | None:
        """Retrieve the most recent snapshot for a pool."""

    @abstractmethod
    async def get_range(
        self,
        pool: PoolAddress,
        start: datetime,
        end: datetime,
    ) -> list[Snapshot]:
        """Retrieve snapshots within a time range (inclusive)."""

    @abstractmethod
    async def exists(self, snapshot: Snapshot) -> bool:
        """Check if a snapshot already exists (by natural key)."""
