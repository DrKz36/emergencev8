# src/backend/features/chat/router.py
# V22.0 - DEBATE WS HANDLER: prise en charge de `debate:create` + validations de base.
import logging
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from dependency_injector.wiring import inject, Provide

from backend.shared.models import ChatMessage, Role
from backend.shared.dependencies import get_user_id_from_websocket
from backend.core.websocket import ConnectionManager
from backend.containers import ServiceContainer

from .service import ChatService
from backend.features.debate.service import DebateService

logger = logging.getLogger(__name__)
router = APIRouter()

# Suivi des tâches WS non bloquantes
background_tasks = set()

@router.websocket("/ws/{session_id}")
@inject
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Depends(get_user_id_from_websocket),
    connection_manager: ConnectionManager = Depends(Provide[ServiceContainer.connection_manager]),
    chat_service: ChatService = Depends(Provide[ServiceContainer.chat_service]),
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service])
):
    # Connexion WS + création/chargement session
    await connection_manager.connect(websocket, session_id, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"---[RAW WS MSG RECEIVED]---: {data}")

            message_type = data.get("type")
            payload = data.get("payload")

            if not message_type or payload is None:
                logger.warning(f"Message WS malformé ou incomplet: {data}")
                # On informe explicitement le client
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": "Message WebSocket incomplet (type/payload)."}},
                        session_id
                    )
                except Exception:
                    pass
                continue

            # =========================
            #  BRANCHE DEBATE:* (WS)
            # =========================
            if message_type.startswith("debate:"):
                try:
                    if message_type == "debate:create":
                        # Validations minimales (le reste est géré par Pydantic dans DebateService)
                        topic = payload.get("topic")
                        agent_order = payload.get("agent_order")
                        rounds = payload.get("rounds")

                        if not topic or not isinstance(topic, str):
                            await connection_manager.send_personal_message(
                                {"type": "ws:error", "payload": {"message": "Débat: 'topic' manquant ou invalide."}},
                                session_id
                            )
                            continue
                        if not agent_order or not isinstance(agent_order, list) or len(agent_order) < 2:
                            await connection_manager.send_personal_message(
                                {"type": "ws:error", "payload": {"message": "Débat: 'agent_order' doit contenir au moins 2 agents (dernier = synthèse)."}},
                                session_id
                            )
                            continue
                        if rounds is None or not isinstance(rounds, int) or rounds < 1:
                            await connection_manager.send_personal_message(
                                {"type": "ws:error", "payload": {"message": "Débat: 'rounds' doit être un entier ≥ 1."}},
                                session_id
                            )
                            continue

                        # Feedback immédiat au client (statut "pending") avant lancement réel
                        await connection_manager.send_personal_message(
                            {"type": "ws:debate_status_update",
                             "payload": {"status": "Initialisation du débat…", "topic": topic}},
                            session_id
                        )

                        # Lancement via le service (il émettra ws:debate_started / ws:debate_turn_update / ws:debate_ended)
                        await debate_service.create_debate(config=payload, session_id=session_id)

                    else:
                        logger.warning(f"Type de message DEBATE non géré: {message_type}")
                        await connection_manager.send_personal_message(
                            {"type": "ws:error", "payload": {"message": f"Type de débat non pris en charge: {message_type}"}},
                            session_id
                        )

                except Exception as e:
                    logger.error(f"Erreur lors du traitement WS débat ({message_type}): {e}", exc_info=True)
                    try:
                        await connection_manager.send_personal_message(
                            {"type": "ws:error", "payload": {"message": f"Erreur interne débat: {str(e)}"}},
                            session_id
                        )
                    except Exception:
                        pass
                continue  # on repart écouter la boucle

            # =========================
            #  BRANCHE CHAT
            # =========================
            elif message_type == "chat.message":
                logger.info(f"Message de chat '{message_type}' intercepté pour traitement.")
                try:
                    message_content = payload.get("text")
                    if not message_content:
                        logger.warning(f"Message de chat reçu sans contenu textuel: {payload}")
                        await connection_manager.send_personal_message(
                            {"type": "ws:error", "payload": {"message": "Message de chat sans texte."}},
                            session_id
                        )
                        continue

                    # Récupère l'agent cible éventuel et conforme l'API du ChatService
                    target_agent = payload.get("agent_id")
                    agents_list = [target_agent] if target_agent else []

                    chat_request = ChatMessage(
                        id=str(uuid4()),
                        session_id=session_id,
                        role=Role.USER,
                        agent="user",
                        content=message_content,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        agents=agents_list,
                        use_rag=payload.get("use_rag", False)
                    )

                    task = asyncio.create_task(
                        chat_service.process_user_message_for_agents(session_id, chat_request, connection_manager)
                    )
                    background_tasks.add(task)
                    task.add_done_callback(background_tasks.discard)

                except Exception as e:
                    logger.error(f"Erreur lors de la création de la tâche de chat: {e}", exc_info=True)
                    try:
                        await connection_manager.send_personal_message(
                            {"type": "ws:error", "payload": {"message": f"Erreur interne chat: {str(e)}"}},
                            session_id
                        )
                    except Exception:
                        pass

            else:
                logger.warning(f"Type de message WS non géré: {message_type}")
                await connection_manager.send_personal_message(
                    {"type": "ws:error", "payload": {"message": f"Type non géré: {message_type}"}},
                    session_id
                )

    except WebSocketDisconnect:
        await connection_manager.disconnect(session_id, websocket)
        logger.info(f"Client déconnecté. Session {session_id} marquée pour finalisation.")
    except Exception as e:
        logger.error(f"Erreur inattendue dans le WebSocket pour la session {session_id}: {e}", exc_info=True)
        try:
            await connection_manager.disconnect(session_id, websocket)
        except Exception:
            pass
