"""Tests for PostgresPositionRepository implementation.

Test categories:
- Domain ↔ ORM Conversion (10 tests)
- Repository Interface (5 tests)
- Error Translation (2 tests)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.position_model import PositionModel
from database.repositories.position_repo_impl import PostgresPositionRepository
from shared.entities.position import Position
from shared.enums import PositionSide, PositionStatus
from shared.exceptions import PositionNotFoundError
from shared.identifiers import PoolAddress, PositionAddress
from shared.value_objects.liquidity import BinLiquidity, Liquidity, LiquidityDistribution
from shared.value_objects.price import Price, PriceRange
from shared.value_objects.token import Token, TokenAmount


# ============================================================================
# CONSTANTS
# ============================================================================

TEST_POSITION_ADDRESS = "AJ6z3Zm9uGaNbJf8xLq3RkPmWvYtHdBnCeFg"
TEST_POOL_ADDRESS = "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"
SOL_ADDRESS = "So11111111111111111111111111111111111111112"
USDC_ADDRESS = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Create reusable Token objects
SOL = Token(address=SOL_ADDRESS, symbol="SOL", decimals=9)
USDC = Token(address=USDC_ADDRESS, symbol="USDC", decimals=6)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    return session


@pytest.fixture
def sample_position() -> Position:
    """Create a sample Position domain entity."""
    return Position(
        address=PositionAddress(value=TEST_POSITION_ADDRESS),
        pool_address=PoolAddress(value=TEST_POOL_ADDRESS),
        status=PositionStatus.ACTIVE,
        side=PositionSide.BOTH,
        price_range=PriceRange(
            low=Price(value=100.0, base_token=SOL, quote_token=USDC),
            high=Price(value=200.0, base_token=SOL, quote_token=USDC),
        ),
        liquidity=Liquidity(
            amount=TokenAmount(token=SOL, raw=1000000000)
        ),
        liquidity_distribution=LiquidityDistribution(
            bins=[
                BinLiquidity(
                    bin_id=10,
                    liquidity=Liquidity(amount=TokenAmount(token=SOL, raw=500000000)),
                ),
                BinLiquidity(
                    bin_id=15,
                    liquidity=Liquidity(amount=TokenAmount(token=SOL, raw=500000000)),
                ),
            ]
        ),
        fee_earned=50.0,
    )


@pytest.fixture
def sample_position_model() -> PositionModel:
    """Create a sample PositionModel ORM instance."""
    return PositionModel(
        id=uuid4(),
        address=TEST_POSITION_ADDRESS,
        pool_address=TEST_POOL_ADDRESS,
        status="active",
        side="both",
        price_range={
            "low": {
                "value": 100.0,
                "base_token": {"address": SOL_ADDRESS, "symbol": "SOL", "decimals": 9},
                "quote_token": {"address": USDC_ADDRESS, "symbol": "USDC", "decimals": 6},
            },
            "high": {
                "value": 200.0,
                "base_token": {"address": SOL_ADDRESS, "symbol": "SOL", "decimals": 9},
                "quote_token": {"address": USDC_ADDRESS, "symbol": "USDC", "decimals": 6},
            },
        },
        liquidity={
            "amount": {
                "raw": 1000000000,
                "token": {"address": SOL_ADDRESS, "symbol": "SOL", "decimals": 9},
            }
        },
        distribution={
            "bins": [
                {
                    "bin_id": 10,
                    "liquidity": {
                        "amount": {
                            "raw": 500000000,
                            "token": {"address": SOL_ADDRESS, "symbol": "SOL", "decimals": 9},
                        }
                    },
                },
                {
                    "bin_id": 15,
                    "liquidity": {
                        "amount": {
                            "raw": 500000000,
                            "token": {"address": SOL_ADDRESS, "symbol": "SOL", "decimals": 9},
                        }
                    },
                },
            ]
        },
        fee_earned=50.0,
    )


@pytest.fixture
def sample_position_minimal() -> Position:
    """Create a minimal Position with only required fields."""
    return Position(
        address=PositionAddress(value=TEST_POSITION_ADDRESS),
        pool_address=PoolAddress(value=TEST_POOL_ADDRESS),
        status=PositionStatus.ACTIVE,
        side=PositionSide.BOTH,
    )


@pytest.fixture
def sample_position_model_minimal() -> PositionModel:
    """Create a minimal PositionModel with only required fields."""
    return PositionModel(
        id=uuid4(),
        address=TEST_POSITION_ADDRESS,
        pool_address=TEST_POOL_ADDRESS,
        status="active",
        side="both",
        fee_earned=0.0,
    )


# ============================================================================
# DOMAIN ↔ ORM CONVERSION TESTS
# ============================================================================


class TestConversion:
    """Test lossless bidirectional conversion between Position and PositionModel."""

    def test_domain_to_orm_address(self, sample_position: Position) -> None:
        """Position address should map to PositionModel address."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert model.address == sample_position.address.value

    def test_domain_to_orm_pool_address(self, sample_position: Position) -> None:
        """Position pool_address should map to PositionModel pool_address."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert model.pool_address == sample_position.pool_address.value

    def test_domain_to_orm_status(self, sample_position: Position) -> None:
        """Position status should map to PositionModel status string."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert model.status == "active"

    def test_domain_to_orm_side(self, sample_position: Position) -> None:
        """Position side should map to PositionModel side string."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert model.side == "both"

    def test_domain_to_orm_price_range(self, sample_position: Position) -> None:
        """Position price_range should map to PositionModel JSONB."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert model.price_range["low"]["value"] == 100.0
        assert model.price_range["high"]["value"] == 200.0
        assert model.price_range["low"]["base_token"]["symbol"] == "SOL"

    def test_domain_to_orm_liquidity(self, sample_position: Position) -> None:
        """Position liquidity should map to PositionModel JSONB."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert model.liquidity["amount"]["raw"] == 1000000000
        assert model.liquidity["amount"]["token"]["symbol"] == "SOL"

    def test_domain_to_orm_distribution(self, sample_position: Position) -> None:
        """Position liquidity_distribution should map to PositionModel distribution."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert len(model.distribution["bins"]) == 2
        assert model.distribution["bins"][0]["bin_id"] == 10

    def test_domain_to_orm_fee_earned(self, sample_position: Position) -> None:
        """Position fee_earned should map to PositionModel fee_earned."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        assert model.fee_earned == 50.0

    def test_orm_to_domain_address(self, sample_position_model: PositionModel) -> None:
        """PositionModel address should map to Position address."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert position.address.value == sample_position_model.address

    def test_orm_to_domain_pool_address(self, sample_position_model: PositionModel) -> None:
        """PositionModel pool_address should map to Position pool_address."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert position.pool_address.value == sample_position_model.pool_address

    def test_orm_to_domain_status(self, sample_position_model: PositionModel) -> None:
        """PositionModel status string should map to PositionStatus enum."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert position.status == PositionStatus.ACTIVE

    def test_orm_to_domain_side(self, sample_position_model: PositionModel) -> None:
        """PositionModel side string should map to PositionSide enum."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert position.side == PositionSide.BOTH

    def test_orm_to_domain_price_range(self, sample_position_model: PositionModel) -> None:
        """PositionModel price_range JSONB should map to PriceRange."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert position.price_range.low.value == 100.0
        assert position.price_range.high.value == 200.0
        assert position.price_range.low.base_token.symbol == "SOL"

    def test_orm_to_domain_liquidity(self, sample_position_model: PositionModel) -> None:
        """PositionModel liquidity JSONB should map to Liquidity."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert position.liquidity.amount.raw == 1000000000
        assert position.liquidity.amount.token.symbol == "SOL"

    def test_orm_to_domain_distribution(self, sample_position_model: PositionModel) -> None:
        """PositionModel distribution JSONB should map to LiquidityDistribution."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert len(position.liquidity_distribution.bins) == 2
        assert position.liquidity_distribution.bins[0].bin_id == 10

    def test_orm_to_domain_fee_earned(self, sample_position_model: PositionModel) -> None:
        """PositionModel fee_earned should map to Position fee_earned."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        position = repo._to_domain(sample_position_model)
        assert position.fee_earned == 50.0

    def test_round_trip_lossless(self, sample_position: Position) -> None:
        """Position → PositionModel → Position should be lossless."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position)
        position_back = repo._to_domain(model)

        assert position_back.address == sample_position.address
        assert position_back.pool_address == sample_position.pool_address
        assert position_back.status == sample_position.status
        assert position_back.side == sample_position.side
        assert position_back.fee_earned == sample_position.fee_earned

    def test_round_trip_with_none_optional_fields(self) -> None:
        """Position with None optional fields should survive round trip."""
        position = Position(
            address=PositionAddress(value=TEST_POSITION_ADDRESS),
            pool_address=PoolAddress(value=TEST_POOL_ADDRESS),
            status=PositionStatus.ACTIVE,
            side=PositionSide.BOTH,
            price_range=None,
            liquidity=None,
            liquidity_distribution=None,
        )
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(position)
        position_back = repo._to_domain(model)

        assert position_back.price_range is None
        assert position_back.liquidity is None
        assert position_back.liquidity_distribution is None

    def test_round_trip_minimal(self, sample_position_minimal: Position) -> None:
        """Minimal Position should survive round trip."""
        repo = PostgresPositionRepository.__new__(PostgresPositionRepository)
        model = repo._to_model(sample_position_minimal)
        position_back = repo._to_domain(model)

        assert position_back.address == sample_position_minimal.address
        assert position_back.pool_address == sample_position_minimal.pool_address
        assert position_back.status == sample_position_minimal.status
        assert position_back.side == sample_position_minimal.side


# ============================================================================
# REPOSITORY INTERFACE TESTS
# ============================================================================


class TestRepositoryInterface:
    """Test PostgresPositionRepository implements PositionRepository correctly."""

    def test_implements_position_repository(self, mock_session: AsyncMock) -> None:
        """PostgresPositionRepository should implement PositionRepository."""
        from shared.ports.position_repo import PositionRepository
        repo = PostgresPositionRepository(mock_session)
        assert isinstance(repo, PositionRepository)

    @pytest.mark.asyncio
    async def test_get_by_address_calls_session(
        self, mock_session: AsyncMock, sample_position_model: PositionModel
    ) -> None:
        """get_by_address should execute SELECT query."""
        repo = PostgresPositionRepository(mock_session)
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = sample_position_model
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        position = await repo.get_by_address(
            PositionAddress(value=TEST_POSITION_ADDRESS)
        )

        assert position is not None
        assert position.address.value == TEST_POSITION_ADDRESS
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_pool_calls_session(
        self, mock_session: AsyncMock, sample_position_model: PositionModel
    ) -> None:
        """get_by_pool should execute SELECT query with pool_address filter."""
        repo = PostgresPositionRepository(mock_session)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_position_model]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        positions = await repo.get_by_pool(
            PoolAddress(value=TEST_POOL_ADDRESS)
        )

        assert len(positions) == 1
        assert positions[0].pool_address.value == TEST_POOL_ADDRESS
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_calls_session_add(
        self, mock_session: AsyncMock, sample_position: Position
    ) -> None:
        """save should add model to session."""
        repo = PostgresPositionRepository(mock_session)
        await repo.save(sample_position)
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_active_calls_session_execute(
        self, mock_session: AsyncMock, sample_position_model: PositionModel
    ) -> None:
        """list_active should execute SELECT query with status filter."""
        repo = PostgresPositionRepository(mock_session)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_position_model]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        positions = await repo.list_active()

        assert len(positions) == 1
        assert positions[0].status == PositionStatus.ACTIVE
        mock_session.execute.assert_called_once()


# ============================================================================
# ERROR TRANSLATION TESTS
# ============================================================================


class TestErrorTranslation:
    """Test error translation from SQLAlchemy to domain exceptions."""

    @pytest.mark.asyncio
    async def test_get_by_address_raises_position_not_found_error(
        self, mock_session: AsyncMock
    ) -> None:
        """get_by_address should raise PositionNotFoundError when not found."""
        repo = PostgresPositionRepository(mock_session)
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        with pytest.raises(PositionNotFoundError):
            await repo.get_by_address(
                PositionAddress(value=TEST_POSITION_ADDRESS)
            )

    @pytest.mark.asyncio
    async def test_get_by_pool_returns_empty_list_when_no_positions(
        self, mock_session: AsyncMock
    ) -> None:
        """get_by_pool should return empty list when no positions found."""
        repo = PostgresPositionRepository(mock_session)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        positions = await repo.get_by_pool(
            PoolAddress(value=TEST_POOL_ADDRESS)
        )

        assert positions == []
