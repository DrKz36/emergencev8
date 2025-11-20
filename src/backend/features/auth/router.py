from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.features.auth.models import (
    AllowlistCreatePayload,
    AllowlistListResponse,
    AllowlistMutationResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    DevLoginRequest,
    LoginResponse,
    LogoutPayload,
    RequestPasswordResetRequest,
    RequestPasswordResetResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SessionRevokePayload,
    SessionRevokeResult,
    SessionStatusResponse,
    SessionsListResponse,
)
from backend.features.auth.service import AuthError, AuthService
from backend.features.auth.email_service import EmailService
from backend.core.session_manager import SessionManager
from backend.shared.dependencies import (
    get_auth_service,
    get_auth_claims,
    get_auth_claims_allow_revoked,
    get_session_manager_optional,
    require_admin_claims,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

PASSWORD_DEFAULT_LENGTH = 16
PASSWORD_SYMBOLS = "!@#$%_-+"
PASSWORD_ALPHABET = string.ascii_letters + string.digits + PASSWORD_SYMBOLS


def _generate_password(length: int = PASSWORD_DEFAULT_LENGTH) -> str:
    if length < 8:
        length = 8
    while True:
        candidate = "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
            and any(c in PASSWORD_SYMBOLS for c in candidate)
        ):
            return candidate


def _map_auth_error(exc: AuthError) -> HTTPException:
    headers: Dict[str, str] = {}
    retry_after = None
    if exc.payload:
        retry_after = exc.payload.get("retry_after")
    if retry_after is not None:
        try:
            headers["Retry-After"] = str(int(float(retry_after)))
        except (TypeError, ValueError):
            pass
    detail = str(exc) or "Erreur d'authentification."
    return HTTPException(
        status_code=exc.status_code, detail=detail, headers=headers or None
    )


def _set_blank_cookie(response: Response, key: str, *, secure: bool) -> None:
    """Expire cookie immediately while keeping logout semantics explicit."""
    expires_at = datetime.fromtimestamp(0, tz=timezone.utc)
    response.set_cookie(
        key=key,
        value="",
        max_age=0,
        expires=expires_at,
        path="/",
        secure=secure,
        httponly=False,
        samesite="lax",
    )


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    try:
        login_result = await auth_service.login(
            payload.email,
            payload.password,
            client_host,
            user_agent,
        )
    except AuthError as exc:
        raise _map_auth_error(exc)

    max_age = int(auth_service.config.token_ttl_seconds)
    cookie_secure = not bool(getattr(auth_service.config, "dev_mode", False))
    response.set_cookie(
        key="id_token",
        value=login_result.token,
        max_age=max_age,
        expires=login_result.expires_at,
        path="/",
        secure=cookie_secure,
        httponly=False,
        samesite="lax",
    )
    response.set_cookie(
        key="emergence_session_id",
        value=login_result.session_id,
        max_age=max_age,
        expires=login_result.expires_at,
        path="/",
        secure=cookie_secure,
        httponly=False,
        samesite="lax",
    )
    return login_result


@router.post("/dev/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def dev_login(
    request: Request,
    response: Response,
    payload: Optional[DevLoginRequest] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    if not getattr(auth_service.config, "dev_mode", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    client_host = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    email = payload.email if payload else None

    try:
        login_result = await auth_service.dev_login(email, client_host, user_agent)
    except AuthError as exc:
        raise _map_auth_error(exc)

    max_age = int(auth_service.config.token_ttl_seconds)
    cookie_secure = not bool(getattr(auth_service.config, "dev_mode", False))
    response.set_cookie(
        key="id_token",
        value=login_result.token,
        max_age=max_age,
        expires=login_result.expires_at,
        path="/",
        secure=cookie_secure,
        httponly=False,
        samesite="lax",
    )
    response.set_cookie(
        key="emergence_session_id",
        value=login_result.session_id,
        max_age=max_age,
        expires=login_result.expires_at,
        path="/",
        secure=cookie_secure,
        httponly=False,
        samesite="lax",
    )
    return login_result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutPayload,
    claims: Dict[str, Any] = Depends(get_auth_claims_allow_revoked),
    auth_service: AuthService = Depends(get_auth_service),
    session_manager: Optional[SessionManager] = Depends(get_session_manager_optional),
) -> Response:
    session_id = payload.session_id or claims.get("session_id") or claims.get("sid")
    actor = claims.get("email")
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if session_id:
        sid = str(session_id)
        await auth_service.logout(sid, actor=actor)
        if session_manager:
            await session_manager.handle_session_revocation(
                sid,
                reason="session_revoked",
                close_code=4401,
            )
    cookie_secure = not bool(getattr(auth_service.config, "dev_mode", False))
    _set_blank_cookie(response, "id_token", secure=cookie_secure)
    _set_blank_cookie(response, "emergence_session_id", secure=cookie_secure)
    return response


@router.get("/session", response_model=SessionStatusResponse)
async def get_session(
    claims: Dict[str, Any] = Depends(get_auth_claims),
) -> SessionStatusResponse:
    email = str(claims.get("email") or "")
    role = str(claims.get("role") or "member")
    expires_at = claims.get("expires_at")
    if not isinstance(expires_at, datetime):
        exp_val = claims.get("exp")
        expires_at = (
            datetime.fromtimestamp(int(exp_val), tz=timezone.utc)
            if exp_val
            else datetime.fromtimestamp(0, tz=timezone.utc)
        )
    issued_raw = claims.get("iat")
    issued_at = (
        datetime.fromtimestamp(int(issued_raw), tz=timezone.utc)
        if issued_raw
        else datetime.fromtimestamp(0, tz=timezone.utc)
    )
    session_id = str(claims.get("session_id") or claims.get("sid") or "")
    source = str(claims.get("_auth_source") or "") or None
    return SessionStatusResponse(
        email=email,
        role=role,
        expires_at=expires_at,
        issued_at=issued_at,
        session_id=session_id,
        source=source,
    )


@router.get("/my-sessions", response_model=SessionsListResponse)
async def list_my_sessions(
    claims: Dict[str, Any] = Depends(get_auth_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionsListResponse:
    """
    List all active sessions for the authenticated user.
    Phase P2 - Feature 8: Gestion Multi-Sessions
    """
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found in token"
        )

    # Get user ID from auth service
    user = await auth_service.get_user_by_email(email)  # type: ignore[attr-defined]
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Get sessions for this specific user only
    all_sessions = await auth_service.list_sessions(active_only=True)
    user_sessions = [s for s in all_sessions if s.user_id == user.id]

    return SessionsListResponse(items=user_sessions)


@router.post("/my-sessions/{session_id}/revoke", response_model=SessionRevokeResult)
async def revoke_my_session(
    session_id: str,
    claims: Dict[str, Any] = Depends(get_auth_claims),
    auth_service: AuthService = Depends(get_auth_service),
    session_manager: Optional[SessionManager] = Depends(get_session_manager_optional),
) -> SessionRevokeResult:
    """
    Revoke one of the authenticated user's sessions.
    User can only revoke their own sessions.
    Phase P2 - Feature 8: Gestion Multi-Sessions
    """
    email = claims.get("email")
    current_session_id = claims.get("session_id") or claims.get("sid")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found in token"
        )

    # Prevent revoking current session (user should logout instead)
    if session_id == current_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke current session. Use /logout instead.",
        )

    # Get user ID
    user = await auth_service.get_user_by_email(email)  # type: ignore[attr-defined]
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Verify session belongs to user before revoking
    all_sessions = await auth_service.list_sessions(active_only=True)
    target_session = next((s for s in all_sessions if s.id == session_id), None)

    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if target_session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only revoke your own sessions",
        )

    # Revoke session
    updated = await auth_service.revoke_session(session_id, actor=email)

    # Notify session manager (close WebSocket if active)
    if updated and session_manager:
        await session_manager.handle_session_revocation(
            session_id,
            reason="user_revoke",
            close_code=4401,
        )

    return SessionRevokeResult(updated=1 if updated else 0)


# =========================================================================
# 2FA / TOTP ENDPOINTS (Phase P2 - Feature 9)
# =========================================================================


@router.post("/2fa/enable")
async def enable_2fa_endpoint(
    claims: Dict[str, Any] = Depends(get_auth_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """
    Initiate 2FA setup by generating TOTP secret and backup codes.
    Returns QR code and secret for authenticator app.
    Phase P2 - Feature 9: Authentification 2FA
    """
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found in token"
        )

    try:
        result = await auth_service.enable_2fa(email)
        return result
    except AuthError as exc:
        raise _map_auth_error(exc)


@router.post("/2fa/verify")
async def verify_and_enable_2fa_endpoint(
    payload: Dict[str, str],
    claims: Dict[str, Any] = Depends(get_auth_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """
    Verify TOTP code and enable 2FA for the user.
    Requires 6-digit code from authenticator app.
    Phase P2 - Feature 9: Authentification 2FA
    """
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found in token"
        )

    totp_code = payload.get("code", "").strip()
    if not totp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP code is required"
        )

    try:
        success = await auth_service.verify_and_enable_2fa(email, totp_code)
        if success:
            return {"success": True, "message": "2FA enabled successfully"}
        else:
            return {"success": False, "message": "Invalid TOTP code"}
    except AuthError as exc:
        raise _map_auth_error(exc)


@router.post("/2fa/disable")
async def disable_2fa_endpoint(
    payload: Dict[str, str],
    claims: Dict[str, Any] = Depends(get_auth_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """
    Disable 2FA for the user (requires password confirmation).
    Phase P2 - Feature 9: Authentification 2FA
    """
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found in token"
        )

    password = payload.get("password", "").strip()
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required to disable 2FA",
        )

    try:
        success = await auth_service.disable_2fa(email, password)
        if success:
            return {"success": True, "message": "2FA disabled successfully"}
        else:
            return {"success": False, "message": "Failed to disable 2FA"}
    except AuthError as exc:
        raise _map_auth_error(exc)


@router.get("/2fa/status")
async def get_2fa_status_endpoint(
    claims: Dict[str, Any] = Depends(get_auth_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """
    Get 2FA status for the authenticated user.
    Phase P2 - Feature 9: Authentification 2FA
    """
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not found in token"
        )

    try:
        status_info = await auth_service.get_2fa_status(email)
        return status_info
    except AuthError as exc:
        raise _map_auth_error(exc)


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    payload: ChangePasswordRequest,
    claims: Dict[str, Any] = Depends(get_auth_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> ChangePasswordResponse:
    """Change password for the authenticated user."""
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email non trouve dans le token.",
        )

    try:
        await auth_service.change_own_password(
            email,
            payload.current_password,
            payload.new_password,
        )
        return ChangePasswordResponse(
            success=True, message="Mot de passe change avec succes."
        )
    except AuthError as exc:
        raise _map_auth_error(exc)


@router.post("/request-password-reset", response_model=RequestPasswordResetResponse)
async def request_password_reset(
    payload: RequestPasswordResetRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> RequestPasswordResetResponse:
    """Request a password reset email."""
    try:
        # Create reset token
        token = await auth_service.create_password_reset_token(payload.email)

        # Send email
        email_service = EmailService()
        if email_service.is_enabled():
            # Get base URL from request
            base_url = str(request.base_url).rstrip("/")

            # Send email
            email_sent = await email_service.send_password_reset_email(
                to_email=payload.email,
                reset_token=token,
                base_url=base_url,
            )

            if not email_sent:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Erreur lors de l'envoi de l'email. Veuillez contacter l'administrateur.",
                )
        else:
            # Email service not configured - for development, log the token
            import logging

            logger = logging.getLogger("emergence.auth")
            logger.warning(
                f"Email service not configured. Reset token for {payload.email}: {token}"
            )
            logger.warning(
                f"Reset URL: {str(request.base_url).rstrip('/')}/reset-password?token={token}"
            )

        return RequestPasswordResetResponse(
            success=True,
            message="Si votre email est enregistré, vous recevrez un lien de réinitialisation sous peu.",
        )
    except AuthError:
        # For security, always return success message even if email not found
        # This prevents email enumeration
        return RequestPasswordResetResponse(
            success=True,
            message="Si votre email est enregistré, vous recevrez un lien de réinitialisation sous peu.",
        )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ResetPasswordResponse:
    """Reset password using a valid token."""
    try:
        await auth_service.reset_password_with_token(
            payload.token,
            payload.new_password,
        )
        return ResetPasswordResponse(
            success=True,
            message="Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter.",
        )
    except AuthError as exc:
        raise _map_auth_error(exc)


@router.get("/admin/allowlist", response_model=AllowlistListResponse)
async def list_allowlist(
    include_revoked: Optional[bool] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    _claims: Dict[str, Any] = Depends(require_admin_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> AllowlistListResponse:
    normalized_status = (status or "").strip().lower()
    if include_revoked:
        normalized_status = "all"
    if normalized_status not in {"active", "revoked", "all"}:
        normalized_status = "active"

    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1

    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 20
    page_size = max(1, min(page_size, 100))

    offset = (page - 1) * page_size
    query_value = (search or "").strip()

    items, total = await auth_service.list_allowlist(
        status=normalized_status,
        search=query_value or None,
        limit=page_size,
        offset=offset,
    )
    has_more = offset + len(items) < total

    return AllowlistListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
        status=normalized_status,
        query=query_value or None,
    )


@router.post(
    "/admin/allowlist",
    response_model=AllowlistMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upsert_allowlist(
    payload: AllowlistCreatePayload,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> AllowlistMutationResponse:
    if payload.generate_password and payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ne pas fournir 'password' lorsque 'generate_password' est actif.",
        )

    clear_password: Optional[str] = None
    password_value = payload.password
    if payload.generate_password:
        clear_password = _generate_password()
        password_value = clear_password
    elif isinstance(password_value, str):
        password_value = password_value.strip()

    try:
        entry = await auth_service.upsert_allowlist(
            payload.email,
            payload.role,
            payload.note,
            actor=claims.get("email"),
            password=password_value,
            password_generated=bool(payload.generate_password),
        )
    except AuthError as exc:
        raise _map_auth_error(exc)

    if clear_password is not None:
        clear_password = clear_password.strip()

    return AllowlistMutationResponse(
        entry=entry, clear_password=clear_password, generated=bool(clear_password)
    )


@router.delete("/admin/allowlist/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_allowlist(
    email: str,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.remove_allowlist(email, actor=claims.get("email"))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/sessions", response_model=SessionsListResponse)
async def list_sessions(
    status_filter: Optional[str] = None,
    _claims: Dict[str, Any] = Depends(require_admin_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionsListResponse:
    active_only = status_filter == "active"
    items = await auth_service.list_sessions(active_only=active_only)
    return SessionsListResponse(items=items)


@router.post("/admin/sessions/revoke", response_model=SessionRevokeResult)
async def revoke_session(
    payload: SessionRevokePayload,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    auth_service: AuthService = Depends(get_auth_service),
    session_manager: Optional[SessionManager] = Depends(get_session_manager_optional),
) -> SessionRevokeResult:
    updated = await auth_service.revoke_session(
        payload.session_id, actor=claims.get("email")
    )
    if updated and session_manager:
        await session_manager.handle_session_revocation(
            payload.session_id,
            reason="admin_revoke",
            close_code=4401,
        )
    return SessionRevokeResult(updated=1 if updated else 0)
