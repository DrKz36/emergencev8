# tests/backend/features/memory/test_weighted_integration.py
# Tests d'intégration pour le système de retrieval pondéré complet
#
# Objectif: Tester l'intégration de query_weighted() dans:
# - ConceptRecallTracker
# - MemoryQueryTool
# - UnifiedRetriever
# - MemoryGarbageCollector
# - ScoreCache
# - Métriques Prometheus

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
import json


# ---------- Tests ConceptRecallTracker avec query_weighted ----------


@pytest.mark.asyncio
async def test_concept_recall_uses_weighted_query():
    """
    Vérifie que ConceptRecallTracker utilise bien query_weighted() au lieu de query().
    """
    from backend.features.memory.concept_recall import ConceptRecallTracker

    # Mock VectorService
    mock_vector_service = Mock()
    mock_collection = Mock()
    mock_collection.name = "emergence_knowledge"
    mock_vector_service.get_or_create_collection.return_value = mock_collection

    # Mock query_weighted() pour retourner résultats
    mock_vector_service.query_weighted.return_value = [
        {
            "id": "concept_1",
            "text": "CI/CD pipeline",
            "metadata": {
                "user_id": "user123",
                "type": "concept",
                "concept_text": "CI/CD pipeline",
                "thread_ids_json": json.dumps(["thread_old"]),
                "first_mentioned_at": "2025-10-01T10:00:00+00:00",
                "last_mentioned_at": "2025-10-10T10:00:00+00:00",
                "mention_count": 2,
            },
            "weighted_score": 0.85,
        }
    ]

    # Mock DB
    mock_db = Mock()

    # Initialiser tracker
    tracker = ConceptRecallTracker(
        db_manager=mock_db, vector_service=mock_vector_service, connection_manager=None
    )

    # Appeler detect_recurring_concepts
    recalls = await tracker.detect_recurring_concepts(
        message_text="Parlons de CI/CD",
        user_id="user123",
        thread_id="thread_new",
        message_id="msg_1",
        session_id="session_1",
    )

    # Vérifier que query_weighted() a été appelé (pas query())
    mock_vector_service.query_weighted.assert_called_once()
    mock_vector_service.query.assert_not_called()

    # Vérifier les rappels détectés
    assert len(recalls) == 1
    assert recalls[0]["concept_text"] == "CI/CD pipeline"
    assert recalls[0]["similarity_score"] == 0.85


@pytest.mark.asyncio
async def test_concept_recall_query_history_uses_weighted_query():
    """
    Vérifie que query_concept_history() utilise bien query_weighted().
    """
    from backend.features.memory.concept_recall import ConceptRecallTracker

    # Mock VectorService
    mock_vector_service = Mock()
    mock_collection = Mock()
    mock_collection.name = "emergence_knowledge"
    mock_vector_service.get_or_create_collection.return_value = mock_collection

    # Mock query_weighted()
    mock_vector_service.query_weighted.return_value = [
        {
            "id": "concept_docker",
            "text": "Docker containerisation",
            "metadata": {
                "concept_text": "Docker containerisation",
                "first_mentioned_at": "2025-09-28T10:15:00+00:00",
                "thread_ids_json": json.dumps(["thread_abc", "thread_def"]),
                "mention_count": 2,
            },
            "weighted_score": 0.75,
        }
    ]

    # Mock DB
    mock_db = Mock()

    # Initialiser tracker
    tracker = ConceptRecallTracker(
        db_manager=mock_db, vector_service=mock_vector_service, connection_manager=None
    )

    # Appeler query_concept_history
    history = await tracker.query_concept_history(
        concept_text="containerisation", user_id="user123", limit=10
    )

    # Vérifier que query_weighted() a été appelé
    mock_vector_service.query_weighted.assert_called_once()

    # Vérifier résultats
    assert len(history) == 1
    assert history[0]["concept_text"] == "Docker containerisation"
    assert history[0]["similarity_score"] == 0.75


# ---------- Tests MemoryQueryTool avec query_weighted ----------


@pytest.mark.asyncio
async def test_memory_query_tool_get_topic_details_uses_weighted_query():
    """
    Vérifie que MemoryQueryTool.get_topic_details() utilise bien query_weighted().
    """
    from backend.features.memory.memory_query_tool import MemoryQueryTool

    # Mock VectorService
    mock_vector_service = Mock()
    mock_collection = Mock()
    mock_collection.name = "emergence_knowledge"
    mock_vector_service.get_or_create_collection.return_value = mock_collection

    # Mock query_weighted()
    mock_vector_service.query_weighted.return_value = [
        {
            "id": "topic_cicd",
            "text": "CI/CD pipeline avec GitHub Actions",
            "metadata": {
                "concept_text": "CI/CD pipeline",
                "first_mentioned_at": "2025-10-02T14:32:00+00:00",
                "last_mentioned_at": "2025-10-08T09:15:00+00:00",
                "mention_count": 3,
                "thread_ids_json": json.dumps(["abc", "def"]),
                "summary": "Automatisation déploiement GitHub Actions",
                "vitality": 0.8,
            },
            "weighted_score": 0.87,
        }
    ]

    # Initialiser tool
    tool = MemoryQueryTool(mock_vector_service)

    # Appeler get_topic_details
    details = await tool.get_topic_details(
        user_id="user123", topic_query="CI/CD", limit=5
    )

    # Vérifier que query_weighted() a été appelé
    mock_vector_service.query_weighted.assert_called_once()

    # Vérifier détails
    assert details is not None
    assert details["topic"] == "CI/CD pipeline"
    assert details["weighted_score"] == 0.87
    assert details["mention_count"] == 3


# ---------- Tests UnifiedRetriever avec query_weighted ----------


@pytest.mark.asyncio
async def test_unified_retriever_uses_weighted_query():
    """
    Vérifie que UnifiedRetriever utilise bien query_weighted() pour concepts LTM.
    """
    from backend.features.memory.unified_retriever import UnifiedMemoryRetriever

    # Mock SessionManager
    mock_session_manager = Mock()
    mock_session_manager.get_full_history.return_value = []

    # Mock VectorService
    mock_vector_service = Mock()
    mock_collection = Mock()
    mock_collection.name = "emergence_knowledge"
    mock_vector_service.get_or_create_collection.return_value = mock_collection

    # Mock query_weighted() pour concepts
    mock_vector_service.query_weighted.return_value = [
        {"text": "Concept 1", "metadata": {}, "weighted_score": 0.85},
        {"text": "Concept 2", "metadata": {}, "weighted_score": 0.75},
    ]

    # Mock collection.get() pour préférences
    mock_collection.get.return_value = {
        "documents": ["Préférence 1"],
        "metadatas": [{"confidence": 0.8, "topic": "general"}],
    }

    # Mock DB
    mock_db = Mock()

    # Initialiser retriever
    retriever = UnifiedMemoryRetriever(
        session_manager=mock_session_manager,
        vector_service=mock_vector_service,
        db_manager=mock_db,
    )

    # Appeler retrieve_context
    context = await retriever.retrieve_context(
        user_id="user123",
        agent_id="anima",
        session_id="session_1",
        current_query="Test query",
        include_stm=True,
        include_ltm=True,
        include_archives=False,
        top_k_concepts=5,
    )

    # Vérifier que query_weighted() a été appelé
    mock_vector_service.query_weighted.assert_called_once()

    # Vérifier contexte
    assert len(context.ltm_concepts) == 2
    assert context.ltm_concepts[0]["weighted_score"] == 0.85


# ---------- Tests MemoryGarbageCollector ----------


@pytest.mark.asyncio
async def test_memory_gc_archive_inactive_entries():
    """
    Vérifie que MemoryGarbageCollector archive bien les entrées inactives > gc_inactive_days.
    """
    from backend.features.memory.memory_gc import MemoryGarbageCollector

    # Mock VectorService
    mock_vector_service = Mock()
    mock_collection = Mock()
    mock_collection.name = "emergence_knowledge"
    mock_archived_collection = Mock()
    mock_archived_collection.name = "emergence_knowledge_archived"

    # get_or_create_collection retourne différentes collections selon le nom
    def get_collection(name):
        if name.endswith("_archived"):
            return mock_archived_collection
        return mock_collection

    mock_vector_service.get_or_create_collection.side_effect = get_collection

    # Mock collection.get() pour retourner entrées
    old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    mock_collection.get.return_value = {
        "ids": ["entry_old", "entry_recent"],
        "documents": ["Old concept", "Recent concept"],
        "metadatas": [
            {"last_used_at": old_date, "use_count": 1},
            {"last_used_at": recent_date, "use_count": 5},
        ],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
    }

    # Initialiser GC
    gc = MemoryGarbageCollector(
        vector_service=mock_vector_service, gc_inactive_days=180
    )

    # Run GC
    stats = await gc.run_gc(collection_name="emergence_knowledge", dry_run=False)

    # Vérifier statistiques
    assert stats["candidates_found"] == 1  # Seulement entry_old
    assert stats["entries_archived"] == 1
    assert stats["errors"] == 0

    # Vérifier que archived_collection.add() a été appelé
    mock_archived_collection.add.assert_called_once()

    # Vérifier que source collection.delete() a été appelé
    mock_collection.delete.assert_called_once_with(ids=["entry_old"])


@pytest.mark.asyncio
async def test_memory_gc_dry_run():
    """
    Vérifie que dry_run ne modifie rien.
    """
    from backend.features.memory.memory_gc import MemoryGarbageCollector

    # Mock VectorService
    mock_vector_service = Mock()
    mock_collection = Mock()
    mock_collection.name = "emergence_knowledge"
    mock_vector_service.get_or_create_collection.return_value = mock_collection

    # Mock collection.get()
    old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    mock_collection.get.return_value = {
        "ids": ["entry_old"],
        "documents": ["Old concept"],
        "metadatas": [{"last_used_at": old_date}],
        "embeddings": [[0.1, 0.2]],
    }

    # Initialiser GC
    gc = MemoryGarbageCollector(
        vector_service=mock_vector_service, gc_inactive_days=180
    )

    # Run GC en dry_run
    stats = await gc.run_gc(collection_name="emergence_knowledge", dry_run=True)

    # Vérifier statistiques
    assert stats["candidates_found"] == 1
    assert stats["entries_archived"] == 0
    assert stats["dry_run"] is True

    # Vérifier qu'aucune modification n'a été faite
    mock_collection.add.assert_not_called()
    mock_collection.delete.assert_not_called()


# ---------- Tests ScoreCache ----------


def test_score_cache_hit():
    """
    Vérifie que le cache retourne les scores cachés.
    """
    from backend.features.memory.score_cache import ScoreCache

    cache = ScoreCache(max_size=100, ttl_seconds=3600)

    # Stocker un score
    cache.set("query1", "entry1", "2025-10-21T10:00:00+00:00", 0.85)

    # Récupérer le score
    score = cache.get("query1", "entry1", "2025-10-21T10:00:00+00:00")

    assert score == 0.85


def test_score_cache_miss():
    """
    Vérifie que le cache retourne None pour cache miss.
    """
    from backend.features.memory.score_cache import ScoreCache

    cache = ScoreCache(max_size=100, ttl_seconds=3600)

    # Récupérer score non existant
    score = cache.get("query_unknown", "entry_unknown", "2025-10-21T10:00:00+00:00")

    assert score is None


def test_score_cache_invalidation():
    """
    Vérifie que invalidate() supprime les entrées.
    """
    from backend.features.memory.score_cache import ScoreCache

    cache = ScoreCache(max_size=100, ttl_seconds=3600)

    # Stocker scores pour même entry
    cache.set("query1", "entry1", "2025-10-21T10:00:00+00:00", 0.85)
    cache.set("query2", "entry1", "2025-10-21T10:00:00+00:00", 0.75)

    # Invalider entry1
    cache.invalidate("entry1")

    # Vérifier que les scores ont été supprimés
    score1 = cache.get("query1", "entry1", "2025-10-21T10:00:00+00:00")
    score2 = cache.get("query2", "entry1", "2025-10-21T10:00:00+00:00")

    assert score1 is None
    assert score2 is None


def test_score_cache_ttl_expiration():
    """
    Vérifie que le cache expire après TTL.
    """
    from backend.features.memory.score_cache import ScoreCache
    import time

    cache = ScoreCache(max_size=100, ttl_seconds=1)  # 1 seconde TTL

    # Stocker un score
    cache.set("query1", "entry1", "2025-10-21T10:00:00+00:00", 0.85)

    # Attendre expiration
    time.sleep(1.1)

    # Récupérer score (doit être None car expiré)
    score = cache.get("query1", "entry1", "2025-10-21T10:00:00+00:00")

    assert score is None


def test_score_cache_lru_eviction():
    """
    Vérifie que le cache fait du LRU eviction quand plein.
    """
    from backend.features.memory.score_cache import ScoreCache

    cache = ScoreCache(max_size=2, ttl_seconds=3600)

    # Remplir cache
    cache.set("query1", "entry1", "2025-10-21T10:00:00+00:00", 0.85)
    cache.set("query2", "entry2", "2025-10-21T10:00:00+00:00", 0.75)

    # Ajouter troisième entrée (doit évincer la plus ancienne)
    cache.set("query3", "entry3", "2025-10-21T10:00:00+00:00", 0.65)

    # Vérifier que entry1 a été évincée
    score1 = cache.get("query1", "entry1", "2025-10-21T10:00:00+00:00")
    score3 = cache.get("query3", "entry3", "2025-10-21T10:00:00+00:00")

    assert score1 is None  # Evicted
    assert score3 == 0.65  # Présent


# ---------- Tests Métriques Prometheus ----------


def test_weighted_retrieval_metrics():
    """
    Vérifie que les métriques Prometheus sont enregistrées.
    """
    from backend.features.memory.weighted_retrieval_metrics import (
        WeightedRetrievalMetrics,
    )

    metrics = WeightedRetrievalMetrics()

    # Enregistrer métriques (ne devrait pas lever d'exception)
    metrics.record_query("emergence_knowledge", "success", 5, 0.123)
    metrics.record_score("emergence_knowledge", 0.85, 0.01)
    metrics.record_metadata_update("emergence_knowledge", 0.05)
    metrics.record_entry_age("emergence_knowledge", 30.0)
    metrics.record_use_count("emergence_knowledge", 5)
    metrics.set_active_count("emergence_knowledge", 1234)

    # Si aucune exception, le test passe
    assert True
