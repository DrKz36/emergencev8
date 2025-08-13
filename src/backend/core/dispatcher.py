# src/backend/core/dispatcher.py
import logging
import json
from fastapi import WebSocket

# On importe les 'service' et 'models' dont on aura besoin pour le dispatching
# Note: On importe les classes de service, pas les instances.
from backend.features.chat.service import ChatService
from backend.features.debate.service import DebateService
from backend.features.debate.models import DebateConfig
from backend.shared.models import ChatMessage

logger = logging.getLogger(__name__)

class WebSocketDispatcher:
    def __init__(self, chat_service: ChatService, debate_service: DebateService):
        """
        Initialise le dispatcher avec les instances des services nécessaires.
        """
        self.chat_service = chat_service
        self.debate_service = debate_service
        # Le routage interne basé sur le 'type' du message WebSocket
        self._routes = {
            "chat:message": self._handle_chat_message,
            "debate:create": self._handle_debate_create,
        }
        logger.info("WebSocketDispatcher V1.0 initialisé avec les routes : chat, debate.")

    async def dispatch(self, websocket: WebSocket, session_id: str, raw_data: str):
        """
        Point d'entrée. Analyse le message et le dirige vers le bon handler.
        """
        try:
            data = json.loads(raw_data)
            message_type = data.get("type")
            payload = data.get("payload")

            if not message_type or payload is None:
                logger.warning(f"Message WebSocket invalide (type ou payload manquant): {raw_data}")
                return

            handler = self._routes.get(message_type)
            if handler:
                logger.info(f"Dispatching de l'événement '{message_type}' vers son handler.")
                await handler(session_id, payload)
            else:
                logger.warning(f"Aucun handler trouvé pour le message de type '{message_type}'.")

        except json.JSONDecodeError:
            logger.error(f"Erreur de décodage JSON pour le message WebSocket: {raw_data}")
        except Exception as e:
            logger.error(f"Erreur inattendue dans le dispatcher WebSocket: {e}", exc_info=True)

    async def _handle_chat_message(self, session_id: str, payload: dict):
        """Gère les messages destinés au service de chat."""
        try:
            # On valide que le payload correspond bien à un ChatMessage
            chat_request = ChatMessage(**payload)
            await self.chat_service.process_user_message_for_agents(
                session_id=session_id,
                chat_request=chat_request
            )
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message de chat: {e}, payload: {payload}")

    async def _handle_debate_create(self, session_id: str, payload: dict):
        """Gère les demandes de création de débat."""
        try:
            # Pydantic validera la configuration du débat ici
            debate_config = DebateConfig(**payload)
            
            # Appel de la méthode du service de débat
            await self.debate_service.create_debate(
                session_id=session_id,
                config=debate_config
            )
        except Exception as e:
            logger.error(f"Erreur lors de la création du débat: {e}, payload: {payload}")