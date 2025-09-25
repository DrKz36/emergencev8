from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.features.auth.models import (
    AllowlistCreatePayload,
    AllowlistEntry,
    AllowlistListResponse,
    AllowlistMutationResponse,
    LoginRequest,
    LoginResponse,
    LogoutPayload,
    SessionRevokePayload,
    SessionRevokeResult,
    SessionStatusResponse,
    SessionsListResponse,
)
from backend.features.auth.service import AuthError, AuthService
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
        candidate = ''.join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))
        if (any(c.islower() for c in candidate)
                and any(c.isupper() for c in candidate)
                and any(c.isdigit() for c in candidate)
                and any(c in PASSWORD_SYMBOLS for c in candidate)):
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
    return HTTPException(status_code=exc.status_code, detail=detail, headers=headers or None)


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
        login_result = await auth_service.login(payload.email, payload.password, client_host, user_agent)
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
async def get_session(claims: Dict[str, Any] = Depends(get_auth_claims)) -> SessionStatusResponse:
    email = str(claims.get("email") or "")
    role = str(claims.get("role") or "member")
    expires_at = claims.get("expires_at")
    if not isinstance(expires_at, datetime):
        exp_val = claims.get("exp")
        expires_at = datetime.fromtimestamp(int(exp_val), tz=timezone.utc) if exp_val else datetime.fromtimestamp(0, tz=timezone.utc)
    issued_raw = claims.get("iat")
    issued_at = datetime.fromtimestamp(int(issued_raw), tz=timezone.utc) if issued_raw else datetime.fromtimestamp(0, tz=timezone.utc)
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


@router.post("/admin/allowlist", response_model=AllowlistMutationResponse, status_code=status.HTTP_201_CREATED)
async def upsert_allowlist(
    payload: AllowlistCreatePayload,
    claims: Dict[str, Any] = Depends(require_admin_claims),
    auth_service: AuthService = Depends(get_auth_service),
) -> AllowlistMutationResponse:
    if payload.generate_password and payload.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ne pas fournir 'password' lorsque 'generate_password' est actif.")

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

    return AllowlistMutationResponse(entry=entry, clear_password=clear_password, generated=bool(clear_password))


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
    updated = await auth_service.revoke_session(payload.session_id, actor=claims.get("email"))
    if updated and session_manager:
        await session_manager.handle_session_revocation(
            payload.session_id,
            reason="admin_revoke",
            close_code=4401,
        )
    return SessionRevokeResult(updated=1 if updated else 0)




