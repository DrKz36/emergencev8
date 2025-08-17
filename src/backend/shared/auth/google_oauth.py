# src/backend/shared/auth/google_oauth.py
# V1.1 — Audience multiple + logs de diagnostic (aud/iss/azp) + garde FastAPI
# - Valide un ID token Google (One Tap / GIS) côté backend.
# - Audience: supporte plusieurs client_id (séparés par des virgules dans l'env).
# - Dev mode optionnel pour accepter "testtoken" localement.
#
# ENV attendues :
#   GOOGLE_OAUTH_CLIENT_ID        -> aud à vérifier (id client OAuth Web) ; peut être "id1,id2,id3"
#   GOOGLE_ID_TOKEN_AUDIENCE      -> (optionnel) alias pour la même valeur
#   GOOGLE_ALLOWED_EMAILS         -> CSV d’emails autorisés (optionnel) [non loggé]
#   GOOGLE_ALLOWED_HD             -> CSV de domaines GSuite (optionnel) [non loggé]
#   AUTH_DEV_MODE                 -> "1/true/on" pour autoriser "testtoken" (dev only)

from __future__ import annotations

import os
import json
import time
import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Dict, Any, Iterable

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


def _split_csv_env(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


class AuthConfig:
    # Audience(s) acceptée(s) : support multi client_id via CSV
    _AUD: list[str] = (
        _split_csv_env(os.getenv("GOOGLE_OAUTH_CLIENT_ID"))
        or _split_csv_env(os.getenv("GOOGLE_ID_TOKEN_AUDIENCE"))
        or []
    )
    AUDIENCES: Optional[Sequence[str]] = _AUD if _AUD else None

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


def _unsafe_decode_payload(jwt_token: str) -> dict:
    """
    Décode SANS vérifier la signature — UNIQUEMENT pour logs de diag.
    Ne logge jamais d'email complet ni d'identifiants bruts.
    """
    try:
        header_b64, payload_b64, _ = jwt_token.split(".")
        import base64
        def b64url_to_bytes(b: str) -> bytes:
            pad = "=" * ((4 - (len(b) % 4)) % 4)
            return base64.urlsafe_b64decode(b + pad)
        raw = b64url_to_bytes(payload_b64)
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _verify_with_google(token: str, audiences: Optional[Iterable[str]]) -> Dict[str, Any]:
    if not _GOOGLE_AUTH_AVAILABLE:
        # Dépendance côté serveur manquante (google-auth)
        raise HTTPException(status_code=500, detail="Missing dependency: google-auth")

    req = google_requests.Request()

    # Stratégie :
    # - Si plusieurs audiences sont définies, on essaie chacune.
    # - Si aucune audience n'est fournie (None), on laisse google-auth vérifier tout sauf aud.
    tried = 0
    last_err: Optional[Exception] = None
    audiences_list = list(audiences) if audiences else [None]

    for aud in audiences_list:
        tried += 1
        try:
            claims = google_id_token.verify_oauth2_token(token, req, audience=aud)
            # google-auth accepte déjà iss = accounts.google.com OU https://accounts.google.com
            return claims
        except Exception as e:
            last_err = e
            continue

    # Échec → log de diagnostic minimal (sans PII)
    pld = _unsafe_decode_payload(token)
    diag = {
        "diag": "google_id_token_validation_failed",
        "aud_env": audiences_list,
        "payload_iss": pld.get("iss"),
        "payload_aud": pld.get("aud"),
        "payload_azp": pld.get("azp"),
        "payload_email_verified": pld.get("email_verified"),
        "now_epoch": int(time.time()),
        # ATTENTION : pas d'email en clair, pas de sub, pas de name/photo
    }
    logger.warning("Auth failure (ID token). Details=%s", json.dumps(diag, ensure_ascii=False))
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Google ID token (aud/iss mismatch or expired)."
    )


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

    claims = _verify_with_google(token, audiences=AuthConfig.AUDIENCES)
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
