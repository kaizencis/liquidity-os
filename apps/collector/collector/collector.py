"""Collector Service — periodic DEX data ingestion from Meteora DLMM.

[WHY] Central nervous system of Liquidity OS.
      Polls Meteora DLMM on a schedule, persists snapshots and positions.
      Rate-limited, retried, timed-out operations with graceful shutdown.
[OWNERSHIP] Collector Service — orchestration.
[DEPENDENTS] Allowed: apps (via DI wiring).
             Forbidden: shared, agents, other packages.
[EXAMPLE]
    settings = CollectorSettings()
    manager = DatabaseSessionManager(DatabaseSettings())
    repo = PostgresSnapshotRepository(manager)
    collector = CollectorService(
        pool_reader=pool_adapter,
        position_reader=position_adapter,
        pool_repo=pool_repo,
        position_repo=position_repo,
        snapshot_repo=repo,
        decision_log=decision_log,
        settings=settings,
    )
    await collector.run_forever()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from collector.rate_limiter import RateLimiter
from collector.retry import _default_is_retryable, retry_with_backoff
from collector.settings import CollectorSettings
from collector.snapshotter import Snapshotter
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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PoolResult:
    """Result of processing a single pool."""

    address: PoolAddress
    positions_count: int


@dataclass(frozen=True)
class CycleResult:
    """Result of one collector cycle."""

    pools_attempted: int
    pools_succeeded: int
    pools_failed: int
    duration_seconds: float
    cycle_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CollectorService:
    """Orchestrates periodic collection of pool data from Meteora DLMM.

    Responsibilities:
        - Discover pools via list_pools()
        - Fetch positions for each pool concurrently
        - Create and persist snapshots
        - Persist positions with eventual consistency
        - Rate-limit all outbound HTTP calls
        - Retry transient failures with exponential backoff
        - Graceful shutdown via interruptible sleep

    R2: Every HTTP call is wrapped in asyncio.wait_for.
        RateLimiter.acquire() is called BEFORE the timeout — never inside it.
    R4: Pool entities from list_pools() are used directly.
        No redundant get_pool() call.
    """

    def __init__(
        self,
        pool_reader: PoolReader,
        position_reader: PositionReader,
        pool_repo: PoolRepository,
        position_repo: PositionRepository,
        snapshot_repo: SnapshotRepository,
        decision_log: DecisionLog,
        settings: CollectorSettings,
    ) -> None:
        """Initialize CollectorService with injected dependencies.

        Args:
            pool_reader: Port for reading pool data (e.g., MeteoraPoolAdapter).
            position_reader: Port for reading position data.
            pool_repo: Port for persisting pool entities.
            position_repo: Port for persisting position entities.
            snapshot_repo: Port for appending snapshots (append-only).
            decision_log: Port for logging cycle decisions.
            settings: Frozen collector configuration.
        """
        self._pool_reader = pool_reader
        self._position_reader = position_reader
        self._pool_repo = pool_repo
        self._position_repo = position_repo
        self._snapshot_repo = snapshot_repo
        self._decision_log = decision_log
        self._settings = settings

        self._running: bool = False

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the collector. Sets running flag.

        Dependencies (pool_reader, position_reader, repos) are injected
        via constructor and assumed to be ready.
        """
        self._running = True
        logger.info("CollectorService started")

    async def run_forever(self) -> None:
        """Run collection cycles indefinitely until stop() is called.

        Re-entrancy guard: if already running, subsequent calls are no-ops.

        Each cycle:
            1. Fetches all pools via list_pools()
            2. Processes each pool concurrently via gather
            3. Logs cycle result to decision_log
            4. Sleeps for interval (interruptible by stop())
        """
        if self._running:
            logger.warning("run_forever called while already running — ignoring")
            return

        await self.start()

        while self._running:
            cycle_start = time.monotonic()
            try:
                result = await self._run_cycle()
                await self._log_cycle(result)
                logger.info(
                    "Cycle: %d pools, %d succeeded, %d failed in %.2fs",
                    result.pools_attempted,
                    result.pools_succeeded,
                    result.pools_failed,
                    result.duration_seconds,
                )
            except Exception:
                logger.exception("Cycle failed with unhandled error")
            finally:
                elapsed = time.monotonic() - cycle_start
                sleep_duration = max(0.0, self._settings.interval_seconds - elapsed)
                await self._sleep_with_interrupt(sleep_duration)

    async def stop(self) -> None:
        """Signal the collector to stop after the current cycle completes.

        If a cycle is in progress, in-flight tasks complete normally.
        The sleep loop exits on the next 0.5s tick.
        """
        self._running = False
        logger.info("CollectorService stopping")

    # ------------------------------------------------------------------
    # Core cycle logic
    # ------------------------------------------------------------------

    async def _run_cycle(self) -> CycleResult:
        """Execute one collection cycle.

        Returns:
            CycleResult with statistics about the cycle.
        """
        cycle_start_mono = time.monotonic()
        cycle_timestamp = datetime.now(timezone.utc)

        # Fresh RateLimiter per cycle — scope includes ALL HTTP requests.
        # acquire() before list_pools() per contract: every HTTP request
        # including retries must call acquire().
        limiter = RateLimiter(self._settings.rate_limit_rps)

        # R4: list_pools() returns list[Pool] — use Pool entities directly.
        #     No redundant get_pool() call.
        await limiter.acquire()
        pools = await retry_with_backoff(
            self._fetch_pools_with_timeout,
            is_retryable=self._is_retryable,
        )

        # R4: Pass Pool entity (not PoolAddress) to _process_one.
        tasks = [
            self._process_one(pool, cycle_timestamp, limiter)
            for pool in pools
        ]

        # gather with return_exceptions=True ensures one pool failure
        # does not cancel other in-flight tasks.
        results = await asyncio.gather(*tasks, return_exceptions=True)

        succeeded = [r for r in results if isinstance(r, PoolResult)]
        failed = [r for r in results if isinstance(r, Exception)]

        elapsed = time.monotonic() - cycle_start_mono

        return CycleResult(
            pools_attempted=len(pools),
            pools_succeeded=len(succeeded),
            pools_failed=len(failed),
            duration_seconds=elapsed,
            cycle_timestamp=cycle_timestamp,
        )

    async def _process_one(
        self,
        pool: Pool,
        cycle_timestamp: datetime,
        limiter: RateLimiter,
    ) -> PoolResult | None:
        """Process a single pool: fetch positions, create snapshot, persist.

        R2: HTTP calls wrapped in asyncio.wait_for. acquire() outside timeout.
        R4: Pool data already available from list_pools() — no get_pool() call.

        Args:
            pool: Pool entity from list_pools().
            cycle_timestamp: Single timestamp for this cycle.
            limiter: Per-cycle rate limiter.

        Returns:
            PoolResult if successful, None if pool has no positions.

        Raises:
            Exception: Propagated to gather when retries exhausted.
        """
        # Phase 1: Fetch positions (rate-limited, retried, timed out).
        #         R2: acquire() BEFORE retry — not wrapped in wait_for.
        await limiter.acquire()
        positions = await retry_with_backoff(
            self._fetch_positions_with_timeout,
            pool.address,
            is_retryable=self._is_retryable,
        )

        # Phase 2: Create snapshot from existing pool data (no extra API call).
        #         R4: pool entity already in memory from list_pools().
        snapshot = Snapshotter.from_pool(
            pool,
            timestamp=cycle_timestamp,
        )

        # Phase 3: Persist snapshot (timed out individually).
        await asyncio.wait_for(
            self._persist_snapshot(snapshot),
            timeout=self._settings.db_timeout_seconds,
        )

        # Phase 4: Persist positions (timed out as aggregate batch).
        #         Partial writes accepted — eventual consistency.
        await asyncio.wait_for(
            self._persist_positions(pool.address, positions),
            timeout=self._settings.pool_positions_timeout,
        )

        return PoolResult(address=pool.address, positions_count=len(positions))

    # ------------------------------------------------------------------
    # Timeout-wrapped HTTP helpers (R2)
    # ------------------------------------------------------------------

    async def _fetch_pools_with_timeout(self) -> list[Pool]:
        """Fetch all pools with timeout. One HTTP call, many pools.

        R2: asyncio.wait_for wraps ONLY the HTTP call.
            acquire() is called by the caller before this helper.
        """
        return await asyncio.wait_for(
            self._pool_reader.list_pools(),
            timeout=self._settings.api_timeout_seconds,
        )

    async def _fetch_positions_with_timeout(
        self,
        address: PoolAddress,
    ) -> list[Position]:
        """Fetch positions for a pool with timeout.

        R2: Each retry attempt gets its own timeout window because
            retry_with_backoff re-invokes this function on each attempt.
            acquire() is called by the caller before this helper.
        """
        return await asyncio.wait_for(
            self._position_reader.get_positions_by_pool(address),
            timeout=self._settings.positions_timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _persist_positions(
        self,
        pool_address: PoolAddress,
        positions: list[Position],
    ) -> None:
        """Persist all positions for a pool.

        Eventually consistent: partial writes are accepted.
        Next cycle reconciles via idempotent upserts.
        """
        for position in positions:
            await self._position_repo.save(position)

    async def _persist_snapshot(self, snapshot: Snapshot) -> None:
        """Persist a single snapshot."""
        await self._snapshot_repo.append(snapshot)

    # ------------------------------------------------------------------
    # Retry classifier
    # ------------------------------------------------------------------

    def _is_retryable(self, exc: Exception) -> bool:
        """Determine if an exception should trigger a retry.

        Extends the default classifier (timeout errors) with MeteoraError
        for transient API failures (5xx, 429).
        """
        if _default_is_retryable(exc):
            return True
        if isinstance(exc, MeteoraError):
            return True
        return False

    # ------------------------------------------------------------------
    # Cycle logging
    # ------------------------------------------------------------------

    async def _log_cycle(self, result: CycleResult) -> None:
        """Log cycle result to DecisionLog."""
        await self._decision_log.append(
            Decision(
                id=DecisionId.generate(),
                agent=AgentRole.COLLECTOR,
                event_type="collector_cycle",
                trigger="scheduled",
                pool_address=None,
                outcome=DecisionOutcome.EXECUTED,
                features={
                    "pools_attempted": result.pools_attempted,
                    "pools_succeeded": result.pools_succeeded,
                    "pools_failed": result.pools_failed,
                    "duration_seconds": result.duration_seconds,
                },
                metadata={
                    "cycle_timestamp": result.cycle_timestamp.isoformat(),
                },
            )
        )

    # ------------------------------------------------------------------
    # Interruptible sleep
    # ------------------------------------------------------------------

    async def _sleep_with_interrupt(self, duration: float) -> None:
        """Sleep in short increments to allow stop() to interrupt quickly.

        Checks self._running on every 0.5s tick.
        """
        while duration > 0 and self._running:
            step = min(0.5, duration)
            await asyncio.sleep(step)
            duration -= step
