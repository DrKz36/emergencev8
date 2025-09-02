# src/backend/containers.py
# V5.8 — DI alignée :
#    - DocumentService(db_manager, parser_factory, vector_service, uploads_dir) ✅
#    - Plus d’injection 'cost_tracker' dans DocumentService ❌
#    - VectorService(persist_directory, embed_model_name) ✅
#    - Helpers robustes _get_db_path/_get_vector_dir/_get_embed_model_name/_get_uploads_dir ✅
#    - DebateService présent (déjà utilisé par WS) ✅
#    - Alias ServiceContainer ✅

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dependency_injector import containers, providers

# --- Services principaux ---
from backend.shared.config import Settings
from backend.core.database.manager import DatabaseManager
from backend.core.cost_tracker import CostTracker
from backend.core.session_manager import SessionManager
from backend.core.websocket import ConnectionManager

from backend.features.memory.vector_service import VectorService  # persist_directory + embed_model_name
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.chat.service import ChatService

# --- Features optionnelles (tolérance à l’absence) ---
try:
    from backend.features.dashboard.service import DashboardService  # type: ignore
except Exception:  # pragma: no cover
    DashboardService = None  # type: ignore

try:
    from backend.features.documents.service import DocumentService  # type: ignore
    from backend.features.documents.parser import ParserFactory  # requis par DocumentService
except Exception:  # pragma: no cover
    DocumentService = None  # type: ignore
    ParserFactory = None    # type: ignore

try:
    from backend.features.debate.service import DebateService  # type: ignore
except Exception:  # pragma: no cover
    DebateService = None  # type: ignore

# ----------------------------
# Helpers chemins / options
# ----------------------------
def _get_db_path(settings: Settings) -> str:
    """
    Préfère settings.db.path, tolère db.PATH/URL/url, sinon EMERGENCE_DB_PATH, défaut ./data/emergence.db
    Retour absolu.
    """
    cand: Optional[str] = None
    try:
        db = getattr(settings, "db", None)
        for key in ("path", "PATH", "url", "URL"):
            val = getattr(db, key, None) if db is not None else None
            if isinstance(val, str) and val.strip():
                cand = val.strip()
                break
    except Exception:
        cand = None
    if not cand:
        cand = os.getenv("EMERGENCE_DB_PATH")
    if not cand:
        cand = "./data/emergence.db"
    return str(Path(cand).resolve())

def _get_vector_dir(settings: Settings) -> str:
    """
    Préfère settings.vector.persist_directory, sinon EMERGENCE_VECTOR_DIR, défaut ./data/vector_store
    """
    cand: Optional[str] = None
    try:
        vec = getattr(settings, "vector", None)
        for key in ("persist_directory", "dir", "path"):
            val = getattr(vec, key, None) if vec is not None else None
            if isinstance(val, str) and val.strip():
                cand = val.strip()
                break
    except Exception:
        cand = None
    if not cand:
        cand = os.getenv("EMERGENCE_VECTOR_DIR")
    if not cand:
        cand = "./data/vector_store"
    return str(Path(cand).resolve())

def _get_embed_model_name(settings: Settings) -> str:
    """
    Modèle d'embedding SentenceTransformer.
    Préfère settings.vector.embed_model_name, sinon EMBED_MODEL_NAME, défaut all-MiniLM-L6-v2
    """
    try:
        vec = getattr(settings, "vector", None)
        name = getattr(vec, "embed_model_name", None)
        if isinstance(name, str) and name.strip():
            return name.strip()
    except Exception:
        pass
    return (os.getenv("EMBED_MODEL_NAME") or "all-MiniLM-L6-v2").strip()

def _get_uploads_dir(settings: Settings) -> str:
    """
    Répertoire de dépôt des fichiers uploadés (Documents).
    Préfère settings.paths.uploads, sinon EMERGENCE_UPLOADS_DIR, défaut ./data/uploads
    """
    try:
        paths = getattr(settings, "paths", None)
        up = getattr(paths, "uploads", None) if paths is not None else None
        if isinstance(up, str) and up.strip():
            return str(Path(up).resolve())
    except Exception:
        pass
    env = os.getenv("EMERGENCE_UPLOADS_DIR")
    if env and env.strip():
        return str(Path(env).resolve())
    return str(Path("./data/uploads").resolve())

# ----------------------------
# Container
# ----------------------------
class AppContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "backend.features.chat.router",
            "backend.features.threads.router",
            "backend.features.chat.service",
            "backend.features.debate.router",
        ]
    )

    # Settings (pydantic BaseSettings)
    settings = providers.Singleton(Settings)

    # --- DB ---
    db_path = providers.Callable(_get_db_path, settings)
    db_manager = providers.Singleton(DatabaseManager, db_path)  # positionnel → robuste

    # --- Coûts ---
    cost_tracker = providers.Singleton(CostTracker, db_manager=db_manager)

    # --- Mémoire vectorielle ---
    vector_dir = providers.Callable(_get_vector_dir, settings)
    embed_model_name = providers.Callable(_get_embed_model_name, settings)
    vector_service = providers.Singleton(
        VectorService,
        persist_directory=vector_dir,
        embed_model_name=embed_model_name,
    )

    # --- Analyse sémantique (STM) ---
    memory_analyzer = providers.Singleton(MemoryAnalyzer, db_manager=db_manager)

    # --- Sessions + WS ---
    session_manager = providers.Singleton(
        SessionManager,
        db_manager=db_manager,
        memory_analyzer=memory_analyzer,
    )
    connection_manager = providers.Singleton(ConnectionManager, session_manager=session_manager)

    # --- Chat ---
    chat_service = providers.Singleton(
        ChatService,
        session_manager=session_manager,
        cost_tracker=cost_tracker,
        vector_service=vector_service,
        settings=settings,
    )

    # --- Features optionnelles ---
    if DashboardService is not None:
        dashboard_service = providers.Singleton(
            DashboardService,
            db_manager=db_manager,
            cost_tracker=cost_tracker,
        )

    if DocumentService is not None and ParserFactory is not None:
        parser_factory = providers.Singleton(ParserFactory)
        uploads_dir = providers.Callable(_get_uploads_dir, settings)
        document_service = providers.Singleton(
            DocumentService,
            db_manager=db_manager,
            parser_factory=parser_factory,
            vector_service=vector_service,
            uploads_dir=uploads_dir,
        )

    if DebateService is not None:
        debate_service = providers.Singleton(
            DebateService,
            settings=settings,
            chat_service=chat_service,
            session_manager=session_manager,
            vector_service=vector_service,
            connection_manager=connection_manager,
            cost_tracker=cost_tracker,
        )

# Alias attendu par main.py & routers
ServiceContainer = AppContainer
