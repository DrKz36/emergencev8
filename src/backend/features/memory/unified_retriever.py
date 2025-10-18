# src/backend/features/memory/unified_retriever.py
# V1.0 - UnifiedMemoryRetriever - Sprint 3 Memory Refactoring
#
# Objectif: Couche unifiée de rappel mémoire agent
# Récupère contexte depuis:
#   1. STM (session active - historique messages)
#   2. LTM (concepts/préférences vectoriels ChromaDB)
#   3. Archives (conversations passées pertinentes)
#
# Date création: 2025-10-18
# Roadmap: MEMORY_REFACTORING_ROADMAP.md Sprint 3

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Prometheus metrics pour monitoring
try:
    from prometheus_client import Counter, Histogram, REGISTRY

    def _get_unified_retriever_counter() -> Counter:
        try:
            return Counter(
                'unified_retriever_calls_total',
                'Nombre appels UnifiedRetriever',
                ['agent_id', 'source'],  # source: stm, ltm, archives
                registry=REGISTRY
            )
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(
                'unified_retriever_calls_total'
            )
            if existing is None:
                raise
            return existing

    def _get_unified_retriever_duration() -> Histogram:
        try:
            return Histogram(
                'unified_retriever_duration_seconds',
                'Durée récupération contexte',
                ['source'],
                registry=REGISTRY
            )
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(
                'unified_retriever_duration_seconds'
            )
            if existing is None:
                raise
            return existing

    UNIFIED_RETRIEVER_CALLS = _get_unified_retriever_counter()
    UNIFIED_RETRIEVER_DURATION = _get_unified_retriever_duration()
    PROMETHEUS_AVAILABLE = True

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.debug("[UnifiedRetriever] Prometheus client non disponible")


class MemoryContext:
    """
    Contexte mémoire unifié pour injection dans prompt agent.

    Contient 3 sources:
    - STM: Historique session active
    - LTM: Concepts/préférences vectoriels
    - Archives: Conversations passées pertinentes
    """

    def __init__(self):
        self.stm_history: List[Dict] = []
        self.ltm_concepts: List[Dict] = []
        self.ltm_preferences: List[Dict] = []
        self.archived_conversations: List[Dict] = []

    def to_prompt_sections(self) -> List[tuple[str, str]]:
        """
        Formatte pour injection dans prompt système.

        Returns:
            Liste de tuples (titre_section, contenu_markdown)
        """
        sections = []

        # Préférences actives (prioritaire - affiché en premier)
        if self.ltm_preferences:
            prefs_text = "\n".join([
                f"- {p['text']}" for p in self.ltm_preferences[:5]
            ])
            sections.append(("Préférences actives", prefs_text))

        # Conversations passées pertinentes
        if self.archived_conversations:
            conv_text = "\n".join([
                f"- {c['date']}: {c['summary']}"
                for c in self.archived_conversations[:3]
            ])
            sections.append(("Conversations passées pertinentes", conv_text))

        # Concepts pertinents
        if self.ltm_concepts:
            concepts_text = "\n".join([
                f"- {c['text']}" for c in self.ltm_concepts[:5]
            ])
            sections.append(("Connaissances pertinentes", concepts_text))

        return sections

    def to_markdown(self) -> str:
        """
        Formate en markdown pour injection prompt.

        Returns:
            Markdown formaté avec sections H3
        """
        sections = self.to_prompt_sections()
        parts = []
        for title, body in sections:
            if body.strip():
                parts.append(f"### {title}\n{body.strip()}")
        return "\n\n".join(parts)


class UnifiedMemoryRetriever:
    """
    Récupérateur unifié de mémoire agent.

    Centralise accès à toutes les sources mémoire:
    - STM: SessionManager (RAM)
    - LTM: VectorService (ChromaDB)
    - Archives: DatabaseManager (SQLite) + recherche fulltext
    """

    def __init__(
        self,
        session_manager,
        vector_service,
        db_manager,
        memory_query_tool=None
    ):
        """
        Initialize UnifiedMemoryRetriever.

        Args:
            session_manager: SessionManager instance (STM)
            vector_service: VectorService instance (LTM)
            db_manager: DatabaseManager instance (DB queries)
            memory_query_tool: MemoryQueryTool instance (optionnel)
        """
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.db = db_manager
        self.memory_query_tool = memory_query_tool

        logger.info(
            "[UnifiedMemoryRetriever] Initialized with STM + LTM + Archives support"
        )

    async def retrieve_context(
        self,
        user_id: str,
        agent_id: str,
        session_id: str,
        current_query: str,
        *,
        include_stm: bool = True,
        include_ltm: bool = True,
        include_archives: bool = True,
        top_k_concepts: int = 5,
        top_k_archives: int = 3
    ) -> MemoryContext:
        """
        Récupère contexte unifié pour agent.

        Args:
            user_id: Identifiant utilisateur
            agent_id: Identifiant agent (anima/neo/nexus)
            session_id: Session WebSocket active
            current_query: Requête utilisateur actuelle
            include_stm: Inclure STM (défaut: True)
            include_ltm: Inclure LTM concepts (défaut: True)
            include_archives: Inclure archives (défaut: True)
            top_k_concepts: Nombre concepts LTM (défaut: 5)
            top_k_archives: Nombre conversations archivées (défaut: 3)

        Returns:
            MemoryContext avec sections remplies
        """
        import time

        start_time = time.time()
        context = MemoryContext()

        # 1. STM: Historique session active
        if include_stm:
            stm_start = time.time()
            context.stm_history = await self._get_stm_context(session_id)
            if PROMETHEUS_AVAILABLE:
                UNIFIED_RETRIEVER_DURATION.labels(source='stm').observe(time.time() - stm_start)
                UNIFIED_RETRIEVER_CALLS.labels(agent_id=agent_id, source='stm').inc()

        # 2. LTM: Préférences + concepts pertinents
        if include_ltm:
            ltm_start = time.time()
            ltm_results = await self._get_ltm_context(
                user_id, agent_id, current_query, top_k=top_k_concepts
            )
            context.ltm_preferences = ltm_results['preferences']
            context.ltm_concepts = ltm_results['concepts']
            if PROMETHEUS_AVAILABLE:
                UNIFIED_RETRIEVER_DURATION.labels(source='ltm').observe(time.time() - ltm_start)
                UNIFIED_RETRIEVER_CALLS.labels(agent_id=agent_id, source='ltm').inc()

        # 3. 🆕 Archives: Conversations passées pertinentes
        if include_archives:
            archives_start = time.time()
            context.archived_conversations = await self._get_archived_context(
                user_id, agent_id, current_query, limit=top_k_archives
            )
            if PROMETHEUS_AVAILABLE:
                UNIFIED_RETRIEVER_DURATION.labels(source='archives').observe(time.time() - archives_start)
                UNIFIED_RETRIEVER_CALLS.labels(agent_id=agent_id, source='archives').inc()

        total_duration = time.time() - start_time

        if PROMETHEUS_AVAILABLE:
            UNIFIED_RETRIEVER_DURATION.labels(source='total').observe(total_duration)

        logger.info(
            f"[UnifiedRetriever] Context récupéré en {total_duration:.3f}s: "
            f"STM={len(context.stm_history)} msgs, "
            f"LTM={len(context.ltm_concepts)} concepts, "
            f"Prefs={len(context.ltm_preferences)}, "
            f"Archives={len(context.archived_conversations)} convs"
        )

        return context

    async def _get_stm_context(self, session_id: str) -> List[Dict]:
        """
        Récupère historique session active depuis SessionManager.

        Args:
            session_id: ID session WebSocket

        Returns:
            Liste messages (role, content, timestamp)
        """
        try:
            # Try get_full_history first
            if hasattr(self.session_manager, 'get_full_history'):
                return self.session_manager.get_full_history(session_id)

            # Fallback: get_session puis extraire history
            session = self.session_manager.get_session(session_id)
            if session and hasattr(session, 'history'):
                return session.history

            return []
        except Exception as e:
            logger.warning(f"STM retrieval failed for session {session_id}: {e}")
            return []

    async def _get_ltm_context(
        self, user_id: str, agent_id: str, query: str, top_k: int
    ) -> Dict[str, List[Dict]]:
        """
        Récupère préférences + concepts depuis ChromaDB.

        Args:
            user_id: User ID
            agent_id: Agent ID
            query: Requête utilisateur pour recherche vectorielle
            top_k: Nombre de concepts à retourner

        Returns:
            Dict avec 'preferences' et 'concepts'
        """
        try:
            collection = self.vector_service.get_or_create_collection(
                "emergence_knowledge"
            )

            # Préférences actives (confidence >= 0.6)
            try:
                prefs_result = collection.get(
                    where={
                        "$and": [
                            {"user_id": user_id},
                            {"agent_id": agent_id},
                            {"type": "preference"},
                            {"confidence": {"$gte": 0.6}}
                        ]
                    },
                    include=["documents", "metadatas"]
                )

                preferences = [
                    {
                        'text': doc,
                        'confidence': meta.get('confidence', 0.5),
                        'topic': meta.get('topic', 'general')
                    }
                    for doc, meta in zip(
                        prefs_result.get('documents', []),
                        prefs_result.get('metadatas', [])
                    )
                ]
            except Exception as e:
                logger.warning(f"Preferences retrieval failed: {e}")
                preferences = []

            # Concepts pertinents (requête vectorielle)
            try:
                concepts_results = self.vector_service.query(
                    collection=collection,
                    query_text=query,
                    n_results=top_k,
                    where_filter={
                        "$and": [
                            {"user_id": user_id},
                            {"agent_id": agent_id},
                            {"type": "concept"}
                        ]
                    }
                )

                concepts = [
                    {
                        'text': r.get('text', ''),
                        'score': r.get('score', 0),
                        'metadata': r.get('metadata', {})
                    }
                    for r in (concepts_results or [])
                    if r.get('text', '').strip()
                ]
            except Exception as e:
                logger.warning(f"Concepts retrieval failed: {e}")
                concepts = []

            return {
                'preferences': preferences,
                'concepts': concepts
            }

        except Exception as e:
            logger.error(f"LTM retrieval failed: {e}", exc_info=True)
            return {'preferences': [], 'concepts': []}

    async def _get_archived_context(
        self, user_id: str, agent_id: str, query: str, limit: int
    ) -> List[Dict]:
        """
        🆕 Récupère conversations archivées pertinentes.

        Stratégie:
        1. Recherche threads archivés consolidés en LTM (déjà dans concepts)
        2. Recherche fulltext dans messages de threads archivés

        Args:
            user_id: User ID
            agent_id: Agent ID (pour filtrage futur)
            query: Requête utilisateur
            limit: Nombre max de conversations à retourner

        Returns:
            Liste conversations archivées pertinentes
        """
        try:
            # Import local pour éviter circular imports
            from backend.core.database import queries

            # Récupérer threads archivés de l'utilisateur
            archived_threads = await queries.get_threads(
                self.db,
                session_id=None,
                user_id=user_id,
                archived_only=True,
                limit=limit * 3  # Fetch plus pour filtrer
            )

            if not archived_threads:
                logger.debug(f"No archived threads found for user {user_id}")
                return []

            # Recherche simple: threads avec title ou messages contenant query keywords
            # TODO: Améliorer avec recherche fulltext SQLite FTS5
            query_lower = query.lower()
            query_keywords = set(query_lower.split())

            scored_threads = []

            for thread in archived_threads:
                thread_id = thread.get('id')
                title = thread.get('title', '').lower()

                # Score basique: mots clés dans title
                score = 0
                for keyword in query_keywords:
                    if len(keyword) > 2 and keyword in title:
                        score += 1

                # Si consolidated_at existe, bonus (thread consolidé)
                if thread.get('consolidated_at'):
                    score += 0.5

                if score > 0:
                    scored_threads.append({
                        'thread': thread,
                        'score': score
                    })

            # Trier par score
            scored_threads.sort(key=lambda x: x['score'], reverse=True)

            # Formater résultats
            results = []
            for item in scored_threads[:limit]:
                thread = item['thread']
                results.append({
                    'thread_id': thread.get('id'),
                    'title': thread.get('title', 'Sans titre'),
                    'date': self._format_date(thread.get('archived_at')),
                    'summary': thread.get('title', '')[:200],
                    'relevance': item['score']
                })

            logger.info(
                f"[UnifiedRetriever] Found {len(results)} relevant archived conversations "
                f"(scored {len(scored_threads)} total)"
            )

            return results

        except Exception as e:
            logger.error(f"Archive retrieval failed: {e}", exc_info=True)
            return []

    @staticmethod
    def _format_date(iso_date: Optional[str]) -> str:
        """
        Formatte date ISO en français naturel.

        Args:
            iso_date: Date ISO format

        Returns:
            Date formatée "DD mois" ou date ISO si parsing échoue
        """
        if not iso_date:
            return ""
        try:
            dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
            months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                     "juil", "août", "sept", "oct", "nov", "déc"]
            month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
            return f"{dt.day} {month}"
        except Exception:
            return iso_date[:10]
