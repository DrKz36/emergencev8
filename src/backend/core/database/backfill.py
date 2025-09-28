# src/backend/core/database/backfill.py
"""Utilities to backfill user-scoped data after introducing user_id columns."""
from __future__ import annotations

import hashlib
import logging
from typing import Dict, Tuple

from backend.core.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


def _normalize_email(value: object) -> str | None:
    if value is None:
        return None
    try:
        text = str(value).strip().lower()
    except Exception:
        return None
    return text or None


def _compute_user_id(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


async def _sync_auth_session_user_ids(db: DatabaseManager) -> Dict[str, str]:
    rows = await db.fetch_all("SELECT id, email, user_id FROM auth_sessions")
    if not rows:
        return {}

    updates: list[Tuple[str, str]] = []
    mapping: Dict[str, str] = {}

    for row in rows:
        session_id = str(row["id"]).strip() if row["id"] else ""
        if not session_id:
            continue
        email = _normalize_email(row["email"])
        if not email:
            continue
        expected = _compute_user_id(email)
        stored = str(row["user_id"]).strip() if row["user_id"] else ""
        mapping[session_id] = expected
        if stored != expected:
            updates.append((expected, session_id))

    if updates:
        await db.executemany(
            "UPDATE auth_sessions SET user_id = ? WHERE id = ?",
            updates,
        )
        logger.info("Auth sessions user_id backfilled: %d", len(updates))

    return mapping


async def _apply_session_mapping(
    db: DatabaseManager,
    table: str,
    session_column: str,
    mapping: Dict[str, str],
    *,
    user_column: str = "user_id",
) -> None:
    if not mapping:
        return
    updates = [
        (user_id, session_id)
        for session_id, user_id in mapping.items()
        if session_id
    ]
    if not updates:
        return
    query = f"""
        UPDATE {table}
           SET {user_column} = ?
         WHERE {session_column} = ?
           AND ({user_column} IS NULL OR {user_column} = '' OR {user_column} = {session_column})
    """
    await db.executemany(query, updates)


async def _backfill_from_threads(db: DatabaseManager) -> None:
    await db.execute(
        """
        UPDATE messages
           SET user_id = (
               SELECT user_id
                 FROM threads
                WHERE threads.id = messages.thread_id
           )
         WHERE (user_id IS NULL OR user_id = '' OR user_id = session_id)
           AND EXISTS (
               SELECT 1
                 FROM threads
                WHERE threads.id = messages.thread_id
                  AND threads.user_id IS NOT NULL
                  AND threads.user_id <> ''
           )
        """
    )
    await db.execute(
        """
        UPDATE thread_docs
           SET user_id = (
               SELECT user_id
                 FROM threads
                WHERE threads.id = thread_docs.thread_id
           )
         WHERE (user_id IS NULL OR user_id = '' OR user_id = session_id)
           AND EXISTS (
               SELECT 1
                 FROM threads
                WHERE threads.id = thread_docs.thread_id
                  AND threads.user_id IS NOT NULL
                  AND threads.user_id <> ''
           )
        """
    )


async def _backfill_document_chunks(db: DatabaseManager) -> None:
    await db.execute(
        """
        UPDATE document_chunks
           SET user_id = (
               SELECT user_id
                 FROM documents
                WHERE documents.id = document_chunks.document_id
           )
         WHERE (user_id IS NULL OR user_id = '' OR user_id = session_id)
           AND EXISTS (
               SELECT 1
                 FROM documents
                WHERE documents.id = document_chunks.document_id
                  AND documents.user_id IS NOT NULL
                  AND documents.user_id <> ''
           )
        """
    )


async def run_user_scope_backfill(db: DatabaseManager) -> None:
    """Ensure user_id columns are populated using the JWT subject."""
    try:
        mapping = await _sync_auth_session_user_ids(db)
        if not mapping:
            logger.info("User scope backfill: no auth sessions with emails detected.")
            return

        await _apply_session_mapping(db, "threads", "session_id", mapping)
        await _apply_session_mapping(db, "messages", "session_id", mapping)
        await _apply_session_mapping(db, "thread_docs", "session_id", mapping)
        await _apply_session_mapping(db, "documents", "session_id", mapping)
        await _apply_session_mapping(db, "document_chunks", "session_id", mapping)

        await _backfill_from_threads(db)
        await _backfill_document_chunks(db)

        logger.info("User scope backfill completed (sessions=%d).", len(mapping))
    except Exception as exc:
        logger.warning("User scope backfill failed: %s", exc, exc_info=True)
