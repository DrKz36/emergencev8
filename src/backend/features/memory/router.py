# src/backend/features/memory/router.py
# V2.2 - GET/POST + garde Bearer; aucun prefix local (monté dans main.py).
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from backend.features.memory.gardener import MemoryGardener
from backend.shared.dependencies import get_memory_gardener, require_bearer_or_401

# IMPORTANT: pas de prefix ici; main.py monte déjà le router avec "/api/memory"
router = APIRouter(tags=["Memory"])
logger = logging.getLogger(__name__)

@router.get("/tend-garden")
@router.post("/tend-garden")
async def tend_garden(
    gardener: MemoryGardener = Depends(get_memory_gardener),
    _token: str = Depends(require_bearer_or_401),
) -> Dict[str, Any]:
    """
    Déclenche la consolidation des sessions -> summary/concepts -> vecteurs.
    GET ou POST acceptés. Protégé par Authorization: Bearer <token>.
    """
    logger.info("Endpoint /api/memory/tend-garden déclenché.")
    try:
        report = await gardener.tend_the_garden()
        if report.get("status") == "error":
            raise HTTPException(status_code=500, detail=report.get("message", "Erreur inconnue."))
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Échec serveur dans tend_garden.")
        raise HTTPException(status_code=500, detail=str(e))
