# src/backend/features/memory/analyzer.py
# V3.2 - + analyze_history(no-persist) ; refactor _analyze(..., persist)
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.features.chat.service import ChatService
    from backend.core.database.manager import DatabaseManager

from backend.core.database import queries

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT_TEMPLATE = """
Analyse la conversation suivante et extrais les informations clÃ©s.
La conversation est un dialogue entre un utilisateur ("user") et un ou plusieurs assistants IA ("assistant").

CONVERSATION:
---
{conversation_text}
---

En te basant sur cette conversation, fournis les Ã©lÃ©ments suivants :
1.  **summary**: Un rÃ©sumÃ© concis de la conversation en 2-3 phrases maximum.
2.  **concepts**: Une liste de 3 Ã  5 concepts ou thÃ¨mes principaux abordÃ©s. Sois spÃ©cifique (ex: "Ã©thique de l'IA dans le diagnostic mÃ©dical" plutÃ´t que "IA").
3.  **entities**: Une liste des noms propres, lieux, ou titres d'Å“uvres spÃ©cifiques mentionnÃ©s.
"""

ANALYSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "RÃ©sumÃ© concis de la conversation (2-3 phrases).",
        },
        "concepts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 Ã  5 concepts clÃ©s.",
        },
        "entities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "EntitÃ©s nommÃ©es.",
        },
    },
    "required": ["summary", "concepts", "entities"],
}


class MemoryAnalyzer:
    """Analyse sÃ©mantique de session: summary + concepts + entities (STM)"""

    def __init__(
        self,
        db_manager: "DatabaseManager",
        chat_service: Optional["ChatService"] = None,
    ):
        self.db_manager = db_manager
        self.chat_service = chat_service
        self.is_ready = self.chat_service is not None
        logger.info(f"MemoryAnalyzer V3.2 initialisÃ©. PrÃªt: {self.is_ready}")

    def set_chat_service(self, chat_service: "ChatService"):
        self.chat_service = chat_service
        self.is_ready = True
        logger.info("ChatService injectÃ© dans MemoryAnalyzer. L'analyseur est prÃªt.")

    def _ensure_ready(self):
        if not self.chat_service:
            self.is_ready = False
            logger.error(
                "DÃ©pendance 'chat_service' non injectÃ©e. L'analyse est impossible."
            )
            raise ReferenceError(
                "MemoryAnalyzer n'est pas prÃªt : chat_service manquant."
            )
        self.is_ready = True

    async def _notify(self, session_id: str, payload: Dict[str, Any]) -> None:
        conn = getattr(
            getattr(self.chat_service, "session_manager", None),
            "connection_manager",
            None,
        )
        if conn:
            try:
                await conn.send_personal_message(
                    {"type": "ws:analysis_status", "payload": payload}, session_id
                )
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

    async def _analyze(
        self,
        session_id: str,
        history: List[Dict[str, Any]],
        persist: bool = True,
        force: bool = False,
    ) -> Dict[str, Any]:
        self._ensure_ready()
        chat_service = self.chat_service
        if chat_service is None:
            raise ReferenceError(
                "MemoryAnalyzer n'est pas prêt : chat_service manquant."
            )
        logger.info(
            f"Lancement de l'analyse sÃ©mantique (persist={persist}) pour {session_id}"
        )

        # Idempotence seulement si on persiste (session rÃ©elle)
        if persist and not force and self._already_analyzed(session_id):
            logger.info(f"Session {session_id} dÃ©jÃ  analysÃ©e â€” skip.")
            await self._notify(
                session_id,
                {
                    "session_id": session_id,
                    "status": "skipped",
                    "reason": "already_analyzed",
                },
            )
            return {}

        conversation_text = "\n".join(
            f"{m.get('role')}: {m.get('content') or m.get('message', '')}"
            for m in (history or [])
        )
        if not conversation_text.strip():
            logger.warning(f"Historique vide pour {session_id}. Analyse annulÃ©e.")
            await self._notify(
                session_id,
                {"session_id": session_id, "status": "skipped", "reason": "no_history"},
            )
            return {}

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(conversation_text=conversation_text)

        analysis_result: Dict[str, Any] = {}
        primary_error: Optional[Exception] = None
        try:
            analysis_result = await chat_service.get_structured_llm_response(
                agent_id="neo", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
            )
        except Exception as e:
            primary_error = e
            logger.warning(
                f"Analyse (neo) a Ã©chouÃ© â€” tentative fallback nexus. err={e}",
                exc_info=True,
            )

        if not analysis_result:
            try:
                analysis_result = await chat_service.get_structured_llm_response(
                    agent_id="nexus", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
                )
            except Exception as e:
                logger.error(f"Analyse (fallback nexus) a Ã©chouÃ©: {e}", exc_info=True)
                retry_after = None
                try:
                    rd = getattr(primary_error or e, "retry_delay", None)
                    retry_after = getattr(rd, "seconds", None)
                except Exception:
                    pass
                await self._notify(
                    session_id,
                    {
                        "session_id": session_id,
                        "status": "failed",
                        "error": str(e),
                        "retry_after": retry_after,
                    },
                )
                raise

        summary_value = str(analysis_result.get("summary", "") or "")
        concepts_raw = analysis_result.get("concepts", []) or []
        entities_raw = analysis_result.get("entities", []) or []
        concepts_value = [str(item) for item in concepts_raw if isinstance(item, str)]
        entities_value = [str(item) for item in entities_raw if isinstance(item, str)]

        if persist:
            await queries.update_session_analysis_data(
                db=self.db_manager,
                session_id=session_id,
                summary=summary_value,
                concepts=concepts_value,
                entities=entities_value,
            )

        try:
            session_manager = getattr(chat_service, "session_manager", None)
            if session_manager:
                session_manager.update_session_metadata(
                    session_id,
                    summary=summary_value,
                    concepts=concepts_value,
                    entities=entities_value,
                )
        except Exception as meta_err:
            logger.debug(
                f"Impossible de mettre Ã  jour les mÃ©tadonnÃ©es de session {session_id}: {meta_err}"
            )

        await self._notify(
            session_id, {"session_id": session_id, "status": "completed"}
        )
        logger.info(
            f"Analyse sÃ©mantique terminÃ©e (persist={persist}) pour {session_id}."
        )
        return analysis_result

    async def analyze_session_for_concepts(
        self, session_id: str, history: List[Dict[str, Any]], *, force: bool = False
    ):
        """Mode historique (sessions) : persiste dans la table sessions."""
        return await self._analyze(session_id, history, persist=True, force=force)

    async def analyze_history(self, session_id: str, history: List[Dict[str, Any]]):
        """Mode Â«thread-onlyÂ» : renvoie le rÃ©sultat sans Ã©crire dans la table sessions."""
        return await self._analyze(session_id, history, persist=False, force=False)
