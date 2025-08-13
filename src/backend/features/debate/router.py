# src/backend/features/debate/router.py
# V3.0 - FIX ARCHITECTURAL: Importe le ServiceContainer depuis containers.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from dependency_injector.wiring import inject, Provide

from .service import DebateService
# --- CORRECTION ARCHITECTURALE : On importe depuis le fichier dédié ---
from backend.containers import ServiceContainer

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{debate_id}", summary="Get Debate Details")
@inject
async def get_debate_details(
    debate_id: str,
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service])
):
    """Récupère les détails d'un débat actif."""
    session = debate_service.active_debates.get(debate_id)
    if not session:
        raise HTTPException(status_code=404, detail="Débat non trouvé dans les sessions actives.")
    return session.model_dump(mode='json')

@router.get("/", summary="List Active Debates")
@inject
async def list_active_debates(
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service])
):
    """Liste tous les débats actuellement en cours d'exécution."""
    return {
        "active_debates": [
            {"debate_id": id, "topic": s.config.topic, "status": s.status}
            for id, s in debate_service.active_debates.items()
        ]
    }
