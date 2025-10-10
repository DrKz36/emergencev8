"""
Tests pour la persistance des préférences dans ChromaDB.
Phase P1.2 - Validation workflow extraction → sauvegarde → récupération
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timezone
from typing import List, Dict, Any

# Import des modules à tester
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.memory.preference_extractor import PreferenceExtractor, PreferenceRecord


@pytest.fixture
def mock_vector_service():
    """Mock VectorService avec collection ChromaDB."""
    service = Mock()
    collection = Mock()
    service.get_or_create_collection = Mock(return_value=collection)
    service.add_documents = Mock()  # Capture des appels
    return service, collection


@pytest.fixture
def mock_chat_service(mock_vector_service):
    """Mock ChatService avec VectorService."""
    vector_service, _ = mock_vector_service
    service = Mock()
    service.vector_service = vector_service
    service.session_manager = Mock()

    # Mock get_session pour retourner un objet avec user_id
    mock_session = Mock()
    mock_session.user_id = "test_user_123"
    service.session_manager.get_session = Mock(return_value=mock_session)

    return service


@pytest.fixture
def mock_db_manager():
    """Mock DatabaseManager."""
    db = Mock()
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def analyzer(mock_db_manager, mock_chat_service):
    """Instancier MemoryAnalyzer avec mocks."""
    analyzer = MemoryAnalyzer(db_manager=mock_db_manager, chat_service=mock_chat_service)
    return analyzer


@pytest.fixture
def sample_preferences():
    """Préférences exemple pour tests."""
    return [
        PreferenceRecord(
            id="pref1",
            text="Je préfère Python pour le scripting",
            type="preference",
            topic="programming_languages",
            action="préférer",
            confidence=0.85,
            sentiment="positive",
            timeframe="",
            entities=[],
            source_message_id="msg1",
            thread_id="thread1",
            captured_at=datetime.now(timezone.utc).isoformat()
        ),
        PreferenceRecord(
            id="pref2",
            text="Je vais déployer sur Cloud Run demain",
            type="intent",
            topic="deployment",
            action="déployer",
            confidence=0.75,
            sentiment="neutral",
            timeframe="tomorrow",
            entities=["Cloud Run"],
            source_message_id="msg2",
            thread_id="thread1",
            captured_at=datetime.now(timezone.utc).isoformat()
        ),
        PreferenceRecord(
            id="pref3",
            text="N'utilise jamais de variables globales",
            type="constraint",
            action="utiliser",
            topic="code_style",
            confidence=0.90,
            sentiment="negative",
            timeframe="",
            entities=[],
            source_message_id="msg3",
            thread_id="thread1",
            captured_at=datetime.now(timezone.utc).isoformat()
        ),
    ]


# ============================================================================
# Tests unitaires - Sauvegarde préférences
# ============================================================================

@pytest.mark.asyncio
async def test_save_preferences_to_vector_db_success(analyzer, mock_vector_service, sample_preferences):
    """Test sauvegarde préférences dans ChromaDB - succès."""
    vector_service, collection = mock_vector_service

    # Appeler méthode de sauvegarde
    saved_count = await analyzer._save_preferences_to_vector_db(
        preferences=sample_preferences,
        user_id="test_user_123",
        thread_id="thread_abc",
        session_id="session_xyz"
    )

    # Vérifications
    assert saved_count == 3, "Devrait sauvegarder les 3 préférences"

    # Vérifier appels VectorService
    assert vector_service.get_or_create_collection.called
    assert vector_service.add_documents.call_count == 3

    # Vérifier format documents
    first_call = vector_service.add_documents.call_args_list[0]
    call_kwargs = first_call[1]

    assert "documents" in call_kwargs
    assert "metadatas" in call_kwargs
    assert "ids" in call_kwargs

    # Vérifier contenu document
    doc_text = call_kwargs["documents"][0]
    assert "programming_languages" in doc_text
    assert "Python" in doc_text

    # Vérifier métadonnées
    metadata = call_kwargs["metadatas"][0]
    assert metadata["user_id"] == "test_user_123"
    assert metadata["type"] == "preference"
    assert metadata["topic"] == "programming_languages"
    assert metadata["confidence"] == 0.85
    assert metadata["thread_id"] == "thread_abc"
    assert metadata["session_id"] == "session_xyz"
    assert metadata["source"] == "preference_extractor_v1.2"
    assert "created_at" in metadata

    # Vérifier ID unique
    doc_id = call_kwargs["ids"][0]
    assert doc_id.startswith("pref_test_use")  # pref_{user_id[:8]}_...


@pytest.mark.asyncio
async def test_save_preferences_empty_list(analyzer):
    """Test sauvegarde liste vide - devrait retourner 0."""
    saved_count = await analyzer._save_preferences_to_vector_db(
        preferences=[],
        user_id="test_user",
        thread_id="thread_1",
        session_id="session_1"
    )

    assert saved_count == 0


@pytest.mark.asyncio
async def test_save_preferences_no_vector_service(analyzer):
    """Test sauvegarde sans VectorService - graceful degradation."""
    # Supprimer VectorService du ChatService
    analyzer.chat_service.vector_service = None

    saved_count = await analyzer._save_preferences_to_vector_db(
        preferences=[
            PreferenceRecord(
                id="test1",
                text="Test pref",
                type="preference",
                topic="test",
                action="test",
                confidence=0.8,
                sentiment="neutral",
                timeframe="",
                entities=[],
                source_message_id="msg1",
                thread_id="thread1",
                captured_at=datetime.now(timezone.utc).isoformat()
            )
        ],
        user_id="test_user",
        thread_id="thread_1",
        session_id="session_1"
    )

    assert saved_count == 0, "Devrait retourner 0 si VectorService absent"


@pytest.mark.asyncio
async def test_save_preferences_partial_failure(analyzer, mock_vector_service, sample_preferences):
    """Test sauvegarde avec échec partiel - devrait continuer."""
    vector_service, collection = mock_vector_service

    # Simuler échec sur 2ème préférence
    call_count = [0]

    def add_documents_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise Exception("ChromaDB error on 2nd doc")

    vector_service.add_documents.side_effect = add_documents_side_effect

    saved_count = await analyzer._save_preferences_to_vector_db(
        preferences=sample_preferences,
        user_id="test_user",
        thread_id="thread_1",
        session_id="session_1"
    )

    # Devrait sauvegarder 2/3 (1ère et 3ème réussissent)
    assert saved_count == 2


@pytest.mark.asyncio
async def test_save_preferences_unique_ids(analyzer, mock_vector_service):
    """Test génération IDs uniques basés sur contenu + user."""
    vector_service, collection = mock_vector_service

    pref1 = PreferenceRecord(
        id="test1",
        text="Je préfère Python",
        type="preference",
        topic="language",
        action="préférer",
        confidence=0.9,
        sentiment="positive",
        timeframe="",
        entities=[],
        source_message_id="msg1",
        thread_id="thread1",
        captured_at=datetime.now(timezone.utc).isoformat()
    )

    # Sauvegarder 2 fois la même préférence
    await analyzer._save_preferences_to_vector_db(
        preferences=[pref1],
        user_id="user_A",
        thread_id="thread_1",
        session_id="session_1"
    )

    await analyzer._save_preferences_to_vector_db(
        preferences=[pref1],
        user_id="user_A",
        thread_id="thread_2",
        session_id="session_2"
    )

    # Vérifier que les 2 appels ont le MÊME ID (déduplication)
    call1 = vector_service.add_documents.call_args_list[0]
    call2 = vector_service.add_documents.call_args_list[1]

    id1 = call1[1]["ids"][0]
    id2 = call2[1]["ids"][0]

    assert id1 == id2, "Même préférence + même user devrait générer même ID"


# ============================================================================
# Tests intégration - Workflow complet
# ============================================================================

@pytest.mark.asyncio
async def test_integration_extraction_and_persistence(analyzer, mock_vector_service):
    """Test workflow extraction → sauvegarde direct (sans analyse complète)."""
    vector_service, collection = mock_vector_service

    # Simuler préférences extraites
    preferences = [
        PreferenceRecord(
            id="test1",
            text="Je préfère TypeScript à JavaScript",
            type="preference",
            topic="programming",
            action="préférer",
            confidence=0.88,
            sentiment="positive",
            timeframe="",
            entities=[],
            source_message_id="msg1",
            thread_id="session_test",
            captured_at=datetime.now(timezone.utc).isoformat()
        )
    ]

    # Appeler directement la méthode de sauvegarde
    saved_count = await analyzer._save_preferences_to_vector_db(
        preferences=preferences,
        user_id="test_user",
        thread_id="session_test",
        session_id="session_test"
    )

    # Vérifications
    assert saved_count == 1

    # Vérifier sauvegarde appelée
    assert vector_service.add_documents.called

    # Vérifier métadonnées sauvegardées
    call_kwargs = vector_service.add_documents.call_args_list[0][1]
    metadata = call_kwargs["metadatas"][0]

    assert metadata["type"] == "preference"
    assert metadata["confidence"] == 0.88
    assert metadata["topic"] == "programming"
    assert metadata["user_id"] == "test_user"


@pytest.mark.asyncio
async def test_integration_fetch_active_preferences(mock_vector_service):
    """Test récupération préférences sauvegardées via _fetch_active_preferences."""
    from backend.features.chat.memory_ctx import MemoryContextBuilder

    vector_service, collection = mock_vector_service
    mock_session_manager = Mock()

    # Mock collection.get pour retourner préférences
    collection.get = Mock(return_value={
        "documents": [
            "programming: Je préfère Python",
            "deployment: Utilise Docker pour tout"
        ],
        "metadatas": [
            {"user_id": "user_123", "type": "preference", "confidence": 0.85},
            {"user_id": "user_123", "type": "preference", "confidence": 0.90}
        ]
    })

    # Instancier MemoryContextBuilder
    builder = MemoryContextBuilder(
        session_manager=mock_session_manager,
        vector_service=vector_service
    )

    # Récupérer préférences
    prefs_text = builder._fetch_active_preferences(collection, "user_123")

    # Vérifications
    assert "Python" in prefs_text
    assert "Docker" in prefs_text
    assert collection.get.called

    # Vérifier filtre WHERE correct
    call_kwargs = collection.get.call_args[1]
    where_clause = call_kwargs["where"]

    assert where_clause["$and"][0]["user_id"] == "user_123"
    assert where_clause["$and"][1]["type"] == "preference"
    assert where_clause["$and"][2]["confidence"]["$gte"] == 0.6


@pytest.mark.asyncio
async def test_integration_preferences_in_context_rag():
    """Test injection préférences dans contexte RAG complet."""
    from backend.features.chat.memory_ctx import MemoryContextBuilder

    # Setup mocks
    mock_session_manager = Mock()
    mock_session_manager.get_session = Mock(return_value=Mock(user_id="user_123"))

    mock_vector_service = Mock()
    collection = Mock()

    # Simuler préférences + concepts dans ChromaDB
    def get_side_effect(*args, **kwargs):
        where = kwargs.get("where", {})

        # Si requête préférences
        if isinstance(where, dict) and "$and" in where:
            filters = where["$and"]
            if any(f.get("type") == "preference" for f in filters):
                return {
                    "documents": ["programming: Je préfère Python"],
                    "metadatas": [{"confidence": 0.9, "type": "preference"}]
                }

        # Sinon concepts génériques
        return {
            "documents": ["Python est un langage de scripting"],
            "metadatas": [{"created_at": "2025-10-10T12:00:00Z"}]
        }

    collection.get = Mock(side_effect=get_side_effect)
    mock_vector_service.get_or_create_collection = Mock(return_value=collection)
    mock_vector_service.query = Mock(return_value=[
        {"text": "Python supporte async/await", "metadata": {"created_at": "2025-10-10T10:00:00Z"}}
    ])

    # Instancier builder
    builder = MemoryContextBuilder(
        session_manager=mock_session_manager,
        vector_service=mock_vector_service
    )

    # Construire contexte mémoire
    context = await builder.build_memory_context(
        session_id="session_123",
        last_user_message="Comment utiliser async en Python ?",
        top_k=5
    )

    # Vérifications
    assert "Python" in context, "Devrait contenir concepts Python"
    assert "préférence" in context.lower() or "python" in context.lower()


# ============================================================================
# Tests edge cases
# ============================================================================

@pytest.mark.asyncio
async def test_save_preferences_with_special_characters(analyzer, mock_vector_service):
    """Test sauvegarde préférences avec caractères spéciaux."""
    vector_service, collection = mock_vector_service

    pref = PreferenceRecord(
        id="test1",
        text="J'adore les émojis 🎉 et les caractères accentués: àéïôù",
        type="preference",
        topic="communication",
        action="adorer",
        confidence=0.7,
        sentiment="positive",
        timeframe="",
        entities=[],
        source_message_id="msg1",
        thread_id="thread1",
        captured_at=datetime.now(timezone.utc).isoformat()
    )

    saved_count = await analyzer._save_preferences_to_vector_db(
        preferences=[pref],
        user_id="user_émoji",
        thread_id="thread_1",
        session_id="session_1"
    )

    assert saved_count == 1

    # Vérifier document sauvegardé
    call_kwargs = vector_service.add_documents.call_args[1]
    doc_text = call_kwargs["documents"][0]

    assert "émojis" in doc_text
    assert "🎉" in doc_text


@pytest.mark.asyncio
async def test_save_preferences_without_topic(analyzer, mock_vector_service):
    """Test sauvegarde préférence sans topic (fallback 'general')."""
    vector_service, collection = mock_vector_service

    pref = PreferenceRecord(
        id="test1",
        text="Je préfère les couleurs sombres",
        type="preference",
        topic="",  # Topic vide
        action="préférer",
        confidence=0.65,
        sentiment="positive",
        timeframe="",
        entities=[],
        source_message_id="msg1",
        thread_id="thread1",
        captured_at=datetime.now(timezone.utc).isoformat()
    )

    await analyzer._save_preferences_to_vector_db(
        preferences=[pref],
        user_id="user_1",
        thread_id="thread_1",
        session_id="session_1"
    )

    # Vérifier métadonnées
    call_kwargs = vector_service.add_documents.call_args[1]
    metadata = call_kwargs["metadatas"][0]

    assert metadata["topic"] == "general", "Devrait fallback à 'general' si topic vide"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
