# src/backend/features/dashboard/router.py
# V3.2 - Prefix retiré (évite double /api/dashboard) + safe resolver
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Any, Awaitable, Callable, Dict, List

from backend.features.dashboard.service import DashboardService
from backend.features.dashboard.timeline_service import TimelineService
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


def _resolve_get_timeline_service() -> Callable[..., Awaitable[TimelineService]]:
    try:
        candidate = getattr(deps, "get_timeline_service")
        if callable(candidate):
            return candidate  # type: ignore[return-value]
    except Exception:
        logger.debug(
            "get_timeline_service not available from dependencies", exc_info=True
        )

    async def _placeholder(*args: Any, **kwargs: Any) -> TimelineService:
        raise HTTPException(status_code=503, detail="Timeline service unavailable.")

    return _placeholder


@router.get(
    "/costs/summary",
    response_model=Dict[str, Any],
    tags=["Dashboard"],
    summary="Récupère le résumé complet des données du cockpit",
    description="Fournit un résumé des coûts, des métriques de monitoring et les seuils d'alerte. "
                "Filtre par session si X-Session-Id est fourni dans les headers, sinon retourne toutes les sessions de l'utilisateur.",
)
async def get_dashboard_summary(
    request: Request,
    dashboard_service: DashboardService = Depends(_resolve_get_dashboard_service()),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, Any]:
    logger.info("Récupération du résumé des données pour le dashboard.")
    session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")

    if session_id:
        logger.info(f"Filtrage par session: {session_id}")
    else:
        logger.info("Pas de session_id fourni, agrégation sur toutes les sessions de l'utilisateur")

    data = await dashboard_service.get_dashboard_data(user_id=user_id, session_id=session_id)
    logger.info("Résumé des données du cockpit envoyé.")
    return data


@router.get(
    "/costs/summary/session/{session_id}",
    response_model=Dict[str, Any],
    tags=["Dashboard"],
    summary="Récupère le résumé des données pour une session spécifique",
    description="Fournit un résumé complet filtré strictement pour une session donnée.",
)
async def get_session_dashboard_summary(
    session_id: str,
    dashboard_service: DashboardService = Depends(_resolve_get_dashboard_service()),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, Any]:
    logger.info(f"Récupération des données du cockpit pour session: {session_id}")
    data = await dashboard_service.get_dashboard_data(user_id=user_id, session_id=session_id)
    logger.info(f"Données session {session_id} envoyées.")
    return data


@router.get(
    "/timeline/activity",
    response_model=List[Dict[str, Any]],
    tags=["Dashboard", "Timeline"],
    summary="Timeline d'activité (messages + threads par jour)",
    description="Retourne les données temporelles d'activité pour les graphiques.",
)
async def get_activity_timeline(
    request: Request,
    period: str = Query("30d", description="Période: 7d, 30d, 90d, 1y"),
    timeline_service: TimelineService = Depends(_resolve_get_timeline_service()),
    user_id: str = Depends(deps.get_user_id),
) -> List[Dict[str, Any]]:
    session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
    logger.info(f"Timeline activité period={period}, session_id={session_id}")
    return await timeline_service.get_activity_timeline(
        period=period, user_id=user_id, session_id=session_id
    )


@router.get(
    "/timeline/costs",
    response_model=List[Dict[str, Any]],
    tags=["Dashboard", "Timeline"],
    summary="Timeline des coûts par jour",
)
async def get_costs_timeline(
    request: Request,
    period: str = Query("30d", description="Période: 7d, 30d, 90d, 1y"),
    timeline_service: TimelineService = Depends(_resolve_get_timeline_service()),
    user_id: str = Depends(deps.get_user_id),
) -> List[Dict[str, Any]]:
    session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
    return await timeline_service.get_costs_timeline(
        period=period, user_id=user_id, session_id=session_id
    )


@router.get(
    "/timeline/tokens",
    response_model=List[Dict[str, Any]],
    tags=["Dashboard", "Timeline"],
    summary="Timeline des tokens par jour",
)
async def get_tokens_timeline(
    request: Request,
    period: str = Query("30d", description="Période: 7d, 30d, 90d, 1y"),
    timeline_service: TimelineService = Depends(_resolve_get_timeline_service()),
    user_id: str = Depends(deps.get_user_id),
) -> List[Dict[str, Any]]:
    session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
    return await timeline_service.get_tokens_timeline(
        period=period, user_id=user_id, session_id=session_id
    )


@router.get(
    "/distribution/{metric}",
    response_model=Dict[str, int],
    tags=["Dashboard", "Distribution"],
    summary="Distribution par agent pour une métrique",
)
async def get_distribution(
    request: Request,
    metric: str,
    period: str = Query("30d", description="Période: 7d, 30d, 90d, 1y"),
    timeline_service: TimelineService = Depends(_resolve_get_timeline_service()),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, int]:
    session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
    return await timeline_service.get_distribution_by_agent(
        metric=metric, period=period, user_id=user_id, session_id=session_id
    )


@router.get(
    "/costs/by-agent",
    response_model=List[Dict[str, Any]],
    tags=["Dashboard", "Costs"],
    summary="Récupère les coûts par agent avec le modèle utilisé",
    description="Retourne la liste des agents avec leurs coûts, tokens et le modèle utilisé.",
)
async def get_costs_by_agent(
    request: Request,
    dashboard_service: DashboardService = Depends(_resolve_get_dashboard_service()),
    user_id: str = Depends(deps.get_user_id),
) -> List[Dict[str, Any]]:
    session_id = request.headers.get("X-Session-Id") or request.headers.get("x-session-id")
    logger.info(f"Récupération des coûts par agent, user_id={user_id}, session_id={session_id}")
    return await dashboard_service.get_costs_by_agent(user_id=user_id, session_id=session_id)
