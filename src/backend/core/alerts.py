"""
Module d'alertes pour notifications Slack
Permet d'envoyer des alertes critiques/warning/info
"""

import os
from datetime import datetime, timezone
from typing import Any, Literal
import httpx

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


class SlackAlerter:
    """Gestionnaire d'alertes Slack"""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or SLACK_WEBHOOK_URL
        self.enabled = bool(self.webhook_url)

    async def send_alert(
        self,
        message: str,
        severity: Literal["critical", "warning", "info"] = "warning",
        **metadata: Any
    ) -> None:
        """
        Envoie une alerte Slack

        Args:
            message: Message de l'alerte
            severity: Niveau de sévérité (critical/warning/info)
            **metadata: Données additionnelles à inclure
        """
        if not self.enabled:
            return

        color = {
            "critical": "#ff0000",  # Rouge
            "warning": "#ff9900",   # Orange
            "info": "#36a64f",      # Vert
        }[severity]

        emoji = {
            "critical": ":fire:",
            "warning": ":warning:",
            "info": ":information_source:",
        }[severity]

        # Construire le payload Slack
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{emoji} {severity.upper()} ALERT",
                    "text": message,
                    "fields": [
                        {"title": key, "value": str(value), "short": True}
                        for key, value in metadata.items()
                    ],
                    "footer": "Emergence Monitoring",
                    "ts": int(datetime.now(timezone.utc).timestamp()),
                }
            ]
        }

        try:
            if not self.webhook_url:
                return
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=5.0,
                )
                response.raise_for_status()
        except Exception as e:
            # Ne pas crasher l'app si Slack est down
            import logging
            logging.error(f"Erreur envoi alerte Slack: {e}")

    async def alert_critical(self, message: str, **metadata: Any) -> None:
        """Alerte critique (rouge)"""
        await self.send_alert(message, severity="critical", **metadata)

    async def alert_warning(self, message: str, **metadata: Any) -> None:
        """Alerte warning (orange)"""
        await self.send_alert(message, severity="warning", **metadata)

    async def alert_info(self, message: str, **metadata: Any) -> None:
        """Alerte info (vert)"""
        await self.send_alert(message, severity="info", **metadata)


# Instance globale
slack_alerter = SlackAlerter()


# Fonctions helpers pour usage direct
async def alert_critical(message: str, **kwargs: Any) -> None:
    """Envoie une alerte critique"""
    await slack_alerter.alert_critical(message, **kwargs)


async def alert_warning(message: str, **kwargs: Any) -> None:
    """Envoie une alerte warning"""
    await slack_alerter.alert_warning(message, **kwargs)


async def alert_info(message: str, **kwargs: Any) -> None:
    """Envoie une alerte info"""
    await slack_alerter.alert_info(message, **kwargs)


# Exemples d'utilisation
"""
# Dans votre code:
from backend.core.alerts import alert_critical, alert_warning, alert_info

# Alerte critique
await alert_critical(
    "Taux d'erreur critique dépassé",
    error_rate="12.5%",
    endpoint="/api/chat",
    duration="5min"
)

# Alerte warning
await alert_warning(
    "Latence élevée détectée",
    p95_latency="3.2s",
    endpoint="/api/threads"
)

# Alerte info
await alert_info(
    "Déploiement réussi",
    version="v1.2.0",
    deployed_at="2025-01-08 10:30:00"
)
"""
