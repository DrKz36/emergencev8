# src/backend/core/database/manager.py
# V23.2 - Retry logic pour reconnexion DB robuste
import aiosqlite
import asyncio
import logging
import json
from typing import Optional, List, TYPE_CHECKING, Dict, Any, Iterable, Tuple
from pathlib import Path
from datetime import datetime, timezone

if TYPE_CHECKING:
    from backend.shared.models import Session

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gère la connexion aiosqlite et opérations de base."""

    def __init__(self, db_path: str, max_retries: int = 3, retry_delay: float = 0.5):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
        self.db_dir = Path(self.db_path).parent
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logger.info(f"DatabaseManager (Async) V23.2 initialisé pour : {self.db_path}")

    async def connect(self):
        if not self.is_connected():
            try:
                self.connection = await aiosqlite.connect(self.db_path, timeout=30.0)
                self.connection.row_factory = aiosqlite.Row
                await self.connection.execute("PRAGMA journal_mode=WAL;")
                await self.connection.execute("PRAGMA busy_timeout = 10000;")  # 10 secondes
                await self.connection.execute("PRAGMA foreign_keys = ON;")
                logger.info("Connexion aiosqlite établie (WAL, busy_timeout=10s).")
            except Exception as e:
                logger.error(f"Erreur de connexion DB: {e}", exc_info=True)
                raise

    async def disconnect(self):
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Connexion aiosqlite fermée.")

    async def close(self) -> None:
        """Alias explicite pour compat tests externes."""
        await self.disconnect()

    def is_connected(self) -> bool:
        conn = self.connection
        if conn is None:
            return False
        if getattr(conn, "_conn", None) is None:
            return False
        if getattr(conn, "_closed", False):
            return False
        return True

    async def _ensure_connection(self) -> aiosqlite.Connection:
        """
        Assure qu'une connexion DB valide existe, avec retry logic robuste.
        Tente jusqu'à max_retries reconnexions avant d'échouer.
        """
        if not self.is_connected():
            logger.warning(
                "Database connection lost. Attempting automatic reconnection..."
            )

            last_error = None
            for attempt in range(self.max_retries):
                try:
                    # Force reset de la connexion pour éviter les états corrompus
                    if self.connection:
                        try:
                            await self.connection.close()
                        except Exception:
                            pass
                        self.connection = None

                    await self.connect()
                    logger.info(f"Database reconnected successfully (attempt {attempt + 1}/{self.max_retries})")
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Reconnection attempt {attempt + 1}/{self.max_retries} failed: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))  # Backoff exponentiel
                    else:
                        logger.error(
                            f"Failed to reconnect to database after {self.max_retries} attempts",
                            exc_info=True
                        )
                        raise RuntimeError(
                            f"Database connection is not available after {self.max_retries} reconnection attempts"
                        ) from last_error

        assert self.connection is not None  # pour mypy
        return self.connection

    async def execute(
        self,
        query: str,
        params: Optional[Tuple[Any, ...]] = None,
        *,
        commit: bool = False,
    ) -> aiosqlite.Cursor:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors
        max_lock_retries = 5
        for attempt in range(max_lock_retries):
            try:
                cursor = await conn.execute(query, params or ())
                if commit:
                    await conn.commit()
                return cursor
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_lock_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1, 0.2, 0.4, 0.8, 1.6s
                    logger.warning(f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def executemany(
        self,
        query: str,
        params: Iterable[Tuple[Any, ...]],
        *,
        commit: bool = False,
    ) -> aiosqlite.Cursor:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors
        max_lock_retries = 5
        for attempt in range(max_lock_retries):
            try:
                cursor = await conn.executemany(query, params)
                if commit:
                    await conn.commit()
                return cursor
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_lock_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1, 0.2, 0.4, 0.8, 1.6s
                    logger.warning(f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def fetch_one(
        self,
        query: str,
        params: Optional[Tuple[Any, ...]] = None,
    ) -> Optional[aiosqlite.Row]:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors
        max_lock_retries = 5
        for attempt in range(max_lock_retries):
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    return await cursor.fetchone()
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_lock_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1, 0.2, 0.4, 0.8, 1.6s
                    logger.warning(f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def fetch_all(
        self,
        query: str,
        params: Optional[Tuple[Any, ...]] = None,
    ) -> List[aiosqlite.Row]:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors
        max_lock_retries = 5
        for attempt in range(max_lock_retries):
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    rows = await cursor.fetchall()
                return list(rows)
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_lock_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1, 0.2, 0.4, 0.8, 1.6s
                    logger.warning(f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def commit(self) -> None:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors
        max_lock_retries = 5
        for attempt in range(max_lock_retries):
            try:
                await conn.commit()
                return
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_lock_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1, 0.2, 0.4, 0.8, 1.6s
                    logger.warning(f"Database locked on commit, retry {attempt + 1}/{max_lock_retries} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def rollback(self) -> None:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors
        max_lock_retries = 5
        for attempt in range(max_lock_retries):
            try:
                await conn.rollback()
                return
            except Exception as e:
                if "database is locked" in str(e).lower() and attempt < max_lock_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1, 0.2, 0.4, 0.8, 1.6s
                    logger.warning(f"Database locked on rollback, retry {attempt + 1}/{max_lock_retries} after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def initialize(self, migrations_dir: Optional[str] = None) -> None:
        """
        Convenience helper used by tests to provision an in-memory database.
        """
        from .schema import initialize_database  # import local pour éviter cycles

        default_dir = (
            Path(__file__).resolve().parent / "migrations"
        )
        await initialize_database(self, str(migrations_dir or default_dir))

    # --------- AJOUT POUR TemporalSearch ---------
    async def search_messages(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche simple (LIKE) dans messages.content, du plus récent au plus ancien.
        Compat sans FTS (FTS5 non requis par le schéma actuel).
        """
        if not self.is_connected():
            await self.connect()
        like = f"%{query}%"
        sql = """
            SELECT id, thread_id, role, agent_id, content, tokens, meta, created_at
            FROM messages
            WHERE content LIKE ?
            ORDER BY datetime(created_at) DESC
            LIMIT ?
        """
        rows = await self.fetch_all(sql, (like, int(limit)))
        out: List[Dict[str, Any]] = []
        for r in rows or []:
            d = {k: r[k] for k in r.keys()}
            # meta -> dict si JSON
            try:
                if d.get("meta"):
                    d["meta"] = json.loads(d["meta"])
            except Exception:
                pass
            out.append(d)
        return out

    # --------------------------------------------

    async def save_session(self, session_data: "Session"):
        history_json = json.dumps(getattr(session_data, "history", []))
        metadata = getattr(session_data, "metadata", {})
        summary = metadata.get("summary")
        concepts = metadata.get("concepts")
        entities = metadata.get("entities")
        concepts_json = json.dumps(concepts) if concepts is not None else None
        entities_json = json.dumps(entities) if entities is not None else None

        query = """
            INSERT INTO sessions (id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at = excluded.updated_at,
                session_data = excluded.session_data,
                summary = excluded.summary,
                extracted_concepts = excluded.extracted_concepts,
                extracted_entities = excluded.extracted_entities;
        """
        params = (
            session_data.id,
            session_data.user_id,
            session_data.start_time.isoformat(),
            session_data.end_time.isoformat()
            if session_data.end_time
            else datetime.now(timezone.utc).isoformat(),
            history_json,
            summary,
            concepts_json,
            entities_json,
        )
        try:
            await self.execute(query, params)
            logger.info(f"Session {session_data.id} sauvegardée.")
        except Exception as e:
            logger.error(
                f"Échec sauvegarde session {session_data.id}: {e}", exc_info=True
            )
            # on ne raise pas
