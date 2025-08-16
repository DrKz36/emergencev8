# src/backend/shared/dependencies.py
# V6.0 - Ajout require_bearer_or_401 (401 propre si Bearer absent/mal formé)
#        Conserve require_authenticated_user pour compat. Aucun changement d'arbo.
import logging
from typing import Optional

from fastapi import Request, WebSocket, HTTPException, status, Query, Header

# MODIFICATION: Import du nouveau DatabaseManager
from backend.core.database.manager import DatabaseManager
from backend.core.session_manager import SessionManager
from backend.core.cost_tracker import CostTracker
from backend.core.websocket import ConnectionManager
from backend.features.chat.service import ChatService
from backend.features.documents.service import DocumentService
from backend.features.dashboard.service import DashboardService

logger = logging.getLogger(__name__)

class WebSocketException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

def get_service_container_from_request(request: Request):
    container = getattr(request.app.state, 'service_container', None)
    if not container:
        logger.critical("FATAL: ServiceContainer non trouvé dans l'état de l'application (depuis Request).")
        raise HTTPException(status_code=500, detail="Configuration critique manquante: ServiceContainer.")
    return container

def get_service_container_from_websocket(websocket: WebSocket):
    container = getattr(websocket.app.state, 'service_container', None)
    if not container:
        logger.critical("FATAL: ServiceContainer non trouvé dans l'état de l'application (depuis WebSocket).")
        raise RuntimeError("ServiceContainer non trouvé.")
    return container

# --- Dépendances pour les services (Pattern unifié pour HTTP) ---

def get_db(request: Request) -> DatabaseManager:
    return get_service_container_from_request(request).db_manager()

def get_session_manager(request: Request) -> SessionManager:
    return get_service_container_from_request(request).session_manager()

def get_cost_tracker(request: Request) -> CostTracker:
    return get_service_container_from_request(request).cost_tracker()

def get_document_service(request: Request) -> DocumentService:
    return get_service_container_from_request(request).document_service()

def get_dashboard_service(request: Request) -> DashboardService:
    return get_service_container_from_request(request).dashboard_service()

# --- Dépendances pour les services (Pattern unifié pour WebSocket) ---

def get_connection_manager(websocket: WebSocket) -> ConnectionManager:
    return get_service_container_from_websocket(websocket).connection_manager()

def get_chat_service(websocket: WebSocket) -> ChatService:
    return get_service_container_from_websocket(websocket).chat_service()

# --- Dépendances pour les routes spécifiques ---

async def get_user_id(request: Request) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=400, detail="En-tête X-User-ID manquant.")
    return user_id

async def get_user_id_from_websocket(user_id: Optional[str] = Query(None, alias="user_id")) -> str:
    if not user_id:
        logger.warning("Connexion WebSocket rejetée. Raison: Paramètre 'user_id' manquant.")
        raise WebSocketException(
            status_code=status.WS_1008_POLICY_VIOLATION,
            detail="Paramètre 'user_id' manquant dans l'URL de connexion WebSocket."
        )
    logger.info(f"ID utilisateur '{user_id}' extrait avec succès des query params WebSocket.")
    return user_id

# --- NOUVEAU : garde stricte 'Bearer' pour routes HTTP protégées (/api/documents GET) ---

async def require_bearer_or_401(authorization: Optional[str] = Header(default=None)) -> str:
    """
    Renvoie 401 si l'en-tête Authorization n'est pas 'Bearer <token>'.
    Ne valide pas le token, vérifie juste présence/forme pour éviter les 500.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    return parts[1].strip()

# --- Garde existante : X-User-ID OU Bearer (compat) ---

async def require_authenticated_user(request: Request):
    """
    Garde minimale : accepte soit un header 'X-User-ID', soit un 'Authorization: Bearer <token>'.
    - Renvoie 401 si aucune info d'auth valide n'est fournie.
    - NE valide PAS le token ici (la validation reste au service si nécessaire).
    - Évite les 500 en cas de header mal formé.
    """
    # 1) Cas X-User-ID (interop simple)
    x_user = request.headers.get("X-User-ID")
    if x_user and x_user.strip():
        return {"user_id": x_user.strip()}

    # 2) Cas Authorization: Bearer <token>
    auth = request.headers.get("Authorization")
    if not auth:
        raise HTTPException(status_code=401, detail="Not authenticated")

    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        logger.warning("Authorization mal formé ou token manquant.")
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = parts[1].strip()
    return {"token": token}
