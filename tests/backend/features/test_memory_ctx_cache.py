"""Tests d'invalidation du cache préférences dans MemoryContextBuilder.

Tests pour Bug #5 (P1): Invalidation cache préférences
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from backend.features.chat.memory_ctx import MemoryContextBuilder


@pytest.fixture
def mock_session_manager():
    """Session manager mocké."""
    session_manager = Mock()
    session_manager.get_session = Mock(return_value={"id": "session123"})
    session_manager.get_user_id_for_session = Mock(return_value="user123")
    return session_manager


@pytest.fixture
def mock_vector_service():
    """VectorService mocké."""
    service = Mock()
    collection = MagicMock()
    collection.get = MagicMock(
        return_value={
            "documents": ["Préférence v1"],
            "metadatas": [{"confidence": 0.8}],
        }
    )
    service.get_or_create_collection = Mock(return_value=collection)
    return service


@pytest.fixture
def memory_ctx_builder(mock_session_manager, mock_vector_service):
    """Instance de MemoryContextBuilder pour les tests."""
    return MemoryContextBuilder(
        session_manager=mock_session_manager, vector_service=mock_vector_service
    )


class TestPreferencesCacheInvalidation:
    """Tests d'invalidation du cache préférences."""

    def test_invalidate_preferences_cache_existing_user(self, memory_ctx_builder):
        """Test invalidation cache pour utilisateur existant dans le cache."""
        user_id = "user123"

        # Pré-remplir le cache
        memory_ctx_builder._prefs_cache[user_id] = ("Préférence v1", datetime.now())
        assert user_id in memory_ctx_builder._prefs_cache

        # Invalider le cache
        memory_ctx_builder.invalidate_preferences_cache(user_id)

        # Vérifier que l'entrée a été supprimée
        assert user_id not in memory_ctx_builder._prefs_cache

    def test_invalidate_preferences_cache_nonexistent_user(self, memory_ctx_builder):
        """Test invalidation cache pour utilisateur non présent (no-op)."""
        user_id = "user_not_in_cache"

        # Vérifier que l'utilisateur n'est pas dans le cache
        assert user_id not in memory_ctx_builder._prefs_cache

        # Invalider le cache ne devrait pas lever d'exception
        memory_ctx_builder.invalidate_preferences_cache(user_id)

        # Cache devrait rester vide
        assert user_id not in memory_ctx_builder._prefs_cache

    def test_invalidate_only_target_user(self, memory_ctx_builder):
        """Test que l'invalidation n'affecte que l'utilisateur cible."""
        user1 = "user1"
        user2 = "user2"
        user3 = "user3"

        # Pré-remplir le cache avec 3 utilisateurs
        now = datetime.now()
        memory_ctx_builder._prefs_cache[user1] = ("Pref1", now)
        memory_ctx_builder._prefs_cache[user2] = ("Pref2", now)
        memory_ctx_builder._prefs_cache[user3] = ("Pref3", now)

        # Invalider seulement user2
        memory_ctx_builder.invalidate_preferences_cache(user2)

        # Vérifier que seul user2 a été supprimé
        assert user1 in memory_ctx_builder._prefs_cache
        assert user2 not in memory_ctx_builder._prefs_cache
        assert user3 in memory_ctx_builder._prefs_cache

    def test_cache_refresh_after_invalidation(
        self, memory_ctx_builder, mock_vector_service
    ):
        """Test que le cache est rechargé depuis ChromaDB après invalidation."""
        user_id = "user123"
        collection = mock_vector_service.get_or_create_collection.return_value

        # 1. Premier chargement (mise en cache)
        collection.get = MagicMock(
            return_value={
                "documents": ["Préférence v1"],
                "metadatas": [{"confidence": 0.8}],
            }
        )
        prefs1 = memory_ctx_builder._fetch_active_preferences_cached(
            collection, user_id
        )
        assert "Préférence v1" in prefs1
        assert user_id in memory_ctx_builder._prefs_cache

        # 2. Simuler mise à jour préférences dans ChromaDB
        collection.get = MagicMock(
            return_value={
                "documents": ["Préférence v2"],
                "metadatas": [{"confidence": 0.9}],
            }
        )

        # 3. Sans invalidation → cache stale (retourne v1)
        prefs2 = memory_ctx_builder._fetch_active_preferences_cached(
            collection, user_id
        )
        assert "Préférence v1" in prefs2  # Ancienne version (cache hit)

        # 4. Avec invalidation → rechargement depuis ChromaDB (retourne v2)
        memory_ctx_builder.invalidate_preferences_cache(user_id)
        prefs3 = memory_ctx_builder._fetch_active_preferences_cached(
            collection, user_id
        )
        assert "Préférence v2" in prefs3  # Nouvelle version (cache miss + refresh)

    def test_cache_ttl_still_works_after_invalidation_feature(
        self, memory_ctx_builder, mock_vector_service
    ):
        """Test que le TTL du cache continue de fonctionner normalement."""
        user_id = "user123"
        collection = mock_vector_service.get_or_create_collection.return_value

        # Charger dans le cache
        collection.get = MagicMock(
            return_value={
                "documents": ["Préférence v1"],
                "metadatas": [{"confidence": 0.8}],
            }
        )
        memory_ctx_builder._fetch_active_preferences_cached(collection, user_id)
        assert user_id in memory_ctx_builder._prefs_cache

        # Simuler expiration TTL (modifier timestamp dans le passé)
        old_timestamp = datetime.now() - timedelta(minutes=10)  # TTL = 5 min
        memory_ctx_builder._prefs_cache[user_id] = ("Préférence v1", old_timestamp)

        # Changer réponse ChromaDB
        collection.get = MagicMock(
            return_value={
                "documents": ["Préférence v2"],
                "metadatas": [{"confidence": 0.9}],
            }
        )

        # Accès après expiration TTL → devrait recharger (v2)
        prefs2 = memory_ctx_builder._fetch_active_preferences_cached(
            collection, user_id
        )
        assert "Préférence v2" in prefs2

    def test_multiple_invalidations_sequential(self, memory_ctx_builder):
        """Test invalidations séquentielles multiples."""
        user_id = "user123"

        # Ajouter au cache
        memory_ctx_builder._prefs_cache[user_id] = ("Pref v1", datetime.now())
        assert user_id in memory_ctx_builder._prefs_cache

        # Invalider 3 fois de suite
        memory_ctx_builder.invalidate_preferences_cache(user_id)
        assert user_id not in memory_ctx_builder._prefs_cache

        memory_ctx_builder.invalidate_preferences_cache(user_id)  # No-op
        memory_ctx_builder.invalidate_preferences_cache(user_id)  # No-op

        # Cache devrait rester vide
        assert user_id not in memory_ctx_builder._prefs_cache


class TestCacheInvalidationIntegration:
    """Tests d'intégration avec le flux complet de mise en cache."""

    def test_cache_invalidation_workflow(self, memory_ctx_builder, mock_vector_service):
        """Test du workflow complet: cache → update → invalidate → refresh."""
        user_id = "user123"
        collection = mock_vector_service.get_or_create_collection.return_value

        # Étape 1: Cache initial
        collection.get = MagicMock(
            return_value={
                "documents": ["Aime le café"],
                "metadatas": [{"confidence": 0.9}],
            }
        )
        prefs_v1 = memory_ctx_builder._fetch_active_preferences_cached(
            collection, user_id
        )
        assert "café" in prefs_v1

        # Étape 2: Simulation mise à jour ChromaDB (analyse mémoire)
        collection.get = MagicMock(
            return_value={
                "documents": ["Aime le café", "N'aime pas le thé"],
                "metadatas": [{"confidence": 0.9}, {"confidence": 0.8}],
            }
        )

        # Étape 3: Sans invalidation → ancienne version
        prefs_stale = memory_ctx_builder._fetch_active_preferences_cached(
            collection, user_id
        )
        assert "café" in prefs_stale
        assert "thé" not in prefs_stale  # Pas encore visible

        # Étape 4: Invalidation après analyse
        memory_ctx_builder.invalidate_preferences_cache(user_id)

        # Étape 5: Rechargement → nouvelle version
        prefs_fresh = memory_ctx_builder._fetch_active_preferences_cached(
            collection, user_id
        )
        assert "café" in prefs_fresh
        assert "thé" in prefs_fresh  # Maintenant visible

    def test_cache_size_management_with_invalidation(self, memory_ctx_builder):
        """Test que l'invalidation fonctionne bien avec le cleanup automatique."""
        # Pré-remplir le cache avec plusieurs utilisateurs
        now = datetime.now()
        for i in range(10):
            user_id = f"user{i}"
            memory_ctx_builder._prefs_cache[user_id] = (f"Pref{i}", now)

        assert len(memory_ctx_builder._prefs_cache) == 10

        # Invalider quelques utilisateurs
        memory_ctx_builder.invalidate_preferences_cache("user3")
        memory_ctx_builder.invalidate_preferences_cache("user7")

        assert len(memory_ctx_builder._prefs_cache) == 8
        assert "user3" not in memory_ctx_builder._prefs_cache
        assert "user7" not in memory_ctx_builder._prefs_cache

        # Les autres devraient rester
        assert "user0" in memory_ctx_builder._prefs_cache
        assert "user9" in memory_ctx_builder._prefs_cache
