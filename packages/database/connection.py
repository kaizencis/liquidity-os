"""Database connection and session management for Liquidity OS.

[WHY] Provides dependency-injection-ready database connectivity.
      Uses settings-driven configuration with no global state.
      Shares AsyncSession across repositories via session factory.
      Preserves transaction boundaries for M5+ (Collector, Feature Store).

[OWNERSHIP] Infrastructure layer — database connectivity.
[DEPENDENTS] Allowed: repositories, apps (via DI).
             Forbidden: shared, agents (must go through ports).
[EXAMPLE]
    from database.connection import DatabaseSettings, DatabaseSessionManager

    settings = DatabaseSettings(url="postgresql+asyncpg://localhost:5432/liquidity_os")
    manager = DatabaseSessionManager(settings)
    manager.connect()

    async with manager.session() as session:
        # Use session for database operations
        pass

    manager.disconnect()
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(frozen=True)
class DatabaseSettings:
    """[WHY] Configuration for database connectivity and pooling.
    [OWNERSHIP] Infrastructure layer — settings.
    [DEPENDENTS] Allowed: connection module.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        settings = DatabaseSettings()
        assert settings.url == "postgresql+asyncpg://localhost:5432/liquidity_os"
    """

    url: str = field(
        default="postgresql+asyncpg://localhost:5432/liquidity_os",
        metadata={"description": "PostgreSQL async connection URL"},
    )
    pool_size: int = field(
        default=5,
        metadata={"description": "Number of connections to maintain in pool"},
    )
    max_overflow: int = field(
        default=10,
        metadata={"description": "Maximum overflow connections beyond pool_size"},
    )
    pool_timeout: int = field(
        default=30,
        metadata={"description": "Seconds to wait for connection from pool"},
    )
    echo: bool = field(
        default=False,
        metadata={"description": "Enable SQL statement logging"},
    )


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    """[WHY] Factory function for creating AsyncEngine.
    [OWNERSHIP] Infrastructure layer — engine factory.
    [DEPENDENTS] Allowed: DatabaseSessionManager, tests.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        settings = DatabaseSettings()
        engine = create_engine(settings)
        assert isinstance(engine, AsyncEngine)
    """
    return create_async_engine(
        settings.url,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        echo=settings.echo,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """[WHY] Factory function for creating session factories.
    [OWNERSHIP] Infrastructure layer — session factory.
    [DEPENDENTS] Allowed: DatabaseSessionManager.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        engine = create_engine(settings)
        factory = create_session_factory(engine)
        session = factory()
        assert isinstance(session, AsyncSession)
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


class DatabaseSessionManager:
    """[WHY] Manages database engine and session lifecycle.
    [OWNERSHIP] Infrastructure layer — session manager.
    [DEPENDENTS] Allowed: apps, repositories (via DI).
                 Forbidden: shared, agents (must go through ports).
    [EXAMPLE]
        manager = DatabaseSessionManager(settings)
        manager.connect()

        async with manager.session() as session:
            # Use session for database operations
            pass

        manager.disconnect()
    """

    def __init__(self, settings: DatabaseSettings) -> None:
        """Initialize manager with settings (no engine creation yet)."""
        self.settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def connect(self) -> None:
        """Create engine and session factory (lazy initialization)."""
        self._engine = create_engine(self.settings)
        self._session_factory = create_session_factory(self._engine)

    def disconnect(self) -> None:
        """Close engine and clear session factory."""
        self._engine = None
        self._session_factory = None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession] | None:
        """Return session factory (None if not connected)."""
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """[WHY] Provide async session context with automatic transaction handling.
        [OWNERSHIP] Infrastructure layer — session lifecycle.
        [DEPENDENTS] Allowed: repositories, apps (via DI).
                     Forbidden: shared, agents (must go through ports).
        [EXAMPLE]
            async with manager.session() as session:
                result = await session.execute(select(PoolModel))
                pools = result.scalars().all()
        """
        if self._session_factory is None:
            raise RuntimeError("DatabaseSessionManager not connected. Call connect() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
