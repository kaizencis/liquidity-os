"""Meteora-specific exceptions for the adapter layer.

[WHY] Infrastructure exceptions for Meteora API communication errors.
      Domain exceptions remain in shared.exceptions.
[OWNERSHIP] Infrastructure layer — Meteora adapter errors.
[DEPENDENTS] Allowed: meteora.client, meteora.adapters.
             Forbidden: shared, apps, agents.
"""


class MeteoraError(Exception):
    """[WHY] Base exception for all Meteora adapter errors.
    [OWNERSHIP] Infrastructure layer — base error class.
    [DEPENDENTS] Allowed: meteora.client, meteora.adapters.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        raise MeteoraError("API connection failed")
    """


class MeteoraNotFoundError(MeteoraError):
    """[WHY] Raised when a resource is not found (HTTP 404).
    [OWNERSHIP] Infrastructure layer — specific error class.
    [DEPENDENTS] Allowed: meteora.client.
                 Forbidden: shared, apps, agents.
    [EXAMPLE]
        raise MeteoraNotFoundError("Pool not found")
    """
