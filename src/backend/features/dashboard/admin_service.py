# src/backend/features/dashboard/admin_service.py
"""
Admin Dashboard Service - Global statistics accessible only to admins
V1.0 - Provides global aggregated data across all users and sessions
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries
from backend.core.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class AdminDashboardService:
    """
    Provides global aggregated analytics for administrators.
    Includes data breakdown by user, date ranges, and comprehensive metrics.
    """

    def __init__(self, db_manager: DatabaseManager, cost_tracker: CostTracker):
        self.db = db_manager
        self.cost_tracker = cost_tracker
        logger.info("AdminDashboardService V1.0 initialized.")

    async def get_global_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive global dashboard data for admins.
        Includes all users, all sessions, and aggregated metrics.
        """
        try:
            # Get global costs (no user_id or session_id filter)
            costs_global = await db_queries.get_costs_summary(self.db)

            # Get all documents and sessions
            documents_all = await db_queries.get_all_documents(self.db)
            sessions_all = await db_queries.get_all_sessions_overview(self.db)

            # Get per-user breakdown
            users_breakdown = await self._get_users_breakdown()

            # Calculate date-based metrics
            date_metrics = await self._get_date_metrics()

            return {
                "global_costs": {
                    "total_cost": float(costs_global.get("total", 0.0) or 0.0),
                    "today_cost": float(costs_global.get("today", 0.0) or 0.0),
                    "current_week_cost": float(costs_global.get("this_week", 0.0) or 0.0),
                    "current_month_cost": float(costs_global.get("this_month", 0.0) or 0.0),
                },
                "global_monitoring": {
                    "total_documents": len(documents_all) if documents_all else 0,
                    "total_sessions": len(sessions_all) if sessions_all else 0,
                    "total_users": len(users_breakdown),
                },
                "users_breakdown": users_breakdown,
                "date_metrics": date_metrics,
                "thresholds": {
                    "daily_threshold": self.cost_tracker.DAILY_LIMIT,
                    "weekly_threshold": self.cost_tracker.WEEKLY_LIMIT,
                    "monthly_threshold": self.cost_tracker.MONTHLY_LIMIT,
                },
            }
        except Exception as e:
            logger.error(f"[admin_dashboard] Error fetching global data: {e}", exc_info=True)
            return {
                "global_costs": {
                    "total_cost": 0.0,
                    "today_cost": 0.0,
                    "current_week_cost": 0.0,
                    "current_month_cost": 0.0,
                },
                "global_monitoring": {
                    "total_documents": 0,
                    "total_sessions": 0,
                    "total_users": 0,
                },
                "users_breakdown": [],
                "date_metrics": {},
                "thresholds": {
                    "daily_threshold": 1.0,
                    "weekly_threshold": 1.0,
                    "monthly_threshold": 1.0,
                },
            }

    async def _get_users_breakdown(self) -> List[Dict[str, Any]]:
        """Get per-user statistics breakdown."""
        try:
            # Query to get unique users from sessions
            query = """
                SELECT DISTINCT user_id
                FROM sessions
                WHERE user_id IS NOT NULL
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()

            users_data = []
            for row in rows:
                user_id = row[0]
                if not user_id:
                    continue

                # Get user-specific metrics
                user_costs = await db_queries.get_costs_summary(
                    self.db, user_id=user_id
                )
                user_sessions = await db_queries.get_all_sessions_overview(
                    self.db, user_id=user_id
                )
                user_documents = await db_queries.get_all_documents(
                    self.db, user_id=user_id
                )

                users_data.append({
                    "user_id": user_id,
                    "total_cost": float(user_costs.get("total", 0.0) or 0.0),
                    "session_count": len(user_sessions) if user_sessions else 0,
                    "document_count": len(user_documents) if user_documents else 0,
                    "last_activity": await self._get_user_last_activity(user_id),
                })

            # Sort by total cost descending
            users_data.sort(key=lambda x: x["total_cost"], reverse=True)
            return users_data

        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting users breakdown: {e}", exc_info=True)
            return []

    async def _get_user_last_activity(self, user_id: str) -> Optional[str]:
        """Get last activity timestamp for a user."""
        try:
            query = """
                SELECT MAX(updated_at) as last_activity
                FROM sessions
                WHERE user_id = ?
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query, (user_id,))
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
        except Exception as e:
            logger.debug(f"Error getting last activity for {user_id}: {e}")
        return None

    async def _get_date_metrics(self) -> Dict[str, Any]:
        """Get metrics grouped by date ranges."""
        try:
            now = datetime.now(timezone.utc)

            # Last 7 days breakdown
            daily_costs = []
            for i in range(7):
                date = now - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")

                query = """
                    SELECT COALESCE(SUM(total_cost), 0) as daily_total
                    FROM costs
                    WHERE DATE(timestamp) = ?
                """
                conn = await self.db._ensure_connection()
                cursor = await conn.execute(query, (date_str,))
                row = await cursor.fetchone()
                daily_total = float(row[0]) if row else 0.0

                daily_costs.append({
                    "date": date_str,
                    "cost": daily_total,
                })

            # Reverse to show oldest to newest
            daily_costs.reverse()

            return {
                "last_7_days": daily_costs,
            }

        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting date metrics: {e}", exc_info=True)
            return {"last_7_days": []}

    async def get_user_detailed_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed data for a specific user (admin view).
        Includes all sessions, costs history, and documents.
        """
        try:
            # Get user costs
            costs = await db_queries.get_costs_summary(self.db, user_id=user_id)

            # Get user sessions with details
            sessions = await db_queries.get_all_sessions_overview(self.db, user_id=user_id)

            # Get user documents
            documents = await db_queries.get_all_documents(self.db, user_id=user_id)

            # Get cost logs history for this user
            cost_history = await self._get_user_cost_history(user_id)

            return {
                "user_id": user_id,
                "costs": {
                    "total_cost": float(costs.get("total", 0.0) or 0.0),
                    "today_cost": float(costs.get("today", 0.0) or 0.0),
                    "current_week_cost": float(costs.get("this_week", 0.0) or 0.0),
                    "current_month_cost": float(costs.get("this_month", 0.0) or 0.0),
                },
                "sessions": sessions or [],
                "documents": documents or [],
                "cost_history": cost_history,
            }
        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting user {user_id} data: {e}", exc_info=True)
            return {
                "user_id": user_id,
                "costs": {
                    "total_cost": 0.0,
                    "today_cost": 0.0,
                    "current_week_cost": 0.0,
                    "current_month_cost": 0.0,
                },
                "sessions": [],
                "documents": [],
                "cost_history": [],
            }

    async def _get_user_cost_history(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get cost logs history for a user."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = """
                SELECT
                    timestamp,
                    agent,
                    model,
                    total_cost,
                    feature,
                    session_id
                FROM costs
                WHERE user_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query, (user_id, cutoff_date.isoformat()))
            rows = await cursor.fetchall()

            history = []
            for row in rows:
                history.append({
                    "timestamp": row[0],
                    "agent": row[1],
                    "model": row[2],
                    "cost": float(row[3]),
                    "feature": row[4],
                    "session_id": row[5],
                })

            return history
        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting cost history for {user_id}: {e}", exc_info=True)
            return []
