# src/backend/features/usage/repository.py
"""
Phase 2 Guardian Cloud - Repository pour Usage Tracking
Utilise SQLite en fallback (Firestore viendra en Phase 3+)
Privacy-compliant: NO sensitive data stored
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Any

from backend.core.database.manager import DatabaseManager
from .models import UserSession, FeatureUsage, UserError

logger = logging.getLogger(__name__)


class UsageRepository:
    """Repository pour stocker usage tracking (sessions, features, errors)"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def ensure_tables(self) -> None:
        """Crée les tables usage tracking si elles n'existent pas"""
        try:
            # Table user_sessions
            await self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    session_start TEXT NOT NULL,
                    session_end TEXT,
                    duration_seconds INTEGER,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Table feature_usage
            await self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS feature_usage (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    feature_name TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL DEFAULT 'GET',
                    timestamp TEXT NOT NULL,
                    success BOOLEAN NOT NULL DEFAULT 1,
                    error_message TEXT,
                    duration_ms INTEGER,
                    status_code INTEGER NOT NULL DEFAULT 200,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Table user_errors
            await self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_errors (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_code INTEGER NOT NULL,
                    error_message TEXT NOT NULL,
                    stack_trace TEXT,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Index pour requêtes rapides
            await self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_feature_usage_timestamp ON feature_usage(timestamp)"
            )
            await self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_feature_usage_user ON feature_usage(user_email)"
            )
            await self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_errors_timestamp ON user_errors(timestamp)"
            )

            logger.info("Tables usage tracking créées/vérifiées")
        except Exception as e:
            logger.error(f"Erreur création tables usage: {e}")

    # ---- UserSession methods ----

    async def create_session(self, session: UserSession) -> UserSession:
        """Crée une nouvelle session utilisateur"""
        try:
            await self.db.execute(
                """
                INSERT INTO user_sessions (
                    id, user_email, session_start, session_end,
                    duration_seconds, ip_address, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.user_email,
                    session.session_start.isoformat(),
                    session.session_end.isoformat() if session.session_end else None,
                    session.duration_seconds,
                    session.ip_address,
                    session.user_agent,
                ),
            )
            logger.debug(f"Session créée: {session.id} ({session.user_email})")
            return session
        except Exception as e:
            logger.error(f"Erreur création session: {e}")
            raise

    async def end_session(self, session_id: str) -> None:
        """Ferme une session (met session_end + calcule durée)"""
        try:
            row = await self.db.fetch_one(
                "SELECT session_start FROM user_sessions WHERE id = ?", (session_id,)
            )
            if not row:
                logger.warning(f"Session {session_id} introuvable")
                return

            session_start = datetime.fromisoformat(row[0])
            session_end = datetime.now(timezone.utc)
            duration = int((session_end - session_start).total_seconds())

            await self.db.execute(
                """
                UPDATE user_sessions
                SET session_end = ?, duration_seconds = ?
                WHERE id = ?
                """,
                (session_end.isoformat(), duration, session_id),
            )
            logger.debug(f"Session terminée: {session_id} (durée: {duration}s)")
        except Exception as e:
            logger.error(f"Erreur fermeture session {session_id}: {e}")

    # ---- FeatureUsage methods ----

    async def log_feature_usage(self, usage: FeatureUsage) -> FeatureUsage:
        """Log utilisation d'une feature"""
        try:
            await self.db.execute(
                """
                INSERT INTO feature_usage (
                    id, user_email, feature_name, endpoint, method,
                    timestamp, success, error_message, duration_ms, status_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usage.id,
                    usage.user_email,
                    usage.feature_name,
                    usage.endpoint,
                    usage.method,
                    usage.timestamp.isoformat(),
                    int(usage.success),
                    usage.error_message,
                    usage.duration_ms,
                    usage.status_code,
                ),
            )
            # Pas de log debug pour chaque requête (trop verbose)
            return usage
        except Exception as e:
            logger.error(f"Erreur log feature usage: {e}")
            raise

    async def get_feature_usage_period(
        self, start: datetime, end: datetime
    ) -> List[FeatureUsage]:
        """Récupère feature usage pour une période donnée"""
        try:
            rows = await self.db.fetch_all(
                """
                SELECT id, user_email, feature_name, endpoint, method,
                       timestamp, success, error_message, duration_ms, status_code
                FROM feature_usage
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
                """,
                (start.isoformat(), end.isoformat()),
            )

            return [
                FeatureUsage(
                    id=row[0],
                    user_email=row[1],
                    feature_name=row[2],
                    endpoint=row[3],
                    method=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    success=bool(row[6]),
                    error_message=row[7],
                    duration_ms=row[8],
                    status_code=row[9],
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Erreur récup feature usage: {e}")
            return []

    # ---- UserError methods ----

    async def log_user_error(self, error: UserError) -> UserError:
        """Log une erreur utilisateur"""
        try:
            await self.db.execute(
                """
                INSERT INTO user_errors (
                    id, user_email, endpoint, method, error_type,
                    error_code, error_message, stack_trace, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    error.id,
                    error.user_email,
                    error.endpoint,
                    error.method,
                    error.error_type,
                    error.error_code,
                    error.error_message,
                    error.stack_trace,
                    error.timestamp.isoformat(),
                ),
            )
            logger.info(
                f"User error logged: {error.user_email} - {error.error_code} {error.endpoint}"
            )
            return error
        except Exception as e:
            logger.error(f"Erreur log user error: {e}")
            raise

    async def get_user_errors_period(
        self, start: datetime, end: datetime
    ) -> List[UserError]:
        """Récupère erreurs utilisateur pour une période"""
        try:
            rows = await self.db.fetch_all(
                """
                SELECT id, user_email, endpoint, method, error_type,
                       error_code, error_message, stack_trace, timestamp
                FROM user_errors
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY timestamp ASC
                """,
                (start.isoformat(), end.isoformat()),
            )

            return [
                UserError(
                    id=row[0],
                    user_email=row[1],
                    endpoint=row[2],
                    method=row[3],
                    error_type=row[4],
                    error_code=row[5],
                    error_message=row[6],
                    stack_trace=row[7],
                    timestamp=datetime.fromisoformat(row[8]),
                )
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Erreur récup user errors: {e}")
            return []

    # ---- Aggregation methods (pour UsageGuardian) ----

    async def get_active_users_count(self, start: datetime, end: datetime) -> int:
        """Compte utilisateurs actifs sur période"""
        try:
            row = await self.db.fetch_one(
                """
                SELECT COUNT(DISTINCT user_email)
                FROM feature_usage
                WHERE timestamp >= ? AND timestamp < ?
                """,
                (start.isoformat(), end.isoformat()),
            )
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Erreur count active users: {e}")
            return 0

    async def get_top_features(
        self, start: datetime, end: datetime, limit: int = 10
    ) -> List[dict[str, Any]]:
        """Top N features utilisées"""
        try:
            rows = await self.db.fetch_all(
                """
                SELECT feature_name, COUNT(*) as count
                FROM feature_usage
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY feature_name
                ORDER BY count DESC
                LIMIT ?
                """,
                (start.isoformat(), end.isoformat(), limit),
            )
            return [{"name": row[0], "count": row[1]} for row in rows]
        except Exception as e:
            logger.error(f"Erreur récup top features: {e}")
            return []

    async def get_error_breakdown(
        self, start: datetime, end: datetime
    ) -> dict[str, int]:
        """Breakdown erreurs par code HTTP"""
        try:
            rows = await self.db.fetch_all(
                """
                SELECT error_code, COUNT(*) as count
                FROM user_errors
                WHERE timestamp >= ? AND timestamp < ?
                GROUP BY error_code
                ORDER BY count DESC
                """,
                (start.isoformat(), end.isoformat()),
            )
            return {str(row[0]): row[1] for row in rows}
        except Exception as e:
            logger.error(f"Erreur breakdown errors: {e}")
            return {}
