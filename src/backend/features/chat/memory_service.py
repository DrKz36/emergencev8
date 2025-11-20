# src/backend/features/chat/memory_service.py
"""
MemoryService - Consolidated Memory & Temporal History

Extracted from ChatService to handle all memory-related operations:
- Consolidated memory retrieval with caching
- Concept grouping by theme
- Temporal history building
- Conversation timeline generation

✅ Phase 2 of ChatService decomposition
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional
from collections import Counter
from datetime import datetime

from backend.features.memory.vector_service import VectorService
from backend.core.session_manager import SessionManager
from backend.features.chat.rag_metrics import RAGMetrics
from backend.core.database import queries

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Handles consolidated memory retrieval, concept grouping, and temporal history.
    
    🎯 Responsibilities:
    - Retrieve consolidated concepts from ChromaDB with caching
    - Group concepts by semantic similarity
    - Build temporal history context for temporal queries
    - Generate conversation timelines
    """
    
    def __init__(
        self,
        vector_service: VectorService,
        session_manager: SessionManager,
        rag_cache: Any,  # RAGCache from ChatService
        memory_query_tool: Optional[Any] = None,
        metrics: Optional[RAGMetrics] = None
    ):
        """
        Initialize MemoryService.
        
        Args:
            vector_service: VectorService for embeddings & search
            session_manager: SessionManager for database access
            rag_cache: RAGCache instance for caching
            memory_query_tool: Optional MemoryQueryTool for timeline
           metrics: Optional RAGMetrics for telemetry
        """
        self.vector_service = vector_service
        self.session_manager = session_manager
        self.rag_cache = rag_cache
        self.memory_query_tool = memory_query_tool
        self.metrics = metrics or RAGMetrics()
        
        # Collection
        self._knowledge_collection = None
        
        logger.info("MemoryService initialized")
    
    async def get_consolidated_memory(
        self, user_id: str, query_text: str, n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Récupère les concepts consolidés depuis le cache ou ChromaDB.

        Utilise le RAGCache pour éviter des recherches répétées sur ChromaDB.
        Cache hit rate cible: 30-40% selon Phase 3 specs.

        Args:
            user_id: ID de l'utilisateur
            query_text: Texte de la requête pour recherche sémantique
            n_results: Nombre maximum de résultats à retourner

        Returns:
            Liste de dicts avec timestamp, content, type
        """
        import time

        # Vérifier si la collection knowledge existe
        if self._knowledge_collection is None:
            knowledge_name = os.getenv(
                "EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge"
            )
            self._knowledge_collection = self.vector_service.get_or_create_collection(
                knowledge_name
            )

        # Utiliser le cache RAG avec une clé spécifique pour la mémoire consolidée
        cache_query = f"__CONSOLIDATED_MEMORY__:{query_text}"
        where_filter = {"user_id": user_id} if user_id else None

        # Tenter de récupérer depuis le cache
        start_time = time.time()
        cached_result = self.rag_cache.get(
            cache_query,
            where_filter,
            agent_id="memory_consolidation",
            selected_doc_ids=None,
        )

        if cached_result:
            # Cache HIT
            duration = time.time() - start_time
            logger.debug(
                f"[TemporalCache] HIT: {duration * 1000:.1f}ms pour '{query_text[:50]}'"
            )

            consolidated_entries = cached_result.get("doc_hits", [])

            # Métriques
            from backend.features.chat import rag_metrics
            rag_metrics.record_cache_hit()

            return consolidated_entries

        # Cache MISS - Recherche dans ChromaDB
        logger.debug(
            f"[TemporalCache] MISS: Recherche ChromaDB pour '{query_text[:50]}'"
        )

        try:
            search_start = time.time()
            if self._knowledge_collection is None:
                raise RuntimeError("Knowledge collection should be initialized")
            
            results = self._knowledge_collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filter,
                include=["metadatas", "documents"],
            )
            search_duration = time.time() - search_start

            consolidated_entries = []

            if results and results.get("metadatas") and results["metadatas"][0]:
                metadatas = results["metadatas"][0]
                documents = results.get("documents", [[]])[0]

                for i, metadata in enumerate(metadatas):
                    # Extraire timestamp des concepts consolidés
                    timestamp = (
                        metadata.get("timestamp")
                        or metadata.get("created_at")
                        or metadata.get("first_mentioned_at")
                    )

                    # Extraire contenu
                    if i < len(documents) and documents[i]:
                        content = documents[i]
                    else:
                        content = (
                            metadata.get("concept_text")
                            or metadata.get("summary")
                            or metadata.get("value")
                            or ""
                        )

                    concept_type = metadata.get("type", "concept")

                    if timestamp and content:
                        consolidated_entries.append(
                            {
                                "timestamp": timestamp,
                                "content": content[:80]
                                + ("..." if len(content) > 80 else ""),
                                "type": concept_type,
                                "metadata": metadata,
                            }
                        )
                        logger.debug(
                            f"[TemporalHistory] Concept consolidé trouvé: {concept_type} @ {timestamp[:10]}"
                        )

            # Stocker dans le cache
            self.rag_cache.set(
                cache_query,
                where_filter,
                agent_id="memory_consolidation",
                doc_hits=consolidated_entries,
                rag_sources=[],
                selected_doc_ids=None,
            )

            # Métriques
            from backend.features.chat import rag_metrics
            rag_metrics.record_cache_miss()
            rag_metrics.record_temporal_search_duration(search_duration)
            rag_metrics.record_temporal_concepts_found(len(consolidated_entries))
            
            logger.info(
                f"[TemporalCache] ChromaDB search: {search_duration * 1000:.0f}ms, "
                f"{len(consolidated_entries)} concepts trouvés"
            )

            return consolidated_entries

        except Exception as e:
            logger.error(
                f"[TemporalHistory] Erreur recherche concepts consolidés: {e}",
                exc_info=True,
            )
            return []
    
    async def group_concepts_by_theme(
        self, consolidated_entries: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groupe les concepts consolidés par similarité sémantique.

        Phase 3 - Priorité 3: Groupement thématique pour contexte plus concis.

        Args:
            consolidated_entries: Liste de concepts avec timestamp, content, type

        Returns:
            Dict[group_id, List[concepts]] - Concepts regroupés par thème

        Algorithme:
        1. Si < 3 concepts → pas de groupement
        2. Générer embeddings pour chaque concept
        3. Calculer matrice de similarité cosine
        4. Regrouper concepts avec similarité > 0.7
        5. Assigner concepts orphelins au groupe le plus proche (si > 0.5)
        """
        # Pas de groupement si peu de concepts
        if len(consolidated_entries) < 3:
            return {"ungrouped": consolidated_entries}

        try:
            # Extraire les contenus pour embedding
            contents = [entry["content"] for entry in consolidated_entries]

            # Générer embeddings
            embeddings = self.vector_service.model.encode(contents)

            # Calculer similarité cosine
            from sklearn.metrics.pairwise import cosine_similarity

            similarity_matrix = cosine_similarity(embeddings)

            # Clustering simple avec seuil
            groups = {}
            assigned = set()
            group_id = 0

            for i in range(len(consolidated_entries)):
                if i in assigned:
                    continue

                # Créer nouveau groupe
                group_key = f"theme_{group_id}"
                groups[group_key] = [consolidated_entries[i]]
                assigned.add(i)

                # Ajouter concepts similaires (cosine > 0.7)
                for j in range(i + 1, len(consolidated_entries)):
                    if j not in assigned and similarity_matrix[i][j] > 0.7:
                        groups[group_key].append(consolidated_entries[j])
                        assigned.add(j)

                group_id += 1

            logger.info(
                f"[ThematicGrouping] {len(consolidated_entries)} concepts → {len(groups)} groupes"
            )

            return groups

        except Exception as e:
            logger.warning(f"[ThematicGrouping] Erreur clustering: {e}", exc_info=True)
            return {"ungrouped": consolidated_entries}
    
    def extract_group_title(self, concepts: List[Dict[str, Any]]) -> str:
        """
        Extrait un titre représentatif pour un groupe de concepts.

        Phase 3 - Priorité 3: Extraction de titres intelligents.

        Args:
            concepts: Liste de concepts du groupe

        Returns:
            Titre formaté (ex: "Infrastructure & Déploiement")
        """
        import re

        # Limite maximale de caractères
        max_chars = 20000
        processed_chars = 0

        # Stop words
        stop_words = {
            "être", "avoir", "faire", "dire", "aller", "voir", "savoir",
            "pouvoir", "vouloir", "venir", "devoir", "prendre", "donner",
            "utilisateur", "demande", "question", "discussion", "parler",
            "the", "and", "for", "that", "with", "this", "from",
            "they", "have", "will", "what", "been", "more", "when", "there",
        }

        pattern = re.compile(r"\b[a-zA-ZÀ-ÿ]{4,}\b")
        word_freq: Counter[str] = Counter()

        for concept in concepts:
            if processed_chars >= max_chars:
                break

            content = concept.get("content", "")
            if not content:
                continue

            remaining = max_chars - processed_chars
            snippet = content[:remaining]
            processed_chars += len(snippet)

            for match in pattern.finditer(snippet.lower()):
                word = match.group(0)
                if len(word) > 3 and word not in stop_words:
                    word_freq[word] += 1

        # Prendre les 2-3 mots les plus fréquents
        if not word_freq:
            return "Discussion"

        top_words = word_freq.most_common(3)

        # Formater en titre (capitaliser)
        title_words = [w[0].capitalize() for w in top_words[:2]]

        # Joindre avec &
        if len(title_words) == 2:
            return f"{title_words[0]} & {title_words[1]}"
        elif len(title_words) == 1:
            return title_words[0]
        else:
            return "Discussion"
    
    async def build_temporal_history_context(
        self,
        thread_id: str,
        session_id: str,
        user_id: str,
        agent_id: Optional[str] = None,
        limit: int = 20,
        last_user_message: str = "",
    ) -> str:
        """
        Construit un contexte historique enrichi avec timestamps pour répondre
        aux questions temporelles (quand, quel jour, quelle heure).

        Récupère les messages du thread ET les concepts consolidés pertinents
        pour fournir un contexte temporel complet.

        🆕 Pour questions exhaustives (tous, toutes, résumer tout), cherche dans
        TOUTES les conversations archivées.
        """
        try:
            # Détection questions exhaustives
            is_exhaustive_query = bool(
                re.search(
                    r"\b(tous|toutes|tout|exhaustif|complet|résumer tout|toutes?\s+(nos|mes)\s+conversations?)\b",
                    last_user_message.lower(),
                )
            )

            # Messages du thread (skip si exhaustive)
            messages = []
            if not is_exhaustive_query:
                messages = await queries.get_messages(
                    self.session_manager.db_manager,
                    thread_id,
                    session_id=session_id,
                    user_id=user_id,
                    limit=limit,
                )

            lines = []

            # Concepts consolidés avec cache
            n_results = 50 if is_exhaustive_query else min(5, max(3, len(messages) // 4)) if messages else 5

            consolidated_entries = []
            if last_user_message and user_id:
                consolidated_entries = await self.get_consolidated_memory(
                    user_id=user_id, query_text=last_user_message, n_results=n_results
                )

            # Groupement thématique
            grouped_concepts = {}
            if len(consolidated_entries) >= 3:
                grouped_concepts = await self.group_concepts_by_theme(
                    consolidated_entries
                )
                logger.info(f"[ThematicGrouping] {len(grouped_concepts)} groupes créés")
            elif consolidated_entries:
                grouped_concepts = {"ungrouped": consolidated_entries}

            # Timeline via MemoryQueryTool
            timeline_added = False
            if self.memory_query_tool and user_id:
                try:
                    max_topics_per_period = 6 if is_exhaustive_query else 3
                    timeline_limit = max(limit * 2, 20)

                    if is_exhaustive_query:
                        logger.info(
                            f"[ExhaustiveQuery] Question globale détectée - limite={timeline_limit}"
                        )

                    timeline = await self.memory_query_tool.get_conversation_timeline(
                        user_id=user_id, limit=timeline_limit, agent_id=agent_id
                    )
                    
                    period_labels = {
                        "this_week": "**Cette semaine:**",
                        "last_week": "**Semaine dernière:**",
                        "this_month": "**Ce mois-ci:**",
                        "older": "**Plus ancien:**",
                    }
                    
                    timeline_section: List[str] = []
                    for period in ("this_week", "last_week", "this_month", "older"):
                        topics = timeline.get(period, [])
                        if not topics:
                            continue
                        timeline_section.append(period_labels[period])
                        count = 0
                        for topic in topics:
                            timeline_section.append(f"- {topic.format_natural_fr()}")
                            count += 1
                            if count >= max_topics_per_period:
                                break
                        timeline_section.append("")
                    
                    formatted_timeline = "\n".join(
                        line for line in timeline_section if line.strip()
                    )
                    
                    if formatted_timeline:
                        lines.append("**Synthèse chronologique consolidée :**")
                        lines.append(formatted_timeline)
                        timeline_added = True

                except Exception as e:
                    logger.warning(
                        f"[TemporalHistory] Erreur timeline: {e}", exc_info=True
                    )

            # Formatage groupes thématiques
            if grouped_concepts and not timeline_added:
                for group_name, group_concepts in grouped_concepts.items():
                    if group_name == "ungrouped":
                        title = "**Concepts pertinents:**"
                    else:
                        title = f"**{self.extract_group_title(group_concepts)}:**"

                    lines.append(title)
                    for concept in group_concepts[:5]:  # Max 5 par groupe
                        timestamp = concept.get("timestamp", "")
                        content = concept.get("content", "")
                        if timestamp and content:
                            lines.append(f"- {timestamp[:10]}: {content}")
                    lines.append("")

            # Messages du thread (si pas exhaustive)
            if messages and not is_exhaustive_query:
                lines.append("**Messages récents (horodatés):**")
                for msg in messages[-10:]:  # Max 10 derniers
                    created_at = msg.get("created_at", "")
                    role = msg.get("role", "")
                    content = msg.get("content", "")[:100]
                    
                    if created_at:
                        ts = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        formatted_time = ts.strftime("%d/%m à %H:%M")
                        lines.append(f"- {formatted_time} [{role}]: {content}...")

            return "\n".join(lines) if lines else ""

        except Exception as e:
            logger.error(
                f"[TemporalHistory] Erreur construction: {e}", exc_info=True
            )
            return ""
