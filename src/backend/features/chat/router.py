# src/backend/features/chat/router.py
# V22.8 — Fix ChatMessage (id/session_id/content/timestamp) + dédoublon doux si POST REST déjà passé

import logging
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, Depends
from dependency_injector.wiring import inject, Provide

from backend.shared.models import ChatMessage, Role
from backend.shared import dependencies as deps
from backend.core.websocket import ConnectionManager
from backend.containers import ServiceContainer

from .service import ChatService
from backend.features.debate.service import DebateService

logger = logging.getLogger(__name__)
router = APIRouter()

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
    connection_manager: ConnectionManager = Depends(Provide[ServiceContainer.connection_manager]),
    chat_service: ChatService = Depends(Provide[ServiceContainer.chat_service]),
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service]),
):
    # Auth 'accept-first' tolérante
    _uid = None
    try:
        tok = deps._extract_ws_bearer_token(websocket)
        if tok:
            claims = deps._read_bearer_claims_from_token(tok)
            deps._enforce_allowlist_claims(claims)
            _uid = str(claims.get("sub") or "")
    except Exception as e:
        logger.info(f"WS auth tentative échouée: {e}")

    await connection_manager.connect(websocket, session_id, _uid or f"guest:{session_id}")
    if not _uid:
        try:
            await connection_manager.send_personal_message(
                {"type": "ws:auth_required", "payload": {"message": "Authentication required", "reason": "missing_or_invalid_token"}},
                session_id
            )
        except Exception:
            pass
        try:
            await websocket.close(code=4401)
        finally:
            await connection_manager.disconnect(session_id, websocket)
        return

    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"---[RAW WS MSG RECEIVED]---: {data}")

            message_type = data.get("type")
            payload = data.get("payload")

            if not message_type or payload is None:
                logger.warning(f"Message WS incomplet: {data}")
                try:
                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": "Message WebSocket incomplet (type/payload)."}},
                        session_id,
                    )
                except Exception:
                    pass
                continue

            # Compat legacy
            if isinstance(message_type, str) and message_type in {"chat:send", "chat_message"}:
                logger.info(f"[WS] Normalisation du type hérité '{message_type}' -> 'chat.message'")
                message_type = "chat.message"

            # ======================
            # DEBATE (non-stream)
            # ======================
            if message_type.startswith("debate:"):
                try:
                    if message_type == "debate:create":
                        topic       = payload.get("topic")
                        agent_order = _norm_list(payload, "agent_order", "agentOrder")
                        rounds      = payload.get("rounds")
                        use_rag     = _norm_bool(payload, "use_rag", "useRag", default=False)
                        if not topic or not isinstance(topic, str):
                            await connection_manager.send_personal_message(
                                {"type": "ws:error", "payload": {"message": "Débat: 'topic' manquant ou invalide."}}, session_id
                            ); continue
                        if not agent_order or not isinstance(agent_order, list) or len(agent_order) < 2:
                            await connection_manager.send_personal_message(
                                {"type": "ws:error", "payload": {"message": "Débat: 'agent_order' ≥ 2 agents requis."}}, session_id
                            ); continue
                        if rounds is None or not isinstance(rounds, int) or rounds < 1:
                            await connection_manager.send_personal_message(
                                {"type": "ws:error", "payload": {"message": "Débat: 'rounds' doit être un entier ≥ 1."}}, session_id
                            ); continue

                        await connection_manager.send_personal_message(
                            {"type": "ws:debate_status_update", "payload": {"status": "Initialisation du débat…", "topic": topic}},
                            session_id
                        )
                        text, cost = await debate_service.run(topic=topic, agent_order=agent_order, rounds=rounds, use_rag=use_rag)
                        await connection_manager.send_personal_message(
                            {"type": "ws:debate_result", "payload": {"topic": topic, "summary": text, "cost": cost}},
                            session_id
                        )
                        continue

                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": f"Type débat inconnu: {message_type}"}}, session_id
                    )
                except Exception as e:
                    logger.error(f"[WS] Erreur débat: {e}", exc_info=True)
                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": f"Erreur débat: {e}"}}, session_id
                    )
                continue

            # ======================
            # CHAT (stream)
            # ======================
            if message_type == "chat.message":
                try:
                    txt = (payload.get("text") or "").strip()
                    ag  = (payload.get("agent_id") or "").strip().lower()
                    use_rag = _norm_bool(payload, "use_rag", "useRag", default=False)
                    if not txt or not ag:
                        await connection_manager.send_personal_message(
                            {"type": "ws:error", "payload": {"message": "chat.message: 'text' et 'agent_id' requis."}},
                            session_id
                        )
                        continue

                    # Dédoublon doux: si le dernier message USER est identique, on ne réinsère pas
                    try:
                        history = connection_manager.session_manager.get_full_history(session_id) or []
                        last = history[-1] if history else None
                        last_role = (last.get("role") if isinstance(last, dict) else getattr(last, "role", None)) if last else None
                        last_text = None
                        if isinstance(last, dict):
                            last_text = last.get("content") or last.get("message")
                        else:
                            last_text = getattr(last, "content", None) or getattr(last, "message", None)
                        already_there = (str(last_role).lower().endswith("user") and (last_text or "").strip() == txt.strip())
                    except Exception:
                        already_there = False

                    if not already_there:
                        # Crée un ChatMessage COMPLET (sinon Pydantic râle)
                        umsg = ChatMessage(
                            id=str(uuid4()),
                            session_id=session_id,
                            role=Role.USER,
                            agent=ag,
                            content=txt,
                            timestamp=datetime.now(timezone.utc).isoformat()
                        )
                        await connection_manager.session_manager.add_message_to_session(session_id, umsg)

                    # Lance la réponse agent (stream WS)
                    chat_service.process_user_message_for_agents(session_id, {"agent_id": ag, "use_rag": use_rag}, connection_manager)

                except Exception as e:
                    logger.error(f"[WS] chat.message erreur: {e}", exc_info=True)
                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": f"chat.message erreur: {e}"}}, session_id
                    )
                continue

            # Inconnu → erreur douce
            await connection_manager.send_personal_message(
                {"type": "ws:error", "payload": {"message": f"Type inconnu: {message_type}"}}, session_id
            )

    except Exception as e:
        logger.info(f"Fermeture WS session={session_id}: {e}")
    finally:
        try:
            await connection_manager.disconnect(session_id, websocket)
        except Exception:
            pass
