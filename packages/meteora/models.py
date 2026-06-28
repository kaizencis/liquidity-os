"""DTOs for Meteora DLMM API responses.

[WHY] Defines data transfer objects for API responses.
      Minimal fields only — no business logic.
[OWNERSHIP] Infrastructure layer — API data structures.
[DEPENDENTS] Allowed: meteora.client, meteora.mappers.
             Forbidden: shared, apps, agents.
[EXAMPLE]
    from meteora.models import PoolResponseDTO, TokenMetricsDTO

    dto = PoolResponseDTO(
        address="7Ytt...",
        name="SOL/USDC",
        token_x=TokenMetricsDTO(address="So111...", symbol="SOL", decimals=9),
        token_y=TokenMetricsDTO(address="EPjF...", symbol="USDC", decimals=6),
        ...
    )
"""

from __future__ import annotations

from pydantic import BaseModel


class TokenMetricsDTO(BaseModel):
    """[WHY] Minimal token data from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        token = TokenMetricsDTO(address="So111...", symbol="SOL", decimals=9)
    """

    address: str
    symbol: str
    decimals: int


class PoolConfigDTO(BaseModel):
    """[WHY] Minimal pool config from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        config = PoolConfigDTO(bin_step=1, base_fee_pct=0.3)
    """

    bin_step: int
    base_fee_pct: float


class PoolResponseDTO(BaseModel):
    """[WHY] Minimal pool response from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        pool = PoolResponseDTO(
            address="7Ytt...",
            name="SOL/USDC",
            token_x=TokenMetricsDTO(...),
            token_y=TokenMetricsDTO(...),
            pool_config=PoolConfigDTO(...),
            current_price=150.0,
            dynamic_fee_pct=0.3,
            tvl=1000000.0,
            is_blacklisted=False,
            created_at=1234567890,
        )
    """

    address: str
    name: str
    token_x: TokenMetricsDTO
    token_y: TokenMetricsDTO
    pool_config: PoolConfigDTO
    current_price: float
    dynamic_fee_pct: float
    tvl: float
    is_blacklisted: bool
    created_at: int


class PaginationResponseDTO(BaseModel):
    """[WHY] Paginated pool response from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        response = PaginationResponseDTO(
            total=1000,
            pages=10,
            current_page=1,
            page_size=100,
            data=[PoolResponseDTO(...)],
        )
    """

    total: int
    pages: int
    current_page: int
    page_size: int
    data: list[PoolResponseDTO]


class TokenAmountDTO(BaseModel):
    """[WHY] Token amount from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        amount = TokenAmountDTO(amount="1000000", usd="150.0")
    """

    amount: str
    usd: str


class TotalUsdDTO(BaseModel):
    """[WHY] USD total from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        total = TotalUsdDTO(usd="500.0", sol="2.5")
    """

    usd: str
    sol: str | None = None


class TokenPairWithTotalDTO(BaseModel):
    """[WHY] Token pair with totals from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        pair = TokenPairWithTotalDTO(
            tokenX=TokenAmountDTO(amount="100", usd="150"),
            tokenY=TokenAmountDTO(amount="50", usd="50"),
            total=TotalUsdDTO(usd="200"),
        )
    """

    tokenX: TokenAmountDTO
    tokenY: TokenAmountDTO
    total: TotalUsdDTO


class PositionPnLResponseDTO(BaseModel):
    """[WHY] Position PnL data from Meteora API.
    [OWNERSHIP] Infrastructure layer — API DTO.
    [EXAMPLE]
        position = PositionPnLResponseDTO(
            positionAddress="AJ6z...",
            minPrice="140.0",
            maxPrice="160.0",
            lowerBinId=100,
            upperBinId=200,
            isClosed=False,
            allTimeDeposits=TokenPairWithTotalDTO(...),
            allTimeFees=TokenPairWithTotalDTO(...),
        )
    """

    positionAddress: str
    minPrice: str
    maxPrice: str
    lowerBinId: int
    upperBinId: int
    isClosed: bool
    allTimeDeposits: TokenPairWithTotalDTO
    allTimeFees: TokenPairWithTotalDTO
