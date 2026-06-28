"""Type-safe identifier wrappers for the Liquidity OS domain.

[WHY] Solana addresses and transaction signatures are plain strings.
      Without type safety, a PoolAddress could be accidentally passed
      where a PositionAddress is expected — a bug caught only at runtime.

[OWNERSHIP] Domain layer — defines identity types used by all entities.

[DEPENDENTS] Allowed: entities, value_objects, ports, apps, agents.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.identifiers import PoolAddress, PositionAddress

    pool_id = PoolAddress("7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY...")
    pos_id = PositionAddress("AJ6z3Z...")

    # Type-safe: this would be a type error
    # repo.get_by_address(pool_id)  # expects PoolAddress ✓
    # repo.get_by_address(pos_id)   # expects PositionAddress ✗
"""

from __future__ import annotations

import re
import uuid
from typing import Final

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SOLANA_ADDRESS_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------


class PoolAddress(BaseModel):
    """[WHY] Uniquely identifies a Meteora DLMM pool on Solana.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.pool, ports.pool_repo, ports.snapshot_repo,
                 apps.collector, apps.analytics, apps.dashboard, apps.telegram,
                 agents.oracle, agents.navigator.
                 Forbidden: infrastructure packages.

    [EXAMPLE]
        addr = PoolAddress(value="7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY")
        print(addr.value)  # "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eSTY"
    """

    model_config = {"frozen": True}

    value: str = Field(..., description="Base-58 encoded Solana address (32-44 chars)")

    @field_validator("value")
    @classmethod
    def validate_solana_address(cls, v: str) -> str:
        if not _SOLANA_ADDRESS_PATTERN.match(v):
            msg = f"Invalid Solana address format: {v!r}"
            raise ValueError(msg)
        return v

    def __str__(self) -> str:
        return self.value


class PositionAddress(BaseModel):
    """[WHY] Uniquely identifies a liquidity position on Meteora DLMM.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.position, ports.position_repo,
                 apps.collector, apps.dashboard, agents.navigator.
                 Forbidden: infrastructure packages.

    [EXAMPLE]
        addr = PositionAddress(value="AJ6z3Zm9uGaNbJf8xLq3...")
        print(addr.value)  # "AJ6z3Zm9uGaNbJf8xLq3..."
    """

    model_config = {"frozen": True}

    value: str = Field(..., description="Base-58 encoded Solana address (32-44 chars)")

    @field_validator("value")
    @classmethod
    def validate_solana_address(cls, v: str) -> str:
        if not _SOLANA_ADDRESS_PATTERN.match(v):
            msg = f"Invalid Solana address format: {v!r}"
            raise ValueError(msg)
        return v

    def __str__(self) -> str:
        return self.value


class TxSignature(BaseModel):
    """[WHY] Uniquely identifies a Solana transaction on-chain.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.decision, ports.decision_log,
                 apps.collector, agents.navigator.
                 Forbidden: infrastructure packages.

    [EXAMPLE]
        sig = TxSignature(value="5VERv8NMhJQV...txSig...")
        print(sig.value)  # "5VERv8NMhJQV...txSig..."
    """

    model_config = {"frozen": True}

    value: str = Field(..., description="Base-58 encoded Solana transaction signature")

    @field_validator("value")
    @classmethod
    def validate_signature(cls, v: str) -> str:
        if not _SOLANA_ADDRESS_PATTERN.match(v):
            msg = f"Invalid transaction signature format: {v!r}"
            raise ValueError(msg)
        return v

    def __str__(self) -> str:
        return self.value


class DecisionId(BaseModel):
    """[WHY] Uniquely identifies a decision record in the audit trail.

    [OWNERSHIP] Domain layer — immutable value object.

    [DEPENDENTS] Allowed: entities.decision, ports.decision_log,
                 apps.analytics, apps.dashboard, agents.oracle, agents.navigator.
                 Forbidden: infrastructure packages.

    [EXAMPLE]
        did = DecisionId(value=uuid.uuid4())
        print(did.value)  # UUID4 e.g. 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
    """

    model_config = {"frozen": True}

    value: uuid.UUID = Field(..., description="UUID v4 unique identifier")

    @classmethod
    def generate(cls) -> DecisionId:
        """Create a new DecisionId with a random UUID4."""
        return cls(value=uuid.uuid4())

    def __str__(self) -> str:
        return str(self.value)
