# src/backend/core/session_manager.py
# V13.2 - FIX: Alignement avec queries.py V5.1 et ajout du chargement de session.
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Imports corrigés pour refléter la structure réelle
from backend.shared.models import Session, ChatMessage, AgentMessage
from backend.core.database.manager import DatabaseManager
from backend.core.database import queries # Import du module queries
from backend.features.memory.analyzer import MemoryAnalyzer

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Gère les sessions de chat actives en mémoire et leur persistance.
    V13.2: Ajout du chargement de session depuis la BDD et correction des dépendances.
    """

    def __init__(self, db_manager: DatabaseManager, memory_analyzer: Optional[MemoryAnalyzer] = None):
        self.db_manager = db_manager
        self.memory_analyzer = memory_analyzer
        self.active_sessions: Dict[str, Session] = {}
        is_ready = self.memory_analyzer is not None
        logger.info(f"SessionManager V13.2 initialisé. MemoryAnalyzer prêt : {is_ready}")

    def _ensure_analyzer_ready(self):
        """Vérifie que le service dépendant est bien injecté avant utilisation."""
        if not self.memory_analyzer:
            logger.error("Dépendance 'memory_analyzer' non injectée dans SessionManager.")
            raise ReferenceError("SessionManager: memory_analyzer manquant.")

    def create_session(self, session_id: str, user_id: str):
        """Crée une session et la garde active en mémoire."""
        if session_id not in self.active_sessions:
            new_session = Session(id=session_id, user_id=user_id, start_time=datetime.now(timezone.utc))
            self.active_sessions[session_id] = new_session
            logger.info(f"Session active créée : {session_id} pour l'utilisateur {user_id}")
        else:
            logger.warning(f"Tentative de création d'une session déjà existante: {session_id}")

    def get_session(self, session_id: str) -> Optional[Session]:
        """Récupère une session depuis le cache mémoire actif."""
        return self.active_sessions.get(session_id)

    async def load_session_from_db(self, session_id: str) -> Optional[Session]:
        """
        NOUVEAU V13.2: Charge une session depuis la BDD si elle n'est pas active.
        C'est le chaînon manquant pour travailler sur des sessions passées.
        """
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        logger.info(f"Session {session_id} non active, tentative de chargement depuis la BDD...")
        # On utilise la nouvelle fonction de queries.py
        session_row = await queries.get_session_by_id(self.db_manager, session_id)

        if not session_row:
            logger.warning(f"Session {session_id} non trouvée en BDD.")
            return None

        try:
            # Reconstruction de l'objet Session à partir des données de la BDD
            session_dict = dict(session_row)
            history_json = session_dict.get('session_data', '[]')
            
            # Reconstruction de l'historique avec les bons modèles Pydantic
            history_list = json.loads(history_json)
            reconstructed_history = [
                AgentMessage(**msg) if msg.get('role') == 'assistant' else ChatMessage(**msg)
                for msg in history_list
            ]

            session = Session(
                id=session_dict['id'],
                user_id=session_dict['user_id'],
                start_time=datetime.fromisoformat(session_dict['created_at']),
                end_time=datetime.fromisoformat(session_dict['updated_at']),
                history=reconstructed_history,
                metadata={
                    "summary": session_dict.get('summary'),
                    "concepts": json.loads(session_dict.get('extracted_concepts', '[]') or '[]'),
                    "entities": json.loads(session_dict.get('extracted_entities', '[]') or '[]')
                }
            )
            
            self.active_sessions[session_id] = session # On la met en cache actif
            logger.info(f"Session {session_id} chargée et reconstruite depuis la BDD.")
            return session
        except Exception as e:
            logger.error(f"Erreur lors de la reconstruction de la session {session_id} depuis la BDD: {e}", exc_info=True)
            return None

    async def add_message_to_session(self, session_id: str, message: ChatMessage | AgentMessage):
        session = self.get_session(session_id)
        if session:
            # On utilise bien model_dump pour la sérialisation JSON
            session.history.append(message.model_dump(mode='json'))
        else:
            logger.error(f"Impossible d'ajouter un message : session {session_id} non trouvée.")

    def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.get_session(session_id)
        return session.history if session else []
    
    async def finalize_session(self, session_id: str):
        session = self.active_sessions.pop(session_id, None)
        if session:
            session.end_time = datetime.now(timezone.utc)
            duration = (session.end_time - session.start_time).total_seconds()
            logger.info(f"Finalisation de la session {session_id}. Durée: {duration:.2f}s.")
            
            # On utilise la méthode robuste du DatabaseManager pour sauvegarder
            await self.db_manager.save_session(session)

            # Lancement de l'analyse sémantique post-session
            if self.memory_analyzer:
                await self.memory_analyzer.analyze_session_for_concepts(session_id, session.history)
            else:
                logger.warning("MemoryAnalyzer non disponible, l'analyse post-session est sautée.")
        else:
            logger.warning(f"Tentative de finalisation d'une session inexistante ou déjà finalisée: {session_id}")

    async def update_and_save_session(self, session_id: str, update_data: Dict[str, Any]):
        """Met à jour une session active et la sauvegarde."""
        session = self.get_session(session_id)
        if not session:
            logger.error(f"Impossible de mettre à jour la session {session_id} : non trouvée.")
            return

        try:
            if not hasattr(session, 'metadata'):
                session.metadata = {}
            
            session.metadata.update(update_data.get("metadata", {}))
            logger.info(f"Session {session_id} mise à jour avec les données du débat.")
            
            await self.db_manager.save_session(session)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour et sauvegarde de la session {session_id}: {e}", exc_info=True)
