"""Unit tests for shared.exceptions module."""

from __future__ import annotations

import pytest

from shared.exceptions import (
    DomainError,
    InvalidConfigurationError,
    PoolNotFoundError,
    PositionNotFoundError,
)


# ---------------------------------------------------------------------------
# DomainError (base)
# ---------------------------------------------------------------------------


class TestDomainError:
    """Tests for DomainError base exception."""

    def test_message(self) -> None:
        err = DomainError("test error")
        assert str(err) == "test error"
        assert err.message == "test error"

    def test_default_message(self) -> None:
        err = DomainError()
        assert str(err) == "Domain error occurred"
        assert err.message == "Domain error occurred"

    def test_is_exception(self) -> None:
        err = DomainError("test")
        assert isinstance(err, Exception)

    def test_catchable_as_domain_error(self) -> None:
        with pytest.raises(DomainError):
            raise DomainError("caught")

    def test_catchable_as_exception(self) -> None:
        with pytest.raises(Exception):
            raise DomainError("caught")


# ---------------------------------------------------------------------------
# PoolNotFoundError
# ---------------------------------------------------------------------------


class TestPoolNotFoundError:
    """Tests for PoolNotFoundError exception."""

    def test_message_contains_address(self) -> None:
        addr = "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"
        err = PoolNotFoundError(address=addr)
        assert addr in str(err)

    def test_stores_address(self) -> None:
        addr = "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"
        err = PoolNotFoundError(address=addr)
        assert err.address == addr

    def test_is_domain_error(self) -> None:
        err = PoolNotFoundError(address="test")
        assert isinstance(err, DomainError)

    def test_catchable_as_domain_error(self) -> None:
        with pytest.raises(DomainError):
            raise PoolNotFoundError(address="test")

    def test_with_non_string_address(self) -> None:
        addr = 12345
        err = PoolNotFoundError(address=addr)
        assert err.address == 12345
        assert "12345" in str(err)


# ---------------------------------------------------------------------------
# PositionNotFoundError
# ---------------------------------------------------------------------------


class TestPositionNotFoundError:
    """Tests for PositionNotFoundError exception."""

    def test_message_contains_address(self) -> None:
        addr = "AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"
        err = PositionNotFoundError(address=addr)
        assert addr in str(err)

    def test_stores_address(self) -> None:
        addr = "AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"
        err = PositionNotFoundError(address=addr)
        assert err.address == addr

    def test_is_domain_error(self) -> None:
        err = PositionNotFoundError(address="test")
        assert isinstance(err, DomainError)


# ---------------------------------------------------------------------------
# InvalidConfigurationError
# ---------------------------------------------------------------------------


class TestInvalidConfigurationError:
    """Tests for InvalidConfigurationError exception."""

    def test_message_contains_field_and_reason(self) -> None:
        err = InvalidConfigurationError(
            field="threshold",
            value=-5,
            reason="must be non-negative",
        )
        msg = str(err)
        assert "threshold" in msg
        assert "-5" in msg
        assert "must be non-negative" in msg

    def test_stores_attributes(self) -> None:
        err = InvalidConfigurationError(
            field="threshold",
            value=-5,
            reason="must be non-negative",
        )
        assert err.field == "threshold"
        assert err.value == -5
        assert err.reason == "must be non-negative"

    def test_is_domain_error(self) -> None:
        err = InvalidConfigurationError(
            field="test",
            value=0,
            reason="test",
        )
        assert isinstance(err, DomainError)

    def test_with_string_value(self) -> None:
        err = InvalidConfigurationError(
            field="mode",
            value="invalid",
            reason="must be 'active' or 'paused'",
        )
        assert err.value == "invalid"
        assert "'invalid'" in str(err)


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Verify exception hierarchy is correct."""

    def test_all_inherit_from_domain_error(self) -> None:
        exceptions = [
            PoolNotFoundError(address="test"),
            PositionNotFoundError(address="test"),
            InvalidConfigurationError(field="test", value=0, reason="test"),
        ]
        for exc in exceptions:
            assert isinstance(exc, DomainError)
            assert isinstance(exc, Exception)

    def test_all_catchable_by_domain_error(self) -> None:
        exceptions = [
            PoolNotFoundError(address="test"),
            PositionNotFoundError(address="test"),
            InvalidConfigurationError(field="test", value=0, reason="test"),
        ]
        for exc in exceptions:
            with pytest.raises(DomainError):
                raise exc
