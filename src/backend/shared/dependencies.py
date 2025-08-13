# src/backend/shared/dependencies.py
# V5.0 - Refonte de la base de données
import logging
from typing import Optional

from fastapi import Request, WebSocket, HTTPException, status, Query

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
