# src/backend/features/chat/router.py
# V23.5 — Remove duplicate ws:debate_result (service emits) + minor cleanup

import logging
from uuid import uuid4
from datetime import datetime, timezone
from json import JSONDecodeError

from fastapi import APIRouter, WebSocket, Depends
from dependency_injector.wiring import inject, Provide
from starlette.websockets import WebSocketDisconnect

from backend.shared.models import ChatMessage, Role
from backend.shared import dependencies as deps
from backend.core.websocket import ConnectionManager
from backend.containers import ServiceContainer

from .service import ChatService
from backend.features.debate.service import DebateService

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------
# Helpers normalisation
# ---------------------------
def _norm_bool(payload, snake_key, camel_key, default=False):
    if snake_key in payload:
        return bool(payload.get(snake_key))
    if camel_key in payload:
        return bool(payload.get(camel_key))
    return default

def _norm_list(payload, snake_key, camel_key):
    val = payload.get(snake_key)
    if val is None:
        val = payload.get(camel_key)
    return val


def _norm_doc_ids(payload, snake_key="doc_ids", camel_key="docIds") -> list[str]:
    raw = _norm_list(payload, snake_key, camel_key)
    if raw is None:
        return []
    if isinstance(raw, (set, tuple)):
        raw = list(raw)
    elif isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []

    doc_ids: list[str] = []
    for item in raw:
        if item is None:
            continue
        try:
            num = int(str(item).strip())
            doc_ids.append(str(num))
        except (ValueError, TypeError):
            text = str(item).strip()
            if text:
                doc_ids.append(text)
    # Déduplication en conservant l'ordre
    seen = set()
    ordered: list[str] = []
    for _id in doc_ids:
        if _id in seen:
            continue
        seen.add(_id)
        ordered.append(_id)
    return ordered

def _norm_type(t: str) -> str:
    t = (t or "").strip()
    return t.replace(".", ":", 1) if t.startswith("debate.") else t

# ---------------------------
# Core WS — SANS Depends / SANS @inject
# (les endpoints résolvent les deps et les passent ici)
# ---------------------------
async def _ws_core(
    websocket: WebSocket,
    session_id: str,
    connection_manager: ConnectionManager,
    chat_service: ChatService,
    debate_service: DebateService,
):
    """Boucle WS commune. Les deps sont déjà résolues par les endpoints."""
    thread_id = None
    try:
        thread_id = websocket.query_params.get('thread_id')
    except Exception:
        thread_id = None
    _uid = None
    try:
        tok = deps._extract_ws_bearer_token(websocket)
        if tok:
            claims = deps._read_bearer_claims_from_token(tok)
            deps._enforce_allowlist_claims(claims)
            _uid = str(claims.get('sub') or '')
    except Exception as e:
        logger.info(f"WS auth tentative échouée: {e}")

    await connection_manager.connect(
        websocket,
        session_id,
        _uid or f"guest:{session_id}",
        thread_id=thread_id,
    )
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
            try:
                data = await websocket.receive_json()
            except (JSONDecodeError, WebSocketDisconnect):
                logger.info(f"[WS] JSON/Disconnect lors de receive_json() — fermeture propre (session={session_id})")
                break

            logger.info(f"---[RAW WS MSG RECEIVED]---: {data}")

            message_type = _norm_type(data.get("type"))
            payload = data.get("payload")

            if not message_type or payload is None:
                await connection_manager.send_personal_message(
                    {"type": "ws:error", "payload": {"message": "Message WebSocket incomplet (type/payload)."}},
                    session_id
                )
                continue

            # Compat anciens noms
            if isinstance(message_type, str) and message_type in {"chat:send", "chat_message"}:
                logger.info(f"[WS] Normalisation du type hérité '{message_type}' -> 'chat.message'")
                message_type = "chat.message"

            # -------- Débat
            if message_type.startswith("debate:"):
                try:
                    if message_type == "debate:create":
                        topic       = payload.get("topic")
                        agent_order = _norm_list(payload, "agent_order", "agentOrder")
                        rounds      = payload.get("rounds")
                        use_rag     = _norm_bool(payload, "use_rag", "useRag", default=False)
                        doc_ids     = _norm_doc_ids(payload)

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

                        # Info statut initial
                        await connection_manager.send_personal_message(
                            {"type": "ws:debate_status_update", "payload": {"status": "Initialisation du débat…", "topic": topic}},
                            session_id
                        )

                        # Orchestration — le service émet déjà ws:debate_started/turn_update/result/ended
                        await debate_service.run(
                            session_id=session_id,
                            topic=topic,
                            agent_order=agent_order,
                            rounds=rounds,
                            use_rag=use_rag,
                            doc_ids=doc_ids,
                        )

                        # Pas de ré-émission ici (évite les doublons ws:debate_result).
                        continue

                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": f"Type débat inconnu: {message_type}"}},
                        session_id
                    )
                except Exception as e:
                    logger.error(f"[WS] Erreur débat: {e}", exc_info=True)
                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": f"Erreur débat: {e}"}}, session_id
                    )
                continue

            # -------- Chat
            if message_type == "chat.message":
                try:
                    txt = (payload.get("text") or "").strip()
                    ag  = (payload.get("agent_id") or "").strip().lower()
                    use_rag = _norm_bool(payload, "use_rag", "useRag", default=False)
                    doc_ids = _norm_doc_ids(payload)

                    if not txt or not ag:
                        await connection_manager.send_personal_message(
                            {"type": "ws:error", "payload": {"message": "chat.message: 'text' et 'agent_id' requis."}},
                            session_id
                        )
                        continue

                    # Anti-duplicate (si dernier message user == txt)
                    try:
                        history = connection_manager.session_manager.get_full_history(session_id) or []
                        last = history[-1] if history else None
                        last_role = (last.get("role") if isinstance(last, dict) else getattr(last, "role", None)) if last else None
                        if isinstance(last, dict):
                            last_text = last.get("content") or last.get("message")
                            last_doc_ids_raw = last.get("doc_ids")
                        else:
                            last_text = getattr(last, "content", None) or getattr(last, "message", None)
                            last_doc_ids_raw = getattr(last, "doc_ids", None)
                        already_there = (str(last_role).lower().endswith("user") and (last_text or "").strip() == txt.strip())
                        if already_there:
                            try:
                                last_doc_ids = {str(int(str(x).strip())) for x in (last_doc_ids_raw or []) if x not in (None, "")}
                                current_doc_ids = {str(int(x)) for x in doc_ids}
                                if last_doc_ids != current_doc_ids:
                                    already_there = False
                            except Exception:
                                already_there = False
                    except Exception:
                        already_there = False

                    if not already_there:
                        umsg = ChatMessage(
                            id=str(uuid4()),
                            session_id=session_id,
                            role=Role.USER,
                            agent=ag,
                            content=txt,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            use_rag=use_rag,
                            doc_ids=doc_ids,
                        )
                        await connection_manager.session_manager.add_message_to_session(session_id, umsg)

                    chat_service.process_user_message_for_agents(
                        session_id,
                        {"agent_id": ag, "use_rag": use_rag, "doc_ids": doc_ids},
                        connection_manager,
                    )

                except Exception as e:
                    logger.error(f"[WS] chat.message erreur: {e}", exc_info=True)
                    await connection_manager.send_personal_message(
                        {"type": "ws:error", "payload": {"message": f"chat.message erreur: {e}"}}, session_id
                    )
                continue

            # -------- Inconnu
            await connection_manager.send_personal_message(
                {"type": "ws:error", "payload": {"message": f"Type inconnu: {message_type}"}},
                session_id
            )

    except Exception as e:
        logger.info(f"Fermeture WS session={session_id}: {e}")
    finally:
        try:
            await connection_manager.disconnect(session_id, websocket)
        except Exception:
            pass

# ---------------------------
# Endpoints WS (DI ici UNIQUEMENT)
# ---------------------------
@router.websocket("/ws/{session_id}")
@inject
async def websocket_with_session(
    websocket: WebSocket,
    session_id: str,
    connection_manager: ConnectionManager = Depends(Provide[ServiceContainer.connection_manager]),
    chat_service: ChatService = Depends(Provide[ServiceContainer.chat_service]),
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service]),
):
    await _ws_core(
        websocket=websocket,
        session_id=session_id,
        connection_manager=connection_manager,
        chat_service=chat_service,
        debate_service=debate_service,
    )

@router.websocket("/ws")
@inject
async def websocket_without_session(
    websocket: WebSocket,
    connection_manager: ConnectionManager = Depends(Provide[ServiceContainer.connection_manager]),
    chat_service: ChatService = Depends(Provide[ServiceContainer.chat_service]),
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service]),
):
    await _ws_core(
        websocket=websocket,
        session_id=uuid4().hex,
        connection_manager=connection_manager,
        chat_service=chat_service,
        debate_service=debate_service,
    )
