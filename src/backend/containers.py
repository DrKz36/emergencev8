# src/backend/containers.py
# V5.2 - FINAL: Injection de db_manager dans MemoryAnalyzer.
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
    Version 5.2: Finalise l'injection pour la Mémoire Vive.
    """
    config = providers.Configuration()

    settings = providers.Singleton(Settings)
    
    db_manager = providers.Singleton(
        DatabaseManager,
        db_path=settings.provided.db.filepath
    )
    
    cost_tracker = providers.Singleton(CostTracker, db_manager=db_manager)
    
    vector_service = providers.Singleton(
        VectorService,
        persist_directory=settings.provided.db.vector_store_path,
        embed_model_name=settings.provided.rag.EMBED_MODEL_NAME
    )
    
    parser_factory = providers.Singleton(ParserFactory)

    # --- BLOC DE SERVICES AVEC DÉPENDANCES CIRCULAIRES ---
    session_manager = providers.Singleton(
        SessionManager, 
        db_manager=db_manager
        # NOTE: Le memory_analyzer est injecté manuellement dans main.py
    )

    chat_service = providers.Singleton(
        ChatService,
        session_manager=session_manager,
        cost_tracker=cost_tracker,
        vector_service=vector_service,
        settings=settings
    )

    # --- CORRECTION V5.2 ---
    # On injecte maintenant le db_manager dans l'analyseur pour qu'il puisse
    # sauvegarder les résultats de l'analyse sémantique.
    memory_analyzer = providers.Singleton(
        MemoryAnalyzer,
        db_manager=db_manager
    )
    
    connection_manager = providers.Singleton(
        ConnectionManager,
        session_manager=session_manager
    )
    
    # --- FIN DU BLOC ---
    
    document_service = providers.Singleton(
        DocumentService,
        db_manager=db_manager,
        parser_factory=parser_factory,
        vector_service=vector_service,
        uploads_dir=settings.provided.paths.documents
    )
    
    debate_service = providers.Singleton(
        DebateService,
        chat_service=chat_service,
        connection_manager=connection_manager,
        session_manager=session_manager,
        vector_service=vector_service,
        settings=settings
    )
    
    dashboard_service = providers.Singleton(
        DashboardService,
        db_manager=db_manager,
        cost_tracker=cost_tracker
    )
