"""Tests for database.models.base module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from database.models.base import Base, TimestampMixin, UUIDMixin


class TestBase:
    """Tests for DeclarativeBase."""

    def test_is_declarative_base(self) -> None:
        """Verify Base is a DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)

    def test_metadata_exists(self) -> None:
        """Verify Base has metadata for table registration."""
        assert hasattr(Base, "metadata")


class TestUUIDMixin:
    """Tests for UUIDMixin."""

    def test_adds_id_column(self) -> None:
        """Verify UUIDMixin adds id column."""
        class TestModel(UUIDMixin, Base):
            __tablename__ = "test_uuid"
            name = Column(String(50))

        table = TestModel.__table__
        assert "id" in table.columns

    def test_id_is_primary_key(self) -> None:
        """Verify id column is primary key."""
        class TestModel(UUIDMixin, Base):
            __tablename__ = "test_uuid_pk"
            name = Column(String(50))

        pk = TestModel.__table__.primary_key
        assert len(pk.columns) == 1
        assert pk.columns[0].name == "id"

    def test_id_is_uuid_type(self) -> None:
        """Verify id column is UUID type."""
        class TestModel(UUIDMixin, Base):
            __tablename__ = "test_uuid_type"
            name = Column(String(50))

        id_col = TestModel.__table__.columns["id"]
        assert isinstance(id_col.type, UUID)


class TestTimestampMixin:
    """Tests for TimestampMixin."""

    def test_adds_created_at_column(self) -> None:
        """Verify TimestampMixin adds created_at column."""
        class TestModel(UUIDMixin, TimestampMixin, Base):
            __tablename__ = "test_timestamp"
            name = Column(String(50))

        table = TestModel.__table__
        assert "created_at" in table.columns

    def test_adds_updated_at_column(self) -> None:
        """Verify TimestampMixin adds updated_at column."""
        class TestModel(UUIDMixin, TimestampMixin, Base):
            __tablename__ = "test_timestamp_updated"
            name = Column(String(50))

        table = TestModel.__table__
        assert "updated_at" in table.columns

    def test_created_at_is_datetime(self) -> None:
        """Verify created_at is DateTime type."""
        from sqlalchemy import DateTime
        class TestModel(UUIDMixin, TimestampMixin, Base):
            __tablename__ = "test_timestamp_datetime"
            name = Column(String(50))

        created_at_col = TestModel.__table__.columns["created_at"]
        assert isinstance(created_at_col.type, DateTime)

    def test_created_at_has_default(self) -> None:
        """Verify created_at has default value."""
        class TestModel(UUIDMixin, TimestampMixin, Base):
            __tablename__ = "test_timestamp_default"
            name = Column(String(50))

        created_at_col = TestModel.__table__.columns["created_at"]
        assert created_at_col.default is not None


class TestCombinedMixins:
    """Tests for using UUIDMixin and TimestampMixin together."""

    def test_combined_mixins(self) -> None:
        """Verify both mixins work together."""
        class TestModel(UUIDMixin, TimestampMixin, Base):
            __tablename__ = "test_combined"
            name = Column(String(50))

        table = TestModel.__table__
        assert "id" in table.columns
        assert "created_at" in table.columns
        assert "updated_at" in table.columns
        assert "name" in table.columns

    def test_all_columns_present(self) -> None:
        """Verify all expected columns are present."""
        class TestModel(UUIDMixin, TimestampMixin, Base):
            __tablename__ = "test_all_columns"
            name = Column(String(50))
            description = Column(String(200))

        table = TestModel.__table__
        expected_columns = {"id", "created_at", "updated_at", "name", "description"}
        assert set(table.columns.keys()) == expected_columns
