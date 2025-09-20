# src/backend/shared/dependencies.py
# V7.4 – Allowlist GIS + WS token handshake + compat alias (_extract_ws_bearer_token) + DI getters sans import container
from __future__ import annotations

import os
import json
import base64
import logging
import re
from typing import Optional

from fastapi import Request, HTTPException, Query
from fastapi import WebSocket

logger = logging.getLogger("emergence.allowlist")

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
    if not mode and not client_id:
        return
    if _has_dev_bypass(request.headers):
        logger.debug("Allowlist bypass via X-Dev-Bypass header.")
        return
    claims = _read_bearer_claims(request)  # 401 si absent/invalide
    _enforce_allowlist_claims(claims)
    return

async def get_user_id(request: Request) -> str:
    mode, _emails, _hd, _client_id, dev = _get_cfg()
    dev_bypass = _has_dev_bypass(request.headers)
    auth_header = request.headers.get("Authorization") or ""

    if auth_header.startswith("Bearer "):
        claims = _read_bearer_claims(request)  # 401 si absent/invalide
        sub = claims.get("sub")
        if sub:
            return str(sub)
        if dev or dev_bypass:
            hdr = request.headers.get("X-User-ID") or request.headers.get("X-User-Id")
            if hdr:
                logger.warning("DevMode: fallback X-User-ID utilisé car le JWT ne porte pas de 'sub'.")
                return hdr
        raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")

    if dev or dev_bypass:
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
    token = _get_ws_token_from_headers(ws)
    dev_bypass = _has_dev_bypass(ws.headers) or _has_dev_bypass_query(ws.query_params)

    if not token:
        if (dev or dev_bypass) and user_id:
            logger.warning("DevMode WS: fallback user_id utilisé (pas de token).")
            return str(user_id)
        if dev or dev_bypass:
            qp_user = ws.query_params.get('user_id')
            if qp_user:
                logger.warning("DevMode WS: fallback user_id utilisé (query, pas de token).")
                return str(qp_user)
        raise HTTPException(status_code=401, detail="WS: token absent (Authorization/subprotocol/cookie/query).")

    claims = _read_bearer_claims_from_token(token)
    if not dev_bypass:
        _enforce_allowlist_claims(claims)

    sub = claims.get("sub")
    if not sub:
        if dev or dev_bypass:
            fallback = user_id or ws.query_params.get('user_id')
            if fallback:
                logger.warning("DevMode WS: fallback user_id utilisé (token sans 'sub').")
                return str(fallback)
        raise HTTPException(status_code=401, detail="WS: token sans 'sub'.")
    return str(sub)
async def get_user_id_from_websocket(ws: WebSocket, user_id: Optional[str] = Query(default=None)) -> str:
    return await get_user_id_for_ws(ws, user_id)

# -----------------------------
# DI getters (Dashboard & Documents) — sans import containers
# -----------------------------
# NB: pas d'import de ServiceContainer ici (évite les cycles).
# On récupère le conteneur déjà instancié via request.app.state.service_container

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
