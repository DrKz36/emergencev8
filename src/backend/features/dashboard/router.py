# src/backend/features/dashboard/router.py
# V3.2 - Prefix retiré (évite double /api/dashboard) + safe resolver
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Callable

from backend.features.dashboard.service import DashboardService
from backend.shared import dependencies as deps  # module, pas l’attribut direct

# ⚠️ Pas de prefix ici : main.py montera le router avec "/api/dashboard"
router = APIRouter(tags=["Dashboard"])
logger = logging.getLogger(__name__)

def _resolve_get_dashboard_service() -> Callable[[], DashboardService]:
    try:
        return getattr(deps, "get_dashboard_service")
    except Exception:
        async def _placeholder() -> DashboardService:  # type: ignore
            raise HTTPException(status_code=503, detail="Dashboard service unavailable.")
        return _placeholder

@router.get(
    "/costs/summary",
    response_model=Dict[str, Any],
    tags=["Dashboard"],
    summary="Récupère le résumé complet des données du cockpit",
    description="Fournit un résumé des coûts, des métriques de monitoring et les seuils d'alerte."
)
async def get_dashboard_summary(
    dashboard_service: DashboardService = Depends(_resolve_get_dashboard_service())
) -> Dict[str, Any]:
    logger.info("Récupération du résumé des données pour le dashboard…")
    data = await dashboard_service.get_dashboard_data()
    logger.info("Résumé des données du cockpit envoyé.")
    return data
