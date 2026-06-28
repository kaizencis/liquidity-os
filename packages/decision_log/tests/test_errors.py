"""Tests for decision_log.errors module."""

from __future__ import annotations

import pytest

from shared.exceptions import DomainError
from shared.identifiers import DecisionId
from decision_log.errors import (
    DecisionLogError,
    DecisionNotFoundError,
    DuplicateDecisionError,
    QueryError,
)


class TestDecisionLogError:
    """Tests for DecisionLogError base exception."""

    def test_is_domain_error(self) -> None:
        """Verify DecisionLogError inherits from DomainError."""
        err = DecisionLogError("test error")
        assert isinstance(err, DomainError)

    def test_message(self) -> None:
        """Verify error message is stored."""
        err = DecisionLogError("test error")
        assert str(err) == "test error"
        assert err.message == "test error"

    def test_default_message(self) -> None:
        """Verify default message."""
        err = DecisionLogError()
        assert "Decision Log error" in str(err)


class TestDecisionNotFoundError:
    """Tests for DecisionNotFoundError exception."""

    def test_is_decision_log_error(self) -> None:
        """Verify inheritance."""
        did = DecisionId.generate()
        err = DecisionNotFoundError(decision_id=did)
        assert isinstance(err, DecisionLogError)
        assert isinstance(err, DomainError)

    def test_stores_decision_id(self) -> None:
        """Verify decision_id is stored."""
        did = DecisionId.generate()
        err = DecisionNotFoundError(decision_id=did)
        assert err.decision_id == did

    def test_message_contains_id(self) -> None:
        """Verify message contains decision ID."""
        did = DecisionId.generate()
        err = DecisionNotFoundError(decision_id=did)
        assert str(did) in str(err)


class TestDuplicateDecisionError:
    """Tests for DuplicateDecisionError exception."""

    def test_is_decision_log_error(self) -> None:
        """Verify inheritance."""
        did = DecisionId.generate()
        err = DuplicateDecisionError(decision_id=did)
        assert isinstance(err, DecisionLogError)
        assert isinstance(err, DomainError)

    def test_stores_decision_id(self) -> None:
        """Verify decision_id is stored."""
        did = DecisionId.generate()
        err = DuplicateDecisionError(decision_id=did)
        assert err.decision_id == did

    def test_message_contains_id(self) -> None:
        """Verify message contains decision ID."""
        did = DecisionId.generate()
        err = DuplicateDecisionError(decision_id=did)
        assert str(did) in str(err)


class TestQueryError:
    """Tests for QueryError exception."""

    def test_is_decision_log_error(self) -> None:
        """Verify inheritance."""
        err = QueryError("query failed")
        assert isinstance(err, DecisionLogError)
        assert isinstance(err, DomainError)

    def test_message(self) -> None:
        """Verify error message is stored."""
        err = QueryError("query failed")
        assert str(err) == "query failed"
