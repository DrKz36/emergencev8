# src/backend/features/memory/router.py
# V1.1 — Endpoint pour déclencher le MemoryGardener (sans dépendance externe).
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request

from backend.features.memory.gardener import MemoryGardener

router = APIRouter(prefix="/api/memory", tags=["Memory & Knowledge"])
logger = logging.getLogger(__name__)


def _get_gardener_from_request(request: Request) -> MemoryGardener:
    """
    Construit un MemoryGardener à partir du container DI stocké sur l'app FastAPI.
    Évite l'import d'un provider inexistant dans shared.dependencies.
    """
    container = request.app.state.service_container
    return MemoryGardener(
        db_manager=container.db_manager(),
        vector_service=container.vector_service(),
        memory_analyzer=container.memory_analyzer(),
    )


@router.post(
    "/tend-garden",
    response_model=Dict[str, Any],
    summary="Déclenche la tâche de consolidation de la mémoire",
    description=(
        "Lance manuellement le 'MemoryGardener' pour analyser les sessions récentes, "
        "consolider les concepts dans la base de connaissance et gérer le cycle de vie des souvenirs."
    ),
)
async def tend_garden_endpoint(request: Request) -> Dict[str, Any]:
    logger.info("Requête reçue sur l'endpoint /api/memory/tend-garden.")
    try:
        gardener = _get_gardener_from_request(request)
        report = await gardener.tend_the_garden()
        if report.get("status") == "error":
            raise HTTPException(status_code=500, detail=report.get("message", "Erreur interne"))
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Erreur non gérée dans l'endpoint tend_garden: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Une erreur interne critique est survenue.")
