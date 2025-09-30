# src/backend/features/dashboard/router.py
# V3.2 - Prefix retiré (évite double /api/dashboard) + safe resolver
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Any, Awaitable, Callable, Dict

from backend.features.dashboard.service import DashboardService
from backend.shared import dependencies as deps  # module, pas l'attribut direct

# ⚠️ Pas de prefix ici : main.py montera le router avec "/api/dashboard"
router = APIRouter(tags=["Dashboard"])
logger = logging.getLogger(__name__)


def _resolve_get_dashboard_service() -> Callable[..., Awaitable[DashboardService]]:
    try:
        candidate = getattr(deps, "get_dashboard_service")
        if callable(candidate):
            return candidate  # type: ignore[return-value]
    except Exception:
        logger.debug(
            "get_dashboard_service not available from dependencies", exc_info=True
        )

    async def _placeholder(*args: Any, **kwargs: Any) -> DashboardService:
        raise HTTPException(status_code=503, detail="Dashboard service unavailable.")

    return _placeholder


@router.get(
    "/costs/summary",
    response_model=Dict[str, Any],
    tags=["Dashboard"],
    summary="Récupère le résumé complet des données du cockpit",
    description="Fournit un résumé des coûts, des métriques de monitoring et les seuils d'alerte.",
)
async def get_dashboard_summary(
    request: Request,
    dashboard_service: DashboardService = Depends(_resolve_get_dashboard_service()),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, Any]:
    logger.info("Récupération du résumé des données pour le dashboard.")
    session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
    data = await dashboard_service.get_dashboard_data(user_id=user_id, session_id=session_id)
    logger.info("Résumé des données du cockpit envoyé.")
    return data
