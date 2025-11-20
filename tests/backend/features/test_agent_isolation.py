# tests/backend/features/test_agent_isolation.py
# Tests unitaires isolation agent stricte
# Sprint 4 Memory Refactoring
#
# Coverage:
# - Filtrage strict vs permissif
# - Monitoring violations isolation
# - Backfill agent_ids

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from backend.features.chat.memory_ctx import MemoryContextBuilder


class TestAgentIsolationStrict:
    """Tests pour isolation agent stricte (Sprint 4)"""

    def test_result_matches_agent_permissive_with_legacy(self):
        """Test filtrage permissif inclut concepts legacy"""
        result = {
            "text": "Concept Docker",
            "metadata": {
                "user_id": "user_123",
                # Pas d'agent_id → concept legacy
            },
        }

        # Mode permissif (strict_mode=False)
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=False
            )
            is True
        )

    def test_result_matches_agent_strict_excludes_legacy(self):
        """Test filtrage strict exclut concepts legacy"""
        result = {
            "text": "Concept Docker",
            "metadata": {
                "user_id": "user_123",
                # Pas d'agent_id → concept legacy
            },
        }

        # Mode strict (strict_mode=True)
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=True
            )
            is False
        )

    def test_result_matches_agent_strict_matching_agent(self):
        """Test filtrage strict inclut concepts du même agent"""
        result = {
            "text": "Concept Anima",
            "metadata": {"user_id": "user_123", "agent_id": "anima"},
        }

        # Mode strict - même agent
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=True
            )
            is True
        )

    def test_result_matches_agent_strict_different_agent(self):
        """Test filtrage strict exclut concepts d'autres agents"""
        result = {
            "text": "Concept Neo",
            "metadata": {"user_id": "user_123", "agent_id": "neo"},
        }

        # Mode strict - agent différent
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=True
            )
            is False
        )

    def test_result_matches_agent_permissive_different_agent(self):
        """Test filtrage permissif exclut quand même concepts d'autres agents"""
        result = {
            "text": "Concept Neo",
            "metadata": {"user_id": "user_123", "agent_id": "neo"},
        }

        # Mode permissif - agent différent (quand même exclu)
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=False
            )
            is False
        )

    def test_result_matches_agent_auto_mode_from_env_false(self):
        """Test auto-détection mode depuis env (STRICT_AGENT_ISOLATION=false)"""
        result = {"text": "Concept legacy", "metadata": {"user_id": "user_123"}}

        with patch.dict(os.environ, {"STRICT_AGENT_ISOLATION": "false"}):
            # Mode auto → doit lire env et utiliser permissif
            assert (
                MemoryContextBuilder._result_matches_agent(
                    result, "anima", strict_mode=None
                )
                is True
            )

    def test_result_matches_agent_auto_mode_from_env_true(self):
        """Test auto-détection mode depuis env (STRICT_AGENT_ISOLATION=true)"""
        result = {"text": "Concept legacy", "metadata": {"user_id": "user_123"}}

        with patch.dict(os.environ, {"STRICT_AGENT_ISOLATION": "true"}):
            # Mode auto → doit lire env et utiliser strict
            assert (
                MemoryContextBuilder._result_matches_agent(
                    result, "anima", strict_mode=None
                )
                is False
            )

    def test_result_matches_agent_case_insensitive(self):
        """Test filtrage insensible à la casse"""
        result = {
            "text": "Concept Anima",
            "metadata": {
                "user_id": "user_123",
                "agent_id": "ANIMA",  # Uppercase
            },
        }

        # Doit matcher malgré différence casse
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=True
            )
            is True
        )

    def test_result_matches_agent_no_metadata(self):
        """Test filtrage avec résultat sans metadata"""
        result = {"text": "Concept sans metadata"}

        # Mode permissif → inclure
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=False
            )
            is True
        )

        # Mode strict → exclure
        assert (
            MemoryContextBuilder._result_matches_agent(
                result, "anima", strict_mode=True
            )
            is False
        )


class TestAgentIsolationMonitoring:
    """Tests monitoring violations isolation"""

    @patch("backend.features.chat.memory_ctx.PROMETHEUS_AVAILABLE", True)
    @patch("backend.features.chat.memory_ctx.agent_isolation_violations")
    def test_violation_monitored_in_strict_mode(self, mock_counter):
        """Test violation monitorée en mode strict"""
        result = {
            "text": "Concept Neo",
            "metadata": {"user_id": "user_123", "agent_id": "neo"},
        }

        # Mode strict - devrait incrémenter counter
        MemoryContextBuilder._result_matches_agent(result, "anima", strict_mode=True)

        # Vérifier counter incrémenté
        mock_counter.labels.assert_called_once_with(
            agent_requesting="anima", agent_concept="neo"
        )
        mock_counter.labels.return_value.inc.assert_called_once()

    @patch("backend.features.chat.memory_ctx.PROMETHEUS_AVAILABLE", True)
    @patch("backend.features.chat.memory_ctx.agent_isolation_violations")
    def test_no_violation_when_matching(self, mock_counter):
        """Test pas de violation quand agent correspond"""
        result = {
            "text": "Concept Anima",
            "metadata": {"user_id": "user_123", "agent_id": "anima"},
        }

        # Mode strict - même agent, pas de violation
        MemoryContextBuilder._result_matches_agent(result, "anima", strict_mode=True)

        # Counter ne doit pas être appelé
        mock_counter.labels.assert_not_called()

    @patch("backend.features.chat.memory_ctx.PROMETHEUS_AVAILABLE", True)
    @patch("backend.features.chat.memory_ctx.agent_isolation_violations")
    def test_no_violation_in_permissive_mode(self, mock_counter):
        """Test pas de monitoring en mode permissif"""
        result = {
            "text": "Concept Neo",
            "metadata": {"user_id": "user_123", "agent_id": "neo"},
        }

        # Mode permissif - pas de monitoring
        MemoryContextBuilder._result_matches_agent(result, "anima", strict_mode=False)

        # Counter ne doit pas être appelé
        mock_counter.labels.assert_not_called()


class TestBackfillAgentIds:
    """Tests pour backfill_agent_ids.py"""

    @pytest.mark.asyncio
    async def test_infer_agent_from_thread_with_agent_id(self):
        """Test inférence agent_id depuis thread"""
        from backend.cli.backfill_agent_ids import infer_agent_from_thread
        from backend.core.database import queries

        mock_db = AsyncMock()

        with patch.object(
            queries, "get_thread_any", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "id": "thread_123",
                "agent_id": "neo",
                "user_id": "user_123",
            }

            agent_id = await infer_agent_from_thread(mock_db, "thread_123")

            assert agent_id == "neo"

    @pytest.mark.asyncio
    async def test_infer_agent_from_thread_default_anima(self):
        """Test inférence retourne 'anima' par défaut"""
        from backend.cli.backfill_agent_ids import infer_agent_from_thread
        from backend.core.database import queries

        mock_db = AsyncMock()

        with patch.object(
            queries, "get_thread_any", new_callable=AsyncMock
        ) as mock_get:
            # Thread sans agent_id
            mock_get.return_value = {"id": "thread_123", "user_id": "user_123"}

            agent_id = await infer_agent_from_thread(mock_db, "thread_123")

            assert agent_id == "anima"

    @pytest.mark.asyncio
    async def test_infer_agent_from_thread_error_fallback(self):
        """Test inférence retourne 'anima' en cas d'erreur"""
        from backend.cli.backfill_agent_ids import infer_agent_from_thread
        from backend.core.database import queries

        mock_db = AsyncMock()

        with patch.object(
            queries, "get_thread_any", new_callable=AsyncMock
        ) as mock_get:
            # Erreur DB
            mock_get.side_effect = Exception("DB error")

            agent_id = await infer_agent_from_thread(mock_db, "thread_123")

            assert agent_id == "anima"

    @pytest.mark.asyncio
    async def test_backfill_skips_existing_agent_ids(self):
        """Test backfill skip concepts avec agent_id existant"""
        from backend.cli.backfill_agent_ids import backfill_missing_agent_ids

        mock_vector = Mock()
        mock_collection = Mock()
        mock_db = AsyncMock()

        # Mock collection.get() retourne concepts avec agent_id déjà présent
        mock_collection.get.return_value = {
            "ids": ["concept_1", "concept_2"],
            "metadatas": [
                {"user_id": "u1", "agent_id": "anima", "thread_ids": ["t1"]},
                {"user_id": "u1", "agent_id": "neo", "thread_ids": ["t2"]},
            ],
        }

        mock_vector.get_or_create_collection.return_value = mock_collection

        # Exécuter backfill
        result = await backfill_missing_agent_ids(mock_vector, mock_db, dry_run=True)

        # Tous skipped
        assert result["skipped"] == 2
        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_backfill_updates_missing_agent_ids(self):
        """Test backfill met à jour concepts sans agent_id"""
        from backend.cli.backfill_agent_ids import backfill_missing_agent_ids
        from backend.core.database import queries

        mock_vector = Mock()
        mock_collection = Mock()
        mock_db = AsyncMock()

        # Mock collection.get() retourne concept sans agent_id
        mock_collection.get.return_value = {
            "ids": ["concept_1"],
            "metadatas": [
                {"user_id": "u1", "thread_ids": ["thread_123"]}  # Pas d'agent_id
            ],
        }

        mock_vector.get_or_create_collection.return_value = mock_collection

        # Mock infer_agent_from_thread
        with patch.object(
            queries, "get_thread_any", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {"id": "thread_123", "agent_id": "neo"}

            # Exécuter backfill (dry_run pour pas modifier réellement)
            result = await backfill_missing_agent_ids(
                mock_vector, mock_db, dry_run=True
            )

            # 1 updated (dry_run)
            assert result["updated"] == 1
            assert result["skipped"] == 0
