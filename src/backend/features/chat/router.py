# src/backend/features/chat/router.py
# V22.3 - WS CHAT: accept legacy aliases ('chat:send', 'chat_message') by normalizing to 'chat.message'
#            payload plat -> service, save user message, no create_task on sync call
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

# Suivi des tâches WS non bloquantes (utile pour d’autres branches)
background_tasks = set()

def _norm_bool(payload, snake_key, camel_key, default=False):
    if snake_key in payload: return bool(payload.get(snake_key))
    if camel_key in payload: return bool(payload.get(camel_key))
    return default

def _norm_list(payload, snake_key, camel_key):
    val = payload.get(snake_key)
    if val is None:
        val = payload.get(camel_key)
    return val

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
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": "Message WebSocket incomplet (type/payload)."}} ,
                        session_id
                    )
                except Exception:
                    pass
                continue

            # Normalisation des alias historiques pour compatibilité clients
            if isinstance(message_type, str) and message_type in {"chat:send", "chat_message"}:
                logger.info(f"[WS] Normalisation du type hérité '{message_type}' -> 'chat.message'")
                message_type = "chat.message"

            # =========================
            #  BRANCHE DEBATE:* (WS)
            # =========================
            if message_type.startswith("debate:"):
                try:
                    if message_type == "debate:create":
                        # Normalisation camelCase/snake_case
                        topic       = payload.get("topic")
                        agent_order = _norm_list(payload, "agent_order", "agentOrder")
                        rounds      = payload.get("rounds")
                        use_rag     = _norm_bool(payload, "use_rag", "useRag", default=False)

                        # Validations minimales (le reste côté Pydantic/service)
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

                        # Feedback immédiat
                        await connection_manager.send_personal_message(
                            {"type": "ws:debate_status_update",
                             "payload": {"status": "Initialisation du débat…", "topic": topic}},
                            session_id
                        )

                        # Lancement via le service avec une config NORMALISÉE
                        normalized_config = {
                            "topic": topic,
                            "agent_order": agent_order,
                            "rounds": rounds,
                            "use_rag": use_rag
                        }
                        await debate_service.create_debate(config=normalized_config, session_id=session_id)

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
                    # 1) Récupérer et valider le texte utilisateur
                    message_content = payload.get("text") or payload.get("content") or payload.get("message")
                    if not (isinstance(message_content, str) and message_content.strip()):
                        logger.warning(f"Message de chat reçu sans contenu textuel: {payload}")
                        await connection_manager.send_personal_message(
                            {"type": "ws:error", "payload": {"message": "Message de chat sans texte."}},
                            session_id
                        )
                        continue

                    # 2) Écrire le message utilisateur dans l'historique (avant la réponse agent)
                    target_agent = payload.get("agent_id") or payload.get("agentId")
                    use_rag_flag = _norm_bool(payload, "use_rag", "useRag", default=False)

                    user_msg = ChatMessage(
                        id=str(uuid4()),
                        session_id=session_id,
                        role=Role.USER,
                        agent="user",
                        content=message_content,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        agents=[target_agent] if target_agent else [],
                        use_rag=use_rag_flag,
                    )
                    await chat_service.session_manager.add_message_to_session(session_id, user_msg)

                    # 3) Appeler le service avec un payload PLAT attendu (snake_case), sans create_task ici
                    normalized = {
                        "agent_id": (target_agent or "").strip().lower(),
                        "use_rag": bool(use_rag_flag),
                        "text": message_content,
                    }
                    chat_service.process_user_message_for_agents(session_id, normalized, connection_manager)

                except Exception as e:
                    logger.error(f"Erreur lors du traitement du chat: {e}", exc_info=True)
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
