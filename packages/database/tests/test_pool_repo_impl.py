"""Tests for PostgresPoolRepository implementation.

Test categories:
- Domain ↔ ORM Conversion (10 tests)
- Repository Interface (4 tests)
- Error Translation (2 tests)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.pool_model import PoolModel
from database.repositories.pool_repo_impl import PostgresPoolRepository
from shared.entities.pool import Pool
from shared.enums import PoolStatus
from shared.exceptions import PoolNotFoundError
from shared.identifiers import PoolAddress
from shared.value_objects.price import Price, SqrtPrice
from shared.value_objects.token import Token


# ============================================================================
# FIXTURES
# ============================================================================

# Valid Solana address format for testing (32-44 chars, base58)
TEST_ADDRESS = "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"
NON_EXISTENT_ADDRESS = "11111111111111111111111111111111"


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_pool() -> Pool:
    """Create a sample Pool domain entity."""
    return Pool(
        address=PoolAddress(value=TEST_ADDRESS),
        token_a=Token(
            address="So11111111111111111111111111111111111111112",
            symbol="SOL",
            decimals=9,
        ),
        token_b=Token(
            address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            symbol="USDC",
            decimals=6,
        ),
        status=PoolStatus.ACTIVE,
        sqrt_price=SqrtPrice(
            raw=79228162514264337593543950336,
            tick=0,
            bin_id=0,
        ),
        price=Price(
            value=150.0,
            base_token=Token(
                address="So11111111111111111111111111111111111111112",
                symbol="SOL",
                decimals=9,
            ),
            quote_token=Token(
                address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                symbol="USDC",
                decimals=6,
            ),
        ),
        fee_rate=0.003,
        bin_step=1,
    )


@pytest.fixture
def sample_pool_model() -> PoolModel:
    """Create a sample PoolModel ORM instance."""
    return PoolModel(
        id=uuid4(),
        address=TEST_ADDRESS,
        token_a={
            "address": "So11111111111111111111111111111111111111112",
            "symbol": "SOL",
            "decimals": 9,
        },
        token_b={
            "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "symbol": "USDC",
            "decimals": 6,
        },
        status="active",
        sqrt_price={
            "raw": 79228162514264337593543950336,
            "tick": 0,
            "bin_id": 0,
        },
        price={
            "value": 150.0,
            "base_token": {
                "address": "So11111111111111111111111111111111111111112",
                "symbol": "SOL",
                "decimals": 9,
            },
            "quote_token": {
                "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "symbol": "USDC",
                "decimals": 6,
            },
        },
        fee_rate=0.003,
        bin_step=1,
    )


# ============================================================================
# DOMAIN ↔ ORM CONVERSION TESTS
# ============================================================================


class TestConversion:
    """Test lossless bidirectional conversion between Pool and PoolModel."""

    def test_domain_to_orm_address(self, sample_pool: Pool) -> None:
        """Pool address should map to PoolModel address."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        model = repo._to_model(sample_pool)
        assert model.address == sample_pool.address.value

    def test_domain_to_orm_tokens(self, sample_pool: Pool) -> None:
        """Pool tokens should map to PoolModel JSONB."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        model = repo._to_model(sample_pool)
        assert model.token_a["symbol"] == "SOL"
        assert model.token_b["symbol"] == "USDC"
        assert model.token_a["decimals"] == 9
        assert model.token_b["decimals"] == 6

    def test_domain_to_orm_status(self, sample_pool: Pool) -> None:
        """Pool status should map to PoolModel status string."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        model = repo._to_model(sample_pool)
        assert model.status == "active"

    def test_domain_to_orm_price(self, sample_pool: Pool) -> None:
        """Pool price should map to PoolModel JSONB."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        model = repo._to_model(sample_pool)
        assert model.price["value"] == 150.0
        assert model.price["base_token"]["symbol"] == "SOL"

    def test_orm_to_domain_address(self, sample_pool_model: PoolModel) -> None:
        """PoolModel address should map to Pool address."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        pool = repo._to_domain(sample_pool_model)
        assert pool.address.value == sample_pool_model.address

    def test_orm_to_domain_tokens(self, sample_pool_model: PoolModel) -> None:
        """PoolModel tokens should map to Pool Token objects."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        pool = repo._to_domain(sample_pool_model)
        assert pool.token_a.symbol == "SOL"
        assert pool.token_b.symbol == "USDC"
        assert pool.token_a.decimals == 9
        assert pool.token_b.decimals == 6

    def test_orm_to_domain_status(self, sample_pool_model: PoolModel) -> None:
        """PoolModel status string should map to PoolStatus enum."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        pool = repo._to_domain(sample_pool_model)
        assert pool.status == PoolStatus.ACTIVE

    def test_orm_to_domain_price(self, sample_pool_model: PoolModel) -> None:
        """PoolModel price JSONB should map to Price value object."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        pool = repo._to_domain(sample_pool_model)
        assert pool.price.value == 150.0
        assert pool.price.base_token.symbol == "SOL"

    def test_round_trip_lossless(self, sample_pool: Pool) -> None:
        """Pool → PoolModel → Pool should be lossless."""
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        model = repo._to_model(sample_pool)
        pool_back = repo._to_domain(model)

        assert pool_back.address == sample_pool.address
        assert pool_back.token_a == sample_pool.token_a
        assert pool_back.token_b == sample_pool.token_b
        assert pool_back.status == sample_pool.status
        assert pool_back.fee_rate == sample_pool.fee_rate
        assert pool_back.bin_step == sample_pool.bin_step

    def test_round_trip_with_none_price(self) -> None:
        """Pool with None price should survive round trip."""
        pool = Pool(
            address=PoolAddress(value=TEST_ADDRESS),
            token_a=Token(
                address="So11111111111111111111111111111111111111112",
                symbol="SOL",
                decimals=9,
            ),
            token_b=Token(
                address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                symbol="USDC",
                decimals=6,
            ),
            status=PoolStatus.ACTIVE,
            sqrt_price=None,
            price=None,
        )
        repo = PostgresPoolRepository.__new__(PostgresPoolRepository)
        model = repo._to_model(pool)
        pool_back = repo._to_domain(model)

        assert pool_back.sqrt_price is None
        assert pool_back.price is None


# ============================================================================
# REPOSITORY INTERFACE TESTS
# ============================================================================


class TestRepositoryInterface:
    """Test PostgresPoolRepository implements PoolRepository correctly."""

    def test_implements_pool_repository(self, mock_session: AsyncMock) -> None:
        """PostgresPoolRepository should implement PoolRepository."""
        from shared.ports.pool_repo import PoolRepository
        repo = PostgresPoolRepository(mock_session)
        assert isinstance(repo, PoolRepository)

    @pytest.mark.asyncio
    async def test_get_by_address_calls_session(
        self, mock_session: AsyncMock, sample_pool_model: PoolModel
    ) -> None:
        """get_by_address should execute SELECT query."""
        repo = PostgresPoolRepository(mock_session)
        # Setup mock chain: execute -> scalars -> first
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = sample_pool_model
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        pool = await repo.get_by_address(
            PoolAddress(value=TEST_ADDRESS)
        )

        assert pool is not None
        assert pool.address.value == TEST_ADDRESS
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_calls_session_add(
        self, mock_session: AsyncMock, sample_pool: Pool
    ) -> None:
        """save should add model to session."""
        repo = PostgresPoolRepository(mock_session)
        await repo.save(sample_pool)
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_all_calls_session_execute(
        self, mock_session: AsyncMock
    ) -> None:
        """list_all should execute SELECT query."""
        repo = PostgresPoolRepository(mock_session)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        pools = await repo.list_all()

        assert pools == []
        mock_session.execute.assert_called_once()


# ============================================================================
# ERROR TRANSLATION TESTS
# ============================================================================


class TestErrorTranslation:
    """Test error translation from SQLAlchemy to domain exceptions."""

    @pytest.mark.asyncio
    async def test_get_by_address_raises_pool_not_found_error(
        self, mock_session: AsyncMock
    ) -> None:
        """get_by_address should raise PoolNotFoundError when pool not found."""
        repo = PostgresPoolRepository(mock_session)
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with pytest.raises(PoolNotFoundError):
            await repo.get_by_address(
                PoolAddress(value=NON_EXISTENT_ADDRESS)
            )
