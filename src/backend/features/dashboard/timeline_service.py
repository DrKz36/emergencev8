# src/backend/features/dashboard/timeline_service.py
"""
Service pour fournir les données temporelles pour les graphiques du cockpit.
Gère les timelines de messages, threads, tokens et coûts.
"""
import logging
from typing import Dict, Any, List, Optional

from backend.core.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class TimelineService:
    """Fournit les données temporelles agrégées pour les graphiques."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        logger.info("TimelineService initialisé")

    async def get_activity_timeline(
        self,
        period: str = "30d",
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne la timeline d'activité (messages + threads par jour).

        Args:
            period: "7d", "30d", "90d", "1y"
            user_id: Filtrer par utilisateur
            session_id: Filtrer par session

        Returns:
            Liste de {date, messages, threads}
        """
        days = self._parse_period(period)

        # Construire les conditions de filtrage
        conditions = []
        params = []

        if session_id:
            conditions.append("m.session_id = ?")
            params.append(session_id)
        elif user_id:
            conditions.append("m.user_id = ?")
            params.append(user_id)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        # Détecter le champ de date (created_at ou timestamp)
        date_field = "created_at"  # Par défaut V6

        query = f"""
            WITH RECURSIVE dates(date) AS (
                SELECT date('now', '-{days} days')
                UNION ALL
                SELECT date(date, '+1 day')
                FROM dates
                WHERE date < date('now')
            )
            SELECT
                dates.date as date,
                COALESCE(COUNT(DISTINCT m.id), 0) as messages,
                COALESCE(COUNT(DISTINCT t.id), 0) as threads
            FROM dates
            LEFT JOIN messages m ON date(m.{date_field}) = dates.date {where_clause}
            LEFT JOIN threads t ON date(t.created_at) = dates.date
                {"AND t.user_id = ?" if user_id and not session_id else ""}
                {"AND t.session_id = ?" if session_id else ""}
            GROUP BY dates.date
            ORDER BY dates.date ASC
        """

        # Ajouter params supplémentaires pour threads si nécessaire
        if user_id and not session_id:
            params.append(user_id)
        if session_id:
            params.append(session_id)

        try:
            rows = await self.db.fetch_all(query, tuple(params) if params else ())
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Erreur get_activity_timeline: {e}", exc_info=True)
            return []

    async def get_costs_timeline(
        self,
        period: str = "30d",
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne la timeline des coûts par jour.

        Returns:
            Liste de {date, cost}
        """
        days = self._parse_period(period)

        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        elif user_id:
            conditions.append("user_id = ?")
            params.append(user_id)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            WITH RECURSIVE dates(date) AS (
                SELECT date('now', '-{days} days')
                UNION ALL
                SELECT date(date, '+1 day')
                FROM dates
                WHERE date < date('now')
            )
            SELECT
                dates.date as date,
                COALESCE(SUM(c.total_cost), 0) as cost
            FROM dates
            LEFT JOIN costs c ON date(c.timestamp) = dates.date{where_clause}
            GROUP BY dates.date
            ORDER BY dates.date ASC
        """

        try:
            rows = await self.db.fetch_all(query, tuple(params) if params else ())
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Erreur get_costs_timeline: {e}", exc_info=True)
            return []

    async def get_tokens_timeline(
        self,
        period: str = "30d",
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retourne la timeline des tokens par jour.

        Returns:
            Liste de {date, input, output, total}
        """
        days = self._parse_period(period)

        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        elif user_id:
            conditions.append("user_id = ?")
            params.append(user_id)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            WITH RECURSIVE dates(date) AS (
                SELECT date('now', '-{days} days')
                UNION ALL
                SELECT date(date, '+1 day')
                FROM dates
                WHERE date < date('now')
            )
            SELECT
                dates.date as date,
                COALESCE(SUM(c.input_tokens), 0) as input,
                COALESCE(SUM(c.output_tokens), 0) as output,
                COALESCE(SUM(c.input_tokens + c.output_tokens), 0) as total
            FROM dates
            LEFT JOIN costs c ON date(c.timestamp) = dates.date{where_clause}
            GROUP BY dates.date
            ORDER BY dates.date ASC
        """

        try:
            rows = await self.db.fetch_all(query, tuple(params) if params else ())
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Erreur get_tokens_timeline: {e}", exc_info=True)
            return []

    async def get_distribution_by_agent(
        self,
        metric: str = "messages",
        period: str = "30d",
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Retourne la distribution par agent pour une métrique donnée.

        Args:
            metric: "messages", "tokens", "costs"
            period: "7d", "30d", "90d", "1y"

        Returns:
            Dict {agent_name: count}
        """
        days = self._parse_period(period)

        if metric == "messages":
            # Messages n'ont pas de champ agent direct, simuler avec des données
            # Pour l'instant, retourner une distribution basique
            return {
                "Assistant": 50,
                "Orchestrator": 30,
                "Researcher": 20
            }

        elif metric in ["tokens", "costs"]:
            conditions = [f"date(timestamp) >= date('now', '-{days} days')"]
            params = []

            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            elif user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            where_clause = " WHERE " + " AND ".join(conditions)

            field = "total_cost" if metric == "costs" else "input_tokens + output_tokens"

            query = f"""
                SELECT agent, SUM({field}) as total
                FROM costs{where_clause}
                GROUP BY agent
                ORDER BY total DESC
            """

            try:
                rows = await self.db.fetch_all(query, tuple(params) if params else ())
                return {row["agent"]: int(row["total"]) for row in rows}
            except Exception as e:
                logger.error(f"Erreur get_distribution_by_agent: {e}", exc_info=True)
                return {}

        return {}

    def _parse_period(self, period: str) -> int:
        """Convertit une période (7d, 30d, etc.) en nombre de jours."""
        if period.endswith("d"):
            return int(period[:-1])
        elif period.endswith("y"):
            return int(period[:-1]) * 365
        return 30  # Default
