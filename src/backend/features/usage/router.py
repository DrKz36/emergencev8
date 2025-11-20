# src/backend/features/usage/router.py
"""
Phase 2 Guardian Cloud - Usage API Router
Endpoint /api/usage/summary pour dashboard admin
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException

from backend.shared.dependencies import require_admin_claims

from .repository import UsageRepository
from .guardian import UsageGuardian

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/usage", tags=["Usage Tracking"])


def _get_usage_repository() -> UsageRepository:
    """
    Dependency pour récupérer UsageRepository
    TODO: Intégrer dans ServiceContainer pour DI propre
    """
    try:
        # Import local pour éviter circular dependency
        from backend.containers import ServiceContainer

        container = ServiceContainer()
        db_manager = container.db_manager()
        return UsageRepository(db_manager)
    except Exception as e:
        logger.error(f"Erreur init UsageRepository: {e}")
        raise HTTPException(status_code=503, detail="UsageRepository indisponible")


@router.get("/summary")
async def get_usage_summary(
    hours: int = Query(2, ge=1, le=720, description="Heures à analyser (1-720)"),
    admin_claims: Dict[str, Any] = Depends(require_admin_claims),
    repository: UsageRepository = Depends(_get_usage_repository),
) -> dict[str, Any]:
    """
    Retourne rapport d'usage pour dashboard admin

    **Admin only** - Require role=admin

    Query params:
    - hours: Nombre d'heures à analyser (défaut: 2h, max: 30 jours)

    Returns:
        UsageReport dict avec:
        - period_start/end
        - active_users
        - total_requests
        - total_errors
        - users[] (stats par user)
        - top_features[]
        - error_breakdown{}
    """
    try:
        logger.info(
            f"Admin {admin_claims.get('email')} demande rapport usage ({hours}h)"
        )

        guardian = UsageGuardian(repository)
        report = await guardian.generate_report(hours=hours)

        return report

    except Exception as e:
        logger.error(f"Erreur génération rapport usage: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erreur génération rapport: {str(e)}"
        )


@router.post("/generate-report")
async def generate_usage_report_file(
    hours: int = Query(2, ge=1, le=720),
    admin_claims: Dict[str, Any] = Depends(require_admin_claims),
    repository: UsageRepository = Depends(_get_usage_repository),
) -> dict[str, Any]:
    """
    Génère rapport usage ET le sauvegarde dans reports/usage_report.json

    **Admin only**

    Returns:
        {
            "status": "success",
            "report_path": "reports/usage_report.json",
            "summary": {...}
        }
    """
    try:
        logger.info(
            f"Admin {admin_claims.get('email')} génère rapport fichier ({hours}h)"
        )

        guardian = UsageGuardian(repository)
        report, path = await guardian.generate_and_save_report(hours=hours)

        return {
            "status": "success",
            "report_path": str(path),
            "summary": {
                "active_users": report.get("active_users", 0),
                "total_requests": report.get("total_requests", 0),
                "total_errors": report.get("total_errors", 0),
                "period": f"{report.get('period_start')} -> {report.get('period_end')}",
            },
        }

    except Exception as e:
        logger.error(f"Erreur génération rapport fichier: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erreur génération rapport: {str(e)}"
        )


@router.get("/health")
async def usage_tracking_health() -> dict[str, Any]:
    """
    Health check pour usage tracking system
    Public endpoint (pas besoin admin)
    """
    try:
        _ = _get_usage_repository()  # Test repository disponible
        return {
            "status": "healthy",
            "service": "usage-tracking",
            "repository": "available",
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "usage-tracking",
            "repository": "unavailable",
            "error": str(e),
        }
