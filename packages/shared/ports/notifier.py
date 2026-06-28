"""Notifier interface for Liquidity OS.

[WHY] Defines the contract for sending notifications (alerts, reports, approvals).
      The domain defines what notifications are needed; infrastructure (Telegram,
      email, webhook) provides the implementation.

[OWNERSHIP] Domain layer — port interface.

[DEPENDENTS] Allowed: telegram (implements), agents.oracle, agents.navigator.
             Forbidden: infrastructure implementations in this file.

[EXAMPLE]
    from shared.ports.notifier import Notifier

    class TelegramNotifier(Notifier):
        async def send_alert(self, message: str, severity: str) -> None:
            # Telegram API call here
            ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shared.enums import AlertSeverity


class Notifier(ABC):
    """[WHY] Sends notifications to users via various channels.

    [OWNERSHIP] Domain layer — defines the contract for notification delivery.

    [DEPENDENTS] Allowed: telegram (implements), oracle, navigator.
                 Forbidden: shared, database (must go through ports).

    [EXAMPLE]
        notifier = TelegramNotifier(bot)
        await notifier.send_alert("High volatility detected", AlertSeverity.CRITICAL)
    """

    @abstractmethod
    async def send_alert(
        self,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
    ) -> None:
        """Send an alert notification."""

    @abstractmethod
    async def send_report(
        self,
        title: str,
        content: str,
    ) -> None:
        """Send a report notification."""

    @abstractmethod
    async def send_approval_request(
        self,
        message: str,
        callback_data: str,
    ) -> None:
        """Send an approval request with callback."""
