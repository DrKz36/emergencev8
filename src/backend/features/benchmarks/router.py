from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.features.benchmarks.service import BenchmarksService
from backend.shared import dependencies as deps

router = APIRouter(tags=["Benchmarks"])
logger = logging.getLogger(__name__)


class RankedItem(BaseModel):
    """Item classé avec pertinence et timestamp."""

    rel: float = Field(..., description="Relevance score (0+)")
    ts: datetime = Field(..., description="Timestamp ISO format")


class TemporalNDCGRequest(BaseModel):
    """Requête pour calculer nDCG@k temporelle."""

    ranked_items: List[RankedItem] = Field(
        ..., description="Liste ordonnée d'items classés"
    )
    k: int = Field(
        default=10, ge=1, description="Nombre d'items considérés (top-k)"
    )
    now: Optional[datetime] = Field(
        default=None, description="Timestamp de référence (défaut: UTC now)"
    )
    T_days: float = Field(
        default=7.0, gt=0, description="Période de normalisation en jours"
    )
    lam: float = Field(
        default=0.3, ge=0, description="Taux de décroissance exponentielle"
    )


async def _resolve_benchmarks_service(request: Request) -> BenchmarksService:
    from typing import cast

    try:
        provider = getattr(deps, "get_benchmarks_service")
    except AttributeError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=503, detail="Benchmarks service unavailable."
        ) from exc
    return cast(BenchmarksService, await provider(request))


@router.get(
    "/results",
    summary="Retourne les derniers résultats de benchmarks",
)
async def list_benchmark_results(
    request: Request,
    scenario_id: Optional[str] = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
    service: BenchmarksService = Depends(_resolve_benchmarks_service),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, Any]:
    del user_id  # utilisé uniquement pour valider l'accès
    payload = await service.list_results(scenario_id=scenario_id, limit=limit)
    return {
        "results": payload,
        "filters": {"scenario_id": scenario_id, "limit": limit},
    }


@router.get(
    "/scenarios",
    summary="Catalogue des scénarios de benchmarks supportés",
)
async def list_benchmark_scenarios(
    request: Request,
    service: BenchmarksService = Depends(_resolve_benchmarks_service),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, Any]:
    del user_id
    return {"scenarios": service.get_supported_scenarios()}


@router.post(
    "/run",
    status_code=202,
    summary="Déclenche l'exécution synchrone d'une matrice benchmarks",
)
async def trigger_benchmark_run(
    request: Request,
    body: Dict[str, Any],
    service: BenchmarksService = Depends(_resolve_benchmarks_service),
    admin_claims: Dict[str, Any] = Depends(deps.require_admin_claims),
) -> Dict[str, Any]:
    del admin_claims
    scenario_id = body.get("scenario_id")
    if not scenario_id:
        raise HTTPException(status_code=422, detail="scenario_id requis.")
    try:
        matrix = await service.run_matrix(
            scenario_id=scenario_id,
            context=body.get("context"),
            metadata=body.get("metadata"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"matrix": matrix.to_dict()}


@router.post(
    "/metrics/ndcg-temporal",
    summary="Calcule la métrique nDCG@k temporelle sur des résultats classés",
)
async def calculate_ndcg_temporal(
    request: Request,
    payload: TemporalNDCGRequest,
    service: BenchmarksService = Depends(_resolve_benchmarks_service),
    user_id: str = Depends(deps.get_user_id),
) -> Dict[str, Any]:
    """
    Calcule le nDCG@k temporel pour mesurer la qualité d'un classement
    en intégrant la fraîcheur temporelle des documents.

    Cette métrique combine :
    - La pertinence (relevance) des items
    - La fraîcheur temporelle (timestamp)

    Utilisé pour mesurer l'impact des boosts de fraîcheur et entropie
    dans le moteur de ranking.

    Args:
        payload: Requête contenant les items classés et paramètres

    Returns:
        Score nDCG@k temporel entre 0 (pire) et 1 (parfait)
    """
    del user_id  # utilisé uniquement pour valider l'accès

    # Conversion Pydantic models → dicts pour la métrique
    ranked_items = [{"rel": item.rel, "ts": item.ts} for item in payload.ranked_items]

    try:
        score = service.calculate_temporal_ndcg(
            ranked_items=ranked_items,
            k=payload.k,
            now=payload.now,
            T_days=payload.T_days,
            lam=payload.lam,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "ndcg_time@k": score,
        "k": payload.k,
        "num_items": len(ranked_items),
        "parameters": {
            "T_days": payload.T_days,
            "lambda": payload.lam,
        },
    }
