"""Tests for PostgresSnapshotRepository — PostgreSQL implementation.

Requires: testcontainers and Docker daemon.  Skip if Docker unavailable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from collector.ports.snapshot_repo_impl import (
    PostgresSnapshotRepository,
    _serialize_jsonb,
    _deserialize_snapshot_row,
    CREATE_SNAPSHOTS_TABLE,
    CREATE_SNAPSHOTS_INDEXES,
)
from database.connection import DatabaseSessionManager, DatabaseSettings
from shared.identifiers import PoolAddress
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.snapshot import Snapshot
from shared.value_objects.token import Token, TokenAmount

# ---- skip condition ---- #
try:
    from testcontainers.postgres import PostgresContainer
    HAS_DOCKER = True
except (ImportError, ModuleNotFoundError):
    HAS_DOCKER = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not HAS_DOCKER, reason="Docker / testcontainers not available"),
]

# ---- helpers ---- #

_TS = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
_POOL = PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs")
_POOL2 = PoolAddress(value="8YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK2jKs")
_POOL3 = PoolAddress(value="9ZttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK3kLs")
_UNKNOWN_POOL = PoolAddress(value="8YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK3kLs")
_TOKEN_A = Token(
    address="So11111111111111111111111111111111111111112", symbol="SOL", decimals=9
)
_TOKEN_B = Token(
    address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", symbol="USDC", decimals=6
)


def _snapshot(ts: datetime | None = None, pool=None) -> Snapshot:
    return Snapshot(
        pool=pool or _POOL,
        timestamp=ts or _TS,
        price=Price(
            value=Decimal("142.5"),
            base_token=_TOKEN_B,
            quote_token=_TOKEN_A,
        ),
        sqrt_price=SqrtPrice(raw=79228162514264337593543950336, tick=0, bin_id=0),
    )


# ---- Fixtures ---- #


@pytest.fixture(scope="module")
def postgres():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture
async def manager(postgres):
    url = postgres.get_connection_url().replace("psycopg2", "asyncpg")
    mgr = DatabaseSessionManager(DatabaseSettings(url=url))
    mgr.connect()
    async with mgr.session() as session:
        await session.execute(text(CREATE_SNAPSHOTS_TABLE))
        for idx_sql in CREATE_SNAPSHOTS_INDEXES:
            await session.execute(text(idx_sql))
    yield mgr
    mgr.disconnect()


@pytest.fixture
def repo(manager):
    return PostgresSnapshotRepository(manager)


# ---- SnapshotRepository contract tests ---- #


class TestPostgresSnapshotRepository:
    """PostgresSnapshotRepository correctness."""

    @pytest.mark.asyncio
    async def test_append_inserts(self, repo):
        """Basic insert works."""
        s = _snapshot()
        await repo.append(s)
        ok = await repo.exists(s)
        assert ok is True

    @pytest.mark.asyncio
    async def test_append_duplicate_noop(self, repo):
        """Same (pool, ts) does not raise."""
        s = _snapshot()
        await repo.append(s)
        await repo.append(s)  # should not raise

    @pytest.mark.asyncio
    async def test_append_duplicate_single_row(self, repo):
        """Duplicate append does not create extra rows."""
        s = _snapshot()
        await repo.append(s)
        await repo.append(s)
        rows = await repo.get_range(
            _POOL,
            _TS - timedelta(hours=1),
            _TS + timedelta(hours=1),
        )
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_get_latest_newest(self, repo):
        """get_latest returns most recent snapshot."""
        t1 = _TS
        t2 = _TS + timedelta(hours=2)
        s1 = _snapshot(ts=t1, pool=_POOL2)
        s2 = _snapshot(ts=t2, pool=_POOL2)
        await repo.append(s1)
        await repo.append(s2)
        result = await repo.get_latest(_POOL2)
        assert result is not None
        assert result.timestamp == t2

    @pytest.mark.asyncio
    async def test_get_latest_empty(self, repo):
        """get_latest on empty table returns None."""
        result = await repo.get_latest(_UNKNOWN_POOL)
        assert result is None

    @pytest.mark.asyncio
    async def test_range_inclusive(self, repo):
        """get_range includes boundary timestamps."""
        t1, t2, t3 = _TS, _TS + timedelta(hours=1), _TS + timedelta(hours=2)
        for t in (t1, t2, t3):
            await repo.append(_snapshot(ts=t, pool=_POOL2))
        rows = await repo.get_range(_POOL2, t1, t3)
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_range_subset(self, repo):
        """get_range returns correct subset."""
        t1, t2, t3 = _TS, _TS + timedelta(hours=1), _TS + timedelta(hours=2)
        for t in (t1, t2, t3):
            await repo.append(_snapshot(ts=t, pool=_POOL2))
        rows = await repo.get_range(_POOL2, t2, t2)
        assert len(rows) == 1
        assert rows[0].timestamp == t2

    @pytest.mark.asyncio
    async def test_range_empty(self, repo):
        """get_range outside data range returns []."""
        far_future = _TS + timedelta(days=365)
        rows = await repo.get_range(_POOL2, far_future, far_future + timedelta(days=1))
        assert rows == []

    @pytest.mark.asyncio
    async def test_range_ascending(self, repo):
        """get_range returns rows ordered by timestamp ASC."""
        t1, t2, t3 = _TS, _TS + timedelta(hours=1), _TS + timedelta(hours=2)
        # Insert out of order
        await repo.append(_snapshot(ts=t3, pool=_POOL2))
        await repo.append(_snapshot(ts=t1, pool=_POOL2))
        await repo.append(_snapshot(ts=t2, pool=_POOL2))
        rows = await repo.get_range(_POOL2, t1, t3)
        timestamps = [r.timestamp for r in rows]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_exists_true(self, repo):
        """exists returns True for existing snapshot."""
        s = _snapshot()
        await repo.append(s)
        assert await repo.exists(s) is True

    @pytest.mark.asyncio
    async def test_exists_false(self, repo):
        """exists returns False for non-existing snapshot."""
        # Use a unique pool address so no other test could have inserted it
        unique_pool = PoolAddress(
            value="9ZttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK3kLs"
        )
        s = _snapshot(pool=unique_pool)
        assert await repo.exists(s) is False

    # ---- Serialization ---- #

    def test_serialize_none(self):
        """_serialize_jsonb(None) returns None."""
        assert _serialize_jsonb(None) is None

    def test_serialize_pydantic(self):
        """Pydantic model → JSON string via model_dump()."""
        price = Price(value=Decimal("100.0"), base_token=_TOKEN_B, quote_token=_TOKEN_A)
        result = _serialize_jsonb(price)
        expected = price.model_dump_json()
        assert result == expected

    def test_serialize_dict(self):
        """dict → JSON string."""
        result = _serialize_jsonb({"a": 1, "b": "hello"})
        assert result == json.dumps({"a": 1, "b": "hello"})

    @pytest.mark.asyncio
    async def test_roundtrip(self, repo):
        """Append → exists → get_latest round-trips correctly."""
        s = _snapshot(pool=_POOL3)
        await repo.append(s)

        ok = await repo.exists(s)
        assert ok is True

        retrieved = await repo.get_latest(s.pool)
        assert retrieved is not None
        assert retrieved.pool == s.pool
        assert retrieved.timestamp == s.timestamp
        assert retrieved.price == s.price
        assert retrieved.sqrt_price == s.sqrt_price
        assert retrieved.metadata == s.metadata
