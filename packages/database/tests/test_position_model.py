"""Tests for database.models.position_model module."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database.models.base import Base, TimestampMixin, UUIDMixin
from database.models.position_model import PositionModel


class TestPositionModel:
    """Tests for PositionModel ORM model."""

    def test_table_name(self) -> None:
        """Verify table name is correct."""
        assert PositionModel.__tablename__ == "position"

    def test_inherits_from_base(self) -> None:
        """Verify PositionModel inherits from Base."""
        assert issubclass(PositionModel, Base)

    def test_has_uuid_mixin(self) -> None:
        """Verify PositionModel has UUIDMixin (id column)."""
        assert hasattr(PositionModel, "id")
        id_col = PositionModel.__table__.columns["id"]
        assert isinstance(id_col.type, UUID)

    def test_has_timestamp_mixin(self) -> None:
        """Verify PositionModel has TimestampMixin columns."""
        assert "created_at" in PositionModel.__table__.columns
        assert "updated_at" in PositionModel.__table__.columns

    def test_address_column(self) -> None:
        """Verify address column exists and is correct type."""
        assert "address" in PositionModel.__table__.columns
        address_col = PositionModel.__table__.columns["address"]
        assert isinstance(address_col.type, String)
        assert address_col.type.length == 44
        assert not address_col.nullable

    def test_pool_address_column(self) -> None:
        """Verify pool_address column exists and is correct type."""
        assert "pool_address" in PositionModel.__table__.columns
        pool_address_col = PositionModel.__table__.columns["pool_address"]
        assert isinstance(pool_address_col.type, String)
        assert pool_address_col.type.length == 44
        assert not pool_address_col.nullable

    def test_status_column(self) -> None:
        """Verify status column exists and is correct type."""
        assert "status" in PositionModel.__table__.columns
        status_col = PositionModel.__table__.columns["status"]
        assert isinstance(status_col.type, String)
        assert status_col.type.length == 50
        assert not status_col.nullable

    def test_side_column(self) -> None:
        """Verify side column exists and is correct type."""
        assert "side" in PositionModel.__table__.columns
        side_col = PositionModel.__table__.columns["side"]
        assert isinstance(side_col.type, String)
        assert side_col.type.length == 50
        assert not side_col.nullable

    def test_price_range_column(self) -> None:
        """Verify price_range column exists and is JSONB."""
        assert "price_range" in PositionModel.__table__.columns
        price_range_col = PositionModel.__table__.columns["price_range"]
        assert isinstance(price_range_col.type, JSONB)
        assert price_range_col.nullable

    def test_liquidity_column(self) -> None:
        """Verify liquidity column exists and is JSONB."""
        assert "liquidity" in PositionModel.__table__.columns
        liquidity_col = PositionModel.__table__.columns["liquidity"]
        assert isinstance(liquidity_col.type, JSONB)
        assert liquidity_col.nullable

    def test_distribution_column(self) -> None:
        """Verify distribution column exists and is JSONB."""
        assert "distribution" in PositionModel.__table__.columns
        distribution_col = PositionModel.__table__.columns["distribution"]
        assert isinstance(distribution_col.type, JSONB)
        assert distribution_col.nullable

    def test_fee_earned_column(self) -> None:
        """Verify fee_earned column exists and is Float."""
        assert "fee_earned" in PositionModel.__table__.columns
        fee_earned_col = PositionModel.__table__.columns["fee_earned"]
        assert isinstance(fee_earned_col.type, Float)
        assert not fee_earned_col.nullable

    def test_primary_key(self) -> None:
        """Verify primary key is 'id'."""
        pk = PositionModel.__table__.primary_key
        assert len(pk.columns) == 1
        assert pk.columns[0].name == "id"

    def test_not_null_columns(self) -> None:
        """Verify required columns are NOT NULL."""
        table = PositionModel.__table__
        not_null_columns = [
            "id", "address", "pool_address", "status", "side", "fee_earned"
        ]
        for col_name in not_null_columns:
            col = table.columns[col_name]
            assert not col.nullable, f"{col_name} should be NOT NULL"

    def test_nullable_columns(self) -> None:
        """Verify optional columns are nullable."""
        table = PositionModel.__table__
        nullable_columns = ["price_range", "liquidity", "distribution"]
        for col_name in nullable_columns:
            col = table.columns[col_name]
            assert col.nullable, f"{col_name} should be nullable"

    def test_default_status(self) -> None:
        """Verify status defaults to 'active'."""
        col = PositionModel.__table__.columns["status"]
        assert col.default.arg == "active"

    def test_default_side(self) -> None:
        """Verify side defaults to 'both'."""
        col = PositionModel.__table__.columns["side"]
        assert col.default.arg == "both"

    def test_default_fee_earned(self) -> None:
        """Verify fee_earned defaults to 0.0."""
        col = PositionModel.__table__.columns["fee_earned"]
        assert col.default.arg == 0.0
