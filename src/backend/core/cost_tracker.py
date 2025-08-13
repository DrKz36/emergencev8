# src/backend/core/cost_tracker.py
# V13.1 - Mapping tolérant des clés de coûts pour les alertes (compat v5.x)
import logging
import asyncio
from typing import Dict, List, Tuple
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries
from backend.core import config  # conservé si utilisé ailleurs

logger = logging.getLogger(__name__)

class CostTracker:
    """
    COST TRACKER V13.1
    - Enregistre les coûts (async, aiosqlite).
    - Fournit un résumé & des alertes avec mapping tolérant des clés.
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

    def __init__(self, db_manager: DatabaseManager = None):
        if not hasattr(self, 'initialized'):
            if db_manager is None:
                raise ValueError("DatabaseManager est requis pour l'initialisation de CostTracker.")
            self.db_manager = db_manager
            self.initialized = True
            logger.info("CostTracker V13.1 initialisé.")

    async def record_cost(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_cost: float,
        feature: str
    ):
        """Enregistre le coût d'une opération via le module requêtes."""
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
                    feature=feature
                )
                logger.info(f"Coût de {total_cost:.6f} pour '{agent}' ('{model}') enregistré.")
            except Exception as e:
                logger.error(f"Erreur lors de l'enregistrement du coût pour {model}: {e}", exc_info=True)

    async def get_spending_summary(self) -> Dict[str, float]:
        """Résumé brut depuis la BDD (clés: total/today/this_week/this_month)."""
        return await db_queries.get_costs_summary(db=self.db_manager)

    async def check_alerts(self) -> List[Tuple[str, float, float]]:
        """
        Vérifie les seuils journaliers/hebdo/mensuels.
        Tolère les deux schémas de clés:
        - brut BDD: today / this_week / this_month
        - format UI: today_cost / current_week_cost / current_month_cost
        """
        summary = await self.get_spending_summary()

        # Mapping tolérant (fallback sur 0.0)
        today_val  = summary.get('today', summary.get('today_cost', 0.0))
        week_val   = summary.get('this_week', summary.get('current_week_cost', 0.0))
        month_val  = summary.get('this_month', summary.get('current_month_cost', 0.0))

        alerts: List[Tuple[str, float, float]] = []
        if today_val > self.DAILY_LIMIT:
            alerts.append(("jour", today_val, self.DAILY_LIMIT))
        if week_val > self.WEEKLY_LIMIT:
            alerts.append(("semaine", week_val, self.WEEKLY_LIMIT))
        if month_val > self.MONTHLY_LIMIT:
            alerts.append(("mois", month_val, self.MONTHLY_LIMIT))
        return alerts
