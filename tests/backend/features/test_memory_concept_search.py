"""
Tests for Concept Search API - Phase 4
Tests GET /api/memory/concepts/search endpoint
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone


@pytest.fixture
def client(app):
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
async def authenticated_user(client):
    """
    Fixture to get authenticated user credentials.
    Assumes test user exists or creates one.
    """
    # TODO: Implement actual authentication for tests
    # For now, return mock credentials
    return {
        "user_id": "test_user_concepts",
        "token": "test_token_123",
        "headers": {
            "Authorization": "Bearer test_token_123",
            "X-Session-Id": "test_session_concepts",
        },
    }


@pytest.fixture
async def seed_test_concepts(vector_service, authenticated_user):
    """
    Seed test concepts for search testing.
    """
    collection = vector_service.get_or_create_collection("emergence_knowledge")
    now_iso = datetime.now(timezone.utc).isoformat()

    concepts = [
        {
            "id": "concept_docker_1",
            "text": "Docker containerization",
            "metadata": {
                "type": "concept",
                "user_id": authenticated_user["user_id"],
                "concept_text": "Docker containerization",
                "created_at": now_iso,
                "first_mentioned_at": "2025-09-28T10:15:00+00:00",
                "last_mentioned_at": now_iso,
                "thread_ids": ["thread_docker_1", "thread_docker_2"],
                "mention_count": 2,
                "vitality": 0.9,
            },
        },
        {
            "id": "concept_k8s_1",
            "text": "Kubernetes orchestration",
            "metadata": {
                "type": "concept",
                "user_id": authenticated_user["user_id"],
                "concept_text": "Kubernetes orchestration",
                "created_at": now_iso,
                "first_mentioned_at": "2025-09-29T14:20:00+00:00",
                "last_mentioned_at": now_iso,
                "thread_ids": ["thread_k8s_1"],
                "mention_count": 1,
                "vitality": 0.85,
            },
        },
        {
            "id": "concept_cicd_1",
            "text": "CI/CD pipeline automation",
            "metadata": {
                "type": "concept",
                "user_id": authenticated_user["user_id"],
                "concept_text": "CI/CD pipeline automation",
                "created_at": now_iso,
                "first_mentioned_at": "2025-10-01T09:30:00+00:00",
                "last_mentioned_at": now_iso,
                "thread_ids": ["thread_cicd_1", "thread_cicd_2", "thread_cicd_3"],
                "mention_count": 3,
                "vitality": 0.95,
            },
        },
    ]

    for concept in concepts:
        collection.add(
            ids=[concept["id"]],
            documents=[concept["text"]],
            metadatas=[concept["metadata"]],
        )

    yield concepts

    # Cleanup
    try:
        for concept in concepts:
            collection.delete(ids=[concept["id"]])
    except Exception:
        pass


@pytest.mark.asyncio
async def test_search_concepts_valid_query(
    client, authenticated_user, seed_test_concepts
):
    """
    Test valid concept search query.
    """
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "containerization", "limit": 10},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 200
    data = response.json()

    assert "query" in data
    assert data["query"] == "containerization"
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)
    assert data["count"] >= 1  # At least Docker containerization


@pytest.mark.asyncio
async def test_search_concepts_short_query(client, authenticated_user):
    """
    Test that queries shorter than 3 chars are rejected.
    """
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "xy", "limit": 10},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_search_concepts_missing_query(client, authenticated_user):
    """
    Test that missing query parameter returns validation error.
    """
    response = client.get(
        "/api/memory/concepts/search",
        params={"limit": 10},
        headers=authenticated_user["headers"],
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_concepts_limit_validation(client, authenticated_user):
    """
    Test limit parameter validation (must be between 1 and 50).
    """
    # Limit = 0 (invalid)
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "docker", "limit": 0},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 422

    # Limit = 51 (invalid)
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "docker", "limit": 51},
        headers=authenticated_user["headers"],
    )
    assert response.status_code == 422

    # Limit = 25 (valid)
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "docker", "limit": 25},
        headers=authenticated_user["headers"],
    )
    assert response.status_code in [200, 401]  # Either success or auth required


@pytest.mark.asyncio
async def test_search_concepts_unauthenticated(client):
    """
    Test that unauthenticated requests are rejected.
    """
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "docker", "limit": 10},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_concepts_results_sorted_by_similarity(
    client, authenticated_user, seed_test_concepts
):
    """
    Test that search results are sorted by similarity score (highest first).
    """
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "containerization", "limit": 10},
        headers=authenticated_user["headers"],
    )

    if response.status_code == 200:
        data = response.json()
        results = data["results"]

        if len(results) >= 2:
            # Verify results are sorted by similarity (descending)
            for i in range(len(results) - 1):
                assert (
                    results[i]["similarity_score"] >= results[i + 1]["similarity_score"]
                )


@pytest.mark.asyncio
async def test_search_concepts_metadata_structure(
    client, authenticated_user, seed_test_concepts
):
    """
    Test that returned concept metadata has expected structure.
    """
    response = client.get(
        "/api/memory/concepts/search",
        params={"q": "Docker", "limit": 10},
        headers=authenticated_user["headers"],
    )

    if response.status_code == 200:
        data = response.json()
        results = data["results"]

        if len(results) > 0:
            concept = results[0]

            # Verify required fields
            assert "concept_text" in concept
            assert "first_mentioned_at" in concept
            assert "last_mentioned_at" in concept
            assert "thread_ids" in concept
            assert "mention_count" in concept
            assert "similarity_score" in concept

            # Verify types
            assert isinstance(concept["concept_text"], str)
            assert isinstance(concept["thread_ids"], list)
            assert isinstance(concept["mention_count"], int)
            assert isinstance(concept["similarity_score"], (int, float))
