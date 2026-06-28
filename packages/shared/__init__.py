"""Liquidity OS domain layer.

[WHY] Provides all domain types (entities, value objects, ports, enums)
      that the entire system depends on.

[OWNERSHIP] Domain layer — the heart of Clean Architecture.

[DEPENDENTS] Allowed: everything (database, feature-store, rule-engine,
             decision-log, simulation, apps/*, agents/*).
             Forbidden: nothing — this is the innermost layer.
"""
