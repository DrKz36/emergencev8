"""
Unit tests for ProactiveHintEngine (Phase P2 Sprint 2).

Tests:
- Hint generation with preference match
- Concept recurrence tracking
- Relevance scoring
- Max hint limit (3)
- Intent followup hints

Run:
    python -m pytest tests/backend/features/test_proactive_hints.py -v
"""

import pytest
from unittest.mock import MagicMock
from backend.features.memory.proactive_hints import (
    ProactiveHintEngine,
    ProactiveHint,
    ConceptTracker,
)


@pytest.fixture
def mock_vector_service():
    """Mock VectorService for testing."""
    service = MagicMock()

    # Mock collection
    collection = MagicMock()
    collection.name = "emergence_knowledge"
    service.get_or_create_collection.return_value = collection

    # Mock query results (preferences)
    service.query.return_value = [
        {
            "id": "pref_123",
            "text": "I prefer Python for scripting",
            "metadata": {
                "user_id": "user_123",
                "type": "preference",
                "confidence": 0.85,
            },
            "distance": 0.15,  # High similarity
        },
        {
            "id": "pref_456",
            "text": "I like Docker for containerization",
            "metadata": {
                "user_id": "user_123",
                "type": "preference",
                "confidence": 0.75,
            },
            "distance": 0.25,
        },
    ]

    return service


@pytest.fixture
def hint_engine(mock_vector_service):
    """Create ProactiveHintEngine instance."""
    return ProactiveHintEngine(vector_service=mock_vector_service)


class TestConceptTracker:
    """Test ConceptTracker class."""

    @pytest.mark.asyncio
    async def test_track_mention_increments_counter(self):
        """Test that tracking increments counter correctly."""
        tracker = ConceptTracker()

        count1 = await tracker.track_mention("user_123", "python")
        assert count1 == 1

        count2 = await tracker.track_mention("user_123", "python")
        assert count2 == 2

        count3 = await tracker.track_mention("user_123", "python")
        assert count3 == 3

    @pytest.mark.asyncio
    async def test_track_mention_separate_users(self):
        """Test that different users have separate counters."""
        tracker = ConceptTracker()

        await tracker.track_mention("user_123", "python")
        await tracker.track_mention("user_123", "python")

        count_user_456 = await tracker.track_mention("user_456", "python")
        assert count_user_456 == 1  # Separate counter

    @pytest.mark.asyncio
    async def test_reset_counter(self):
        """Test resetting counter for specific concept."""
        tracker = ConceptTracker()

        await tracker.track_mention("user_123", "python")
        await tracker.track_mention("user_123", "python")
        await tracker.track_mention("user_123", "python")

        await tracker.reset_counter("user_123", "python")

        count = await tracker.track_mention("user_123", "python")
        assert count == 1  # Reset to 0, then incremented to 1


class TestProactiveHintEngine:
    """Test ProactiveHintEngine class."""

    @pytest.mark.asyncio
    async def test_generate_hints_preference_match(self, hint_engine):
        """Test hint generation when concept matches preference."""
        # Simulate concept mentioned 3 times (threshold reached)
        await hint_engine.concept_tracker.track_mention("user_123", "python")
        await hint_engine.concept_tracker.track_mention("user_123", "python")
        await hint_engine.concept_tracker.track_mention("user_123", "python")

        # Generate hints
        hints = await hint_engine.generate_hints(
            user_id="user_123",
            current_context={
                "topic": "scripting",
                "message": "I need to write a python script",
            },
        )

        # Assertions
        assert len(hints) > 0, "Should generate at least one hint"
        hint = hints[0]
        assert hint.type == "preference_reminder"
        assert "python" in hint.message.lower()
        assert hint.relevance_score > 0.6  # High relevance
        assert hint.source_preference_id == "pref_123"

    @pytest.mark.asyncio
    async def test_generate_hints_no_match_below_threshold(self, hint_engine):
        """Test no hints generated when concept mentioned < 3 times."""
        # Mention only 1 time (below threshold)
        # Note: generate_hints() will track the concept from the message, so total = 2 (still below 3)
        await hint_engine.concept_tracker.track_mention("user_123", "docker")

        hints = await hint_engine.generate_hints(
            user_id="user_123",
            current_context={
                "topic": "containers",
                "message": "How do I use docker?",  # This will track "docker" once more (total = 2)
            },
        )

        # Should not generate preference reminder (below threshold of 3)
        pref_hints = [
            h
            for h in hints
            if h.type == "preference_reminder" and "docker" in h.message.lower()
        ]
        assert len(pref_hints) == 0

    @pytest.mark.asyncio
    async def test_generate_hints_max_limit(self, hint_engine):
        """Test max 3 hints returned."""
        # Setup multiple concepts above threshold
        for concept in ["python", "docker", "kubernetes", "terraform", "ansible"]:
            for _ in range(3):
                await hint_engine.concept_tracker.track_mention("user_123", concept)

        hints = await hint_engine.generate_hints(
            user_id="user_123",
            current_context={
                "topic": "devops",
                "message": "I need to set up python, docker, kubernetes, terraform, and ansible",
            },
        )

        # Max 3 hints enforced
        assert len(hints) <= hint_engine.max_hints_per_call
        assert len(hints) <= 3

    @pytest.mark.asyncio
    async def test_generate_hints_sorted_by_relevance(self, hint_engine):
        """Test hints are sorted by relevance score descending."""
        # Mock vector service to return varied distances
        hint_engine.vector_service.query.return_value = [
            {
                "id": "pref_1",
                "text": "Low relevance preference",
                "metadata": {
                    "user_id": "user_123",
                    "type": "preference",
                    "confidence": 0.65,
                },
                "distance": 0.8,  # Low relevance (high distance)
            },
            {
                "id": "pref_2",
                "text": "High relevance preference",
                "metadata": {
                    "user_id": "user_123",
                    "type": "preference",
                    "confidence": 0.95,
                },
                "distance": 0.1,  # High relevance (low distance)
            },
        ]

        # Trigger hints for multiple concepts
        for concept in ["test1", "test2"]:
            for _ in range(3):
                await hint_engine.concept_tracker.track_mention("user_123", concept)

        hints = await hint_engine.generate_hints(
            user_id="user_123", current_context={"message": "test1 and test2"}
        )

        # Verify sorted by relevance (descending)
        if len(hints) > 1:
            for i in range(len(hints) - 1):
                assert hints[i].relevance_score >= hints[i + 1].relevance_score

    @pytest.mark.asyncio
    async def test_generate_hints_filters_low_relevance(self, hint_engine):
        """Test low relevance hints are filtered out."""
        # Mock very low relevance results
        hint_engine.vector_service.query.return_value = [
            {
                "id": "pref_low",
                "text": "Unrelated preference",
                "metadata": {
                    "user_id": "user_123",
                    "type": "preference",
                    "confidence": 0.5,
                },
                "distance": 0.95,  # Very low relevance
            }
        ]

        # Trigger concept above threshold
        for _ in range(3):
            await hint_engine.concept_tracker.track_mention("user_123", "irrelevant")

        hints = await hint_engine.generate_hints(
            user_id="user_123", current_context={"message": "irrelevant topic"}
        )

        # Should filter out hints with relevance < 0.6
        assert all(h.relevance_score >= hint_engine.min_relevance_score for h in hints)

    @pytest.mark.asyncio
    async def test_generate_hints_resets_counter_after_hint(self, hint_engine):
        """Test counter resets after hint is generated."""
        # Track concept to threshold
        for _ in range(3):
            await hint_engine.concept_tracker.track_mention("user_123", "python")

        # Generate hint (should reset counter)
        await hint_engine.generate_hints(
            user_id="user_123", current_context={"message": "python script"}
        )

        # Verify counter was reset
        count = await hint_engine.concept_tracker.track_mention("user_123", "python")
        assert count == 1  # Reset to 0, then incremented to 1

    @pytest.mark.asyncio
    async def test_generate_hints_intent_followup(self, hint_engine):
        """Test intent followup hints."""
        # Mock vector service to return intents
        hint_engine.vector_service.query.return_value = [
            {
                "id": "intent_123",
                "text": "Learn Docker containerization",
                "metadata": {"user_id": "user_123", "type": "intent"},
                "distance": 0.2,  # High relevance
            }
        ]

        hints = await hint_engine.generate_hints(
            user_id="user_123",
            current_context={"message": "Working on containerization"},
        )

        # Should include intent followup hint
        intent_hints = [h for h in hints if h.type == "intent_followup"]
        assert len(intent_hints) > 0

        hint = intent_hints[0]
        assert "Learn Docker containerization" in hint.message
        assert hint.relevance_score > 0.6

    @pytest.mark.asyncio
    async def test_generate_hints_empty_user_id(self, hint_engine):
        """Test graceful handling of empty user_id."""
        hints = await hint_engine.generate_hints(
            user_id="", current_context={"message": "test"}
        )

        assert hints == []

    def test_extract_concepts_simple(self, hint_engine):
        """Test simple concept extraction."""
        text = "I want to learn Python and Docker for containerization projects"

        concepts = hint_engine._extract_concepts_simple(text)

        # Should extract words > 4 chars
        assert "python" in concepts
        assert "docker" in concepts
        assert "containerization" in concepts
        assert "projects" in concepts

        # Should not include short words
        assert "want" not in concepts  # 4 chars
        assert "and" not in concepts
        assert "for" not in concepts

    def test_extract_concepts_deduplication(self, hint_engine):
        """Test concept deduplication."""
        text = "python python python docker docker"

        concepts = hint_engine._extract_concepts_simple(text)

        # Should deduplicate
        assert concepts.count("python") == 1
        assert concepts.count("docker") == 1

    def test_proactive_hint_to_dict(self):
        """Test ProactiveHint serialization to dict."""
        hint = ProactiveHint(
            id="hint_123",
            type="preference_reminder",
            title="Test Hint",
            message="This is a test hint",
            relevance_score=0.85,
            source_preference_id="pref_456",
            action_label="Apply",
            action_payload={"key": "value"},
        )

        hint_dict = hint.to_dict()

        assert hint_dict["id"] == "hint_123"
        assert hint_dict["type"] == "preference_reminder"
        assert hint_dict["relevance_score"] == 0.85
        assert hint_dict["action_payload"]["key"] == "value"


class TestProactiveHintEngineConfiguration:
    """Test configuration parameters."""

    def test_default_configuration(self, hint_engine):
        """Test default engine configuration."""
        assert hint_engine.max_hints_per_call == 3
        assert hint_engine.recurrence_threshold == 3
        assert hint_engine.min_relevance_score == 0.6

    @pytest.mark.asyncio
    async def test_custom_recurrence_threshold(self, mock_vector_service):
        """Test custom recurrence threshold."""
        engine = ProactiveHintEngine(vector_service=mock_vector_service)
        engine.recurrence_threshold = 2  # Lower threshold

        # Track concept 2 times (new threshold)
        await engine.concept_tracker.track_mention("user_123", "python")
        await engine.concept_tracker.track_mention("user_123", "python")

        hints = await engine.generate_hints(
            user_id="user_123", current_context={"message": "python script"}
        )

        # Should generate hint at 2 mentions (custom threshold)
        pref_hints = [h for h in hints if h.type == "preference_reminder"]
        assert len(pref_hints) > 0


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
