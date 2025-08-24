# src/backend/features/memory/analyzer.py
# V3.0 - Implémentation de la logique d'analyse sémantique réelle.
import logging
import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING

# --- GESTION DE LA DÉPENDANCE CIRCULAIRE ---
if TYPE_CHECKING:
    from backend.features.chat.service import ChatService
    from backend.core.database.manager import DatabaseManager  # NOUVEAU

# NOUVEAU: Import des requêtes pour la mise à jour
from backend.core.database import queries

logger = logging.getLogger(__name__)

# NOUVEAU: Prompt et Schéma pour l'analyse structurée
ANALYSIS_PROMPT_TEMPLATE = """
Analyse la conversation suivante et extrais les informations clés.
La conversation est un dialogue entre un utilisateur ("user") et un ou plusieurs assistants IA ("assistant").

CONVERSATION:
---
{conversation_text}
---

En te basant sur cette conversation, fournis les éléments suivants :
1.  **summary**: Un résumé concis de la conversation en 2-3 phrases maximum.
2.  **concepts**: Une liste de 3 à 5 concepts ou thèmes principaux abordés. Sois spécifique (ex: "éthique de l'IA dans le diagnostic médical" plutôt que "IA").
3.  **entities**: Une liste des noms propres, lieux, ou titres d'œuvres spécifiques mentionnés.
"""

ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "Résumé concis de la conversation (2-3 phrases)."
        },
        "concepts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Liste de 3 à 5 concepts ou thèmes clés."
        },
        "entities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Liste des entités nommées (personnes, lieux, œuvres)."
        }
    },
    "required": ["summary", "concepts", "entities"]
}


class MemoryAnalyzer:
    """
    Analyse les conversations pour en extraire les concepts clés et les entités.
    V3.0 : Implémente l'appel réel au LLM pour l'analyse sémantique.
    """
    def __init__(self, db_manager: 'DatabaseManager', chat_service: Optional['ChatService'] = None):
        """
        MODIFIÉ V3.0: Ajout du db_manager pour sauvegarder les résultats de l'analyse.
        """
        self.db_manager = db_manager  # NOUVEAU
        self.chat_service = chat_service
        self.is_ready = self.chat_service is not None
        logger.info(f"MemoryAnalyzer V3.0 initialisé. Prêt : {self.is_ready}")

    def set_chat_service(self, chat_service: 'ChatService'):
        """Méthode pour injecter le ChatService et casser la dépendance circulaire."""
        self.chat_service = chat_service
        self.is_ready = True
        logger.info("ChatService injecté dans MemoryAnalyzer. L'analyseur est prêt.")

    def _ensure_ready(self):
        """Vérifie que le service dépendant est bien injecté avant utilisation."""
        if not self.chat_service:
            self.is_ready = False
            logger.error("Dépendance 'chat_service' non injectée. L'analyse est impossible.")
            raise ReferenceError("MemoryAnalyzer n'est pas prêt : chat_service manquant.")
        self.is_ready = True

    async def analyze_session_for_concepts(self, session_id: str, history: List[Dict[str, Any]]):
        """
        MODIFIÉ V3.0: Tâche principale d'analyse réelle de la session.
        """
        self._ensure_ready()
        logger.info(f"Lancement de l'analyse sémantique pour la session {session_id}")

        try:
            # 1. Préparer le contenu pour l'analyse
            conversation_text = "\n".join(
                f"{msg.get('role')}: {msg.get('content') or msg.get('message', '')}" for msg in history
            )

            if not conversation_text.strip():
                logger.warning(f"Historique de la session {session_id} est vide. Analyse annulée.")
                return

            prompt = ANALYSIS_PROMPT_TEMPLATE.format(conversation_text=conversation_text)

            # 2. Appeler le LLM pour une réponse structurée
            analysis_result = await self.chat_service.get_structured_llm_response(
                agent_id='neo',  # 'neo' (Gemini Flash) pour ce type de tâche
                prompt=prompt,
                json_schema=ANALYSIS_JSON_SCHEMA
            )

            if not analysis_result:
                raise ValueError("La réponse du LLM pour l'analyse était vide ou invalide.")

            logger.info(f"Analyse reçue pour la session {session_id}: {analysis_result}")

            # 3. Sauvegarder les résultats dans la base de données
            await queries.update_session_analysis_data(
                db=self.db_manager,
                session_id=session_id,
                summary=analysis_result.get("summary"),
                concepts=analysis_result.get("concepts", []),
                entities=analysis_result.get("entities", [])
            )

            # 4. Notifier le client du succès via SessionManager → ConnectionManager
            conn = getattr(getattr(self.chat_service, "session_manager", None), "connection_manager", None)
            if conn:
                await conn.send_personal_message(
                    {"type": "ws:analysis_status", "payload": {"session_id": session_id, "status": "completed"}},
                    session_id
                )
            else:
                logger.warning("ConnectionManager indisponible, skip notification ws:analysis_status (completed).")

            logger.info(f"Analyse sémantique et sauvegarde terminées pour la session {session_id}.")

        except Exception as e:
            logger.error(f"Erreur durant l'analyse de la session {session_id}: {e}", exc_info=True)
            try:
                conn = getattr(getattr(self.chat_service, "session_manager", None), "connection_manager", None)
                if conn:
                    await conn.send_personal_message(
                        {"type": "ws:analysis_status", "payload": {"session_id": session_id, "status": "failed", "error": str(e)}},
                        session_id
                    )
                else:
                    logger.warning("ConnectionManager indisponible, skip notification ws:analysis_status (failed).")
            except Exception as send_error:
                logger.error(f"Impossible de notifier le client de l'échec de l'analyse pour {session_id}: {send_error}")
