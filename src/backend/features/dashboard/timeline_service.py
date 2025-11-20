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
        En mode dev, si user_id est None, agrège toutes les données.

        Args:
            period: "7d", "30d", "90d", "1y"
            user_id: Filtrer par utilisateur (OBLIGATOIRE en prod, optionnel en dev)
            session_id: Filtrer par session (optionnel)

        Returns:
            Liste de {date, message_count, thread_count}
        """
        days = self._parse_period(period)

        # Construire les conditions de filtrage
        # Fix: NE PAS utiliser COALESCE avec 'now' - ça groupe tous les NULL sur aujourd'hui !
        # On filtre juste les NULL avec m.created_at IS NOT NULL
        message_filters = [
            "m.created_at IS NOT NULL",
            "date(m.created_at) = dates.date",
        ]
        thread_filters = [
            "(t.created_at IS NOT NULL OR t.updated_at IS NOT NULL)",
            "date(COALESCE(t.created_at, t.updated_at)) = dates.date",
        ]
        params: List[Any] = []

        # Si user_id est fourni, filtrer par user_id (mode prod)
        if user_id:
            message_filters.append("m.user_id = ?")
            thread_filters.append("t.user_id = ?")
            params.extend([user_id, user_id])
        # Sinon, en mode dev, on agrège toutes les données (pas de filtre user_id)

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
            logger.info(
                f"[Timeline] Activity timeline returned {len(rows)} days for user_id={user_id}"
            )
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
        En mode dev, si user_id est None, agrège toutes les données.

        Returns:
            Liste de {date, total_cost}
        """
        days = self._parse_period(period)

        # Fix: NE PAS utiliser COALESCE avec 'now' - filtre NULL au lieu de les grouper sur aujourd'hui
        cost_filters = ["c.timestamp IS NOT NULL", "date(c.timestamp) = dates.date"]
        params: List[Any] = []

        # Si user_id est fourni, filtrer par user_id
        if user_id:
            cost_filters.append("c.user_id = ?")
            params.append(user_id)

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
            logger.info(
                f"[Timeline] Costs timeline returned {len(rows)} days for user_id={user_id}"
            )
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
        En mode dev, si user_id est None, agrège toutes les données.

        Returns:
            Liste de {date, input_tokens, output_tokens, total}
        """
        days = self._parse_period(period)

        # Fix: NE PAS utiliser COALESCE avec 'now' - filtre NULL au lieu de les grouper sur aujourd'hui
        token_filters = ["c.timestamp IS NOT NULL", "date(c.timestamp) = dates.date"]
        params: List[Any] = []

        # Si user_id est fourni, filtrer par user_id
        if user_id:
            token_filters.append("c.user_id = ?")
            params.append(user_id)

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
            logger.info(
                f"[Timeline] Tokens timeline returned {len(rows)} days for user_id={user_id}"
            )
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
        En mode dev, si user_id est None, agrège toutes les données.

        Args:
            metric: "messages", "tokens", "costs"
            period: "7d", "30d", "90d", "1y"
            user_id: ID utilisateur (OBLIGATOIRE en prod, optionnel en dev)
            session_id: ID session (optionnel)

        Returns:
            Dict {agent_name: count}
        """
        days = self._parse_period(period)

        # Whitelist des agents valides (filtrage agents fantômes/legacy)
        valid_agents = {"anima", "neo", "nexus", "user", "system"}

        # Mapping des noms d'agents techniques vers les noms d'affichage
        agent_display_names = {
            "anima": "Anima",
            "neo": "Neo",
            "nexus": "Nexus",
            "user": "User",
            "system": "System",
        }

        if metric == "threads":
            # Compter les threads par agent via les messages associés
            # On utilise la table messages qui lie thread_id -> agent
            conditions = [
                "m.created_at IS NOT NULL",
                f"date(m.created_at) >= date('now', '-{days} days')",
            ]
            params = []

            if user_id:
                conditions.append("m.user_id = ?")
                params.append(user_id)

            if session_id:
                conditions.append("m.session_id = ?")
                params.append(session_id)

            where_clause = " WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT agent_id, COUNT(DISTINCT thread_id) as total
                FROM messages m{where_clause}
                GROUP BY agent_id
                ORDER BY total DESC
            """

            try:
                rows = await self.db.fetch_all(query, tuple(params) if params else ())
                logger.info(
                    f"[Timeline] Distribution threads returned {len(rows)} agents"
                )

                result = {}
                for row in rows:
                    agent_name = (
                        row["agent_id"].lower() if row["agent_id"] else "unknown"
                    )

                    # Filtrer les agents invalides
                    if agent_name not in valid_agents:
                        logger.debug(
                            f"[Timeline] Agent filtré (non valide): {agent_name}"
                        )
                        continue

                    display_name = agent_display_names.get(
                        agent_name, agent_name.capitalize()
                    )
                    result[display_name] = int(row["total"])

                return result
            except Exception as e:
                logger.error(f"Erreur get_distribution threads: {e}", exc_info=True)
                return {}

        elif metric == "messages":
            # Compter les messages par agent
            conditions = [
                "created_at IS NOT NULL",
                f"date(created_at) >= date('now', '-{days} days')",
            ]
            params = []

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)

            where_clause = " WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT agent_id, COUNT(*) as total
                FROM messages{where_clause}
                GROUP BY agent_id
                ORDER BY total DESC
            """

            try:
                rows = await self.db.fetch_all(query, tuple(params) if params else ())
                logger.info(
                    f"[Timeline] Distribution messages returned {len(rows)} agents"
                )

                result = {}
                for row in rows:
                    agent_name = (
                        row["agent_id"].lower() if row["agent_id"] else "unknown"
                    )

                    # Filtrer les agents invalides
                    if agent_name not in valid_agents:
                        logger.debug(
                            f"[Timeline] Agent filtré (non valide): {agent_name}"
                        )
                        continue

                    display_name = agent_display_names.get(
                        agent_name, agent_name.capitalize()
                    )
                    result[display_name] = int(row["total"])

                return result
            except Exception as e:
                logger.error(f"Erreur get_distribution messages: {e}", exc_info=True)
                return {}

        elif metric in ["tokens", "costs"]:
            # Fix: NE PAS utiliser COALESCE avec 'now' - filtre NULL au lieu de les grouper sur aujourd'hui
            conditions = [
                "timestamp IS NOT NULL",
                f"date(timestamp) >= date('now', '-{days} days')",
            ]
            params = []

            # Si user_id est fourni, filtrer par user_id
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)

            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)

            where_clause = " WHERE " + " AND ".join(conditions)

            field = (
                "total_cost" if metric == "costs" else "input_tokens + output_tokens"
            )

            query = f"""
                SELECT agent, SUM({field}) as total
                FROM costs{where_clause}
                GROUP BY agent
                ORDER BY total DESC
            """

            try:
                rows = await self.db.fetch_all(query, tuple(params) if params else ())
                logger.info(
                    f"[Timeline] Distribution by agent returned {len(rows)} agents for metric={metric}"
                )

                # Filtrer les agents invalides et mapper les noms
                result = {}
                for row in rows:
                    agent_name = row["agent"].lower()

                    # Filtrer les agents invalides (agents fantômes)
                    if agent_name not in valid_agents:
                        logger.debug(
                            f"[Timeline] Agent filtré (non valide): {agent_name}"
                        )
                        continue

                    display_name = agent_display_names.get(
                        agent_name, agent_name.capitalize()
                    )
                    result[display_name] = int(row["total"])

                return result
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
