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


async def verify_admin_role(user_role: str = Depends(deps.get_user_role)) -> bool:
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
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
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
    "/admin/dashboard/audits",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get audit reports history (admin only)",
    description="Returns the last N audit reports with timestamps and status.",
)
async def get_audit_history(
    limit: int = 10,
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
) -> Dict[str, Any]:
    """
    Get audit reports history - admin only.
    Returns audit reports from reports/ directory.
    """
    logger.info(f"[Admin] Fetching audit history (limit={limit})")
    data = await admin_service.get_audit_history(limit=limit)
    logger.info(f"[Admin] Audit history sent ({len(data.get('audits', []))} reports)")
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
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
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
    auth_service: Any = Depends(deps.get_auth_service),
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
    "/admin/emails/send",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Send emails to members (admin only)",
    description="Send emails to selected members with specified template type.",
)
async def send_member_emails(
    request: Dict[str, Any],
    _admin_verified: bool = Depends(verify_admin_role),
) -> Dict[str, Any]:
    """
    Send emails to members - admin only.
    Supports different email types: beta_invitation, auth_issue, custom
    """
    from backend.features.auth.email_service import EmailService

    logger.info("[Admin] Sending member emails")

    emails = request.get("emails", [])
    base_url = request.get("base_url", "https://emergence-app.ch")
    email_type = request.get("email_type", "beta_invitation")

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
        "email_type": email_type,
    }

    for email in emails:
        try:
            success = False

            if email_type == "beta_invitation":
                success = await email_service.send_beta_invitation_email(email, base_url)
            elif email_type == "auth_issue":
                success = await email_service.send_auth_issue_notification_email(email, base_url)
            elif email_type == "custom":
                # For custom emails, expect subject and body in request
                subject = request.get("subject", "")
                html_body = request.get("html_body", "")
                text_body = request.get("text_body", "")

                if not subject or not html_body or not text_body:
                    raise HTTPException(
                        status_code=400,
                        detail="Custom emails require subject, html_body, and text_body"
                    )

                success = await email_service.send_custom_email(
                    email, subject, html_body, text_body
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown email type: {email_type}"
                )

            if success:
                results["sent"] += 1
                results["sent_to"].append(email)
                logger.info(f"[Admin] Email ({email_type}) sent to {email}")
            else:
                results["failed"] += 1
                results["failed_emails"].append(email)
                logger.warning(f"[Admin] Failed to send email ({email_type}) to {email}")
        except Exception as e:
            results["failed"] += 1
            results["failed_emails"].append(email)
            logger.error(f"[Admin] Error sending email ({email_type}) to {email}: {e}")

    logger.info(f"[Admin] Emails sent: {results['sent']}/{results['total']} (type: {email_type})")

    return results


# Keep old endpoint for backward compatibility
@router.post(
    "/admin/beta-invitations/send",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Send beta invitations (admin only) - DEPRECATED",
    description="Send beta invitation emails to selected addresses. Use /admin/emails/send instead.",
    deprecated=True,
)
async def send_beta_invitations(
    request: Dict[str, Any],
    _admin_verified: bool = Depends(verify_admin_role),
) -> Dict[str, Any]:
    """
    Send beta invitation emails - admin only.
    DEPRECATED: Use /admin/emails/send with email_type='beta_invitation' instead.
    """
    # Redirect to new endpoint
    request["email_type"] = "beta_invitation"
    return await send_member_emails(request, _admin_verified)


@router.get(
    "/admin/analytics/threads",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get all active threads (admin only)",
    description="Returns all active conversation threads with details for monitoring and management. "
                "Note: This endpoint returns THREADS (conversations), not authentication sessions. "
                "For authentication sessions, use /api/auth/admin/sessions instead.",
)
async def get_active_threads(
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
) -> Dict[str, Any]:
    """
    Get all active threads - admin only.
    Returns thread details including user, device info, IP, and last activity.

    Note: This endpoint returns THREADS (conversations from 'sessions' table),
    not authentication sessions (from 'auth_sessions' table).
    """
    logger.info("[Admin] Fetching active threads")
    threads = await admin_service.get_active_threads()
    logger.info(f"[Admin] Retrieved {len(threads)} active threads")
    return {
        "threads": threads,
        "total": len(threads),
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
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
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
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
) -> Dict[str, Any]:
    """
    Get system metrics - admin only.
    Includes uptime, average latency, error rate, and resource statistics.
    """
    logger.info("[Admin] Fetching system metrics")
    metrics = await admin_service.get_system_metrics()
    logger.info("[Admin] System metrics retrieved")
    return metrics


@router.get(
    "/admin/costs/detailed",
    response_model=Dict[str, Any],
    tags=["Admin Dashboard"],
    summary="Get detailed costs breakdown by user and module (admin only)",
    description="Returns granular cost analysis aggregated by user and feature/module. Fix Phase 1.5.",
)
async def get_detailed_costs_breakdown(
    _admin_verified: bool = Depends(verify_admin_role),
    admin_service: AdminDashboardService = Depends(deps.get_admin_dashboard_service),
) -> Dict[str, Any]:
    """
    Get detailed costs breakdown - admin only.
    Returns costs aggregated by user, with module-level breakdown for each user.
    """
    logger.info("[Admin] Fetching detailed costs breakdown")
    breakdown = await admin_service.get_detailed_costs_breakdown()
    logger.info(f"[Admin] Detailed costs breakdown retrieved: {breakdown.get('total_users', 0)} users")
    return breakdown
