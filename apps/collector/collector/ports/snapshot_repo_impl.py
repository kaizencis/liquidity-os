"""PostgreSQL implementation of SnapshotRepository port.

[WHY] Translates between domain Snapshot entities and the snapshots table.
      Uses raw SQL for explicit control over JSONB serialization.
      Atomic append with ON CONFLICT DO NOTHING for idempotency.
[OWNERSHIP] Collector Service — port implementation.
[DEPENDENTS] Allowed: collector.collector.
             Forbidden: shared, agents, other apps.
[EXAMPLE]
    from database.connection import DatabaseSessionManager, DatabaseSettings
    from collector.ports.snapshot_repo_impl import PostgresSnapshotRepository

    manager = DatabaseSessionManager(DatabaseSettings())
    repo = PostgresSnapshotRepository(manager)
    await repo.append(snapshot)
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import text

from database.connection import DatabaseSessionManager
from shared.identifiers import PoolAddress
from shared.ports.snapshot_repo import SnapshotRepository
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.snapshot import Snapshot

# DDL for the snapshots table
CREATE_SNAPSHOTS_TABLE = """
CREATE TABLE IF NOT EXISTS snapshots (
    pool_address  VARCHAR(44)     NOT NULL,
    timestamp     TIMESTAMPTZ     NOT NULL,
    price         JSONB,
    sqrt_price    JSONB,
    liquidity     JSONB,
    volume_24h    JSONB,
    fees_24h      JSONB,
    metadata      JSONB           DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ     DEFAULT NOW(),
    PRIMARY KEY (pool_address, timestamp)
);
"""

# Indexes for efficient range queries
CREATE_SNAPSHOTS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_snapshots_pool_ts "
    "ON snapshots (pool_address, timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_ts "
    "ON snapshots (timestamp);",
]

# INSERT with ON CONFLICT DO NOTHING for idempotent appends
INSERT_SNAPSHOT = """
INSERT INTO snapshots (pool_address, timestamp, price, sqrt_price,
                       liquidity, volume_24h, fees_24h, metadata)
VALUES (:pool, :ts, :price, :sqrt_price,
        :liquidity, :volume_24h, :fees_24h, :metadata)
ON CONFLICT (pool_address, timestamp) DO NOTHING;
"""

SELECT_LATEST = """
SELECT pool_address, timestamp, price, sqrt_price,
       liquidity, volume_24h, fees_24h, metadata
FROM snapshots
WHERE pool_address = :pool
ORDER BY timestamp DESC
LIMIT 1;
"""

SELECT_RANGE = """
SELECT pool_address, timestamp, price, sqrt_price,
       liquidity, volume_24h, fees_24h, metadata
FROM snapshots
WHERE pool_address = :pool
  AND timestamp >= :start_ts
  AND timestamp <= :end_ts
ORDER BY timestamp ASC;
"""

SELECT_EXISTS = """
SELECT 1 FROM snapshots
WHERE pool_address = :pool AND timestamp = :ts
LIMIT 1;
"""


def _serialize_jsonb(value: object) -> str | None:
    """Serialize a Pydantic model or dict to JSON string for JSONB column.

    Args:
        value: Pydantic BaseModel, dict, or None.

    Returns:
        JSON string, or None if value is None.
    """
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump_json()
    if isinstance(value, dict):
        return json.dumps(value)
    return json.dumps(value)


def _deserialize_snapshot_row(row) -> Snapshot:
    """Convert a DB result row to a domain Snapshot entity.

    Args:
        row: SQLAlchemy Row object with columns matching SELECT order.

    Returns:
        Snapshot domain entity.
    """
    price_data = row.price
    sqrt_price_data = row.sqrt_price

    return Snapshot(
        pool=PoolAddress(value=row.pool_address),
        timestamp=row.timestamp,
        sqrt_price=SqrtPrice(**sqrt_price_data) if isinstance(sqrt_price_data, dict) else
                   SqrtPrice(**json.loads(sqrt_price_data)) if sqrt_price_data else None,
        price=Price(**price_data) if isinstance(price_data, dict) else
              Price(**json.loads(price_data)) if price_data else None,
        metadata=row.metadata if isinstance(row.metadata, dict) else
                 json.loads(row.metadata) if row.metadata else {},
    )


class PostgresSnapshotRepository(SnapshotRepository):
    """PostgreSQL implementation of SnapshotRepository.

    Manages its own session lifecycle via injected DatabaseSessionManager.
    All methods are atomic — append commits on success, rolls back on failure.
    Duplicate (pool, timestamp) appends are silent no-ops.
    """

    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        """Initialize repository with a session manager.

        Args:
            session_manager: Controls database engine and session lifecycle.
        """
        self._session_manager = session_manager

    async def append(self, snapshot: Snapshot) -> None:
        """Append a snapshot. Duplicate (pool, timestamp) is a no-op.

        Atomic: fully commits or raises an exception.
        """
        async with self._session_manager.session() as session:
            await session.execute(
                text(INSERT_SNAPSHOT),
                {
                    "pool": str(snapshot.pool.value),
                    "ts": snapshot.timestamp,
                    "price": _serialize_jsonb(snapshot.price),
                    "sqrt_price": _serialize_jsonb(snapshot.sqrt_price),
                    "liquidity": _serialize_jsonb(snapshot.liquidity),
                    "volume_24h": _serialize_jsonb(snapshot.volume_24h),
                    "fees_24h": _serialize_jsonb(snapshot.fees_24h),
                    "metadata": _serialize_jsonb(snapshot.metadata),
                },
            )

    async def get_latest(self, pool: PoolAddress) -> Snapshot | None:
        """Retrieve the most recent snapshot for a pool."""
        async with self._session_manager.session() as session:
            result = await session.execute(
                text(SELECT_LATEST),
                {"pool": str(pool.value)},
            )
            row = result.one_or_none()
            if row is None:
                return None
            return _deserialize_snapshot_row(row)

    async def get_range(
        self,
        pool: PoolAddress,
        start: datetime,
        end: datetime,
    ) -> list[Snapshot]:
        """Retrieve snapshots within a time range (inclusive)."""
        async with self._session_manager.session() as session:
            result = await session.execute(
                text(SELECT_RANGE),
                {
                    "pool": str(pool.value),
                    "start_ts": start,
                    "end_ts": end,
                },
            )
            return [_deserialize_snapshot_row(row) for row in result]

    async def exists(self, snapshot: Snapshot) -> bool:
        """Check if a snapshot exists by its natural key (pool, timestamp)."""
        async with self._session_manager.session() as session:
            result = await session.execute(
                text(SELECT_EXISTS),
                {
                    "pool": str(snapshot.pool.value),
                    "ts": snapshot.timestamp,
                },
            )
            return result.one_or_none() is not None
