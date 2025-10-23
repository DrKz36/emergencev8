# src/backend/core/database/queries.py
# V6.7 - Backcompat messages ultra-robuste + utilitaire get_thread_any
#  - SchÃ©mas legacy pris en charge: id INTEGER, session_id NOT NULL (+FK), timestamp NOT NULL, Ã©ventuelle FK agent_id
#  - SchÃ©ma cible V6: id TEXT (UUID), created_at TEXT, pas de session_id/timestamp
import logging
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import aiosqlite

from .manager import DatabaseManager

logger = logging.getLogger(__name__)


# ------------------- Introspection schÃ©ma / FK ------------------- #
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
    return False  # dÃ©faut: V6 (TEXT)


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


# ------------------- NULL Timestamp Handling Helper ------------------- #
def get_safe_date_column(table: str, use_localtime: bool = True) -> str:
    """
    Returns a safe SQL expression to extract dates from tables that may have NULL timestamps.
    Uses COALESCE to fall back from timestamp → created_at → 'now' to prevent NULL date failures.

    Args:
        table: Table name (determines which columns to check first)
        use_localtime: If True, converts to localtime (default: True for consistency with existing queries)

    Returns:
        SQL expression like "DATE(COALESCE(timestamp, created_at, 'now'), 'localtime')"

    Examples:
        >>> get_safe_date_column("costs")
        "DATE(COALESCE(timestamp, created_at, 'now'), 'localtime')"

        >>> get_safe_date_column("messages", use_localtime=False)
        "DATE(COALESCE(created_at, timestamp, 'now'))"

    Usage in queries:
        date_col = get_safe_date_column("costs")
        query = f"SELECT {date_col} as date, SUM(total_cost) FROM costs WHERE {date_col} >= ..."
    """
    # Déterminer l'ordre de priorité des colonnes selon la table
    if table == "costs":
        # costs table: priorité timestamp (plus précis), puis created_at
        date_expr = "COALESCE(timestamp, created_at, 'now')"
    elif table == "messages":
        # messages table: priorité created_at (plus standard V6), puis timestamp (legacy)
        date_expr = "COALESCE(created_at, timestamp, 'now')"
    elif table in ("sessions", "threads", "documents"):
        # Tables avec created_at standard
        date_expr = "COALESCE(created_at, 'now')"
    else:
        # Par défaut: essayer created_at, puis timestamp, puis now
        date_expr = "COALESCE(created_at, timestamp, 'now')"

    # Appliquer la conversion de timezone si demandé
    if use_localtime:
        return f"DATE({date_expr}, 'localtime')"
    else:
        return f"DATE({date_expr})"


def get_safe_timestamp_column(table: str) -> str:
    """
    Returns a safe SQL expression to get a timestamp value that handles NULL gracefully.
    Similar to get_safe_date_column but returns the full timestamp instead of just the date.

    Args:
        table: Table name (determines which columns to check first)

    Returns:
        SQL expression like "COALESCE(timestamp, created_at, 'now')"

    Examples:
        >>> get_safe_timestamp_column("costs")
        "COALESCE(timestamp, created_at, 'now')"
    """
    if table == "costs":
        return "COALESCE(timestamp, created_at, 'now')"
    elif table == "messages":
        return "COALESCE(created_at, timestamp, 'now')"
    elif table in ("sessions", "threads", "documents"):
        return "COALESCE(created_at, 'now')"
    else:
        return "COALESCE(created_at, timestamp, 'now')"


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
        commit=True,
    )
    logger.info(f"[DDL] Bootstrap '{table}'({pk_col}='{pk_value}') assurÃ©.")


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
        logger.info(f"[FK] agent_id='{agent_id}' non rÃ©fÃ©rencÃ© â†’ neutralisÃ© (NULL).")
        return None
    try:
        await _bootstrap_row_for_fk_table(
            db, table=tgt_table, pk_col=tgt_col, pk_value=agent_id, thread_id=""
        )
        logger.info(
            f"[FK] agent '{agent_id}' crÃ©Ã© Ã  la volÃ©e dans {tgt_table}.{tgt_col}."
        )
        return agent_id
    except Exception as e:
        logger.warning(
            f"[FK] Impossible de crÃ©er {tgt_table}({tgt_col})='{agent_id}': {e}"
        )
        return agent_id


# ------------------- CoÃ»ts (existant) ------------------- #
async def add_cost_log(
    db: DatabaseManager,
    timestamp: datetime,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    total_cost: float,
    feature: str,
    *,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    await db.execute(
        """
        INSERT INTO costs (timestamp, session_id, user_id, agent, model, input_tokens, output_tokens, total_cost, feature)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp.isoformat(),
            session_id,
            user_id,
            agent,
            model,
            input_tokens,
            output_tokens,
            total_cost,
            feature,
        ),
        commit=True,
    )


async def _build_costs_where_clause(
    db: DatabaseManager,
    user_id: Optional[str],
    session_id: Optional[str],
    *,
    allow_global: bool = False
) -> tuple[str, tuple[Any, ...]]:
    """
    Construit la clause WHERE pour la table costs.
    IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données, sauf si allow_global=True (admin only).
    Cette fonction vérifie si ces colonnes existent avant de les utiliser.

    Args:
        db: Database manager
        user_id: User ID for isolation (required unless allow_global=True)
        session_id: Optional session ID for additional filtering
        allow_global: If True, allows querying all data without user_id (ADMIN ONLY)
    """
    clauses: list[str] = []
    params: list[Any] = []

    # Vérifier si la table costs a les colonnes user_id/session_id
    has_user_id = await _table_has_column(db, "costs", "user_id")
    has_session_id = await _table_has_column(db, "costs", "session_id")

    normalized_user = _normalize_scope_identifier(user_id)
    normalized_session = _normalize_scope_identifier(session_id)

    # user_id est OBLIGATOIRE pour l'isolation des données utilisateur, sauf mode admin
    if not normalized_user and not allow_global:
        raise ValueError("user_id est obligatoire pour accéder aux données de coûts")

    # Si user_id est fourni, l'utiliser pour le filtrage
    if normalized_user:
        if has_user_id:
            clauses.append("user_id = ?")
            params.append(normalized_user)
        else:
            # Si la colonne user_id n'existe pas encore (ancienne DB), retourner une clause qui ne matche rien
            # pour éviter de montrer des données non filtrées
            logger.warning("[SECURITY] costs table missing user_id column - returning empty results for safety")
            clauses.append("1 = 0")  # Clause qui ne matche jamais

    if normalized_session and has_session_id:
        clauses.append("session_id = ?")
        params.append(normalized_session)

    # Si aucune clause, retourner une chaîne vide (pas de WHERE)
    if not clauses:
        return "", tuple()

    return " WHERE " + " AND ".join(clauses), tuple(params)


async def get_costs_summary(
    db: DatabaseManager,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    allow_global: bool = False,
) -> Dict[str, float]:
    """
    Get costs summary for a user or globally (admin only).

    Args:
        db: Database manager
        user_id: User ID to filter by (required unless allow_global=True)
        session_id: Optional session ID to filter by
        allow_global: If True, allows querying all costs without user_id (ADMIN ONLY)
    """
    where_clause, params = await _build_costs_where_clause(db, user_id, session_id, allow_global=allow_global)
    query = f"""
        SELECT
            SUM(total_cost) AS total_cost,
            SUM(CASE WHEN date(timestamp) = date('now','localtime') THEN total_cost ELSE 0 END) AS today_cost,
            SUM(CASE WHEN strftime('%Y-%W', timestamp) = strftime('%Y-%W','now','localtime') THEN total_cost ELSE 0 END) AS week_cost,
            SUM(CASE WHEN strftime('%Y-%m',  timestamp) = strftime('%Y-%m','now','localtime') THEN total_cost ELSE 0 END) AS month_cost
        FROM costs{where_clause}
    """
    row = await db.fetch_one(query, params)
    if row:
        return {
            "total": row["total_cost"] or 0.0,
            "today": row["today_cost"] or 0.0,
            "this_week": row["week_cost"] or 0.0,
            "this_month": row["month_cost"] or 0.0,
        }
    return {"total": 0.0, "today": 0.0, "this_week": 0.0, "this_month": 0.0}


async def get_messages_by_period(
    db: DatabaseManager,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, int]:
    """
    Retourne le nombre de messages par période (today, week, month, total).
    IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données.
    """
    # user_id est OBLIGATOIRE pour l'isolation des données utilisateur
    if not user_id:
        raise ValueError("user_id est obligatoire pour accéder aux statistiques de messages")

    scope_conditions = []
    params = []

    # Vérifier si la table messages a la colonne user_id
    has_user_id = await _table_has_column(db, "messages", "user_id")

    if has_user_id:
        scope_conditions.append("user_id = ?")
        params.append(user_id)
    else:
        # Si la colonne user_id n'existe pas, retourner des données vides pour la sécurité
        logger.warning("[SECURITY] messages table missing user_id column - returning empty results for safety")
        return {"total": 0, "today": 0, "week": 0, "month": 0}

    if session_id:
        has_session_id = await _table_has_column(db, "messages", "session_id")
        if has_session_id:
            scope_conditions.append("session_id = ?")
            params.append(session_id)

    where_clause = ""
    if scope_conditions:
        where_clause = " WHERE " + " AND ".join(scope_conditions)

    # Détection du schéma: utiliser created_at ou timestamp
    has_created_at = await _table_has_column(db, "messages", "created_at")
    has_timestamp = await _table_has_column(db, "messages", "timestamp")

    date_field = "created_at" if has_created_at else ("timestamp" if has_timestamp else "created_at")

    query = f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN date({date_field}) = date('now','localtime') THEN 1 ELSE 0 END) AS today,
            SUM(CASE WHEN strftime('%Y-%W', {date_field}) = strftime('%Y-%W','now','localtime') THEN 1 ELSE 0 END) AS week,
            SUM(CASE WHEN strftime('%Y-%m', {date_field}) = strftime('%Y-%m','now','localtime') THEN 1 ELSE 0 END) AS month
        FROM messages{where_clause}
    """

    row = await db.fetch_one(query, tuple(params) if params else ())
    if row:
        return {
            "total": int(row["total"] or 0),
            "today": int(row["today"] or 0),
            "week": int(row["week"] or 0),
            "month": int(row["month"] or 0),
        }
    return {"total": 0, "today": 0, "week": 0, "month": 0}


async def get_tokens_summary(
    db: DatabaseManager,
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    allow_global: bool = False,
) -> Dict[str, Any]:
    """
    Retourne un résumé des tokens utilisés (input, output, total, moyenne par message).
    Agrège depuis la table costs.

    Args:
        db: Database manager
        user_id: User ID to filter by (required unless allow_global=True)
        session_id: Optional session ID to filter by
        allow_global: If True, allows querying all tokens without user_id (ADMIN ONLY)
    """
    where_clause, params = await _build_costs_where_clause(db, user_id, session_id, allow_global=allow_global)

    query = f"""
        SELECT
            COALESCE(SUM(input_tokens), 0) AS total_input,
            COALESCE(SUM(output_tokens), 0) AS total_output,
            COUNT(*) AS request_count
        FROM costs{where_clause}
    """

    row = await db.fetch_one(query, params)

    if row:
        total_input = int(row["total_input"] or 0)
        total_output = int(row["total_output"] or 0)
        total = total_input + total_output
        request_count = int(row["request_count"] or 0)

        # Calculer moyenne par message
        avg_per_message = total / request_count if request_count > 0 else 0

        return {
            "total": total,
            "input": total_input,
            "output": total_output,
            "avgPerMessage": round(avg_per_message, 2),
        }

    return {"total": 0, "input": 0, "output": 0, "avgPerMessage": 0}


# ------------------- Documents (existant) ------------------- #
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
        commit=True,
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
) -> None:
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"UPDATE documents SET char_count = ?, chunk_count = ?, status = ? WHERE id = ? AND {scope_sql}",
        (char_count, chunk_count, status, doc_id, *scope_params),
        commit=True,
    )
async def set_document_error_status(
    db: DatabaseManager, doc_id: int, session_id: Optional[str], error_message: str, *, user_id: Optional[str] = None
) -> None:
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"UPDATE documents SET status = 'error', error_message = ? WHERE id = ? AND {scope_sql}",
        (error_message, doc_id, *scope_params),
        commit=True,
    )
async def insert_document_chunks(
    db: DatabaseManager,
    session_id: Optional[str],
    chunks: List[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
) -> None:
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
        commit=True,
    )
async def get_all_documents(
    db: DatabaseManager,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
    allow_global: bool = False,
) -> List[Dict[str, Any]]:
    """
    Get all documents for a user or globally (admin only).

    Args:
        db: Database manager
        session_id: Optional session ID to filter by
        user_id: User ID to filter by (required unless allow_global=True)
        allow_global: If True, allows querying all documents without user_id (ADMIN ONLY)
    """
    # IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données utilisateur, sauf mode admin
    if not user_id and not allow_global:
        raise ValueError("user_id est obligatoire pour accéder aux documents")

    # Si user_id est fourni, utiliser le filtrage normal
    if user_id:
        scope_sql, scope_params = _build_scope_condition(user_id, session_id)
        rows = await db.fetch_all(
            f"SELECT id, filename, status, char_count, chunk_count, error_message, uploaded_at FROM documents WHERE {scope_sql} ORDER BY uploaded_at DESC",
            scope_params,
        )
    else:
        # Mode admin: récupérer tous les documents
        rows = await db.fetch_all(
            "SELECT id, filename, status, char_count, chunk_count, error_message, uploaded_at FROM documents ORDER BY uploaded_at DESC",
            (),
        )
    return [dict(row) for row in rows]
async def get_document_by_id(
    db: DatabaseManager,
    doc_id: int,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    # IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données utilisateur
    if not user_id:
        raise ValueError("user_id est obligatoire pour accéder aux documents")

    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    row = await db.fetch_one(
        f"SELECT * FROM documents WHERE id = ? AND {scope_sql}",
        (doc_id, *scope_params),
    )
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
        commit=True,
    )
    await db.execute(
        f"DELETE FROM document_chunks WHERE document_id = ? AND {scope_sql}",
        params,
        commit=True,
    )
    await db.execute(
        f"DELETE FROM thread_docs WHERE doc_id = ? AND {scope_sql}",
        params,
        commit=True,
    )
    return True
# ------------------- Sessions (existant) ------------------- #
async def get_session_by_id(
    db: DatabaseManager, session_id: str
) -> Optional[aiosqlite.Row]:
    return await db.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))


async def get_all_sessions_overview(
    db: DatabaseManager,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    *,
    allow_global: bool = False,
) -> List[Dict[str, Any]]:
    """
    Récupère un aperçu des sessions avec comptage des messages.
    Si session_id est fourni, retourne uniquement cette session.

    Args:
        db: Database manager
        user_id: User ID to filter by (optional)
        session_id: Optional session ID to filter by
        allow_global: If True, allows querying all sessions without user_id (ADMIN ONLY)
    """
    # Construction de la requête avec LEFT JOIN pour compter les messages
    base_query = """
        SELECT
            s.id,
            s.created_at,
            s.updated_at,
            s.summary,
            COALESCE(json_array_length(s.extracted_concepts), 0) as concept_count,
            COALESCE(json_array_length(s.extracted_entities), 0) as entity_count,
            COUNT(DISTINCT m.id) as message_count
        FROM sessions s
        LEFT JOIN messages m ON (m.session_id = s.id OR m.user_id = s.user_id)
    """

    # Conditions WHERE
    conditions = []
    params = []

    if session_id:
        conditions.append("s.id = ?")
        params.append(session_id)

    if user_id:
        conditions.append("s.user_id = ?")
        params.append(user_id)
    elif not allow_global:
        # Si ni user_id ni allow_global, c'est une erreur de sécurité potentielle
        # On retourne une liste vide par sécurité
        logger.warning("[SECURITY] get_all_sessions_overview called without user_id and allow_global=False")
        return []

    where_clause = ""
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    # Groupement et tri
    query = base_query + where_clause + " GROUP BY s.id ORDER BY s.updated_at DESC"

    rows = await db.fetch_all(query, tuple(params) if params else ())
    return [dict(r) for r in rows]


async def update_session_analysis_data(
    db: DatabaseManager,
    session_id: str,
    summary: str,
    concepts: List[str],
    entities: List[str],
) -> None:
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
        commit=True,
    )
    logger.info(f"DonnÃ©es d'analyse pour la session {session_id} mises Ã  jour en BDD.")


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
    conversation_id: Optional[str] = None,  # ✅ NOUVEAU: identifiant canonique conversation
) -> str:
    thread_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    user_value = _resolve_user_scope(user_id, session_id)
    normalized_session = _normalize_scope_identifier(session_id) or user_value

    # ✅ NOUVEAU: Générer conversation_id si pas fourni (défaut = thread_id)
    if not conversation_id:
        conversation_id = thread_id

    await db.execute(
        "INSERT INTO threads (id, conversation_id, session_id, user_id, type, title, agent_id, meta, archived, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
        (
            thread_id,
            conversation_id,  # ✅ NOUVEAU
            normalized_session,
            user_value,
            type_,
            title,
            agent_id,
            json.dumps(meta) if meta is not None else None,
            now,
            now,
        ),
        commit=True,
    )
    return thread_id
async def get_threads(
    db: DatabaseManager,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
    type_: Optional[str] = None,
    include_archived: bool = False,
    archived_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    # IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données utilisateur
    if not user_id:
        raise ValueError("user_id est obligatoire pour accéder aux threads")

    clauses: list[str] = []
    params: list[Any] = []

    # Gestion du filtrage par statut d'archivage
    if archived_only:
        clauses.append("archived = 1")
    elif not include_archived:
        clauses.append("archived = 0")
    # Si include_archived=True et archived_only=False, pas de filtre (tous les threads)

    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    clauses.append(scope_sql)
    params.extend(scope_params)
    if type_:
        clauses.append("type = ?")
        params.append(type_)

    # Utiliser la vue enrichie si disponible, sinon table threads
    query = """
        SELECT
            t.*,
            COALESCE(t.last_message_at, (SELECT MAX(m.created_at) FROM messages m WHERE m.thread_id = t.id)) as last_message_at,
            COALESCE(t.message_count, (SELECT COUNT(*) FROM messages m WHERE m.thread_id = t.id)) as message_count
        FROM threads t
    """
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY COALESCE(t.last_message_at, t.updated_at) DESC LIMIT ? OFFSET ?"
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
    # IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données utilisateur
    if not user_id:
        raise ValueError("user_id est obligatoire pour accéder aux threads")

    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    row = await db.fetch_one(
        f"SELECT * FROM threads WHERE id = ? AND {scope_sql}",
        (thread_id, *scope_params),
    )
    return dict(row) if row else None
async def get_thread_any(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    # Si user_id est fourni, essayer d'abord avec filtrage
    if user_id:
        try:
            row = await get_thread(db, thread_id, session_id, user_id=user_id)
            if row:
                return row
        except ValueError:
            pass  # user_id manquant, continuer avec fallback

    # Fallback sans filtrage (pour usage interne seulement, pas pour API publique)
    fallback = await db.fetch_one("SELECT * FROM threads WHERE id = ?", (thread_id,))
    return dict(fallback) if fallback else None
async def get_threads_by_conversation(
    db: DatabaseManager,
    conversation_id: str,
    user_id: str,
    *,
    include_archived: bool = False
) -> List[Dict[str, Any]]:
    """
    ✅ NOUVEAU Sprint 1: Récupère tous threads d'une conversation.

    Une conversation peut avoir plusieurs threads (sessions différentes).
    Utile pour retrouver l'historique complet d'une discussion persistante.

    Args:
        db: DatabaseManager
        conversation_id: Identifiant canonique conversation
        user_id: Utilisateur propriétaire (sécurité)
        include_archived: Inclure threads archivés (défaut: False)

    Returns:
        Liste threads triés par date création (plus récent en premier)
    """
    clauses = ["conversation_id = ?", "user_id = ?"]
    params = [conversation_id, user_id]

    if not include_archived:
        clauses.append("archived = 0")

    query = f"""
        SELECT
            t.*,
            COALESCE(t.last_message_at, (SELECT MAX(m.created_at) FROM messages m WHERE m.thread_id = t.id)) as last_message_at,
            COALESCE(t.message_count, (SELECT COUNT(*) FROM messages m WHERE m.thread_id = t.id)) as message_count
        FROM threads t
        WHERE {' AND '.join(clauses)}
        ORDER BY t.created_at DESC
    """
    rows = await db.fetch_all(query, tuple(params))
    return [dict(r) for r in rows]


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
    gardener: Any = None,  # ✅ NOUVEAU Sprint 2: injection MemoryGardener pour consolidation auto
) -> None:
    """
    Met à jour un thread existant.

    ✅ NOUVEAU Sprint 2: Si archived=True et gardener fourni,
    déclenche automatiquement la consolidation LTM du thread.
    """
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

        # ✅ NOUVEAU Sprint 2: Si archivage, ajouter timestamp + raison
        if archived:
            fields.append("archived_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())

            # Raison par défaut si pas dans meta
            archival_reason = (meta or {}).get('archival_reason', 'manual_archive')
            fields.append("archival_reason = ?")
            params.append(archival_reason)

    fields.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    params.extend([thread_id, *scope_params])
    await db.execute(
        f"UPDATE threads SET {', '.join(fields)} WHERE id = ? AND {scope_sql}",
        tuple(params),
        commit=True,
    )

    # ✅ NOUVEAU Sprint 2: Déclencher consolidation si archivage
    if archived and gardener:
        try:
            logger.info(f"Thread {thread_id} archivé, déclenchement consolidation LTM...")

            # Récupérer user_id si pas fourni
            if not user_id:
                thread = await get_thread_any(db, thread_id, session_id=session_id, user_id=None)
                user_id = thread.get('user_id') if thread else None

            if user_id:
                await gardener._tend_single_thread(
                    thread_id=thread_id,
                    session_id=session_id,
                    user_id=user_id
                )

                # Marquer comme consolidé
                await db.execute(
                    "UPDATE threads SET consolidated_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), thread_id),
                    commit=True
                )
                logger.info(f"Thread {thread_id} consolidé en LTM avec succès")
            else:
                logger.warning(f"Impossible de consolider thread {thread_id}: user_id introuvable")
        except Exception as e:
            logger.error(f"Échec consolidation thread {thread_id}: {e}", exc_info=True)
            # Ne pas bloquer l'archivage si consolidation échoue
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
        commit=True,
    )
    await db.execute(
        f"DELETE FROM messages WHERE thread_id = ? AND {scope_sql}",
        (thread_id, *scope_params),
        commit=True,
    )
    await db.execute(
        f"DELETE FROM threads WHERE id = ? AND {scope_sql}",
        (thread_id, *scope_params),
        commit=True,
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
    message_id: Optional[str] = None,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(meta) if meta is not None else None

    custom_message_id = None
    if message_id is not None:
        try:
            candidate = str(message_id).strip()
        except Exception:
            candidate = None
        if candidate:
            if len(candidate) > 256:
                candidate = candidate[:256]
            custom_message_id = candidate

    id_is_int = await _messages_id_is_integer(db)
    need_session = await _messages_requires_session_id(db)
    need_timestamp = await _messages_requires_timestamp(db)
    has_user_column = await _table_has_column(db, "messages", "user_id")
    safe_agent_id = await _maybe_neutralize_agent_id(db, agent_id)
    normalized_session = _normalize_scope_identifier(session_id)
    session_value = normalized_session or _resolve_user_scope(user_id, session_id)
    user_value = _resolve_user_scope(user_id, session_id)

    def _cols_vals(base_cols: List[str], base_vals: List[Any]) -> tuple[List[str], List[Any]]:
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

    persisted_id = None
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
            commit=True,
        )
        row = await db.fetch_one("SELECT last_insert_rowid() AS id")
        persisted_id = str(row["id"]) if row and "id" in row.keys() else None
    else:
        assigned_id = custom_message_id or uuid.uuid4().hex
        base_cols = ["id", "thread_id", "role", "content", "tokens", "meta"]
        base_vals = [assigned_id, thread_id, role, content, tokens, meta_json]
        if include_agent:
            base_cols.insert(3, "agent_id")
            base_vals.insert(3, safe_agent_id)
        cols, vals = _cols_vals(base_cols, base_vals)
        placeholders = ", ".join(["?"] * len(cols))
        await db.execute(
            f"INSERT INTO messages ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
            commit=True,
        )
        persisted_id = assigned_id

    scope_sql, scope_params = _build_scope_condition(user_id, session_id)
    await db.execute(
        f"""
        UPDATE threads
        SET updated_at = ?, last_message_at = ?, message_count = COALESCE(message_count, 0) + 1
        WHERE id = ? AND {scope_sql}
        """,
        (now, now, thread_id, *scope_params),
        commit=True,
    )
    return {"id": persisted_id, "created_at": now}
async def get_messages(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
    limit: int = 50,
    before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données utilisateur
    if not user_id:
        raise ValueError("user_id est obligatoire pour accéder aux messages")

    clauses = ["thread_id = ?"]
    params: list[Any] = [thread_id]
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
        commit=True,
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
            commit=True,
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
            commit=True,
        )
async def get_thread_docs(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # IMPORTANT: user_id est OBLIGATOIRE pour l'isolation des données utilisateur
    if not user_id:
        raise ValueError("user_id est obligatoire pour accéder aux thread_docs")

    clauses = ["td.thread_id = ?"]
    params: list[Any] = [thread_id]
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
