# src/backend/shared/auth/google_oauth.py
# V1.0 — Vérification d’ID Token Google (OAuth) + garde FastAPI prête à brancher.
# - Valide un ID token (Google Sign-In / One Tap) côté backend.
# - Whitelist optionnelle par email et/ou domaine (GSuite).
# - Dev mode optionnel pour accepter "testtoken" localement.
#
# INTÉGRATION MINIMALE (après validation de ta part) :
#   from backend.shared.auth.google_oauth import require_google_user
#   @router.get("/secure")
#   async def secure_ep(user = Depends(require_google_user)): ...
#
# ENV attendues :
#   GOOGLE_OAUTH_CLIENT_ID        -> aud à vérifier (id client OAuth Web)
#   GOOGLE_ALLOWED_EMAILS         -> liste csv d’emails autorisés (optionnel)
#   GOOGLE_ALLOWED_HD             -> liste csv de domaines GSuite (optionnel)
#   AUTH_DEV_MODE                 -> "1/true/on" pour autoriser "testtoken" (dev only)

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Dict, Any

from fastapi import Header, HTTPException, status

try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    _GOOGLE_AUTH_AVAILABLE = True
except Exception:
    _GOOGLE_AUTH_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerifiedGoogleUser:
    sub: str
    email: str
    email_verified: bool
    name: Optional[str] = None
    picture: Optional[str] = None
    hd: Optional[str] = None
    raw_claims: Dict[str, Any] | None = None


class AuthConfig:
    AUDIENCE: Optional[str] = (
        os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        or os.getenv("GOOGLE_ID_TOKEN_AUDIENCE")
        or None
    )
    ALLOWED_EMAILS: Optional[Sequence[str]] = (
        [e.strip().lower() for e in os.getenv("GOOGLE_ALLOWED_EMAILS", "").split(",") if e.strip()] or None
    )
    ALLOWED_HD: Optional[Sequence[str]] = (
        [d.strip().lower() for d in os.getenv("GOOGLE_ALLOWED_HD", "").split(",") if d.strip()] or None
    )
    DEV_MODE: bool = os.getenv("AUTH_DEV_MODE", "").lower() in {"1", "true", "yes", "on"}


def _parse_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed Authorization header.")
    return parts[1]


def _verify_with_google(token: str, audience: Optional[str]) -> Dict[str, Any]:
    if not _GOOGLE_AUTH_AVAILABLE:
        # Dépendance côté serveur manquante (google-auth)
        raise HTTPException(status_code=500, detail="Missing dependency: google-auth")
    try:
        req = google_requests.Request()
        claims = google_id_token.verify_oauth2_token(token, req, audience=audience)
        return claims
    except Exception as e:
        logger.info(f"Invalid Google ID token: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token.")


def _enforce_allowlists(claims: Dict[str, Any]) -> None:
    email = (claims.get("email") or "").lower()
    hd = (claims.get("hd") or "").lower() or None

    if AuthConfig.ALLOWED_EMAILS and email not in AuthConfig.ALLOWED_EMAILS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not allowed.")
    if AuthConfig.ALLOWED_HD and (hd is None or hd not in AuthConfig.ALLOWED_HD):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Domain not allowed.")
    if not claims.get("email_verified", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified.")


def verify_id_token(token: str) -> VerifiedGoogleUser:
    # Dev mode : accepte un token de test (ne jamais activer en prod)
    if AuthConfig.DEV_MODE and token in {"dev", "testtoken", "debug"}:
        return VerifiedGoogleUser(
            sub="dev",
            email="dev@local",
            email_verified=True,
            name="Dev User",
            raw_claims={"dev": True},
        )

    claims = _verify_with_google(token, audience=AuthConfig.AUDIENCE)
    _enforce_allowlists(claims)

    return VerifiedGoogleUser(
        sub=str(claims.get("sub")),
        email=claims.get("email", ""),
        email_verified=bool(claims.get("email_verified", False)),
        name=claims.get("name"),
        picture=claims.get("picture"),
        hd=claims.get("hd"),
        raw_claims=claims,
    )


async def require_google_user(authorization: Optional[str] = Header(default=None)) -> VerifiedGoogleUser:
    """
    Garde FastAPI à brancher sur tes endpoints:
      user = Depends(require_google_user)
    Retourne un VerifiedGoogleUser si OK ; sinon lève HTTP 401/403.
    """
    token = _parse_bearer(authorization)
    return verify_id_token(token)
