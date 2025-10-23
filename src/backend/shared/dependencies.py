# src/backend/shared/dependencies.py
# V8.0 - Local JWT auth (email/password) + dev bypass + WS token helpers
from __future__ import annotations

import os
import json
import base64
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Optional, Any, Dict

from fastapi import Request, HTTPException, Query
from fastapi import WebSocket

logger = logging.getLogger("emergence.allowlist")


if TYPE_CHECKING:
    from backend.features.auth.service import AuthService
    from backend.core.session_manager import SessionManager

@dataclass(frozen=True)
class SessionContext:
    session_id: str
    user_id: Optional[str]
    email: Optional[str]
    role: Optional[str]
    claims: Dict[str, Any]


def _normalize_identifier(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def _extract_session_id_from_claims(claims: Dict[str, Any]) -> Optional[str]:
    for key in ("session_id", "sid", "sessionId"):
        candidate = _normalize_identifier(claims.get(key))
        if candidate:
            return candidate
    return None


def _resolve_session_id_from_request(request: Request) -> Optional[str]:
    for candidate in (
        request.headers.get("X-Session-Id"),
        request.headers.get("X-Session-ID"),
        request.headers.get("x-session-id"),
        request.query_params.get("session_id"),
        request.query_params.get("sessionId"),
        getattr(request.state, "session_id", None),
    ):
        normalized = _normalize_identifier(candidate)
        if normalized:
            return normalized
    return None


async def _resolve_user_id_from_session(session_id: Optional[str], scope_holder: Any) -> Optional[str]:
    normalized = _normalize_identifier(session_id)
    if not normalized:
        return None
    auth_service = _maybe_get_auth_service(scope_holder)
    if auth_service is None:
        return None
    try:
        resolved = await auth_service.get_user_id_for_session(normalized)
    except Exception as exc:  # pragma: no cover - logging only
        logger.debug("Resolution user_id via session %s impossible: %s", normalized, exc)
        return None
    return _normalize_identifier(resolved)


async def _ensure_user_id_in_claims(claims: Dict[str, Any], scope_holder: Any) -> Optional[str]:
    user_candidate = _normalize_identifier(claims.get("sub") or claims.get("user_id"))
    if user_candidate:
        claims.setdefault("sub", user_candidate)
        claims.setdefault("user_id", user_candidate)
        return user_candidate
    session_candidate = _normalize_identifier(
        claims.get("session_id") or claims.get("sid") or claims.get("sessionId")
    )
    if not session_candidate:
        return None
    resolved = await _resolve_user_id_from_session(session_candidate, scope_holder)
    if resolved:
        claims["sub"] = resolved
        claims.setdefault("user_id", resolved)
        return resolved
    return None


# -----------------------------
# Helpers JWT
# -----------------------------
def _try_json(s: str) -> dict[str, Any]:
    try:
        return json.loads(s)
    except Exception:
        return {}

def _read_bearer_claims_from_token(token: str) -> dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("not-a-jwt")
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8", "ignore"))
        return claims if isinstance(claims, dict) else {}
    except Exception:
        return {}

def _read_bearer_claims(request: Request) -> dict[str, Any]:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer requis.")
    token = auth.split(" ", 1)[1].strip()
    return _read_bearer_claims_from_token(token)

_jwt_like = re.compile(r"^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$")

def _looks_like_jwt(s: str) -> bool:
    return bool(_jwt_like.fullmatch(s or ""))

_DEV_BYPASS_TRUTHY = {"1", "true", "yes", "on", "enable"}


def _is_global_dev_mode(scope_holder: Any) -> bool:
    auth_service = _maybe_get_auth_service(scope_holder)
    if auth_service is not None:
        try:
            if bool(getattr(getattr(auth_service, "config", None), "dev_mode", False)):
                return True
        except Exception:
            pass
    env_flag = (os.getenv("AUTH_DEV_MODE") or "0").strip().lower()
    return env_flag in _DEV_BYPASS_TRUTHY


def _has_dev_bypass(headers: Any) -> bool:
    try:
        if not headers:
            return False
        val = headers.get('x-dev-bypass') or headers.get('X-Dev-Bypass')
        return bool(val) and str(val).strip().lower() in _DEV_BYPASS_TRUTHY
    except Exception:
        return False


def _has_dev_bypass_query(params: Any) -> bool:
    try:
        if not params:
            return False
        val = params.get('dev_bypass')
        return bool(val) and str(val).strip().lower() in _DEV_BYPASS_TRUTHY
    except Exception:
        return False



def _maybe_get_auth_service(scope_holder: Any) -> Optional["AuthService"]:
    try:
        app = scope_holder.app
    except AttributeError:
        app = getattr(scope_holder, "app", None)
    if app is None:
        return None
    state = getattr(app, "state", None)
    container = getattr(state, "service_container", None)
    if container is None:
        return None
    getter = getattr(container, "auth_service", None)
    if getter is None:
        return None
    try:
        return getter()
    except Exception as exc:
        logger.debug("AuthService indisponible: %s", exc)
        return None

def _extract_bearer_token_from_header(auth_header: Optional[str]) -> str:
    if not auth_header:
        return ""
    parts = auth_header.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


def _extract_token_from_request(request: Request) -> str:
    token = _extract_bearer_token_from_header(request.headers.get("Authorization"))
    if token:
        return token

    cookie_candidates: list[str | None] = []
    try:
        cookie_candidates.extend(
            [
                request.cookies.get("id_token"),
                request.cookies.get("access_token"),
                request.cookies.get("token"),
            ]
        )
    except Exception:
        pass

    for raw in cookie_candidates:
        normalized = _normalize_bearer_value(raw) if isinstance(raw, str) else None
        if normalized and _looks_like_jwt(normalized):
            return normalized

    query_candidates: list[str] = []
    try:
        qp = request.query_params
        if qp:
            for key in ("token", "auth", "access_token", "id_token"):
                value = qp.get(key)
                if value:
                    query_candidates.append(str(value))
    except Exception:
        pass

    for raw in query_candidates:
        normalized = _normalize_bearer_value(raw)
        if normalized and _looks_like_jwt(normalized):
            return normalized

    return ""

async def _resolve_token_claims(token: str, scope_holder: Any, *, allow_revoked: bool = False) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="ID token invalide ou absent.")
    auth_service = _maybe_get_auth_service(scope_holder)
    if auth_service is None:
        raise HTTPException(status_code=503, detail="AuthService indisponible.")
    try:
        verified = await auth_service.verify_token(token, allow_revoked=allow_revoked)
    except Exception as exc:
        status = getattr(exc, "status_code", 401)
        message = str(exc) or "Token invalide."
        raise HTTPException(status_code=status, detail=message) from exc
    verified_dict = dict(verified)
    verified_dict.setdefault("_auth_source", "local")
    verified_dict["_raw_token"] = token
    return verified_dict

async def _get_claims_from_request(request: Request, *, allow_revoked: bool = False) -> Dict[str, Any]:
    cache_key = "auth_claims_allow_revoked" if allow_revoked else "auth_claims"
    cached = getattr(request.state, cache_key, None)
    if isinstance(cached, dict):
        return cached
    token = _extract_token_from_request(request)
    claims = await _resolve_token_claims(token, request, allow_revoked=allow_revoked)
    setattr(request.state, cache_key, claims)
    if allow_revoked and not isinstance(getattr(request.state, "auth_claims", None), dict):
        setattr(request.state, "auth_claims", claims)
    return claims

async def _get_claims_from_ws(ws: WebSocket) -> Dict[str, Any]:
    cached = getattr(ws.state, "auth_claims", None)
    if isinstance(cached, dict):
        return cached
    token_raw = _get_ws_token_from_headers(ws)
    token = _normalize_bearer_value(token_raw) if isinstance(token_raw, str) else token_raw
    token_str = str(token) if token is not None else ""
    if not token_str or not _looks_like_jwt(token_str):
        raise HTTPException(status_code=401, detail="WS: token absent (Authorization/subprotocol/cookie/query).")
    claims = await _resolve_token_claims(token_str, ws)
    setattr(ws.state, "auth_claims", claims)
    return claims

def _is_admin_claims(claims: Dict[str, Any], auth_service: Optional["AuthService"]) -> bool:
    role = str(claims.get("role") or "").lower()
    if claims.get("_auth_source") == "local":
        return role == "admin"
    email = str(claims.get("email") or "").lower().strip()
    if not email or auth_service is None:
        return False
    try:
        return email in getattr(auth_service, "config").admin_emails
    except Exception:
        return False
# -----------------------------
# WebSocket token helpers
# -----------------------------
def _normalize_bearer_value(value: str) -> str:
    if not value:
        return ""
    candidate = str(value).strip()
    if not candidate:
        return ""
    lower = candidate.lower()
    if lower.startswith("bearer "):
        return candidate[7:].strip()
    if lower.startswith("token="):
        return candidate.split("=", 1)[1].strip()
    if lower.startswith("jwt "):
        return candidate.split(" ", 1)[1].strip()
    return candidate


def _iter_ws_protocol_candidates(ws: WebSocket) -> Any:
    try:
        scope_protocols = ws.scope.get("subprotocols") if isinstance(ws.scope, dict) else None
        if scope_protocols:
            for item in scope_protocols:
                if item:
                    yield str(item)
    except Exception:
        pass
    try:
        header_value = ws.headers.get("sec-websocket-protocol")
        if header_value:
            for part in header_value.split(","):
                part = part.strip()
                if part:
                    yield part
    except Exception:
        pass


def _get_ws_token_from_headers(ws: WebSocket) -> Optional[str]:
    candidates: list[str] = []

    try:
        auth_header = ws.headers.get("authorization") or ws.headers.get("Authorization")
        if auth_header:
            candidates.append(auth_header)
    except Exception:
        pass

    candidates.extend(_iter_ws_protocol_candidates(ws))

    try:
        qp_token = ws.query_params.get("token") or ws.query_params.get("auth") or ws.query_params.get("access_token")
        if qp_token:
            candidates.append(qp_token)
    except Exception:
        pass

    try:
        cookie_token = ws.cookies.get("token") or ws.cookies.get("id_token") or ws.cookies.get("access_token")
        if cookie_token:
            candidates.append(cookie_token)
    except Exception:
        pass

    normalized: list[str] = []
    for raw in candidates:
        norm = _normalize_bearer_value(str(raw))
        if not norm:
            continue
        lower = norm.lower()
        if lower in {"jwt", "bearer"}:
            continue
        normalized.append(norm)

    for token in normalized:
        if _looks_like_jwt(token):
            return token

    return normalized[0] if normalized else None


def _extract_ws_bearer_token(ws: WebSocket) -> Optional[str]:
    token = _get_ws_token_from_headers(ws)
    if token and _looks_like_jwt(token):
        return token
    return None

# -----------------------------
# REST
# -----------------------------
async def get_session_context(request: Request) -> SessionContext:
    dev_bypass = _has_dev_bypass(request.headers)
    dev_mode = dev_bypass or _is_global_dev_mode(request)
    try:
        claims = await _get_claims_from_request(request)
    except HTTPException:
        if dev_mode:
            fallback_sid = _resolve_session_id_from_request(request)
            if not fallback_sid:
                fallback_sid = _normalize_identifier(request.headers.get("X-User-ID") or request.headers.get("X-User-Id")) or "dev-session"
            raw_user_id = _normalize_identifier(request.headers.get("X-User-ID") or request.headers.get("X-User-Id"))
            email = _normalize_identifier(request.headers.get("X-User-Email"))
            role_value = _normalize_identifier(request.headers.get("X-User-Role")) or "admin"
            claims = {"_auth_source": "bypass", "session_id": fallback_sid}
            resolved_user_id = raw_user_id or await _resolve_user_id_from_session(fallback_sid, request)
            if resolved_user_id:
                claims.setdefault("sub", resolved_user_id)
                claims.setdefault("user_id", resolved_user_id)
            if email:
                claims.setdefault("email", email)
            if role_value:
                claims.setdefault("role", role_value)
            return SessionContext(
                session_id=fallback_sid,
                user_id=resolved_user_id,
                email=email,
                role=role_value,
                claims=claims,
            )
        raise

    session_id = _extract_session_id_from_claims(claims)
    if not session_id and dev_mode:
        session_id = _resolve_session_id_from_request(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID manquant ou invalide.")

    claims.setdefault("session_id", session_id)
    user_id = await _ensure_user_id_in_claims(claims, request)
    email = _normalize_identifier(claims.get("email"))
    role_claim = _normalize_identifier(claims.get("role"))
    return SessionContext(
        session_id=session_id,
        user_id=user_id,
        email=email,
        role=role_claim,
        claims=claims,
    )


async def get_session_id(request: Request) -> str:
    return (await get_session_context(request)).session_id



async def enforce_allowlist(request: Request) -> None:
    if _has_dev_bypass(request.headers):
        logger.debug("Allowlist bypass via X-Dev-Bypass header.")
        return
    auth_service = _maybe_get_auth_service(request)
    if auth_service is None:
        raise HTTPException(status_code=503, detail="AuthService indisponible.")
    token_present = bool(_extract_bearer_token_from_header(request.headers.get("Authorization")))
    if token_present:
        await _get_claims_from_request(request)
        return
    if _is_global_dev_mode(request):
        return
    raise HTTPException(status_code=401, detail="Authorization Bearer requis.")

async def get_user_id_optional(request: Request) -> Optional[str]:
    """Retourne user_id ou None en mode dev (pour les dashboards)."""
    dev_bypass = _has_dev_bypass(request.headers)
    token = _extract_bearer_token_from_header(request.headers.get("Authorization"))

    if token:
        try:
            claims = await _get_claims_from_request(request)
            resolved_user_id = await _ensure_user_id_in_claims(claims, request)
            if resolved_user_id:
                return resolved_user_id
        except HTTPException:
            pass  # Continue to dev mode checks

    if dev_bypass or _is_global_dev_mode(request):
        hdr = request.headers.get("X-User-ID") or request.headers.get("X-User-Id")
        if hdr:
            logger.warning("DevMode: fallback X-User-ID used")
            return hdr
        # En mode dev, retourner None si aucun user_id n'est fourni
        return None

    raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")

async def get_user_id(request: Request) -> str:
    dev_bypass = _has_dev_bypass(request.headers)
    token = _extract_bearer_token_from_header(request.headers.get("Authorization"))

    if token:
        claims = await _get_claims_from_request(request)
        resolved_user_id = await _ensure_user_id_in_claims(claims, request)
        if resolved_user_id:
            return resolved_user_id
        if dev_bypass or _is_global_dev_mode(request):
            hdr = request.headers.get("X-User-ID") or request.headers.get("X-User-Id")
            if hdr:
                logger.warning("DevMode: fallback X-User-ID used because JWT has no 'sub'.")
                return hdr
        raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")

    if dev_bypass or _is_global_dev_mode(request):
        hdr = request.headers.get("X-User-ID") or request.headers.get("X-User-Id")
        if hdr:
            logger.warning("DevMode: fallback X-User-ID used with no Authorization header.")
            return hdr

    raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")

async def get_user_id_for_ws(ws: WebSocket, user_id: Optional[str] = Query(default=None)) -> str:
    """
    Retourne l'user_id à partir d'un JWT trouvé dans le handshake WS.
    En DEV (AUTH_DEV_MODE=1) peut accepter user_id explicite si aucun token.
    """
    dev_bypass = _has_dev_bypass(ws.headers) or _has_dev_bypass_query(ws.query_params)
    dev_mode = _is_global_dev_mode(ws)

    try:
        claims = await _get_claims_from_ws(ws)
    except HTTPException:
        if dev_mode or dev_bypass:
            fallback = user_id or ws.query_params.get('user_id')
            if fallback:
                logger.warning("DevMode WS: fallback user_id utilisé (pas de token).")
                return str(fallback)
        raise

    resolved_user_id = await _ensure_user_id_in_claims(claims, ws)
    if resolved_user_id:
        return resolved_user_id
    if dev_mode or dev_bypass:
        fallback = user_id or ws.query_params.get('user_id')
        if fallback:
            logger.warning("DevMode WS: fallback user_id utilisé (token sans 'sub').")
            return str(fallback)
    raise HTTPException(status_code=401, detail="WS: token sans 'sub'.")
async def get_user_id_from_websocket(ws: WebSocket, user_id: Optional[str] = Query(default=None)) -> str:
    return await get_user_id_for_ws(ws, user_id)

# -----------------------------
# DI getters (Dashboard & Documents) — sans import containers
# -----------------------------
# NB: pas d'import de ServiceContainer ici (évite les cycles).
# On récupère le conteneur déjà instancié via request.app.state.service_container

async def get_auth_service(request: Request):
    service = _maybe_get_auth_service(request)
    if service is None:
        raise HTTPException(status_code=503, detail="AuthService indisponible.")
    return service

async def get_auth_claims(request: Request) -> Dict[str, Any]:
    if _has_dev_bypass(request.headers):
        email = request.headers.get("X-User-Email") or request.headers.get("X-User-ID") or "dev@local"
        return {"email": email, "role": "admin", "_auth_source": "bypass"}
    return await _get_claims_from_request(request)

async def get_auth_claims_allow_revoked(request: Request) -> Dict[str, Any]:
    if _has_dev_bypass(request.headers):
        email = request.headers.get("X-User-Email") or request.headers.get("X-User-ID") or "dev@local"
        return {"email": email, "role": "admin", "_auth_source": "bypass"}
    return await _get_claims_from_request(request, allow_revoked=True)

async def require_admin_claims(request: Request) -> Dict[str, Any]:
    if _has_dev_bypass(request.headers):
        email = request.headers.get("X-User-Email") or request.headers.get("X-User-ID") or "dev@local"
        return {"email": email, "role": "admin", "_auth_source": "bypass"}
    claims = await _get_claims_from_request(request)
    auth_service = _maybe_get_auth_service(request)
    if _is_admin_claims(claims, auth_service):
        return claims
    raise HTTPException(status_code=403, detail="Accès admin requis.")

async def get_session_manager_optional(request: Request) -> Optional["SessionManager"]:
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        return None
    provider = getattr(container, "session_manager", None)
    if provider is None:
        return None
    try:
        return provider()
    except Exception as exc:
        logger.debug("SessionManager indisponible: %s", exc)
        return None

async def get_dashboard_service(request: Request) -> Any:
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    return container.dashboard_service()

async def get_timeline_service(request: Request) -> Any:
    """Retourne le TimelineService pour les endpoints de graphiques."""
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    return container.timeline_service()

async def get_benchmarks_service(request: Request) -> Any:
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    provider = getattr(container, "benchmarks_service", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="BenchmarksService indisponible.")
    try:
        return provider()
    except Exception as exc:
        logger.debug("BenchmarksService indisponible: %s", exc)
        raise HTTPException(status_code=503, detail="BenchmarksService indisponible.")
async def get_document_service(request: Request) -> Any:
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    return container.document_service()

async def get_admin_dashboard_service(request: Request) -> Any:
    """Get admin dashboard service from container."""
    container = getattr(request.app.state, "service_container", None)
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    provider = getattr(container, "admin_dashboard_service", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Admin dashboard service indisponible.")
    try:
        return provider()
    except Exception as exc:
        logger.debug("AdminDashboardService indisponible: %s", exc)
        raise HTTPException(status_code=503, detail="AdminDashboardService indisponible.")

async def get_user_role(request: Request) -> str:
    """Extract user role from JWT claims or dev headers."""
    dev_bypass = _has_dev_bypass(request.headers)
    token = _extract_bearer_token_from_header(request.headers.get("Authorization"))

    if token:
        claims = await _get_claims_from_request(request)
        role = _normalize_identifier(claims.get("role"))
        if role:
            return role.lower()

    if dev_bypass or _is_global_dev_mode(request):
        role_hdr = request.headers.get("X-User-Role")
        if role_hdr:
            return role_hdr.lower()

    # Default to member if no role found
    return "member"

