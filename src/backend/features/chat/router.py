# src/backend/features/chat/router.py
# V23.5 â€” Remove duplicate ws:debate_result (service emits) + minor cleanup

import logging
from uuid import uuid4
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, WebSocket, Depends, HTTPException
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


def _norm_doc_ids(
    payload: dict[str, Any], snake_key: str = "doc_ids", camel_key: str = "docIds"
) -> list[str]:
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
    # DÃ©duplication en conservant l'ordre
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


def _history_has_opinion_request(
    history: list[Any], *, target_agent: str, source_agent: str | None, message_id: str
) -> bool:
    target = (target_agent or "").strip().lower()
    source = (source_agent or "").strip().lower() if source_agent else ""
    message = (message_id or "").strip()
    if not target or not message:
        return False

    request_ids: set[str] = set()
    note_found = False
    responses: list[dict[str, str]] = []

    for item in history or []:
        if not item:
            continue
        if isinstance(item, dict):
            role = item.get("role")
            meta = item.get("meta") or item.get("metadata")
        else:
            role = getattr(item, "role", None)
            meta = getattr(item, "meta", None)
            if meta is None:
                meta = getattr(item, "metadata", None)
        if not isinstance(meta, dict):
            continue

        role_str = str(role or "").lower()
        if role_str.endswith("user"):
            opinion_req = meta.get("opinion_request") or meta.get("opinion-request")
            if not isinstance(opinion_req, dict):
                continue
            req_target = (
                str(
                    opinion_req.get("target_agent")
                    or opinion_req.get("target_agent_id")
                    or ""
                )
                .strip()
                .lower()
            )
            if req_target != target:
                continue
            req_source = (
                str(
                    opinion_req.get("source_agent")
                    or opinion_req.get("source_agent_id")
                    or ""
                )
                .strip()
                .lower()
            )
            if source and req_source and req_source != source:
                continue
            req_message = str(
                opinion_req.get("requested_message_id")
                or opinion_req.get("message_id")
                or opinion_req.get("of_message_id")
                or ""
            ).strip()
            if req_message and req_message != message:
                continue
            note_found = True
            req_id = str(
                opinion_req.get("request_id")
                or opinion_req.get("request_note_id")
                or opinion_req.get("note_id")
                or opinion_req.get("id")
                or ""
            ).strip()
            if req_id:
                request_ids.add(req_id)
        elif role_str.endswith("assistant"):
            opinion_meta = meta.get("opinion") or meta.get("opinion_meta")
            if not isinstance(opinion_meta, dict):
                continue
            responses.append(
                {
                    "reviewer": str(
                        opinion_meta.get("reviewer_agent_id")
                        or opinion_meta.get("reviewer_agent")
                        or opinion_meta.get("agent_id")
                        or ""
                    )
                    .strip()
                    .lower(),
                    "source": str(
                        opinion_meta.get("source_agent_id")
                        or opinion_meta.get("source_agent")
                        or ""
                    )
                    .strip()
                    .lower(),
                    "message": str(
                        opinion_meta.get("of_message_id")
                        or opinion_meta.get("of_message")
                        or opinion_meta.get("message_id")
                        or ""
                    ).strip(),
                    "note": str(
                        opinion_meta.get("request_note_id")
                        or opinion_meta.get("request_id")
                        or opinion_meta.get("note_id")
                        or ""
                    ).strip(),
                }
            )

    if not note_found:
        return False

    for response in responses:
        reviewer = response["reviewer"]
        if reviewer and reviewer != target:
            continue
        src_meta = response["source"]
        if source and src_meta and src_meta != source:
            continue
        related_msg = response["message"]
        if related_msg and related_msg != message:
            continue
        req_note = response["note"]
        if request_ids:
            if req_note and req_note in request_ids:
                return True
            if not req_note:
                return True
        else:
            return True

    return False


# ---------------------------
# Handlers
# ---------------------------
async def _handle_debate_create(
    session_id: str,
    payload: dict[str, Any],
    debate_service: DebateService,
    connection_manager: ConnectionManager,
) -> None:
    topic = payload.get("topic")
    agent_order = _norm_list(payload, "agent_order", "agentOrder")
    rounds = payload.get("rounds")
    use_rag = _norm_bool(payload, "use_rag", "useRag", default=False)
    doc_ids = _norm_doc_ids(payload)

    if not topic or not isinstance(topic, str):
        await connection_manager.send_personal_message(
            {"type": "ws:error", "payload": {"message": "Débat: 'topic' manquant ou invalide."}},
            session_id,
        )
        return
    if not agent_order or not isinstance(agent_order, list) or len(agent_order) < 2:
        await connection_manager.send_personal_message(
            {"type": "ws:error", "payload": {"message": "Débat: 'agent_order' ≥ 2 agents requis."}},
            session_id,
        )
        return
    if rounds is None or not isinstance(rounds, int) or rounds < 1:
        await connection_manager.send_personal_message(
            {"type": "ws:error", "payload": {"message": "Débat: 'rounds' doit être un entier ≥ 1."}},
            session_id,
        )
        return

    # Info statut initial
    await connection_manager.send_personal_message(
        {
            "type": "ws:debate_status_update",
            "payload": {
                "stage": "starting",
                "status": "starting",
                "message": "Initialisation du debat...",
                "topic": topic,
            },
        },
        session_id,
    )

    await debate_service.run(
        session_id=session_id,
        topic=topic,
        agent_order=agent_order,
        rounds=rounds,
        use_rag=use_rag,
        doc_ids=doc_ids,
    )


async def _handle_chat_message(
    session_id: str,
    payload: dict[str, Any],
    chat_service: ChatService,
    connection_manager: ConnectionManager,
) -> None:
    txt = (payload.get("text") or "").strip()
    ag = (payload.get("agent_id") or "").strip().lower()
    use_rag = _norm_bool(payload, "use_rag", "useRag", default=False)
    doc_ids = _norm_doc_ids(payload)

    if not txt or not ag:
        await connection_manager.send_personal_message(
            {"type": "ws:error", "payload": {"message": "chat.message: 'text' et 'agent_id' requis."}},
            session_id,
        )
        return

    # Anti-duplicate logic
    already_there = False
    try:
        history = connection_manager.session_manager.get_full_history(session_id) or []
        last = history[-1] if history else None
        if last:
            last_role = (
                last.get("role") if isinstance(last, dict) else getattr(last, "role", None)
            )
            if isinstance(last, dict):
                last_text = last.get("content") or last.get("message")
                last_doc_ids_raw = last.get("doc_ids")
            else:
                # mypy thinks this is unreachable but it's not (last can be a Message object)
                last_text = getattr(last, "content", None) or getattr(last, "message", None)  # type: ignore[unreachable]
                last_doc_ids_raw = getattr(last, "doc_ids", None)
            
            if str(last_role).lower().endswith("user") and (last_text or "").strip() == txt.strip():
                try:
                    last_doc_ids = {
                        str(int(str(x).strip()))
                        for x in (last_doc_ids_raw or [])
                        if x not in (None, "")
                    }
                    current_doc_ids = {str(int(x)) for x in doc_ids}
                    if last_doc_ids == current_doc_ids:
                        already_there = True
                except Exception:
                    pass
    except Exception:
        pass

    if not already_there:
        umsg = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            role=Role.USER,
            agent=ag,
            content=txt,
            timestamp=datetime.now(timezone.utc).isoformat(),
            cost=None,
            tokens=None,
            agents=[ag],
            use_rag=use_rag,
            doc_ids=doc_ids,
        )
        await connection_manager.session_manager.add_message_to_session(session_id, umsg)

    chat_service.process_user_message_for_agents(
        session_id,
        {"agent_id": ag, "use_rag": use_rag, "doc_ids": doc_ids},
        connection_manager,
    )


async def _handle_chat_opinion(
    session_id: str,
    payload: dict[str, Any],
    chat_service: ChatService,
    connection_manager: ConnectionManager,
) -> None:
    opinion_payload = payload if isinstance(payload, dict) else {}
    target_agent = str(opinion_payload.get("target_agent_id") or opinion_payload.get("target_agent") or "").strip().lower()
    source_agent = str(opinion_payload.get("source_agent_id") or opinion_payload.get("source_agent") or "").strip().lower()
    message_id = str(opinion_payload.get("message_id") or opinion_payload.get("messageId") or "").strip()
    request_id = str(opinion_payload.get("request_id") or opinion_payload.get("requestId") or opinion_payload.get("note_id") or opinion_payload.get("noteId") or "").strip()
    message_text = opinion_payload.get("message_text") or opinion_payload.get("messageText")

    if not target_agent or not message_id:
        await connection_manager.send_personal_message(
            {"type": "ws:error", "payload": {"message": "chat.opinion: 'target_agent_id' et 'message_id' requis."}},
            session_id,
        )
        return

    already_there = False
    try:
        history = connection_manager.session_manager.get_full_history(session_id) or []
        already_there = _history_has_opinion_request(
            history,
            target_agent=target_agent,
            source_agent=source_agent,
            message_id=message_id,
        )
    except Exception:
        pass

    if already_there:
        logger.info("[WS] chat.opinion ignored (duplicate target=%s message_id=%s)", target_agent, message_id)
        try:
            await connection_manager.send_personal_message(
                {
                    "type": "ws:error",
                    "payload": {
                        "message": "Avis déjà disponible pour cette réponse.",
                        "code": "opinion_already_exists",
                    },
                },
                session_id,
            )
        except Exception:
            pass
        return

    await chat_service.request_opinion(
        session_id=session_id,
        target_agent_id=target_agent,
        source_agent_id=source_agent or None,
        message_id=message_id or None,
        message_text=message_text,
        connection_manager=connection_manager,
        request_id=request_id or None,
    )


# ---------------------------
# Core WS â€” SANS Depends / SANS @inject
# (les endpoints rÃ©solvent les deps et les passent ici)
# ---------------------------
async def _ws_core(
    websocket: WebSocket,
    session_id: str,
    connection_manager: ConnectionManager,
    chat_service: ChatService,
    debate_service: DebateService,
) -> None:
    """Boucle WS commune. Les deps sont dÃ©jÃ  rÃ©solues par les endpoints."""
    thread_id = None
    try:
        thread_id = websocket.query_params.get("thread_id")
    except Exception:
        thread_id = None
    _uid = None
    try:
        _uid = await deps.get_user_id_from_websocket(websocket)
    except HTTPException as exc:
        logger.info(f"WS auth tentative échouée: {getattr(exc, 'detail', exc)}")

    await connection_manager.connect(
        websocket,
        session_id,
        _uid or f"guest:{session_id}",
        thread_id=thread_id,
    )
    if not _uid:
        try:
            await connection_manager.send_personal_message(
                {
                    "type": "ws:auth_required",
                    "payload": {
                        "message": "Authentication required",
                        "reason": "missing_or_invalid_token",
                    },
                },
                session_id,
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
                logger.info(
                    f"[WS] JSON/Disconnect lors de receive_json() — fermeture propre (session={session_id})"
                )
                break

            logger.info(f"---[RAW WS MSG RECEIVED]---: {data}")

            message_type = _norm_type(data.get("type"))
            payload = data.get("payload")

            if not message_type or payload is None:
                await connection_manager.send_personal_message(
                    {
                        "type": "ws:error",
                        "payload": {
                            "message": "Message WebSocket incomplet (type/payload)."
                        },
                    },
                    session_id,
                )
                continue

            # Compat anciens noms
            if isinstance(message_type, str) and message_type in {
                "chat:send",
                "chat_message",
            }:
                logger.info(
                    f"[WS] Normalisation du type hérité '{message_type}' -> 'chat.message'"
                )
                message_type = "chat.message"

            # Dispatch vers les handlers appropriés
            try:
                if message_type == "debate:create":
                    await _handle_debate_create(session_id, payload, debate_service, connection_manager)
                elif message_type == "chat.message":
                    await _handle_chat_message(session_id, payload, chat_service, connection_manager)
                elif message_type == "chat.opinion":
                    await _handle_chat_opinion(session_id, payload, chat_service, connection_manager)
                else:
                    await connection_manager.send_personal_message(
                        {
                            "type": "ws:error",
                            "payload": {"message": f"Type inconnu: {message_type}"},
                        },
                        session_id,
                    )
            except Exception as e:
                logger.error(f"[WS] Erreur handler pour {message_type}: {e}", exc_info=True)
                await connection_manager.send_personal_message(
                    {
                        "type": "ws:error",
                        "payload": {"message": f"Erreur: {e}"},
                    },
                    session_id,
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
    connection_manager: ConnectionManager = Depends(
        Provide[ServiceContainer.connection_manager]
    ),
    chat_service: ChatService = Depends(Provide[ServiceContainer.chat_service]),
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service]),
) -> None:
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
    connection_manager: ConnectionManager = Depends(
        Provide[ServiceContainer.connection_manager]
    ),
    chat_service: ChatService = Depends(Provide[ServiceContainer.chat_service]),
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service]),
) -> None:
    await _ws_core(
        websocket=websocket,
        session_id=uuid4().hex,
        connection_manager=connection_manager,
        chat_service=chat_service,
        debate_service=debate_service,
    )
