# src/backend/features/memory/router.py
# V3.3 — P1.5 mémoire : body optionnel sur /tend-garden (évite 422),
#        /status conservé, /clear non destructif (journalisation decay).
# Aucune modif d'architecture ; DI via app.state.service_container.

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, Body, HTTPException
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger("memory.router")

router = APIRouter(tags=["Memory"])

# Mémoire éphémère (dernier rapport pour GET /status)
_LAST_REPORT: Dict[str, Any] = {"ts": None, "report": None}


# --------- Schemas ---------
class TendGardenPayload(BaseModel):
    consolidation_limit: int = Field(
        10, ge=1, le=100, description="Nombre max de sessions/threads à traiter"
    )
    thread_id: Optional[str] = Field(
        None, description="Si fourni, consolidation ciblée sur ce thread"
    )


# --------- Helpers (DI & time) ---------
def _container(request: Request):
    c = getattr(request.app.state, "service_container", None)
    if c is None:
        raise HTTPException(status_code=503, detail="Service container indisponible")
    return c

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _safe_payload(payload_in: Optional[dict | TendGardenPayload]) -> TendGardenPayload:
    """
    Rend l'endpoint tolérant :
    - Aucun body -> defaults
    - Body non typé -> coerce via Pydantic
    - consolidation_limit string -> convertie si possible
    """
    if payload_in is None:
        return TendGardenPayload()

    if isinstance(payload_in, TendGardenPayload):
        # normalize string -> int si besoin (déjà validé normalement)
        try:
            payload_in.consolidation_limit = int(payload_in.consolidation_limit)
        except Exception:
            pass
        return payload_in

    # dict brut
    data = dict(payload_in)
    # coercion manuelle légère
    if "consolidation_limit" in data and isinstance(data["consolidation_limit"], str):
        try:
            data["consolidation_limit"] = int(data["consolidation_limit"])
        except Exception:
            # on laisse Pydantic décider
            pass
    try:
        return TendGardenPayload(**data)
    except ValidationError as ve:
        logger.warning(f"[tend-garden] Payload invalide, defaults utilisés: {ve}")
        return TendGardenPayload()


# --------- Routes ---------

@router.post("/tend-garden")
async def tend_garden(
    request: Request,
    # Body optionnel : certains clients enverront POST sans body -> plus de 422
    payload: Optional[TendGardenPayload | dict] = Body(default=None),
):
    """
    Lance la consolidation mémoire.
    - Sans body : defaults (limit=10, pas de thread ciblé).
    - Avec thread_id : consolidation ciblée sur ce thread.
    """
    container = _container(request)
    try:
        db = container.db_manager()
        vec = container.vector_service()
        analyzer = container.memory_analyzer()
    except Exception as e:
        logger.error(f"[tend-garden] DI KO: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Dépendances mémoire indisponibles")

    from backend.features.memory.gardener import MemoryGardener  # import tardif

    p = _safe_payload(payload)
    gardener = MemoryGardener(db_manager=db, vector_service=vec, memory_analyzer=analyzer)

    try:
        report = await gardener.tend_the_garden(
            consolidation_limit=int(p.consolidation_limit or 10),
            thread_id=(p.thread_id or None),
        )
    except Exception as e:
        logger.error(f"[tend-garden] Erreur: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur tend-garden: {e}")

    _LAST_REPORT["ts"] = _now_iso()
    _LAST_REPORT["report"] = report

    return {
        "status": "success",
        "run_at": _LAST_REPORT["ts"],
        "thread_id": p.thread_id or None,
        "report": report,
    }


@router.get("/status")
async def memory_status():
    """
    Retourne le dernier rapport tend-garden en mémoire (léger, non persistant).
    """
    if not _LAST_REPORT["ts"] or not _LAST_REPORT["report"]:
        return {
            "status": "idle",
            "message": "Aucun rapport en mémoire. Lance POST /api/memory/tend-garden.",
        }
    return {
        "status": "ok",
        "last_run": _LAST_REPORT["ts"],
        "report": _LAST_REPORT["report"],
    }


@router.delete("/clear")
@router.post("/clear")
async def clear_memory(request: Request):
    """
    Compat API client (DELETE puis fallback POST).
    Non destructif par défaut : journalise un aging (decay).
    """
    container = _container(request)
    try:
        db = container.db_manager()
        vec = container.vector_service()
        analyzer = container.memory_analyzer()
    except Exception as e:
        logger.error(f"[clear] DI KO: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Dépendances mémoire indisponibles")

    from backend.features.memory.gardener import MemoryGardener  # import tardif

    gardener = MemoryGardener(db_manager=db, vector_service=vec, memory_analyzer=analyzer)
    try:
        await gardener._decay_knowledge()  # trace l’intention d’effacement
    except Exception as e:
        logger.warning(f"[clear] Décay non journalisé: {e}")

    return {"status": "success", "message": "Mémoire: opération de maintenance journalisée (decay)."}
