# src/backend/containers.py
# V6.2 — DI unifiée : plus d'instance module-level, wiring géré dans main.py; MemoryAnalyzer injecté dans SessionManager.
from dependency_injector import containers, providers

# --- IMPORTS DES SERVICES ---
from backend.shared.config import Settings
from backend.core.database.manager import DatabaseManager
from backend.core.cost_tracker import CostTracker
from backend.core.session_manager import SessionManager
from backend.core.websocket import ConnectionManager
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.memory.vector_service import VectorService
from backend.features.chat.service import ChatService
from backend.features.debate.service import DebateService
from backend.features.documents.parser import ParserFactory
from backend.features.documents.service import DocumentService
from backend.features.dashboard.service import DashboardService


class ServiceContainer(containers.DeclarativeContainer):
    """
    Conteneur de dépendances.
    V6.2 : un seul container instancié dans main.create_app(); plus de wiring/instance module-level ici.
    """
    config = providers.Configuration()

    settings = providers.Singleton(Settings)

    db_manager = providers.Singleton(
        DatabaseManager,
        db_path=settings.provided.db.filepath,
    )

    cost_tracker = providers.Singleton(CostTracker, db_manager=db_manager)

    vector_service = providers.Singleton(
        VectorService,
        persist_directory=settings.provided.db.vector_store_path,
        embed_model_name=settings.provided.rag.EMBED_MODEL_NAME,
    )

    parser_factory = providers.Singleton(ParserFactory)

    # --- Mémoire / Analyse ---
    memory_analyzer = providers.Singleton(
        MemoryAnalyzer,
        db_manager=db_manager,
        # chat_service injecté plus tard au startup (injection tardive via main.py)
    )

    # --- Sessions / Chat / WS ---
    session_manager = providers.Singleton(
        SessionManager,
        db_manager=db_manager,
        memory_analyzer=memory_analyzer,
    )

    chat_service = providers.Singleton(
        ChatService,
        session_manager=session_manager,
        cost_tracker=cost_tracker,
        vector_service=vector_service,
        settings=settings,
    )

    connection_manager = providers.Singleton(
        ConnectionManager,
        session_manager=session_manager,
    )

    # --- DOCUMENTS / DÉBAT / DASHBOARD ---
    document_service = providers.Singleton(
        DocumentService,
        db_manager=db_manager,
        parser_factory=parser_factory,
        vector_service=vector_service,
        uploads_dir=settings.provided.paths.documents,
    )

    debate_service = providers.Singleton(
        DebateService,
        chat_service=chat_service,
        connection_manager=connection_manager,
        session_manager=session_manager,
        vector_service=vector_service,
        settings=settings,
    )

    dashboard_service = providers.Singleton(
        DashboardService,
        db_manager=db_manager,
        cost_tracker=cost_tracker,
    )


__all__ = ["ServiceContainer"]
