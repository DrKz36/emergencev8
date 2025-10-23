"""
Tests pour LLM Cost Telemetry V13.2
- Métriques Prometheus (requests, tokens, cost par agent/model)
- Incrémentation correcte des counters/histograms
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from backend.core.cost_tracker import (
    CostTracker,
    METRICS_ENABLED,
    llm_requests_total,
    llm_tokens_prompt_total,
    llm_tokens_completion_total,
    llm_cost_usd_total,
    llm_latency_seconds,
)


@pytest.fixture
def db_manager_mock():
    """Mock DatabaseManager"""
    mock = MagicMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
async def cost_tracker(db_manager_mock):
    """Fixture CostTracker avec DB mockée"""
    # Reset singleton
    CostTracker._instance = None
    tracker = CostTracker(db_manager=db_manager_mock)
    return tracker


class TestCostTelemetryPrometheus:
    """Tests pour métriques Prometheus V13.2"""

    @pytest.mark.asyncio
    async def test_record_cost_increments_metrics(self, cost_tracker, db_manager_mock):
        """Test que record_cost incrémente les métriques Prometheus"""
        if not METRICS_ENABLED:
            pytest.skip("Métriques Prometheus désactivées (CONCEPT_RECALL_METRICS_ENABLED=false)")

        # Mock db_queries.add_cost_log
        with patch("backend.core.database.queries.add_cost_log", new_callable=AsyncMock):
            # Mock les métriques Prometheus pour capturer les appels
            mock_requests = MagicMock()
            mock_tokens_prompt = MagicMock()
            mock_tokens_completion = MagicMock()
            mock_cost = MagicMock()

            with patch.multiple(
                "backend.core.cost_tracker",
                llm_requests_total=mock_requests,
                llm_tokens_prompt_total=mock_tokens_prompt,
                llm_tokens_completion_total=mock_tokens_completion,
                llm_cost_usd_total=mock_cost,
            ):
                # Enregistrer un coût
                await cost_tracker.record_cost(
                    agent="anima",
                    model="gpt-4",
                    input_tokens=100,
                    output_tokens=50,
                    total_cost=0.05,
                    feature="chat",
                )

                # Vérifier incrémentations
                mock_requests.labels.assert_called_once_with(agent="anima", model="gpt-4")
                mock_requests.labels().inc.assert_called_once()

                mock_tokens_prompt.labels.assert_called_once_with(agent="anima", model="gpt-4")
                mock_tokens_prompt.labels().inc.assert_called_once_with(100)

                mock_tokens_completion.labels.assert_called_once_with(agent="anima", model="gpt-4")
                mock_tokens_completion.labels().inc.assert_called_once_with(50)

                mock_cost.labels.assert_called_once_with(agent="anima", model="gpt-4")
                mock_cost.labels().inc.assert_called_once_with(0.05)

    @pytest.mark.asyncio
    async def test_record_cost_with_latency(self, cost_tracker, db_manager_mock):
        """Test enregistrement coût avec latence (histogram)"""
        if not METRICS_ENABLED:
            pytest.skip("Métriques Prometheus désactivées")

        with patch("backend.core.database.queries.add_cost_log", new_callable=AsyncMock):
            mock_latency = MagicMock()

            with patch("backend.core.cost_tracker.llm_latency_seconds", mock_latency):
                # Enregistrer avec latency
                await cost_tracker.record_cost(
                    agent="neo",
                    model="claude-3-opus",
                    input_tokens=200,
                    output_tokens=100,
                    total_cost=0.10,
                    feature="debug",
                    latency_seconds=2.5,
                )

                # Vérifier observe() appelé
                mock_latency.labels.assert_called_once_with(agent="neo", model="claude-3-opus")
                mock_latency.labels().observe.assert_called_once_with(2.5)

    @pytest.mark.asyncio
    async def test_record_cost_multiple_agents(self, cost_tracker, db_manager_mock):
        """Test métriques correctes pour plusieurs agents"""
        if not METRICS_ENABLED:
            pytest.skip("Métriques Prometheus désactivées")

        with patch("backend.core.database.queries.add_cost_log", new_callable=AsyncMock):
            mock_requests = MagicMock()

            with patch("backend.core.cost_tracker.llm_requests_total", mock_requests):
                # Enregistrer plusieurs agents
                await cost_tracker.record_cost(
                    agent="anima",
                    model="gpt-4",
                    input_tokens=100,
                    output_tokens=50,
                    total_cost=0.05,
                    feature="chat",
                )

                await cost_tracker.record_cost(
                    agent="neo",
                    model="claude-3-opus",
                    input_tokens=200,
                    output_tokens=100,
                    total_cost=0.10,
                    feature="debug",
                )

                await cost_tracker.record_cost(
                    agent="nexus",
                    model="gemini-pro",
                    input_tokens=150,
                    output_tokens=75,
                    total_cost=0.03,
                    feature="coordination",
                )

                # Vérifier 3 appels avec labels différents
                assert mock_requests.labels.call_count == 3
                mock_requests.labels.assert_any_call(agent="anima", model="gpt-4")
                mock_requests.labels.assert_any_call(agent="neo", model="claude-3-opus")
                mock_requests.labels.assert_any_call(agent="nexus", model="gemini-pro")

    @pytest.mark.asyncio
    async def test_metrics_disabled_no_error(self, db_manager_mock):
        """Test que l'enregistrement fonctionne même si métriques désactivées"""
        # Mock METRICS_ENABLED = False
        with patch("backend.core.cost_tracker.METRICS_ENABLED", False):
            with patch("backend.core.database.queries.add_cost_log", new_callable=AsyncMock):
                # Reset singleton
                CostTracker._instance = None
                tracker = CostTracker(db_manager=db_manager_mock)

                # Ne doit pas raise
                await tracker.record_cost(
                    agent="anima",
                    model="gpt-4",
                    input_tokens=100,
                    output_tokens=50,
                    total_cost=0.05,
                    feature="chat",
                )

    @pytest.mark.asyncio
    async def test_initialization_logs_metrics_status(self, db_manager_mock):
        """Test que le log d'init mentionne le status des métriques"""
        with patch("backend.core.cost_tracker.logger") as mock_logger:
            # Reset singleton
            CostTracker._instance = None
            tracker = CostTracker(db_manager=db_manager_mock)

            # Vérifier log init
            mock_logger.info.assert_called_once()
            log_msg = mock_logger.info.call_args[0][0]
            assert "CostTracker V13.2" in log_msg
            assert "Prometheus metrics:" in log_msg


class TestCostTrackerBackwardCompat:
    """Tests de rétrocompatibilité V13.2"""

    @pytest.mark.asyncio
    async def test_record_cost_without_latency_param(self, cost_tracker, db_manager_mock):
        """Test que latency_seconds est optionnel (rétrocompat)"""
        with patch("backend.core.database.queries.add_cost_log", new_callable=AsyncMock):
            # Appel sans latency_seconds (comme V13.1)
            await cost_tracker.record_cost(
                agent="anima",
                model="gpt-4",
                input_tokens=100,
                output_tokens=50,
                total_cost=0.05,
                feature="chat",
            )
            # Ne doit pas raise

    @pytest.mark.asyncio
    async def test_get_spending_summary_still_works(self, cost_tracker, db_manager_mock):
        """Test que get_spending_summary fonctionne toujours (API stable)"""
        with patch("backend.core.database.queries.get_costs_summary", new_callable=AsyncMock) as mock_summary:
            mock_summary.return_value = {
                "total": 10.0,
                "today": 2.0,
                "this_week": 5.0,
                "this_month": 8.0,
            }

            summary = await cost_tracker.get_spending_summary()
            assert summary["total"] == 10.0
            assert summary["today"] == 2.0

    @pytest.mark.asyncio
    async def test_check_alerts_still_works(self, cost_tracker, db_manager_mock):
        """Test que check_alerts fonctionne toujours (API stable)"""
        with patch("backend.core.database.queries.get_costs_summary", new_callable=AsyncMock) as mock_summary:
            # Mock dépasser le seuil daily
            mock_summary.return_value = {
                "today": 5.0,  # > DAILY_LIMIT (3.0)
                "this_week": 2.0,
                "this_month": 2.0,
            }

            alerts = await cost_tracker.check_alerts()
            assert len(alerts) == 1
            assert alerts[0][0] == "jour"
            assert alerts[0][1] == 5.0
            assert alerts[0][2] == 3.0
