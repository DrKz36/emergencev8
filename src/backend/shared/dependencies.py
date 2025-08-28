# src/backend/shared/dependencies.py
# V7.1 – Allowlist GIS + WS token handshake
# Lit le token via: Authorization: Bearer <JWT> | Sec-WebSocket-Protocol: jwt,<JWT> | item "qui ressemble à un JWT" | Cookie id_token | ?access_token
from __future__ import annotations

import os
import json
import base64
import logging
import re
from typing import Optional, List

from fastapi import Request, HTTPException, Query
from fastapi import WebSocket

logger = logging.getLogger("emergence.allowlist")

# -----------------------------
# Helpers JWT (GIS ID token)
# -----------------------------

def _decode_jwt_segment(segment: str) -> dict:
    padding = '=' * ((4 - len(segment) % 4) % 4)
    data = segment + padding
    try:
        decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"ID token illisible ({e}).")

def _read_bearer_claims_from_token(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=401, detail="Format JWT invalide.")
    _ = _decode_jwt_segment(parts[0])  # header
    claims = _decode_jwt_segment(parts[1])
    return claims

def _read_bearer_claims(request: Request) -> dict:
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer manquant.")
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
    sub = claims.get("sub")

    if client_id and aud != client_id:
        logger.warning(f"ID token aud≠client_id (aud={aud}, cfg={client_id}, sub={sub}).")
        raise HTTPException(status_code=401, detail="aud non reconnu.")
    if not (iss.endswith("accounts.google.com")):
        raise HTTPException(status_code=401, detail="iss invalide.")

    if mode == "email":
        if email not in allowed_emails:
            logger.info(f"Refus allowlist (email='{email}', sub={sub}).")
            raise HTTPException(status_code=401, detail="Email non autorisé.")
    elif mode in {"domain", "hd"}:
        if not hd or hd not in allowed_hd:
            logger.info(f"Refus allowlist (hd='{hd}', sub={sub}).")
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
# WebSockets
# -----------------------------

def _extract_ws_bearer_token(websocket: WebSocket) -> Optional[str]:
    # 1) Authorization
    auth = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()

    # 2) Subprotocol(s)
    proto_hdr = websocket.headers.get("sec-websocket-protocol") or websocket.headers.get("Sec-WebSocket-Protocol")
    if proto_hdr:
        # Exemple: "jwt,eyJhbGciOi..."; ou "Bearer eyJhbGciOi..."
        # On découpe sur la virgule et on trim
        candidates: List[str] = [p.strip() for p in proto_hdr.split(",") if p.strip()]
        # a) motif "Bearer <JWT>" fusionné en un seul item (certains clients non-navigateur)
        for p in candidates:
            if p.startswith("Bearer "):
                tok = p.split(" ", 1)[1].strip()
                if _looks_like_jwt(tok):
                    return tok
        # b) motif ["jwt", "<JWT>"] (navigateurs)
        for i, p in enumerate(candidates):
            if p.lower() == "jwt" and i + 1 < len(candidates) and _looks_like_jwt(candidates[i + 1]):
                return candidates[i + 1]
        # c) tout item qui ressemble directement à un JWT
        for p in candidates:
            if _looks_like_jwt(p):
                return p

    # 3) Cookie
    cookie = websocket.headers.get("cookie") or websocket.headers.get("Cookie")
    if cookie:
        try:
            parts = [c.strip() for c in cookie.split(";")]
            for kv in parts:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if k.strip() == "id_token" and v.strip():
                        return v.strip()
        except Exception:
            pass

    return None

async def get_user_id_from_websocket(
    websocket: WebSocket,
    access_token: Optional[str] = Query(None, alias="access_token"),
    user_id: Optional[str] = Query(None, alias="user_id"),
) -> str:
    token = _extract_ws_bearer_token(websocket) or access_token
    mode, _emails, _hd, _client_id, dev = _get_cfg()

    if not token:
        if dev and user_id:
            logger.warning("DevMode WS: fallback user_id accepté (pas de token).")
            return str(user_id)
        raise HTTPException(status_code=401, detail="WS: token absent (Authorization/subprotocol/cookie/access_token).")

    claims = _read_bearer_claims_from_token(token)
    _enforce_allowlist_claims(claims)

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="WS: token sans 'sub'.")
    return str(sub)
