# tests/backend/features/test_memory_enhancements.py
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone, timedelta

from backend.features.chat.memory_ctx import MemoryContextBuilder
from backend.features.memory.incremental_consolidation import IncrementalConsolidator
from backend.features.memory.intent_tracker import IntentTracker


class TestMemoryContextEnhancements:
    """Tests pour les améliorations du contexte mémoire."""

    @pytest.fixture
    def mock_vector_service(self):
        service = Mock()
        service.get_or_create_collection = Mock(return_value=Mock())
        service.query = Mock(return_value=[])
        return service

    @pytest.fixture
    def mock_session_manager(self):
        manager = Mock()
        manager.get_session = Mock(
            return_value=Mock(metadata={"summary": "Test summary"})
        )
        return manager

    @pytest.fixture
    def memory_ctx(self, mock_session_manager, mock_vector_service):
        return MemoryContextBuilder(mock_session_manager, mock_vector_service)

    @pytest.mark.asyncio
    async def test_fetch_active_preferences(self, memory_ctx, mock_vector_service):
        """Test que les préférences actives sont récupérées correctement."""
        collection = Mock()
        collection.get = Mock(
            return_value={
                "documents": [
                    "Python: éviter NumPy, privilégier Polars",
                    "Tests: toujours inclure type hints",
                ],
                "metadatas": [
                    {"confidence": 0.8, "type": "preference"},
                    {"confidence": 0.7, "type": "preference"},
                ],
            }
        )

        prefs = memory_ctx._fetch_active_preferences(collection, "test_user")

        assert "Python: éviter NumPy" in prefs
        assert "Tests: toujours inclure type hints" in prefs
        collection.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_temporal_weighting_recent_boost(self, memory_ctx):
        """Test que les items récents reçoivent un boost de score."""
        now = datetime.now(timezone.utc)
        recent_item = {
            "text": "Recent knowledge",
            "score": 1.0,
            "metadata": {
                "created_at": now.isoformat(),
                "usage_count": 2,
            },
        }
        old_item = {
            "text": "Old knowledge",
            "score": 1.0,
            "metadata": {
                "created_at": (now - timedelta(days=60)).isoformat(),
                "usage_count": 0,
            },
        }

        results = [old_item, recent_item]
        weighted = memory_ctx._apply_temporal_weighting(results)

        # Recent item should have higher boosted score
        assert weighted[0]["text"] == "Recent knowledge"
        assert weighted[0]["boosted_score"] > weighted[1]["boosted_score"]

    @pytest.mark.asyncio
    async def test_build_memory_context_with_preferences(
        self, memory_ctx, mock_vector_service
    ):
        """Test que le contexte mémoire inclut les préférences."""
        collection = Mock()
        collection.get = Mock(
            return_value={
                "documents": ["Préférence: utiliser FastAPI"],
                "metadatas": [{"confidence": 0.8}],
            }
        )

        mock_vector_service.get_or_create_collection = Mock(return_value=collection)
        mock_vector_service.query = Mock(
            return_value=[
                {
                    "text": "Connaissance générale Python",
                    "score": 1.0,
                    "metadata": {},
                }
            ]
        )

        memory_ctx.vector_service = mock_vector_service
        memory_ctx.try_get_user_id = Mock(return_value="test_user")

        context = await memory_ctx.build_memory_context(
            "test_session", "question Python", top_k=5
        )

        assert "Préférences actives" in context
        assert "utiliser FastAPI" in context
        assert "Connaissances pertinentes" in context


class TestIncrementalConsolidation:
    """Tests pour la consolidation incrémentale."""

    @pytest.fixture
    def mock_analyzer(self):
        analyzer = Mock()
        analyzer.analyze_history = AsyncMock(
            return_value={
                "summary": "New summary",
                "concepts": ["Python", "FastAPI"],
                "entities": [],
            }
        )
        analyzer.chat_service = Mock()
        return analyzer

    @pytest.fixture
    def consolidator(self, mock_analyzer):
        return IncrementalConsolidator(
            memory_analyzer=mock_analyzer,
            vector_service=Mock(),
            db_manager=Mock(),
            consolidation_threshold=10,
        )

    @pytest.mark.asyncio
    async def test_consolidation_threshold(self, consolidator):
        """Test que la consolidation se déclenche au seuil."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(5)]

        # First 9 messages: no consolidation
        for i in range(9):
            result = await consolidator.check_and_consolidate(
                "session1", "thread1", messages
            )
            assert result is None

        # 10th message: consolidation triggered
        result = await consolidator.check_and_consolidate(
            "session1", "thread1", messages
        )
        assert result is not None
        assert result["status"] in ["success", "partial", "skipped"]

    @pytest.mark.asyncio
    async def test_micro_consolidate_merges_concepts(
        self, consolidator, mock_analyzer
    ):
        """Test que les concepts sont fusionnés avec STM existante."""
        session_manager = Mock()
        session_manager.get_session = Mock(
            return_value=Mock(
                metadata={
                    "summary": "Old summary",
                    "concepts": ["Django", "PostgreSQL"],
                    "entities": [],
                }
            )
        )
        session_manager.update_session_metadata = Mock()

        mock_analyzer.chat_service.session_manager = session_manager

        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

        result = await consolidator._micro_consolidate(
            "session1", "thread1", messages
        )

        assert result["status"] == "success"
        # Should have called update with merged concepts
        session_manager.update_session_metadata.assert_called_once()
        call_args = session_manager.update_session_metadata.call_args
        merged_concepts = call_args[1]["concepts"]
        assert "Python" in merged_concepts or "FastAPI" in merged_concepts
        assert "Django" in merged_concepts or "PostgreSQL" in merged_concepts


class TestIntentTracker:
    """Tests pour le suivi des intentions."""

    @pytest.fixture
    def intent_tracker(self):
        return IntentTracker(vector_service=Mock(), connection_manager=Mock())

    def test_parse_timeframe_demain(self, intent_tracker):
        """Test parsing 'demain'."""
        result = intent_tracker.parse_timeframe("demain")
        assert result is not None
        expected = datetime.now(timezone.utc) + timedelta(days=1)
        assert result.date() == expected.date()

    def test_parse_timeframe_dans_3_jours(self, intent_tracker):
        """Test parsing 'dans 3 jours'."""
        result = intent_tracker.parse_timeframe("dans 3 jours")
        assert result is not None
        expected = datetime.now(timezone.utc) + timedelta(days=3)
        assert result.date() == expected.date()

    def test_parse_timeframe_cette_semaine(self, intent_tracker):
        """Test parsing 'cette semaine'."""
        result = intent_tracker.parse_timeframe("cette semaine")
        assert result is not None
        expected = datetime.now(timezone.utc) + timedelta(days=7)
        assert result.date() == expected.date()

    @pytest.mark.asyncio
    async def test_check_expiring_intents(self, intent_tracker):
        """Test détection des intentions expirantes."""
        now = datetime.now(timezone.utc)
        upcoming = now + timedelta(days=3)

        collection = Mock()
        collection.get = Mock(
            return_value={
                "ids": ["intent1"],
                "documents": ["Faire migration DB"],
                "metadatas": [
                    {
                        "type": "intent",
                        "timeframe": "dans 3 jours",
                        "confidence": 0.7,
                    }
                ],
            }
        )

        intent_tracker.vector_service.get_or_create_collection = Mock(
            return_value=collection
        )

        expiring = await intent_tracker.check_expiring_intents("user1", lookahead_days=7)

        assert len(expiring) == 1
        assert expiring[0]["id"] == "intent1"
        assert expiring[0]["days_remaining"] >= 2
        assert expiring[0]["days_remaining"] <= 4

    @pytest.mark.asyncio
    async def test_purge_ignored_intents(self, intent_tracker):
        """Test purge des intentions ignorées."""
        intent_tracker.reminder_counts = {
            "intent1": 3,
            "intent2": 2,
            "intent3": 4,
        }

        collection = Mock()
        collection.delete = Mock()

        intent_tracker.vector_service.get_or_create_collection = Mock(
            return_value=collection
        )

        purged = await intent_tracker.purge_ignored_intents("user1")

        assert purged == 2  # intent1 and intent3
        assert "intent1" not in intent_tracker.reminder_counts
        assert "intent2" in intent_tracker.reminder_counts  # Still there
        assert "intent3" not in intent_tracker.reminder_counts
