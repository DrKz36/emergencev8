# src/backend/features/threads/service.py
# UTF-8 (CRLF recommandé) — Service Firestore async (Option A).

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from google.cloud.firestore_v1 import AsyncClient, Query
from google.cloud import firestore_v1 as firestore

from .schemas import ThreadCreate, ThreadPatch, ThreadSummary, ThreadDetail, MessageCreate, MessageOut

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt.astimezone(timezone.utc).isoformat()
    try:
        # Firestore Timestamp -> to_datetime()
        return dt.to_datetime().astimezone(timezone.utc).isoformat()  # type: ignore[attr-defined]
    except Exception:
        return str(dt)

def _session_thread_id(session_id: str) -> str:
    # Id court, déterministe et Firestore-safe
    base = re.sub(r"[^a-zA-Z0-9]", "", (session_id or "s")) or "s"
    return ("s_" + base)[:12]

class ThreadsService:
    """
    Service de persistance basé sur Firestore (AsyncClient).
    Modèle: users/{user_id}/threads/{thread_id} + messages/{message_id}
    """
    _client: Optional[AsyncClient] = None

    @classmethod
    def client(cls) -> AsyncClient:
        if cls._client is None:
            # Projet auto-détecté via ADC (Cloud Run) ou GOOGLE_CLOUD_PROJECT
            cls._client = AsyncClient(project=os.getenv("GOOGLE_CLOUD_PROJECT") or None)
        return cls._client  # type: ignore[return-value]

    # ----- Helpers chemin -----
    @classmethod
    def _threads_col(cls, user_id: str):
        return cls.client().collection("users").document(user_id).collection("threads")

    @classmethod
    def _thread_doc(cls, user_id: str, thread_id: str):
        return cls._threads_col(user_id).document(thread_id)

    @classmethod
    def _messages_col(cls, user_id: str, thread_id: str):
        return cls._thread_doc(user_id, thread_id).collection("messages")

    # ----- Threads -----
    async def list_threads(self, user_id: str, archived: bool = False, limit: int = 50) -> List[ThreadSummary]:
        q: Query = (
            self._threads_col(user_id)
            .where("archived", "==", bool(archived))
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(max(1, min(limit, 200)))
        )
        items: List[ThreadSummary] = []
        async for snap in q.stream():
            data = snap.to_dict() or {}
            items.append(ThreadSummary(
                id=snap.id,
                title=data.get("title"),
                archived=bool(data.get("archived", False)),
                doc_ids=list(data.get("doc_ids", [])),
                created_at=_iso(data.get("created_at")) or _iso(_utcnow()),
                updated_at=_iso(data.get("updated_at")) or _iso(_utcnow()),
                last_message_at=_iso(data.get("last_message_at")),
                message_count=int(data.get("message_count", 0)),
            ))
        return items

    async def create_thread(self, user_id: str, payload: ThreadCreate) -> ThreadDetail:
        thread_id = uuid4().hex[:12]
        now = _utcnow()
        doc_ref = self._thread_doc(user_id, thread_id)
        await doc_ref.set({
            "title": payload.title,
            "archived": False,
            "doc_ids": payload.doc_ids or [],
            "created_at": now,
            "updated_at": now,
            "last_message_at": None,
            "message_count": 0,
        })
        return ThreadDetail(
            id=thread_id,
            title=payload.title,
            archived=False,
            doc_ids=payload.doc_ids or [],
            created_at=_iso(now),
            updated_at=_iso(now),
            last_message_at=None,
            message_count=0,
        )

    async def patch_thread(self, user_id: str, thread_id: str, changes: ThreadPatch) -> ThreadDetail:
        doc_ref = self._thread_doc(user_id, thread_id)
        snap = await doc_ref.get()
        if not snap.exists:
            raise KeyError("thread_not_found")
        data = snap.to_dict() or {}
        upd: Dict[str, Any] = {"updated_at": _utcnow()}
        if changes.title is not None:
            upd["title"] = changes.title
        if changes.archived is not None:
            upd["archived"] = bool(changes.archived)
        await doc_ref.update(upd)
        # reload
        snap = await doc_ref.get()
        d2 = snap.to_dict() or {}
        return ThreadDetail(
            id=snap.id,
            title=d2.get("title"),
            archived=bool(d2.get("archived", False)),
            doc_ids=list(d2.get("doc_ids", [])),
            created_at=_iso(d2.get("created_at")),
            updated_at=_iso(d2.get("updated_at")),
            last_message_at=_iso(d2.get("last_message_at")),
            message_count=int(d2.get("message_count", 0)),
        )

    # ----- Messages -----
    async def list_messages(self, user_id: str, thread_id: str, limit: int = 100, after_ts: Optional[str] = None) -> List[MessageOut]:
        col = self._messages_col(user_id, thread_id)
        q: Query = col.order_by("ts", direction=firestore.Query.ASCENDING)
        if after_ts:
            try:
                # simple pagination par horodatage ISO
                q = q.start_after({"ts": after_ts})
            except Exception:
                pass
        q = q.limit(max(1, min(limit, 500)))
        out: List[MessageOut] = []
        async for snap in q.stream():
            data = snap.to_dict() or {}
            out.append(MessageOut(
                id=snap.id,
                role=str(data.get("role") or "assistant"),
                content=str(data.get("content") or ""),
                agent=data.get("agent"),
                model=data.get("model"),
                ts=_iso(data.get("ts")) or _iso(_utcnow()),
                rag_sources=data.get("rag_sources"),
            ))
        return out

    async def add_message(self, user_id: str, thread_id: str, msg: MessageCreate) -> MessageOut:
        now = _utcnow()
        doc = self._thread_doc(user_id, thread_id)
        if not (await doc.get()).exists:
            raise KeyError("thread_not_found")
        mid = uuid4().hex[:12]
        msg_ref = self._messages_col(user_id, thread_id).document(mid)
        payload = {
            "role": msg.role,
            "content": msg.content,
            "agent": msg.agent,
            "model": msg.model,
            "rag_sources": msg.rag_sources or None,
            "ts": now,
        }
        await msg_ref.set(payload)
        # compteur + horodatages
        await doc.update({
            "message_count": firestore.Increment(1),
            "last_message_at": now,
            "updated_at": now,
        })
        return MessageOut(
            id=mid,
            role=msg.role,
            content=msg.content,
            agent=msg.agent,
            model=msg.model,
            ts=_iso(now),
            rag_sources=msg.rag_sources or None,
        )

    # ----- Helpers intégration Chat/Débat -----
    async def ensure_session_thread(self, user_id: str, session_id: str, *, title: Optional[str] = None) -> str:
        """
        Crée (si besoin) un thread déterministe lié à la session.
        - id: s_<session_id…> (12 chars)
        - stocke 'session_id' dans le doc (utile pour diagnostics)
        """
        tid = _session_thread_id(session_id)
        doc = self._thread_doc(user_id, tid)
        snap = await doc.get()
        now = _utcnow()
        if not snap.exists:
            await doc.set({
                "title": title or f"Session {session_id[:8]}",
                "archived": False,
                "doc_ids": [],
                "created_at": now,
                "updated_at": now,
                "last_message_at": None,
                "message_count": 0,
                "session_id": session_id,
            })
        else:
            await doc.update({"updated_at": now})
        return tid
