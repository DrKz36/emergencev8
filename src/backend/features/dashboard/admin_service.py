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
            # Get global costs (no user_id or session_id filter, admin mode)
            costs_global = await db_queries.get_costs_summary(self.db, allow_global=True)

            # Get all documents and sessions (admin mode)
            documents_all = await db_queries.get_all_documents(self.db, allow_global=True)
            sessions_all = await db_queries.get_all_sessions_overview(self.db, allow_global=True)

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
        """Get per-user statistics breakdown with flexible user matching."""
        try:
            # Get all unique user_ids from sessions
            query = """
                SELECT DISTINCT user_id
                FROM sessions
                WHERE user_id IS NOT NULL
                ORDER BY created_at DESC
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query)
            user_id_rows = await cursor.fetchall()

            # Get all emails from auth_allowlist
            cursor = await conn.execute("SELECT email, role FROM auth_allowlist")
            allowlist_rows = await cursor.fetchall()

            # Create a mapping: user_id -> (email, role)
            import hashlib
            email_map = {}
            for email, role in allowlist_rows:
                # Hash the email to match against user_ids
                email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
                email_map[email_hash] = (email, role)
                # Also store plain email as key (for non-hashed user_ids)
                email_map[email] = (email, role)

            # Build rows with matched emails
            rows = []
            for (user_id,) in user_id_rows:
                if user_id in email_map:
                    email, role = email_map[user_id]
                    rows.append((user_id, email, role))
                else:
                    # Fallback: use user_id as email if no match
                    rows.append((user_id, user_id, 'member'))

            if not rows:
                logger.warning("[admin_dashboard] No users found in sessions table")

            users_data = []
            for row in rows:
                user_id = row[0]
                user_email = row[1] if row[1] else user_id  # Use user_id as fallback
                user_role = row[2] if row[2] else "member"
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

                # Get total usage time and modules used
                usage_stats = await self._get_user_usage_stats(user_id)
                modules_used = await self._get_user_modules_used(user_id)
                costs_by_module = await self._get_user_costs_by_module(user_id)
                first_session_time = await self._get_user_first_session(user_id)

                users_data.append({
                    "user_id": user_id,
                    "email": user_email,
                    "role": user_role,
                    "total_cost": float(user_costs.get("total", 0.0) or 0.0),
                    "session_count": len(user_sessions) if user_sessions else 0,
                    "document_count": len(user_documents) if user_documents else 0,
                    "last_activity": await self._get_user_last_activity(user_id),
                    "first_session": first_session_time,
                    "total_usage_time_minutes": usage_stats.get("total_minutes", 0),
                    "modules_used": modules_used,
                    "costs_by_module": costs_by_module,
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

    async def _get_user_first_session(self, user_id: str) -> Optional[str]:
        """Get first session creation timestamp for a user."""
        try:
            query = """
                SELECT MIN(created_at) as first_session
                FROM sessions
                WHERE user_id = ?
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query, (user_id,))
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
        except Exception as e:
            logger.debug(f"Error getting first session for {user_id}: {e}")
        return None

    async def _get_user_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Calculate total usage time for a user based on sessions."""
        try:
            query = """
                SELECT created_at, updated_at
                FROM sessions
                WHERE user_id = ?
                ORDER BY created_at
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query, (user_id,))
            rows = await cursor.fetchall()

            total_minutes = 0
            for row in rows:
                if row[0] and row[1]:
                    try:
                        created = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                        updated = datetime.fromisoformat(row[1].replace('Z', '+00:00'))
                        duration = (updated - created).total_seconds() / 60
                        total_minutes += max(0, duration)  # Only positive durations
                    except Exception:
                        continue

            return {
                "total_minutes": round(total_minutes, 2),
            }
        except Exception as e:
            logger.debug(f"Error getting usage stats for {user_id}: {e}")
            return {"total_minutes": 0}

    async def _get_user_modules_used(self, user_id: str) -> List[str]:
        """Get list of unique modules/features used by a user."""
        try:
            query = """
                SELECT DISTINCT feature
                FROM costs
                WHERE user_id = ? AND feature IS NOT NULL
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query, (user_id,))
            rows = await cursor.fetchall()

            modules = [row[0] for row in rows if row[0]]
            return sorted(modules)
        except Exception as e:
            logger.debug(f"Error getting modules used for {user_id}: {e}")
            return []

    async def _get_user_costs_by_module(self, user_id: str) -> Dict[str, float]:
        """Get cost breakdown by module/feature for a user."""
        try:
            query = """
                SELECT feature, SUM(total_cost) as module_cost
                FROM costs
                WHERE user_id = ? AND feature IS NOT NULL
                GROUP BY feature
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query, (user_id,))
            rows = await cursor.fetchall()

            costs_by_module = {}
            for row in rows:
                if row[0]:
                    costs_by_module[row[0]] = float(row[1]) if row[1] else 0.0

            return costs_by_module
        except Exception as e:
            logger.debug(f"Error getting costs by module for {user_id}: {e}")
            return {}

    async def _get_date_metrics(self) -> Dict[str, Any]:
        """Get metrics grouped by date ranges with NULL-safe timestamp handling."""
        try:
            now = datetime.now(timezone.utc)

            # Fix Phase 1.4: Use COALESCE to handle NULL timestamps
            # This ensures the "Évolution des Coûts" chart displays data correctly
            daily_costs = []
            for i in range(7):
                date = now - timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")

                # Fix Phase 1.6: costs table a timestamp (pas created_at)
                query = """
                    SELECT
                        COALESCE(SUM(total_cost), 0) as daily_total,
                        COUNT(*) as request_count
                    FROM costs
                    WHERE DATE(COALESCE(timestamp, 'now')) = ?
                """
                conn = await self.db._ensure_connection()
                cursor = await conn.execute(query, (date_str,))
                row = await cursor.fetchone()
                daily_total = float(row[0]) if row and row[0] else 0.0
                request_count = int(row[1]) if row and row[1] else 0

                daily_costs.append({
                    "date": date_str,
                    "cost": daily_total,
                    "request_count": request_count,
                })

            # Reverse to show oldest to newest
            daily_costs.reverse()

            logger.info(f"[admin_dashboard] Date metrics calculated for last 7 days, total entries: {len(daily_costs)}")

            return {
                "last_7_days": daily_costs,
            }

        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting date metrics: {e}", exc_info=True)
            # Return valid structure with 7 days of zero data as fallback
            now = datetime.now(timezone.utc)
            fallback_costs = []
            for i in range(7):
                date = now - timedelta(days=6-i)
                fallback_costs.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "cost": 0.0,
                    "request_count": 0,
                })
            return {"last_7_days": fallback_costs}

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
        """Get cost logs history for a user with NULL-safe timestamp handling."""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            # Fix Phase 1.6: costs table a timestamp (pas created_at)
            query = """
                SELECT
                    timestamp as effective_timestamp,
                    agent,
                    model,
                    total_cost,
                    feature,
                    session_id
                FROM costs
                WHERE user_id = ?
                  AND COALESCE(timestamp, 'now') >= ?
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
                    "cost": float(row[3]) if row[3] else 0.0,
                    "feature": row[4],
                    "session_id": row[5],
                })

            logger.info(f"[admin_dashboard] Retrieved {len(history)} cost history entries for user {user_id}")
            return history
        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting cost history for {user_id}: {e}", exc_info=True)
            return []

    async def get_active_threads(self) -> List[Dict[str, Any]]:
        """
        Get all active threads (conversations) across all users.
        Returns thread details including user, device, IP, and last activity.

        Note: This returns THREADS (conversations from 'sessions' table - legacy naming),
        not authentication sessions. For authentication sessions, use AuthService.list_sessions() instead.
        """
        try:
            # Get all sessions
            query = """
                SELECT
                    s.id,
                    s.user_id,
                    s.created_at,
                    s.updated_at,
                    s.metadata
                FROM sessions s
                WHERE s.user_id IS NOT NULL
                ORDER BY s.updated_at DESC
                LIMIT 100
            """
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query)
            session_rows = await cursor.fetchall()

            # Get all emails from auth_allowlist
            cursor = await conn.execute("SELECT email, role FROM auth_allowlist")
            allowlist_rows = await cursor.fetchall()

            # Create email mapping
            import hashlib
            email_map = {}
            for email, role in allowlist_rows:
                email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
                email_map[email_hash] = (email, role)
                email_map[email] = (email, role)

            sessions = []
            for row in session_rows:
                session_id = row[0]
                user_id = row[1]
                created_at = row[2]
                updated_at = row[3]
                metadata_json = row[4]

                # Match user_id with email from allowlist
                if user_id in email_map:
                    email, role = email_map[user_id]
                else:
                    email = user_id
                    role = "member"

                # Parse metadata
                metadata = {}
                if metadata_json:
                    try:
                        import json
                        metadata = json.loads(metadata_json)
                    except Exception:
                        pass

                # Calculate session duration
                duration_minutes = 0
                if created_at and updated_at:
                    try:
                        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        duration_minutes = (updated - created).total_seconds() / 60
                    except Exception:
                        pass

                # Determine if session is still active (last activity < 30 minutes ago)
                is_active = False
                if updated_at:
                    try:
                        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        minutes_since_activity = (now - updated).total_seconds() / 60
                        is_active = minutes_since_activity < 30
                    except Exception:
                        pass

                sessions.append({
                    "session_id": session_id,
                    "user_id": user_id,
                    "email": email,
                    "role": role,
                    "created_at": created_at,
                    "last_activity": updated_at,
                    "duration_minutes": round(duration_minutes, 2),
                    "is_active": is_active,
                    "device": metadata.get("device", "Unknown"),
                    "ip_address": metadata.get("ip", "Unknown"),
                    "user_agent": metadata.get("user_agent", "Unknown"),
                })

            return sessions

        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting active threads: {e}", exc_info=True)
            return []

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a session by deleting it from the database.
        Returns True if successful, False if session not found.
        """
        try:
            query = "DELETE FROM sessions WHERE id = ?"
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query, (session_id,))
            await conn.commit()

            # Check if any rows were affected
            if cursor.rowcount > 0:
                logger.info(f"[admin_dashboard] Session {session_id} revoked successfully")
                return True
            else:
                logger.warning(f"[admin_dashboard] Session {session_id} not found")
                return False

        except Exception as e:
            logger.error(f"[admin_dashboard] Error revoking session {session_id}: {e}", exc_info=True)
            return False

    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system health and performance metrics.
        Includes uptime, average latency, error rates, and resource usage.
        """
        try:
            import psutil
            import os

            # Get process info
            process = psutil.Process(os.getpid())

            # Calculate uptime
            process_create_time = datetime.fromtimestamp(process.create_time(), tz=timezone.utc)
            now = datetime.now(timezone.utc)
            uptime_seconds = (now - process_create_time).total_seconds()

            # Get system metrics
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            # Get database stats
            db_stats = await self._get_database_stats()

            # Get error rate from recent logs (last hour)
            error_rate = await self._get_error_rate()

            # Get average latency from recent requests (last hour)
            avg_latency = await self._get_average_latency()

            return {
                "uptime": {
                    "seconds": int(uptime_seconds),
                    "formatted": self._format_uptime(uptime_seconds),
                    "start_time": process_create_time.isoformat(),
                },
                "performance": {
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_mb": round(memory_mb, 2),
                    "average_latency_ms": round(avg_latency, 2),
                },
                "reliability": {
                    "error_rate_percent": round(error_rate, 2),
                    "total_errors_last_hour": await self._count_recent_errors(),
                },
                "database": db_stats,
                "timestamp": now.isoformat(),
            }

        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting system metrics: {e}", exc_info=True)
            return {
                "uptime": {"seconds": 0, "formatted": "Unknown", "start_time": None},
                "performance": {"cpu_percent": 0, "memory_mb": 0, "average_latency_ms": 0},
                "reliability": {"error_rate_percent": 0, "total_errors_last_hour": 0},
                "database": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

    async def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            # Count total tables
            query = "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query)
            row = await cursor.fetchone()
            total_tables = row[0] if row else 0

            # Get database size (approximate)
            query = "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
            cursor = await conn.execute(query)
            row = await cursor.fetchone()
            db_size_bytes = row[0] if row else 0
            db_size_mb = db_size_bytes / (1024 * 1024)

            return {
                "total_tables": total_tables,
                "size_mb": round(db_size_mb, 2),
            }
        except Exception as e:
            logger.debug(f"Error getting database stats: {e}")
            return {"total_tables": 0, "size_mb": 0}

    async def _get_error_rate(self) -> float:
        """Calculate error rate based on recent activity (placeholder)."""
        # TODO: Implement actual error tracking
        # For now, return a placeholder value
        return 0.0

    async def _get_average_latency(self) -> float:
        """Calculate average API latency (placeholder)."""
        # TODO: Implement actual latency tracking
        # For now, return a placeholder value
        return 150.0

    async def _count_recent_errors(self) -> int:
        """Count errors in the last hour (placeholder)."""
        # TODO: Implement actual error counting
        # For now, return a placeholder value
        return 0

    async def get_detailed_costs_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed cost breakdown by user and module.
        Fix Phase 1.5: New endpoint to provide granular cost analysis.
        Returns costs aggregated by user, then by module/feature.
        """
        try:
            # Fix Phase 1.6: costs table a timestamp (pas created_at)
            query = """
                SELECT
                    user_id,
                    feature as module,
                    SUM(total_cost) as module_cost,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens,
                    COUNT(*) as request_count,
                    MIN(timestamp) as first_request,
                    MAX(timestamp) as last_request
                FROM costs
                WHERE user_id IS NOT NULL
                GROUP BY user_id, feature
                ORDER BY module_cost DESC
            """

            conn = await self.db._ensure_connection()
            cursor = await conn.execute(query)
            rows = await cursor.fetchall()

            # Structure by user
            breakdown = {}
            for row in rows:
                user_id = row[0]
                if user_id not in breakdown:
                    breakdown[user_id] = {
                        "user_id": user_id,
                        "total_cost": 0.0,
                        "total_requests": 0,
                        "modules": []
                    }

                module_data = {
                    "module": row[1] or "unknown",
                    "cost": float(row[2] or 0),
                    "input_tokens": int(row[3] or 0),
                    "output_tokens": int(row[4] or 0),
                    "request_count": int(row[5] or 0),
                    "first_request": row[6],
                    "last_request": row[7],
                }

                breakdown[user_id]["total_cost"] += module_data["cost"]
                breakdown[user_id]["total_requests"] += module_data["request_count"]
                breakdown[user_id]["modules"].append(module_data)

            # Sort modules within each user by cost
            for user_data in breakdown.values():
                user_data["modules"].sort(key=lambda x: x["cost"], reverse=True)

            # Convert to list and sort by total cost
            users_list = list(breakdown.values())
            users_list.sort(key=lambda x: x["total_cost"], reverse=True)

            grand_total = sum(u["total_cost"] for u in users_list)
            total_requests = sum(u["total_requests"] for u in users_list)

            logger.info(f"[admin_dashboard] Detailed costs breakdown: {len(users_list)} users, ${grand_total:.4f} total")

            return {
                "users": users_list,
                "total_users": len(users_list),
                "grand_total_cost": round(grand_total, 4),
                "total_requests": total_requests,
            }

        except Exception as e:
            logger.error(f"[admin_dashboard] Error getting detailed costs: {e}", exc_info=True)
            return {
                "users": [],
                "total_users": 0,
                "grand_total_cost": 0.0,
                "total_requests": 0,
            }
