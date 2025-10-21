# src/backend/features/memory/concept_recall.py
# V1.1 - Concept Recall Tracker with Prometheus metrics

import json
import logging
import os
import time
from typing import Dict, Any, List
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.features.memory.vector_service import VectorService
from backend.features.memory.concept_recall_metrics import concept_recall_metrics

logger = logging.getLogger(__name__)


class ConceptRecallTracker:
    """
    Détecte et trace les récurrences conceptuelles dans l'historique utilisateur.

    Fonctionnalités :
    - Recherche vectorielle sur concepts existants
    - Enrichissement métadonnées (first_mentioned_at, mention_count, thread_ids)
    - Émission événements ws:concept_recall pour UI
    """

    COLLECTION_NAME = "emergence_knowledge"
    SIMILARITY_THRESHOLD = 0.75  # Seuil de détection (cosine similarity)
    MAX_RECALLS_PER_MESSAGE = 3  # Limite de rappels par message pour éviter spam

    def __init__(
        self,
        db_manager: DatabaseManager,
        vector_service: VectorService,
        connection_manager=None,
    ):
        self.db = db_manager
        self.vector_service = vector_service
        self.connection_manager = connection_manager
        self.collection = vector_service.get_or_create_collection(self.COLLECTION_NAME) if vector_service else None
        self.metrics = concept_recall_metrics
        logger.info("[ConceptRecallTracker] Initialisé avec métriques Prometheus")

    async def detect_recurring_concepts(
        self,
        message_text: str,
        user_id: str,
        thread_id: str,
        message_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Détecte si le message contient des concepts déjà abordés.

        Returns:
            Liste de récurrences : [
                {
                    "concept_text": "CI/CD pipeline",
                    "first_mentioned_at": "2025-10-02T14:32:00+00:00",
                    "last_mentioned_at": "2025-10-03T09:15:00+00:00",
                    "mention_count": 3,
                    "thread_ids": ["thread_xyz", "thread_abc"],
                    "similarity_score": 0.87,
                    "vector_id": "abc123"
                }
            ]
        """
        if not message_text or not user_id:
            return []

        try:
            # Start timing for metrics
            start_time = time.time()

            # 1. Recherche vectorielle pondérée sur concepts existants de l'utilisateur
            # Utilise query_weighted() pour bénéficier du scoring temporel
            vector_search_start = time.time()
            results = self.vector_service.query_weighted(
                collection=self.collection,
                query_text=message_text,
                n_results=10,  # Top 10 concepts similaires
                where_filter={
                    "$and": [
                        {"user_id": user_id},
                        {"type": "concept"}
                    ]
                }
            )
            vector_search_duration = time.time() - vector_search_start
            self.metrics.record_vector_search(vector_search_duration)

            if not results:
                return []

            # 2. Filtrer par similarité et exclure thread actuel (éviter auto-détection)
            # Note: query_weighted() retourne déjà weighted_score au lieu de distance
            recalls = []
            for res in results:
                meta = res.get("metadata", {})
                # Récupérer le weighted_score calculé par query_weighted()
                score = res.get("weighted_score", 0.0)

                # Seuil de similarité (weighted_score combine cosine_sim + temporal + freq)
                if score < self.SIMILARITY_THRESHOLD:
                    continue

                # Exclure mentions du thread actuel (on cherche l'historique passé)
                thread_ids_json = meta.get("thread_ids_json", "[]")
                thread_ids = json.loads(thread_ids_json) if thread_ids_json else []
                if len(thread_ids) == 1 and thread_ids[0] == thread_id:
                    continue  # Concept mentionné uniquement dans le thread actuel

                recall = {
                    "concept_text": meta.get("concept_text", ""),
                    "first_mentioned_at": meta.get("first_mentioned_at") or meta.get("created_at"),
                    "last_mentioned_at": meta.get("last_mentioned_at") or meta.get("created_at"),
                    "mention_count": meta.get("mention_count", 1),
                    "thread_ids": [tid for tid in thread_ids if tid != thread_id],  # Exclure thread actuel
                    "similarity_score": round(score, 4),
                    "vector_id": res.get("id", ""),
                }

                # Ne garder que si au moins un thread passé existe
                if recall["thread_ids"]:
                    recalls.append(recall)

                if len(recalls) >= self.MAX_RECALLS_PER_MESSAGE:
                    break

            # 3. Mettre à jour les métadonnées pour cette nouvelle mention
            if recalls:
                await self._update_mention_metadata(
                    recalls=recalls,
                    current_thread_id=thread_id,
                    current_message_id=message_id,
                    session_id=session_id,
                )

            # 4. Émettre événement WebSocket si récurrences détectées
            if recalls and self.connection_manager:
                await self._emit_concept_recall_event(
                    session_id=session_id,
                    recalls=recalls,
                )

            # 5. Record metrics for each detection
            detection_duration = time.time() - start_time
            for recall in recalls:
                self.metrics.record_detection(
                    user_id=user_id,
                    similarity_score=recall["similarity_score"],
                    thread_count=len(recall["thread_ids"]),
                    duration_seconds=detection_duration
                )

            return recalls

        except Exception as e:
            logger.error(f"[ConceptRecallTracker] Erreur détection récurrences : {e}", exc_info=True)
            return []

    async def _update_mention_metadata(
        self,
        recalls: List[Dict[str, Any]],
        current_thread_id: str,
        current_message_id: str,
        session_id: str,
    ) -> None:
        """
        Met à jour les métadonnées vectorielles pour enregistrer la nouvelle mention.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        update_start = time.time()

        for recall in recalls:
            vector_id = recall.get("vector_id")
            if not vector_id:
                continue

            try:
                # Récupérer métadonnées actuelles
                if not self.collection:
                    continue
                existing = self.collection.get(ids=[vector_id], include=["metadatas"])
                if not existing or not existing.get("metadatas"):
                    continue

                meta = existing["metadatas"][0] if isinstance(existing["metadatas"], list) else existing["metadatas"]

                # Incrémenter mention_count
                mention_count = int(meta.get("mention_count", 1)) + 1

                # Ajouter thread_id si pas déjà présent
                thread_ids_json = meta.get("thread_ids_json", "[]")
                thread_ids = json.loads(thread_ids_json) if thread_ids_json else []
                if current_thread_id not in thread_ids:
                    thread_ids.append(current_thread_id)

                # Mettre à jour
                updated_meta = dict(meta)
                updated_meta["mention_count"] = mention_count
                updated_meta["last_mentioned_at"] = now_iso
                updated_meta["thread_ids_json"] = json.dumps(thread_ids)

                # Boost vitality (concept réutilisé = plus pertinent)
                vitality = float(meta.get("vitality", 0.5))
                updated_meta["vitality"] = min(1.0, vitality + 0.1)

                self.vector_service.update_metadatas(
                    collection=self.collection,
                    ids=[vector_id],
                    metadatas=[updated_meta]
                )

                logger.debug(f"[ConceptRecallTracker] Concept {vector_id} mis à jour : {mention_count} mentions")

                # Record concept reuse metric
                user_id = meta.get("user_id", "")
                if user_id:
                    self.metrics.record_concept_reuse(user_id, mention_count)

            except Exception as e:
                logger.warning(f"[ConceptRecallTracker] Impossible de mettre à jour {vector_id} : {e}")

        # Record metadata update duration
        update_duration = time.time() - update_start
        self.metrics.record_metadata_update(update_duration)

    async def _emit_concept_recall_event(
        self,
        session_id: str,
        recalls: List[Dict[str, Any]],
    ) -> None:
        """
        Émet un événement WebSocket ws:concept_recall pour affichage UI.
        """
        # Phase 2 : Émission désactivée par défaut
        if not os.getenv("CONCEPT_RECALL_EMIT_EVENTS", "false").lower() == "true":
            logger.debug("[ConceptRecallTracker] Émission ws:concept_recall désactivée (CONCEPT_RECALL_EMIT_EVENTS=false)")
            return

        if not self.connection_manager:
            return

        payload = {
            "variant": "concept_recall",
            "recalls": [
                {
                    "concept": r["concept_text"],
                    "first_date": r["first_mentioned_at"],
                    "last_date": r["last_mentioned_at"],
                    "count": r["mention_count"],
                    "thread_count": len(r["thread_ids"]),
                    "similarity": r["similarity_score"],
                }
                for r in recalls[:self.MAX_RECALLS_PER_MESSAGE]
            ]
        }

        try:
            await self.connection_manager.send_personal_message(
                {"type": "ws:concept_recall", "payload": payload},
                session_id
            )
            logger.info(f"[ConceptRecallTracker] Événement ws:concept_recall émis : {len(recalls)} récurrences")

            # Record event emission metric (extract user_id from first recall)
            if recalls and len(recalls) > 0:
                # Try to get user_id from session or recall metadata
                # For now, we'll need to pass user_id from caller
                pass

        except Exception as e:
            logger.debug(f"[ConceptRecallTracker] Impossible d'émettre ws:concept_recall : {e}")

    async def query_concept_history(
        self,
        concept_text: str,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Recherche explicite d'un concept dans l'historique (pour requête utilisateur).

        Usage:
            USER: "Est-ce qu'on a déjà parlé de containerisation ?"
            AGENT: appelle query_concept_history("containerisation", user_id)

        Returns:
            [
                {
                    "concept_text": "Docker containerisation",
                    "first_mentioned_at": "2025-09-28T10:15:00+00:00",
                    "thread_ids": ["thread_abc", "thread_def"],
                    "mention_count": 2,
                }
            ]
        """
        try:
            # Utilise query_weighted() pour bénéficier du scoring temporel
            results = self.vector_service.query_weighted(
                collection=self.collection,
                query_text=concept_text,
                n_results=limit,
                where_filter={
                    "$and": [
                        {"user_id": user_id},
                        {"type": "concept"}
                    ]
                }
            )

            history = []
            for res in results:
                meta = res.get("metadata", {})
                # Récupérer weighted_score calculé par query_weighted()
                score = res.get("weighted_score", 0.0)

                if score >= 0.6:  # Seuil plus permissif pour requête explicite
                    # Decode thread_ids from JSON
                    thread_ids_json = meta.get("thread_ids_json", "[]")
                    thread_ids = json.loads(thread_ids_json) if thread_ids_json else []

                    history.append({
                        "concept_text": meta.get("concept_text", ""),
                        "first_mentioned_at": meta.get("first_mentioned_at") or meta.get("created_at"),
                        "last_mentioned_at": meta.get("last_mentioned_at") or meta.get("created_at"),
                        "thread_ids": thread_ids,
                        "mention_count": meta.get("mention_count", 1),
                        "similarity_score": round(score, 4),
                    })

            return history

        except Exception as e:
            logger.error(f"[ConceptRecallTracker] Erreur query_concept_history : {e}", exc_info=True)
            return []
