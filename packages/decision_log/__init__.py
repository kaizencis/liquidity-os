"""Decision Log package for Liquidity OS.

[WHY] Provides append-only audit trail for all agent decisions.
      Implements the DecisionLog port from shared package.

[OWNERSHIP] Infrastructure layer — implements shared.ports.decision_log.

[DEPENDENTS] Allowed: apps, agents (via DecisionLog port).
             Forbidden: shared (must go through ports).

[EXAMPLE]
    from decision_log import PostgresDecisionLog, DecisionQuery

    logger = PostgresDecisionLog(session)
    query = DecisionQuery(session)

    await logger.append(decision)
    results = await query.query_by_agent(AgentRole.ORACLE)
"""

from decision_log.errors import (
    DecisionLogError,
    DecisionNotFoundError,
    DuplicateDecisionError,
    QueryError,
)
from decision_log.logger import PostgresDecisionLog
from decision_log.query import DecisionQuery
from decision_log.settings import DecisionLogSettings

__all__ = [
    # Settings
    "DecisionLogSettings",
    # Errors
    "DecisionLogError",
    "DecisionNotFoundError",
    "DuplicateDecisionError",
    "QueryError",
    # Logger (write path)
    "PostgresDecisionLog",
    # Query (read path)
    "DecisionQuery",
]
