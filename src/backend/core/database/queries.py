# src/backend/core/database/queries.py
# V6.0 - Mémoire persistante : sessions.is_consolidated + knowledge_concepts + helpers MemoryGardener.
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import aiosqlite
from .manager import DatabaseManager

logger = logging.getLogger(__name__)

# ------------------------------
# Cost Queries
# ------------------------------
async def add_cost_log(db: DatabaseManager, timestamp: datetime, agent: str, model: str, input_tokens: int, output_tokens: int, total_cost: float, feature: str):
    query = "INSERT INTO costs (timestamp, agent, model, input_tokens, output_tokens, total_cost, feature) VALUES (?, ?, ?, ?, ?, ?, ?)"
    params = (timestamp.isoformat(), agent, model, input_tokens, output_tokens, total_cost, feature)
    await db.execute(query, params)

async def get_costs_summary(db: DatabaseManager) -> Dict[str, float]:
    query = """
    SELECT
        SUM(total_cost) AS total_cost,
        SUM(CASE WHEN date(timestamp) = date('now', 'localtime') THEN total_cost ELSE 0 END) AS today_cost,
        SUM(CASE WHEN strftime('%Y-%W', timestamp) = strftime('%Y-%W', 'now', 'localtime') THEN total_cost ELSE 0 END) AS week_cost,
        SUM(CASE WHEN strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now', 'localtime') THEN total_cost ELSE 0 END) AS month_cost
    FROM costs
    """
    row = await db.fetch_one(query)
    if row:
        return {
            "total": row["total_cost"] or 0.0,
            "today": row["today_cost"] or 0.0,
            "this_week": row["week_cost"] or 0.0,
            "this_month": row["month_cost"] or 0.0,
        }
    return {"total": 0.0, "today": 0.0, "this_week": 0.0, "this_month": 0.0}

# ------------------------------
# Document Queries
# ------------------------------
async def insert_document(db: DatabaseManager, filename: str, filepath: str, status: str, uploaded_at: str) -> int:
    query = "INSERT INTO documents (filename, filepath, status, uploaded_at) VALUES (?, ?, ?, ?)"
    params = (filename, filepath, status, uploaded_at)
    await db.execute(query, params)
    res = await db.fetch_one("SELECT last_insert_rowid() as id")
    return res['id']

async def update_document_processing_info(db: DatabaseManager, doc_id: int, char_count: int, chunk_count: int, status: str):
    query = "UPDATE documents SET char_count = ?, chunk_count = ?, status = ? WHERE id = ?"
    await db.execute(query, (char_count, chunk_count, status, doc_id))

async def set_document_error_status(db: DatabaseManager, doc_id: int, error_message: str):
    query = "UPDATE documents SET status = 'error', error_message = ? WHERE id = ?"
    await db.execute(query, (error_message, doc_id))

async def insert_document_chunks(db: DatabaseManager, chunks: List[Dict[str, Any]]):
    query = "INSERT INTO document_chunks (id, document_id, chunk_index, content) VALUES (?, ?, ?, ?)"
    params = [(c['id'], c['document_id'], c['chunk_index'], c['content']) for c in chunks]
    await db.executemany(query, params)

async def get_all_documents(db: DatabaseManager) -> List[Dict[str, Any]]:
    query = "SELECT id, filename, status, char_count, chunk_count, error_message, uploaded_at FROM documents ORDER BY uploaded_at DESC"
    rows = await db.fetch_all(query)
    return [dict(row) for row in rows]

async def get_document_by_id(db: DatabaseManager, doc_id: int) -> Optional[Dict[str, Any]]:
    query = "SELECT * FROM documents WHERE id = ?"
    row = await db.fetch_one(query, (doc_id,))
    return dict(row) if row else None

async def delete_document(db: DatabaseManager, doc_id: int):
    query = "DELETE FROM documents WHERE id = ?"
    await db.execute(query, (doc_id,))

# ------------------------------
# Session Queries (mémoire brut)
# ------------------------------
async def save_session(*args, **kwargs):
    logger.warning("DEPRECATION WARNING: queries.save_session est obsolète. Utiliser SessionManager (DatabaseManager.save_session).")
    pass

async def get_session_by_id(db: DatabaseManager, session_id: str) -> Optional[aiosqlite.Row]:
    query = "SELECT * FROM sessions WHERE id = ?"
    row = await db.fetch_one(query, (session_id,))
    return row

async def get_all_sessions_overview(db: DatabaseManager) -> List[Dict[str, Any]]:
    query = """
    SELECT id, created_at, updated_at, summary, 
           json_array_length(extracted_concepts) as concept_count, 
           json_array_length(extracted_entities) as entity_count,
           is_consolidated
    FROM sessions ORDER BY updated_at DESC
    """
    rows = await db.fetch_all(query)
    return [dict(row) for row in rows]

async def update_session_analysis_data(db: DatabaseManager, session_id: str, summary: str, concepts: List[str], entities: List[str]):
    """Met à jour une session existante avec les données d'analyse."""
    query = """
    UPDATE sessions
    SET
        summary = ?,
        extracted_concepts = ?,
        extracted_entities = ?,
        updated_at = ?
    WHERE id = ?
    """
    params = (
        summary,
        json.dumps(concepts),
        json.dumps(entities),
        datetime.now(timezone.utc).isoformat(),
        session_id
    )
    await db.execute(query, params)
    logger.info(f"Données d'analyse pour la session {session_id} mises à jour en BDD.")

async def get_unconsolidated_sessions(db: DatabaseManager, limit: int = 10) -> List[Dict[str, Any]]:
    """Retourne des sessions à consolider (pas encore consolidées)."""
    query = """
    SELECT id, session_data, summary, extracted_concepts, extracted_entities, created_at, updated_at
    FROM sessions
    WHERE IFNULL(is_consolidated, 0) = 0
    ORDER BY updated_at DESC
    LIMIT ?
    """
    rows = await db.fetch_all(query, (limit,))
    result: List[Dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        # Assurer des valeurs par défaut
        item.setdefault('summary', None)
        item.setdefault('extracted_concepts', None)
        item.setdefault('extracted_entities', None)
        result.append(item)
    return result

async def mark_sessions_as_consolidated(db: DatabaseManager, session_ids: List[str]):
    if not session_ids:
        return
    # Construction d'un IN (?, ?, ...)
    placeholders = ",".join(["?"] * len(session_ids))
    query = f"UPDATE sessions SET is_consolidated = 1 WHERE id IN ({placeholders})"
    await db.execute(query, tuple(session_ids))

# ------------------------------
# Knowledge base (concepts consolidés)
# ------------------------------
async def upsert_knowledge_concept(db: DatabaseManager, concept: Dict[str, Any]):
    """Enregistre/Met à jour un concept consolidé.
    Fields attendus : id, concept, description, categories(list|json), vector_id
    """
    # Normalisation
    cid = concept.get('id')
    cname = concept.get('concept')
    desc = concept.get('description')
    cats = concept.get('categories') or []  # list or json
    vid  = concept.get('vector_id')

    cats_json = json.dumps(cats) if not isinstance(cats, str) else cats
    created_at = datetime.now(timezone.utc).isoformat()

    query = """
    INSERT INTO knowledge_concepts (id, concept, description, categories, vector_id, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        concept = excluded.concept,
        description = excluded.description,
        categories = excluded.categories,
        vector_id = excluded.vector_id
    """
    await db.execute(query, (cid, cname, desc, cats_json, vid, created_at))
