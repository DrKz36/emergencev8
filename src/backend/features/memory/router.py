# src/backend/features/memory/router.py
# V3.4 — P1.5 mémoire : tolérance totale au body malformé sur /tend-garden.
#         On lit le body brut (sans Pydantic préalable), on tente json.loads,
#         et on retombe sur des defaults en cas d'échec. /status et /clear inchangés.
#         Aucune modif d’architecture.

from __future__ import annotations

import json
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

def _coerce_payload_dict(data: Dict[str, Any]) -> TendGardenPayload:
    # coercion douce (ex: "10" -> 10)
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


# --------- Routes ---------

@router.post("/tend-garden")
async def tend_garden(request: Request):
    """
    Lance la consolidation mémoire.
    - Aucun body ou body invalide -> defaults (limit=10, pas de thread ciblé).
    - Body JSON valide pouvant contenir: { "consolidation_limit": int, "thread_id": "..." }.
    """
    container = _container(request)
    try:
        db = container.db_manager()
        vec = container.vector_service()
        analyzer = container.memory_analyzer()
    except Exception as e:
        logger.error(f"[tend-garden] DI KO: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Dépendances mémoire indisponibles")

    # Lecture du body BRUT pour éviter le 422 avant d'entrer ici
    raw = await request.body()
    payload_obj: TendGardenPayload
    if not raw:
        payload_obj = TendGardenPayload()
    else:
        try:
            # Tente un JSON ; si malformé -> defaults
            parsed = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(parsed, dict):
                parsed = {}
            payload_obj = _coerce_payload_dict(parsed)
        except Exception as e:
            logger.info(f"[tend-garden] Body non JSON ou invalide, defaults utilisés: {e}")
            payload_obj = TendGardenPayload()

    from backend.features.memory.gardener import MemoryGardener  # import tardif pour éviter cycles

    gardener = MemoryGardener(db_manager=db, vector_service=vec, memory_analyzer=analyzer)
    try:
        report = await gardener.tend_the_garden(
            consolidation_limit=int(payload_obj.consolidation_limit or 10),
            thread_id=(payload_obj.thread_id or None),
        )
    except Exception as e:
        logger.error(f"[tend-garden] Erreur: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur tend-garden: {e}")

    _LAST_REPORT["ts"] = _now_iso()
    _LAST_REPORT["report"] = report

    return {
        "status": "success",
        "run_at": _LAST_REPORT["ts"],
        "thread_id": payload_obj.thread_id or None,
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
