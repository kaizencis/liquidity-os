"""Liquidity OS Database Package.

[WHY] Provides persistence layer for domain entities.
      Exports public API for consumers (repositories, connection).
[OWNERSHIP] Infrastructure layer — database package.
[DEPENDENTS] Allowed: apps, agents (via repositories).
             Forbidden: shared (must go through ports).
"""

from database.connection import (
    DatabaseSettings,
    DatabaseSessionManager,
    create_engine,
    create_session_factory,
)
from database.models.base import Base, TimestampMixin, UUIDMixin
from database.models.pool_model import PoolModel
from database.models.position_model import PositionModel
from database.repositories.pool_repo_impl import PostgresPoolRepository
from database.repositories.position_repo_impl import PostgresPositionRepository

__all__ = [
    # Connection
    "DatabaseSettings",
    "DatabaseSessionManager",
    "create_engine",
    "create_session_factory",
    # Models
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "PoolModel",
    "PositionModel",
    # Repositories
    "PostgresPoolRepository",
    "PostgresPositionRepository",
]
