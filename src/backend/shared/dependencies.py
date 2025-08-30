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
    claims = _read_bearer_claims(request)  # 401 si absent/invalide
    _enforce_allowlist_claims(claims)
    return

async def get_user_id(request: Request) -> str:
    claims = _read_bearer_claims(request)  # 401 si absent/invalide
    sub = claims.get("sub")
    if sub:
        return str(sub)
    _mode, _emails, _hd, _client_id, dev = _get_cfg()
    if dev:
        hdr = request.headers.get("X-User-ID")
        if hdr:
            logger.warning("DevMode: fallback X-User-ID utilisé car le JWT ne porte pas de 'sub'.")
            return hdr
    raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")

# -----------------------------
# WebSocket — extraction du JWT
# -----------------------------
def _get_ws_token_from_headers(ws: WebSocket) -> Optional[str]:
    """
    Stratégie tolérante :
      1) Sec-WebSocket-Protocol : "jwt,<token>" | "jwt <token>" | "jwt",<token>
      2) Query params : token | id_token | access_token
      3) Cookie : id_token
      4) Header Authorization: Bearer <token> (rare en browser)
    """
    # 1) Sous-protocoles
    proto_raw = ws.headers.get("sec-websocket-protocol") or ""
    if proto_raw:
        try:
            parts = [p.strip() for p in proto_raw.split(",") if p.strip()]
            if parts:
                first = parts[0]
                if first.lower().startswith("jwt"):
                    rest = first[3:].strip(" ,")
                    if rest and _looks_like_jwt(rest):
                        return rest
                    # second élément possible: token brut
                    if len(parts) >= 2 and _looks_like_jwt(parts[1]):
                        return parts[1]
        except Exception as e:
            logger.debug(f"Parsing sec-websocket-protocol échoué: {e}")

    # 2) Query
    for key in ("token", "id_token", "access_token"):
        val = ws.query_params.get(key)
        if val and _looks_like_jwt(val):
            return val

    # 3) Cookie
    cookie = ws.headers.get("cookie") or ""
    if cookie:
        for part in cookie.split(";"):
            k, _, v = part.strip().partition("=")
            if k == "id_token" and v:
                v = v.strip()
                if _looks_like_jwt(v):
                    return v

    # 4) Authorization (rare)
    auth = ws.headers.get("authorization") or ws.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        maybe = auth.split(" ", 1)[1].strip()
        if _looks_like_jwt(maybe):
            return maybe

    return None

# --- Compat : nom attendu par le router WS actuel ---
def _extract_ws_bearer_token(ws: WebSocket) -> Optional[str]:
    """Alias compat utilisé par le router WS (accept-first)."""
    return _get_ws_token_from_headers(ws)

async def get_user_id_for_ws(ws: WebSocket, user_id: Optional[str] = Query(default=None)) -> str:
    """
    Retourne l'user_id à partir d'un JWT trouvé dans le handshake WS.
    En DEV (AUTH_DEV_MODE=1) peut accepter user_id explicite si aucun token.
    """
    mode, _emails, _hd, client_id, dev = _get_cfg()
    token = _get_ws_token_from_headers(ws)

    if not token:
        if dev and user_id:
            logger.warning("DevMode WS: fallback user_id accepté (pas de token).")
            return str(user_id)
        raise HTTPException(status_code=401, detail="WS: token absent (Authorization/subprotocol/cookie/query).")

    claims = _read_bearer_claims_from_token(token)
    _enforce_allowlist_claims(claims)

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="WS: token sans 'sub'.")
    return str(sub)

# --- Compat pour les modules qui importent l'ancien nom ---
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
