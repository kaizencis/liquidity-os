"""Tests for database.connection module.

Test categories:
- DatabaseSettings (5 tests)
- Engine Factory (4 tests - mock-based)
- Session Factory (4 tests - mock-based)
- DatabaseSessionManager (5 tests)
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import FrozenInstanceError


class TestDatabaseSettings:
    """Test DatabaseSettings configuration."""

    def test_default_url(self) -> None:
        """DatabaseSettings should have default PostgreSQL URL."""
        from database.connection import DatabaseSettings
        settings = DatabaseSettings()
        assert settings.url == "postgresql+asyncpg://localhost:5432/liquidity_os"

    def test_custom_url(self) -> None:
        """DatabaseSettings should accept custom URL."""
        from database.connection import DatabaseSettings
        settings = DatabaseSettings(url="postgresql+asyncpg://custom:5432/testdb")
        assert settings.url == "postgresql+asyncpg://custom:5432/testdb"

    def test_default_pool_size(self) -> None:
        """DatabaseSettings should have default pool size."""
        from database.connection import DatabaseSettings
        settings = DatabaseSettings()
        assert settings.pool_size == 5

    def test_default_max_overflow(self) -> None:
        """DatabaseSettings should have default max overflow."""
        from database.connection import DatabaseSettings
        settings = DatabaseSettings()
        assert settings.max_overflow == 10

    def test_is_frozen(self) -> None:
        """DatabaseSettings should be immutable."""
        from database.connection import DatabaseSettings
        settings = DatabaseSettings()
        with pytest.raises(FrozenInstanceError):
            settings.url = "new_url"


class TestEngineFactory:
    """Test engine creation functions (mock-based)."""

    @patch("database.connection.create_async_engine")
    def test_create_engine_returns_async_engine(self, mock_create: MagicMock) -> None:
        """create_engine should return AsyncEngine."""
        from database.connection import DatabaseSettings, create_engine
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine

        settings = DatabaseSettings()
        engine = create_engine(settings)

        assert engine == mock_engine

    @patch("database.connection.create_async_engine")
    def test_create_engine_uses_settings_url(self, mock_create: MagicMock) -> None:
        """create_engine should use URL from settings."""
        from database.connection import DatabaseSettings, create_engine
        settings = DatabaseSettings(url="postgresql+asyncpg://test:test@localhost/test")
        create_engine(settings)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs[0][0] == "postgresql+asyncpg://test:test@localhost/test"

    @patch("database.connection.create_async_engine")
    def test_create_engine_uses_pool_settings(self, mock_create: MagicMock) -> None:
        """create_engine should apply pool settings from settings."""
        from database.connection import DatabaseSettings, create_engine
        settings = DatabaseSettings(pool_size=10, max_overflow=20, pool_timeout=60)
        create_engine(settings)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["pool_size"] == 10
        assert call_kwargs["max_overflow"] == 20
        assert call_kwargs["pool_timeout"] == 60

    @patch("database.connection.create_async_engine")
    def test_create_engine_echo_disabled(self, mock_create: MagicMock) -> None:
        """create_engine should disable echo by default."""
        from database.connection import DatabaseSettings, create_engine
        settings = DatabaseSettings()
        create_engine(settings)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["echo"] is False


class TestSessionFactory:
    """Test session factory functions (mock-based)."""

    def test_create_session_factory_returns_callable(self) -> None:
        """create_session_factory should return callable."""
        from database.connection import create_session_factory
        mock_engine = MagicMock()
        factory = create_session_factory(mock_engine)
        assert callable(factory)

    def test_create_session_factory_creates_async_session(self) -> None:
        """create_session_factory should create AsyncSession."""
        from database.connection import create_session_factory
        from sqlalchemy.ext.asyncio import AsyncSession
        mock_engine = MagicMock()
        factory = create_session_factory(mock_engine)
        session = factory()
        assert isinstance(session, AsyncSession)

    def test_session_factory_uses_engine(self) -> None:
        """Session factory should bind to provided engine."""
        from database.connection import create_session_factory
        mock_engine = MagicMock()
        factory = create_session_factory(mock_engine)
        session = factory()
        assert session.bind is mock_engine

    def test_session_factory_autocommit_false(self) -> None:
        """Session factory should have autocommit=False."""
        from database.connection import create_session_factory
        mock_engine = MagicMock()
        factory = create_session_factory(mock_engine)
        session = factory()
        assert session is not None


class TestDatabaseSessionManager:
    """Test DatabaseSessionManager context manager."""

    def test_manager_initialization(self) -> None:
        """DatabaseSessionManager should initialize with settings."""
        from database.connection import DatabaseSettings, DatabaseSessionManager
        settings = DatabaseSettings()
        manager = DatabaseSessionManager(settings)
        assert manager.settings == settings

    def test_manager_has_session_factory_none_before_connect(self) -> None:
        """DatabaseSessionManager should have session_factory=None before connect."""
        from database.connection import DatabaseSettings, DatabaseSessionManager
        settings = DatabaseSettings()
        manager = DatabaseSessionManager(settings)
        assert manager.session_factory is None

    @patch("database.connection.create_async_engine")
    def test_manager_connect_creates_factory(self, mock_create: MagicMock) -> None:
        """DatabaseSessionManager.connect should create session factory."""
        from database.connection import DatabaseSettings, DatabaseSessionManager
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine

        settings = DatabaseSettings()
        manager = DatabaseSessionManager(settings)
        manager.connect()

        assert manager.session_factory is not None

    def test_manager_disconnect_clears_factory(self) -> None:
        """DatabaseSessionManager.disconnect should clear session factory."""
        from database.connection import DatabaseSettings, DatabaseSessionManager
        settings = DatabaseSettings()
        manager = DatabaseSessionManager(settings)
        # Simulate connected state
        manager._session_factory = MagicMock()
        manager.disconnect()
        assert manager.session_factory is None

    def test_manager_session_raises_if_not_connected(self) -> None:
        """DatabaseSessionManager.session should raise if not connected."""
        import asyncio
        from database.connection import DatabaseSettings, DatabaseSessionManager

        async def _test():
            settings = DatabaseSettings()
            manager = DatabaseSessionManager(settings)
            with pytest.raises(RuntimeError, match="not connected"):
                async with manager.session():
                    pass

        asyncio.get_event_loop().run_until_complete(_test())
