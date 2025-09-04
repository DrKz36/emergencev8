# src/backend/core/database/manager.py
# V23.2 - Fix search_messages: tri ISO-8601 lexicographique (ORDER BY created_at DESC)
import aiosqlite
import logging
import json
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

if TYPE_CHECKING:
    from backend.shared.models import Session

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gère la connexion aiosqlite et opérations de base."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
        self.db_dir = Path(self.db_path).parent
        self.db_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DatabaseManager (Async) V23.2 initialisé pour : {self.db_path}")

    async def connect(self):
        if self.connection is None or self.connection._conn is None:
            try:
                self.connection = await aiosqlite.connect(self.db_path)
                self.connection.row_factory = aiosqlite.Row
                await self.connection.execute("PRAGMA journal_mode=WAL;")
                await self.connection.execute("PRAGMA foreign_keys = ON;")
                logger.info("Connexion aiosqlite établie (WAL).")
            except Exception as e:
                logger.error(f"Erreur de connexion DB: {e}", exc_info=True)
                raise

    async def disconnect(self):
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Connexion aiosqlite fermée.")

    async def execute(self, query: str, params: tuple = None):
        if not self.connection:
            await self.connect()
        await self.connection.execute(query, params or ())
        await self.connection.commit()

    async def executemany(self, query: str, params: List[tuple]):
        if not self.connection:
            await self.connect()
        await self.connection.executemany(query, params)
        await self.connection.commit()

    async def fetch_one(self, query: str, params: tuple = None) -> Optional[aiosqlite.Row]:
        if not self.connection:
            await self.connect()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or ())
            return await cursor.fetchone()

    async def fetch_all(self, query: str, params: tuple = None) -> List[aiosqlite.Row]:
        if not self.connection:
            await self.connect()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or ())
            return await cursor.fetchall()

    # --------- Recherche messages (compat sans FTS) ---------
    async def search_messages(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recherche simple (LIKE) dans messages.content, tri du plus récent au plus ancien.
        Remarque: created_at est stocké en ISO-8601 → tri lexicographique fiable.
        """
        if not self.connection:
            await self.connect()
        like = f"%{query}%"
        sql = """
            SELECT id, thread_id, role, agent_id, content, tokens, meta, created_at
            FROM messages
            WHERE content LIKE ?
            ORDER BY created_at DESC
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

    async def save_session(self, session_data: 'Session'):
        history_json = json.dumps(getattr(session_data, 'history', []))
        metadata = getattr(session_data, 'metadata', {})
        summary = metadata.get('summary')
        concepts = metadata.get('concepts')
        entities = metadata.get('entities')
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
            session_data.end_time.isoformat() if session_data.end_time else datetime.now(timezone.utc).isoformat(),
            history_json,
            summary,
            concepts_json,
            entities_json
        )
        try:
            await self.execute(query, params)
            logger.info(f"Session {session_data.id} sauvegardée.")
        except Exception as e:
            logger.error(f"Échec sauvegarde session {session_data.id}: {e}", exc_info=True)
            # on ne raise pas
