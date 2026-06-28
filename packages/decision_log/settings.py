"""Configuration for Decision Log package.

[WHY] Centralizes all configuration for the Decision Log package.
      Uses explicit settings with sensible defaults — no magic constants.

[OWNERSHIP] Infrastructure layer — configuration.

[DEPENDENTS] Allowed: logger, query, models.
             Forbidden: shared, apps, agents.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DecisionLogSettings(BaseModel):
    """[WHY] Configuration for Decision Log storage and retention.

    [OWNERSHIP] Infrastructure layer — settings.

    [DEPENDENTS] Allowed: logger, query.
                 Forbidden: shared, apps, agents.

    [EXAMPLE]
        settings = DecisionLogSettings()
        assert settings.retention_days == 90
    """

    model_config = {"frozen": True}

    # Retention
    retention_days: int = Field(
        default=90,
        description="Number of days to retain decision records",
    )

    # Query defaults
    default_query_limit: int = Field(
        default=100,
        description="Default limit for query results",
    )

    max_query_limit: int = Field(
        default=1000,
        description="Maximum allowed query limit",
    )

    # Batch operations
    batch_size: int = Field(
        default=100,
        description="Batch size for bulk operations",
    )

    # Table name
    table_name: str = Field(
        default="decision_log",
        description="Name of the database table",
    )
