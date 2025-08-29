# src/backend/core/websocket.py
# V11.0 – Router WS complet (echo sous-protocole, auth WS via GIS, tolérance SessionManager)
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from .session_manager import SessionManager
from backend.shared import dependencies  # auth WS (allowlist + sub=uid)
from backend.containers import ServiceContainer  # DI container

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Gère les connexions WebSocket actives.
    V10.3+:
      - Echo du sous-protocole ('jwt' ou 'bearer') si demandé par le client.
      - Gestion robuste des déconnexions (zombies évités).
    """
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

        # Annonce session établie
        try:
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
                await ws.send_json(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.error(f"Erreur d'envoi (session {session_id}) → cleanup: {e}")
                await self.disconnect(session_id, ws)

def _find_handler(sm: SessionManager) -> Optional[Callable[..., Any]]:
    """
    Tolérance : on tente plusieurs conventions d'API côté SessionManager.
    """
    for name in ("on_client_message", "ingest_ws_message", "handle_client_message", "dispatch"):
        fn = getattr(sm, name, None)
        if callable(fn):
            return fn
    return None

def get_websocket_router(container: ServiceContainer) -> APIRouter:
    """
    Retourne un APIRouter montant l'endpoint WS officiel:
    - GET /ws/{session_id} (upgrade)
    - Auth: Google ID token via sous-protocole 'jwt' (ou cookie/query) → user_id = 'sub'
    """
    router = APIRouter()

    @router.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        # 1) Auth WS (GIS ID token, allowlist, DEV fallback user_id=?)
        user_id_hint = websocket.query_params.get("user_id")
        try:
            user_id = await dependencies.get_user_id_for_ws(websocket, user_id=user_id_hint)
        except Exception as e:
            # Refus propre (aucun accept() préalable)
            logger.warning(f"Refus WS (auth échouée) : {e}")
            # Starlette/fastapi exige accept() avant close() parfois; mais on évite pour 401 handshake
            return

        # 2) Managers
        session_manager: SessionManager = container.session_manager()
        conn_manager = getattr(session_manager, "connection_manager", None)
        if conn_manager is None:
            conn_manager = ConnectionManager(session_manager)

        # 3) Ouverture
        await conn_manager.connect(websocket, session_id, user_id=user_id)

        # 4) Boucle de réception
        handler = _find_handler(session_manager)
        try:
            while True:
                data = await websocket.receive_json()
                # Acheminer si un handler existe, sinon echo ack
                if handler:
                    try:
                        res = handler(session_id, data)  # sync ?
                        if asyncio.iscoroutine(res):
                            await res
                    except TypeError:
                        # Certaines signatures attendent (data, session_id)
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
