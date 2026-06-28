"""Domain exceptions for Liquidity OS.

[WHY] Typed exceptions enable precise error handling at every boundary.
      Callers can catch specific exceptions without parsing error messages.
      Domain exceptions carry context (e.g., which pool address was not found)
      without leaking infrastructure details (e.g., SQL errors).

[OWNERSHIP] Domain layer — used by all entities, ports, apps, and agents.

[DEPENDENTS] Allowed: entities, value_objects, ports, apps, agents.
             Forbidden: infrastructure (database, redis, httpx).

[EXAMPLE]
    from shared.exceptions import PoolNotFoundError, InvalidConfigurationError

    pool = await repo.get_by_address(addr)
    if pool is None:
        raise PoolNotFoundError(address=addr)

    if threshold < 0:
        raise InvalidConfigurationError(
            field="threshold",
            value=threshold,
            reason="must be non-negative",
        )
"""

from __future__ import annotations


class DomainError(Exception):
    """[WHY] Base exception for all domain errors in Liquidity OS.

    [OWNERSHIP] Domain layer — root of the exception hierarchy.

    [DEPENDENTS] Allowed: all domain, app, and agent code.
                 Forbidden: none.

    [EXAMPLE]
        try:
            await some_domain_operation()
        except DomainError as e:
            logger.error(f"Domain error: {e}")
    """

    def __init__(self, message: str = "Domain error occurred") -> None:
        super().__init__(message)
        self.message = message


class PoolNotFoundError(DomainError):
    """[WHY] Raised when a pool cannot be found by its address.

    [OWNERSHIP] Domain layer — specific domain error.

    [DEPENDENTS] Allowed: entities.pool, ports.pool_repo,
                 apps.collector, apps.analytics, apps.dashboard,
                 agents.oracle, agents.navigator.

    [EXAMPLE]
        pool = await repo.get_by_address(PoolAddress("7Ytt..."))
        if pool is None:
            raise PoolNotFoundError(address=PoolAddress("7Ytt..."))
    """

    def __init__(self, address: object) -> None:
        self.address = address
        super().__init__(f"Pool not found: {address}")


class PositionNotFoundError(DomainError):
    """[WHY] Raised when a position cannot be found by its address.

    [OWNERSHIP] Domain layer — specific domain error.

    [DEPENDENTS] Allowed: entities.position, ports.position_repo,
                 apps.collector, apps.dashboard, agents.navigator.

    [EXAMPLE]
        pos = await repo.get_by_address(PositionAddress("AJ6z..."))
        if pos is None:
            raise PositionNotFoundError(address=PositionAddress("AJ6z..."))
    """

    def __init__(self, address: object) -> None:
        self.address = address
        super().__init__(f"Position not found: {address}")


class InvalidConfigurationError(DomainError):
    """[WHY] Raised when a configuration value is invalid or out of range.

    [OWNERSHIP] Domain layer — specific domain error.

    [DEPENDENTS] Allowed: value_objects, ports, apps, agents,
                 rule_engine, feature_store.

    [EXAMPLE]
        if threshold < 0:
            raise InvalidConfigurationError(
                field="volatility_threshold",
                value=threshold,
                reason="must be non-negative",
            )
    """

    def __init__(self, field: str, value: object, reason: str) -> None:
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Invalid {field}: {value!r} — {reason}")
