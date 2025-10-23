# src/backend/features/threads/router.py
# V1.6 — Hook consolidation automatique lors archivage (Phase P0)
from typing import Any, List, Optional, cast
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries
from backend.shared.dependencies import get_session_context, SessionContext

router = APIRouter(tags=["Threads"])  # ← plus de prefix ici (monté par main.py)
logger = logging.getLogger(__name__)

def get_db(request: Request) -> DatabaseManager:
    return cast(DatabaseManager, request.app.state.service_container.db_manager())

# ---------- Schemas ----------
class ThreadCreate(BaseModel):
    type: str = Field(pattern="^(chat|debate)$")
    title: Optional[str] = None
    agent_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None

class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    agent_id: Optional[str] = None
    archived: Optional[bool] = None
    meta: Optional[dict[str, Any]] = None

class MessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant|system|note)$")
    content: str
    agent_id: Optional[str] = None
    tokens: Optional[int] = None
    meta: Optional[dict[str, Any]] = None

class DocsSet(BaseModel):
    doc_ids: List[int]
    mode: str = Field(default="replace", pattern="^(replace|append)$")
    weight: Optional[float] = 1.0

# ---------- Routes ----------
@router.get("/")
async def list_threads(
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
    type: Optional[str] = Query(default=None, pattern="^(chat|debate)$"),
    include_archived: bool = Query(default=False, description="Inclure les conversations archivées"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = await queries.get_threads(
        db,
        session_id=session.session_id,
        user_id=session.user_id,
        type_=type,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return {"items": items}

# Miroir sans slash (évite 404/405 par oubli du '/')
@router.get("", include_in_schema=False)
async def list_threads_no_slash(
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
    type: Optional[str] = Query(default=None, pattern="^(chat|debate)$"),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = await queries.get_threads(
        db,
        session_id=session.session_id,
        user_id=session.user_id,
        type_=type,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return {"items": items}

@router.post("/", status_code=201)
async def create_thread(
    payload: ThreadCreate,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    tid = await queries.create_thread(
        db,
        session_id=session.session_id,
        user_id=session.user_id,
        type_=payload.type,
        title=payload.title,
        agent_id=payload.agent_id,
        meta=payload.meta,
    )
    thread = await queries.get_thread(db, tid, session.session_id, user_id=session.user_id)
    return {"id": tid, "thread": thread}

# Miroir POST sans slash (corrige 405 quand le client poste sur /api/threads)
@router.post("", status_code=201, include_in_schema=False)
async def create_thread_no_slash(
    payload: ThreadCreate,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    tid = await queries.create_thread(
        db,
        session_id=session.session_id,
        user_id=session.user_id,
        type_=payload.type,
        title=payload.title,
        agent_id=payload.agent_id,
        meta=payload.meta,
    )
    thread = await queries.get_thread(db, tid, session.session_id, user_id=session.user_id)
    return {"id": tid, "thread": thread}

# ---- Routes archives ----
@router.get("/archived/list")
async def list_archived_threads(
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
    type: Optional[str] = Query(default=None, pattern="^(chat|debate)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Liste uniquement les conversations archivées."""
    items = await queries.get_threads(
        db,
        session_id=session.session_id,
        user_id=session.user_id,
        type_=type,
        archived_only=True,
        limit=limit,
        offset=offset,
    )
    return {"items": items}

# ---- DEBUG caché ----
@router.get("/_debug/{thread_id}", include_in_schema=False)
async def _debug_get_raw(thread_id: str, db: DatabaseManager = Depends(get_db)) -> dict[str, Any]:
    row = await queries.get_thread_any(db, thread_id)
    return {"raw": row}

@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
    messages_limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    thread = await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread introuvable")

    messages = await queries.get_messages(
        db, thread_id, session_id=session.session_id, user_id=session.user_id, limit=messages_limit
    )
    docs = await queries.get_thread_docs(db, thread_id, session.session_id, user_id=session.user_id)
    return {"thread": thread, "messages": messages, "docs": docs}

@router.patch("/{thread_id}")
async def update_thread(
    thread_id: str,
    payload: ThreadUpdate,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    thread_before = await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id)
    if not thread_before:
        raise HTTPException(status_code=404, detail="Thread introuvable")

    # Récupérer état archivage AVANT mise à jour
    was_archived = thread_before.get("archived", False)

    # Appliquer mise à jour
    await queries.update_thread(
        db,
        thread_id,
        session.session_id,
        user_id=session.user_id,
        title=payload.title,
        agent_id=payload.agent_id,
        archived=payload.archived,
        meta=payload.meta,
    )

    # 🆕 NOUVEAU (Phase P0): Hook consolidation automatique lors archivage
    if payload.archived and not was_archived:
        try:
            from backend.features.memory.task_queue import get_memory_queue

            queue = get_memory_queue()
            await queue.enqueue(
                task_type="consolidate_thread",
                payload={
                    "thread_id": thread_id,
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "reason": "archiving"
                }
            )

            logger.info(f"[Thread Archiving] Consolidation enqueued for thread {thread_id}")

        except Exception as e:
            # Ne pas bloquer l'archivage si consolidation échoue
            logger.warning(f"[Thread Archiving] Failed to enqueue consolidation: {e}")

    thread = await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id)
    return {"thread": thread}

@router.delete("/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: str,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> Response:
    removed = await queries.delete_thread(db, thread_id, session.session_id, user_id=session.user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Thread introuvable")
    return Response(status_code=204)


@router.post("/{thread_id}/messages", status_code=201)
async def add_message(
    thread_id: str,
    payload: MessageCreate,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    if not await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")

    res = await queries.add_message(
        db,
        thread_id,
        session.session_id,
        user_id=session.user_id,
        role=payload.role,
        content=payload.content,
        agent_id=payload.agent_id,
        tokens=payload.tokens,
        meta=payload.meta or {},
    )
    return {"message_id": res["id"], "created_at": res["created_at"]}

@router.get("/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    before: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    if not await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")
    items = await queries.get_messages(
        db, thread_id, session_id=session.session_id, user_id=session.user_id, limit=limit, before=before
    )
    return {"items": items}

@router.post("/{thread_id}/docs")
async def set_docs(
    thread_id: str,
    payload: DocsSet,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    if not await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")
    if payload.mode == "replace":
        await queries.set_thread_docs(
            db,
            thread_id,
            session.session_id,
            payload.doc_ids,
            user_id=session.user_id,
            weight=payload.weight or 1.0,
        )
    else:
        await queries.append_thread_docs(
            db,
            thread_id,
            session.session_id,
            payload.doc_ids,
            user_id=session.user_id,
            weight=payload.weight or 1.0,
        )
    docs = await queries.get_thread_docs(db, thread_id, session.session_id, user_id=session.user_id)
    return {"docs": docs}

@router.get("/{thread_id}/docs")
async def get_docs(
    thread_id: str,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    if not await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")
    docs = await queries.get_thread_docs(db, thread_id, session.session_id, user_id=session.user_id)
    return {"docs": docs}

@router.post("/{thread_id}/export")
async def export_thread(
    thread_id: str,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
) -> dict[str, Any]:
    thread = await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread introuvable")
    messages = await queries.get_messages(
        db, thread_id, session_id=session.session_id, user_id=session.user_id, limit=1000
    )
    docs = await queries.get_thread_docs(db, thread_id, session.session_id, user_id=session.user_id)
    return {"thread": thread, "messages": messages, "docs": docs}
