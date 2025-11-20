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
        # Global write mutex pour sérialiser écritures critiques (auth)
        self._write_lock = asyncio.Lock()
        logger.info(
            f"DatabaseManager (Async) V23.3-locked initialisé pour : {self.db_path}"
        )

    async def connect(self):
        if not self.is_connected():
            try:
                # Timeout augmenté à 60s pour Cloud Run + retry logic
                self.connection = await aiosqlite.connect(self.db_path, timeout=60.0)
                self.connection.row_factory = aiosqlite.Row

                # WAL mode (Write-Ahead Logging) pour permettre lectures concurrentes
                await self.connection.execute("PRAGMA journal_mode=WAL;")

                # Busy timeout maximal pour éviter "database is locked"
                await self.connection.execute(
                    "PRAGMA busy_timeout = 60000;"
                )  # 60 secondes (max)

                # Foreign keys actives
                await self.connection.execute("PRAGMA foreign_keys = ON;")

                # OPTIMISATIONS ANTI-LOCK AGRESSIVES
                # synchronous=NORMAL: Balance perf/durabilité (WAL checkpoint async)
                await self.connection.execute("PRAGMA synchronous = NORMAL;")

                # Cache augmenté à 128MB pour réduire I/O disk
                await self.connection.execute(
                    "PRAGMA cache_size = -131072;"
                )  # 128MB cache

                # Temp en mémoire pour éviter locks sur fichiers temporaires
                await self.connection.execute("PRAGMA temp_store = MEMORY;")

                # Locking mode NORMAL (défaut mais explicite)
                await self.connection.execute("PRAGMA locking_mode = NORMAL;")

                # WAL autocheckpoint agressif (chaque 1000 pages au lieu de 1000 par défaut)
                # Réduit la taille du WAL et les locks prolongés
                await self.connection.execute("PRAGMA wal_autocheckpoint = 500;")

                # Page size optimisé (4KB par défaut, on garde)
                # await self.connection.execute("PRAGMA page_size = 4096;")

                logger.info(
                    "Connexion aiosqlite établie (WAL, busy_timeout=60s, cache=128MB, optimisée anti-lock)."
                )
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
                    logger.info(
                        f"Database reconnected successfully (attempt {attempt + 1}/{self.max_retries})"
                    )
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Reconnection attempt {attempt + 1}/{self.max_retries} failed: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(
                            self.retry_delay * (attempt + 1)
                        )  # Backoff exponentiel
                    else:
                        logger.error(
                            f"Failed to reconnect to database after {self.max_retries} attempts",
                            exc_info=True,
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

        # Retry logic pour database locked errors - augmenté à 8 tentatives
        max_lock_retries = 8
        for attempt in range(max_lock_retries):
            try:
                cursor = await conn.execute(query, params or ())
                if commit:
                    await conn.commit()
                return cursor
            except Exception as e:
                if (
                    "database is locked" in str(e).lower()
                    and attempt < max_lock_retries - 1
                ):
                    # Exponential backoff plus agressif: 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8s
                    wait_time = 0.2 * (2**attempt)
                    logger.warning(
                        f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
        # Unreachable, but satisfies mypy
        raise RuntimeError("Database operation failed after all retries")

    async def executemany(
        self,
        query: str,
        params: Iterable[Tuple[Any, ...]],
        *,
        commit: bool = False,
    ) -> aiosqlite.Cursor:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors - augmenté à 8 tentatives
        max_lock_retries = 8
        for attempt in range(max_lock_retries):
            try:
                cursor = await conn.executemany(query, params)
                if commit:
                    await conn.commit()
                return cursor
            except Exception as e:
                if (
                    "database is locked" in str(e).lower()
                    and attempt < max_lock_retries - 1
                ):
                    wait_time = 0.2 * (2**attempt)
                    logger.warning(
                        f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
        # Unreachable, but satisfies mypy
        raise RuntimeError("Database operation failed after all retries")

    async def fetch_one(
        self,
        query: str,
        params: Optional[Tuple[Any, ...]] = None,
    ) -> Optional[aiosqlite.Row]:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors - augmenté à 8 tentatives
        max_lock_retries = 8
        for attempt in range(max_lock_retries):
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    return await cursor.fetchone()
            except Exception as e:
                if (
                    "database is locked" in str(e).lower()
                    and attempt < max_lock_retries - 1
                ):
                    wait_time = 0.2 * (2**attempt)
                    logger.warning(
                        f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
        # Unreachable, but satisfies mypy
        raise RuntimeError("Database operation failed after all retries")

    async def fetch_all(
        self,
        query: str,
        params: Optional[Tuple[Any, ...]] = None,
    ) -> List[aiosqlite.Row]:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors - augmenté à 8 tentatives
        max_lock_retries = 8
        for attempt in range(max_lock_retries):
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params or ())
                    rows = await cursor.fetchall()
                return list(rows)
            except Exception as e:
                if (
                    "database is locked" in str(e).lower()
                    and attempt < max_lock_retries - 1
                ):
                    wait_time = 0.2 * (2**attempt)
                    logger.warning(
                        f"Database locked, retry {attempt + 1}/{max_lock_retries} after {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
        # Unreachable, but satisfies mypy
        raise RuntimeError("Database operation failed after all retries")

    async def commit(self) -> None:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors - augmenté à 8 tentatives
        max_lock_retries = 8
        for attempt in range(max_lock_retries):
            try:
                await conn.commit()
                return
            except Exception as e:
                if (
                    "database is locked" in str(e).lower()
                    and attempt < max_lock_retries - 1
                ):
                    wait_time = 0.2 * (2**attempt)
                    logger.warning(
                        f"Database locked on commit, retry {attempt + 1}/{max_lock_retries} after {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def rollback(self) -> None:
        conn = await self._ensure_connection()

        # Retry logic pour database locked errors - augmenté à 8 tentatives
        max_lock_retries = 8
        for attempt in range(max_lock_retries):
            try:
                await conn.rollback()
                return
            except Exception as e:
                if (
                    "database is locked" in str(e).lower()
                    and attempt < max_lock_retries - 1
                ):
                    wait_time = 0.2 * (2**attempt)
                    logger.warning(
                        f"Database locked on rollback, retry {attempt + 1}/{max_lock_retries} after {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def execute_critical_write(
        self,
        query: str,
        params: Optional[Tuple[Any, ...]] = None,
        *,
        commit: bool = True,
    ) -> aiosqlite.Cursor:
        """
        Exécute une écriture critique (auth sessions, audit logs) avec mutex global.
        Sérialise les écritures concurrentes pour éviter "database is locked".

        Utiliser cette méthode pour :
        - INSERT/UPDATE auth_sessions
        - INSERT auth_audit_log
        - Autres écritures transactionnelles critiques

        Ne PAS utiliser pour lectures simples (fetch_one, fetch_all).
        """
        async with self._write_lock:
            logger.debug(f"Critical write acquired lock: {query[:50]}...")
            try:
                result = await self.execute(query, params, commit=commit)
                logger.debug(f"Critical write completed: {query[:50]}...")
                return result
            except Exception as e:
                logger.error(f"Critical write failed: {e}", exc_info=True)
                raise

    async def initialize(self, migrations_dir: Optional[str] = None) -> None:
        """
        Convenience helper used by tests to provision an in-memory database.
        """
        from .schema import initialize_database  # import local pour éviter cycles

        default_dir = Path(__file__).resolve().parent / "migrations"
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

    async def save_session(self, session_data: "Session") -> None:
        """
        Persist session metadata to the 'threads' table.
        Migration V6.8: 'sessions' table is deprecated. We now update 'threads'.
        """
        metadata = getattr(session_data, "metadata", {}) or {}

        # Determine thread_id: use metadata['thread_id'] if available, else session_id (legacy behavior)
        thread_id = metadata.get("thread_id") or session_data.id

        # Prepare meta JSON
        # We merge summary/concepts/entities into the meta dict if they are not already there
        # (though usually they are part of metadata dict in Session object)
        meta_dict = metadata.copy()

        # Serialize meta
        try:
            meta_json = json.dumps(meta_dict)
        except Exception:
            meta_json = "{}"

        created_at = session_data.start_time.isoformat()
        updated_at = (
            session_data.end_time.isoformat()
            if session_data.end_time
            else datetime.now(timezone.utc).isoformat()
        )

        # Upsert into threads
        # We do NOT update 'type', 'title', 'created_at' on conflict to preserve existing values.
        # We only update 'updated_at' and 'meta'.
        query = """
            INSERT INTO threads (id, session_id, user_id, type, title, created_at, updated_at, meta)
            VALUES (?, ?, ?, 'chat', ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at = excluded.updated_at,
                meta = excluded.meta;
        """

        # Default title for new threads created via this path (fallback)
        title = f"Session {str(session_data.id)[:8]}"

        params = (
            thread_id,
            session_data.id,
            session_data.user_id,
            title,
            created_at,
            updated_at,
            meta_json,
        )

        try:
            await self.execute(query, params, commit=True)
            logger.info(f"Session {session_data.id} (thread {thread_id}) saved to threads.")
        except Exception as e:
            logger.error(
                f"Failed to save session {session_data.id} to threads: {e}", exc_info=True
            )
            # We do not raise to avoid breaking the flow

