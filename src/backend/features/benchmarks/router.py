from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.features.benchmarks.service import BenchmarksService
from backend.shared import dependencies as deps

router = APIRouter(tags=["Benchmarks"])
logger = logging.getLogger(__name__)


async def _resolve_benchmarks_service(request: Request) -> BenchmarksService:
    from typing import cast
    try:
        provider = getattr(deps, "get_benchmarks_service")
    except AttributeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=503, detail="Benchmarks service unavailable.") from exc
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
