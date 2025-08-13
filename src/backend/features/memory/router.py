# src/backend/features/memory/router.py
# NOUVEAU - V1.0: Endpoint pour déclencher le MemoryGardener.
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from backend.features.memory.gardener import MemoryGardener
from backend.shared.dependencies import get_memory_gardener

router = APIRouter(
    prefix="/api/memory",
    tags=["Memory & Knowledge"]
)
logger = logging.getLogger(__name__)

@router.post(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="Déclenche la tâche de consolidation de la mémoire",
    description="Lance manuellement le 'MemoryGardener' pour analyser les sessions récentes, "
                "consolider les concepts dans la base de connaissance et gérer le cycle de vie des souvenirs."
)
async def tend_garden_endpoint(
    gardener: MemoryGardener = Depends(get_memory_gardener)
) -> Dict[str, Any]:
    """
    Déclenche le processus du jardinier de la mémoire.
    
    Cette opération peut être longue si de nombreuses sessions doivent être traitées.
    """
    logger.info("Requête reçue sur l'endpoint /tend-garden.")
    try:
        report = await gardener.tend_the_garden()
        if report["status"] == "error":
            raise HTTPException(status_code=500, detail=report["message"])
        return report
    except Exception as e:
        logger.critical(f"Erreur non gérée dans l'endpoint tend_garden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Une erreur interne critique est survenue.")

