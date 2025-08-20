# src/backend/features/threads/schemas.py
# UTF-8 (CRLF recommandé) — Schémas Pydantic v2 pour Threads/Messages.

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# ---------- Threads ----------
class ThreadCreate(BaseModel):
    title: Optional[str] = Field(default=None)
    doc_ids: List[str] = Field(default_factory=list)

class ThreadPatch(BaseModel):
    title: Optional[str] = None
    archived: Optional[bool] = None

class ThreadSummary(BaseModel):
    id: str
    title: Optional[str] = None
    archived: bool = False
    doc_ids: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    last_message_at: Optional[str] = None
    message_count: int = 0

class ThreadDetail(ThreadSummary):
    # Placeholder si on veut renvoyer des infos supplémentaires (meta, etc.)
    pass

# ---------- Messages ----------
class MessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    agent: Optional[str] = None
    model: Optional[str] = None
    rag_sources: Optional[List[Dict[str, Any]]] = None

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    agent: Optional[str] = None
    model: Optional[str] = None
    ts: str
    rag_sources: Optional[List[Dict[str, Any]]] = None
