"""
Test de validation pour les timestamps réels lors de la consolidation de threads archivés.

Ce test vérifie que :
1. Les timestamps first_mentioned_at et last_mentioned_at correspondent aux dates réelles des messages
2. Les métadonnées thread_ids_json sont correctement remplies
3. Les agents peuvent interroger les concepts avec les bonnes dates

Usage:
    pytest tests/memory/test_thread_consolidation_timestamps.py -v
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import pytest

from backend.core.database.manager import DatabaseManager
from backend.features.memory.gardener import MemoryGardener
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer


@pytest.fixture
async def db_manager():
    """Fixture pour la base de données de test."""
    db = DatabaseManager(":memory:")
    await db.initialize()
    yield db
    await db.close()


@pytest.fixture
async def vector_service(tmp_path):
    """Fixture pour le service vectoriel (ChromaDB temporaire)."""
    import os
    persist_dir = str(tmp_path / "chroma_test")
    os.makedirs(persist_dir, exist_ok=True)

    # Utiliser un modèle léger pour les tests
    vs = VectorService(
        persist_directory=persist_dir,
        embed_model_name="all-MiniLM-L6-v2",  # Modèle léger
        auto_reset_on_schema_error=True
    )
    return vs


@pytest.fixture
async def memory_analyzer(db_manager):
    """Fixture pour l'analyseur mémoire."""
    # MemoryAnalyzer nécessite db_manager et optionnellement chat_service
    analyzer = MemoryAnalyzer(db_manager=db_manager, chat_service=None)
    return analyzer


@pytest.fixture
async def gardener(db_manager, vector_service, memory_analyzer):
    """Fixture pour le MemoryGardener."""
    return MemoryGardener(
        db_manager=db_manager,
        vector_service=vector_service,
        memory_analyzer=memory_analyzer
    )


@pytest.mark.asyncio
async def test_thread_consolidation_preserves_real_timestamps(
    db_manager: DatabaseManager,
    gardener: MemoryGardener
):
    """
    Teste que la consolidation d'un thread préserve les timestamps réels des messages.
    """
    # ARRANGE: Créer un thread avec 3 messages à des dates différentes
    user_id = "test-user-123"
    thread_id = "test-thread-archived-456"

    # Date de base il y a 30 jours
    base_date = datetime.now(timezone.utc) - timedelta(days=30)

    # Créer le thread
    session_id = f"session-{thread_id}"
    await db_manager.execute(
        """
        INSERT INTO threads (id, session_id, user_id, type, title, archived, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            thread_id,
            session_id,
            user_id,
            "chat",
            "Discussion Docker et containerisation",
            1,  # archivé
            base_date.isoformat(),
            base_date.isoformat()
        ),
        commit=True
    )

    # Créer 3 messages avec des dates espacées
    messages = [
        {
            "id": "msg1",
            "role": "user",
            "content": "Je veux apprendre Docker et la containerisation",
            "created_at": base_date.isoformat(),
        },
        {
            "id": "msg2",
            "role": "assistant",
            "content": "Docker est un outil de containerisation...",
            "created_at": (base_date + timedelta(minutes=5)).isoformat(),
        },
        {
            "id": "msg3",
            "role": "user",
            "content": "Comment configurer un CI/CD pipeline avec Docker ?",
            "created_at": (base_date + timedelta(days=2)).isoformat(),
        }
    ]

    for msg in messages:
        await db_manager.execute(
            """
            INSERT INTO messages (id, session_id, thread_id, user_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg["id"], session_id, thread_id, user_id, msg["role"], msg["content"], msg["created_at"]),
            commit=True
        )

    # ACT: Consolider le thread
    result = await gardener.tend_the_garden(thread_id=thread_id, user_id=user_id)

    # ASSERT: Vérifier que la consolidation a réussi
    assert result["status"] == "success"
    assert result["new_concepts"] > 0

    # Vérifier que les concepts ont été vectorisés avec les bons timestamps
    collection = gardener.knowledge_collection

    # Rechercher un concept (ex: "docker")
    concepts = gardener.vector_service.query(
        collection=collection,
        query_text="docker containerisation",
        n_results=5,
        where_filter={"user_id": user_id, "type": "concept"}
    )

    assert len(concepts) > 0, "Aucun concept trouvé après consolidation"

    # Vérifier le premier concept retourné
    concept_meta = concepts[0].get("metadata", {})

    # Le first_mentioned_at doit être proche de la date du premier message
    first_mentioned = datetime.fromisoformat(concept_meta["first_mentioned_at"])
    expected_first = base_date
    time_diff_first = abs((first_mentioned - expected_first).total_seconds())
    assert time_diff_first < 60, f"first_mentioned_at incorrect: {first_mentioned} vs {expected_first}"

    # Le last_mentioned_at doit être proche de la date du dernier message
    last_mentioned = datetime.fromisoformat(concept_meta["last_mentioned_at"])
    expected_last = base_date + timedelta(days=2)
    time_diff_last = abs((last_mentioned - expected_last).total_seconds())
    assert time_diff_last < 60, f"last_mentioned_at incorrect: {last_mentioned} vs {expected_last}"

    # Vérifier que le thread_id est présent
    assert concept_meta.get("thread_id") == thread_id

    # Vérifier que thread_ids_json est correctement formaté
    thread_ids = json.loads(concept_meta.get("thread_ids_json", "[]"))
    assert thread_id in thread_ids, f"thread_id absent de thread_ids_json: {thread_ids}"

    print("[OK] Test réussi : Les timestamps réels sont correctement préservés")


@pytest.mark.asyncio
async def test_concept_query_returns_historical_dates(
    db_manager: DatabaseManager,
    gardener: MemoryGardener
):
    """
    Teste qu'un agent peut interroger les concepts et obtenir les dates historiques.
    """
    # ARRANGE: Même setup que test précédent
    user_id = "test-user-789"
    thread_id = "test-thread-history-012"

    # Date il y a 45 jours (au-delà du seuil d'archivage)
    old_date = datetime.now(timezone.utc) - timedelta(days=45)
    session_id = f"session-{thread_id}"

    await db_manager.execute(
        """
        INSERT INTO threads (id, session_id, user_id, type, title, archived, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (thread_id, session_id, user_id, "chat", "Discussion CI/CD", 1, old_date.isoformat(), old_date.isoformat()),
        commit=True
    )

    await db_manager.execute(
        """
        INSERT INTO messages (id, session_id, thread_id, user_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("msg_old", session_id, thread_id, user_id, "user", "Je veux mettre en place un pipeline CI/CD", old_date.isoformat()),
        commit=True
    )

    # ACT: Consolider
    await gardener.tend_the_garden(thread_id=thread_id, user_id=user_id)

    # Simuler une requête agent via l'API concept_recall
    from backend.features.memory.concept_recall import ConceptRecallTracker
    tracker = ConceptRecallTracker(
        db_manager=db_manager,
        vector_service=gardener.vector_service
    )

    history = await tracker.query_concept_history(
        concept_text="CI/CD pipeline",
        user_id=user_id,
        limit=10
    )

    # ASSERT: L'agent doit pouvoir récupérer le concept avec la date historique
    assert len(history) > 0, "Aucun concept historique trouvé"

    concept = history[0]
    first_date = datetime.fromisoformat(concept["first_mentioned_at"])

    # La date doit être ancienne (il y a ~45 jours)
    age_days = (datetime.now(timezone.utc) - first_date).days
    assert age_days >= 40, f"Le concept devrait être vieux de ~45j, mais age={age_days}j"

    # Vérifier que le thread_id est présent
    assert thread_id in concept["thread_ids"]

    print(f"[OK] Test réussi : L'agent peut récupérer un concept vieux de {age_days} jours")


@pytest.mark.asyncio
async def test_empty_thread_handles_gracefully(
    db_manager: DatabaseManager,
    gardener: MemoryGardener
):
    """
    Teste que la consolidation d'un thread vide ne plante pas.
    """
    user_id = "test-user-empty"
    thread_id = "test-thread-empty"
    session_id = f"session-{thread_id}"
    now = datetime.now(timezone.utc).isoformat()

    await db_manager.execute(
        "INSERT INTO threads (id, session_id, user_id, type, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (thread_id, session_id, user_id, "chat", "Thread vide", now, now),
        commit=True
    )

    # ACT: Consolider un thread sans messages
    result = await gardener.tend_the_garden(thread_id=thread_id, user_id=user_id)

    # ASSERT: Pas d'erreur, mais aucun concept ajouté
    assert result["status"] == "success"
    assert result["new_concepts"] == 0

    print("[OK] Test réussi : Thread vide géré sans erreur")


if __name__ == "__main__":
    """Exécution manuelle pour debug."""
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
