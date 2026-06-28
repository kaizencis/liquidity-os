"""Tests for decision_log.query module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from decision_log.query import DecisionQuery
from shared.entities.decision import Decision
from shared.enums import AgentRole, DecisionOutcome
from shared.identifiers import DecisionId


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_decisions() -> list[Decision]:
    """Create sample decisions for testing."""
    return [
        Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
            trigger="volatility > 0.15",
            outcome=DecisionOutcome.PENDING,
        ),
        Decision(
            id=DecisionId.generate(),
            agent=AgentRole.NAVIGATOR,
            event_type="rebalance_proposed",
            trigger="liquidity_out_of_range",
            outcome=DecisionOutcome.APPROVED,
        ),
        Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
            trigger="volume_spike",
            outcome=DecisionOutcome.EXECUTED,
        ),
    ]


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def query(mock_session: AsyncMock) -> DecisionQuery:
    """Create a DecisionQuery with mock session."""
    return DecisionQuery(session=mock_session)


# ---------------------------------------------------------------------------
# DecisionQuery — Query All
# ---------------------------------------------------------------------------


class TestDecisionQueryAll:
    """Tests for querying all decisions."""

    @pytest.mark.asyncio
    async def test_query_all_returns_list(
        self, query: DecisionQuery, sample_decisions: list[Decision]
    ) -> None:
        """Verify query returns list of decisions."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            self._create_mock_model(d) for d in sample_decisions
        ]
        query.session.execute = AsyncMock(return_value=mock_result)

        result = await query.query_all()

        assert len(result) == len(sample_decisions)

    @pytest.mark.asyncio
    async def test_query_all_with_limit(
        self, query: DecisionQuery, sample_decisions: list[Decision]
    ) -> None:
        """Verify query respects limit parameter."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            self._create_mock_model(d) for d in sample_decisions[:2]
        ]
        query.session.execute = AsyncMock(return_value=mock_result)

        result = await query.query_all(limit=2)

        assert len(result) == 2

    def _create_mock_model(self, decision: Decision) -> MagicMock:
        """Create a mock model from decision."""
        return MagicMock(
            id=decision.id.value,
            agent=decision.agent.value,
            event_type=decision.event_type,
            trigger_rule=decision.trigger,
            pool_address=None,
            outcome=decision.outcome.value,
            timestamp=decision.timestamp,
            features=decision.features,
            metadata_=decision.metadata,
        )


# ---------------------------------------------------------------------------
# DecisionQuery — Query By Agent
# ---------------------------------------------------------------------------


class TestDecisionQueryByAgent:
    """Tests for querying decisions by agent."""

    @pytest.mark.asyncio
    async def test_query_by_agent_filters_correctly(
        self, query: DecisionQuery, sample_decisions: list[Decision]
    ) -> None:
        """Verify query filters by agent."""
        oracle_decisions = [d for d in sample_decisions if d.agent == AgentRole.ORACLE]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(
                id=d.id.value,
                agent=d.agent.value,
                event_type=d.event_type,
                trigger_rule=d.trigger,
                pool_address=None,
                outcome=d.outcome.value,
                timestamp=d.timestamp,
                features=d.features,
                metadata_=d.metadata,
            )
            for d in oracle_decisions
        ]
        query.session.execute = AsyncMock(return_value=mock_result)

        result = await query.query_by_agent(AgentRole.ORACLE)

        assert all(d.agent == AgentRole.ORACLE for d in result)


# ---------------------------------------------------------------------------
# DecisionQuery — Query By Outcome
# ---------------------------------------------------------------------------


class TestDecisionQueryByOutcome:
    """Tests for querying decisions by outcome."""

    @pytest.mark.asyncio
    async def test_query_by_outcome_filters_correctly(
        self, query: DecisionQuery, sample_decisions: list[Decision]
    ) -> None:
        """Verify query filters by outcome."""
        pending_decisions = [d for d in sample_decisions if d.outcome == DecisionOutcome.PENDING]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(
                id=d.id.value,
                agent=d.agent.value,
                event_type=d.event_type,
                trigger_rule=d.trigger,
                pool_address=None,
                outcome=d.outcome.value,
                timestamp=d.timestamp,
                features=d.features,
                metadata_=d.metadata,
            )
            for d in pending_decisions
        ]
        query.session.execute = AsyncMock(return_value=mock_result)

        result = await query.query_by_outcome(DecisionOutcome.PENDING)

        assert all(d.outcome == DecisionOutcome.PENDING for d in result)


# ---------------------------------------------------------------------------
# DecisionQuery — Query By Time Range
# ---------------------------------------------------------------------------


class TestDecisionQueryByTimeRange:
    """Tests for querying decisions by time range."""

    @pytest.mark.asyncio
    async def test_query_by_time_range_filters_correctly(
        self, query: DecisionQuery, sample_decisions: list[Decision]
    ) -> None:
        """Verify query filters by time range."""
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 12, 31, tzinfo=timezone.utc)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(
                id=d.id.value,
                agent=d.agent.value,
                event_type=d.event_type,
                trigger_rule=d.trigger,
                pool_address=None,
                outcome=d.outcome.value,
                timestamp=d.timestamp,
                features=d.features,
                metadata_=d.metadata,
            )
            for d in sample_decisions
        ]
        query.session.execute = AsyncMock(return_value=mock_result)

        result = await query.query_by_time_range(start, end)

        assert len(result) == len(sample_decisions)


# ---------------------------------------------------------------------------
# DecisionQuery — Count
# ---------------------------------------------------------------------------


class TestDecisionQueryCount:
    """Tests for counting decisions."""

    @pytest.mark.asyncio
    async def test_count_returns_integer(self, query: DecisionQuery) -> None:
        """Verify count returns integer."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        query.session.execute = AsyncMock(return_value=mock_result)

        result = await query.count()

        assert isinstance(result, int)
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_agent(self, query: DecisionQuery) -> None:
        """Verify count filters by agent."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        query.session.execute = AsyncMock(return_value=mock_result)

        result = await query.count(agent=AgentRole.ORACLE)

        assert result == 3
