"""Unit tests for shared.enums module."""

from __future__ import annotations

import json

from shared.enums import (
    AgentRole,
    AlertSeverity,
    DecisionOutcome,
    PositionSide,
    PositionStatus,
    PoolStatus,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# PoolStatus
# ---------------------------------------------------------------------------


class TestPoolStatus:
    """Tests for PoolStatus enumeration."""

    def test_all_values_exist(self) -> None:
        assert PoolStatus.ACTIVE == "active"
        assert PoolStatus.PAUSED == "paused"
        assert PoolStatus.CLOSED == "closed"
        assert PoolStatus.MIGRATING == "migrating"

    def test_string_serialization(self) -> None:
        assert str(PoolStatus.ACTIVE) == "active"
        assert PoolStatus.ACTIVE.value == "active"

    def test_json_serializable(self) -> None:
        data = {"status": PoolStatus.ACTIVE}
        result = json.dumps(data)
        assert '"active"' in result

    def test_from_string(self) -> None:
        assert PoolStatus("active") == PoolStatus.ACTIVE

    def test_membership(self) -> None:
        assert PoolStatus.ACTIVE in PoolStatus


# ---------------------------------------------------------------------------
# PositionStatus
# ---------------------------------------------------------------------------


class TestPositionStatus:
    """Tests for PositionStatus enumeration."""

    def test_all_values_exist(self) -> None:
        assert PositionStatus.ACTIVE == "active"
        assert PositionStatus.CLOSED == "closed"
        assert PositionStatus.PENDING_CLOSE == "pending_close"
        assert PositionStatus.LIQUIDATED == "liquidated"

    def test_string_serialization(self) -> None:
        assert str(PositionStatus.ACTIVE) == "active"

    def test_json_serializable(self) -> None:
        data = {"status": PositionStatus.ACTIVE}
        result = json.dumps(data)
        assert '"active"' in result


# ---------------------------------------------------------------------------
# PositionSide
# ---------------------------------------------------------------------------


class TestPositionSide:
    """Tests for PositionSide enumeration."""

    def test_all_values_exist(self) -> None:
        assert PositionSide.BOTH == "both"
        assert PositionSide.BID_ONLY == "bid_only"
        assert PositionSide.ASK_ONLY == "ask_only"

    def test_string_serialization(self) -> None:
        assert str(PositionSide.BOTH) == "both"


# ---------------------------------------------------------------------------
# AgentRole
# ---------------------------------------------------------------------------


class TestAgentRole:
    """Tests for AgentRole enumeration."""

    def test_all_values_exist(self) -> None:
        assert AgentRole.ORACLE == "oracle"
        assert AgentRole.NAVIGATOR == "navigator"
        assert AgentRole.COLLECTOR == "collector"
        assert AgentRole.SYSTEM == "system"

    def test_string_serialization(self) -> None:
        assert str(AgentRole.ORACLE) == "oracle"

    def test_json_serializable(self) -> None:
        data = {"agent": AgentRole.COLLECTOR}
        result = json.dumps(data)
        assert '"collector"' in result

    def test_from_string(self) -> None:
        assert AgentRole("navigator") == AgentRole.NAVIGATOR


# ---------------------------------------------------------------------------
# DecisionOutcome
# ---------------------------------------------------------------------------


class TestDecisionOutcome:
    """Tests for DecisionOutcome enumeration."""

    def test_all_values_exist(self) -> None:
        assert DecisionOutcome.PENDING == "pending"
        assert DecisionOutcome.APPROVED == "approved"
        assert DecisionOutcome.REJECTED == "rejected"
        assert DecisionOutcome.EXECUTED == "executed"
        assert DecisionOutcome.CANCELLED == "cancelled"
        assert DecisionOutcome.EXPIRED == "expired"

    def test_string_serialization(self) -> None:
        assert str(DecisionOutcome.APPROVED) == "approved"

    def test_json_serializable(self) -> None:
        data = {"outcome": DecisionOutcome.EXECUTED}
        result = json.dumps(data)
        assert '"executed"' in result


# ---------------------------------------------------------------------------
# AlertSeverity
# ---------------------------------------------------------------------------


class TestAlertSeverity:
    """Tests for AlertSeverity enumeration."""

    def test_all_values_exist(self) -> None:
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.EMERGENCY == "emergency"

    def test_string_serialization(self) -> None:
        assert str(AlertSeverity.CRITICAL) == "critical"


# ---------------------------------------------------------------------------
# RiskLevel
# ---------------------------------------------------------------------------


class TestRiskLevel:
    """Tests for RiskLevel enumeration."""

    def test_all_values_exist(self) -> None:
        assert RiskLevel.LOW == "low"
        assert RiskLevel.MEDIUM == "medium"
        assert RiskLevel.HIGH == "high"
        assert RiskLevel.CRITICAL == "critical"

    def test_string_serialization(self) -> None:
        assert str(RiskLevel.HIGH) == "high"

    def test_json_serializable(self) -> None:
        data = {"risk": RiskLevel.MEDIUM}
        result = json.dumps(data)
        assert '"medium"' in result


# ---------------------------------------------------------------------------
# Cross-cutting: All enums are StrEnum
# ---------------------------------------------------------------------------


class TestAllEnumsAreStrEnum:
    """Verify all enums inherit from StrEnum for JSON compatibility."""

    ENUM_CLASSES = [
        PoolStatus,
        PositionStatus,
        PositionSide,
        AgentRole,
        DecisionOutcome,
        AlertSeverity,
        RiskLevel,
    ]

    def test_all_are_str_enums(self) -> None:
        for cls in self.ENUM_CLASSES:
            assert issubclass(cls, str), f"{cls.__name__} is not a StrEnum"

    def test_all_values_are_strings(self) -> None:
        for cls in self.ENUM_CLASSES:
            for member in cls:
                assert isinstance(member.value, str), (
                    f"{cls.__name__}.{member.name} value is not a string"
                )

    def test_all_members_are_json_serializable(self) -> None:
        for cls in self.ENUM_CLASSES:
            for member in cls:
                result = json.dumps({"test": member})
                assert isinstance(result, str)
