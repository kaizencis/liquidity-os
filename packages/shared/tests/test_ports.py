"""Unit tests for shared.ports module."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from shared.entities.decision import Decision
from shared.entities.pool import Pool
from shared.entities.position import Position
from shared.enums import (
    AgentRole,
    AlertSeverity,
    DecisionOutcome,
    PoolStatus,
    PositionStatus,
)
from shared.identifiers import DecisionId, PoolAddress, PositionAddress
from shared.ports.decision_log import DecisionLog
from shared.ports.feature_provider import FeatureProvider
from shared.ports.notifier import Notifier
from shared.ports.pool_repo import PoolRepository
from shared.ports.position_repo import PositionRepository
from shared.ports.snapshot_repo import SnapshotRepository
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.snapshot import Snapshot
from shared.value_objects.token import Token, TokenAmount


# ---------------------------------------------------------------------------
# Mock Implementations
# ---------------------------------------------------------------------------


class MockPoolRepository(PoolRepository):
    def __init__(self) -> None:
        self.pools: dict[str, Pool] = {}

    async def get_by_address(self, address: PoolAddress) -> Pool | None:
        return self.pools.get(str(address))

    async def save(self, pool: Pool) -> None:
        self.pools[str(pool.address)] = pool

    async def list_all(self) -> list[Pool]:
        return list(self.pools.values())

    async def list_by_status(self, status: str) -> list[Pool]:
        return [p for p in self.pools.values() if p.status.value == status]


class MockPositionRepository(PositionRepository):
    def __init__(self) -> None:
        self.positions: dict[str, Position] = {}

    async def get_by_address(self, address: PositionAddress) -> Position | None:
        return self.positions.get(str(address))

    async def get_by_pool(self, pool_address: PoolAddress) -> list[Position]:
        return [p for p in self.positions.values() if p.pool_address == pool_address]

    async def save(self, position: Position) -> None:
        self.positions[str(position.address)] = position

    async def list_active(self) -> list[Position]:
        return [p for p in self.positions.values() if p.is_active]


class MockSnapshotRepository(SnapshotRepository):
    def __init__(self) -> None:
        self.snapshots: list[Snapshot] = []

    async def append(self, snapshot: Snapshot) -> None:
        self.snapshots.append(snapshot)

    async def get_latest(self, pool: PoolAddress) -> Snapshot | None:
        pool_snapshots = [s for s in self.snapshots if s.pool == pool]
        if not pool_snapshots:
            return None
        return max(pool_snapshots, key=lambda s: s.timestamp)

    async def get_range(
        self,
        pool: PoolAddress,
        start: datetime,
        end: datetime,
    ) -> list[Snapshot]:
        return [
            s for s in self.snapshots
            if s.pool == pool and start <= s.timestamp <= end
        ]

    async def exists(self, snapshot: Snapshot) -> bool:
        return snapshot in self.snapshots


class MockFeatureProvider(FeatureProvider):
    def __init__(self) -> None:
        self.features: dict[str, dict[str, float | None]] = {}

    async def get_volatility(self, pool: PoolAddress) -> float | None:
        return self.features.get(str(pool), {}).get("volatility")

    async def get_volume_change(self, pool: PoolAddress) -> float | None:
        return self.features.get(str(pool), {}).get("volume_change")

    async def get_liquidity_concentration(self, pool: PoolAddress) -> float | None:
        return self.features.get(str(pool), {}).get("liquidity_concentration")

    async def get_spread(self, pool: PoolAddress) -> float | None:
        return self.features.get(str(pool), {}).get("spread")

    async def get_features(self, pool: PoolAddress) -> dict[str, float | None]:
        return self.features.get(str(pool), {})

    async def invalidate(self, pool: PoolAddress) -> None:
        self.features.pop(str(pool), None)


class MockDecisionLog(DecisionLog):
    def __init__(self) -> None:
        self.decisions: dict[str, Decision] = {}

    async def append(self, decision: Decision) -> None:
        self.decisions[str(decision.id)] = decision

    async def get_by_id(self, decision_id: DecisionId) -> Decision | None:
        return self.decisions.get(str(decision_id))

    async def query(
        self,
        agent: AgentRole | None = None,
        outcome: DecisionOutcome | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
    ) -> list[Decision]:
        results = list(self.decisions.values())
        if agent:
            results = [d for d in results if d.agent == agent]
        if outcome:
            results = [d for d in results if d.outcome == outcome]
        if start:
            results = [d for d in results if d.timestamp >= start]
        if end:
            results = [d for d in results if d.timestamp <= end]
        return results[:limit]

    async def count(
        self,
        agent: AgentRole | None = None,
        outcome: DecisionOutcome | None = None,
    ) -> int:
        results = list(self.decisions.values())
        if agent:
            results = [d for d in results if d.agent == agent]
        if outcome:
            results = [d for d in results if d.outcome == outcome]
        return len(results)


class MockNotifier(Notifier):
    def __init__(self) -> None:
        self.sent_alerts: list[tuple[str, AlertSeverity]] = []
        self.sent_reports: list[tuple[str, str]] = []
        self.sent_approvals: list[tuple[str, str]] = []

    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> None:
        self.sent_alerts.append((message, severity))

    async def send_report(
        self,
        title: str,
        content: str,
    ) -> None:
        self.sent_reports.append((title, content))

    async def send_approval_request(
        self,
        message: str,
        callback_data: str,
    ) -> None:
        self.sent_approvals.append((message, callback_data))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def SOL() -> Token:
    return Token(
        address="So11111111111111111111111111111111111111112",
        symbol="SOL",
        decimals=9,
    )


@pytest.fixture
def USDC() -> Token:
    return Token(
        address="EPjFwd4pz9iJGSVQiGieoXyBdKXX4usSJr7jTyCn9e",
        symbol="USDC",
        decimals=6,
    )


@pytest.fixture
def pool_address() -> PoolAddress:
    return PoolAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY")


@pytest.fixture
def pool(pool_address: PoolAddress, SOL: Token, USDC: Token) -> Pool:
    return Pool(
        address=pool_address,
        token_a=SOL,
        token_b=USDC,
        status=PoolStatus.ACTIVE,
    )


# ---------------------------------------------------------------------------
# PoolRepository
# ---------------------------------------------------------------------------


class TestPoolRepository:
    """Tests for PoolRepository interface contract."""

    @pytest.mark.asyncio
    async def test_save_and_get(self, pool: Pool) -> None:
        repo = MockPoolRepository()
        await repo.save(pool)
        result = await repo.get_by_address(pool.address)
        assert result == pool

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, pool_address: PoolAddress) -> None:
        repo = MockPoolRepository()
        result = await repo.get_by_address(pool_address)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all(self, pool: Pool) -> None:
        repo = MockPoolRepository()
        await repo.save(pool)
        result = await repo.list_all()
        assert len(result) == 1
        assert result[0] == pool

    @pytest.mark.asyncio
    async def test_list_by_status(self, pool: Pool) -> None:
        repo = MockPoolRepository()
        await repo.save(pool)
        result = await repo.list_by_status("active")
        assert len(result) == 1


# ---------------------------------------------------------------------------
# PositionRepository
# ---------------------------------------------------------------------------


class TestPositionRepository:
    """Tests for PositionRepository interface contract."""

    @pytest.mark.asyncio
    async def test_save_and_get(self, pool_address: PoolAddress) -> None:
        position = Position(
            address=PositionAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"),
            pool_address=pool_address,
        )
        repo = MockPositionRepository()
        await repo.save(position)
        result = await repo.get_by_address(position.address)
        assert result == position

    @pytest.mark.asyncio
    async def test_get_by_pool(self, pool_address: PoolAddress) -> None:
        position = Position(
            address=PositionAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"),
            pool_address=pool_address,
        )
        repo = MockPositionRepository()
        await repo.save(position)
        result = await repo.get_by_pool(pool_address)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_active(self, pool_address: PoolAddress) -> None:
        position = Position(
            address=PositionAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"),
            pool_address=pool_address,
            status=PositionStatus.ACTIVE,
        )
        repo = MockPositionRepository()
        await repo.save(position)
        result = await repo.list_active()
        assert len(result) == 1


# ---------------------------------------------------------------------------
# SnapshotRepository
# ---------------------------------------------------------------------------


class TestSnapshotRepository:
    """Tests for SnapshotRepository interface contract."""

    @pytest.mark.asyncio
    async def test_append_and_get_latest(self, pool_address: PoolAddress) -> None:
        snapshot = Snapshot(pool=pool_address)
        repo = MockSnapshotRepository()
        await repo.append(snapshot)
        result = await repo.get_latest(pool_address)
        assert result == snapshot

    @pytest.mark.asyncio
    async def test_get_latest_nonexistent(self, pool_address: PoolAddress) -> None:
        repo = MockSnapshotRepository()
        result = await repo.get_latest(pool_address)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_range(self, pool_address: PoolAddress) -> None:
        t1 = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 28, 13, 0, 0, tzinfo=timezone.utc)
        s1 = Snapshot(pool=pool_address, timestamp=t1)
        s2 = Snapshot(pool=pool_address, timestamp=t2)
        repo = MockSnapshotRepository()
        await repo.append(s1)
        await repo.append(s2)
        result = await repo.get_range(pool_address, t1, t2)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_exists(self, pool_address: PoolAddress) -> None:
        snapshot = Snapshot(pool=pool_address)
        repo = MockSnapshotRepository()
        assert not await repo.exists(snapshot)
        await repo.append(snapshot)
        assert await repo.exists(snapshot)


# ---------------------------------------------------------------------------
# FeatureProvider
# ---------------------------------------------------------------------------


class TestFeatureProvider:
    """Tests for FeatureProvider interface contract."""

    @pytest.mark.asyncio
    async def test_get_features(self, pool_address: PoolAddress) -> None:
        provider = MockFeatureProvider()
        provider.features[str(pool_address)] = {"volatility": 0.15, "spread": 0.001}
        result = await provider.get_features(pool_address)
        assert result["volatility"] == 0.15

    @pytest.mark.asyncio
    async def test_get_volatility(self, pool_address: PoolAddress) -> None:
        provider = MockFeatureProvider()
        provider.features[str(pool_address)] = {"volatility": 0.15}
        result = await provider.get_volatility(pool_address)
        assert result == 0.15

    @pytest.mark.asyncio
    async def test_invalidate(self, pool_address: PoolAddress) -> None:
        provider = MockFeatureProvider()
        provider.features[str(pool_address)] = {"volatility": 0.15}
        await provider.invalidate(pool_address)
        result = await provider.get_volatility(pool_address)
        assert result is None


# ---------------------------------------------------------------------------
# DecisionLog
# ---------------------------------------------------------------------------


class TestDecisionLog:
    """Tests for DecisionLog interface contract."""

    @pytest.mark.asyncio
    async def test_append_and_get(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
        )
        log = MockDecisionLog()
        await log.append(decision)
        result = await log.get_by_id(decision.id)
        assert result == decision

    @pytest.mark.asyncio
    async def test_query_by_agent(self) -> None:
        d1 = Decision(id=DecisionId.generate(), agent=AgentRole.ORACLE, event_type="test")
        d2 = Decision(id=DecisionId.generate(), agent=AgentRole.NAVIGATOR, event_type="test")
        log = MockDecisionLog()
        await log.append(d1)
        await log.append(d2)
        result = await log.query(agent=AgentRole.ORACLE)
        assert len(result) == 1
        assert result[0].agent == AgentRole.ORACLE

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        d1 = Decision(id=DecisionId.generate(), agent=AgentRole.ORACLE, event_type="test")
        log = MockDecisionLog()
        await log.append(d1)
        count = await log.count(agent=AgentRole.ORACLE)
        assert count == 1


# ---------------------------------------------------------------------------
# Notifier
# ---------------------------------------------------------------------------


class TestNotifier:
    """Tests for Notifier interface contract."""

    @pytest.mark.asyncio
    async def test_send_alert(self) -> None:
        notifier = MockNotifier()
        await notifier.send_alert("Test alert", AlertSeverity.CRITICAL)
        assert len(notifier.sent_alerts) == 1
        assert notifier.sent_alerts[0] == ("Test alert", AlertSeverity.CRITICAL)

    @pytest.mark.asyncio
    async def test_send_report(self) -> None:
        notifier = MockNotifier()
        await notifier.send_report("Daily Report", "Content here")
        assert len(notifier.sent_reports) == 1
        assert notifier.sent_reports[0] == ("Daily Report", "Content here")

    @pytest.mark.asyncio
    async def test_send_approval_request(self) -> None:
        notifier = MockNotifier()
        await notifier.send_approval_request("Approve rebalance?", "approve_123")
        assert len(notifier.sent_approvals) == 1
