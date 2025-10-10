# incremental_consolidation.py - Consolidation incrémentale de la mémoire
import logging
import asyncio
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class IncrementalConsolidator:
    """
    Consolidation incrémentale de la mémoire (micro-consolidations fréquentes).

    Au lieu de tout consolider en fin de session, cette classe permet de:
    - Déclencher une micro-consolidation tous les N messages (10-15)
    - Traiter seulement les derniers messages (fenêtre glissante)
    - Extraire concepts de façon incrémentale et les merger avec STM existante
    """

    def __init__(
        self,
        memory_analyzer,
        vector_service,
        db_manager,
        consolidation_threshold: int = 10,
    ):
        self.memory_analyzer = memory_analyzer
        self.vector_service = vector_service
        self.db_manager = db_manager
        self.consolidation_threshold = consolidation_threshold
        self.message_counters: Dict[str, int] = {}
        # 🔒 Lock pour accès concurrent aux compteurs (Bug #3 fix)
        self._counter_lock = asyncio.Lock()

    async def increment_counter(self, key: str) -> int:
        """Incrémente compteur de manière thread-safe"""
        async with self._counter_lock:
            self.message_counters[key] = self.message_counters.get(key, 0) + 1
            return self.message_counters[key]

    async def get_counter(self, key: str) -> int:
        """Récupère compteur de manière thread-safe"""
        async with self._counter_lock:
            return self.message_counters.get(key, 0)

    async def reset_counter(self, key: str):
        """Remet compteur à zéro de manière thread-safe"""
        async with self._counter_lock:
            self.message_counters[key] = 0

    async def check_and_consolidate(
        self, session_id: str, thread_id: str, recent_messages: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if consolidation threshold reached and trigger micro-consolidation.

        Args:
            session_id: Session identifier
            thread_id: Thread identifier
            recent_messages: Recent messages from the conversation

        Returns:
            Consolidation result dict if triggered, None otherwise
        """
        # Increment message counter for this thread (thread-safe)
        counter_key = f"{session_id}:{thread_id}"
        counter_value = await self.increment_counter(counter_key)

        # Check if threshold reached
        if counter_value < self.consolidation_threshold:
            return None

        # Reset counter (thread-safe)
        await self.reset_counter(counter_key)

        logger.info(
            f"Seuil de consolidation atteint pour {counter_key}. "
            f"Déclenchement micro-consolidation..."
        )

        # Trigger micro-consolidation
        result = await self._micro_consolidate(
            session_id=session_id, thread_id=thread_id, recent_messages=recent_messages
        )

        return result

    async def _micro_consolidate(
        self, session_id: str, thread_id: str, recent_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform micro-consolidation on recent messages only (sliding window).

        Steps:
        1. Extract concepts from last 10 messages (fenêtre glissante)
        2. Merge new concepts with existing STM
        3. Update session metadata with enriched summary
        """
        try:
            # 1. Get sliding window (last 10 messages)
            window = recent_messages[-10:] if len(recent_messages) > 10 else recent_messages

            if len(window) < 3:  # Not enough messages to consolidate
                return {"status": "skipped", "reason": "insufficient_messages"}

            # 2. Analyze recent window for concepts
            analysis = await self.memory_analyzer.analyze_history(
                session_id=session_id, history=window
            )

            if not analysis:
                return {"status": "skipped", "reason": "analysis_failed"}

            new_summary = analysis.get("summary", "")
            new_concepts = analysis.get("concepts", [])
            new_entities = analysis.get("entities", [])

            # 3. Merge with existing STM
            chat_service = self.memory_analyzer.chat_service
            if chat_service:
                session_manager = getattr(chat_service, "session_manager", None)
                if session_manager:
                    try:
                        sess = session_manager.get_session(session_id)
                        meta = getattr(sess, "metadata", {}) or {}

                        existing_summary = meta.get("summary", "")
                        existing_concepts = meta.get("concepts", [])
                        existing_entities = meta.get("entities", [])

                        # Merge concepts (dedupe)
                        merged_concepts = list(
                            set(existing_concepts + new_concepts)
                        )[:10]  # Keep top 10
                        merged_entities = list(
                            set(existing_entities + new_entities)
                        )[:10]

                        # Enrich summary (append recent context)
                        if existing_summary:
                            enriched_summary = (
                                f"{existing_summary} [Récent: {new_summary}]"
                            )
                        else:
                            enriched_summary = new_summary

                        # Update session metadata
                        session_manager.update_session_metadata(
                            session_id,
                            summary=enriched_summary,
                            concepts=merged_concepts,
                            entities=merged_entities,
                        )

                        logger.info(
                            f"Micro-consolidation réussie pour {session_id}: "
                            f"{len(new_concepts)} nouveaux concepts, "
                            f"{len(merged_concepts)} total"
                        )

                        return {
                            "status": "success",
                            "new_concepts_count": len(new_concepts),
                            "total_concepts_count": len(merged_concepts),
                            "window_size": len(window),
                        }

                    except Exception as e:
                        logger.warning(
                            f"Erreur lors du merge STM pour {session_id}: {e}"
                        )

            # Fallback: return analysis without merge
            return {
                "status": "partial",
                "new_concepts": new_concepts,
                "new_summary": new_summary,
            }

        except Exception as e:
            logger.error(f"Micro-consolidation échouée pour {session_id}: {e}")
            return {"status": "error", "error": str(e)}
