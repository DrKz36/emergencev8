# src/backend/features/threads/router.py
# V1.5 — Retrait du prefix interne (montage géré par main.py) + alias GET/POST sans slash conservés
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries
from backend.shared.dependencies import get_user_id  # lit "X-User-Id"

router = APIRouter(tags=["Threads"])  # ← plus de prefix ici (monté par main.py)

def get_db(request: Request) -> DatabaseManager:
    return request.app.state.service_container.db_manager()

# ---------- Schemas ----------
class ThreadCreate(BaseModel):
    type: str = Field(pattern="^(chat|debate)$")
    title: Optional[str] = None
    agent_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    agent_id: Optional[str] = None
    archived: Optional[bool] = None
    meta: Optional[Dict[str, Any]] = None

class MessageCreate(BaseModel):
    role: str = Field(pattern="^(user|assistant|system|note)$")
    content: str
    agent_id: Optional[str] = None
    tokens: Optional[int] = None
    meta: Optional[Dict[str, Any]] = None

class DocsSet(BaseModel):
    doc_ids: List[int]
    mode: str = Field(default="replace", pattern="^(replace|append)$")
    weight: Optional[float] = 1.0

# ---------- Routes ----------
@router.get("/")
async def list_threads(
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
    type: Optional[str] = Query(default=None, pattern="^(chat|debate)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items = await queries.get_threads(db, user_id=user_id, type_=type, limit=limit, offset=offset)
    return {"items": items}

# Miroir sans slash (évite 404/405 par oubli du '/')
@router.get("", include_in_schema=False)
async def list_threads_no_slash(
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
    type: Optional[str] = Query(default=None, pattern="^(chat|debate)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items = await queries.get_threads(db, user_id=user_id, type_=type, limit=limit, offset=offset)
    return {"items": items}

@router.post("/", status_code=201)
async def create_thread(
    payload: ThreadCreate,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
):
    tid = await queries.create_thread(
        db, user_id=user_id, type_=payload.type, title=payload.title,
        agent_id=payload.agent_id, meta=payload.meta
    )
    thread = await queries.get_thread(db, tid, user_id)
    return {"id": tid, "thread": thread}

# Miroir POST sans slash (corrige 405 quand le client poste sur /api/threads)
@router.post("", status_code=201, include_in_schema=False)
async def create_thread_no_slash(
    payload: ThreadCreate,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
):
    tid = await queries.create_thread(
        db, user_id=user_id, type_=payload.type, title=payload.title,
        agent_id=payload.agent_id, meta=payload.meta
    )
    thread = await queries.get_thread(db, tid, user_id)
    return {"id": tid, "thread": thread}

# ---- DEBUG caché ----
@router.get("/_debug/{thread_id}", include_in_schema=False)
async def _debug_get_raw(thread_id: str, db: DatabaseManager = Depends(get_db)):
    row = await queries.get_thread_any(db, thread_id)
    return {"raw": row}

@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
    messages_limit: int = Query(default=50, ge=1, le=200),
):
    thread = await queries.get_thread(db, thread_id, user_id)
    if not thread:
        alt = await queries.get_thread_any(db, thread_id)
        if not alt:
            raise HTTPException(status_code=404, detail="Thread introuvable")
        t_uid = (alt.get("user_id") or "").strip().lower()
        u_uid = (user_id or "").strip().lower()
        if t_uid and t_uid != u_uid:
            raise HTTPException(status_code=403, detail="Thread non accessible pour cet utilisateur")
        thread = alt

    messages = await queries.get_messages(db, thread_id, limit=messages_limit)
    docs = await queries.get_thread_docs(db, thread_id)
    return {"thread": thread, "messages": messages, "docs": docs}

@router.patch("/{thread_id}")
async def update_thread(
    thread_id: str,
    payload: ThreadUpdate,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
):
    if not await queries.get_thread(db, thread_id, user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")
    await queries.update_thread(
        db, thread_id, user_id,
        title=payload.title, agent_id=payload.agent_id,
        archived=payload.archived, meta=payload.meta
    )
    thread = await queries.get_thread(db, thread_id, user_id)
    return {"thread": thread}

@router.post("/{thread_id}/messages", status_code=201)
async def add_message(
    thread_id: str,
    payload: MessageCreate,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
):
    if not await queries.get_thread(db, thread_id, user_id):
        alt = await queries.get_thread_any(db, thread_id)
        if not alt:
            raise HTTPException(status_code=404, detail="Thread introuvable")
        t_uid = (alt.get("user_id") or "").strip().lower()
        u_uid = (user_id or "").strip().lower()
        if t_uid and t_uid != u_uid:
            raise HTTPException(status_code=403, detail="Thread non accessible pour cet utilisateur")

    res = await queries.add_message(
        db, thread_id, role=payload.role, content=payload.content,
        agent_id=payload.agent_id, tokens=payload.tokens, meta=payload.meta or {}
    )
    return {"message_id": res["id"], "created_at": res["created_at"]}

@router.get("/{thread_id}/messages")
async def list_messages(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    before: Optional[str] = Query(default=None),
):
    if not await queries.get_thread(db, thread_id, user_id):
        alt = await queries.get_thread_any(db, thread_id)
        if not alt:
            raise HTTPException(status_code=404, detail="Thread introuvable")
        t_uid = (alt.get("user_id") or "").strip().lower()
        u_uid = (user_id or "").strip().lower()
        if t_uid and t_uid != u_uid:
            raise HTTPException(status_code=403, detail="Thread non accessible pour cet utilisateur")
    items = await queries.get_messages(db, thread_id, limit=limit, before=before)
    return {"items": items}

@router.post("/{thread_id}/docs")
async def set_docs(
    thread_id: str,
    payload: DocsSet,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
):
    if not await queries.get_thread(db, thread_id, user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")
    if payload.mode == "replace":
        await queries.set_thread_docs(db, thread_id, payload.doc_ids, weight=payload.weight or 1.0)
    else:
        await queries.append_thread_docs(db, thread_id, payload.doc_ids, weight=payload.weight or 1.0)
    docs = await queries.get_thread_docs(db, thread_id)
    return {"docs": docs}

@router.get("/{thread_id}/docs")
async def get_docs(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
):
    if not await queries.get_thread(db, thread_id, user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")
    docs = await queries.get_thread_docs(db, thread_id)
    return {"docs": docs}

@router.post("/{thread_id}/export")
async def export_thread(
    thread_id: str,
    user_id: str = Depends(get_user_id),
    db: DatabaseManager = Depends(get_db),
):
    thread = await queries.get_thread(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread introuvable")
    messages = await queries.get_messages(db, thread_id, limit=1000)
    docs = await queries.get_thread_docs(db, thread_id)
    return {"thread": thread, "messages": messages, "docs": docs}
