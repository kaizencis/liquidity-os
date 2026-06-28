"""Unit tests for shared.entities module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from shared.entities.decision import Decision
from shared.entities.pool import Pool
from shared.entities.position import Position
from shared.enums import (
    AgentRole,
    DecisionOutcome,
    PoolStatus,
    PositionSide,
    PositionStatus,
)
from shared.identifiers import DecisionId, PoolAddress, PositionAddress
from shared.value_objects.liquidity import Liquidity
from shared.value_objects.price import Price, PriceRange
from shared.value_objects.token import Token, TokenAmount

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
def position_address() -> PositionAddress:
    return PositionAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n")


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------


class TestPool:
    """Tests for Pool entity."""

    def test_create_pool(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        pool = Pool(
            address=pool_address,
            token_a=SOL,
            token_b=USDC,
        )
        assert pool.address == pool_address
        assert pool.token_a == SOL
        assert pool.token_b == USDC
        assert pool.status == PoolStatus.ACTIVE

    def test_immutable(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        pool = Pool(address=pool_address, token_a=SOL, token_b=USDC)
        with pytest.raises(Exception):
            pool.status = PoolStatus.CLOSED  # type: ignore[misc]

    def test_is_active_true(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        pool = Pool(address=pool_address, token_a=SOL, token_b=USDC, status=PoolStatus.ACTIVE)
        assert pool.is_active

    def test_is_active_false(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        pool = Pool(address=pool_address, token_a=SOL, token_b=USDC, status=PoolStatus.CLOSED)
        assert not pool.is_active

    def test_pair_property(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        pool = Pool(address=pool_address, token_a=SOL, token_b=USDC)
        assert pool.pair == "SOL/USDC"

    def test_string_representation(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        pool = Pool(address=pool_address, token_a=SOL, token_b=USDC)
        assert str(pool) == "Pool(SOL/USDC, active)"

    def test_equal_same_address(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        a = Pool(address=pool_address, token_a=SOL, token_b=USDC)
        b = Pool(address=pool_address, token_a=SOL, token_b=USDC)
        assert a == b

    def test_not_equal_different_address(self, SOL: Token, USDC: Token) -> None:
        a = Pool(address=PoolAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"),
                 token_a=SOL, token_b=USDC)
        b = Pool(address=PoolAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"),
                 token_a=SOL, token_b=USDC)
        assert a != b

    def test_hashable(self, pool_address: PoolAddress, SOL: Token, USDC: Token) -> None:
        pool = Pool(address=pool_address, token_a=SOL, token_b=USDC)
        pool_set = {pool}
        assert pool in pool_set


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------


class TestPosition:
    """Tests for Position entity."""

    def test_create_position(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        position = Position(
            address=position_address,
            pool_address=pool_address,
        )
        assert position.address == position_address
        assert position.pool_address == pool_address
        assert position.status == PositionStatus.ACTIVE

    def test_immutable(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        position = Position(address=position_address, pool_address=pool_address)
        with pytest.raises(Exception):
            position.status = PositionStatus.CLOSED  # type: ignore[misc]

    def test_is_active_true(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        position = Position(
            address=position_address,
            pool_address=pool_address,
            status=PositionStatus.ACTIVE,
        )
        assert position.is_active

    def test_is_active_false(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        position = Position(
            address=position_address,
            pool_address=pool_address,
            status=PositionStatus.CLOSED,
        )
        assert not position.is_active

    def test_has_liquidity_true(
        self, position_address: PositionAddress, pool_address: PoolAddress, SOL: Token
    ) -> None:
        liquidity = Liquidity(amount=TokenAmount(token=SOL, raw=1_000_000_000))
        position = Position(
            address=position_address,
            pool_address=pool_address,
            liquidity=liquidity,
        )
        assert position.has_liquidity

    def test_has_liquidity_false(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        position = Position(
            address=position_address,
            pool_address=pool_address,
        )
        assert not position.has_liquidity

    def test_string_representation(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        position = Position(address=position_address, pool_address=pool_address)
        assert str(position) == f"Position({position_address}, active)"

    def test_equal_same_address(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        a = Position(address=position_address, pool_address=pool_address)
        b = Position(address=position_address, pool_address=pool_address)
        assert a == b

    def test_not_equal_different_address(self, pool_address: PoolAddress) -> None:
        a = Position(
            address=PositionAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"),
            pool_address=pool_address,
        )
        b = Position(
            address=PositionAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"),
            pool_address=pool_address,
        )
        assert a != b

    def test_hashable(
        self, position_address: PositionAddress, pool_address: PoolAddress
    ) -> None:
        position = Position(address=position_address, pool_address=pool_address)
        position_set = {position}
        assert position in position_set


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


class TestDecision:
    """Tests for Decision entity."""

    def test_create_decision(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
        )
        assert decision.agent == AgentRole.ORACLE
        assert decision.event_type == "alert_triggered"
        assert decision.outcome == DecisionOutcome.PENDING

    def test_immutable(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
        )
        with pytest.raises(Exception):
            decision.outcome = DecisionOutcome.EXECUTED  # type: ignore[misc]

    def test_is_pending_true(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
            outcome=DecisionOutcome.PENDING,
        )
        assert decision.is_pending

    def test_is_pending_false(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
            outcome=DecisionOutcome.EXECUTED,
        )
        assert not decision.is_pending

    def test_is_terminal_true(self) -> None:
        for outcome in [
            DecisionOutcome.EXECUTED,
            DecisionOutcome.REJECTED,
            DecisionOutcome.CANCELLED,
            DecisionOutcome.EXPIRED,
        ]:
            decision = Decision(
                id=DecisionId.generate(),
                agent=AgentRole.ORACLE,
                event_type="test",
                outcome=outcome,
            )
            assert decision.is_terminal

    def test_is_terminal_false(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="test",
            outcome=DecisionOutcome.PENDING,
        )
        assert not decision.is_terminal

    def test_timestamp_default(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="test",
        )
        assert isinstance(decision.timestamp, datetime)
        assert decision.timestamp.tzinfo is not None

    def test_string_representation(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="alert_triggered",
            outcome=DecisionOutcome.PENDING,
        )
        result = str(decision)
        assert "Decision(" in result
        assert "oracle" in result
        assert "pending" in result

    def test_equal_same_id(self) -> None:
        did = DecisionId.generate()
        a = Decision(id=did, agent=AgentRole.ORACLE, event_type="test")
        b = Decision(id=did, agent=AgentRole.NAVIGATOR, event_type="other")
        assert a == b

    def test_not_equal_different_id(self) -> None:
        a = Decision(id=DecisionId.generate(), agent=AgentRole.ORACLE, event_type="test")
        b = Decision(id=DecisionId.generate(), agent=AgentRole.ORACLE, event_type="test")
        assert a != b

    def test_hashable(self) -> None:
        decision = Decision(
            id=DecisionId.generate(),
            agent=AgentRole.ORACLE,
            event_type="test",
        )
        decision_set = {decision}
        assert decision in decision_set


# ---------------------------------------------------------------------------
# Cross-entity: Pool + Position relationship
# ---------------------------------------------------------------------------


class TestPoolPositionRelationship:
    """Tests for Pool ↔ Position relationship."""

    def test_position_references_pool(
        self, pool_address: PoolAddress, position_address: PositionAddress
    ) -> None:
        position = Position(
            address=position_address,
            pool_address=pool_address,
        )
        assert position.pool_address == pool_address

    def test_positions_share_pool(
        self, pool_address: PoolAddress
    ) -> None:
        pos1 = Position(
            address=PositionAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"),
            pool_address=pool_address,
        )
        pos2 = Position(
            address=PositionAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"),
            pool_address=pool_address,
        )
        assert pos1.pool_address == pos2.pool_address
