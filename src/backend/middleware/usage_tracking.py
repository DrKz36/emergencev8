# src/backend/middleware/usage_tracking.py
"""
Phase 2 Guardian Cloud - Middleware Usage Tracking
Capture automatiquement toutes les requêtes API pour monitoring

⚠️ PRIVACY-COMPLIANT:
- ✅ Capture endpoint + méthode + status
- ✅ Capture user email depuis JWT
- ✅ Capture durée requête
- ❌ NE capture PAS le body des requêtes (/api/chat/message content)
- ❌ NE capture PAS les fichiers uploadés
- ❌ NE capture PAS les mots de passe
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Callable
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui track automatiquement l'usage des endpoints.
    Fire-and-forget (pas de await bloquant) pour performance maximale.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._repository_getter: Optional[Callable] = None
        self._initialized = False

    def set_repository_getter(self, getter: Callable):
        """Injecte getter pour UsageRepository (DI)"""
        self._repository_getter = getter
        self._initialized = True

    def _get_repository(self):
        """Récupère repository via DI"""
        if not self._initialized or self._repository_getter is None:
            return None
        try:
            return self._repository_getter()
        except Exception as e:
            logger.debug(f"UsageRepository indisponible: {e}")
            return None

    def _extract_user_email(self, request: Request) -> Optional[str]:
        """
        Extrait email utilisateur depuis JWT token ou headers dev
        Utilise le cache request.state.auth_claims si déjà résolu
        """
        try:
            # 1. Essayer depuis request.state (déjà résolu par get_auth_claims)
            claims = getattr(request.state, "auth_claims", None)
            if claims and isinstance(claims, dict):
                email = claims.get("email")
                if email:
                    return str(email).strip()

            # 2. Fallback: headers dev bypass
            dev_email = request.headers.get("X-User-Email")
            if dev_email:
                return str(dev_email).strip()

            # 3. Fallback: essayer de lire JWT directement (pas vérifié)
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                # Simple parse sans vérification signature (juste pour email)
                import base64
                import json

                try:
                    parts = token.split(".")
                    if len(parts) == 3:
                        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
                        payload = json.loads(
                            base64.urlsafe_b64decode(payload_b64).decode("utf-8")
                        )
                        email = payload.get("email")
                        if email:
                            return str(email).strip()
                except Exception:
                    pass

            return "anonymous"
        except Exception as e:
            logger.debug(f"Erreur extraction user email: {e}")
            return "anonymous"

    def _extract_feature_name(self, endpoint: str) -> str:
        """
        Convertit endpoint en feature_name plus lisible
        Ex: /api/chat/message -> chat_message
        """
        if endpoint.startswith("/api/"):
            endpoint = endpoint[5:]  # Remove /api/
        endpoint = endpoint.lstrip("/").rstrip("/")
        return endpoint.replace("/", "_") or "unknown"

    def _should_skip_endpoint(self, path: str) -> bool:
        """Endpoints à ne PAS tracker (health, metrics, static files)"""
        skip_prefixes = (
            "/health",
            "/metrics",
            "/favicon.ico",
            "/static/",
            "/_next/",
            "/assets/",
            "/docs",
            "/redoc",
            "/openapi.json",
        )
        return any(path.startswith(prefix) for prefix in skip_prefixes)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Intercepte toutes les requêtes pour tracking"""
        # Skip health/metrics endpoints
        if self._should_skip_endpoint(request.url.path):
            return await call_next(request)

        # Infos de base
        user_email = self._extract_user_email(request)
        endpoint = request.url.path
        method = request.method
        feature_name = self._extract_feature_name(endpoint)

        # Timer
        start_time = time.time()
        status_code = 500  # Default en cas d'erreur
        error_message = None

        try:
            # Execute request
            response = await call_next(request)
            status_code = response.status_code
            duration_ms = int((time.time() - start_time) * 1000)

            # Log success (fire-and-forget)
            self._log_feature_usage_background(
                user_email=user_email,
                feature_name=feature_name,
                endpoint=endpoint,
                method=method,
                success=(status_code < 400),
                status_code=status_code,
                duration_ms=duration_ms,
                error_message=None,
            )

            return response

        except Exception as e:
            # Log error (fire-and-forget)
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)
            error_type = type(e).__name__

            # Log comme feature usage (success=False)
            self._log_feature_usage_background(
                user_email=user_email,
                feature_name=feature_name,
                endpoint=endpoint,
                method=method,
                success=False,
                status_code=status_code,
                duration_ms=duration_ms,
                error_message=error_message,
            )

            # Log aussi comme user error
            self._log_user_error_background(
                user_email=user_email,
                endpoint=endpoint,
                method=method,
                error_type=error_type,
                error_code=status_code,
                error_message=error_message,
            )

            # Re-raise pour que FastAPI gère l'erreur normalement
            raise

    def _log_feature_usage_background(
        self,
        user_email: str | None,
        feature_name: str,
        endpoint: str,
        method: str,
        success: bool,
        status_code: int,
        duration_ms: int,
        error_message: Optional[str],
    ):
        """Log feature usage en background (fire-and-forget)"""
        try:
            repo = self._get_repository()
            if repo is None:
                return

            from backend.features.usage.models import FeatureUsage

            usage = FeatureUsage(
                user_email=user_email,
                feature_name=feature_name,
                endpoint=endpoint,
                method=method,
                timestamp=datetime.now(timezone.utc),
                success=success,
                error_message=error_message,
                duration_ms=duration_ms,
                status_code=status_code,
            )

            # Fire-and-forget (pas de await pour pas bloquer)
            asyncio.create_task(repo.log_feature_usage(usage))
        except Exception as e:
            # Silent fail (ne doit jamais casser les requêtes)
            logger.debug(f"Erreur log feature usage: {e}")

    def _log_user_error_background(
        self,
        user_email: str | None,
        endpoint: str,
        method: str,
        error_type: str,
        error_code: int,
        error_message: str,
    ):
        """Log user error en background (fire-and-forget)"""
        try:
            repo = self._get_repository()
            if repo is None:
                return

            from backend.features.usage.models import UserError

            error = UserError(
                user_email=user_email,
                endpoint=endpoint,
                method=method,
                error_type=error_type,
                error_code=error_code,
                error_message=error_message,
                stack_trace=None,  # TODO: extraire si besoin
                timestamp=datetime.now(timezone.utc),
            )

            # Fire-and-forget
            asyncio.create_task(repo.log_user_error(error))
        except Exception as e:
            logger.debug(f"Erreur log user error: {e}")
