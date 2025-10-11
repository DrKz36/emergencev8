"""Tests batch fetch préférences dans MemoryGardener.

Tests pour Bug #6 (P1): Optimisation N+1 avec batch fetch
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from src.backend.features.memory.gardener import MemoryGardener


@pytest.fixture
def mock_db_manager():
    """Database manager mocké."""
    db = Mock()
    db.execute = AsyncMock(return_value=None)
    return db


@pytest.fixture
def mock_vector_service():
    """VectorService mocké."""
    service = Mock()
    service.add_items = Mock()
    service.get_or_create_collection = Mock()
    return service


@pytest.fixture
def mock_memory_analyzer():
    """MemoryAnalyzer mocké."""
    analyzer = Mock()
    return analyzer


@pytest.fixture
def mock_preference_collection():
    """Collection ChromaDB mockée pour préférences."""
    collection = MagicMock()
    collection.name = "test_preferences"
    return collection


@pytest.fixture
def gardener(mock_db_manager, mock_vector_service, mock_memory_analyzer, mock_preference_collection):
    """Instance de MemoryGardener pour les tests."""
    instance = MemoryGardener(
        db_manager=mock_db_manager,
        vector_service=mock_vector_service,
        memory_analyzer=mock_memory_analyzer
    )
    instance.preference_collection = mock_preference_collection
    return instance


class TestBatchPreferenceFetch:
    """Tests de la méthode _get_existing_preferences_batch."""

    @pytest.mark.asyncio
    async def test_batch_fetch_empty_list(self, gardener):
        """Test batch fetch avec liste vide."""
        result = await gardener._get_existing_preferences_batch([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_fetch_single_existing(self, gardener, mock_preference_collection):
        """Test batch fetch avec 1 préférence existante."""
        # Mock réponse ChromaDB
        mock_preference_collection.get = Mock(return_value={
            "ids": ["pref_1"],
            "metadatas": [{"confidence": 0.8, "occurrences": 2}],
            "documents": ["Aime le café"]
        })

        result = await gardener._get_existing_preferences_batch(["pref_1"])

        assert "pref_1" in result
        assert result["pref_1"]["id"] == "pref_1"
        assert result["pref_1"]["metadata"]["confidence"] == 0.8
        assert result["pref_1"]["document"] == "Aime le café"

    @pytest.mark.asyncio
    async def test_batch_fetch_multiple_existing(self, gardener, mock_preference_collection):
        """Test batch fetch avec plusieurs préférences existantes."""
        # Mock réponse ChromaDB avec 3 préférences
        mock_preference_collection.get = Mock(return_value={
            "ids": ["pref_1", "pref_2", "pref_3"],
            "metadatas": [
                {"confidence": 0.8, "occurrences": 2},
                {"confidence": 0.9, "occurrences": 5},
                {"confidence": 0.7, "occurrences": 1}
            ],
            "documents": ["Aime le café", "N'aime pas le thé", "Préfère le matin"]
        })

        result = await gardener._get_existing_preferences_batch(["pref_1", "pref_2", "pref_3"])

        assert len(result) == 3
        assert all(pid in result for pid in ["pref_1", "pref_2", "pref_3"])
        assert result["pref_1"]["metadata"]["confidence"] == 0.8
        assert result["pref_2"]["metadata"]["occurrences"] == 5
        assert result["pref_3"]["document"] == "Préfère le matin"

    @pytest.mark.asyncio
    async def test_batch_fetch_partial_missing(self, gardener, mock_preference_collection):
        """Test batch fetch avec certaines préférences manquantes."""
        # Demander 3 préférences, mais seulement 2 existent
        mock_preference_collection.get = Mock(return_value={
            "ids": ["pref_1", "pref_3"],  # pref_2 manquant
            "metadatas": [
                {"confidence": 0.8},
                {"confidence": 0.7}
            ],
            "documents": ["Aime le café", "Préfère le matin"]
        })

        result = await gardener._get_existing_preferences_batch(["pref_1", "pref_2", "pref_3"])

        assert len(result) == 3
        assert result["pref_1"] is not None
        assert result["pref_2"] is None  # Manquant
        assert result["pref_3"] is not None

    @pytest.mark.asyncio
    async def test_batch_fetch_all_missing(self, gardener, mock_preference_collection):
        """Test batch fetch avec aucune préférence existante."""
        mock_preference_collection.get = Mock(return_value={
            "ids": [],
            "metadatas": [],
            "documents": []
        })

        result = await gardener._get_existing_preferences_batch(["pref_1", "pref_2"])

        assert len(result) == 2
        assert result["pref_1"] is None
        assert result["pref_2"] is None

    @pytest.mark.asyncio
    async def test_batch_fetch_handles_exceptions(self, gardener, mock_preference_collection):
        """Test que les exceptions sont gérées gracieusement."""
        mock_preference_collection.get = Mock(side_effect=Exception("ChromaDB error"))

        result = await gardener._get_existing_preferences_batch(["pref_1", "pref_2"])

        # Devrait retourner dict avec None pour chaque ID
        assert len(result) == 2
        assert result["pref_1"] is None
        assert result["pref_2"] is None

    @pytest.mark.asyncio
    async def test_batch_fetch_unwraps_nested_results(self, gardener, mock_preference_collection):
        """Test que les résultats nested sont unwrapped correctement."""
        # Certaines versions ChromaDB retournent [[ids]], [[metadatas]]
        mock_preference_collection.get = Mock(return_value={
            "ids": [["pref_1", "pref_2"]],  # Nested
            "metadatas": [[{"confidence": 0.8}, {"confidence": 0.9}]],  # Nested
            "documents": [["Doc1", "Doc2"]]  # Nested
        })

        result = await gardener._get_existing_preferences_batch(["pref_1", "pref_2"])

        assert len(result) == 2
        assert result["pref_1"]["id"] == "pref_1"
        assert result["pref_2"]["id"] == "pref_2"


class TestStorePreferenceRecordsOptimization:
    """Tests de l'optimisation _store_preference_records avec batch fetch."""

    @pytest.mark.asyncio
    async def test_batch_fetch_called_once(self, gardener, mock_preference_collection):
        """Test que le batch fetch est appelé une seule fois pour plusieurs préférences."""
        # Mock synchrone compatible
        def mock_get(*args, **kwargs):
            return {"ids": [], "metadatas": [], "documents": []}

        mock_preference_collection.get = Mock(side_effect=mock_get)

        # Appeler directement _get_existing_preferences_batch
        preference_ids = [f"pref_{i}" for i in range(5)]
        await gardener._get_existing_preferences_batch(preference_ids)

        # Vérifier 1 seul appel
        assert mock_preference_collection.get.call_count == 1

        # Vérifier que l'appel contenait tous les IDs
        call_args = mock_preference_collection.get.call_args
        assert call_args[1]["ids"] == preference_ids

    @pytest.mark.asyncio
    async def test_batch_fetch_handles_existing(self, gardener, mock_preference_collection):
        """Test que le batch fetch gère correctement les préférences existantes."""
        # Mock avec pref_1 existant
        def mock_get(*args, **kwargs):
            ids = kwargs.get("ids", [])
            if "pref_1" in ids:
                return {
                    "ids": ["pref_1"],
                    "metadatas": [{
                        "confidence": 0.9,
                        "occurrences": 3
                    }],
                    "documents": ["Aime le café"]
                }
            return {"ids": [], "metadatas": [], "documents": []}

        mock_preference_collection.get = Mock(side_effect=mock_get)

        result = await gardener._get_existing_preferences_batch(["pref_1", "pref_2"])

        # pref_1 devrait exister
        assert result["pref_1"] is not None
        assert result["pref_1"]["metadata"]["confidence"] == 0.9

        # pref_2 devrait être None
        assert result["pref_2"] is None


class TestBatchFetchPerformance:
    """Tests de performance comparant batch fetch vs N+1."""

    @pytest.mark.asyncio
    async def test_batch_single_call_vs_multiple_calls(self, gardener, mock_preference_collection):
        """Test que le batch fetch fait 1 seul appel au lieu de N appels."""
        num_prefs = 20

        # Mock synchrone (compatible avec asyncio.to_thread)
        def mock_get(*args, **kwargs):
            ids = kwargs.get("ids", [])
            return {
                "ids": ids,
                "metadatas": [{} for _ in ids],
                "documents": ["" for _ in ids]
            }

        mock_preference_collection.get = Mock(side_effect=mock_get)

        # Appel batch
        await gardener._get_existing_preferences_batch(
            [f"pref_{i}" for i in range(num_prefs)]
        )

        # Vérifier que get a été appelé UNE SEULE FOIS
        assert mock_preference_collection.get.call_count == 1

        # Vérifier que tous les IDs étaient dans l'appel
        call_args = mock_preference_collection.get.call_args
        assert len(call_args[1]["ids"]) == num_prefs

    @pytest.mark.asyncio
    async def test_batch_returns_correct_count(self, gardener, mock_preference_collection):
        """Test que le batch fetch retourne le bon nombre de résultats."""
        test_sizes = [1, 5, 10, 50]

        for size in test_sizes:
            def mock_get(*args, **kwargs):
                ids = kwargs.get("ids", [])
                return {
                    "ids": ids,
                    "metadatas": [{} for _ in ids],
                    "documents": ["" for _ in ids]
                }

            mock_preference_collection.get = Mock(side_effect=mock_get)

            result = await gardener._get_existing_preferences_batch(
                [f"pref_{i}" for i in range(size)]
            )

            # Devrait retourner exactement `size` résultats
            assert len(result) == size
            assert all(f"pref_{i}" in result for i in range(size))
