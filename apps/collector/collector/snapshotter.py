"""Factory for creating Snapshot domain objects from Pool entities.

[WHY] Pure transformation — Pool → Snapshot.
      No infrastructure dependencies, no M4 references.
[OWNERSHIP] Collector Service — domain transformation.
[DEPENDENTS] Allowed: collector.collector.
             Forbidden: shared, agents, other apps.
[EXAMPLE]
    from collector.snapshotter import Snapshotter
    from shared.entities.pool import Pool

    snapshot = Snapshotter.from_pool(pool)
    assert snapshot.pool == pool.address
"""

from __future__ import annotations

from datetime import datetime, timezone

from shared.entities.pool import Pool
from shared.value_objects.snapshot import Snapshot


class Snapshotter:
    """Factory for creating Snapshot objects from Pool entities.

    Pure static transformation — no state, no side effects.
    Only maps fields that exist in the source Pool.
    All unmapped Snapshot fields default to None.
    """

    @staticmethod
    def from_pool(
        pool: Pool,
        timestamp: datetime | None = None,
        metadata: dict | None = None,
    ) -> Snapshot:
        """Create a Snapshot from a Pool entity.

        Args:
            pool: Domain Pool entity (from list_pools or get_pool).
            timestamp: Observation timestamp. Defaults to current UTC time.
            metadata: Optional freeform context data.

        Returns:
            Immutable Snapshot record with natural key (pool, timestamp).
        """
        return Snapshot(
            pool=pool.address,
            timestamp=timestamp if timestamp is not None else datetime.now(timezone.utc),
            sqrt_price=pool.sqrt_price,
            price=pool.price,
            metadata=metadata if metadata is not None else {},
        )
