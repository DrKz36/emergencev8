# src/backend/core/database/backfill.py
"""Utilities to backfill user-scoped data after introducing user_id columns."""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Dict, Tuple

from backend.core.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


def _extract_email(row) -> str | None:
    if row is None:
        return None
    value = None
    if isinstance(row, dict):
        value = row.get("email")
    else:
        try:
            value = row["email"]  # type: ignore[index]
        except Exception:
            try:
                value = row[0]  # type: ignore[index]
            except Exception:
                value = None
    return _normalize_email(value)


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


async def _resolve_placeholder_target_email(db: DatabaseManager) -> str | None:
    env_candidates = [
        os.getenv("AUTH_DEV_DEFAULT_EMAIL"),
    ]
    admin_env = os.getenv("AUTH_ADMIN_EMAILS")
    if admin_env:
        env_candidates.extend(admin_env.split(","))
    for candidate_raw in env_candidates:
        normalized = _normalize_email(candidate_raw)
        if normalized:
            return normalized
    row = await db.fetch_one(
        "SELECT email FROM auth_sessions WHERE email IS NOT NULL ORDER BY issued_at DESC LIMIT 1"
    )
    candidate = _extract_email(row)
    if candidate:
        return candidate
    row = await db.fetch_one(
        "SELECT email FROM auth_allowlist WHERE email IS NOT NULL ORDER BY created_at ASC LIMIT 1"
    )
    candidate = _extract_email(row)
    if candidate:
        return candidate
    return None


async def _resolve_legacy_placeholder_aliases(db: DatabaseManager) -> Dict[str, str]:
    rows = await db.fetch_all(
        "SELECT DISTINCT user_id FROM threads WHERE user_id IS NOT NULL AND TRIM(user_id) <> ''"
    )
    has_fg_placeholder = False
    for row in rows or []:
        value = row["user_id"]
        text = str(value).strip() if value is not None else ""
        if text and text.upper() == "FG":
            has_fg_placeholder = True
            break
    if not has_fg_placeholder:
        return {}
    target_email = await _resolve_placeholder_target_email(db)
    if not target_email:
        logger.warning(
            "User scope backfill: placeholder 'FG' detected but no email mapping was found."
        )
        return {}
    target_user_id = _compute_user_id(target_email)
    return {"FG": target_user_id}


async def _apply_placeholder_aliases(
    db: DatabaseManager, replacements: Dict[str, str]
) -> int:
    if not replacements:
        return 0
    tables = (
        ("threads", "user_id"),
        ("messages", "user_id"),
        ("thread_docs", "user_id"),
        ("documents", "user_id"),
        ("document_chunks", "user_id"),
    )
    total_updated = 0
    for placeholder, resolved in replacements.items():
        if not placeholder or not resolved or placeholder == resolved:
            continue
        placeholder_updates = 0
        for table, column in tables:
            count_row = await db.fetch_one(
                f"SELECT COUNT(*) AS count FROM {table} WHERE {column} = ?",
                (placeholder,),
            )
            count = int(count_row[0]) if count_row else 0
            if not count:
                continue
            await db.execute(
                f"UPDATE {table} SET {column} = ? WHERE {column} = ?",
                (resolved, placeholder),
            )
            placeholder_updates += count
            total_updated += count
        if placeholder_updates:
            logger.info(
                "User scope backfill: remapped placeholder '%s' (rows=%d).",
                placeholder,
                placeholder_updates,
            )
    return total_updated

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
    placeholder_map: Dict[str, str] = {}
    placeholder_rows = 0
    try:
        mapping = await _sync_auth_session_user_ids(db)
        session_mapping_count = len(mapping)
        has_changes = False

        if mapping:
            await _apply_session_mapping(db, "threads", "session_id", mapping)
            await _apply_session_mapping(db, "messages", "session_id", mapping)
            await _apply_session_mapping(db, "thread_docs", "session_id", mapping)
            await _apply_session_mapping(db, "documents", "session_id", mapping)
            await _apply_session_mapping(db, "document_chunks", "session_id", mapping)
            has_changes = True

        placeholder_map = await _resolve_legacy_placeholder_aliases(db)
        if placeholder_map:
            placeholder_rows = await _apply_placeholder_aliases(db, placeholder_map)
            if placeholder_rows:
                has_changes = True

        if has_changes:
            await _backfill_from_threads(db)
            await _backfill_document_chunks(db)

        if not mapping and not placeholder_map:
            logger.info("User scope backfill: nothing to update.")
        else:
            logger.info(
                "User scope backfill completed (session_mappings=%d, legacy_rows=%d).",
                session_mapping_count,
                placeholder_rows,
            )
    except Exception as exc:
        logger.warning("User scope backfill failed: %s", exc, exc_info=True)

