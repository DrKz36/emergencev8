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
        IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données.

        Args:
            period: "7d", "30d", "90d", "1y"
            user_id: Filtrer par utilisateur (OBLIGATOIRE)
            session_id: Filtrer par session (optionnel)

        Returns:
            Liste de {date, message_count, thread_count}
        """
        # user_id est OBLIGATOIRE pour l'isolation des données utilisateur
        if not user_id:
            logger.error("[SECURITY] user_id obligatoire pour get_activity_timeline")
            raise ValueError("user_id est obligatoire pour accéder aux données de timeline")

        days = self._parse_period(period)

        # Construire les conditions de filtrage
        date_field = "created_at"  # champ de référence pour les messages
        message_filters = [f"date(m.{date_field}) = dates.date", "m.user_id = ?"]
        thread_filters = ["date(t.created_at) = dates.date", "t.user_id = ?"]
        params: List[Any] = [user_id, user_id]

        if session_id:
            message_filters.append("m.session_id = ?")
            thread_filters.append("t.session_id = ?")
            params.extend([session_id, session_id])

        message_join = " LEFT JOIN messages m ON " + " AND ".join(message_filters)
        thread_join = " LEFT JOIN threads t ON " + " AND ".join(thread_filters)

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
            {message_join}
            {thread_join}
            GROUP BY dates.date
            ORDER BY dates.date ASC
        """

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
        IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données.

        Returns:
            Liste de {date, total_cost}
        """
        # user_id est OBLIGATOIRE pour l'isolation des données utilisateur
        if not user_id:
            logger.error("[SECURITY] user_id obligatoire pour get_costs_timeline")
            raise ValueError("user_id est obligatoire pour accéder aux données de coûts")

        days = self._parse_period(period)

        cost_filters = ["date(c.timestamp) = dates.date", "c.user_id = ?"]
        params: List[Any] = [user_id]

        if session_id:
            cost_filters.append("c.session_id = ?")
            params.append(session_id)

        cost_join = " LEFT JOIN costs c ON " + " AND ".join(cost_filters)

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
            {cost_join}
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
        IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données.

        Returns:
            Liste de {date, input_tokens, output_tokens, total}
        """
        # user_id est OBLIGATOIRE pour l'isolation des données utilisateur
        if not user_id:
            logger.error("[SECURITY] user_id obligatoire pour get_tokens_timeline")
            raise ValueError("user_id est obligatoire pour accéder aux données de tokens")

        days = self._parse_period(period)

        token_filters = ["date(c.timestamp) = dates.date", "c.user_id = ?"]
        params: List[Any] = [user_id]

        if session_id:
            token_filters.append("c.session_id = ?")
            params.append(session_id)

        token_join = " LEFT JOIN costs c ON " + " AND ".join(token_filters)

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
            {token_join}
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
        IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données.

        Args:
            metric: "messages", "tokens", "costs"
            period: "7d", "30d", "90d", "1y"
            user_id: ID utilisateur (OBLIGATOIRE)
            session_id: ID session (optionnel)

        Returns:
            Dict {agent_name: count}
        """
        # user_id est OBLIGATOIRE pour l'isolation des données utilisateur
        if not user_id:
            logger.error("[SECURITY] user_id obligatoire pour get_distribution_by_agent")
            raise ValueError("user_id est obligatoire pour accéder aux données de distribution")

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
            conditions = [
                f"date(timestamp) >= date('now', '-{days} days')",
                "user_id = ?"
            ]
            params = [user_id]

            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)

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
