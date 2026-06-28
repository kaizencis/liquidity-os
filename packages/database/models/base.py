"""SQLAlchemy base models and mixins for Liquidity OS.

[WHY] Provides common base classes and mixins for all database models.
      Ensures consistent schema patterns across the system.

[OWNERSHIP] Infrastructure layer — database foundation.

[DEPENDENTS] Allowed: models.*, repositories.*
             Forbidden: shared, apps, agents.

[EXAMPLE]
    from database.models.base import Base, UUIDMixin, TimestampMixin

    class PoolModel(UUIDMixin, TimestampMixin, Base):
        __tablename__ = "pools"
        address = Column(String(44), nullable=False)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """[WHY] Base class for all SQLAlchemy models.

    [OWNERSHIP] Infrastructure layer — database foundation.

    [DEPENDENTS] Allowed: models.*, repositories.*
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        class MyModel(Base):
            __tablename__ = "my_table"
            id = Column(Integer, primary_key=True)
    """
    pass


class UUIDMixin:
    """[WHY] Mixin that adds UUID primary key to models.

    [OWNERSHIP] Infrastructure layer — common mixin.

    [DEPENDENTS] Allowed: models.*
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        class PoolModel(UUIDMixin, Base):
            __tablename__ = "pools"
            address = Column(String(44))
    """

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=None,  # Will be set by application layer
        nullable=False,
        comment="UUID v4 unique identifier",
    )


class TimestampMixin:
    """[WHY] Mixin that adds timestamp columns to models.

    [OWNERSHIP] Infrastructure layer — common mixin.

    [DEPENDENTS] Allowed: models.*
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        class PoolModel(TimestampMixin, Base):
            __tablename__ = "pools"
            address = Column(String(44))
    """

    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
        comment="Record creation time (UTC)",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Record last update time (UTC)",
    )
