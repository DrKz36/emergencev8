"""Tests de sécurité pour VectorService - Protection suppression globale.

Tests pour Bug #4 (P1): Validation récursive where_filter
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.backend.features.memory.vector_service import VectorService


@pytest.fixture
def vector_service():
    """Fixture VectorService avec mock minimal."""
    service = VectorService(
        persist_directory="./tmp_test_vector_store",
        embed_model_name="all-MiniLM-L6-v2"
    )
    # Mock pour éviter l'initialisation réelle
    service._inited = True
    service.model = Mock()
    service.backend = "chroma"
    service.client = Mock()
    return service


@pytest.fixture
def mock_collection():
    """Collection ChromaDB mockée."""
    collection = MagicMock()
    collection.name = "test_collection"
    collection.delete = MagicMock()
    return collection


class TestDeleteVectorsEmptyFilterProtection:
    """Tests de protection contre suppression globale avec filtres vides."""

    def test_delete_vectors_empty_filter_direct(self, vector_service, mock_collection):
        """Test protection: Filtre vide direct {}"""
        with pytest.raises(ValueError, match="empty or invalid filter"):
            vector_service.delete_vectors(mock_collection, {})

    def test_delete_vectors_empty_and_list(self, vector_service, mock_collection):
        """Test protection: Filtre avec $and vide []"""
        with pytest.raises(ValueError, match="empty or invalid filter"):
            vector_service.delete_vectors(mock_collection, {"$and": []})

    def test_delete_vectors_user_id_none(self, vector_service, mock_collection):
        """Test protection: Filtre avec user_id=None"""
        with pytest.raises(ValueError, match="empty or invalid filter"):
            vector_service.delete_vectors(mock_collection, {"user_id": None})

    def test_delete_vectors_nested_empty_and(self, vector_service, mock_collection):
        """Test protection: Filtre avec $and contenant dict vide"""
        with pytest.raises(ValueError, match="empty or invalid filter"):
            vector_service.delete_vectors(mock_collection, {"$and": [{}]})

    def test_delete_vectors_nested_user_id_none(self, vector_service, mock_collection):
        """Test protection: Filtre avec $and contenant user_id=None"""
        with pytest.raises(ValueError, match="empty or invalid filter"):
            vector_service.delete_vectors(mock_collection, {"$and": [{"user_id": None}]})

    def test_delete_vectors_all_none_values(self, vector_service, mock_collection):
        """Test protection: Filtre avec toutes valeurs None"""
        with pytest.raises(ValueError, match="empty or invalid filter"):
            vector_service.delete_vectors(
                mock_collection,
                {"user_id": None, "session_id": None}
            )

    def test_delete_vectors_valid_filter_succeeds(self, vector_service, mock_collection):
        """Test validation: Filtre valide devrait fonctionner"""
        # Filtre valide avec user_id non-None
        vector_service.delete_vectors(mock_collection, {"user_id": "user123"})

        # Vérifier que delete a été appelé
        mock_collection.delete.assert_called_once()

    def test_delete_vectors_valid_and_filter(self, vector_service, mock_collection):
        """Test validation: Filtre $and valide devrait fonctionner"""
        valid_filter = {
            "$and": [
                {"user_id": "user123"},
                {"type": "preference"}
            ]
        }
        vector_service.delete_vectors(mock_collection, valid_filter)

        # Vérifier que delete a été appelé
        mock_collection.delete.assert_called_once()

    def test_delete_vectors_mixed_valid_none_accepted(self, vector_service, mock_collection):
        """Test validation: Filtre mixte avec une valeur valide est accepté"""
        # Si au moins une clé a une valeur valide, le filtre est accepté
        # Note: {"user_id": "user123", "session_id": None} est valide car user_id != None
        vector_service.delete_vectors(
            mock_collection,
            {"user_id": "user123", "session_id": None}
        )
        # Vérifier que delete a été appelé
        mock_collection.delete.assert_called_once()


class TestIsFilterEmptyMethod:
    """Tests unitaires de la méthode _is_filter_empty."""

    def test_is_filter_empty_with_empty_dict(self, vector_service):
        """Filtre vide {} → True"""
        assert vector_service._is_filter_empty({}) is True

    def test_is_filter_empty_with_none(self, vector_service):
        """Filtre None → True"""
        assert vector_service._is_filter_empty(None) is True

    def test_is_filter_empty_with_user_id_none(self, vector_service):
        """Filtre {user_id: None} → True"""
        assert vector_service._is_filter_empty({"user_id": None}) is True

    def test_is_filter_empty_with_all_none_values(self, vector_service):
        """Filtre avec toutes valeurs None → True"""
        assert vector_service._is_filter_empty({
            "user_id": None,
            "session_id": None
        }) is True

    def test_is_filter_empty_with_empty_and(self, vector_service):
        """Filtre {$and: []} → True (liste vide, all([]) retourne True)"""
        # Note: all([]) retourne True en Python, donc liste vide considérée vide
        assert vector_service._is_filter_empty({"$and": []}) is True

    def test_is_filter_empty_with_and_containing_empty_dict(self, vector_service):
        """Filtre {$and: [{}]} → True"""
        assert vector_service._is_filter_empty({"$and": [{}]}) is True

    def test_is_filter_empty_with_and_containing_none(self, vector_service):
        """Filtre {$and: [{user_id: None}]} → True"""
        assert vector_service._is_filter_empty({"$and": [{"user_id": None}]}) is True

    def test_is_filter_empty_with_valid_filter(self, vector_service):
        """Filtre valide {user_id: "123"} → False"""
        assert vector_service._is_filter_empty({"user_id": "user123"}) is False

    def test_is_filter_empty_with_valid_and_filter(self, vector_service):
        """Filtre $and valide → False"""
        assert vector_service._is_filter_empty({
            "$and": [
                {"user_id": "user123"},
                {"type": "preference"}
            ]
        }) is False

    def test_is_filter_empty_with_nested_valid_or(self, vector_service):
        """Filtre $or valide → False"""
        assert vector_service._is_filter_empty({
            "$or": [
                {"user_id": "user1"},
                {"user_id": "user2"}
            ]
        }) is False

    def test_is_filter_empty_with_nested_empty_or(self, vector_service):
        """Filtre {$or: [{}]} → True"""
        assert vector_service._is_filter_empty({"$or": [{}]}) is True
