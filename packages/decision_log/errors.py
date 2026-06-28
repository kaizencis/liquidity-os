"""Decision Log exceptions for Liquidity OS.

[WHY] Typed exceptions enable precise error handling at every boundary.
      Callers can catch specific exceptions without parsing error messages.

[OWNERSHIP] Infrastructure layer — decision-log specific exceptions.

[DEPENDENTS] Allowed: logger, query, tests.
             Forbidden: shared, apps, agents.

[EXAMPLE]
    from decision_log.errors import DuplicateDecisionError

    raise DuplicateDecisionError(decision_id=did)
"""

from __future__ import annotations

from shared.exceptions import DomainError
from shared.identifiers import DecisionId


class DecisionLogError(DomainError):
    """[WHY] Base exception for all Decision Log errors.

    [OWNERSHIP] Infrastructure layer — root of decision-log exception hierarchy.

    [DEPENDENTS] Allowed: logger, query, tests.
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        try:
            await decision_log.append(decision)
        except DecisionLogError as e:
            logger.error(f"Decision Log error: {e}")
    """

    def __init__(self, message: str = "Decision Log error occurred") -> None:
        super().__init__(message)


class DecisionNotFoundError(DecisionLogError):
    """[WHY] Raised when a decision cannot be found by its ID.

    [OWNERSHIP] Infrastructure layer — specific decision-log error.

    [DEPENDENTS] Allowed: logger, query.
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        decision = await decision_log.get_by_id(did)
        if decision is None:
            raise DecisionNotFoundError(decision_id=did)
    """

    def __init__(self, decision_id: DecisionId) -> None:
        self.decision_id = decision_id
        super().__init__(f"Decision not found: {decision_id}")


class DuplicateDecisionError(DecisionLogError):
    """[WHY] Raised when attempting to append a decision that already exists.

    [OWNERSHIP] Infrastructure layer — specific decision-log error.

    [DEPENDENTS] Allowed: logger.
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        existing = await decision_log.get_by_id(decision.id)
        if existing is not None:
            raise DuplicateDecisionError(decision_id=decision.id)
    """

    def __init__(self, decision_id: DecisionId) -> None:
        self.decision_id = decision_id
        super().__init__(f"Decision already exists: {decision_id}")


class QueryError(DecisionLogError):
    """[WHY] Raised when a query operation fails.

    [OWNERSHIP] Infrastructure layer — specific decision-log error.

    [DEPENDENTS] Allowed: query.
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        try:
            results = await decision_log.query(agent=AgentRole.ORACLE)
        except QueryError as e:
            logger.error(f"Query failed: {e}")
    """

    def __init__(self, message: str = "Query operation failed") -> None:
        super().__init__(message)
