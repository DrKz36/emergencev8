# src/backend/features/debate/router.py
# V3.1 - REST "lecture seule" des débats actifs
# - DI conforme au ServiceContainer
# - Endpoints: GET / (liste), GET /{debate_id} (détail)
import logging
from fastapi import APIRouter, HTTPException, Depends
from dependency_injector.wiring import inject, Provide

from .service import DebateService
from backend.containers import ServiceContainer  # DI officielle

logger = logging.getLogger(__name__)
router = APIRouter()
tags = ["Debate"]  # optionnel, pour la doc si activée

@router.get("/{debate_id}", summary="Get Debate Details", tags=tags)
@inject
async def get_debate_details(
    debate_id: str,
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service])
):
    """
    Récupère les détails d'un débat actif (structure Pydantic sérialisable).
    """
    session = getattr(debate_service, "active_debates", {}).get(debate_id)
    if not session:
        raise HTTPException(status_code=404, detail="Débat non trouvé dans les sessions actives.")
    return session.model_dump(mode='json')

@router.get("/", summary="List Active Debates", tags=tags)
@inject
async def list_active_debates(
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service])
):
    """
    Liste des débats actuellement en cours (vue synthétique).
    """
    active = getattr(debate_service, "active_debates", {})
    return {
        "active_debates": [
            {"debate_id": id, "topic": s.config.topic, "status": s.status}
            for id, s in active.items()
        ]
    }
