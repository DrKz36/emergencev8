# src/backend/features/threads/router.py
# V1.8 – Router Threads (fallback DB)
# - Surface API inchangée (liste / création / détail).
# - get_db() tente d’abord le ServiceContainer, puis **fallback** autonome via Settings().db.filepath.
# - Scoping strict par user (Google ID token) via backend.shared.dependencies.get_user_id.

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import json
import logging

from fastapi import (
    APIRouter, Depends, HTTPException, Query, Request, Path, status
)
from pydantic import BaseModel, Field

# Auth (Bearer → sub + allowlist/audience)
from backend.shared import dependencies as deps  # get_user_id (REST)                          #  
# Settings (chemins DB si fallback)
from backend.shared.config import Settings                                                    #  
# DB aiosqlite (WAL, FK ON)
from backend.core.database.manager import DatabaseManager                                     #  

logger = logging.getLogger("threads.router")
router = APIRouter()

# ----------------------- Pydantic models -----------------------

class ThreadCreate(BaseModel):
    type: str = Field(..., description="chat|debate")
    title: Optional[str] = None
    agent_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class ThreadOut(BaseModel):
    id: str
    type: str
    title: Optional[str] = None
    agent_id: Optional[str] = None
    archived: int = 0
    created_at: str
    updated_at: str

class ThreadDetail(ThreadOut):
    """Extension future (messages/docs)."""
    pass

# ----------------------- DI helpers -----------------------

async def get_db(request: Request) -> DatabaseManager:
    """
    1) Essaie d'obtenir le DatabaseManager depuis le container d'app.
    2) Si indisponible (tests/hors app), **fallback** autonome via Settings().db.filepath.
    """
    # 1) Container
    try:
        container = getattr(request.app.state, "service_container", None)  # type: ignore[attr-defined]
        if container and hasattr(container, "db_manager"):
            dbm = container.db_manager()
            if isinstance(dbm, DatabaseManager):
                return dbm
    except Exception as e:
        logger.warning(f"Container DB indisponible, tentative fallback. Détail: {e}")

    # 2) Fallback autonome
    settings = Settings()  # chemins projet (db.filepath, etc.)                                  #  
    dbm = DatabaseManager(settings.db.filepath)                                                   #  
    await dbm.connect()
    return dbm

# ----------------------- SQL primitives -----------------------

async def _list_threads(db: DatabaseManager, user_id: str,
                        type_: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
    params: List[Any] = [user_id]
    where = "WHERE user_id = ?"
    if type_:
        where += " AND type = ?"
        params.append(type_)
    sql = f"""
        SELECT id, type, title, agent_id, archived, created_at, updated_at
        FROM threads
        {where}
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([int(limit), int(offset)])
    rows = await db.fetch_all(sql, tuple(params))
    return [dict(r) for r in (rows or [])]

async def _create_thread(db: DatabaseManager, user_id: str, payload: ThreadCreate) -> Dict[str, Any]:
    # Contrôle type (conforme CHECK schéma: chat|debate)                                         #  
    t = (payload.type or "").strip().lower()
    if t not in {"chat", "debate"}:
        raise HTTPException(status_code=422, detail="type must be 'chat' or 'debate'")

    thread_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(payload.meta) if payload.meta is not None else None

    try:
        await db.execute(
            """
            INSERT INTO threads (id, user_id, type, title, agent_id, meta, archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (thread_id, user_id, t, payload.title, payload.agent_id, meta_json, now, now),
        )
    except Exception as e:
        logger.error(f"INSERT threads failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="DB insert failed for thread")

    row = await db.fetch_one(
        "SELECT id, type, title, agent_id, archived, created_at, updated_at FROM threads WHERE id = ?",
        (thread_id,),
    )
    if not row:
        raise HTTPException(status_code=500, detail="Thread not found after insert")
    return dict(row)

async def _get_thread(db: DatabaseManager, user_id: str, thread_id: str) -> Dict[str, Any]:
    row = await db.fetch_one(
        """
        SELECT id, type, title, agent_id, archived, created_at, updated_at
        FROM threads
        WHERE id = ? AND user_id = ?
        """,
        (thread_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")
    return dict(row)

# ----------------------- Routes -----------------------

@router.get("", response_model=List[ThreadOut], summary="Liste mes threads")
async def list_threads(
    request: Request,
    user_id: str = Depends(deps.get_user_id),  # Bearer → sub (allowlist/audience)              #  
    type: Optional[str] = Query(default=None, pattern="^(chat|debate)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: DatabaseManager = Depends(get_db),
):
    try:
        return await _list_threads(db, user_id=user_id, type_=type, limit=limit, offset=offset)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /api/threads failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error while listing threads")

@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED, summary="Créer un thread")
async def create_thread(
    payload: ThreadCreate,
    user_id: str = Depends(deps.get_user_id),                                                   #  
    db: DatabaseManager = Depends(get_db),
):
    try:
        return await _create_thread(db, user_id=user_id, payload=payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"POST /api/threads failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error while creating thread")

@router.get("/{thread_id}", response_model=ThreadDetail, summary="Détail d’un thread")
async def get_thread(
    thread_id: str = Path(..., min_length=8),
    user_id: str = Depends(deps.get_user_id),                                                   #  
    db: DatabaseManager = Depends(get_db),
):
    try:
        return await _get_thread(db, user_id=user_id, thread_id=thread_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GET /api/threads/{thread_id} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error while fetching thread")
