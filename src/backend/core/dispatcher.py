# src/backend/core/dispatcher.py
import json
import logging
from typing import Any, Callable, Awaitable, Dict

logger = logging.getLogger(__name__)

HandlerType = Callable[[str, Dict[str, Any]], Awaitable[None]]


class WebSocketDispatcher:
    def __init__(self):
        """Initialise le dispatcher sans dépendances directes."""
        self._routes: Dict[str, HandlerType] = {}
        logger.info("WebSocketDispatcher V2.0 (Generic) initialisé.")

    def register_handler(self, message_type: str, handler: HandlerType) -> None:
        """Enregistre un handler pour un type de message donné."""
        self._routes[message_type] = handler
        logger.debug(f"Handler enregistré pour '{message_type}'")

    async def dispatch(
        self, session_id: str, raw_data: str
    ) -> None:
        """Point d'entree : route les evenements recus sur la connexion WS."""
        try:
            data = json.loads(raw_data)
            message_type = data.get("type")
            payload = data.get("payload")

            if not message_type or payload is None:
                logger.warning(
                    "Message WebSocket invalide (type ou payload manquant): %s",
                    raw_data,
                )
                return

            # Normalisation basique si nécessaire (peut être fait en amont)
            # Ici on suppose que message_type correspond exactement à la clé enregistrée

            await self.dispatch_payload(session_id, message_type, payload)

        except json.JSONDecodeError:
            logger.error(
                "Erreur de decodage JSON pour le message WebSocket: %s", raw_data
            )
        except Exception as exc:
            logger.error(
                "Erreur inattendue dans le dispatcher WebSocket: %s",
                exc,
                exc_info=True,
            )

    async def dispatch_payload(
        self, session_id: str, message_type: str, payload: Dict[str, Any]
    ) -> None:
        """Dispatche un payload déjà décodé vers le bon handler."""
        handler = self._routes.get(message_type)
        if handler:
            logger.debug(
                "Dispatch de l'evenement '%s' vers son handler.", message_type
            )
            await handler(session_id, payload)
        else:
            logger.warning(
                "Aucun handler trouve pour le message de type '%s'.", message_type
            )
