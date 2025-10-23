# src/backend/core/cost_tracker.py
# V13.2 - Télémétrie Prometheus pour coûts LLM (requests, tokens, cost par agent/model)
import logging
import asyncio
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries

# V13.2 - Prometheus metrics pour LLM cost tracking
try:
    from prometheus_client import Counter, Histogram, REGISTRY
    METRICS_ENABLED = os.getenv("CONCEPT_RECALL_METRICS_ENABLED", "true").lower() == "true"
except ImportError:
    METRICS_ENABLED = False

logger = logging.getLogger(__name__)


# V13.2 - Métriques Prometheus LLM Cost
if METRICS_ENABLED:
    llm_requests_total = Counter(
        "llm_requests_total",
        "Total LLM API requests",
        ["agent", "model"],
        registry=REGISTRY,
    )
    llm_tokens_prompt_total = Counter(
        "llm_tokens_prompt_total",
        "Total prompt/input tokens consumed",
        ["agent", "model"],
        registry=REGISTRY,
    )
    llm_tokens_completion_total = Counter(
        "llm_tokens_completion_total",
        "Total completion/output tokens consumed",
        ["agent", "model"],
        registry=REGISTRY,
    )
    llm_cost_usd_total = Counter(
        "llm_cost_usd_total",
        "Total LLM cost in USD",
        ["agent", "model"],
        registry=REGISTRY,
    )
    llm_latency_seconds = Histogram(
        "llm_latency_seconds",
        "LLM API call latency in seconds",
        ["agent", "model"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        registry=REGISTRY,
    )
else:
    # Stubs si métriques désactivées
    llm_requests_total = None
    llm_tokens_prompt_total = None
    llm_tokens_completion_total = None
    llm_cost_usd_total = None
    llm_latency_seconds = None


class CostTracker:
    """
    COST TRACKER V13.2
    - Enregistre les coûts (async, aiosqlite).
    - Fournit un résumé & des alertes avec mapping tolérant des clés.
    - 🆕 V13.2: Télémétrie Prometheus (llm_requests_total, llm_tokens_*, llm_cost_usd_total, llm_latency_seconds).
      Métriques exposées sur /metrics par agent et modèle.
    """

    DAILY_LIMIT = 3.0
    WEEKLY_LIMIT = 12.0
    MONTHLY_LIMIT = 20.0

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CostTracker, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_manager: Optional[DatabaseManager] = None) -> None:
        if not hasattr(self, "initialized"):
            if db_manager is None:
                raise ValueError(
                    "DatabaseManager est requis pour l'initialisation de CostTracker."
                )
            self.db_manager = db_manager
            self.initialized = True
            metrics_status = "enabled" if METRICS_ENABLED else "disabled"
            logger.info(f"CostTracker V13.2 initialisé (Prometheus metrics: {metrics_status}).")

    async def record_cost(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_cost: float,
        feature: str,
        *,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        latency_seconds: Optional[float] = None,
    ):
        """
        Enregistre le coût d'une opération via le module requêtes.
        V13.2: Incrémente aussi les métriques Prometheus (requests, tokens, cost).
        """
        async with self._lock:
            try:
                await db_queries.add_cost_log(
                    db=self.db_manager,
                    timestamp=datetime.now(timezone.utc),
                    agent=agent,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_cost=total_cost,
                    feature=feature,
                    session_id=session_id,
                    user_id=user_id,
                )

                # V13.2 - Prometheus metrics
                if METRICS_ENABLED and llm_requests_total:
                    llm_requests_total.labels(agent=agent, model=model).inc()
                    llm_tokens_prompt_total.labels(agent=agent, model=model).inc(input_tokens)
                    llm_tokens_completion_total.labels(agent=agent, model=model).inc(output_tokens)
                    llm_cost_usd_total.labels(agent=agent, model=model).inc(total_cost)
                    if latency_seconds is not None and llm_latency_seconds:
                        llm_latency_seconds.labels(agent=agent, model=model).observe(latency_seconds)

                logger.info(
                    f"Coût de {total_cost:.6f} pour '{agent}' ('{model}') enregistré."
                )
            except Exception as e:
                logger.error(
                    f"Erreur lors de l'enregistrement du coût pour {model}: {e}",
                    exc_info=True,
                )

    async def get_spending_summary(self, *, user_id: Optional[str] = None,
                                   session_id: Optional[str] = None) -> Dict[str, float]:
        """Résumé brut depuis la BDD (clés: total/today/this_week/this_month)."""
        return await db_queries.get_costs_summary(
            db=self.db_manager,
            user_id=user_id,
            session_id=session_id,
        )

    async def check_alerts(self) -> List[Tuple[str, float, float]]:
        """
        Vérifie les seuils journaliers/hebdo/mensuels.
        Tolère les deux schémas de clés:
        - brut BDD: today / this_week / this_month
        - format UI: today_cost / current_week_cost / current_month_cost
        """
        summary = await self.get_spending_summary()

        # Mapping tolérant (fallback sur 0.0)
        today_val = summary.get("today", summary.get("today_cost", 0.0))
        week_val = summary.get("this_week", summary.get("current_week_cost", 0.0))
        month_val = summary.get("this_month", summary.get("current_month_cost", 0.0))

        alerts: List[Tuple[str, float, float]] = []
        if today_val > self.DAILY_LIMIT:
            alerts.append(("jour", today_val, self.DAILY_LIMIT))
        if week_val > self.WEEKLY_LIMIT:
            alerts.append(("semaine", week_val, self.WEEKLY_LIMIT))
        if month_val > self.MONTHLY_LIMIT:
            alerts.append(("mois", month_val, self.MONTHLY_LIMIT))
        return alerts
