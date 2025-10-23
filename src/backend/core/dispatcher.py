# src/backend/core/dispatcher.py
import json
import logging
from typing import Any
from fastapi import WebSocket

from backend.features.chat.service import ChatService
from backend.features.debate.service import DebateService, DebateConfig as DebateServiceConfig
from backend.features.debate.models import DebateConfig as DebateConfigModel
from backend.shared.models import ChatMessage

logger = logging.getLogger(__name__)


class WebSocketDispatcher:
    def __init__(self, chat_service: ChatService, debate_service: DebateService):
        """Initialise le dispatcher avec les instances des services necessaires."""
        self.chat_service = chat_service
        self.debate_service = debate_service
        self._routes = {
            "chat:message": self._handle_chat_message,
            "debate:create": self._handle_debate_create,
        }
        logger.info("WebSocketDispatcher V1.0 initialise avec les routes : chat, debate.")

    async def dispatch(self, websocket: WebSocket, session_id: str, raw_data: str) -> None:
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

            handler = self._routes.get(message_type)
            if handler:
                logger.info("Dispatch de l'evenement '%s' vers son handler.", message_type)
                await handler(session_id, payload)
            else:
                logger.warning("Aucun handler trouve pour le message de type '%s'.", message_type)

        except json.JSONDecodeError:
            logger.error("Erreur de decodage JSON pour le message WebSocket: %s", raw_data)
        except Exception as exc:
            logger.error(
                "Erreur inattendue dans le dispatcher WebSocket: %s",
                exc,
                exc_info=True,
            )

    async def _handle_chat_message(self, session_id: str, payload: dict[str, Any]) -> None:
        """Gere les messages destines au service de chat."""
        try:
            chat_request = ChatMessage(**payload)
            self.chat_service.process_user_message_for_agents(
                session_id=session_id,
                chat_request=chat_request,
            )
        except Exception as exc:
            logger.error(
                "Erreur lors du traitement du message de chat: %s, payload: %s",
                exc,
                payload,
            )

    async def _handle_debate_create(self, session_id: str, payload: dict[str, Any]) -> None:
        """Gere les demandes de creation de debat."""
        try:
            debate_config_model = DebateConfigModel(**payload)
            service_config = DebateServiceConfig(
                topic=debate_config_model.topic,
                rounds=debate_config_model.rounds,
                agent_order=list(debate_config_model.agent_order),
                use_rag=debate_config_model.use_rag,
                doc_ids=None,
            )
            await self.debate_service.run(
                session_id=session_id,
                config=service_config,
            )
        except Exception as exc:
            logger.error(
                "Erreur lors de la creation du debat: %s, payload: %s",
                exc,
                payload,
            )
