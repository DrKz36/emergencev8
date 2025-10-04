"""
Tests for ConceptRecallTracker - Phase 2
Tests detection, metadata updates, and event emission (when enabled).
"""

import pytest
import pytest_asyncio
import os
import json
from datetime import datetime, timezone
from backend.features.memory.concept_recall import ConceptRecallTracker
from backend.features.memory.vector_service import VectorService
from backend.core.database.manager import DatabaseManager
from backend.core.database import schema


@pytest_asyncio.fixture
async def db_manager(tmp_path):
    """Database manager fixture."""
    db_path = str(tmp_path / "test_concept_recall.db")
    db = DatabaseManager(db_path)
    await schema.create_tables(db)
    yield db
    await db.disconnect()


@pytest_asyncio.fixture
async def vector_service():
    """Vector service fixture."""
    persist_dir = os.getenv("EMERGENCE_VECTOR_DIR", "./src/backend/data/vector_store")
    embed_model = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
    service = VectorService(persist_directory=persist_dir, embed_model_name=embed_model)
    yield service
    # Cleanup
    try:
        service.client.delete_collection("emergence_knowledge")
    except Exception:
        pass


@pytest_asyncio.fixture
async def tracker(db_manager, vector_service):
    """ConceptRecallTracker fixture."""
    return ConceptRecallTracker(
        db_manager=db_manager,
        vector_service=vector_service,
        connection_manager=None,  # Phase 2: WS events disabled
    )


async def seed_concept(vector_service, **kwargs):
    """
    Helper to seed a concept in ChromaDB.
    Note: ChromaDB ne supporte pas les listes dans les métadonnées,
    donc on stocke thread_ids comme une chaîne JSON (thread_ids_json).
    """
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    concept_id = kwargs.get("concept_id", f"concept_{kwargs['concept_text'].replace(' ', '_')}")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Build thread_ids list
    thread_id = kwargs.get("thread_id")
    thread_ids = kwargs.get("thread_ids", [thread_id] if thread_id else [])

    # Métadonnées minimales que ChromaDB acceptera
    metadata = {
        "type": "concept",
        "user_id": kwargs.get("user_id", "test_user"),
        "concept_text": kwargs["concept_text"],
        "created_at": kwargs.get("created_at", now_iso),
        "first_mentioned_at": kwargs.get("first_mentioned_at", now_iso),
        "last_mentioned_at": kwargs.get("last_mentioned_at", now_iso),
        "thread_id": thread_id or "",
        "thread_ids_json": json.dumps(thread_ids),
        "message_id": kwargs.get("message_id") or "",
        "mention_count": kwargs.get("mention_count", 1),
        "vitality": kwargs.get("vitality", 0.9),
    }

    # Use add_items like production code
    item = {
        "id": concept_id,
        "text": kwargs["concept_text"],
        "metadata": metadata
    }
    vector_service.add_items(collection, [item])

    return concept_id


@pytest.mark.asyncio
async def test_detect_recurring_concepts_first_mention(tracker):
    """
    Test that no recurrence is detected on first mention.
    """
    # Arrange
    message_text = "Je veux setup une CI/CD pipeline"
    user_id = "user_123"
    thread_id = "thread_new"
    message_id = "msg_001"
    session_id = "session_xyz"

    # Act
    recalls = await tracker.detect_recurring_concepts(
        message_text=message_text,
        user_id=user_id,
        thread_id=thread_id,
        message_id=message_id,
        session_id=session_id,
    )

    # Assert
    assert recalls == []  # No existing concepts, no recurrence


@pytest.mark.asyncio
async def test_detect_recurring_concepts_second_mention(vector_service, tracker):
    """
    Test that recurrence is detected on second mention in different thread.
    """
    # Arrange: Seed existing concept
    await seed_concept(
        vector_service,
        concept_text="CI/CD pipeline",
        user_id="user_123",
        thread_id="thread_old",
        first_mentioned_at="2025-10-02T14:32:00+00:00",
    )

    # Act: Mention similar concept in new thread
    recalls = await tracker.detect_recurring_concepts(
        message_text="Comment améliorer notre pipeline CI/CD ?",
        user_id="user_123",
        thread_id="thread_new",
        message_id="msg_002",
        session_id="session_xyz",
    )

    # Assert
    assert len(recalls) == 1
    assert recalls[0]["concept_text"] == "CI/CD pipeline"
    assert recalls[0]["mention_count"] >= 1  # Will be incremented
    assert "thread_old" in recalls[0]["thread_ids"]
    assert recalls[0]["similarity_score"] >= 0.5  # Realistic threshold for semantic similarity


@pytest.mark.asyncio
async def test_detect_recurring_concepts_excludes_same_thread(vector_service, tracker):
    """
    Test that concepts mentioned only in current thread are excluded.
    """
    # Arrange: Seed concept in current thread only
    await seed_concept(
        vector_service,
        concept_text="Docker containerization",
        user_id="user_123",
        thread_id="thread_current",
        thread_ids=["thread_current"],
    )

    # Act: Mention same concept in same thread
    recalls = await tracker.detect_recurring_concepts(
        message_text="Docker containerization is great",
        user_id="user_123",
        thread_id="thread_current",
        message_id="msg_003",
        session_id="session_xyz",
    )

    # Assert
    assert recalls == []  # No cross-thread recurrence


@pytest.mark.asyncio
async def test_update_mention_metadata(vector_service, tracker):
    """
    Test that mention_count and thread_ids are updated correctly.
    """
    # Arrange: Seed concept
    concept_id = await seed_concept(
        vector_service,
        concept_text="Kubernetes orchestration",
        user_id="user_123",
        thread_id="thread_1",
        mention_count=1,
    )

    # Act: Detect recurrence in new thread
    recalls = await tracker.detect_recurring_concepts(
        message_text="Kubernetes orchestration setup",
        user_id="user_123",
        thread_id="thread_2",
        message_id="msg_004",
        session_id="session_xyz",
    )

    # Assert: Metadata should be updated
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    result = collection.get(ids=[concept_id], include=["metadatas"])
    meta = result["metadatas"][0]

    assert meta["mention_count"] == 2
    # Check thread_ids_json (JSON string)
    thread_ids_json = meta["thread_ids_json"]
    thread_ids = json.loads(thread_ids_json)
    assert "thread_2" in thread_ids
    assert meta["last_mentioned_at"] is not None
    # Vitality should be boosted
    assert meta["vitality"] > 0.9


@pytest.mark.asyncio
async def test_query_concept_history(vector_service, tracker):
    """
    Test explicit concept search (for user queries like "on a déjà parlé de X ?").
    """
    # Arrange: Seed multiple related concepts
    await seed_concept(
        vector_service,
        concept_text="Docker containerization",
        user_id="user_123",
        thread_id="thread_1",
    )
    await seed_concept(
        vector_service,
        concept_text="Kubernetes containers",
        user_id="user_123",
        thread_id="thread_2",
    )

    # Act: Query concept history
    history = await tracker.query_concept_history(
        concept_text="containerization",
        user_id="user_123",
        limit=10,
    )

    # Assert
    assert len(history) >= 1
    assert any("Docker" in h["concept_text"] or "container" in h["concept_text"].lower() for h in history)
    assert all(h["similarity_score"] >= 0.6 for h in history)  # Lower threshold for explicit search


@pytest.mark.asyncio
async def test_max_recalls_per_message_limit(vector_service, tracker):
    """
    Test that max 3 recalls are returned per message (avoid spam).
    """
    # Arrange: Seed 5 similar concepts
    for i in range(5):
        await seed_concept(
            vector_service,
            concept_text=f"CI/CD pipeline variant {i}",
            user_id="user_123",
            thread_id=f"thread_{i}",
        )

    # Act: Detect recurrences
    recalls = await tracker.detect_recurring_concepts(
        message_text="CI/CD pipeline setup",
        user_id="user_123",
        thread_id="thread_new",
        message_id="msg_005",
        session_id="session_xyz",
    )

    # Assert: Max 3 recalls
    assert len(recalls) <= ConceptRecallTracker.MAX_RECALLS_PER_MESSAGE


@pytest.mark.asyncio
async def test_emit_events_disabled_by_default():
    """
    Test that WebSocket events are NOT emitted in Phase 2 (disabled by default).
    """
    # Arrange
    os.environ["CONCEPT_RECALL_EMIT_EVENTS"] = "false"

    # Mock connection manager
    class MockConnectionManager:
        def __init__(self):
            self.messages_sent = []

        async def send_personal_message(self, message, session_id):
            self.messages_sent.append((message, session_id))

    mock_cm = MockConnectionManager()

    tracker = ConceptRecallTracker(
        db_manager=None,  # Not needed for this test
        vector_service=None,
        connection_manager=mock_cm,
    )

    # Act
    await tracker._emit_concept_recall_event(
        session_id="session_test",
        recalls=[{"concept_text": "Test"}],
    )

    # Assert: No messages sent (events disabled)
    assert len(mock_cm.messages_sent) == 0


@pytest.mark.asyncio
async def test_similarity_threshold_filtering(vector_service, tracker):
    """
    Test that only concepts above similarity threshold are detected.
    """
    # Arrange: Seed concept
    await seed_concept(
        vector_service,
        concept_text="Machine Learning models",
        user_id="user_123",
        thread_id="thread_1",
    )

    # Act: Query with very different text (should not match)
    recalls = await tracker.detect_recurring_concepts(
        message_text="How to cook pasta",  # Completely different topic
        user_id="user_123",
        thread_id="thread_2",
        message_id="msg_006",
        session_id="session_xyz",
    )

    # Assert: No recalls (below similarity threshold)
    assert recalls == []
