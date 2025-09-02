# src/backend/features/memory/analyzer.py
# V3.2 - + analyze_history(no-persist) ; refactor _analyze(..., persist)
import logging
import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.features.chat.service import ChatService
    from backend.core.database.manager import DatabaseManager

from backend.core.database import queries

logger = logging.getLogger(__name__)

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
        "summary": {"type": "string", "description": "Résumé concis de la conversation (2-3 phrases)."},
        "concepts": {"type": "array", "items": {"type": "string"}, "description": "3 à 5 concepts clés."},
        "entities": {"type": "array", "items": {"type": "string"}, "description": "Entités nommées."},
    },
    "required": ["summary", "concepts", "entities"],
}

class MemoryAnalyzer:
    """Analyse sémantique de session: summary + concepts + entities (STM)"""

    def __init__(self, db_manager: 'DatabaseManager', chat_service: Optional['ChatService'] = None):
        self.db_manager = db_manager
        self.chat_service = chat_service
        self.is_ready = self.chat_service is not None
        logger.info(f"MemoryAnalyzer V3.2 initialisé. Prêt: {self.is_ready}")

    def set_chat_service(self, chat_service: 'ChatService'):
        self.chat_service = chat_service
        self.is_ready = True
        logger.info("ChatService injecté dans MemoryAnalyzer. L'analyseur est prêt.")

    def _ensure_ready(self):
        if not self.chat_service:
            self.is_ready = False
            logger.error("Dépendance 'chat_service' non injectée. L'analyse est impossible.")
            raise ReferenceError("MemoryAnalyzer n'est pas prêt : chat_service manquant.")
        self.is_ready = True

    async def _notify(self, session_id: str, payload: Dict[str, Any]) -> None:
        conn = getattr(getattr(self.chat_service, "session_manager", None), "connection_manager", None)
        if conn:
            try:
                await conn.send_personal_message({"type": "ws:analysis_status", "payload": payload}, session_id)
            except Exception:
                pass

    def _already_analyzed(self, session_id: str) -> bool:
        try:
            sess = self.chat_service.session_manager.get_session(session_id)
            meta = getattr(sess, "metadata", None) or {}
            s = meta.get("summary")
            return isinstance(s, str) and bool(s.strip())
        except Exception:
            return False

    async def _analyze(self, session_id: str, history: List[Dict[str, Any]], persist: bool = True) -> Dict[str, Any]:
        self._ensure_ready()
        logger.info(f"Lancement de l'analyse sémantique (persist={persist}) pour {session_id}")

        # Idempotence seulement si on persiste (session réelle)
        if persist and self._already_analyzed(session_id):
            logger.info(f"Session {session_id} déjà analysée — skip.")
            await self._notify(session_id, {"session_id": session_id, "status": "skipped", "reason": "already_analyzed"})
            return {}

        conversation_text = "\n".join(f"{m.get('role')}: {m.get('content') or m.get('message','')}" for m in (history or []))
        if not conversation_text.strip():
            logger.warning(f"Historique vide pour {session_id}. Analyse annulée.")
            await self._notify(session_id, {"session_id": session_id, "status": "skipped", "reason": "no_history"})
            return {}

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(conversation_text=conversation_text)

        analysis_result: Dict[str, Any] = {}
        primary_error: Optional[Exception] = None
        try:
            analysis_result = await self.chat_service.get_structured_llm_response(agent_id='neo', prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA)
        except Exception as e:
            primary_error = e
            logger.warning(f"Analyse (neo) a échoué — tentative fallback nexus. err={e}", exc_info=True)

        if not analysis_result:
            try:
                analysis_result = await self.chat_service.get_structured_llm_response(agent_id='nexus', prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA)
            except Exception as e:
                logger.error(f"Analyse (fallback nexus) a échoué: {e}", exc_info=True)
                retry_after = None
                try:
                    rd = getattr(primary_error or e, 'retry_delay', None)
                    retry_after = getattr(rd, 'seconds', None)
                except Exception:
                    pass
                await self._notify(session_id, {"session_id": session_id, "status": "failed", "error": str(e), "retry_after": retry_after})
                raise

        if persist:
            await queries.update_session_analysis_data(
                db=self.db_manager,
                session_id=session_id,
                summary=analysis_result.get("summary"),
                concepts=analysis_result.get("concepts", []) or [],
                entities=analysis_result.get("entities", []) or [],
            )

        await self._notify(session_id, {"session_id": session_id, "status": "completed"})
        logger.info(f"Analyse sémantique terminée (persist={persist}) pour {session_id}.")
        return analysis_result

    async def analyze_session_for_concepts(self, session_id: str, history: List[Dict[str, Any]]):
        """Mode historique (sessions) : persiste dans la table sessions."""
        return await self._analyze(session_id, history, persist=True)

    async def analyze_history(self, session_id: str, history: List[Dict[str, Any]]):
        """Mode “thread-only” : renvoie le résultat sans écrire dans la table sessions."""
        return await self._analyze(session_id, history, persist=False)
