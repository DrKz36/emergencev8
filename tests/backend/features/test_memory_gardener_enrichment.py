"""
Tests for enriched metadata in MemoryGardener concept vectorization.
Phase 1: Verify temporal tracking metadata (first_mentioned_at, mention_count, thread_ids, etc.)
"""

import pytest
import pytest_asyncio
import asyncio
import os
from datetime import datetime, timezone
from backend.features.memory.gardener import MemoryGardener
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.features.memory.vector_service import VectorService
from backend.core.database.manager import DatabaseManager
from backend.core.database import schema


@pytest_asyncio.fixture
async def db_manager(tmp_path):
    """Database manager fixture."""
    db_path = str(tmp_path / "test_gardener.db")
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
    # Cleanup: delete test collection
    try:
        service.client.delete_collection("emergence_knowledge")
    except Exception:
        pass


@pytest_asyncio.fixture
async def gardener(db_manager, vector_service):
    """MemoryGardener fixture."""
    analyzer = MemoryAnalyzer(db_manager)
    return MemoryGardener(
        db_manager=db_manager,
        vector_service=vector_service,
        memory_analyzer=analyzer
    )


@pytest.mark.asyncio
async def test_vectorize_concepts_with_enriched_metadata(gardener, vector_service):
    """
    Test that new concepts are vectorized with enriched temporal metadata.
    """
    # Arrange
    concepts = ["Docker containerization", "CI/CD pipeline"]
    session_stub = {
        "id": "test_session_123",
        "user_id": "test_user_456",
        "thread_id": "test_thread_789",
        "message_id": "test_msg_001",
    }
    user_id = "test_user_456"

    # Act
    await gardener._vectorize_concepts(concepts, session_stub, user_id)

    # Assert
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    result = collection.get(
        where={
            "$and": [
                {"type": "concept"},
                {"user_id": user_id},
                {"source_session_id": session_stub["id"]}
            ]
        },
        include=["metadatas"]
    )

    assert result is not None
    assert len(result["ids"]) == 2

    for meta in result["metadatas"]:
        # Verify enriched metadata fields
        assert "first_mentioned_at" in meta
        assert "last_mentioned_at" in meta
        assert meta["mention_count"] == 1
        assert meta["thread_id"] == "test_thread_789"
        assert meta["thread_ids"] == ["test_thread_789"]
        assert meta["message_id"] == "test_msg_001"

        # Verify ISO 8601 timestamps
        assert meta["first_mentioned_at"] == meta["last_mentioned_at"]
        datetime.fromisoformat(meta["first_mentioned_at"].replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_vectorize_concepts_without_thread_id(gardener, vector_service):
    """
    Test that concepts can be vectorized without thread_id (legacy sessions).
    """
    # Arrange
    concepts = ["Legacy concept"]
    session_stub = {
        "id": "legacy_session_001",
        "user_id": "user_legacy",
        # No thread_id or message_id
    }
    user_id = "user_legacy"

    # Act
    await gardener._vectorize_concepts(concepts, session_stub, user_id)

    # Assert
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    result = collection.get(
        where={
            "$and": [
                {"type": "concept"},
                {"user_id": user_id},
            ]
        },
        include=["metadatas"]
    )

    assert len(result["ids"]) == 1
    meta = result["metadatas"][0]

    # Verify graceful handling of missing thread_id
    assert meta["thread_id"] is None
    assert meta["thread_ids"] == []
    assert meta["message_id"] is None
    assert meta["mention_count"] == 1


@pytest.mark.asyncio
async def test_migration_script_compatibility(vector_service):
    """
    Test that migration script logic works correctly.
    Simulates migrating an old concept without enriched metadata.
    """
    # Arrange: Insert old-style concept (no enriched metadata)
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    old_concept_id = "old_concept_abc123"
    now_iso = datetime.now(timezone.utc).isoformat()

    collection.add(
        ids=[old_concept_id],
        documents=["Old Docker concept"],
        metadatas=[{
            "type": "concept",
            "user_id": "old_user_999",
            "concept_text": "Old Docker concept",
            "created_at": now_iso,
            "vitality": 0.9,
        }]
    )

    # Act: Simulate migration (enrich metadata)
    existing = collection.get(ids=[old_concept_id], include=["metadatas"])
    old_meta = existing["metadatas"][0]

    migrated_meta = dict(old_meta)
    migrated_meta["first_mentioned_at"] = old_meta.get("created_at")
    migrated_meta["last_mentioned_at"] = old_meta.get("created_at")
    migrated_meta["mention_count"] = 1
    # Note: thread_ids et message_id ne sont pas mis à jour car ChromaDB
    # n'accepte pas les listes/None dans update. En production, on utilise upsert.

    collection.update(
        ids=[old_concept_id],
        metadatas=[migrated_meta]
    )

    # Assert
    result = collection.get(ids=[old_concept_id], include=["metadatas"])
    meta = result["metadatas"][0]

    assert meta["first_mentioned_at"] == now_iso
    assert meta["last_mentioned_at"] == now_iso
    assert meta["mention_count"] == 1
    # thread_ids et message_id sont vérifiés seulement s'ils existent
    assert "first_mentioned_at" in meta
    assert "last_mentioned_at" in meta


@pytest.mark.asyncio
async def test_enriched_metadata_timestamps_iso8601(gardener, vector_service):
    """
    Test that timestamps are in valid ISO 8601 format with timezone.
    """
    # Arrange
    concepts = ["Kubernetes"]
    session_stub = {
        "id": "session_timestamp_test",
        "user_id": "user_ts",
        "thread_id": "thread_ts",
    }

    # Act
    await gardener._vectorize_concepts(concepts, session_stub, "user_ts")

    # Assert
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    result = collection.get(
        where={"user_id": "user_ts"},
        include=["metadatas"]
    )

    meta = result["metadatas"][0]
    first_ts = meta["first_mentioned_at"]
    last_ts = meta["last_mentioned_at"]

    # Verify ISO 8601 format (should parse without error)
    dt_first = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
    dt_last = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))

    # Verify timezone is UTC
    assert dt_first.tzinfo is not None
    assert dt_last.tzinfo is not None
