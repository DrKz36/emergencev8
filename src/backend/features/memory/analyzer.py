# src/backend/features/memory/analyzer.py
# V3.7 - Phase P1: Extraction préférences/intentions + enrichissement mémoire
import logging
import hashlib
from typing import Dict, Any, List, Optional, TYPE_CHECKING, Callable
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from backend.features.chat.service import ChatService
    from backend.core.database.manager import DatabaseManager

from backend.core.database import queries
from backend.features.memory.preference_extractor import PreferenceExtractor

# ⚡ Métriques Prometheus (Phase 3)
try:
    from prometheus_client import Counter, Histogram, Gauge

    # Compteurs succès/échec par provider
    ANALYSIS_SUCCESS_TOTAL = Counter(
        "memory_analysis_success_total",
        "Nombre total d'analyses réussies",
        ["provider"]  # neo_analysis, nexus, anima
    )
    ANALYSIS_FAILURE_TOTAL = Counter(
        "memory_analysis_failure_total",
        "Nombre total d'analyses échouées",
        ["provider", "error_type"]
    )

    # Cache metrics
    CACHE_HITS_TOTAL = Counter(
        "memory_analysis_cache_hits_total",
        "Nombre total de cache hits"
    )
    CACHE_MISSES_TOTAL = Counter(
        "memory_analysis_cache_misses_total",
        "Nombre total de cache misses"
    )
    CACHE_SIZE = Gauge(
        "memory_analysis_cache_size",
        "Taille actuelle du cache in-memory"
    )

    # Latence analyses
    ANALYSIS_DURATION_SECONDS = Histogram(
        "memory_analysis_duration_seconds",
        "Durée des analyses mémoire",
        ["provider"],
        buckets=[0.5, 1.0, 2.0, 4.0, 6.0, 10.0, 15.0, 20.0, 30.0]
    )

    # 🆕 HOTFIX P1.3: Métriques échecs extraction préférences
    PREFERENCE_EXTRACTION_FAILURES = Counter(
        "memory_preference_extraction_failures_total",
        "Échecs extraction préférences",
        ["reason"]  # "user_identifier_missing", "extraction_error", "persistence_error"
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

if not PROMETHEUS_AVAILABLE:
    logger.warning("Prometheus client non disponible - métriques désactivées")

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
        self.preference_extractor: Optional[PreferenceExtractor] = None
        logger.info(f"MemoryAnalyzer V3.7 (P1) initialisé. Prêt: {self.is_ready}")

    def set_chat_service(self, chat_service: "ChatService"):
        self.chat_service = chat_service
        self.is_ready = True
        # Initialiser PreferenceExtractor avec le chat_service (pour appels LLM)
        self.preference_extractor = PreferenceExtractor(llm_client=chat_service)
        logger.info("ChatService injecté dans MemoryAnalyzer. L'analyseur et PreferenceExtractor sont prêts.")

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
                    # 📊 Métrique cache HIT
                    if PROMETHEUS_AVAILABLE:
                        CACHE_HITS_TOTAL.inc()
                    return cached_data
                else:
                    # Cache expiré
                    del _ANALYSIS_CACHE[cache_key]
                    logger.debug(f"[MemoryAnalyzer] Cache EXPIRED pour session {session_id}")

        # 📊 Métrique cache MISS
        if PROMETHEUS_AVAILABLE and persist and not force:
            CACHE_MISSES_TOTAL.inc()

        analysis_result: Dict[str, Any] = {}
        primary_error: Optional[Exception] = None
        provider_used = "neo_analysis"
        start_time = datetime.now()

        # Tentative primaire : neo_analysis (GPT-4o-mini - rapide pour JSON)
        try:
            analysis_result = await chat_service.get_structured_llm_response(
                agent_id="neo_analysis", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
            )
            # 📊 Métriques succès
            if PROMETHEUS_AVAILABLE:
                duration = (datetime.now() - start_time).total_seconds()
                ANALYSIS_DURATION_SECONDS.labels(provider="neo_analysis").observe(duration)
                ANALYSIS_SUCCESS_TOTAL.labels(provider="neo_analysis").inc()
            logger.info(f"[MemoryAnalyzer] Analyse réussie avec neo_analysis pour session {session_id}")
        except Exception as e:
            primary_error = e
            error_type = type(e).__name__
            # 📊 Métriques échec
            if PROMETHEUS_AVAILABLE:
                ANALYSIS_FAILURE_TOTAL.labels(provider="neo_analysis", error_type=error_type).inc()
            logger.warning(
                f"[MemoryAnalyzer] Analyse neo_analysis échouée ({error_type}) pour session {session_id} — fallback Nexus",
                exc_info=True,
            )

        # Fallback 1 : Nexus (Anthropic - plus fiable)
        if not analysis_result:
            provider_used = "nexus"
            start_time = datetime.now()
            try:
                analysis_result = await chat_service.get_structured_llm_response(
                    agent_id="nexus", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
                )
                # 📊 Métriques succès Nexus
                if PROMETHEUS_AVAILABLE:
                    duration = (datetime.now() - start_time).total_seconds()
                    ANALYSIS_DURATION_SECONDS.labels(provider="nexus").observe(duration)
                    ANALYSIS_SUCCESS_TOTAL.labels(provider="nexus").inc()
                logger.info(f"[MemoryAnalyzer] Fallback Nexus réussi pour session {session_id}")
            except Exception as e:
                # 📊 Métriques échec Nexus
                if PROMETHEUS_AVAILABLE:
                    ANALYSIS_FAILURE_TOTAL.labels(provider="nexus", error_type=type(e).__name__).inc()
                logger.warning(f"[MemoryAnalyzer] Fallback Nexus échoué ({type(e).__name__}) — tentative Anima", exc_info=True)

                # Fallback 2 : Anima (OpenAI - dernière chance)
                provider_used = "anima"
                start_time = datetime.now()
                try:
                    analysis_result = await chat_service.get_structured_llm_response(
                        agent_id="anima", prompt=prompt, json_schema=ANALYSIS_JSON_SCHEMA
                    )
                    # 📊 Métriques succès Anima
                    if PROMETHEUS_AVAILABLE:
                        duration = (datetime.now() - start_time).total_seconds()
                        ANALYSIS_DURATION_SECONDS.labels(provider="anima").observe(duration)
                        ANALYSIS_SUCCESS_TOTAL.labels(provider="anima").inc()
                    logger.info(f"[MemoryAnalyzer] Fallback Anima réussi pour session {session_id}")
                except Exception as final_error:
                    # 📊 Métriques échec Anima
                    if PROMETHEUS_AVAILABLE:
                        ANALYSIS_FAILURE_TOTAL.labels(provider="anima", error_type=type(final_error).__name__).inc()
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

            # 📊 Métrique taille cache
            if PROMETHEUS_AVAILABLE:
                CACHE_SIZE.set(len(_ANALYSIS_CACHE))

        # ⚡ Phase P1: Extraction préférences/intentions
        if persist and self.preference_extractor and analysis_result:
            try:
                # 🆕 HOTFIX P1.3: Récupérer user_sub ET user_id depuis session
                user_sub = None
                user_id = None
                try:
                    session_manager = getattr(chat_service, "session_manager", None)
                    if session_manager:
                        sess = session_manager.get_session(session_id)
                        if sess:
                            # Essayer user_sub depuis metadata
                            user_sub = getattr(sess, "metadata", {}).get("user_sub")
                            # Fallback sur user_id
                            user_id = getattr(sess, "user_id", None)
                except Exception as e:
                    logger.debug(f"[PreferenceExtractor] Error getting user context: {e}")
                    pass

                # 🆕 HOTFIX P1.3: Accepter user_id en fallback si user_sub absent
                if user_sub or user_id:
                    # Identifier utilisateur (priorité user_sub)
                    user_identifier = user_sub if user_sub else user_id
                    if not user_identifier:
                        raise ValueError("user_identifier cannot be None")

                    # Extraire préférences depuis l'historique
                    preferences = await self.preference_extractor.extract(
                        messages=history,
                        user_sub=user_sub,
                        user_id=user_id,
                        thread_id=session_id
                    )

                    if preferences:
                        logger.info(
                            f"[PreferenceExtractor] Extracted {len(preferences)} preferences/intents "
                            f"for session {session_id} (user_sub={user_sub}, user_id={user_id})"
                        )

                        # ✅ P1.2: Sauvegarder dans ChromaDB (emergence_knowledge collection)
                        try:
                            saved_count = await self._save_preferences_to_vector_db(
                                preferences=preferences,
                                user_id=user_identifier,
                                thread_id=session_id,
                                session_id=session_id
                            )
                            logger.info(
                                f"[PreferenceExtractor] Saved {saved_count}/{len(preferences)} "
                                f"preferences to ChromaDB for user {user_sub}"
                            )
                        except Exception as save_error:
                            logger.error(
                                f"[PreferenceExtractor] Failed to save preferences to ChromaDB: {save_error}",
                                exc_info=True
                            )
                            # 📊 Incrémenter métrique échec persistence
                            if PROMETHEUS_AVAILABLE:
                                PREFERENCE_EXTRACTION_FAILURES.labels(
                                    reason="persistence_error"
                                ).inc()
                            # Continue sans bloquer (graceful degradation)

                        # Logging détaillé pour debug
                        for pref in preferences:
                            logger.debug(
                                f"  [{pref.type}] {pref.topic}: {pref.text[:60]}... "
                                f"(confidence={pref.confidence:.2f})"
                            )
                    else:
                        logger.debug(f"[PreferenceExtractor] No preferences found in session {session_id}")
                else:
                    # 🆕 HOTFIX P1.3: Message d'erreur mis à jour + métrique
                    logger.warning(
                        f"[PreferenceExtractor] Cannot extract: no user identifier "
                        f"(user_sub or user_id) found for session {session_id}"
                    )
                    # 📊 Incrémenter métrique échec
                    if PROMETHEUS_AVAILABLE:
                        PREFERENCE_EXTRACTION_FAILURES.labels(
                            reason="user_identifier_missing"
                        ).inc()

            except Exception as pref_error:
                logger.error(
                    f"[PreferenceExtractor] Failed to extract preferences for session {session_id}: {pref_error}",
                    exc_info=True
                )
                # 📊 Incrémenter métrique échec extraction
                if PROMETHEUS_AVAILABLE:
                    PREFERENCE_EXTRACTION_FAILURES.labels(
                        reason="extraction_error"
                    ).inc()

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

    async def _save_preferences_to_vector_db(
        self,
        preferences: List[Any],
        user_id: str,
        thread_id: str,
        session_id: str
    ) -> int:
        """
        Sauvegarde les préférences extraites dans ChromaDB (collection emergence_knowledge).

        Args:
            preferences: Liste de PreferenceItem extraits
            user_id: ID utilisateur propriétaire
            thread_id: ID thread source
            session_id: ID session source

        Returns:
            Nombre de préférences sauvegardées avec succès

        Raises:
            Exception: Si VectorService non disponible ou erreur ChromaDB
        """
        if not preferences:
            return 0

        # Récupérer VectorService depuis ChatService
        vector_service = getattr(self.chat_service, "vector_service", None)
        if not vector_service:
            logger.warning("[PreferenceExtractor] VectorService non disponible, sauvegarde impossible")
            return 0

        import os
        from datetime import datetime, timezone

        knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
        collection = vector_service.get_or_create_collection(knowledge_name)

        saved_count = 0
        timestamp_iso = datetime.now(timezone.utc).isoformat()

        for pref in preferences:
            try:
                # Format document texte (compatible _fetch_active_preferences)
                # Format: "topic: preference_text"
                doc_text = f"{pref.topic}: {pref.text}" if pref.topic else pref.text

                # Métadonnées enrichies pour filtrage et tri
                metadata = {
                    "user_id": user_id,
                    "type": pref.type,  # "preference" | "intent" | "constraint"
                    "topic": pref.topic or "general",
                    "confidence": float(pref.confidence),
                    "created_at": timestamp_iso,
                    "thread_id": thread_id,
                    "session_id": session_id,
                    "source": "preference_extractor_v1.2",
                    "sentiment": getattr(pref, "sentiment", "neutral"),
                    "timeframe": getattr(pref, "timeframe", ""),
                }

                # Générer ID unique basé sur contenu + user
                content_hash = hashlib.md5(
                    f"{user_id}:{pref.type}:{pref.text}".encode("utf-8")
                ).hexdigest()[:12]
                doc_id = f"pref_{user_id[:8]}_{content_hash}"

                # Ajouter au ChromaDB
                vector_service.add_documents(
                    collection=collection,
                    documents=[doc_text],
                    metadatas=[metadata],
                    ids=[doc_id]
                )

                saved_count += 1
                logger.debug(
                    f"[PreferenceExtractor] Saved preference {doc_id}: "
                    f"{pref.type} (confidence={pref.confidence:.2f})"
                )

            except Exception as doc_error:
                logger.warning(
                    f"[PreferenceExtractor] Failed to save preference '{pref.text[:30]}...': {doc_error}"
                )
                # Continue avec les autres préférences

        return saved_count

    async def analyze_session_async(
        self,
        session_id: str,
        force: bool = False,
        callback: Optional[Callable[..., Any]] = None
    ) -> None:
        """
        Version asynchrone non-bloquante de analyze_session_for_concepts.
        Enqueue tâche dans MemoryTaskQueue.

        Args:
            session_id: ID session à analyser
            force: Forcer nouvelle analyse
            callback: Fonction appelée avec résultat
        """
        from backend.features.memory.task_queue import get_memory_queue

        queue = get_memory_queue()
        await queue.enqueue(
            task_type="analyze",
            payload={"session_id": session_id, "force": force},
            callback=callback
        )

        logger.info(f"Analyse session {session_id} enqueued (async)")
