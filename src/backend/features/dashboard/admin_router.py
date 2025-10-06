# src/backend/features/dashboard/admin_router.py
"""
Admin Dashboard Router - Endpoints for global statistics
V1.0 - Admin-only access to global data
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Any, Dict

from backend.features.dashboard.admin_service import AdminDashboardService
from backend.shared import dependencies as deps

router = APIRouter(tags=["Admin Dashboard"])
logger = logging.getLogger(__name__)


def _resolve_get_admin_dashboard_service():
    """Resolve admin dashboard service from dependencies."""
    try:
        candidate = getattr(deps, "get_admin_dashboard_service", None)
        if callable(candidate):
            return candidate
    except Exception:
        logger.debug("get_admin_dashboard_service not available", exc_info=True)

    async def _placeholder(*args, **kwargs):
        raise HTTPException(status_code=503, detail="Admin dashboard service unavailable.")

    return _placeholder


async def verify_admin_role(user_role: str = Depends(deps.get_user_role)):
    """Dependency to verify user has admin role."""
    if user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied. Admin role required."
        )
    return True


@router.get(
    "/admin/dashboard/global",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get global dashboard data (admin only)",
    description="Provides comprehensive global statistics including all users, sessions, and costs.",
)
async def get_global_dashboard(
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(_resolve_get_admin_dashboard_service()),
) -> Dict[str, Any]:
    """
    Get global dashboard data - admin only.
    Includes aggregated data across all users and sessions.
    """
    logger.info("[Admin] Fetching global dashboard data")
    data = await admin_service.get_global_dashboard_data()
    logger.info("[Admin] Global dashboard data sent")
    return data


@router.get(
    "/admin/dashboard/user/{user_id}",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get detailed user data (admin only)",
    description="Provides detailed statistics for a specific user including sessions, costs, and documents.",
)
async def get_user_detailed_data(
    user_id: str,
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(_resolve_get_admin_dashboard_service()),
) -> Dict[str, Any]:
    """
    Get detailed data for a specific user - admin only.
    """
    logger.info(f"[Admin] Fetching detailed data for user {user_id}")
    data = await admin_service.get_user_detailed_data(user_id)
    logger.info(f"[Admin] User {user_id} detailed data sent")
    return data
