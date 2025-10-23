# src/backend/features/dashboard/service.py
# V11.1 — DTO cockpit (robuste) : tolérance aux champs manquants & seuils fallback
from __future__ import annotations

import logging
import os
from typing import Dict, Any, List, Optional

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
    def _coerce_list(maybe_list: Any) -> List[Any]:
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
    # Coûts par agent
    # -------------------------
    async def get_costs_by_agent(self, *, user_id: Optional[str] = None,
                                 session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les coûts agrégés par agent avec le modèle utilisé.

        Returns:
            Liste de {agent, model, total_cost, input_tokens, output_tokens, request_count}
        """
        try:
            # IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données utilisateur
            if not user_id:
                raise ValueError("user_id est obligatoire pour accéder aux coûts")

            # Construction de la clause WHERE
            conditions = ["user_id = ?"]
            params = [user_id]

            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)

            where_clause = " WHERE " + " AND ".join(conditions)

            # Mapping des noms d'agents techniques vers les noms d'affichage
            agent_display_names = {
                "anima": "Anima",
                "neo": "Neo",
                "nexus": "Nexus",
                "user": "User",
                "system": "System"
            }

            query = f"""
                SELECT
                    agent,
                    model,
                    SUM(total_cost) as total_cost,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    COUNT(*) as request_count
                FROM costs{where_clause}
                GROUP BY agent, model
                ORDER BY total_cost DESC
            """

            rows = await self.db.fetch_all(query, tuple(params) if params else ())

            result = []
            for row in rows:
                # Convert sqlite3.Row to dict for .get() method access
                row_dict = dict(row)
                agent_name = row_dict.get("agent", "unknown")
                display_name = agent_display_names.get(agent_name.lower(), agent_name.capitalize())

                result.append({
                    "agent": display_name,
                    "model": row_dict.get("model", "unknown"),
                    "total_cost": float(row_dict.get("total_cost", 0) or 0),
                    "input_tokens": int(row_dict.get("input_tokens", 0) or 0),
                    "output_tokens": int(row_dict.get("output_tokens", 0) or 0),
                    "request_count": int(row_dict.get("request_count", 0) or 0)
                })

            return result

        except Exception as e:
            logger.error(f"[dashboard] Erreur get_costs_by_agent: {e}", exc_info=True)
            return []

    # -------------------------
    # API principale
    # -------------------------
    async def get_dashboard_data(self, *, user_id: Optional[str] = None,
                                session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère, agrège et formate toutes les données pour le cockpit.
        La structure de l'objet retourné correspond exactement à ce que
        le composant dashboard-ui attend.
        """
        try:
            # 1) Récupération des données brutes (tolérance None)
            try:
                costs_raw = await db_queries.get_costs_summary(
                    self.db,
                    user_id=user_id,
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning(f"[dashboard] get_costs_summary KO: {e}")
                costs_raw = {}

            try:
                documents_raw = await db_queries.get_all_documents(
                    self.db, session_id=session_id, user_id=user_id
                )
            except Exception as e:
                logger.warning(f"[dashboard] get_all_documents KO: {e}")
                documents_raw = []

            try:
                sessions_raw = await db_queries.get_all_sessions_overview(
                    self.db, user_id=user_id, session_id=session_id
                )
            except Exception as e:
                logger.warning(f"[dashboard] get_all_sessions_overview KO: {e}")
                sessions_raw = []

            # Récupération des messages et tokens par période
            try:
                messages_by_period = await db_queries.get_messages_by_period(
                    self.db, user_id=user_id, session_id=session_id
                )
            except Exception as e:
                logger.warning(f"[dashboard] get_messages_by_period KO: {e}")
                messages_by_period = {"total": 0, "today": 0, "week": 0, "month": 0}

            try:
                tokens_summary = await db_queries.get_tokens_summary(
                    self.db, user_id=user_id, session_id=session_id
                )
            except Exception as e:
                logger.warning(f"[dashboard] get_tokens_summary KO: {e}")
                tokens_summary = {"total": 0, "input": 0, "output": 0, "avgPerMessage": 0}

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
                "messages": messages_by_period,
                "tokens": tokens_summary,
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
                "messages": {"total": 0, "today": 0, "week": 0, "month": 0},
                "tokens": {"total": 0, "input": 0, "output": 0, "avgPerMessage": 0},
                "raw_data": {"documents": [], "sessions": []},
            }
