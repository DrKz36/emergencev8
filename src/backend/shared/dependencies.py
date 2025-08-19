# src/backend/shared/dependencies.py
# V7.1 - DI unifiée : plus de fallback config; vector_service/analyzer issus du container; garde Bearer + WS.
import logging
from typing import Optional

from fastapi import Request, WebSocket, HTTPException, status, Header, Query

from backend.core.database.manager import DatabaseManager
from backend.core.session_manager import SessionManager
from backend.core.cost_tracker import CostTracker
from backend.core.websocket import ConnectionManager
from backend.shared.config import Settings

from backend.features.chat.service import ChatService
from backend.features.documents.service import DocumentService
from backend.features.dashboard.service import DashboardService

from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.memory.gardener import MemoryGardener

logger = logging.getLogger(__name__)

# --- Accès au container -------------------------------------------------------
def _container(request: Request):
    c = getattr(request.app.state, "service_container", None)
    if c is None:
        raise RuntimeError("ServiceContainer introuvable sur app.state.")
    return c

# --- Factories de services partagés ------------------------------------------
def get_db_manager(request: Request) -> DatabaseManager:
    return _container(request).db_manager()

def get_session_manager(request: Request) -> SessionManager:
    return _container(request).session_manager()

def get_cost_tracker(request: Request) -> CostTracker:
    return _container(request).cost_tracker()

def get_connection_manager(request: Request) -> ConnectionManager:
    return _container(request).connection_manager()

def get_settings(request: Request) -> Settings:
    return _container(request).settings()

def get_vector_service(request: Request) -> VectorService:
    # Source de vérité unique : container.vector_service()
    return _container(request).vector_service()

def get_chat_service(request: Request) -> ChatService:
    return _container(request).chat_service()

def get_document_service(request: Request) -> DocumentService:
    return _container(request).document_service()

def get_dashboard_service(request: Request) -> DashboardService:
    return _container(request).dashboard_service()

# --- Mémoire : MemoryGardener -------------------------------------------------
def get_memory_gardener(request: Request) -> MemoryGardener:
    container = _container(request)
    db = container.db_manager()
    vector_service = container.vector_service()
    analyzer: MemoryAnalyzer = container.memory_analyzer()

    # Injection tardive si nécessaire (sécurisé)
    if getattr(analyzer, "chat_service", None) is None:
        try:
            analyzer.set_chat_service(container.chat_service())
        except Exception:
            pass

    # Singleton app.state
    gard = getattr(request.app.state, "_memory_gardener", None)
    if gard is None:
        gard = MemoryGardener(db_manager=db, vector_service=vector_service, memory_analyzer=analyzer)
        request.app.state._memory_gardener = gard
        logger.info("MemoryGardener initialisé (singleton app.state).")
    return gard

# --- Garde WebSocket: user_id obligatoire ------------------------------------
async def get_user_id_from_websocket(
    websocket: WebSocket,
    user_id: Optional[str] = Query(default=None)
) -> str:
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.WS_1008_POLICY_VIOLATION,
            detail="Paramètre 'user_id' manquant dans l'URL de connexion WebSocket."
        )
    logger.info(f"user_id extrait (WS): {user_id}")
    return user_id

# --- Garde HTTP: Authorization: Bearer <token> obligatoire -------------------
async def require_bearer_or_401(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed Authorization header.")
    return parts[1]
