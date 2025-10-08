# src/backend/features/memory/analyzer.py
# V3.5 - Phase 2: neo_analysis (GPT-4o-mini) + cache in-memory pour optimiser perf
import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from backend.features.chat.service import ChatService
    from backend.core.database.manager import DatabaseManager

from backend.core.database import queries

logger = logging.getLogger(__name__)

# ⚡ Cache in-memory pour analyses (TTL 1h)
_ANALYSIS_CACHE: Dict[str, tuple[Dict[str, Any], datetime]] = {}

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
            "description": "Résumé concis de la conversation (2-3 phrases).",
        },
        "concepts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3 à 5 concepts clés.",
        },
        "entities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Entités nommées.",
        },
    },
    "required": ["summary", "concepts", "entities"],
}


class MemoryAnalyzer:
    """Analyse sémantique de session: summary + concepts + entities (STM)"""

    def __init__(
        self,
        db_manager: "DatabaseManager",
        chat_service: Optional["ChatService"] = None,
    ):
        self.db_manager = db_manager
        self.chat_service = chat_service
        self.is_ready = self.chat_service is not None
        logger.info(f"MemoryAnalyzer V3.4 initialisé. Prêt: {self.is_ready}")

    def set_chat_service(self, chat_service: "ChatService"):
        self.chat_service = chat_service
        self.is_ready = True
        logger.info("ChatService injecté dans MemoryAnalyzer. L'analyseur est prêt.")

    def _ensure_ready(self):
        if not self.chat_service:
            self.is_ready = False
            logger.error(
                "Dépendance 'chat_service' non injectée. L'analyse est impossible."
            )
            raise ReferenceError(
                "MemoryAnalyzer n'est pas prêt : chat_service manquant."
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
        chat_service = self.chat_service
        if chat_service is None:
            return False
        session_manager = getattr(chat_service, "session_manager", None)
        if session_manager is None:
            return False
        try:
            sess = session_manager.get_session(session_id)
            meta = getattr(sess, "metadata", None) or {}
            summary_value = meta.get("summary")
            return isinstance(summary_value, str) and bool(summary_value.strip())
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
            f"Lancement de l'analyse sémantique (persist={persist}) pour {session_id}"
        )

        # Idempotence seulement si on persiste (session réelle)
        if persist and not force and self._already_analyzed(session_id):
            logger.info(f"Session {session_id} déjà analysée — skip.")
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
            logger.warning(f"Historique vide pour {session_id}. Analyse annulée.")
            await self._notify(
                session_id,
                {"session_id": session_id, "status": "skipped", "reason": "no_history"},
            )
            return {}

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(conversation_text=conversation_text)

        # ⚡ Cache Layer: éviter recalculs inutiles
        cache_key = None
        if persist and not force:
            history_hash = hashlib.md5(conversation_text.encode()).hexdigest()[:8]
            cache_key = f"memory_analysis:{session_id}:{history_hash}"

            # Check cache validity (TTL 1h)
            if cache_key in _ANALYSIS_CACHE:
                cached_data, cached_at = _ANALYSIS_CACHE[cache_key]
                if datetime.now() - cached_at < timedelta(hours=1):
                    logger.info(f"[MemoryAnalyzer] Cache HIT pour session {session_id} (hash={history_hash})")
                    return cached_data
                else:
                    # Cache expiré
                    del _ANALYSIS_CACHE[cache_key]
                    logger.debug(f"[MemoryAnalyzer] Cache EXPIRED pour session {session_id}")

        analysis_result: Dict[str, Any] = {}
        primary_error: Optional[Exception] = None
        provider_used = "neo_analysis"

        # Tentative primaire : neo_analysis (GPT-4o-mini - rapide pour JSON)
        try:
            analysis_result = await chat_service.get_structured_llm_response(
                agent_id="neo_analysis", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
            )
            logger.info(f"[MemoryAnalyzer] Analyse réussie avec neo_analysis pour session {session_id}")
        except Exception as e:
            primary_error = e
            error_type = type(e).__name__
            logger.warning(
                f"[MemoryAnalyzer] Analyse neo_analysis échouée ({error_type}) pour session {session_id} — fallback Nexus",
                exc_info=True,
            )

        # Fallback 1 : Nexus (Anthropic - plus fiable)
        if not analysis_result:
            provider_used = "nexus"
            try:
                analysis_result = await chat_service.get_structured_llm_response(
                    agent_id="nexus", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
                )
                logger.info(f"[MemoryAnalyzer] Fallback Nexus réussi pour session {session_id}")
            except Exception as e:
                logger.warning(f"[MemoryAnalyzer] Fallback Nexus échoué ({type(e).__name__}) — tentative Anima", exc_info=True)

                # Fallback 2 : Anima (OpenAI - dernière chance)
                provider_used = "anima"
                try:
                    analysis_result = await chat_service.get_structured_llm_response(
                        agent_id="anima", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
                    )
                    logger.info(f"[MemoryAnalyzer] Fallback Anima réussi pour session {session_id}")
                except Exception as final_error:
                    logger.error(
                        f"[MemoryAnalyzer] Tous fallbacks échoués pour session {session_id}: {final_error}",
                        exc_info=True
                    )
                    retry_after = None
                    try:
                        rd = getattr(primary_error or final_error, "retry_delay", None)
                        retry_after = getattr(rd, "seconds", None)
                    except Exception:
                        pass
                    await self._notify(
                        session_id,
                        {
                            "session_id": session_id,
                            "status": "failed",
                            "error": str(final_error),
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
                f"Impossible de mettre à jour les métadonnées de session {session_id}: {meta_err}"
            )

        # ⚡ Save to cache (après analyse réussie)
        if analysis_result and cache_key and persist:
            _ANALYSIS_CACHE[cache_key] = (analysis_result, datetime.now())
            logger.info(f"[MemoryAnalyzer] Cache SAVED pour session {session_id} (key={cache_key})")

            # Cleanup: limiter taille cache (max 100 entrées)
            if len(_ANALYSIS_CACHE) > 100:
                oldest_key = min(_ANALYSIS_CACHE.keys(), key=lambda k: _ANALYSIS_CACHE[k][1])
                del _ANALYSIS_CACHE[oldest_key]
                logger.debug(f"[MemoryAnalyzer] Cache cleanup: removed oldest entry {oldest_key}")

        await self._notify(
            session_id, {"session_id": session_id, "status": "completed", "provider": provider_used}
        )
        logger.info(
            f"Analyse sémantique terminée (persist={persist}, provider={provider_used}) pour {session_id}."
        )
        return analysis_result

    async def analyze_session_for_concepts(
        self, session_id: str, history: List[Dict[str, Any]], *, force: bool = False
    ):
        """Mode historique (sessions) : persiste dans la table sessions."""
        return await self._analyze(session_id, history, persist=True, force=force)

    async def analyze_history(self, session_id: str, history: List[Dict[str, Any]]):
        """Mode «thread-only» : renvoie le résultat sans écrire dans la table sessions."""
        return await self._analyze(session_id, history, persist=False, force=False)
