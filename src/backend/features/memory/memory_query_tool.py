# src/backend/features/memory/memory_query_tool.py
# V1.0 - Outil de requête mémoire pour agents (Phase 1 Sprint 1)
#
# Objectif: Exposer les métadonnées temporelles stockées dans ChromaDB
#          aux agents pour répondre aux questions sur l'historique.
#
# Fonctionnalités:
# - list_discussed_topics(): Liste sujets avec dates/heures précises
# - get_topic_details(): Détails approfondis sur un sujet spécifique
# - get_conversation_timeline(): Vue chronologique complète

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from backend.features.memory.vector_service import VectorService

logger = logging.getLogger(__name__)


class TopicSummary:
    """Résumé d'un sujet abordé avec métadonnées temporelles."""

    def __init__(self, data: Dict[str, Any]):
        self.topic = data.get("topic", "")
        self.first_date = data.get("first_date", "")
        self.last_date = data.get("last_date", "")
        self.mention_count = data.get("mention_count", 1)
        self.thread_ids = data.get("thread_ids", [])
        self.summary = data.get("summary", "")
        self.vitality = data.get("vitality", 1.0)
        self.agent_id = data.get("agent_id")  # 🆕 Pour filtrage permissif

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "first_date": self.first_date,
            "last_date": self.last_date,
            "mention_count": self.mention_count,
            "thread_count": len(self.thread_ids),
            "thread_ids": self.thread_ids,
            "summary": self.summary,
            "vitality": self.vitality,
        }

    def format_natural_fr(self) -> str:
        """
        Formate le sujet en français naturel.

        Exemple: "CI/CD pipeline (5 oct 14h32, 8 oct 09h15) - 3 conversations"
        """
        first = self._format_date_fr(self.first_date)
        last = self._format_date_fr(self.last_date)

        if first == last or not last:
            date_str = f"({first})"
        else:
            date_str = f"({first}, {last})"

        conv_str = f"{self.mention_count} conversation{'s' if self.mention_count > 1 else ''}"

        if self.summary and self.summary != self.topic:
            return f"{self.topic} {date_str} - {conv_str}\n  └─ {self.summary}"
        else:
            return f"{self.topic} {date_str} - {conv_str}"

    @staticmethod
    def _format_date_fr(iso_date: str) -> str:
        """Formate date ISO en français naturel: '5 oct 14h32'"""
        if not iso_date:
            return ""

        try:
            dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
            months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                      "juil", "août", "sept", "oct", "nov", "déc"]
            month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)

            # Inclure heure si != 00h00
            if dt.hour != 0 or dt.minute != 0:
                return f"{dt.day} {month} {dt.hour:02d}h{dt.minute:02d}"
            else:
                return f"{dt.day} {month}"
        except Exception as e:
            logger.warning(f"Format date failed for '{iso_date}': {e}")
            return iso_date[:10]  # Fallback: YYYY-MM-DD


class MemoryQueryTool:
    """
    Outil de requête mémoire pour agents.

    Expose les métadonnées temporelles stockées dans ChromaDB de manière
    exploitable par les LLMs pour répondre aux questions sur l'historique.

    Usage:
        tool = MemoryQueryTool(vector_service)
        topics = await tool.list_discussed_topics(user_id, timeframe="week")
    """

    KNOWLEDGE_COLLECTION_NAME = "emergence_knowledge"

    def __init__(self, vector_service: VectorService):
        self.vector_service = vector_service
        self.knowledge_collection = vector_service.get_or_create_collection(
            self.KNOWLEDGE_COLLECTION_NAME
        )
        logger.info("[MemoryQueryTool] Initialisé avec collection '%s'", self.KNOWLEDGE_COLLECTION_NAME)

    async def list_discussed_topics(
        self,
        user_id: str,
        timeframe: Optional[str] = None,
        limit: int = 50,
        min_mention_count: int = 1,
        agent_id: Optional[str] = None,
    ) -> List[TopicSummary]:
        """
        Récupère la liste des sujets abordés avec dates et fréquences.

        Args:
            user_id: Identifiant utilisateur
            timeframe: Fenêtre temporelle ("today", "week", "month", "all", None)
            limit: Nombre maximum de résultats
            min_mention_count: Filtre mention_count minimum (défaut: 1)

        Returns:
            Liste de TopicSummary triés par date (plus récent en premier)

        Exemple:
            topics = await tool.list_discussed_topics("user123", timeframe="week")
            for topic in topics:
                print(topic.format_natural_fr())
            # Output:
            # CI/CD pipeline (5 oct 14h32, 8 oct 09h15) - 3 conversations
            #   └─ Automatisation déploiement GitHub Actions
        """
        if not user_id:
            logger.warning("[MemoryQueryTool] list_discussed_topics appelé sans user_id")
            return []

        if limit is not None and limit <= 0:
            logger.info(
                "[MemoryQueryTool] limit<=0 détecté pour user '%s' — aucun sujet retourné",
                user_id[:8],
            )
            return []

        try:
            # 1. Calculer éventuelle date de coupure (filtrage appliqué côté Python)
            cutoff_date: Optional[datetime] = None
            if timeframe and timeframe != "all":
                cutoff_date = self._compute_timeframe_cutoff(timeframe)

            # 2. Construire filtre base (user/type/mention_count/agent_id)
            where_filter = self._build_timeframe_filter(
                user_id,
                None,  # désactive le filtre temporel côté Chroma (comparaison numérique non supportée)
                min_mention_count,
                agent_id=agent_id,
            )

            # 3. Récupérer concepts depuis Chroma.
            fetch_limit = None
            if limit is not None:
                fetch_limit = max(limit * 3, limit)
            result = self.knowledge_collection.get(
                where=where_filter,
                include=["documents", "metadatas"],
                limit=fetch_limit,
            )

            if not result or not result.get("ids"):
                logger.info("[MemoryQueryTool] Aucun concept trouvé pour user '%s' (timeframe=%s)",
                           user_id[:8], timeframe)
                return []

            # 4. Parser et construire TopicSummary
            topics = self._parse_concepts_to_topics(result)

            # 4b. 🆕 FIX: Filtrage PERMISSIF par agent_id côté Python
            # Inclut les concepts avec l'agent_id demandé OU sans agent_id (legacy)
            if agent_id:
                normalized_agent_id = agent_id.lower()
                topics = [
                    topic
                    for topic in topics
                    if self._topic_matches_agent(topic, normalized_agent_id)
                ]
                logger.debug(
                    f"[MemoryQueryTool] Filtré {len(topics)} topics pour agent '{agent_id}' (inclut legacy sans agent_id)"
                )

            # 5. Filtrer par fenetre temporelle si demandée
            if cutoff_date:
                topics = [
                    topic
                    for topic in topics
                    if self._date_is_on_or_after(topic.last_date or topic.first_date, cutoff_date)
                ]

            # 6. Trier par last_mentioned_at (plus récent en premier)
            topics.sort(key=lambda t: t.last_date or t.first_date or "", reverse=True)

            if limit is not None:
                topics = topics[:limit]

            logger.info(
                "[MemoryQueryTool] Récupéré %d sujets pour user '%s' (timeframe=%s, limit=%s)",
                len(topics), user_id[:8], timeframe, limit
            )

            return topics

        except Exception as e:
            logger.error(
                "[MemoryQueryTool] Erreur list_discussed_topics: %s",
                e,
                exc_info=True
            )
            return []

    def _build_timeframe_filter(
        self,
        user_id: str,
        timeframe: Optional[str],
        min_mention_count: int = 1,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Construit filtre ChromaDB avec critères temporels et utilisateur.

        Args:
            user_id: Identifiant utilisateur
            timeframe: "today" | "week" | "month" | "all" | None
            min_mention_count: Filtre mention_count minimum
            agent_id: Filtrer par agent (anima, neo, nexus) - PERMISSIF: inclut aussi concepts sans agent_id (legacy)

        Returns:
            Filtre compatible ChromaDB where clause
        """
        base_conditions = [
            {"user_id": user_id},
            {"type": "concept"}
        ]

        # 🆕 FIX: Filtre agent_id PERMISSIF pour inclure concepts legacy sans agent_id
        # Stratégie: Récupérer TOUS les concepts de l'utilisateur, puis filtrer côté Python
        # (ChromaDB ne supporte pas les requêtes OR complexes avec valeurs nulles)
        # On ne filtre PAS ici par agent_id, on le fera en post-processing dans list_discussed_topics
        # IMPORTANT: Ceci garantit la rétrocompatibilité avec les anciens concepts consolidés

        # Filtre mention_count si spécifié
        if min_mention_count > 1:
            base_conditions.append({"mention_count": {"$gte": min_mention_count}})

        # Filtre temporel sur last_mentioned_at
        if timeframe and timeframe != "all":
            cutoff_date = self._compute_timeframe_cutoff(timeframe)
            if cutoff_date:
                base_conditions.append({
                    "last_mentioned_at": {"$gte": cutoff_date.isoformat()}
                })

        # ChromaDB nécessite $and pour multiple conditions
        if len(base_conditions) == 1:
            return base_conditions[0]
        else:
            return {"$and": base_conditions}

    @staticmethod
    def _compute_timeframe_cutoff(timeframe: str) -> Optional[datetime]:
        """
        Calcule date de coupure pour un timeframe donné.

        Args:
            timeframe: "today" | "week" | "month"

        Returns:
            Datetime UTC ou None si timeframe invalide
        """
        now = datetime.now(timezone.utc)

        timeframe_map = {
            "today": timedelta(days=1),
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
        }

        delta = timeframe_map.get(timeframe.lower())
        if delta:
            return now - delta
        else:
            logger.warning("[MemoryQueryTool] Timeframe inconnu: '%s'", timeframe)
            return None

    @staticmethod
    def _date_is_on_or_after(date_str: Optional[str], cutoff: datetime) -> bool:
        """Retourne True si date ISO >= cutoff UTC."""
        if not date_str:
            return False

        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt >= cutoff
        except Exception:
            logger.debug("[MemoryQueryTool] Impossible de parser la date '%s'", date_str)
            return False

    @staticmethod
    def _topic_matches_agent(topic: TopicSummary, agent_id: str) -> bool:
        """
        Vérifie si un topic correspond à l'agent demandé.

        Stratégie PERMISSIVE pour rétrocompatibilité:
        - Retourne True si le topic a l'agent_id demandé
        - Retourne True si le topic n'a PAS d'agent_id (concepts legacy)
        - Retourne False sinon

        Args:
            topic: TopicSummary à vérifier
            agent_id: Agent ID normalisé (lowercase)

        Returns:
            True si le topic correspond
        """
        topic_agent_id = topic.agent_id

        # Cas 1: Pas d'agent_id dans le topic → concept legacy, on l'inclut
        if not topic_agent_id:
            return True

        # Cas 2: Agent ID correspond exactement
        if isinstance(topic_agent_id, str) and topic_agent_id.lower() == agent_id:
            return True

        # Cas 3: Ne correspond pas
        return False

    def _parse_concepts_to_topics(self, result: Dict[str, Any]) -> List[TopicSummary]:
        """
        Parse résultat ChromaDB en TopicSummary.

        Args:
            result: Résultat brut de collection.get()

        Returns:
            Liste de TopicSummary
        """
        topics = []

        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        # ChromaDB peut retourner nested lists [[...]] ou flat [...]
        # Normaliser
        if ids and isinstance(ids[0], list):
            ids = ids[0]
        if documents and isinstance(documents[0], list):
            documents = documents[0]
        if metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[0]

        for i, concept_id in enumerate(ids):
            try:
                doc = documents[i] if i < len(documents) else None
                meta = metadatas[i] if i < len(metadatas) else {}

                if not isinstance(meta, dict):
                    meta = {}

                # Extraire métadonnées
                concept_text = meta.get("concept_text") or doc or ""
                first_date = meta.get("first_mentioned_at") or meta.get("created_at") or ""
                last_date = meta.get("last_mentioned_at") or first_date
                mention_count = int(meta.get("mention_count", 1))
                vitality = float(meta.get("vitality", 1.0))

                # Parser thread_ids_json
                thread_ids_json = meta.get("thread_ids_json", "[]")
                try:
                    thread_ids = json.loads(thread_ids_json) if thread_ids_json else []
                except json.JSONDecodeError:
                    thread_ids = []

                # Résumé optionnel (Phase 2)
                summary = meta.get("summary", "")

                # 🆕 Agent ID pour filtrage permissif
                agent_id = meta.get("agent_id")

                topic_data = {
                    "topic": concept_text.strip(),
                    "first_date": first_date,
                    "last_date": last_date,
                    "mention_count": mention_count,
                    "thread_ids": thread_ids,
                    "summary": summary,
                    "vitality": vitality,
                    "agent_id": agent_id,
                }

                topics.append(TopicSummary(topic_data))

            except Exception as e:
                logger.warning(
                    "[MemoryQueryTool] Erreur parsing concept %s: %s",
                    concept_id, e
                )
                continue

        return topics

    async def get_topic_details(
        self,
        user_id: str,
        topic_query: str,
        limit: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère détails approfondis sur un sujet spécifique.

        Utilise recherche vectorielle pour matcher le topic_query.

        Args:
            user_id: Identifiant utilisateur
            topic_query: Requête sujet (ex: "CI/CD", "pipeline déploiement")
            limit: Nombre de résultats max (défaut: 5)

        Returns:
            Dictionnaire avec détails du sujet ou None si non trouvé

        Exemple:
            details = await tool.get_topic_details("user123", "CI/CD")
            # {
            #     "topic": "CI/CD pipeline",
            #     "first_mentioned_at": "2025-10-02T14:32:00+00:00",
            #     "last_mentioned_at": "2025-10-08T09:15:00+00:00",
            #     "mention_count": 3,
            #     "thread_ids": ["abc", "def"],
            #     "summary": "Automatisation déploiement GitHub Actions",
            #     "conversations": [
            #         {"thread_id": "abc", "date": "2025-10-02T14:32:00+00:00"},
            #         ...
            #     ]
            # }
        """
        if not user_id or not topic_query:
            return None

        try:
            # Recherche vectorielle sémantique
            results = self.vector_service.query(
                collection=self.knowledge_collection,
                query_text=topic_query,
                n_results=limit,
                where_filter={
                    "$and": [
                        {"user_id": user_id},
                        {"type": "concept"}
                    ]
                }
            )

            if not results:
                logger.info(
                    "[MemoryQueryTool] Aucun détail trouvé pour topic '%s' (user %s)",
                    topic_query, user_id[:8]
                )
                return None

            # Prendre le meilleur match (premier résultat)
            best_match = results[0]
            meta = best_match.get("metadata", {})

            # Parser thread_ids pour générer liste conversations
            thread_ids_json = meta.get("thread_ids_json", "[]")
            try:
                thread_ids = json.loads(thread_ids_json) if thread_ids_json else []
            except json.JSONDecodeError:
                thread_ids = []

            # TODO Phase 2: Enrichir avec détails des conversations
            # (récupérer messages depuis DB pour chaque thread_id)
            conversations = [
                {"thread_id": tid, "date": meta.get("last_mentioned_at", "")}
                for tid in thread_ids
            ]

            details = {
                "topic": meta.get("concept_text", topic_query),
                "first_mentioned_at": meta.get("first_mentioned_at") or meta.get("created_at"),
                "last_mentioned_at": meta.get("last_mentioned_at"),
                "mention_count": int(meta.get("mention_count", 1)),
                "thread_ids": thread_ids,
                "summary": meta.get("summary", ""),
                "vitality": float(meta.get("vitality", 1.0)),
                "similarity_score": best_match.get("distance", 0.0),
                "conversations": conversations,
            }

            logger.info(
                "[MemoryQueryTool] Détails récupérés pour topic '%s' (similarity=%.3f)",
                topic_query, details["similarity_score"]
            )

            return details

        except Exception as e:
            logger.error(
                "[MemoryQueryTool] Erreur get_topic_details: %s",
                e,
                exc_info=True
            )
            return None

    async def get_conversation_timeline(
        self,
        user_id: str,
        limit: int = 100,
        agent_id: Optional[str] = None
    ) -> Dict[str, List[TopicSummary]]:
        """
        Génère vue chronologique complète des conversations.

        Regroupe sujets par période:
        - "this_week": Cette semaine
        - "last_week": Semaine dernière
        - "this_month": Ce mois-ci
        - "older": Plus ancien

        Args:
            user_id: Identifiant utilisateur
            limit: Nombre max de concepts à récupérer

        Returns:
            Dictionnaire {période: [TopicSummary]}

        Exemple:
            timeline = await tool.get_conversation_timeline("user123")
            for period, topics in timeline.items():
                print(f"=== {period} ===")
                for topic in topics:
                    print(topic.format_natural_fr())
        """
        if not user_id:
            return {}

        try:
            # Récupérer TOUS les concepts (pas de filtre temporel)
            all_topics = await self.list_discussed_topics(
                user_id=user_id,
                timeframe="all",
                limit=limit,
                agent_id=agent_id
            )

            if not all_topics:
                return {}

            # Calculer cutoffs temporels
            now = datetime.now(timezone.utc)
            cutoff_this_week = now - timedelta(weeks=1)
            cutoff_last_week = now - timedelta(weeks=2)
            cutoff_this_month = now - timedelta(days=30)

            # Grouper par période
            timeline = {
                "this_week": [],
                "last_week": [],
                "this_month": [],
                "older": []
            }

            for topic in all_topics:
                try:
                    # Utiliser last_date pour classement
                    date_str = topic.last_date or topic.first_date
                    if not date_str:
                        timeline["older"].append(topic)
                        continue

                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

                    if dt >= cutoff_this_week:
                        timeline["this_week"].append(topic)
                    elif dt >= cutoff_last_week:
                        timeline["last_week"].append(topic)
                    elif dt >= cutoff_this_month:
                        timeline["this_month"].append(topic)
                    else:
                        timeline["older"].append(topic)

                except Exception as e:
                    logger.warning(
                        "[MemoryQueryTool] Erreur parsing date pour topic '%s': %s",
                        topic.topic, e
                    )
                    timeline["older"].append(topic)

            # Trier chaque période par date (plus récent en premier)
            for period in timeline:
                timeline[period].sort(
                    key=lambda t: t.last_date or t.first_date or "",
                    reverse=True
                )

            logger.info(
                "[MemoryQueryTool] Timeline générée pour user '%s': "
                "this_week=%d, last_week=%d, this_month=%d, older=%d",
                user_id[:8],
                len(timeline["this_week"]),
                len(timeline["last_week"]),
                len(timeline["this_month"]),
                len(timeline["older"])
            )

            return timeline

        except Exception as e:
            logger.error(
                "[MemoryQueryTool] Erreur get_conversation_timeline: %s",
                e,
                exc_info=True
            )
            return {}

    def format_timeline_natural_fr(self, timeline: Dict[str, List[TopicSummary]]) -> str:
        """
        Formate timeline en français naturel pour injection dans contexte LLM.

        Args:
            timeline: Résultat de get_conversation_timeline()

        Returns:
            Texte formaté markdown

        Exemple output:
            ### Historique des sujets abordés

            **Cette semaine:**
            - CI/CD pipeline (5 oct 14h32, 8 oct 09h15) - 3 conversations
              └─ Automatisation déploiement GitHub Actions
            - Docker (8 oct 14h32) - 1 conversation

            **Semaine dernière:**
            - Kubernetes (2 oct 16h45) - 2 conversations
        """
        # 🔥 FIX: Toujours retourner le header pour que Anima le voit (anti-hallucination)
        lines = ["### Historique des sujets abordés\n"]

        if not timeline:
            lines.append("\n*(Aucun sujet trouvé dans l'historique)*")
            return "\n".join(lines)

        period_labels = {
            "this_week": "**Cette semaine:**",
            "last_week": "**Semaine dernière:**",
            "this_month": "**Ce mois-ci:**",
            "older": "**Plus ancien:**"
        }

        for period in ["this_week", "last_week", "this_month", "older"]:
            topics = timeline.get(period, [])
            if topics:
                lines.append(f"\n{period_labels[period]}")
                for topic in topics:
                    lines.append(f"- {topic.format_natural_fr()}")

        return "\n".join(lines)
