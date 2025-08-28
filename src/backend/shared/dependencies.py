# src/backend/shared/dependencies.py
# V6.1 – Allowlist GIS (Cloud Run) + extraction user_id GIS-only (sub)
# ARBO-LOCK: ce fichier doit vivre à ce chemin. Aucune importation hors plan.
from __future__ import annotations

import os
import json
import base64
import logging
from typing import Optional

from fastapi import Request, HTTPException, Query

logger = logging.getLogger("emergence.allowlist")

# -----------------------------
# Helpers JWT (GIS ID token)
# -----------------------------

def _decode_jwt_segment(segment: str) -> dict:
    """Décodage base64url sans vérification de signature (suffisant pour lire les claims)."""
    padding = '=' * ((4 - len(segment) % 4) % 4)
    data = segment + padding
    try:
        decoded = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"ID token illisible ({e}).")

def _read_bearer_claims(request: Request) -> dict:
    """Récupère les claims du JWT 'Authorization: Bearer …' (sans vérifier la signature)."""
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer manquant.")
    token = auth.split(" ", 1)[1].strip()
    parts = token.split(".")
    if len(parts) < 2:
        raise HTTPException(status_code=401, detail="Format JWT invalide.")
    _ = _decode_jwt_segment(parts[0])  # header non utilisé ici
    claims = _decode_jwt_segment(parts[1])
    return claims

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

async def enforce_allowlist(request: Request):
    """
    Dépendance FastAPI à appliquer sur les routes /api/* (sauf /api/health).
    Règle: si aucune var d'env d'allowlist n'est définie → no-op.
    """
    mode, allowed_emails, allowed_hd, client_id, _dev = _get_cfg()
    if not mode:  # allowlist inactif → exit
        return

    # Lecture des claims du token GIS
    claims = _read_bearer_claims(request)
    iss = (claims.get("iss") or "").lower()
    aud = (claims.get("aud") or "").strip()
    email = (claims.get("email") or "").lower()
    hd = (claims.get("hd") or "").lower()
    sub = claims.get("sub")  # pour logs

    # Vérifs minimales
    if client_id and aud != client_id:
        logger.warning(f"ID token aud≠client_id (aud={aud}, cfg={client_id}, sub={sub}).")
        raise HTTPException(status_code=401, detail="aud non reconnu.")
    if not (iss.endswith("accounts.google.com")):
        raise HTTPException(status_code=401, detail="iss invalide.")

    # Règles allowlist
    if mode == "email":
        if email not in allowed_emails:
            logger.info(f"Refus allowlist (email='{email}', sub={sub}).")
            raise HTTPException(status_code=401, detail="Email non autorisé.")
    elif mode in {"domain", "hd"}:
        if not hd or hd not in allowed_hd:
            logger.info(f"Refus allowlist (hd='{hd}', sub={sub}).")
            raise HTTPException(status_code=401, detail="Domaine non autorisé.")
    else:
        # Mode inconnu → bloquant par prudence
        raise HTTPException(status_code=401, detail="Allowlist mal configurée.")

    # OK
    logger.debug(f"Allowlist OK pour sub={sub}, email={email}, hd={hd}.")
    return

# -----------------------------
# Extraction User ID (REST)
# -----------------------------

async def get_user_id(request: Request) -> str:
    """
    GIS-only: l'identité REST provient du token Google (claim 'sub').
    - En prod: ignore 'X-User-ID'.
    - En dev (AUTH_DEV_MODE=1): tolère 'X-User-ID' en dernier recours si le token n'a pas de 'sub'.
    """
    claims = _read_bearer_claims(request)  # 401 si absent/invalide
    sub = claims.get("sub")
    if sub:
        return str(sub)

    # Fallback strictement DEV si nécessaire
    _mode, _emails, _hd, _client_id, dev = _get_cfg()
    if dev:
        hdr = request.headers.get("X-User-ID")
        if hdr:
            logger.warning("DevMode: fallback X-User-ID utilisé car le JWT ne porte pas de 'sub'.")
            return hdr

    raise HTTPException(status_code=401, detail="ID token invalide ou sans 'sub'.")

# -----------------------------
# Extraction User ID (WebSockets)
# -----------------------------

async def get_user_id_from_websocket(user_id: Optional[str] = Query(None, alias="user_id")) -> str:
    if not user_id:
        raise HTTPException(status_code=400, detail="Paramètre 'user_id' manquant.")
    return user_id
