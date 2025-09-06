# src/backend/features/memory/router.py
# V3.9 — tend-garden: POST+GET ; instanciation MemoryGardener positionnelle ; /status where $eq (compat Chroma)
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("memory.router")

router = APIRouter(tags=["Memory"])

_LAST_REPORT: Dict[str, Any] = {"ts": None, "report": None}

class TendGardenPayload(BaseModel):
    consolidation_limit: int = Field(10, ge=1, le=100)
    thread_id: Optional[str] = Field(None)

def _container(request: Request):
    c = getattr(request.app.state, "service_container", None)
    if c is None:
        raise HTTPException(status_code=503, detail="Service container indisponible")
    return c

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _coerce_payload_dict(data: Dict[str, Any]) -> TendGardenPayload:
    if "consolidation_limit" in data and isinstance(data["consolidation_limit"], str):
        try:
            data["consolidation_limit"] = int(data["consolidation_limit"])
        except Exception:
            pass
    try:
        return TendGardenPayload(**data)
    except ValidationError as ve:
        logger.warning(f"[tend-garden] Payload invalide, defaults utilisés: {ve}")
        return TendGardenPayload()

def _detect_user_id(request: Request) -> Optional[str]:
    # Heuristique : entêtes dev-auth / Google
    for k in ("x-user-id", "x-auth-sub", "x-goog-authenticated-user-id", "x-goog-user-id"):
        v = request.headers.get(k) or request.headers.get(k.upper())
        if v:
            if ":" in v:  # ex: accounts.google.com:123456789
                v = v.split(":", 1)[-1]
            return v.strip()
    return None

async def _run_tend_garden(container, consolidation_limit: int, thread_id: Optional[str]) -> Dict[str, Any]:
    try:
        db = container.db_manager()
        vec = container.vector_service()
        analyzer = container.memory_analyzer()
    except Exception as e:
        logger.error(f"[tend-garden] DI KO: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Dépendances mémoire indisponibles")

    # ⚠️ Instanciation positionnelle (signature-agnostique)
    from backend.features.memory.gardener import MemoryGardener
    gardener = MemoryGardener(db, vec, analyzer)

    try:
        report = await gardener.tend_the_garden(
            consolidation_limit=int(consolidation_limit or 10),
            thread_id=(thread_id or None),
        )
    except Exception as e:
        logger.error(f"[tend-garden] Erreur: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur tend-garden: {e}")

    _LAST_REPORT["ts"] = _now_iso()
    _LAST_REPORT["report"] = report
    return {"status": "success", "run_at": _LAST_REPORT["ts"], "thread_id": thread_id or None, "report": report}

@router.post("/tend-garden")
async def tend_garden_post(request: Request):
    raw = await request.body()
    if not raw:
        payload_obj = TendGardenPayload()
    else:
        try:
            parsed = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(parsed, dict):
                parsed = {}
            payload_obj = _coerce_payload_dict(parsed)
        except Exception as e:
            logger.info(f"[tend-garden] Body non JSON ou invalide, defaults utilisés: {e}")
            payload_obj = TendGardenPayload()
    return await _run_tend_garden(_container(request), payload_obj.consolidation_limit, payload_obj.thread_id)

@router.get("/tend-garden")
async def tend_garden_get(
    request: Request,
    consolidation_limit: int = Query(10, ge=1, le=100),
    thread_id: Optional[str] = Query(None),
):
    return await _run_tend_garden(_container(request), consolidation_limit, thread_id)

@router.get("/status")
async def memory_status(request: Request):
    """
    Statut mémoire user-aware + compat:
    - has_stm: bool(summary) sur la dernière session de l’utilisateur (fallback globale)
    - ltm_count / ltm_items: nb d’items dans emergence_knowledge(user_id)
    - injected: has_stm or ltm_count>0
    - Compat: renvoie aussi le dernier rapport /tend-garden (_LAST_REPORT)
    """
    container = _container(request)
    try:
        db = container.db_manager()
        vec = container.vector_service()
    except Exception as e:
        logger.error(f"[status] DI KO: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Dépendances mémoire indisponibles")

    uid = _detect_user_id(request)

    # 1) has_stm
    has_stm = False
    try:
        if uid:
            row = await db.fetch_one("SELECT summary FROM sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (uid,))
        else:
            row = await db.fetch_one("SELECT summary FROM sessions ORDER BY updated_at DESC LIMIT 1", ())
        if row:
            summary = (row["summary"] if isinstance(row, dict) else row[0]) or ""
            has_stm = bool(isinstance(summary, str) and summary.strip())
    except Exception as e:
        logger.warning(f"[status] Lecture summary KO: {e}")

    # 2) ltm_count (vector store)
    ltm_count = 0
    try:
        knowledge_col = vec.get_or_create_collection("emergence_knowledge")
        where = {"user_id": {"$eq": uid}} if uid else None
        got = knowledge_col.get(where=where)  # pas d'include=ids (builds variables)
        ids = got.get("ids") or []
        if ids and isinstance(ids, list) and len(ids) > 0 and isinstance(ids[0], list):
            ids = [x for sub in ids for x in (sub or [])]
        ltm_count = len(ids or [])
    except Exception as e:
        logger.warning(f"[status] Lecture LTM KO: {e}")

    injected = bool(has_stm or ltm_count > 0)

    return {
        "status": "ok",
        "has_stm": has_stm,
        "ltm_count": int(ltm_count),
        "ltm_items": int(ltm_count),   # compat front
        "injected": injected,
        "last_run": _LAST_REPORT["ts"],
        "report": _LAST_REPORT["report"],
        "user_id": uid,
    }

@router.delete("/clear")
@router.post("/clear")
async def clear_memory(request: Request):
    container = _container(request)
    try:
        db = container.db_manager()
        vec = container.vector_service()
        analyzer = container.memory_analyzer()
    except Exception as e:
        logger.error(f"[clear] DI KO: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Dépendances mémoire indisponibles")

    from backend.features.memory.gardener import MemoryGardener
    gardener = MemoryGardener(db, vec, analyzer)
    try:
        await gardener._decay_knowledge()
    except Exception as e:
        logger.warning(f"[clear] Décay non journalisé: {e}")

    return {"status": "success", "message": "Mémoire: opération de maintenance journalisée (decay)."}
