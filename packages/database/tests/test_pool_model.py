"""Tests for database.models.pool_model module."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database.models.base import Base, TimestampMixin, UUIDMixin
from database.models.pool_model import PoolModel


class TestPoolModel:
    """Tests for PoolModel ORM model."""

    def test_table_name(self) -> None:
        """Verify table name is correct."""
        assert PoolModel.__tablename__ == "pools"

    def test_inherits_from_base(self) -> None:
        """Verify PoolModel inherits from Base."""
        assert issubclass(PoolModel, Base)

    def test_has_uuid_mixin(self) -> None:
        """Verify PoolModel has UUIDMixin (id column)."""
        assert hasattr(PoolModel, "id")
        id_col = PoolModel.__table__.columns["id"]
        assert isinstance(id_col.type, UUID)

    def test_has_timestamp_mixin(self) -> None:
        """Verify PoolModel has TimestampMixin columns."""
        assert "created_at" in PoolModel.__table__.columns
        assert "updated_at" in PoolModel.__table__.columns

    def test_address_column(self) -> None:
        """Verify address column exists and is correct type."""
        assert "address" in PoolModel.__table__.columns
        address_col = PoolModel.__table__.columns["address"]
        assert isinstance(address_col.type, String)
        assert address_col.type.length == 44
        assert not address_col.nullable

    def test_token_a_column(self) -> None:
        """Verify token_a column exists and is JSONB."""
        assert "token_a" in PoolModel.__table__.columns
        token_a_col = PoolModel.__table__.columns["token_a"]
        assert isinstance(token_a_col.type, JSONB)
        assert not token_a_col.nullable

    def test_token_b_column(self) -> None:
        """Verify token_b column exists and is JSONB."""
        assert "token_b" in PoolModel.__table__.columns
        token_b_col = PoolModel.__table__.columns["token_b"]
        assert isinstance(token_b_col.type, JSONB)
        assert not token_b_col.nullable

    def test_status_column(self) -> None:
        """Verify status column exists and is correct type."""
        assert "status" in PoolModel.__table__.columns
        status_col = PoolModel.__table__.columns["status"]
        assert isinstance(status_col.type, String)
        assert status_col.type.length == 50
        assert not status_col.nullable

    def test_sqrt_price_column(self) -> None:
        """Verify sqrt_price column exists and is JSONB."""
        assert "sqrt_price" in PoolModel.__table__.columns
        sqrt_price_col = PoolModel.__table__.columns["sqrt_price"]
        assert isinstance(sqrt_price_col.type, JSONB)
        assert sqrt_price_col.nullable

    def test_price_column(self) -> None:
        """Verify price column exists and is JSONB."""
        assert "price" in PoolModel.__table__.columns
        price_col = PoolModel.__table__.columns["price"]
        assert isinstance(price_col.type, JSONB)
        assert price_col.nullable

    def test_fee_rate_column(self) -> None:
        """Verify fee_rate column exists and is Float."""
        assert "fee_rate" in PoolModel.__table__.columns
        fee_rate_col = PoolModel.__table__.columns["fee_rate"]
        assert isinstance(fee_rate_col.type, Float)
        assert not fee_rate_col.nullable

    def test_bin_step_column(self) -> None:
        """Verify bin_step column exists and is Integer."""
        assert "bin_step" in PoolModel.__table__.columns
        bin_step_col = PoolModel.__table__.columns["bin_step"]
        assert isinstance(bin_step_col.type, Integer)
        assert not bin_step_col.nullable

    def test_primary_key(self) -> None:
        """Verify primary key is 'id'."""
        pk = PoolModel.__table__.primary_key
        assert len(pk.columns) == 1
        assert pk.columns[0].name == "id"

    def test_not_null_columns(self) -> None:
        """Verify required columns are NOT NULL."""
        table = PoolModel.__table__
        not_null_columns = ["id", "address", "token_a", "token_b", "status", "fee_rate", "bin_step"]
        for col_name in not_null_columns:
            col = table.columns[col_name]
            assert not col.nullable, f"{col_name} should be NOT NULL"

    def test_nullable_columns(self) -> None:
        """Verify optional columns are nullable."""
        table = PoolModel.__table__
        nullable_columns = ["sqrt_price", "price"]
        for col_name in nullable_columns:
            col = table.columns[col_name]
            assert col.nullable, f"{col_name} should be nullable"
