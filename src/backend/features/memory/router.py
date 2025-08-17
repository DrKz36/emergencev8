# src/backend/features/memory/router.py
# V2.0 - Endpoint(s) de maintenance de la mémoire consolidée
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from backend.features.memory.gardener import MemoryGardener
from backend.shared.dependencies import get_memory_gardener

router = APIRouter(prefix="/api/memory", tags=["Memory"])

logger = logging.getLogger(__name__)

@router.get("/tend-garden")
@router.post("/tend-garden")
async def tend_garden(gardener: MemoryGardener = Depends(get_memory_gardener)) -> Dict[str, Any]:
    """
    Déclenche la consolidation des sessions -> concepts + vecteurs.
    GET ou POST acceptés.
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
