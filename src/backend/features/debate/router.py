# src/backend/features/debate/router.py
# V3.1 - REST "lecture seule" des debats actifs
# - DI conforme au ServiceContainer
# - Endpoints: GET / (liste), GET /{debate_id} (detail)
import logging
from enum import Enum
from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import Provide, inject

from .service import DebateService
from backend.containers import ServiceContainer  # DI officielle

logger = logging.getLogger(__name__)
router = APIRouter()
TAGS: List[str | Enum] = ["Debate"]  # optionnel, pour la doc si activee


@router.get("/{debate_id}", summary="Get Debate Details", tags=TAGS)
@inject
async def get_debate_details(
    debate_id: str,
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service]),
) -> dict[str, Any]:
    """Recupere les details d'un debat actif (structure Pydantic serialisable)."""
    session = getattr(debate_service, "active_debates", {}).get(debate_id)
    if not session:
        raise HTTPException(status_code=404, detail="Debat non trouve dans les sessions actives.")
    from typing import cast
    return cast(dict[str, Any], session.model_dump(mode="json"))


@router.get("/", summary="List Active Debates", tags=TAGS)
@inject
async def list_active_debates(
    debate_service: DebateService = Depends(Provide[ServiceContainer.debate_service]),
) -> dict[str, Any]:
    """Liste des debats actuellement en cours (vue synthetique)."""
    active = getattr(debate_service, "active_debates", {})
    debate_list: list[dict[str, Any]] = [
        {"debate_id": debate_id, "topic": state.config.topic, "status": state.status}
        for debate_id, state in active.items()
    ]
    return {
        "active_debates": debate_list
    }
