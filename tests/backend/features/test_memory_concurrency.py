# tests/backend/features/test_memory_concurrency.py
"""
Tests de concurrence pour la correction du Bug #3 : Race conditions sur dictionnaires partagés.
Vérifie que les locks asyncio.Lock() fonctionnent correctement.
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.memory.incremental_consolidation import IncrementalConsolidator
from backend.features.memory.proactive_hints import ConceptTracker
from backend.features.memory.intent_tracker import IntentTracker


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager"""
    db = Mock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_chat_service():
    """Mock ChatService"""
    chat = Mock()
    chat.get_structured_llm_response = AsyncMock(return_value={
        "summary": "Test summary",
        "concepts": ["concept1", "concept2"],
        "entities": ["entity1"]
    })
    chat.session_manager = Mock()
    chat.session_manager.get_session = Mock(return_value=None)
    chat.vector_service = None
    return chat


@pytest.fixture
def mock_vector_service():
    """Mock VectorService"""
    vec = Mock()
    vec.get_or_create_collection = Mock(return_value=Mock())
    return vec


class TestCacheConcurrency:
    """Tests de concurrence pour le cache MemoryAnalyzer"""

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self, mock_db_manager, mock_chat_service):
        """Test que le cache gère correctement les accès concurrents"""
        analyzer = MemoryAnalyzer(mock_db_manager)
        analyzer.set_chat_service(mock_chat_service)

        # Patch queries.update_session_analysis_data
        with patch('backend.features.memory.analyzer.queries.update_session_analysis_data', new=AsyncMock()):
            # Fonction pour écrire dans le cache
            async def write_cache(i: int):
                history = [{"role": "user", "content": f"Message {i}"}]
                await analyzer.analyze_session_for_concepts(
                    session_id=f"session_{i}",
                    history=history,
                    force=False,
                    user_id="test_user"
                )

            # Lancer 100 écritures concurrentes
            tasks = [write_cache(i) for i in range(100)]
            await asyncio.gather(*tasks)

            # Le cache devrait être présent et cohérent (pas de corruption)
            # Avec éviction agressive, on devrait avoir ~50 entrées max
            from backend.features.memory.analyzer import _ANALYSIS_CACHE
            cache_size = len(_ANALYSIS_CACHE)

            # Vérifier que le cache est dans les limites attendues
            assert cache_size > 0, "Le cache devrait contenir des entrées"
            assert cache_size <= 100, "Le cache ne devrait pas dépasser 100 entrées"


class TestConsolidatorConcurrency:
    """Tests de concurrence pour IncrementalConsolidator"""

    @pytest.mark.asyncio
    async def test_counter_concurrent_increments(self, mock_db_manager, mock_vector_service):
        """Test que les compteurs gèrent correctement les incréments concurrents"""
        consolidator = IncrementalConsolidator(
            memory_analyzer=Mock(),
            vector_service=mock_vector_service,
            db_manager=mock_db_manager,
            consolidation_threshold=50
        )
        counter_key = "test_session:test_thread"

        async def increment():
            await consolidator.increment_counter(counter_key)

        # Lancer 50 incréments concurrents
        tasks = [increment() for _ in range(50)]
        await asyncio.gather(*tasks)

        # Vérifier compteur correct (pas de race condition)
        count = await consolidator.get_counter(counter_key)
        assert count == 50, f"Le compteur devrait être 50, actuel: {count}"

    @pytest.mark.asyncio
    async def test_counter_reset_thread_safe(self, mock_db_manager, mock_vector_service):
        """Test que le reset est thread-safe"""
        consolidator = IncrementalConsolidator(
            memory_analyzer=Mock(),
            vector_service=mock_vector_service,
            db_manager=mock_db_manager,
            consolidation_threshold=10
        )
        counter_key = "test_session:test_thread"

        # Incrémenter plusieurs fois
        for _ in range(5):
            await consolidator.increment_counter(counter_key)

        # Reset
        await consolidator.reset_counter(counter_key)

        # Vérifier que le compteur est à 0
        count = await consolidator.get_counter(counter_key)
        assert count == 0, "Le compteur devrait être 0 après reset"


class TestConceptTrackerConcurrency:
    """Tests de concurrence pour ConceptTracker"""

    @pytest.mark.asyncio
    async def test_track_mention_concurrent(self):
        """Test que track_mention gère les accès concurrents"""
        tracker = ConceptTracker()
        user_id = "test_user"
        concept = "machine_learning"

        async def track():
            return await tracker.track_mention(user_id, concept)

        # Lancer 30 tracks concurrents
        tasks = [track() for _ in range(30)]
        results = await asyncio.gather(*tasks)

        # Tous les tracks devraient avoir été comptés
        # Le dernier résultat devrait être 30
        assert 30 in results, f"Le compteur final devrait être 30, résultats: {results}"

    @pytest.mark.asyncio
    async def test_reset_counter_thread_safe(self):
        """Test que reset_counter est thread-safe"""
        tracker = ConceptTracker()
        user_id = "test_user"
        concept = "deep_learning"

        # Track plusieurs fois
        for _ in range(5):
            await tracker.track_mention(user_id, concept)

        # Reset
        await tracker.reset_counter(user_id, concept)

        # Vérifier que le compteur est remis à 0
        # (en trackant une nouvelle fois, on devrait avoir 1)
        count = await tracker.track_mention(user_id, concept)
        assert count == 1, f"Le compteur devrait être 1 après reset, actuel: {count}"


class TestIntentTrackerConcurrency:
    """Tests de concurrence pour IntentTracker"""

    @pytest.mark.asyncio
    async def test_reminder_concurrent_increments(self, mock_vector_service):
        """Test que les rappels d'intention gèrent les incréments concurrents"""
        tracker = IntentTracker(vector_service=mock_vector_service)
        intent_id = "intent_123"

        async def increment():
            await tracker.increment_reminder(intent_id)

        # Lancer 10 incréments concurrents
        tasks = [increment() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Vérifier compteur correct
        count = await tracker.get_reminder_count(intent_id)
        assert count == 10, f"Le compteur devrait être 10, actuel: {count}"

    @pytest.mark.asyncio
    async def test_delete_reminder_thread_safe(self, mock_vector_service):
        """Test que delete_reminder est thread-safe"""
        tracker = IntentTracker(vector_service=mock_vector_service)
        intent_id = "intent_456"

        # Incrémenter plusieurs fois
        for _ in range(3):
            await tracker.increment_reminder(intent_id)

        # Supprimer
        await tracker.delete_reminder(intent_id)

        # Vérifier que le compteur est supprimé
        count = await tracker.get_reminder_count(intent_id)
        assert count == 0, "Le compteur devrait être 0 après suppression"


class TestCrossComponentConcurrency:
    """Tests de concurrence entre plusieurs composants"""

    @pytest.mark.asyncio
    async def test_multiple_components_concurrent(self, mock_db_manager, mock_chat_service, mock_vector_service):
        """Test que plusieurs composants peuvent fonctionner concurremment sans deadlock"""
        # Créer tous les composants
        analyzer = MemoryAnalyzer(mock_db_manager)
        analyzer.set_chat_service(mock_chat_service)

        consolidator = IncrementalConsolidator(
            memory_analyzer=Mock(),
            vector_service=mock_vector_service,
            db_manager=mock_db_manager,
            consolidation_threshold=50
        )

        tracker = ConceptTracker()
        intent_tracker = IntentTracker(vector_service=mock_vector_service)

        # Tâches concurrentes sur différents composants
        with patch('backend.features.memory.analyzer.queries.update_session_analysis_data', new=AsyncMock()):
            async def task1():
                # Analyser session
                history = [{"role": "user", "content": "Test concurrent"}]
                await analyzer.analyze_session_for_concepts(
                    session_id="concurrent_session",
                    history=history,
                    force=False,
                    user_id="test_user"
                )

            async def task2():
                # Incrémenter consolidator
                for i in range(10):
                    await consolidator.increment_counter(f"session_{i}:thread")

            async def task3():
                # Track concepts
                for i in range(10):
                    await tracker.track_mention("user1", f"concept_{i}")

            async def task4():
                # Increment reminders
                for i in range(10):
                    await intent_tracker.increment_reminder(f"intent_{i}")

            # Lancer toutes les tâches en parallèle
            await asyncio.gather(task1(), task2(), task3(), task4())

            # Vérifier qu'aucun deadlock ne s'est produit (si on arrive ici, c'est OK)
            assert True, "Toutes les tâches concurrentes ont réussi sans deadlock"


class TestLockPerformance:
    """Tests de performance des locks"""

    @pytest.mark.asyncio
    async def test_lock_does_not_block_independent_operations(self):
        """Test que les locks ne bloquent pas les opérations indépendantes"""
        tracker1 = ConceptTracker()
        tracker2 = ConceptTracker()

        start_time = asyncio.get_event_loop().time()

        # Deux trackers différents ne devraient pas se bloquer mutuellement
        async def track_tracker1():
            for _ in range(20):
                await tracker1.track_mention("user1", "concept_a")

        async def track_tracker2():
            for _ in range(20):
                await tracker2.track_mention("user2", "concept_b")

        await asyncio.gather(track_tracker1(), track_tracker2())

        elapsed = asyncio.get_event_loop().time() - start_time

        # Les deux devraient s'exécuter en parallèle (pas plus de 2x le temps séquentiel)
        # Avec un timeout généreux pour CI/CD lent
        assert elapsed < 2.0, f"Les opérations indépendantes devraient être rapides, temps: {elapsed}s"
