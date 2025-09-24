# src/backend/shared/dependencies.py
# V7.4 – Allowlist GIS + WS token handshake + compat alias (_extract_ws_bearer_token) + DI getters sans import container
from __future__ import annotations

import os
import json
import base64
import logging
import re
from typing import TYPE_CHECKING
from typing import Optional, Any, Dict

from fastapi import Request, HTTPException, Query
from fastapi import WebSocket

logger = logging.getLogger("emergence.allowlist")


if TYPE_CHECKING:
    from backend.features.auth.service import AuthService
    from backend.core.session_manager import SessionManager

# -----------------------------
# Helpers JWT
# -----------------------------
def _try_json(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return {}

def _read_bearer_claims_from_token(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("not-a-jwt")
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8", "ignore"))
        return claims if isinstance(claims, dict) else {}
    except Exception:
        return {}

def _read_bearer_claims(request: Request) -> dict:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer requis.")
    token = auth.split(" ", 1)[1].strip()
    return _read_bearer_claims_from_token(token)

_jwt_like = re.compile(r"^[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+$")

def _looks_like_jwt(s: str) -> bool:
    return bool(_jwt_like.fullmatch(s or ""))

_DEV_BYPASS_TRUTHY = {"1", "true", "yes", "on", "enable"}


def _has_dev_bypass(headers) -> bool:
    try:
        if not headers:
            return False
        val = headers.get('x-dev-bypass') or headers.get('X-Dev-Bypass')
        return bool(val) and str(val).strip().lower() in _DEV_BYPASS_TRUTHY
    except Exception:
        return False


def _has_dev_bypass_query(params) -> bool:
    try:
        if not params:
            return False
        val = params.get('dev_bypass')
        return bool(val) and str(val).strip().lower() in _DEV_BYPASS_TRUTHY
    except Exception:
        return False



def _maybe_get_auth_service(scope_holder) -> Optional["AuthService"]:
    try:
        app = scope_holder.app  # type: ignore[attr-defined]
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

async def _resolve_token_claims(token: str, scope_holder, *, allow_revoked: bool = False) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="ID token invalide ou absent.")
    claims_unverified = _read_bearer_claims_from_token(token)
    auth_service = _maybe_get_auth_service(scope_holder)
    if auth_service is not None:
        try:
            verified = await auth_service.verify_token(token, allow_revoked=allow_revoked)
        except Exception as exc:
            status = getattr(exc, "status_code", 401)
            message = str(exc) or "Token invalide."
            local_issuer = getattr(getattr(auth_service, "config", None), "issuer", None)
            if claims_unverified and local_issuer and claims_unverified.get("iss") == local_issuer:
                raise HTTPException(status_code=status, detail=message) from exc
            if not claims_unverified:
                raise HTTPException(status_code=status, detail=message) from exc
        else:
            verified_dict = dict(verified)
            verified_dict.setdefault("_auth_source", "local")
            verified_dict["_raw_token"] = token
            return verified_dict
    if not claims_unverified:
        raise HTTPException(status_code=401, detail="ID token invalide ou absent.")
    _enforce_allowlist_claims(claims_unverified)
    claims_out = dict(claims_unverified)
    claims_out.setdefault("_auth_source", "google")
    claims_out["_raw_token"] = token
    return claims_out

async def _get_claims_from_request(request: Request, *, allow_revoked: bool = False) -> Dict[str, Any]:
    cache_key = "auth_claims_allow_revoked" if allow_revoked else "auth_claims"
    cached = getattr(request.state, cache_key, None)
    if isinstance(cached, dict):
        return cached
    token = _extract_bearer_token_from_header(request.headers.get("Authorization"))
    claims = await _resolve_token_claims(token, request, allow_revoked=allow_revoked)
    setattr(request.state, cache_key, claims)
    if allow_revoked and not isinstance(getattr(request.state, "auth_claims", None), dict):
        setattr(request.state, "auth_claims", claims)
    return claims

async def _get_claims_from_ws(ws: WebSocket) -> Dict[str, Any]:
    cached = getattr(ws.state, "auth_claims", None)
    if isinstance(cached, dict):
        return cached
    token = _get_ws_token_from_headers(ws)
    token = _normalize_bearer_value(token)
    if not token or not _looks_like_jwt(token):
        raise HTTPException(status_code=401, detail="WS: token absent (Authorization/subprotocol/cookie/query).")
    claims = await _resolve_token_claims(token, ws)
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
        return email in getattr(auth_service, "config").admin_emails  # type: ignore[attr-defined]
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


def _iter_ws_protocol_candidates(ws: WebSocket):
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
# Allowlist (emails / domaine)
# -----------------------------
def _get_cfg():
    mode = (os.getenv("GOOGLE_ALLOWLIST_MODE") or "").strip().lower()  # "email" | "domain" | ""
    allowed_emails = [e.strip().lower() for e in (os.getenv("GOOGLE_ALLOWED_EMAILS") or "").split(",") if e.strip()]
    allowed_hd = [d.strip().lower() for d in (os.getenv("GOOGLE_ALLOWED_HD") or "").split(",") if d.strip()]
    client_id = (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()
    dev = (os.getenv("AUTH_DEV_MODE") or "0").strip() in {"1", "true", "yes"}
    return mode, allowed_emails, allowed_hd, client_id, dev

def _enforce_allowlist_claims(claims: dict):
    mode, allowed_emails, allowed_hd, client_id, _dev = _get_cfg()
    if not mode and not client_id:
        return  # inactif

    iss = (claims.get("iss") or "").lower()
    aud = (claims.get("aud") or "").strip()
    email = (claims.get("email") or "").lower()
    hd = (claims.get("hd") or "").lower()

    if client_id:
        if aud != client_id or "accounts.google.com" not in iss:
            raise HTTPException(status_code=401, detail="ID token (aud/iss) invalide pour cette app.")

    if mode == "email":
        if email and email in set(allowed_emails):
            return
        raise HTTPException(status_code=401, detail="Email non autorisé.")
    elif mode == "domain":
        if hd and hd in set(allowed_hd):
            return
        if email and "@" in email:
            _domain = email.split("@", 1)[1].lower()
            if _domain in set(allowed_hd):
                return
        raise HTTPException(status_code=401, detail="Domaine non autorisé.")
    elif mode:
        raise HTTPException(status_code=401, detail="Allowlist mal configurée.")

# -----------------------------
# REST
# -----------------------------
async def enforce_allowlist(request: Request):
    mode, _emails, _hd, client_id, _dev = _get_cfg()
    if _has_dev_bypass(request.headers):
        logger.debug("Allowlist bypass via X-Dev-Bypass header.")
        return
    auth_service = _maybe_get_auth_service(request)
    token_present = bool(_extract_bearer_token_from_header(request.headers.get("Authorization")))
    if auth_service is not None:
        dev_mode = bool(getattr(getattr(auth_service, "config", None), "dev_mode", False))
        if token_present:
            await _get_claims_from_request(request)
            return
        if dev_mode:
            return
        raise HTTPException(status_code=401, detail="Authorization Bearer requis.")
    if not mode and not client_id:
        return
    await _get_claims_from_request(request)
    return

async def get_user_id(request: Request) -> str:
    mode, _emails, _hd, _client_id, dev = _get_cfg()
    dev_bypass = _has_dev_bypass(request.headers)
    auth_service = _maybe_get_auth_service(request)
    token = _extract_bearer_token_from_header(request.headers.get("Authorization"))

    if token:
        claims = await _get_claims_from_request(request)
        sub = claims.get("sub")
        if sub:
            return str(sub)
        if dev or dev_bypass:
            hdr = request.headers.get("X-User-ID") or request.headers.get("X-User-Id")
            if hdr:
                logger.warning("DevMode: fallback X-User-ID utilisé car le JWT ne porte pas de 'sub'.")
                return hdr
        raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")

    dev_mode_active = bool(getattr(getattr(auth_service, "config", None), "dev_mode", False)) if auth_service else False
    if dev_mode_active or dev_bypass or dev:
        hdr = request.headers.get("X-User-ID") or request.headers.get("X-User-Id")
        if hdr:
            logger.warning("DevMode: fallback X-User-ID utilisé (pas d'Authorization).")
            return hdr

    raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")
async def get_user_id_for_ws(ws: WebSocket, user_id: Optional[str] = Query(default=None)) -> str:
    """
    Retourne l'user_id à partir d'un JWT trouvé dans le handshake WS.
    En DEV (AUTH_DEV_MODE=1) peut accepter user_id explicite si aucun token.
    """
    mode, _emails, _hd, client_id, dev = _get_cfg()
    dev_bypass = _has_dev_bypass(ws.headers) or _has_dev_bypass_query(ws.query_params)
    auth_service = _maybe_get_auth_service(ws)
    dev_mode_active = bool(getattr(getattr(auth_service, "config", None), "dev_mode", False)) if auth_service else False

    try:
        claims = await _get_claims_from_ws(ws)
    except HTTPException as exc:
        if dev or dev_mode_active or dev_bypass:
            fallback = user_id or ws.query_params.get('user_id')
            if fallback:
                logger.warning("DevMode WS: fallback user_id utilisé (pas de token).")
                return str(fallback)
        raise

    sub = claims.get("sub")
    if sub:
        return str(sub)
    if dev or dev_mode_active or dev_bypass:
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
    container = getattr(request.app.state, "service_container", None)  # type: ignore[attr-defined]
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

async def get_dashboard_service(request: Request):
    container = getattr(request.app.state, "service_container", None)  # type: ignore
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    return container.dashboard_service()

async def get_document_service(request: Request):
    container = getattr(request.app.state, "service_container", None)  # type: ignore
    if container is None:
        raise HTTPException(status_code=503, detail="Service container indisponible.")
    return container.document_service()
