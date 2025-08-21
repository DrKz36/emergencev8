# src/backend/core/websocket.py
# V11.1 - Handshake WS avec user_id fiable:
#   - Lit ?token=... (ou Authorization) et vérifie l'ID token Google quand possible
#   - Extrait sub/email -> force user_id=sub (fallback: query user_id / 'default_user')
#   - Compatible DEV (AUTH_DEV_MODE=1) et existant V10.2 (déconnexions blindées)

from __future__ import annotations

import os
import json
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from .session_manager import SessionManager

logger = logging.getLogger(__name__)

# Vérification Google ID token (optionnelle)
_GOOGLE_VERIFY_AVAILABLE = True
try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
except Exception:  # lib absente/imprévue
    _GOOGLE_VERIFY_AVAILABLE = False
    logger.warning("google-auth indisponible — vérification ID token désactivée (fallback decode).")


def _b64url_json(token_part: str) -> Dict[str, Any]:
    """Decode base64url JSON (sans vérif crypto)."""
    try:
        padded = token_part + '=' * (-len(token_part) % 4)
        raw = base64.urlsafe_b64decode(padded.encode('utf-8'))
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return {}


def _parse_jwt_noverify(token: str) -> Dict[str, Any]:
    try:
        parts = (token or '').split('.')
        return _b64url_json(parts[1]) if len(parts) >= 2 else {}
    except Exception:
        return {}


def _extract_token_from_ws(websocket: WebSocket) -> Optional[str]:
    # 1) query ?token=...
    try:
        q = websocket.query_params
        if q and "token" in q:
            return q.get("token")
    except Exception:
        pass
    # 2) header Authorization: Bearer ...
    try:
        auth = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
    except Exception:
        pass
    return None


def _extract_uid_email_from_token(token: str) -> Tuple[Optional[str], Optional[str]]:
    """Retourne (sub, email) depuis un ID token Google. Vérifie si possible, sinon decode léger."""
    if not token:
        return (None, None)

    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("EMERGENCE_GOOGLE_CLIENT_ID")
    if _GOOGLE_VERIFY_AVAILABLE and client_id:
        try:
            req = google_requests.Request()
            claims = google_id_token.verify_oauth2_token(token, req, audience=client_id)
            sub = str(claims.get("sub") or "")
            email = claims.get("email")
            if sub:
                return (sub, email)
        except Exception as e:
            logger.warning(f"[WS] Vérification ID token échouée (client_id='{client_id}'): {e}. Fallback decode.")
    # Fallback: decode sans vérification (DEV / dégradé)
    claims = _parse_jwt_noverify(token)
    sub = str(claims.get("sub") or claims.get("user_id") or "") or None
    email = claims.get("email")
    return (sub, email)


class ConnectionManager:
    """
    Gère les connexions WebSocket actives.
    V11.1: Bind user_id via ID token (Google) au handshake + robustesse déconnexions.
    """
    def __init__(self, session_manager: SessionManager):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.session_manager = session_manager
        logger.info("ConnectionManager V11.1 (Handshake ID token) initialisé.")

    async def connect(self, websocket: WebSocket, session_id: str, user_id: str = "default_user"):
        await websocket.accept()

        # --- Résolution user_id fiable ---
        auth_dev = (os.getenv("AUTH_DEV_MODE", "0") == "1")
        qp_user = None
        try:
            qp_user = websocket.query_params.get("user_id")
        except Exception:
            pass

        token = _extract_token_from_ws(websocket)
        sub, email = (None, None)
        if token and not auth_dev:
            sub, email = _extract_uid_email_from_token(token)

        actual_user_id = sub or qp_user or (user_id or "default_user")
        if not actual_user_id:
            actual_user_id = "default_user"

        # --- Nouvelle ou existante ---
        is_new_session = session_id not in self.active_connections
        if is_new_session:
            self.active_connections[session_id] = []
            # Crée la session avec le user_id déterminé (persistée/seed DB en tâche asynchrone)
            self.session_manager.create_session(session_id=session_id, user_id=actual_user_id)
            logger.info(f"[WS] Session {session_id} créée pour user_id='{actual_user_id}' (email={email or '-'})")
        else:
            # Si la session existe mais avec un mauvais user, on tente une correction douce.
            s = self.session_manager.get_session(session_id)
            if s and s.user_id != actual_user_id:
                try:
                    s.user_id = actual_user_id
                    # Upsert immédiat pour éviter la dérive
                    await self.session_manager.db_manager.save_session(s)  # type: ignore[attr-defined]
                    logger.info(f"[WS] Session {session_id}: user_id corrigé -> '{actual_user_id}'")
                except Exception as e:
                    logger.warning(f"[WS] Impossible d'updater user_id session {session_id}: {e}")

        self.active_connections[session_id].append(websocket)

        # Envoi d'accusé - blindé contre déconnexions instantanées (hérité V10.2)
        try:
            await websocket.send_json({
                "type": "ws:session_established",
                "payload": {"session_id": session_id, "user_id": actual_user_id}
            })
        except (WebSocketDisconnect, RuntimeError) as e:
            logger.warning(f"Client déconnecté IMMÉDIATEMENT (session {session_id}). Nettoyage… Erreur: {e}")
            await self.disconnect(session_id, websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections and websocket in self.active_connections[session_id]:
            self.active_connections[session_id].remove(websocket)

            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                await self.session_manager.finalize_session(session_id)
                logger.info(f"Dernier client déconnecté. Session {session_id} finalisée et archivée.")
            else:
                logger.info(f"Un client s'est déconnecté, {len(self.active_connections[session_id])} connexion(s) restante(s) pour {session_id}.")
        else:
            logger.warning(f"Tentative de déconnexion pour une connexion/session déjà nettoyée : {session_id}")

    async def send_personal_message(self, message: dict, session_id: str):
        connections = self.active_connections.get(session_id, [])
        if not connections:
            logger.warning(f"Aucune connexion active pour la session {session_id} (envoi ignoré).")
            return

        for ws in list(connections):
            try:
                await ws.send_json(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.error(f"Erreur d'envoi au client {session_id} (nettoyage): {e}")
                await self.disconnect(session_id, ws)
