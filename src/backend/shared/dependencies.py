# src/backend/shared/dependencies.py
# V7.0 - DI unifiée + garde Bearer + Mémoire (gardener)
import logging
from typing import Optional

from fastapi import Request, WebSocket, HTTPException, status, Header, Query

from backend.core.database.manager import DatabaseManager
from backend.core.session_manager import SessionManager
from backend.core.cost_tracker import CostTracker
from backend.core.websocket import ConnectionManager
from backend.shared.config import Settings
from backend.core import config

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
    # On réutilise le VectorService déjà attaché au ChatService si disponible.
    try:
        cs = _container(request).chat_service()
        vs = getattr(cs, "vector_service", None)
        if vs is not None:
            return vs
    except Exception:
        pass
    # Sinon créer un singleton sur app.state
    vs = getattr(request.app.state, "_vector_service", None)
    if vs is None:
        persist_dir = getattr(config, "VECTOR_STORE_DIR", "src/backend/data/vector_store")
        embed_model = getattr(config, "EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
        vs = VectorService(persist_directory=persist_dir, embed_model_name=embed_model)
        request.app.state._vector_service = vs
    return vs

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
    chat_service = container.chat_service()
    vector_service = getattr(chat_service, "vector_service", None) or get_vector_service(request)

    # Singleton sur app.state
    gard = getattr(request.app.state, "_memory_gardener", None)
    if gard is None:
        analyzer = MemoryAnalyzer(db_manager=db, chat_service=chat_service)
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
