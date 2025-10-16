# src/backend/features/dashboard/admin_router.py
"""
Admin Dashboard Router - Endpoints for global statistics
V1.0 - Admin-only access to global data
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
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


@router.get(
    "/admin/allowlist/emails",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get all allowlist emails (admin only)",
    description="Returns all emails from the allowlist for beta invitation purposes.",
)
async def get_allowlist_emails(
    _admin_verified: bool = Depends(verify_admin_role),
    auth_service = Depends(deps.get_auth_service),
) -> Dict[str, Any]:
    """
    Get all allowlist emails - admin only.
    Returns a list of all active emails in the allowlist.
    """
    logger.info("[Admin] Fetching allowlist emails")

    # Get all active allowlist entries
    entries, total = await auth_service.list_allowlist(status="active", limit=1000)

    emails = [entry.email for entry in entries if entry.email]

    logger.info(f"[Admin] Retrieved {len(emails)} allowlist emails")
    return {
        "emails": emails,
        "total": len(emails),
    }


@router.post(
    "/admin/beta-invitations/send",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Send beta invitations (admin only)",
    description="Send beta invitation emails to selected addresses.",
)
async def send_beta_invitations(
    request: Dict[str, Any],
    _admin_verified: bool = Depends(verify_admin_role),
) -> Dict[str, Any]:
    """
    Send beta invitation emails - admin only.
    """
    from backend.features.auth.email_service import EmailService

    logger.info("[Admin] Sending beta invitations")

    emails = request.get("emails", [])
    base_url = request.get("base_url", "https://emergence-app.ch")

    if not emails or not isinstance(emails, list):
        raise HTTPException(status_code=400, detail="emails must be a non-empty list")

    email_service = EmailService()

    if not email_service.is_enabled():
        raise HTTPException(status_code=503, detail="Email service is not configured")

    results = {
        "total": len(emails),
        "sent": 0,
        "failed": 0,
        "sent_to": [],
        "failed_emails": [],
    }

    for email in emails:
        try:
            success = await email_service.send_beta_invitation_email(email, base_url)
            if success:
                results["sent"] += 1
                results["sent_to"].append(email)
                logger.info(f"[Admin] Beta invitation sent to {email}")
            else:
                results["failed"] += 1
                results["failed_emails"].append(email)
                logger.warning(f"[Admin] Failed to send beta invitation to {email}")
        except Exception as e:
            results["failed"] += 1
            results["failed_emails"].append(email)
            logger.error(f"[Admin] Error sending beta invitation to {email}: {e}")

    logger.info(f"[Admin] Beta invitations sent: {results['sent']}/{results['total']}")

    return results


@router.get(
    "/admin/analytics/sessions",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get all active sessions (admin only)",
    description="Returns all active user sessions with details for monitoring and management.",
)
async def get_active_sessions(
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(_resolve_get_admin_dashboard_service()),
) -> Dict[str, Any]:
    """
    Get all active sessions - admin only.
    Returns session details including user, device info, IP, and last activity.
    """
    logger.info("[Admin] Fetching active sessions")
    sessions = await admin_service.get_active_sessions()
    logger.info(f"[Admin] Retrieved {len(sessions)} active sessions")
    return {
        "sessions": sessions,
        "total": len(sessions),
    }


@router.post(
    "/admin/sessions/{session_id}/revoke",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Revoke a user session (admin only)",
    description="Forcefully revokes a user session, logging them out immediately.",
)
async def revoke_session(
    session_id: str,
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(_resolve_get_admin_dashboard_service()),
) -> Dict[str, Any]:
    """
    Revoke a session - admin only.
    """
    logger.info(f"[Admin] Revoking session {session_id}")
    success = await admin_service.revoke_session(session_id)
    if success:
        logger.info(f"[Admin] Session {session_id} revoked successfully")
        return {
            "success": True,
            "message": f"Session {session_id} revoked successfully",
        }
    else:
        logger.warning(f"[Admin] Failed to revoke session {session_id}")
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@router.get(
    "/admin/metrics/system",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get system metrics (admin only)",
    description="Returns system health metrics including uptime, latency, error rates, and resource usage.",
)
async def get_system_metrics(
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(_resolve_get_admin_dashboard_service()),
) -> Dict[str, Any]:
    """
    Get system metrics - admin only.
    Includes uptime, average latency, error rate, and resource statistics.
    """
    logger.info("[Admin] Fetching system metrics")
    metrics = await admin_service.get_system_metrics()
    logger.info("[Admin] System metrics retrieved")
    return metrics
