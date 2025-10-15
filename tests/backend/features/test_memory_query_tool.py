# tests/backend/features/test_memory_query_tool.py
# V1.0 - Tests unitaires pour MemoryQueryTool
#
# Coverage:
# - list_discussed_topics() avec différents timeframes
# - get_topic_details() avec recherche vectorielle
# - get_conversation_timeline() avec groupement temporel
# - Format français naturel

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from backend.features.memory.memory_query_tool import (
    MemoryQueryTool,
    TopicSummary
)


@pytest.fixture
def mock_vector_service():
    """Mock VectorService avec collection ChromaDB."""
    service = MagicMock()

    # Mock collection
    collection = MagicMock()
    collection.name = "emergence_knowledge"
    service.get_or_create_collection.return_value = collection

    return service


@pytest.fixture
def memory_tool(mock_vector_service):
    """Instance MemoryQueryTool avec VectorService mocké."""
    return MemoryQueryTool(mock_vector_service)


@pytest.fixture
def sample_concepts_data():
    """Données de test représentant des concepts stockés dans ChromaDB."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    return {
        "ids": ["concept_1", "concept_2", "concept_3"],
        "documents": [
            "CI/CD pipeline",
            "Docker containerisation",
            "Kubernetes deployment"
        ],
        "metadatas": [
            {
                "type": "concept",
                "concept_text": "CI/CD pipeline",
                "first_mentioned_at": week_ago.isoformat(),
                "last_mentioned_at": now.isoformat(),
                "mention_count": 3,
                "thread_ids_json": json.dumps(["thread_abc", "thread_def", "thread_ghi"]),
                "summary": "Automatisation déploiement GitHub Actions",
                "vitality": 0.85,
                "user_id": "user123"
            },
            {
                "type": "concept",
                "concept_text": "Docker containerisation",
                "first_mentioned_at": (now - timedelta(days=2)).isoformat(),
                "last_mentioned_at": (now - timedelta(days=2)).isoformat(),
                "mention_count": 1,
                "thread_ids_json": json.dumps(["thread_xyz"]),
                "summary": "Optimisation images Docker",
                "vitality": 0.90,
                "user_id": "user123"
            },
            {
                "type": "concept",
                "concept_text": "Kubernetes deployment",
                "first_mentioned_at": month_ago.isoformat(),
                "last_mentioned_at": (now - timedelta(days=20)).isoformat(),
                "mention_count": 2,
                "thread_ids_json": json.dumps(["thread_klm", "thread_nop"]),
                "summary": "",
                "vitality": 0.65,
                "user_id": "user123"
            }
        ]
    }


class TestTopicSummary:
    """Tests pour la classe TopicSummary."""

    def test_topic_summary_initialization(self):
        """Test initialisation TopicSummary avec données complètes."""
        data = {
            "topic": "CI/CD pipeline",
            "first_date": "2025-10-02T14:32:00+00:00",
            "last_date": "2025-10-08T09:15:00+00:00",
            "mention_count": 3,
            "thread_ids": ["abc", "def"],
            "summary": "Automatisation déploiement",
            "vitality": 0.85
        }

        topic = TopicSummary(data)

        assert topic.topic == "CI/CD pipeline"
        assert topic.first_date == "2025-10-02T14:32:00+00:00"
        assert topic.last_date == "2025-10-08T09:15:00+00:00"
        assert topic.mention_count == 3
        assert len(topic.thread_ids) == 2
        assert topic.summary == "Automatisation déploiement"
        assert topic.vitality == 0.85

    def test_topic_summary_to_dict(self):
        """Test conversion TopicSummary -> dict."""
        data = {
            "topic": "Docker",
            "first_date": "2025-10-08T14:00:00+00:00",
            "last_date": "2025-10-08T14:00:00+00:00",
            "mention_count": 1,
            "thread_ids": ["xyz"],
            "summary": "Optimisation",
            "vitality": 0.90
        }

        topic = TopicSummary(data)
        result = topic.to_dict()

        assert result["topic"] == "Docker"
        assert result["thread_count"] == 1
        assert "thread_ids" in result

    def test_format_natural_fr_single_date(self):
        """Test format français avec une seule date."""
        data = {
            "topic": "Docker",
            "first_date": "2025-10-08T14:32:00+00:00",
            "last_date": "2025-10-08T14:32:00+00:00",
            "mention_count": 1,
            "thread_ids": ["xyz"],
            "summary": "",
            "vitality": 0.90
        }

        topic = TopicSummary(data)
        formatted = topic.format_natural_fr()

        assert "Docker" in formatted
        assert "8 oct 14h32" in formatted
        assert "1 conversation" in formatted
        assert "conversations" not in formatted  # Singulier

    def test_format_natural_fr_multiple_dates(self):
        """Test format français avec dates multiples."""
        data = {
            "topic": "CI/CD pipeline",
            "first_date": "2025-10-02T14:32:00+00:00",
            "last_date": "2025-10-08T09:15:00+00:00",
            "mention_count": 3,
            "thread_ids": ["abc", "def", "ghi"],
            "summary": "Automatisation déploiement",
            "vitality": 0.85
        }

        topic = TopicSummary(data)
        formatted = topic.format_natural_fr()

        assert "CI/CD pipeline" in formatted
        assert "2 oct 14h32" in formatted
        assert "8 oct 09h15" in formatted
        assert "3 conversations" in formatted
        assert "Automatisation déploiement" in formatted

    def test_format_date_fr_with_time(self):
        """Test format date français avec heure."""
        formatted = TopicSummary._format_date_fr("2025-10-08T14:32:00+00:00")
        assert formatted == "8 oct 14h32"

    def test_format_date_fr_without_time(self):
        """Test format date français sans heure (minuit)."""
        formatted = TopicSummary._format_date_fr("2025-10-08T00:00:00+00:00")
        assert formatted == "8 oct"

    def test_format_date_fr_invalid(self):
        """Test format date avec ISO invalide (fallback)."""
        formatted = TopicSummary._format_date_fr("invalid-date")
        assert formatted == "invalid-da"  # Fallback: [:10]


class TestMemoryQueryTool:
    """Tests pour MemoryQueryTool."""

    @pytest.mark.asyncio
    async def test_list_discussed_topics_timeframe_week(
        self, memory_tool, sample_concepts_data
    ):
        """Test list_discussed_topics avec timeframe='week'."""
        # Mock collection.get() pour retourner concepts
        memory_tool.knowledge_collection.get = MagicMock(
            return_value=sample_concepts_data
        )

        topics = await memory_tool.list_discussed_topics(
            user_id="user123",
            timeframe="week"
        )

        # Vérifier appel collection.get avec bon filtre
        memory_tool.knowledge_collection.get.assert_called_once()
        call_args = memory_tool.knowledge_collection.get.call_args

        where_filter = call_args.kwargs["where"]
        assert "$and" in where_filter
        assert {"user_id": "user123"} in where_filter["$and"]
        assert {"type": "concept"} in where_filter["$and"]

        # Vérifier résultats
        assert len(topics) == 3
        assert all(isinstance(t, TopicSummary) for t in topics)

        # Vérifier tri par date (plus récent en premier)
        assert topics[0].topic == "CI/CD pipeline"  # last_date = now
        assert topics[1].topic == "Docker containerisation"  # 2 jours
        assert topics[2].topic == "Kubernetes deployment"  # 20 jours

    @pytest.mark.asyncio
    async def test_list_discussed_topics_timeframe_all(
        self, memory_tool, sample_concepts_data
    ):
        """Test list_discussed_topics avec timeframe='all'."""
        memory_tool.knowledge_collection.get = MagicMock(
            return_value=sample_concepts_data
        )

        topics = await memory_tool.list_discussed_topics(
            user_id="user123",
            timeframe="all"
        )

        # Vérifier filtre ne contient PAS de critère temporel
        call_args = memory_tool.knowledge_collection.get.call_args
        where_filter = call_args.kwargs["where"]

        # Doit contenir user_id et type, mais PAS last_mentioned_at
        conditions = where_filter.get("$and", [where_filter])
        temporal_filters = [
            c for c in conditions
            if "last_mentioned_at" in c
        ]
        assert len(temporal_filters) == 0

        assert len(topics) == 3

    @pytest.mark.asyncio
    async def test_list_discussed_topics_min_mention_count(
        self, memory_tool, sample_concepts_data
    ):
        """Test filtre min_mention_count."""
        memory_tool.knowledge_collection.get = MagicMock(
            return_value=sample_concepts_data
        )

        topics = await memory_tool.list_discussed_topics(
            user_id="user123",
            timeframe="all",
            min_mention_count=2
        )

        # Vérifier filtre contient mention_count >= 2
        call_args = memory_tool.knowledge_collection.get.call_args
        where_filter = call_args.kwargs["where"]

        conditions = where_filter.get("$and", [])
        mention_filters = [
            c for c in conditions
            if "mention_count" in c
        ]
        assert len(mention_filters) == 1
        assert mention_filters[0] == {"mention_count": {"$gte": 2}}

    @pytest.mark.asyncio
    async def test_list_discussed_topics_empty_result(self, memory_tool):
        """Test comportement avec résultat vide."""
        memory_tool.knowledge_collection.get = MagicMock(
            return_value={"ids": [], "documents": [], "metadatas": []}
        )

        topics = await memory_tool.list_discussed_topics(
            user_id="user123",
            timeframe="week"
        )

        assert topics == []

    @pytest.mark.asyncio
    async def test_list_discussed_topics_no_user_id(self, memory_tool):
        """Test validation user_id requis."""
        topics = await memory_tool.list_discussed_topics(
            user_id="",
            timeframe="week"
        )

        assert topics == []

    @pytest.mark.asyncio
    async def test_get_topic_details_found(self, memory_tool):
        """Test get_topic_details avec résultat trouvé."""
        # Mock vector_service.query pour recherche sémantique
        mock_result = [
            {
                "id": "concept_1",
                "text": "CI/CD pipeline",
                "metadata": {
                    "concept_text": "CI/CD pipeline",
                    "first_mentioned_at": "2025-10-02T14:32:00+00:00",
                    "last_mentioned_at": "2025-10-08T09:15:00+00:00",
                    "mention_count": 3,
                    "thread_ids_json": json.dumps(["abc", "def", "ghi"]),
                    "summary": "Automatisation déploiement",
                    "vitality": 0.85
                },
                "distance": 0.15  # Similarity score
            }
        ]

        memory_tool.vector_service.query = MagicMock(return_value=mock_result)

        details = await memory_tool.get_topic_details(
            user_id="user123",
            topic_query="CI/CD"
        )

        # Vérifier appel query avec bon filtre
        memory_tool.vector_service.query.assert_called_once()
        call_args = memory_tool.vector_service.query.call_args
        assert call_args.kwargs["query_text"] == "CI/CD"

        # Vérifier résultat
        assert details is not None
        assert details["topic"] == "CI/CD pipeline"
        assert details["mention_count"] == 3
        assert len(details["thread_ids"]) == 3
        assert details["similarity_score"] == 0.15
        assert "conversations" in details

    @pytest.mark.asyncio
    async def test_get_topic_details_not_found(self, memory_tool):
        """Test get_topic_details sans résultat."""
        memory_tool.vector_service.query = MagicMock(return_value=[])

        details = await memory_tool.get_topic_details(
            user_id="user123",
            topic_query="unknown topic"
        )

        assert details is None

    @pytest.mark.asyncio
    async def test_get_conversation_timeline(self, memory_tool, sample_concepts_data):
        """Test get_conversation_timeline avec groupement temporel."""
        memory_tool.knowledge_collection.get = MagicMock(
            return_value=sample_concepts_data
        )

        timeline = await memory_tool.get_conversation_timeline(
            user_id="user123",
            limit=100
        )

        # Vérifier structure timeline
        assert "this_week" in timeline
        assert "last_week" in timeline
        assert "this_month" in timeline
        assert "older" in timeline

        # Vérifier groupement (basé sur fixtures)
        # - CI/CD: now → this_week
        # - Docker: 2 jours → this_week
        # - Kubernetes: 20 jours → this_month
        assert len(timeline["this_week"]) == 2
        assert len(timeline["this_month"]) == 1

        # Vérifier tri par date dans chaque période
        this_week = timeline["this_week"]
        assert this_week[0].topic == "CI/CD pipeline"  # Plus récent
        assert this_week[1].topic == "Docker containerisation"

    def test_format_timeline_natural_fr(self, memory_tool):
        """Test format timeline en français naturel."""
        # Créer timeline mock
        now = datetime.now(timezone.utc)

        timeline = {
            "this_week": [
                TopicSummary({
                    "topic": "CI/CD",
                    "first_date": (now - timedelta(days=3)).isoformat(),
                    "last_date": now.isoformat(),
                    "mention_count": 3,
                    "thread_ids": ["abc", "def"],
                    "summary": "Automatisation",
                    "vitality": 0.85
                })
            ],
            "last_week": [],
            "this_month": [
                TopicSummary({
                    "topic": "Docker",
                    "first_date": (now - timedelta(days=20)).isoformat(),
                    "last_date": (now - timedelta(days=20)).isoformat(),
                    "mention_count": 1,
                    "thread_ids": ["xyz"],
                    "summary": "",
                    "vitality": 0.90
                })
            ],
            "older": []
        }

        formatted = memory_tool.format_timeline_natural_fr(timeline)

        # Vérifier présence headers
        assert "### Historique des sujets abordés" in formatted
        assert "**Cette semaine:**" in formatted
        assert "**Ce mois-ci:**" in formatted

        # Vérifier absence sections vides
        assert "**Semaine dernière:**" not in formatted
        assert "**Plus ancien:**" not in formatted

        # Vérifier contenu
        assert "CI/CD" in formatted
        assert "Docker" in formatted
        assert "3 conversations" in formatted

    def test_format_timeline_natural_fr_empty(self, memory_tool):
        """Test format timeline vide."""
        formatted = memory_tool.format_timeline_natural_fr({})
        assert formatted == "Aucun sujet abordé récemment."

    def test_compute_timeframe_cutoff_today(self):
        """Test calcul cutoff pour timeframe='today'."""
        cutoff = MemoryQueryTool._compute_timeframe_cutoff("today")

        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=1)

        # Vérifier cutoff est environ 24h en arrière (tolérance 1 minute)
        assert abs((cutoff - expected).total_seconds()) < 60

    def test_compute_timeframe_cutoff_week(self):
        """Test calcul cutoff pour timeframe='week'."""
        cutoff = MemoryQueryTool._compute_timeframe_cutoff("week")

        now = datetime.now(timezone.utc)
        expected = now - timedelta(weeks=1)

        assert abs((cutoff - expected).total_seconds()) < 60

    def test_compute_timeframe_cutoff_month(self):
        """Test calcul cutoff pour timeframe='month'."""
        cutoff = MemoryQueryTool._compute_timeframe_cutoff("month")

        now = datetime.now(timezone.utc)
        expected = now - timedelta(days=30)

        assert abs((cutoff - expected).total_seconds()) < 60

    def test_compute_timeframe_cutoff_invalid(self):
        """Test comportement avec timeframe invalide."""
        cutoff = MemoryQueryTool._compute_timeframe_cutoff("invalid")
        assert cutoff is None


class TestMemoryQueryToolIntegration:
    """Tests d'intégration (nécessitent ChromaDB réel)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow_real_chromadb(self, tmp_path):
        """
        Test workflow complet avec ChromaDB réel.

        Nécessite:
        - ChromaDB installé
        - VectorService fonctionnel

        Skip si dépendances manquantes.
        """
        pytest.importorskip("chromadb")
        pytest.importorskip("sentence_transformers")

        from backend.features.memory.vector_service import VectorService

        # Créer VectorService réel avec persist_dir temporaire
        vector_service = VectorService(
            persist_directory=str(tmp_path / "chroma"),
            embed_model_name="all-MiniLM-L6-v2",
            auto_reset_on_schema_error=True
        )

        # Créer MemoryQueryTool
        tool = MemoryQueryTool(vector_service)

        # Insérer concepts de test
        now = datetime.now(timezone.utc)
        test_concepts = [
            {
                "id": "test_concept_1",
                "text": "CI/CD pipeline automatisation",
                "metadata": {
                    "type": "concept",
                    "concept_text": "CI/CD pipeline",
                    "first_mentioned_at": (now - timedelta(days=5)).isoformat(),
                    "last_mentioned_at": now.isoformat(),
                    "mention_count": 3,
                    "thread_ids_json": json.dumps(["abc", "def"]),
                    "summary": "Automatisation déploiement",
                    "vitality": 0.85,
                    "user_id": "test_user"
                }
            },
            {
                "id": "test_concept_2",
                "text": "Docker containerisation optimisation",
                "metadata": {
                    "type": "concept",
                    "concept_text": "Docker",
                    "first_mentioned_at": (now - timedelta(days=2)).isoformat(),
                    "last_mentioned_at": (now - timedelta(days=2)).isoformat(),
                    "mention_count": 1,
                    "thread_ids_json": json.dumps(["xyz"]),
                    "summary": "Optimisation images",
                    "vitality": 0.90,
                    "user_id": "test_user"
                }
            }
        ]

        vector_service.add_items(
            collection=tool.knowledge_collection,
            items=test_concepts
        )

        # Test 1: list_discussed_topics
        topics = await tool.list_discussed_topics(
            user_id="test_user",
            timeframe="week"
        )

        assert len(topics) == 2
        assert topics[0].topic == "CI/CD pipeline"
        assert topics[0].mention_count == 3

        # Test 2: get_topic_details
        details = await tool.get_topic_details(
            user_id="test_user",
            topic_query="CI/CD"
        )

        assert details is not None
        assert "CI/CD" in details["topic"]
        assert details["mention_count"] == 3

        # Test 3: get_conversation_timeline
        timeline = await tool.get_conversation_timeline(
            user_id="test_user"
        )

        assert len(timeline["this_week"]) == 2
        assert timeline["this_week"][0].topic == "CI/CD pipeline"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
