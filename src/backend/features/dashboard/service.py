# src/backend/features/dashboard/service.py
# V11.1 — DTO cockpit (robuste) : tolérance aux champs manquants & seuils fallback
from __future__ import annotations

import logging
import os
from typing import Dict, Any, List

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries
from backend.core.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Fournit les données agrégées pour le cockpit de pilotage.
    Cette version agit comme un adaptateur (DTO pattern), formatant les données
    exactement comme le frontend en a besoin.
    """

    def __init__(self, db_manager: DatabaseManager, cost_tracker: CostTracker):
        """
        Initialise le service avec le gestionnaire de BDD et le CostTracker.
        Le CostTracker est nécessaire pour récupérer les seuils d'alerte.
        """
        self.db = db_manager
        self.cost_tracker = cost_tracker
        logger.info("DashboardService V11.1 (DTO robuste) initialisé.")

    # -------------------------
    # Helpers internes
    # -------------------------
    @staticmethod
    def _coerce_list(maybe_list) -> List[Any]:
        if isinstance(maybe_list, list):
            return maybe_list
        return [] if maybe_list is None else list(maybe_list)

    def _get_threshold(self, *names: str, env: str, default: float) -> float:
        """
        Récupère un seuil sur CostTracker (attributs possibles en cascade),
        sinon via variable d'environnement, sinon 'default'.
        """
        for name in names:
            try:
                val = getattr(self.cost_tracker, name)
                if isinstance(val, (int, float)):
                    return float(val)
            except Exception:
                pass
        try:
            env_val = os.getenv(env)
            if env_val is not None:
                return float(env_val)
        except Exception:
            pass
        return float(default)

    def _get_thresholds_payload(self) -> Dict[str, float]:
        # accepte DAILY_LIMIT / daily_limit, etc. + ENV fallback
        daily = self._get_threshold(
            "DAILY_LIMIT", "daily_limit",
            env="COST_DAILY_LIMIT",
            default=1.0,
        )
        weekly = self._get_threshold(
            "WEEKLY_LIMIT", "weekly_limit",
            env="COST_WEEKLY_LIMIT",
            default=1.0,
        )
        monthly = self._get_threshold(
            "MONTHLY_LIMIT", "monthly_limit",
            env="COST_MONTHLY_LIMIT",
            default=1.0,
        )
        return {
            "daily_threshold": daily,
            "weekly_threshold": weekly,
            "monthly_threshold": monthly,
        }

    # -------------------------
    # API principale
    # -------------------------
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Récupère, agrège et formate toutes les données pour le cockpit.
        La structure de l'objet retourné correspond exactement à ce que
        le composant dashboard-ui attend.
        """
        try:
            # 1) Récupération des données brutes (tolérance None)
            try:
                costs_raw = await db_queries.get_costs_summary(self.db)
            except Exception as e:
                logger.warning(f"[dashboard] get_costs_summary KO: {e}")
                costs_raw = {}

            try:
                documents_raw = await db_queries.get_all_documents(self.db)
            except Exception as e:
                logger.warning(f"[dashboard] get_all_documents KO: {e}")
                documents_raw = []

            try:
                sessions_raw = await db_queries.get_all_sessions_overview(self.db)
            except Exception as e:
                logger.warning(f"[dashboard] get_all_sessions_overview KO: {e}")
                sessions_raw = []

            documents_raw = self._coerce_list(documents_raw)
            sessions_raw = self._coerce_list(sessions_raw)

            # 2) Transformation / formatage UI
            costs_formatted = {
                "total_cost": float(costs_raw.get("total", 0.0) or 0.0),
                "today_cost": float(costs_raw.get("today", 0.0) or 0.0),
                "current_week_cost": float(costs_raw.get("this_week", 0.0) or 0.0),
                "current_month_cost": float(costs_raw.get("this_month", 0.0) or 0.0),
            }

            monitoring_formatted = {
                "total_documents": int(len(documents_raw)),
                "total_sessions": int(len(sessions_raw)),
            }

            thresholds_formatted = self._get_thresholds_payload()

            # 3) Assemblage du payload final (inclut un raw minimal pour futures vues)
            return {
                "costs": costs_formatted,
                "monitoring": monitoring_formatted,
                "thresholds": thresholds_formatted,
                "raw_data": {
                    "documents": documents_raw,
                    "sessions": sessions_raw,
                },
            }

        except Exception as e:
            logger.error(
                f"[dashboard] Erreur critique lors du formatage cockpit: {e}",
                exc_info=True,
            )
            # Structure valide pour éviter tout crash UI
            return {
                "costs": {
                    "total_cost": 0.0,
                    "today_cost": 0.0,
                    "current_week_cost": 0.0,
                    "current_month_cost": 0.0,
                },
                "monitoring": {"total_documents": 0, "total_sessions": 0},
                "thresholds": {"daily_threshold": 1.0, "weekly_threshold": 1.0, "monthly_threshold": 1.0},
                "raw_data": {"documents": [], "sessions": []},
            }
