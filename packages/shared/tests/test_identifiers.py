"""Unit tests for shared.identifiers module."""

from __future__ import annotations

import uuid

import pytest

from shared.identifiers import (
    DecisionId,
    PoolAddress,
    PositionAddress,
    TxSignature,
)


# ---------------------------------------------------------------------------
# PoolAddress
# ---------------------------------------------------------------------------


class TestPoolAddress:
    """Tests for PoolAddress identifier."""

    VALID_ADDRESS = "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"

    def test_create_valid_address(self) -> None:
        addr = PoolAddress(value=self.VALID_ADDRESS)
        assert addr.value == self.VALID_ADDRESS
        assert str(addr) == self.VALID_ADDRESS

    def test_immutable(self) -> None:
        addr = PoolAddress(value=self.VALID_ADDRESS)
        with pytest.raises(Exception):
            addr.value = "new_value"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = PoolAddress(value=self.VALID_ADDRESS)
        b = PoolAddress(value=self.VALID_ADDRESS)
        assert a == b

    def test_inequality(self) -> None:
        a = PoolAddress(value=self.VALID_ADDRESS)
        b = PoolAddress(value="AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n")
        assert a != b

    def test_invalid_address_too_short(self) -> None:
        with pytest.raises(Exception):
            PoolAddress(value="short")

    def test_invalid_address_invalid_chars(self) -> None:
        with pytest.raises(Exception):
            PoolAddress(value="0OIl" + "a" * 30)  # contains 0, O, I, l

    def test_hashable(self) -> None:
        addr = PoolAddress(value=self.VALID_ADDRESS)
        assert hash(addr) == hash(self.VALID_ADDRESS)


# ---------------------------------------------------------------------------
# PositionAddress
# ---------------------------------------------------------------------------


class TestPositionAddress:
    """Tests for PositionAddress identifier."""

    VALID_ADDRESS = "AJ6z3Zm9uGaNbJf8xLq3kR5pWtY7vH2n"

    def test_create_valid_address(self) -> None:
        addr = PositionAddress(value=self.VALID_ADDRESS)
        assert addr.value == self.VALID_ADDRESS
        assert str(addr) == self.VALID_ADDRESS

    def test_immutable(self) -> None:
        addr = PositionAddress(value=self.VALID_ADDRESS)
        with pytest.raises(Exception):
            addr.value = "new_value"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = PositionAddress(value=self.VALID_ADDRESS)
        b = PositionAddress(value=self.VALID_ADDRESS)
        assert a == b

    def test_different_from_pool_address(self) -> None:
        pool = PoolAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY")
        pos = PositionAddress(value=self.VALID_ADDRESS)
        # Type safety: these should not be equal even if values were same
        assert type(pool) is not type(pos)


# ---------------------------------------------------------------------------
# TxSignature
# ---------------------------------------------------------------------------


class TestTxSignature:
    """Tests for TxSignature identifier."""

    VALID_SIG = "5VERv8NMhJQVxY9XkZm3pL7qR9tW1yF4hA6bC8dEgHj"

    def test_create_valid_signature(self) -> None:
        sig = TxSignature(value=self.VALID_SIG)
        assert sig.value == self.VALID_SIG
        assert str(sig) == self.VALID_SIG

    def test_immutable(self) -> None:
        sig = TxSignature(value=self.VALID_SIG)
        with pytest.raises(Exception):
            sig.value = "new_value"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = TxSignature(value=self.VALID_SIG)
        b = TxSignature(value=self.VALID_SIG)
        assert a == b


# ---------------------------------------------------------------------------
# DecisionId
# ---------------------------------------------------------------------------


class TestDecisionId:
    """Tests for DecisionId identifier."""

    def test_create_with_uuid(self) -> None:
        uid = uuid.uuid4()
        did = DecisionId(value=uid)
        assert did.value == uid
        assert str(did) == str(uid)

    def test_generate_creates_unique(self) -> None:
        a = DecisionId.generate()
        b = DecisionId.generate()
        assert a != b
        assert a.value != b.value

    def test_immutable(self) -> None:
        did = DecisionId.generate()
        with pytest.raises(Exception):
            did.value = uuid.uuid4()  # type: ignore[misc]

    def test_equality(self) -> None:
        uid = uuid.uuid4()
        a = DecisionId(value=uid)
        b = DecisionId(value=uid)
        assert a == b

    def test_hashable(self) -> None:
        uid = uuid.uuid4()
        did = DecisionId(value=uid)
        assert hash(did) == hash(uid)
