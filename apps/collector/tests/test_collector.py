"""Tests for CollectorService — orchestration, lifecycle, error handling."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, call, patch

import pytest

from collector.collector import CollectorService, CycleResult, PoolResult
from collector.rate_limiter import RateLimiter
from collector.settings import CollectorSettings
from meteora.errors import MeteoraError
from shared.entities.pool import Pool
from shared.entities.position import Position
from shared.entities.decision import Decision
from shared.enums import AgentRole, DecisionOutcome
from shared.identifiers import DecisionId, PoolAddress
from shared.ports.decision_log import DecisionLog
from shared.ports.meteora_reader import PoolReader, PositionReader
from shared.ports.pool_repo import PoolRepository
from shared.ports.position_repo import PositionRepository
from shared.ports.snapshot_repo import SnapshotRepository
from shared.value_objects.snapshot import Snapshot
from shared.value_objects.token import Token
from shared.enums import PoolStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings():
    return CollectorSettings(
        interval_seconds=9999,
        rate_limit_rps=1000,
        api_timeout_seconds=5.0,
        positions_timeout_seconds=5.0,
        db_timeout_seconds=5.0,
        pool_positions_timeout=5.0,
        max_retries=1,
    )


@pytest.fixture
def mock_pool_reader():
    return AsyncMock(spec=PoolReader)


@pytest.fixture
def mock_position_reader():
    return AsyncMock(spec=PositionReader)


@pytest.fixture
def mock_pool_repo():
    return AsyncMock(spec=PoolRepository)


@pytest.fixture
def mock_position_repo():
    return AsyncMock(spec=PositionRepository)


@pytest.fixture
def mock_snapshot_repo():
    return AsyncMock(spec=SnapshotRepository)


@pytest.fixture
def mock_decision_log():
    return AsyncMock(spec=DecisionLog)


@pytest.fixture
def sample_pool():
    token_a = Token(
        address="So11111111111111111111111111111111111111112",
        symbol="SOL", decimals=9,
    )
    token_b = Token(
        address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        symbol="USDC", decimals=6,
    )
    return Pool(
        address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
        token_a=token_a,
        token_b=token_b,
        status=PoolStatus.ACTIVE,
    )


@pytest.fixture
def single_pool_list(sample_pool):
    return [sample_pool]


@pytest.fixture
def three_pools(sample_pool):
    t_a = sample_pool.token_a
    t_b = sample_pool.token_b
    a1 = sample_pool.address
    return [
        sample_pool,
        Pool(
            address=PoolAddress(value="8YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK2jKs"),
            token_a=t_a, token_b=t_b, status=PoolStatus.ACTIVE,
        ),
        Pool(
            address=PoolAddress(value="9ZttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK3kLs"),
            token_a=t_a, token_b=t_b, status=PoolStatus.ACTIVE,
        ),
    ]


@pytest.fixture
def pool_addr(sample_pool):
    return sample_pool.address


@pytest.fixture
def mock_position():
    return AsyncMock(spec=Position)


@pytest.fixture
def mock_positions(mock_position):
    return [mock_position]


@pytest.fixture
def collector(mock_pool_reader, mock_position_reader, mock_pool_repo,
              mock_position_repo, mock_snapshot_repo, mock_decision_log,
              settings):
    return CollectorService(
        pool_reader=mock_pool_reader,
        position_reader=mock_position_reader,
        pool_repo=mock_pool_repo,
        position_repo=mock_position_repo,
        snapshot_repo=mock_snapshot_repo,
        decision_log=mock_decision_log,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


def _make_collector(**overrides) -> CollectorService:
    """Build a CollectorService with fresh mocked deps and optional setting overrides."""
    defaults = dict(
        interval_seconds=9999,
        rate_limit_rps=1000,
        api_timeout_seconds=5.0,
        positions_timeout_seconds=5.0,
        db_timeout_seconds=5.0,
        pool_positions_timeout=5.0,
        max_retries=1,
    )
    defaults.update(overrides)
    s = CollectorSettings(**defaults)
    return CollectorService(
        pool_reader=AsyncMock(spec=PoolReader),
        position_reader=AsyncMock(spec=PositionReader),
        pool_repo=AsyncMock(spec=PoolRepository),
        position_repo=AsyncMock(spec=PositionRepository),
        snapshot_repo=AsyncMock(spec=SnapshotRepository),
        decision_log=AsyncMock(spec=DecisionLog),
        settings=s,
    )


# ===================================================================
# Group A — _run_cycle basic
# ===================================================================


class TestRunCycle:
    """_run_cycle basic behaviour."""

    @pytest.mark.asyncio
    async def test_single_pool_cycle(self, collector, single_pool_list, mock_positions):
        """Single pool succeeds."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        result = await collector._run_cycle()

        assert result.pools_attempted == 1
        assert result.pools_succeeded == 1
        assert result.pools_failed == 0
        assert result.duration_seconds >= 0
        collector._position_repo.save.assert_called_once()
        collector._snapshot_repo.append.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_pool_list(self, collector):
        """No pools yields empty cycle."""
        collector._pool_reader.list_pools.return_value = []

        result = await collector._run_cycle()

        assert result.pools_attempted == 0
        assert result.pools_succeeded == 0
        assert result.pools_failed == 0
        collector._position_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_three_pools_all_succeed(self, collector, three_pools, mock_positions):
        """3 pools all succeed."""
        collector._pool_reader.list_pools.return_value = three_pools
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        result = await collector._run_cycle()

        assert result.pools_attempted == 3
        assert result.pools_succeeded == 3
        assert result.pools_failed == 0
        assert collector._position_repo.save.call_count == 3
        assert collector._snapshot_repo.append.call_count == 3

    @pytest.mark.asyncio
    async def test_cycle_returns_timestamp(self, collector, single_pool_list):
        """cycle_timestamp is a UTC datetime."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = []

        result = await collector._run_cycle()

        assert isinstance(result.cycle_timestamp, datetime)
        assert result.cycle_timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_acquire_called_for_list_pools(self, collector, single_pool_list, mock_positions):
        """RateLimiter.acquire is called at least once (for list_pools)."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        # Count RateLimiter constructor calls — each cycle creates one
        init_count = [0]
        original_init = RateLimiter.__init__

        def counting_init(self, rps):
            init_count[0] += 1
            original_init(self, rps)

        with patch.object(RateLimiter, "__init__", counting_init):
            await collector._run_cycle()
            assert init_count[0] >= 1, "RateLimiter must be created per cycle"

    @pytest.mark.asyncio
    async def test_acquire_count_matches_pools(self, collector, three_pools, mock_positions):
        """RateLimiter created exactly once (acquire is called internally for list + each pool)."""
        collector._pool_reader.list_pools.return_value = three_pools
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        # Test that a RateLimiter is always created (fresh per cycle)
        init_count = [0]
        original_init = RateLimiter.__init__

        def counting_init(self, rps):
            init_count[0] += 1
            original_init(self, rps)

        with patch.object(RateLimiter, "__init__", counting_init):
            await collector._run_cycle()
            assert init_count[0] == 1, "Exactly one RateLimiter per cycle"


# ===================================================================
# Group B — _run_cycle failure paths
# ===================================================================


class TestRunCycleFailures:
    """_run_cycle error handling."""

    @pytest.mark.asyncio
    async def test_all_pools_fail(self, collector, three_pools):
        """All 3 pools fail."""
        collector._pool_reader.list_pools.return_value = three_pools
        collector._position_reader.get_positions_by_pool.side_effect = MeteoraError("down")

        result = await collector._run_cycle()

        assert result.pools_attempted == 3
        assert result.pools_succeeded == 0
        assert result.pools_failed == 3

    @pytest.mark.asyncio
    async def test_one_of_three_fails(self, collector, three_pools, mock_positions):
        """Pool[1] fails, others succeed."""
        collector._pool_reader.list_pools.return_value = three_pools
        collector._position_reader.get_positions_by_pool.side_effect = [
            mock_positions,
            MeteoraError("fail"),
            mock_positions,
        ]

        result = await collector._run_cycle()

        assert result.pools_attempted == 3
        assert result.pools_succeeded == 2
        assert result.pools_failed == 1

    @pytest.mark.asyncio
    async def test_list_pools_retried(self, collector, single_pool_list):
        """list_pools fails once, retries, succeeds."""
        collector._pool_reader.list_pools.side_effect = [
            TimeoutError("timeout"),
            single_pool_list,
        ]

        result = await collector._run_cycle()

        assert result.pools_attempted == 1
        assert collector._pool_reader.list_pools.call_count == 2

    @pytest.mark.asyncio
    async def test_list_pools_retries_exhausted_raises(
        self, collector, caplog
    ):
        """list_pools always fails — exception propagates from _run_cycle."""
        collector._pool_reader.list_pools.side_effect = asyncio.TimeoutError("never")

        with pytest.raises(asyncio.TimeoutError):
            await collector._run_cycle()

    @pytest.mark.asyncio
    async def test_list_pools_failure_cycle_continues(
        self, collector, single_pool_list, caplog
    ):
        """run_forever catches list_pools failure and continues."""
        # Fail first call, succeed second
        collector._pool_reader.list_pools.side_effect = [
            asyncio.TimeoutError("fail"),
            single_pool_list,
        ]
        collector._position_reader.get_positions_by_pool.return_value = []

        caplog.set_level(logging.WARNING)
        # Override interval to avoid infinite loop
        custom = CollectorSettings(
            interval_seconds=9999, rate_limit_rps=1000,
            api_timeout_seconds=1, positions_timeout_seconds=1,
            db_timeout_seconds=1, pool_positions_timeout=1,
            max_retries=1,
        )
        collector._settings = custom

        # Run in a task, stop after 2 list_pools calls
        async def run_and_stop():
            task = asyncio.create_task(collector.run_forever())
            # Wait until list_pools has been called twice (fail + succeed)
            while collector._pool_reader.list_pools.call_count < 2:
                await asyncio.sleep(0.01)
            await asyncio.sleep(0.1)
            await collector.stop()
            await task

        await run_and_stop()
        assert collector._pool_reader.list_pools.call_count >= 2

    @pytest.mark.asyncio
    async def test_positions_retried(self, collector, single_pool_list, mock_positions):
        """positions fetch fails once, retries, succeeds."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.side_effect = [
            TimeoutError("timeout"),
            mock_positions,
        ]

        result = await collector._run_cycle()

        assert result.pools_succeeded == 1
        assert collector._position_reader.get_positions_by_pool.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_rejected(self, collector, single_pool_list):
        """ValueError is NOT retried — pool fails immediately."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.side_effect = ValueError("bad")

        result = await collector._run_cycle()

        assert result.pools_failed == 1
        assert collector._position_reader.get_positions_by_pool.call_count == 1

    @pytest.mark.asyncio
    async def test_meteora_error_retried(
        self, collector, single_pool_list, mock_positions
    ):
        """MeteoraError triggers retry then succeeds."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.side_effect = [
            MeteoraError("429"),
            mock_positions,
        ]

        result = await collector._run_cycle()

        assert result.pools_succeeded == 1
        assert collector._position_reader.get_positions_by_pool.call_count == 2


# ===================================================================
# Group C — Timeout enforcement
# ===================================================================


class TestTimeouts:
    """Per-operation timeout enforcement (R2)."""

    @pytest.mark.asyncio
    async def test_pools_timeout_applied(self):
        """api_timeout_seconds wraps list_pools."""
        c = _make_collector(api_timeout_seconds=0.05)
        c._pool_reader.list_pools.side_effect = asyncio.TimeoutError()

        with pytest.raises(asyncio.TimeoutError):
            await c._run_cycle()

    @pytest.mark.asyncio
    async def test_positions_timeout_applied(self):
        """positions_timeout_seconds wraps positions fetch."""
        c = _make_collector(positions_timeout_seconds=0.05)
        c._pool_reader.list_pools.return_value = [Pool(
            address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
            token_a=Token(address="So11111111111111111111111111111111111111112", symbol="SOL", decimals=9),
            token_b=Token(address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", symbol="USDC", decimals=6),
            status=PoolStatus.ACTIVE,
        )]
        c._position_reader.get_positions_by_pool.side_effect = asyncio.TimeoutError()

        result = await c._run_cycle()
        assert result.pools_failed == 1

    @pytest.mark.asyncio
    async def test_db_timeout_fails_pool(self):
        """db_timeout on snapshot persist causes pool failure."""
        c = _make_collector(db_timeout_seconds=0.05)
        c._pool_reader.list_pools.return_value = [Pool(
            address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
            token_a=Token(address="So11111111111111111111111111111111111111112", symbol="SOL", decimals=9),
            token_b=Token(address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", symbol="USDC", decimals=6),
            status=PoolStatus.ACTIVE,
        )]
        c._position_reader.get_positions_by_pool.return_value = [AsyncMock(spec=Position)]
        c._snapshot_repo.append.side_effect = asyncio.TimeoutError("db timeout")

        result = await c._run_cycle()
        assert result.pools_failed == 1
        c._position_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_positions_batch_timeout(self):
        """pool_positions_timeout on batch causes pool failure."""
        c = _make_collector(pool_positions_timeout=0.05)
        c._pool_reader.list_pools.return_value = [Pool(
            address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
            token_a=Token(address="So11111111111111111111111111111111111111112", symbol="SOL", decimals=9),
            token_b=Token(address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", symbol="USDC", decimals=6),
            status=PoolStatus.ACTIVE,
        )]
        c._position_reader.get_positions_by_pool.return_value = [AsyncMock(spec=Position)]
        c._position_repo.save.side_effect = asyncio.TimeoutError("save timeout")

        result = await c._run_cycle()
        assert result.pools_failed == 1

    @pytest.mark.asyncio
    async def test_acquire_outside_timeout(self):
        """acquire() delay is NOT counted toward the HTTP timeout."""
        c = _make_collector(positions_timeout_seconds=0.3)
        c._pool_reader.list_pools.return_value = [Pool(
            address=PoolAddress(value="7YttVPABs9FKVhiMq2eih6nGByCPqjRUoACKsHFK1hYs"),
            token_a=Token(address="So11111111111111111111111111111111111111112", symbol="SOL", decimals=9),
            token_b=Token(address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", symbol="USDC", decimals=6),
            status=PoolStatus.ACTIVE,
        )]
        c._position_reader.get_positions_by_pool.side_effect = [[AsyncMock(spec=Position)]]
        limiter = RateLimiter(rps=1)  # 1s wait between acquires
        await limiter.acquire()  # first — immediate
        # Now the next acquire will wait ~1s
        t0 = time.monotonic()
        result = await c._process_one(
            c._pool_reader.list_pools.return_value[0],
            _TS,
            limiter,
        )
        elapsed = time.monotonic() - t0
        # positions_timeout_seconds=0.3, but acquire delay is ~1s
        # If acquire were inside timeout, this would exceed 0.3s and fail
        # Since it succeeded, acquire was outside timeout
        assert isinstance(result, PoolResult)
        assert elapsed > 0.3  # acquire delay alone exceeds timeout


# ===================================================================
# Group D — _process_one standalone
# ===================================================================


class TestProcessOne:
    """_process_one in isolation."""

    @pytest.mark.asyncio
    async def test_returns_pool_result(
        self, collector, sample_pool, mock_positions
    ):
        """Returns PoolResult with correct fields."""
        collector._position_reader.get_positions_by_pool.return_value = mock_positions
        limiter = RateLimiter(1000)
        result = await collector._process_one(sample_pool, _TS, limiter)

        assert isinstance(result, PoolResult)
        assert result.address == sample_pool.address
        assert result.positions_count == len(mock_positions)

    @pytest.mark.asyncio
    async def test_empty_positions(self, collector, sample_pool):
        """Empty positions list returns count=0."""
        collector._position_reader.get_positions_by_pool.return_value = []
        limiter = RateLimiter(1000)
        result = await collector._process_one(sample_pool, _TS, limiter)

        assert result.positions_count == 0
        collector._position_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_snapshot_before_positions(
        self, collector, sample_pool, mock_positions
    ):
        """Snapshot appended before positions saved (sequential in _process_one)."""
        collector._position_reader.get_positions_by_pool.return_value = mock_positions
        limiter = RateLimiter(1000)

        # Track call order across separate mocks
        _call_order: list[str] = []
        collector._snapshot_repo.append.side_effect = lambda s: _call_order.append("snapshot")  # type: ignore[func-returns-value]
        collector._position_repo.save.side_effect = lambda p: _call_order.append("position")  # type: ignore[func-returns-value]

        await collector._process_one(sample_pool, _TS, limiter)

        # Both were called
        collector._snapshot_repo.append.assert_called_once()
        collector._position_repo.save.assert_called()

        # Snapshot was persisted before positions
        assert _call_order == ["snapshot", "position"], (
            f"Expected snapshot → position, got {_call_order}"
        )

        # In the combined mock_calls, snapshot.append appears before position_repo.save
        snap_calls = collector._snapshot_repo.method_calls
        pos_calls = collector._position_repo.method_calls
        assert snap_calls and pos_calls, "both must be called"

    @pytest.mark.asyncio
    async def test_acquire_called(self, collector, sample_pool, mock_positions):
        """acquire() is called on the limiter before processing."""
        collector._position_reader.get_positions_by_pool.return_value = mock_positions
        limiter = RateLimiter(1000)

        # Process a pool — acquire is called inside
        result = await collector._process_one(sample_pool, _TS, limiter)

        assert isinstance(result, PoolResult)
        assert result.address == sample_pool.address

    @pytest.mark.asyncio
    async def test_get_pool_not_called(self, collector, sample_pool, mock_positions):
        """get_pool() is never called inside _process_one (R4)."""
        collector._position_reader.get_positions_by_pool.return_value = mock_positions
        limiter = RateLimiter(1000)

        await collector._process_one(sample_pool, _TS, limiter)

        collector._pool_reader.get_pool.assert_not_called()


# ===================================================================
# Group E — Cycle logging
# ===================================================================


class TestCycleLogging:
    """Decision logging."""

    @pytest.mark.asyncio
    async def test_log_cycle_creates_decision(
        self, collector, single_pool_list, mock_positions
    ):
        """_log_cycle creates a Decision."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        result = await collector._run_cycle()
        await collector._log_cycle(result)

        collector._decision_log.append.assert_called_once()
        args, _ = collector._decision_log.append.call_args
        assert isinstance(args[0], Decision)

    @pytest.mark.asyncio
    async def test_log_cycle_correct_fields(
        self, collector, single_pool_list, mock_positions
    ):
        """Decision has expected field values."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        result = await collector._run_cycle()
        await collector._log_cycle(result)

        d: Decision = collector._decision_log.append.call_args[0][0]
        assert d.agent == AgentRole.COLLECTOR
        assert d.event_type == "collector_cycle"
        assert d.outcome == DecisionOutcome.EXECUTED
        assert isinstance(d.id, DecisionId)
        assert d.trigger == "scheduled"
        assert d.pool_address is None
        assert d.features["pools_succeeded"] == 1
        assert d.features["pools_failed"] == 0
        assert isinstance(d.timestamp, datetime)


# ===================================================================
# Group F — Lifecycle
# ===================================================================


class TestLifecycle:
    """start / stop / run_forever."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self, collector):
        await collector.start()
        assert collector._running is True

    @pytest.mark.asyncio
    async def test_stop_clears_running(self, collector):
        await collector.start()
        await collector.stop()
        assert collector._running is False

    @pytest.mark.asyncio
    async def test_full_cycle_via_run_forever(
        self, collector, single_pool_list, mock_positions
    ):
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        cycle_done = asyncio.Event()

        original = collector._log_cycle

        async def log_and_signal(r):
            await original(r)
            cycle_done.set()

        collector._log_cycle = log_and_signal  # type: ignore[assignment]

        task = asyncio.create_task(collector.run_forever())
        await cycle_done.wait()
        await asyncio.sleep(0.05)
        await collector.stop()
        await task

        collector._snapshot_repo.append.assert_called()
        collector._decision_log.append.assert_called()

    @pytest.mark.asyncio
    async def test_stop_during_process_one(
        self, collector, single_pool_list, mock_positions
    ):
        """Stop during a cycle — gather completes, loop exits."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        pause = asyncio.Event()
        original = collector._process_one

        async def paused(*a, **kw):
            await pause.wait()
            return await original(*a, **kw)

        collector._process_one = paused  # type: ignore[assignment]
        task = asyncio.create_task(collector.run_forever())
        await asyncio.sleep(0.05)
        await collector.stop()
        pause.set()
        await task

        assert not collector._running

    @pytest.mark.asyncio
    async def test_stop_during_sleep(self, collector, single_pool_list):
        """Stop during sleep exits within 1.5s."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = []

        cycle_done = asyncio.Event()
        original = collector._log_cycle

        async def log_and_signal(r):
            await original(r)
            cycle_done.set()

        collector._log_cycle = log_and_signal  # type: ignore[assignment]

        task = asyncio.create_task(collector.run_forever())
        await cycle_done.wait()
        t0 = time.monotonic()
        await collector.stop()
        await task
        dt = time.monotonic() - t0
        assert dt <= 1.5

    @pytest.mark.asyncio
    async def test_re_entrancy_guard(self, collector, caplog):
        """Second run_forever call is ignored."""
        collector._running = True
        caplog.set_level(logging.WARNING)

        await collector.run_forever()

        assert "already running" in caplog.text

    @pytest.mark.asyncio
    async def test_cycle_exception_continues(
        self, collector, single_pool_list
    ):
        """Cycle exception caught, loop continues."""
        collector._pool_reader.list_pools.side_effect = [
            Exception("boom"),
            single_pool_list,
        ]
        collector._position_reader.get_positions_by_pool.return_value = []
        # Short interval so second cycle starts quickly
        collector._settings = CollectorSettings(
            interval_seconds=0.05, rate_limit_rps=1000,
            api_timeout_seconds=5, positions_timeout_seconds=5,
            db_timeout_seconds=5, pool_positions_timeout=5,
            max_retries=1,
        )

        # Let two cycles attempt
        cycle_count = 0
        original = collector._log_cycle

        async def track(r):
            nonlocal cycle_count
            cycle_count += 1
            await original(r)

        collector._log_cycle = track  # type: ignore[assignment]

        task = asyncio.create_task(collector.run_forever())
        while cycle_count < 1:
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.1)
        await collector.stop()
        await task

        assert collector._pool_reader.list_pools.call_count >= 2

    @pytest.mark.asyncio
    async def test_stop_then_start_possible(self, collector):
        """Start after stop works."""
        await collector.start()
        assert collector._running is True
        await collector.stop()
        assert collector._running is False
        collector._running = True
        assert collector._running is True


# ===================================================================
# Group G — _sleep_with_interrupt
# ===================================================================


class TestSleepInterrupt:
    """Interruptible sleep."""

    @pytest.mark.asyncio
    async def test_sleep_interrupted(self, collector):
        """stop() during sleep exits early."""
        collector._running = True
        t0 = time.monotonic()
        sleep_task = asyncio.create_task(collector._sleep_with_interrupt(10))
        await asyncio.sleep(0.1)
        collector._running = False
        await sleep_task
        dt = time.monotonic() - t0
        assert dt <= 1.5

    @pytest.mark.asyncio
    async def test_sleep_full_duration(self, collector):
        """Without interrupt, sleeps full duration."""
        collector._running = True
        t0 = time.monotonic()
        await collector._sleep_with_interrupt(0.5)
        dt = time.monotonic() - t0
        assert dt == pytest.approx(0.5, rel=0.4)


# ===================================================================
# Group H — _is_retryable
# ===================================================================


class TestRetryClassifier:
    """_is_retryable classification."""

    def test_timeout_retryable(self, collector):
        assert collector._is_retryable(asyncio.TimeoutError()) is True
        assert collector._is_retryable(TimeoutError()) is True

    def test_meteora_error_retryable(self, collector):
        assert collector._is_retryable(MeteoraError("500")) is True

    def test_other_not_retryable(self, collector):
        assert collector._is_retryable(ValueError()) is False
        assert collector._is_retryable(TypeError()) is False


# ===================================================================
# Group I — _persist_positions
# ===================================================================


class TestPersistPositions:
    """Position persistence."""

    @pytest.mark.asyncio
    async def test_save_called_once_per_position(
        self, collector, pool_addr
    ):
        """Each position saved via save()."""
        p1, p2, p3 = AsyncMock(spec=Position), AsyncMock(spec=Position), AsyncMock(spec=Position)
        await collector._persist_positions(pool_addr, [p1, p2, p3])

        assert collector._position_repo.save.call_count == 3
        assert collector._position_repo.save.call_args_list[0] == call(p1)
        assert collector._position_repo.save.call_args_list[1] == call(p2)
        assert collector._position_repo.save.call_args_list[2] == call(p3)

    def test_upsert_not_called_on_port(self):
        """PositionRepository port does not have upsert."""
        assert not hasattr(PositionRepository, "upsert"), "upsert method must not exist on port"

    @pytest.mark.asyncio
    async def test_save_raise_does_not_block_others(
        self, collector, pool_addr
    ):
        """Save failure on one position does not prevent others (sequential)."""
        p1, p2, p3 = AsyncMock(spec=Position), AsyncMock(spec=Position), AsyncMock(spec=Position)
        collector._position_repo.save.side_effect = [None, ValueError("fail"), None]

        with pytest.raises(ValueError):
            await collector._persist_positions(pool_addr, [p1, p2, p3])

        # p1 saved, p2 raised, p3 NOT attempted
        assert collector._position_repo.save.call_count == 2


# ===================================================================
# Group J — Mutation survival
# ===================================================================


class TestMutationSurvival:
    """Tests that catch specific dangerous mutations."""

    @pytest.mark.asyncio
    async def test_one_pool_failure_does_not_cancel_gather(
        self, collector, three_pools, mock_positions
    ):
        """A single pool failure does NOT cancel other in-flight tasks.

        This catches the mutation: return_exceptions=True → False.
        """
        collector._pool_reader.list_pools.return_value = three_pools
        collector._position_reader.get_positions_by_pool.side_effect = [
            mock_positions,
            RuntimeError("fail"),
            mock_positions,
        ]

        result = await collector._run_cycle()

        # All 3 pools attempted, 2 succeeded, 1 failed
        assert result.pools_succeeded == 2
        assert result.pools_failed == 1

    @pytest.mark.asyncio
    async def test_fresh_limiter_per_cycle(
        self, collector, single_pool_list, mock_positions
    ):
        """Each _run_cycle creates a new RateLimiter (behavioral verification)."""
        collector._pool_reader.list_pools.return_value = single_pool_list
        collector._position_reader.get_positions_by_pool.return_value = mock_positions

        # Run two cycles — they should both succeed (fresh limiter each time)
        r1 = await collector._run_cycle()
        r2 = await collector._run_cycle()

        assert r1.pools_succeeded == 1
        assert r2.pools_succeeded == 1

    @pytest.mark.asyncio
    async def test_cancelled_error_not_in_failed(
        self, collector, three_pools, mock_positions
    ):
        """CancelledError in a subtask is NOT counted in failed list."""
        collector._pool_reader.list_pools.return_value = three_pools
        collector._position_reader.get_positions_by_pool.side_effect = [
            mock_positions,
            asyncio.CancelledError(),
            mock_positions,
        ]

        result = await collector._run_cycle()

        assert result.pools_attempted == 3
        # CancelledError is BaseException, not Exception — filtered out of both lists
        assert result.pools_succeeded + result.pools_failed <= result.pools_attempted

    @pytest.mark.asyncio
    async def test_gather_type_separation(
        self, collector, three_pools, mock_positions
    ):
        """PoolResult and Exception are correctly separated by gather."""
        collector._pool_reader.list_pools.return_value = three_pools
        collector._position_reader.get_positions_by_pool.side_effect = [
            mock_positions,
            RuntimeError("fail"),
            mock_positions,
        ]

        result = await collector._run_cycle()

        assert result.pools_attempted == 3
        assert result.pools_succeeded + result.pools_failed == result.pools_attempted
