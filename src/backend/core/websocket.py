# src/backend/core/websocket.py
# V11.3 – Heartbeat (ws:pong) + Guard client_state + imports datetime/timezone
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from .session_manager import SessionManager
from backend.shared import dependencies  # auth WS (allowlist + sub=uid)

if TYPE_CHECKING:
    from backend.containers import ServiceContainer  # pragma: no cover

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self, session_manager: SessionManager):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.session_manager = session_manager
        try:
            setattr(self.session_manager, "connection_manager", self)
        except Exception as e:
            logger.warning(f"Impossible d'exposer ConnectionManager dans SessionManager: {e}")
        logger.info("ConnectionManager initialisé.")

    async def _accept_with_subprotocol(self, websocket: WebSocket) -> Optional[str]:
        requested = None
        try:
            requested = websocket.headers.get("sec-websocket-protocol")
        except Exception:
            requested = None

        selected = None
        if requested:
            try:
                for p in [s.strip().lower() for s in requested.split(",") if s.strip()]:
                    if p in {"jwt", "bearer"}:
                        selected = p
                        break
            except Exception as e:
                logger.warning(f"Parsing sec-websocket-protocol échoué: {e}")

        await websocket.accept(subprotocol=selected)
        if selected:
            logger.info(f"WebSocket accepté avec sous-protocole: {selected}")
        else:
            logger.info("WebSocket accepté sans sous-protocole compatible.")
        return selected

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str = "default_user"):
        await self._accept_with_subprotocol(websocket)

        is_new_session = session_id not in self.active_connections
        if is_new_session:
            self.active_connections[session_id] = []
            self.session_manager.create_session(session_id=session_id, user_id=user_id)
            logger.info(f"Client connecté. Session {session_id} créée et associée.")
        else:
            logger.info(f"Nouveau client connecté pour la session existante {session_id}.")

        self.active_connections[session_id].append(websocket)

        # Guard: si le client ferme immédiatement, éviter l’exception
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    "type": "ws:session_established",
                    "payload": {"session_id": session_id}
                })
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.warning(f"Client déconnecté immédiatement (session {session_id}). Nettoyage... Erreur: {e}")
            await self.disconnect(session_id, websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket):
        conns = self.active_connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
            try:
                await self.session_manager.finalize_session(session_id)
            except Exception as e:
                logger.warning(f"finalize_session({session_id}) a levé: {e}")
            logger.info(f"Dernier client déconnecté. Session {session_id} finalisée.")
        else:
            logger.info(f"Un client s'est déconnecté, {len(conns)} connexion(s) restante(s) pour {session_id}.")

    async def send_personal_message(self, message: dict, session_id: str):
        connections = self.active_connections.get(session_id, [])
        for ws in list(connections):
            try:
                # ✅ Guard : n'envoie que si CONNECTED
                if getattr(ws, "client_state", None) != WebSocketState.CONNECTED:
                    continue
                await ws.send_json(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.error(f"Erreur d'envoi (session {session_id}) → cleanup: {e}")
                await self.disconnect(session_id, ws)

def _find_handler(sm: SessionManager) -> Optional[Callable[..., Any]]:
    for name in ("on_client_message", "ingest_ws_message", "handle_client_message", "dispatch"):
        fn = getattr(sm, name, None)
        if callable(fn):
            return fn
    return None

def get_websocket_router(container) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        user_id_hint = websocket.query_params.get("user_id")
        try:
            user_id = await dependencies.get_user_id_for_ws(websocket, user_id=user_id_hint)
        except Exception as e:
            logger.warning(f"Refus WS (auth échouée) : {e}")
            return  # handshake refusé

        session_manager: SessionManager = container.session_manager()
        conn_manager = getattr(session_manager, "connection_manager", None)
        if conn_manager is None:
            conn_manager = ConnectionManager(session_manager)

        await conn_manager.connect(websocket, session_id, user_id=user_id)

        handler = _find_handler(session_manager)
        try:
            while True:
                data = await websocket.receive_json()

                # ======================
                # HEARTBEAT (ping/pong)
                # ======================
                try:
                    msg_type = (data.get("type") or "").strip().lower()
                    if msg_type in {"ws:ping", "ping"}:
                        await conn_manager.send_personal_message(
                            {"type": "ws:pong", "payload": {"ts": datetime.now(timezone.utc).isoformat()}},
                            session_id,
                        )
                        continue
                except Exception as e:
                    logger.warning(f"WS ping/pong échec: {e}")

                if handler:
                    try:
                        res = handler(session_id, data)
                        if asyncio.iscoroutine(res):
                            await res
                    except TypeError:
                        res = handler(data, session_id)
                        if asyncio.iscoroutine(res):
                            await res
                else:
                    await conn_manager.send_personal_message(
                        {"type": "ws:ack", "payload": {"received": True, "echo": data}},
                        session_id,
                    )
        except WebSocketDisconnect:
            await conn_manager.disconnect(session_id, websocket)
        except RuntimeError as e:
            logger.error(f"WS RuntimeError session={session_id}: {e}")
            await conn_manager.disconnect(session_id, websocket)
        except Exception as e:
            logger.error(f"WS Exception session={session_id}: {e}")
            await conn_manager.disconnect(session_id, websocket)

    return router
