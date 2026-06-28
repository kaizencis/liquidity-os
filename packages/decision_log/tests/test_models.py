"""Tests for decision_log.models module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from decision_log.models import DecisionLogModel


class TestDecisionLogModel:
    """Tests for DecisionLogModel SQLAlchemy ORM model."""

    def test_table_name(self) -> None:
        """Verify table name is correct."""
        assert DecisionLogModel.__tablename__ == "decision_log"

    def test_column_names(self) -> None:
        """Verify all expected columns exist."""
        columns = DecisionLogModel.__table__.columns.keys()
        expected = [
            "id",
            "agent",
            "event_type",
            "trigger_rule",
            "pool_address",
            "outcome",
            "timestamp",
            "features",
            "metadata",
            "created_at",
        ]
        assert set(expected).issubset(set(columns))

    def test_primary_key(self) -> None:
        """Verify primary key is 'id'."""
        pk = DecisionLogModel.__table__.primary_key
        assert len(pk.columns) == 1
        assert pk.columns[0].name == "id"

    def test_not_null_columns(self) -> None:
        """Verify required columns are NOT NULL."""
        table = DecisionLogModel.__table__
        not_null_columns = ["id", "agent", "event_type", "outcome", "timestamp"]
        for col_name in not_null_columns:
            col = table.columns[col_name]
            assert not col.nullable, f"{col_name} should be NOT NULL"

    def test_nullable_columns(self) -> None:
        """Verify optional columns are nullable."""
        table = DecisionLogModel.__table__
        nullable_columns = ["trigger_rule", "pool_address", "features", "metadata", "created_at"]
        for col_name in nullable_columns:
            col = table.columns[col_name]
            assert col.nullable, f"{col_name} should be nullable"

    def test_default_values(self) -> None:
        """Verify default values are set."""
        table = DecisionLogModel.__table__
        # trigger_rule defaults to ''
        trigger_col = table.columns["trigger_rule"]
        assert trigger_col.default.arg == ""
        # features defaults to '{}'
        features_col = table.columns["features"]
        assert features_col.default.arg == "{}"
        # metadata defaults to '{}'
        metadata_col = table.columns["metadata"]
        assert metadata_col.default.arg == "{}"
        # outcome defaults to 'pending'
        outcome_col = table.columns["outcome"]
        assert outcome_col.default.arg == "pending"
