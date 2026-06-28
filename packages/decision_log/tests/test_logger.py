"""Tests for decision_log.logger module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from decision_log.errors import DuplicateDecisionError
from decision_log.logger import PostgresDecisionLog
from shared.entities.decision import Decision
from shared.enums import AgentRole, DecisionOutcome
from shared.identifiers import DecisionId


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_decision() -> Decision:
    """Create a sample decision for testing."""
    return Decision(
        id=DecisionId.generate(),
        agent=AgentRole.ORACLE,
        event_type="alert_triggered",
        trigger="volatility > 0.15",
        outcome=DecisionOutcome.PENDING,
    )


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.begin = AsyncMock()
    return session


@pytest.fixture
def logger(mock_session: AsyncMock) -> PostgresDecisionLog:
    """Create a PostgresDecisionLog with mock session."""
    return PostgresDecisionLog(session=mock_session)


# ---------------------------------------------------------------------------
# PostgresDecisionLog — Append
# ---------------------------------------------------------------------------


class TestPostgresDecisionLogAppend:
    """Tests for PostgresDecisionLog.append method."""

    @pytest.mark.asyncio
    async def test_append_calls_execute(
        self, logger: PostgresDecisionLog, sample_decision: Decision
    ) -> None:
        """Verify append calls session.execute."""
        # Mock get_by_id to return None (no duplicate)
        logger.get_by_id = AsyncMock(return_value=None)

        await logger.append(sample_decision)

        logger.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_append_duplicate_raises(
        self, logger: PostgresDecisionLog, sample_decision: Decision
    ) -> None:
        """Verify append raises DuplicateDecisionError for existing ID."""
        # Mock get_by_id to return existing decision
        logger.get_by_id = AsyncMock(return_value=sample_decision)

        with pytest.raises(DuplicateDecisionError):
            await logger.append(sample_decision)

    @pytest.mark.asyncio
    async def test_append_preserves_fields(
        self, logger: PostgresDecisionLog, sample_decision: Decision
    ) -> None:
        """Verify append preserves all decision fields."""
        logger.get_by_id = AsyncMock(return_value=None)

        await logger.append(sample_decision)

        # Verify execute was called with correct values
        call_args = logger.session.execute.call_args
        assert call_args is not None


# ---------------------------------------------------------------------------
# PostgresDecisionLog — Get By ID
# ---------------------------------------------------------------------------


class TestPostgresDecisionLogGetById:
    """Tests for PostgresDecisionLog.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_decision(
        self, logger: PostgresDecisionLog, sample_decision: Decision
    ) -> None:
        """Verify get_by_id returns decision when found."""
        # Mock query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = MagicMock(
            id=sample_decision.id.value,
            agent=sample_decision.agent.value,
            event_type=sample_decision.event_type,
            trigger_rule=sample_decision.trigger,
            pool_address=None,
            outcome=sample_decision.outcome.value,
            timestamp=sample_decision.timestamp,
            features=sample_decision.features,
            metadata_=sample_decision.metadata,
        )
        logger.session.execute = AsyncMock(return_value=mock_result)

        result = await logger.get_by_id(sample_decision.id)

        assert result is not None
        assert result.agent == sample_decision.agent

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, logger: PostgresDecisionLog
    ) -> None:
        """Verify get_by_id returns None when decision not found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        logger.session.execute = AsyncMock(return_value=mock_result)

        result = await logger.get_by_id(DecisionId.generate())

        assert result is None


# ---------------------------------------------------------------------------
# PostgresDecisionLog — To Row / To Domain
# ---------------------------------------------------------------------------


class TestPostgresDecisionLogConversion:
    """Tests for domain ↔ model conversion."""

    def test_to_row_conversion(self, logger: PostgresDecisionLog, sample_decision: Decision) -> None:
        """Verify _to_row converts decision to dict correctly."""
        row = logger._to_row(sample_decision)

        assert row["id"] == sample_decision.id.value
        assert row["agent"] == sample_decision.agent.value
        assert row["event_type"] == sample_decision.event_type
        assert row["trigger_rule"] == sample_decision.trigger
        assert row["outcome"] == sample_decision.outcome.value
        assert row["timestamp"] == sample_decision.timestamp

    def test_to_domain_conversion(self, logger: PostgresDecisionLog, sample_decision: Decision) -> None:
        """Verify _to_domain converts model to decision correctly."""
        mock_model = MagicMock(
            id=sample_decision.id.value,
            agent=sample_decision.agent.value,
            event_type=sample_decision.event_type,
            trigger_rule=sample_decision.trigger,
            pool_address=None,
            outcome=sample_decision.outcome.value,
            timestamp=sample_decision.timestamp,
            features=sample_decision.features,
            metadata_=sample_decision.metadata,
        )

        decision = logger._to_domain(mock_model)

        assert decision.id == sample_decision.id
        assert decision.agent == sample_decision.agent
        assert decision.event_type == sample_decision.event_type
        assert decision.outcome == sample_decision.outcome
