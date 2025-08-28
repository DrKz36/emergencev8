# src/backend/core/websocket.py
# V10.3 - FIX: Echo du sous-protocole lors de l'accept WebSocket + gestion robuste des déconnexions.
import logging
import asyncio
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from typing import Dict, Any, List

from .session_manager import SessionManager

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Gère les connexions WebSocket actives.
    V10.3:
      - Echo du sous-protocole ('jwt' ou 'bearer') si demandé par le client.
      - Bloc try/except pour gérer les déconnexions instantanées et éviter les connexions zombies.
    """
    def __init__(self, session_manager: SessionManager):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.session_manager = session_manager
        # ⇩⇩⇩ EXPOSE LE MANAGER DANS LA SESSION ⇩⇩⇩
        try:
            setattr(self.session_manager, "connection_manager", self)
        except Exception as e:
            logger.warning(f"Impossible d'exposer ConnectionManager dans SessionManager: {e}")
        logger.info("ConnectionManager V10.3 (Connexion Blindée + Subprotocol Echo) initialisé.")

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str = "default_user"):
        # Echo du sous-protocole si présent dans la demande (ex: "jwt,<JWT>")
        requested = None
        try:
            requested = websocket.headers.get("sec-websocket-protocol")
        except Exception:
            requested = None

        selected = None
        if requested:
            # Le client envoie typiquement: "jwt,<JWT>" (sans espaces). On renvoie "jwt".
            try:
                for p in [s.strip().lower() for s in requested.split(",") if s.strip()]:
                    if p in {"jwt", "bearer"}:
                        selected = p  # on renvoie exactement un sous-protocole proposé
                        break
            except Exception as e:
                logger.warning(f"Parsing sec-websocket-protocol échoué: {e}")

        await websocket.accept(subprotocol=selected)
        if selected:
            logger.info(f"WebSocket accepté avec sous-protocole: {selected}")
        else:
            logger.info("WebSocket accepté sans sous-protocole (aucune proposition compatible).")

        is_new_session = session_id not in self.active_connections
        if is_new_session:
            self.active_connections[session_id] = []
            self.session_manager.create_session(session_id=session_id, user_id=user_id)
            logger.info(f"Client connecté. Session ID {session_id} créée et associée.")
        else:
            logger.info(f"Nouveau client connecté pour la session existante {session_id}.")

        self.active_connections[session_id].append(websocket)

        # Gestion des déconnexions immédiates
        try:
            await websocket.send_json({
                "type": "ws:session_established",
                "payload": {"session_id": session_id}
            })
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.warning(f"Client déconnecté IMMÉDIATEMENT après la connexion (session {session_id}). Nettoyage... Erreur: {e}")
            await self.disconnect(session_id, websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections and websocket in self.active_connections[session_id]:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                await self.session_manager.finalize_session(session_id)
                logger.info(f"Dernier client déconnecté. Session {session_id} finalisée et archivée.")
            else:
                logger.info(f"Un client s'est déconnecté, mais {len(self.active_connections[session_id])} connexion(s) reste(nt) pour la session {session_id}.")
        else:
            logger.warning(f"Tentative de déconnexion pour une connexion/session déjà nettoyée : {session_id}")

    async def send_personal_message(self, message: dict, session_id: str):
        connections = self.active_connections.get(session_id, [])
        if not connections:
            logger.warning(f"Aucune connexion active trouvée pour la session {session_id} pour envoyer le message.")
            return

        for ws in list(connections):
            try:
                await ws.send_json(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.error(f"Erreur d'envoi au client {session_id} (nettoyage): {e}")
                await self.disconnect(session_id, ws)
