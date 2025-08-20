# src/backend/features/threads/router.py
# UTF-8 (CRLF recommandé) — Routes REST Threads/Messages + auth ID Token Google.

from __future__ import annotations

import os
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from .schemas import ThreadCreate, ThreadPatch, ThreadSummary, ThreadDetail, MessageCreate, MessageOut
from .service import ThreadsService

router = APIRouter(tags=["Threads"])

# ---------- Auth util ----------
async def get_current_user_id(request: Request, authorization: Optional[str] = Header(None)) -> str:
    """
    Essaie, dans l'ordre:
      1) request.state.user.id         (si un middleware l'a déjà peuplé)
      2) Authorization: Bearer <IDTOKEN>  (validation Google + aud)
      3) X-User-Id (dev fallback uniquement)
    """
    # 1) middleware/app existant
    user = getattr(request.state, "user", None)
    uid = getattr(user, "id", None) if user else None
    if uid:
        return str(uid)

    # 2) ID Token (GIS)
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        aud = os.getenv("GOOGLE_OAUTH_CLIENT_ID") or os.getenv("EMERGENCE_GOOGLE_CLIENT_ID")
        try:
            req = google_requests.Request()
            info = google_id_token.verify_oauth2_token(token, req, audience=aud)
            sub = info.get("sub")
            if sub:
                return str(sub)
        except Exception:
            pass

    # 3) Dev fallback
    dev_uid = request.headers.get("X-User-Id")
    if dev_uid:
        return str(dev_uid)

    raise HTTPException(status_code=401, detail="Unauthorized")

def service() -> ThreadsService:
    return ThreadsService()

# ---------- Routes ----------
@router.get("", response_model=List[ThreadSummary])
async def list_threads(archived: bool = Query(False), limit: int = Query(50, ge=1, le=200),
                       user_id: str = Depends(get_current_user_id), svc: ThreadsService = Depends(service)):
    return await svc.list_threads(user_id=user_id, archived=archived, limit=limit)

@router.post("", response_model=ThreadDetail, status_code=201)
async def create_thread(body: ThreadCreate, user_id: str = Depends(get_current_user_id),
                        svc: ThreadsService = Depends(service)):
    return await svc.create_thread(user_id=user_id, payload=body)

@router.patch("/{thread_id}", response_model=ThreadDetail)
async def patch_thread(thread_id: str, body: ThreadPatch, user_id: str = Depends(get_current_user_id),
                       svc: ThreadsService = Depends(service)):
    try:
        return await svc.patch_thread(user_id=user_id, thread_id=thread_id, changes=body)
    except KeyError:
        raise HTTPException(status_code=404, detail="thread_not_found")

@router.get("/{thread_id}/messages", response_model=List[MessageOut])
async def list_messages(thread_id: str, limit: int = Query(100, ge=1, le=500), after_ts: Optional[str] = None,
                        user_id: str = Depends(get_current_user_id), svc: ThreadsService = Depends(service)):
    try:
        return await svc.list_messages(user_id=user_id, thread_id=thread_id, limit=limit, after_ts=after_ts)
    except KeyError:
        raise HTTPException(status_code=404, detail="thread_not_found")

@router.post("/{thread_id}/messages", response_model=MessageOut, status_code=201)
async def add_message(thread_id: str, body: MessageCreate, user_id: str = Depends(get_current_user_id),
                      svc: ThreadsService = Depends(service)):
    try:
        return await svc.add_message(user_id=user_id, thread_id=thread_id, msg=body)
    except KeyError:
        raise HTTPException(status_code=404, detail="thread_not_found")

@router.post("/{thread_id}/export")
async def export_thread(thread_id: str, format: str = Query("json"), user_id: str = Depends(get_current_user_id),
                        svc: ThreadsService = Depends(service)):
    # Export minimal : json (liste messages) ou md (transcript simple)
    try:
        msgs = await svc.list_messages(user_id=user_id, thread_id=thread_id, limit=1000)
    except KeyError:
        raise HTTPException(status_code=404, detail="thread_not_found")

    if (format or "").lower() == "md":
        lines = []
        for m in msgs:
            who = "Vous" if m.role == "user" else (m.agent or "Assistant")
            lines.append(f"**{who}** — {m.ts}\n\n{m.content}\n")
        content = "\n".join(lines)
        return Response(content=content, media_type="text/markdown; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="thread_{thread_id}.md"'})
    else:
        # JSON par défaut
        import json as _json
        content = _json.dumps([m.model_dump() for m in msgs], ensure_ascii=False, indent=2)
        return Response(content=content, media_type="application/json; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="thread_{thread_id}.json"'})
