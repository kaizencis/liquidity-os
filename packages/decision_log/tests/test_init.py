"""Tests for decision_log.__init__ module."""

from __future__ import annotations

import pytest

from decision_log import (
    DecisionLogError,
    DecisionNotFoundError,
    DecisionQuery,
    DuplicateDecisionError,
    PostgresDecisionLog,
    QueryError,
)


class TestPackageExports:
    """Tests for package-level exports."""

    def test_settings_exported(self) -> None:
        """Verify settings is exported."""
        from decision_log import DecisionLogSettings
        assert DecisionLogSettings is not None

    def test_errors_exported(self) -> None:
        """Verify all errors are exported."""
        assert DecisionLogError is not None
        assert DecisionNotFoundError is not None
        assert DuplicateDecisionError is not None
        assert QueryError is not None

    def test_logger_exported(self) -> None:
        """Verify logger is exported."""
        assert PostgresDecisionLog is not None

    def test_query_exported(self) -> None:
        """Verify query is exported."""
        assert DecisionQuery is not None

    def test_all_exports_available(self) -> None:
        """Verify __all__ contains expected exports."""
        from decision_log import __all__
        expected = [
            "DecisionLogSettings",
            "DecisionLogError",
            "DecisionNotFoundError",
            "DuplicateDecisionError",
            "QueryError",
            "PostgresDecisionLog",
            "DecisionQuery",
        ]
        for name in expected:
            assert name in __all__, f"{name} not in __all__"
