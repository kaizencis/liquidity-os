"""Tests for decision_log.settings module."""

from __future__ import annotations

import pytest

from decision_log.settings import DecisionLogSettings


class TestDecisionLogSettings:
    """Tests for DecisionLogSettings configuration."""

    def test_default_values(self) -> None:
        """Verify default configuration values."""
        settings = DecisionLogSettings()
        assert settings.retention_days == 90
        assert settings.default_query_limit == 100
        assert settings.max_query_limit == 1000
        assert settings.batch_size == 100
        assert settings.table_name == "decision_log"

    def test_custom_values(self) -> None:
        """Verify custom configuration values."""
        settings = DecisionLogSettings(
            retention_days=30,
            default_query_limit=50,
            max_query_limit=500,
            batch_size=50,
            table_name="custom_table",
        )
        assert settings.retention_days == 30
        assert settings.default_query_limit == 50
        assert settings.max_query_limit == 500
        assert settings.batch_size == 50
        assert settings.table_name == "custom_table"

    def test_immutable(self) -> None:
        """Verify settings are immutable after creation."""
        settings = DecisionLogSettings()
        with pytest.raises(Exception):
            settings.retention_days = 30  # type: ignore[misc]

    def test_serialization(self) -> None:
        """Verify settings can be serialized to dict."""
        settings = DecisionLogSettings()
        data = settings.model_dump()
        assert isinstance(data, dict)
        assert "retention_days" in data
        assert "table_name" in data
