# src/backend/core/database/queries.py
# V6.7 - Backcompat messages ultra-robuste + utilitaire get_thread_any
#  - Schémas legacy pris en charge: id INTEGER, session_id NOT NULL (+FK), timestamp NOT NULL, éventuelle FK agent_id
#  - Schéma cible V6: id TEXT (UUID), created_at TEXT, pas de session_id/timestamp
import logging
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import aiosqlite

from .manager import DatabaseManager

logger = logging.getLogger(__name__)


# ------------------- Introspection schéma / FK ------------------- #
async def _pragma_table_info(db: DatabaseManager, table: str) -> List[aiosqlite.Row]:
    try:
        return await db.fetch_all(f"PRAGMA table_info({table})")
    except Exception as e:
        logger.warning(f"[PRAGMA] Impossible d'inspecter {table}: {e}")
        return []


async def _pragma_fk_list(db: DatabaseManager, table: str) -> List[Dict[str, Any]]:
    try:
        rows = await db.fetch_all(f"PRAGMA foreign_key_list({table})")
        return [dict(r) for r in (rows or [])]
    except Exception as e:
        logger.warning(f"[PRAGMA] Impossible d'inspecter les FKs de {table}: {e}")
        return []


async def _messages_id_is_integer(db: DatabaseManager) -> bool:
    rows = await _pragma_table_info(db, "messages")
    for r in rows or []:
        if r["name"] == "id":
            return "INT" in (r["type"] or "").upper()
    return False  # défaut: V6 (TEXT)


async def _messages_col_notnull(db: DatabaseManager, col: str) -> bool:
    rows = await _pragma_table_info(db, "messages")
    for r in rows or []:
        if r["name"] == col:
            return bool(r["notnull"])
    return False


async def _messages_requires_session_id(db: DatabaseManager) -> bool:
    return await _messages_col_notnull(db, "session_id")


async def _messages_requires_timestamp(db: DatabaseManager) -> bool:
    return await _messages_col_notnull(db, "timestamp")


async def _agent_fk_target(db: DatabaseManager) -> Optional[Tuple[str, str]]:
    for fk in await _pragma_fk_list(db, "messages"):
        if fk.get("from") == "agent_id":
            target_table = fk.get("table")
            target_column = fk.get("to") or "id"
            if isinstance(target_table, str) and isinstance(target_column, str):
                return target_table, target_column
    return None


async def _session_fk_target(db: DatabaseManager) -> Optional[Tuple[str, str]]:
    for fk in await _pragma_fk_list(db, "messages"):
        if fk.get("from") == "session_id":
            target_table = fk.get("table")
            target_column = fk.get("to") or "id"
            if isinstance(target_table, str) and isinstance(target_column, str):
                return target_table, target_column
    return None


async def _table_has_column(db: DatabaseManager, table: str, column: str) -> bool:
    rows = await _pragma_table_info(db, table)
    for row in rows or []:
        if row["name"] == column:
            return True
    return False


def _normalize_scope_identifier(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def _resolve_user_scope(user_id: Optional[str], session_id: Optional[str]) -> str:
    normalized_user = _normalize_scope_identifier(user_id)
    if normalized_user:
        return normalized_user
    normalized_session = _normalize_scope_identifier(session_id)
    if normalized_session:
        return normalized_session
    raise ValueError("User scope requires user_id or session_id.")


def _build_scope_condition(
    user_id: Optional[str],
    session_id: Optional[str],
    *,
    user_column: str = "user_id",
    session_column: str = "session_id",
) -> Tuple[str, Tuple[Any, ...]]:
    normalized_user = _normalize_scope_identifier(user_id)
    normalized_session = _normalize_scope_identifier(session_id)
    if normalized_user:
        # When the caller knows the user_id we enforce it strictly so data remains
        # accessible across sessions/devices for the same account.
        return f"{user_column} = ?", (normalized_user,)
    if normalized_session:
        return f"{session_column} = ?", (normalized_session,)
    raise ValueError("Scope requires at least user_id or session_id.")

# ------------------- Bootstraps legacy ------------------- #
def _guess_default_for(
    col_name: str, col_type: str, now_iso: str, user_id: Optional[str]
) -> Any:
    t = (col_type or "").upper()
    n = (col_name or "").lower()
    if n in {"id"}:
        return None
    if n in {"user_id", "owner", "owner_id"}:
        return user_id
    if any(k in n for k in ("created", "updated", "timestamp", "time", "date")):
        return now_iso
    if "INT" in t:
        return 0
    if any(k in t for k in ("REAL", "FLOA", "DOUB", "NUM")):
        return 0.0
    return ""  # TEXT/BLOB


async def _bootstrap_row_for_fk_table(
    db: DatabaseManager, table: str, pk_col: str, pk_value: str, thread_id: str
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    thr = await db.fetch_one("SELECT user_id FROM threads WHERE id = ?", (thread_id,))
    user_id = thr["user_id"] if thr and "user_id" in thr.keys() else None

    cols_info = await _pragma_table_info(db, table)
    if not cols_info:
        logger.warning(f"[FK] Table cible '{table}' introuvable.")
        return

    exists = await db.fetch_one(
        f"SELECT {pk_col} FROM {table} WHERE {pk_col} = ?", (pk_value,)
    )
    if exists:
        return

    insert_cols = [pk_col]
    insert_vals = [pk_value]
    for r in cols_info:
        name = r["name"]
        if name == pk_col:
            continue
        if bool(r["notnull"]) and r["dflt_value"] is None:
            insert_cols.append(name)
            insert_vals.append(_guess_default_for(name, r["type"] or "", now, user_id))

    placeholders = ", ".join(["?"] * len(insert_cols))
    cols_clause = ", ".join(insert_cols)
    await db.execute(
        f"INSERT OR IGNORE INTO {table} ({cols_clause}) VALUES ({placeholders})",
        tuple(insert_vals),
    )
    logger.info(f"[DDL] Bootstrap '{table}'({pk_col}='{pk_value}') assuré.")


async def _ensure_legacy_session_fk_row(
    db: DatabaseManager, thread_id: str
) -> Optional[str]:
    target = await _session_fk_target(db)
    if not target:
        return None
    table, col = target
    await _bootstrap_row_for_fk_table(
        db, table=table, pk_col=col, pk_value=thread_id, thread_id=thread_id
    )
    return thread_id


async def _maybe_neutralize_agent_id(
    db: DatabaseManager, agent_id: Optional[str]
) -> Optional[str]:
    target = await _agent_fk_target(db)
    if not target or agent_id is None:
        return agent_id
    tgt_table, tgt_col = target
    exists = await db.fetch_one(
        f"SELECT 1 FROM {tgt_table} WHERE {tgt_col} = ?", (agent_id,)
    )
    if exists:
        return agent_id
    if not await _messages_col_notnull(db, "agent_id"):
        logger.info(f"[FK] agent_id='{agent_id}' non référencé → neutralisé (NULL).")
        return None
    try:
        await _bootstrap_row_for_fk_table(
            db, table=tgt_table, pk_col=tgt_col, pk_value=agent_id, thread_id=""
        )
        logger.info(
            f"[FK] agent '{agent_id}' créé à la volée dans {tgt_table}.{tgt_col}."
        )
        return agent_id
    except Exception as e:
        logger.warning(
            f"[FK] Impossible de créer {tgt_table}({tgt_col})='{agent_id}': {e}"
        )
        return agent_id


# ------------------- Coûts (existant) ------------------- #
async def add_cost_log(
    db: DatabaseManager,
    timestamp: datetime,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_cost: float,
    feature: str,
):
    await db.execute(
        "INSERT INTO costs (timestamp, agent, model, input_tokens, output_tokens, total_cost, feature) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            timestamp.isoformat(),
            agent,
            model,
            input_tokens,
            output_tokens,
            total_cost,
            feature,
        ),
    )


async def get_costs_summary(db: DatabaseManager) -> Dict[str, float]:
    row = await db.fetch_one(
        """
        SELECT
            SUM(total_cost) AS total_cost,
            SUM(CASE WHEN date(timestamp) = date('now','localtime') THEN total_cost ELSE 0 END) AS today_cost,
            SUM(CASE WHEN strftime('%Y-%W', timestamp) = strftime('%Y-%W','now','localtime') THEN total_cost ELSE 0 END) AS week_cost,
            SUM(CASE WHEN strftime('%Y-%m',  timestamp) = strftime('%Y-%m','now','localtime') THEN total_cost ELSE 0 END) AS month_cost
        FROM costs
        """
    )
    if row:
        return {
            "total": row["total_cost"] or 0.0,
            "today": row["today_cost"] or 0.0,
            "this_week": row["week_cost"] or 0.0,
            "this_month": row["month_cost"] or 0.0,
        }
    return {"total": 0.0, "today": 0.0, "this_week": 0.0, "this_month": 0.0}


# ------------------- Documents (existant) ------------------- #
async def insert_document(
    db: DatabaseManager,
    filename: str,
    filepath: str,
    status: str,
    uploaded_at: str,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
) -> int:
    user_value = _resolve_user_scope(user_id, session_id)
    normalized_session = _normalize_scope_identifier(session_id) or user_value
    await db.execute(
        "INSERT INTO documents (filename, filepath, status, uploaded_at, session_id, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        (filename, filepath, status, uploaded_at, normalized_session, user_value),
    )
    row = await db.fetch_one("SELECT last_insert_rowid() AS id")
    if row is None:
        raise RuntimeError("Failed to retrieve inserted document identifier.")
    return int(row["id"])
async def update_document_processing_info(
    db: DatabaseManager,
    doc_id: int,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
    char_count: int,
    chunk_count: int,
    status: str,
):
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"UPDATE documents SET char_count = ?, chunk_count = ?, status = ? WHERE id = ? AND {scope_sql}",
        (char_count, chunk_count, status, doc_id, *scope_params),
    )
async def set_document_error_status(
    db: DatabaseManager, doc_id: int, session_id: Optional[str], error_message: str, *, user_id: Optional[str] = None
):
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"UPDATE documents SET status = 'error', error_message = ? WHERE id = ? AND {scope_sql}",
        (error_message, doc_id, *scope_params),
    )
async def insert_document_chunks(
    db: DatabaseManager,
    session_id: Optional[str],
    chunks: List[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
):
    if not chunks:
        return
    user_value = _resolve_user_scope(user_id, session_id)
    normalized_session = _normalize_scope_identifier(session_id) or user_value
    payload = [
        (
            c["id"],
            c["document_id"],
            c["chunk_index"],
            c.get("content", ""),
            normalized_session,
            user_value,
        )
        for c in chunks
    ]
    await db.executemany(
        "INSERT INTO document_chunks (id, document_id, chunk_index, content, session_id, user_id) VALUES (?, ?, ?, ?, ?, ?)",
        payload,
    )
async def get_all_documents(
    db: DatabaseManager,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if user_id or session_id:
        scope_sql, scope_params = _build_scope_condition(user_id, session_id)
        rows = await db.fetch_all(
            f"SELECT id, filename, status, char_count, chunk_count, error_message, uploaded_at FROM documents WHERE {scope_sql} ORDER BY uploaded_at DESC",
            scope_params,
        )
    else:
        rows = await db.fetch_all(
            "SELECT id, filename, status, char_count, chunk_count, error_message, uploaded_at FROM documents ORDER BY uploaded_at DESC"
        )
    return [dict(row) for row in rows]
async def get_document_by_id(
    db: DatabaseManager,
    doc_id: int,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if user_id or session_id:
        scope_sql, scope_params = _build_scope_condition(user_id, session_id)
        row = await db.fetch_one(
            f"SELECT * FROM documents WHERE id = ? AND {scope_sql}",
            (doc_id, *scope_params),
        )
    else:
        row = await db.fetch_one("SELECT * FROM documents WHERE id = ?", (doc_id,))
    return dict(row) if row else None
async def delete_document(
    db: DatabaseManager,
    doc_id: int,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
) -> bool:
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    existing = await db.fetch_one(
        f"SELECT id FROM documents WHERE id = ? AND {scope_sql}",
        (doc_id, *scope_params),
    )
    if not existing:
        return False

    params = (doc_id, *scope_params)
    await db.execute(
        f"DELETE FROM documents WHERE id = ? AND {scope_sql}",
        params,
    )
    await db.execute(
        f"DELETE FROM document_chunks WHERE document_id = ? AND {scope_sql}",
        params,
    )
    await db.execute(
        f"DELETE FROM thread_docs WHERE doc_id = ? AND {scope_sql}",
        params,
    )
    return True
# ------------------- Sessions (existant) ------------------- #
async def get_session_by_id(
    db: DatabaseManager, session_id: str
) -> Optional[aiosqlite.Row]:
    return await db.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))


async def get_all_sessions_overview(db: DatabaseManager) -> List[Dict[str, Any]]:
    rows = await db.fetch_all(
        """
        SELECT id, created_at, updated_at, summary,
               json_array_length(extracted_concepts) as concept_count,
               json_array_length(extracted_entities) as entity_count
        FROM sessions ORDER BY updated_at DESC
        """
    )
    return [dict(r) for r in rows]


async def update_session_analysis_data(
    db: DatabaseManager,
    session_id: str,
    summary: str,
    concepts: List[str],
    entities: List[str],
):
    await db.execute(
        """
        UPDATE sessions
        SET summary = ?, extracted_concepts = ?, extracted_entities = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            summary,
            json.dumps(concepts),
            json.dumps(entities),
            datetime.now(timezone.utc).isoformat(),
            session_id,
        ),
    )
    logger.info(f"Données d'analyse pour la session {session_id} mises à jour en BDD.")


# ------------------- Threads / Messages / Thread Docs ------------------- #


# -- Threads --
async def create_thread(
    db: DatabaseManager,
    session_id: Optional[str],
    *,
    user_id: Optional[str],
    type_: str,
    title: Optional[str] = None,
    agent_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    thread_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    user_value = _resolve_user_scope(user_id, session_id)
    normalized_session = _normalize_scope_identifier(session_id) or user_value
    await db.execute(
        "INSERT INTO threads (id, session_id, user_id, type, title, agent_id, meta, archived, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
        (
            thread_id,
            normalized_session,
            user_value,
            type_,
            title,
            agent_id,
            json.dumps(meta) if meta is not None else None,
            now,
            now,
        ),
    )
    return thread_id
async def get_threads(
    db: DatabaseManager,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
    type_: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    clauses: list[str] = ["archived = 0"]
    params: list[Any] = []
    if user_id or session_id:
        scope_sql, scope_params = _build_scope_condition(user_id, session_id)
        clauses.append(scope_sql)
        params.extend(scope_params)
    if type_:
        clauses.append("type = ?")
        params.append(type_)
    query = "SELECT * FROM threads"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = await db.fetch_all(query, tuple(params))
    return [dict(r) for r in rows]
async def get_thread(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if user_id or session_id:
        scope_sql, scope_params = _build_scope_condition(user_id, session_id)
        row = await db.fetch_one(
            f"SELECT * FROM threads WHERE id = ? AND {scope_sql}",
            (thread_id, *scope_params),
        )
    else:
        row = await db.fetch_one("SELECT * FROM threads WHERE id = ?", (thread_id,))
    return dict(row) if row else None
async def get_thread_any(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    row = await get_thread(db, thread_id, session_id, user_id=user_id)
    if row:
        return row
    fallback = await db.fetch_one("SELECT * FROM threads WHERE id = ?", (thread_id,))
    return dict(fallback) if fallback else None
async def update_thread(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
    title: Optional[str] = None,
    agent_id: Optional[str] = None,
    archived: Optional[bool] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    fields: list[str] = []
    params: list[Any] = []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if agent_id is not None:
        fields.append("agent_id = ?")
        params.append(agent_id)
    if meta is not None:
        fields.append("meta = ?")
        params.append(json.dumps(meta))
    if archived is not None:
        fields.append("archived = ?")
        params.append(1 if archived else 0)
    fields.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    params.extend([thread_id, *scope_params])
    await db.execute(
        f"UPDATE threads SET {', '.join(fields)} WHERE id = ? AND {scope_sql}",
        tuple(params),
    )
async def delete_thread(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
) -> bool:
    thread = await get_thread(db, thread_id, session_id, user_id=user_id)
    if not thread:
        return False

    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"DELETE FROM thread_docs WHERE thread_id = ? AND {scope_sql}",
        (thread_id, *scope_params),
    )
    await db.execute(
        f"DELETE FROM messages WHERE thread_id = ? AND {scope_sql}",
        (thread_id, *scope_params),
    )
    await db.execute(
        f"DELETE FROM threads WHERE id = ? AND {scope_sql}",
        (thread_id, *scope_params),
    )
    return True
# -- Messages --
async def add_message(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
    role: str,
    content: str,
    agent_id: Optional[str] = None,
    tokens: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(meta) if meta is not None else None

    id_is_int = await _messages_id_is_integer(db)
    need_session = await _messages_requires_session_id(db)
    need_timestamp = await _messages_requires_timestamp(db)
    has_user_column = await _table_has_column(db, "messages", "user_id")
    safe_agent_id = await _maybe_neutralize_agent_id(db, agent_id)
    normalized_session = _normalize_scope_identifier(session_id)
    session_value = normalized_session or _resolve_user_scope(user_id, session_id)
    user_value = _resolve_user_scope(user_id, session_id)

    def _cols_vals(base_cols: List[str], base_vals: List[Any]):
        cols, vals = list(base_cols), list(base_vals)
        if need_session:
            cols.append("session_id")
            vals.append(session_value)
        if has_user_column:
            cols.append("user_id")
            vals.append(user_value)
        if need_timestamp:
            cols.append("timestamp")
            vals.append(now)
        cols.append("created_at")
        vals.append(now)
        return cols, vals

    include_agent = (safe_agent_id is not None) or await _messages_col_notnull(
        db, "agent_id"
    )

    if id_is_int:
        base_cols = ["thread_id", "role", "content", "tokens", "meta"]
        base_vals = [thread_id, role, content, tokens, meta_json]
        if include_agent:
            base_cols.insert(2, "agent_id")
            base_vals.insert(2, safe_agent_id)
        cols, vals = _cols_vals(base_cols, base_vals)
        placeholders = ", ".join(["?"] * len(cols))
        await db.execute(
            f"INSERT INTO messages ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
        )
        row = await db.fetch_one("SELECT last_insert_rowid() AS id")
        message_id = str(row["id"]) if row and "id" in row.keys() else None
    else:
        message_id = uuid.uuid4().hex
        base_cols = ["id", "thread_id", "role", "content", "tokens", "meta"]
        base_vals = [message_id, thread_id, role, content, tokens, meta_json]
        if include_agent:
            base_cols.insert(3, "agent_id")
            base_vals.insert(3, safe_agent_id)
        cols, vals = _cols_vals(base_cols, base_vals)
        placeholders = ", ".join(["?"] * len(cols))
        await db.execute(
            f"INSERT INTO messages ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
        )

    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"UPDATE threads SET updated_at = ? WHERE id = ? AND {scope_sql}",
        (now, thread_id, *scope_params),
    )
    return {"id": message_id, "created_at": now}
async def get_messages(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
    limit: int = 50,
    before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    clauses = ["thread_id = ?"]
    params: list[Any] = [thread_id]
    if user_id or session_id:
        scope_sql, scope_params = _build_scope_condition(user_id, session_id)
        clauses.append(scope_sql)
        params.extend(scope_params)
    if before:
        clauses.append("created_at < ?")
        params.append(before)
    query = "SELECT * FROM messages"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = await db.fetch_all(query, tuple(params))
    return [dict(r) for r in rows][::-1]
# -- Thread Docs --
async def set_thread_docs(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str],
    doc_ids: List[int],
    *,
    user_id: Optional[str] = None,
    weight: float = 1.0,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    user_value = _resolve_user_scope(user_id, session_id)
    normalized_session = _normalize_scope_identifier(session_id) or user_value
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"DELETE FROM thread_docs WHERE thread_id = ? AND {scope_sql}",
        (thread_id, *scope_params),
    )
    params = [
        (thread_id, int(d), normalized_session, user_value, weight, now)
        for d in doc_ids
    ]
    if params:
        await db.executemany(
            """
            INSERT INTO thread_docs (thread_id, doc_id, session_id, user_id, weight, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            params,
        )
async def append_thread_docs(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str],
    doc_ids: List[int],
    *,
    user_id: Optional[str] = None,
    weight: float = 1.0,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    user_value = _resolve_user_scope(user_id, session_id)
    normalized_session = _normalize_scope_identifier(session_id) or user_value
    params = [
        (thread_id, int(d), normalized_session, user_value, weight, now)
        for d in doc_ids
    ]
    if params:
        await db.executemany(
            """
            INSERT INTO thread_docs (thread_id, doc_id, session_id, user_id, weight, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_id, doc_id) DO UPDATE SET
                session_id = excluded.session_id,
                user_id = excluded.user_id,
                weight = excluded.weight,
                last_used_at = excluded.last_used_at
            """,
            params,
        )
async def get_thread_docs(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    clauses = ["td.thread_id = ?"]
    params: list[Any] = [thread_id]
    if user_id or session_id:
        scope_sql, scope_params = _build_scope_condition(
            user_id,
            session_id,
            user_column="td.user_id",
            session_column="td.session_id",
        )
        clauses.append(scope_sql)
        params.extend(scope_params)
    clauses.append("d.user_id = td.user_id")
    query = (
        "SELECT td.thread_id, td.doc_id, td.weight, td.last_used_at, d.filename, d.status "
        "FROM thread_docs td "
        "JOIN documents d ON d.id = td.doc_id"
    )
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY td.last_used_at DESC"
    rows = await db.fetch_all(query, tuple(params))
    return [dict(r) for r in rows]
