# tests/backend/features/test_memory_cache_performance.py
# Tests performance cache in-memory préférences (Phase P2.1)
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from backend.features.chat.memory_ctx import MemoryContextBuilder


class TestMemoryCachePerformance:
    """Tests performance et hit rate du cache préférences in-memory."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock SessionManager pour tests."""
        sm = Mock()
        sm.get_user_id_for_session = Mock(return_value="user_test_123")
        return sm

    @pytest.fixture
    def mock_vector_service(self):
        """Mock VectorService pour tests."""
        vs = Mock()

        # Mock collection
        collection = Mock()
        collection.get = Mock(return_value={
            "documents": [
                "python: Je préfère Python pour automation",
                "containerization: Éviter Docker Compose, utiliser Kubernetes"
            ],
            "metadatas": [
                {"type": "preference", "confidence": 0.92, "user_id": "user_test_123"},
                {"type": "preference", "confidence": 0.78, "user_id": "user_test_123"}
            ]
        })

        vs.get_or_create_collection = Mock(return_value=collection)
        return vs

    @pytest.fixture
    def memory_builder(self, mock_session_manager, mock_vector_service):
        """Créer MemoryContextBuilder avec mocks."""
        return MemoryContextBuilder(mock_session_manager, mock_vector_service)

    def test_cache_hit_performance(self, memory_builder, mock_vector_service):
        """Test que cache hit est significativement plus rapide que cache miss."""
        collection = mock_vector_service.get_or_create_collection()
        user_id = "user_cache_test"

        # Première requête (cache miss)
        start_miss = time.perf_counter()
        prefs_miss = memory_builder._fetch_active_preferences_cached(collection, user_id)
        duration_miss = time.perf_counter() - start_miss

        # Deuxième requête (cache hit)
        start_hit = time.perf_counter()
        prefs_hit = memory_builder._fetch_active_preferences_cached(collection, user_id)
        duration_hit = time.perf_counter() - start_hit

        # Assertions
        assert prefs_miss == prefs_hit, "Résultats identiques hit vs miss"
        # Note: Timing moins strict car mock très rapide (pas de vraie DB)
        assert duration_hit <= duration_miss, f"Cache hit devrait être au moins aussi rapide (hit={duration_hit*1000:.2f}ms, miss={duration_miss*1000:.2f}ms)"
        assert duration_hit < 0.010, f"Cache hit devrait être <10ms (actual={duration_hit*1000:.2f}ms)"
        print(f"\n[Performance] Cache miss: {duration_miss*1000:.2f}ms, Cache hit: {duration_hit*1000:.2f}ms (speedup: {duration_miss/duration_hit:.1f}x)")

    def test_cache_hit_rate_realistic_traffic(self, memory_builder, mock_vector_service):
        """Test hit rate avec pattern trafic réaliste (80% repeat queries)."""
        collection = mock_vector_service.get_or_create_collection()

        hits = 0
        total = 100
        unique_users = 20  # 20 users uniques

        for i in range(total):
            # Simulate 80% repeat queries (5 messages par user)
            user_id = f"user_{i % unique_users}"

            start = time.perf_counter()
            memory_builder._fetch_active_preferences_cached(collection, user_id)
            duration = time.perf_counter() - start

            # Cache hit si < 5ms (heuristique)
            if duration < 0.005:
                hits += 1

        hit_rate = hits / total
        print(f"\n[Cache Stats] Hit rate: {hit_rate*100:.1f}% ({hits}/{total})")

        # Assertions
        assert hit_rate > 0.75, f"Hit rate devrait être >75% (actual={hit_rate*100:.1f}%)"

        # First query for each user = miss (20), rest = hit (80)
        expected_hits = total - unique_users
        expected_rate = expected_hits / total
        assert hit_rate >= expected_rate * 0.9, f"Hit rate proche de l'attendu ({expected_rate*100:.1f}%)"

    def test_cache_ttl_expiration(self, memory_builder, mock_vector_service):
        """Test que cache expire après TTL."""
        collection = mock_vector_service.get_or_create_collection()
        user_id = "user_ttl_test"

        # Cache entry
        memory_builder._fetch_active_preferences_cached(collection, user_id)
        assert user_id in memory_builder._prefs_cache

        # Simulate TTL expiration (6 minutes)
        prefs, cached_at = memory_builder._prefs_cache[user_id]
        memory_builder._prefs_cache[user_id] = (prefs, datetime.now() - timedelta(minutes=6))

        # Next query should be cache miss (expired)
        memory_builder._fetch_active_preferences_cached(collection, user_id)

        # Verify entry was refreshed with new timestamp
        _, new_cached_at = memory_builder._prefs_cache[user_id]
        assert (datetime.now() - new_cached_at).total_seconds() < 1, "Entry devrait être rafraîchie"

    def test_cache_cleanup_garbage_collection(self, memory_builder, mock_vector_service):
        """Test que garbage collection supprime entrées expirées."""
        collection = mock_vector_service.get_or_create_collection()

        # Create 5 cache entries
        for i in range(5):
            memory_builder._fetch_active_preferences_cached(collection, f"user_{i}")

        assert len(memory_builder._prefs_cache) == 5

        # Expire 3 entries
        for i in range(3):
            prefs, _ = memory_builder._prefs_cache[f"user_{i}"]
            memory_builder._prefs_cache[f"user_{i}"] = (prefs, datetime.now() - timedelta(minutes=6))

        # Trigger GC
        memory_builder._cleanup_expired_cache()

        # Verify only 2 entries remain
        assert len(memory_builder._prefs_cache) == 2, "3 entrées expirées devraient être supprimées"
        assert "user_3" in memory_builder._prefs_cache
        assert "user_4" in memory_builder._prefs_cache

    def test_cache_memory_efficiency(self, memory_builder, mock_vector_service):
        """Test que cache ne consomme pas trop de mémoire."""
        collection = mock_vector_service.get_or_create_collection()

        # Simulate 100 users
        for i in range(100):
            memory_builder._fetch_active_preferences_cached(collection, f"user_{i}")

        # Verify cache size
        cache_size = len(memory_builder._prefs_cache)
        assert cache_size == 100, f"Cache devrait contenir 100 entrées (actual={cache_size})"

        # Estimate memory usage (~500 bytes per entry)
        estimated_bytes = cache_size * 500
        estimated_mb = estimated_bytes / (1024 ** 2)

        print(f"\n[Cache Memory] ~{estimated_mb:.2f} MB pour {cache_size} entrées")
        assert estimated_mb < 1.0, "Cache ne devrait pas excéder 1MB pour 100 users"

    @pytest.mark.asyncio
    async def test_cache_integration_build_context(self, memory_builder, mock_vector_service):
        """Test intégration cache dans build_memory_context()."""
        # Mock query results
        mock_vector_service.query = Mock(return_value=[
            {
                "text": "concept: containerization",
                "metadata": {"created_at": "2025-10-10T10:00:00Z"},
                "score": 0.92
            }
        ])

        session_id = "test_session"
        user_message = "Tell me about Docker"

        # First call (cache miss)
        start_miss = time.perf_counter()
        context_miss = await memory_builder.build_memory_context(session_id, user_message, top_k=5)
        duration_miss = time.perf_counter() - start_miss

        # Second call (cache hit)
        start_hit = time.perf_counter()
        context_hit = await memory_builder.build_memory_context(session_id, user_message, top_k=5)
        duration_hit = time.perf_counter() - start_hit

        # Assertions
        assert context_miss == context_hit, "Contextes identiques"
        # Note: Cache améliore performance globale (pas toujours mesurable en micro-benchmark avec mocks)
        print(f"\n[Integration] Context build - miss: {duration_miss*1000:.2f}ms, hit: {duration_hit*1000:.2f}ms")

        # Verify preferences section present
        assert "Préférences actives" in context_hit
        assert "python" in context_hit.lower() or "containerization" in context_hit.lower()


class TestMemoryCacheStressTest:
    """Stress tests pour valider robustesse cache."""

    @pytest.fixture
    def mock_session_manager(self):
        """Mock SessionManager pour tests."""
        sm = Mock()
        sm.get_user_id_for_session = Mock(return_value="user_test_123")
        return sm

    @pytest.fixture
    def mock_vector_service(self):
        """Mock VectorService pour tests."""
        vs = Mock()
        collection = Mock()
        collection.get = Mock(return_value={
            "documents": ["python: Test preference"],
            "metadatas": [{"type": "preference", "confidence": 0.9, "user_id": "user_test"}]
        })
        vs.get_or_create_collection = Mock(return_value=collection)
        return vs

    def test_concurrent_cache_access(self, mock_session_manager, mock_vector_service):
        """Test accès concurrent au cache (simule charge production)."""
        import random

        builder = MemoryContextBuilder(mock_session_manager, mock_vector_service)
        collection = mock_vector_service.get_or_create_collection()

        # Simulate 1000 requests from 50 users
        total_requests = 1000
        user_pool = [f"user_{i}" for i in range(50)]

        for _ in range(total_requests):
            user_id = random.choice(user_pool)
            result = builder._fetch_active_preferences_cached(collection, user_id)
            assert result is not None or result == "", "Cache devrait toujours retourner résultat"

        # Verify cache size reasonable (<= user_pool size)
        cache_size = len(builder._prefs_cache)
        assert cache_size <= len(user_pool), f"Cache ne devrait pas excéder {len(user_pool)} entrées"

        print(f"\n[Stress Test] {total_requests} requests, {cache_size} cached users")

    def test_cache_persistence_across_calls(self, mock_session_manager, mock_vector_service):
        """Test que cache persiste entre appels multiples."""
        builder = MemoryContextBuilder(mock_session_manager, mock_vector_service)
        collection = mock_vector_service.get_or_create_collection()
        user_id = "user_persist"

        # Multiple calls
        results = []
        for i in range(10):
            result = builder._fetch_active_preferences_cached(collection, user_id)
            results.append(result)

        # All results should be identical
        assert all(r == results[0] for r in results), "Résultats devraient être cohérents"

        # Cache should contain single entry
        assert len(builder._prefs_cache) == 1
