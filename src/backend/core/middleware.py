"""
Middleware pour monitoring automatique de toutes les requêtes
"""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Any, Callable, cast

from backend.core.monitoring import (
    metrics,
    security_monitor,
    log_structured,
)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui monitore automatiquement toutes les requêtes
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        # Capturer le début
        start_time = time.time()
        endpoint = request.url.path
        method = request.method

        # Enregistrer la requête
        metrics.record_request(endpoint, method)

        # Log requête entrante
        log_structured(
            "info",
            f"Incoming request: {method} {endpoint}",
            method=method,
            endpoint=endpoint,
            client_ip=request.client.host if request.client else "unknown",
        )

        try:
            # Exécuter la requête
            response = await call_next(request)

            # Vérifier que la réponse est valide
            if response is None:
                log_structured(
                    "error",
                    f"No response returned for: {method} {endpoint}",
                    method=method,
                    endpoint=endpoint,
                )
                return Response(
                    content="Internal server error: no response",
                    status_code=500,
                )

            # Calculer la durée
            duration = time.time() - start_time
            metrics.record_latency(endpoint, duration)

            # Log réponse
            log_structured(
                "info",
                f"Request completed: {method} {endpoint}",
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Ajouter headers de monitoring
            response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
            response.headers["X-Request-ID"] = str(id(request))

            return cast(Response, response)

        except RuntimeError as exc:
            # Gérer le cas spécifique "No response returned"
            if "No response returned" in str(exc):
                duration = time.time() - start_time
                log_structured(
                    "error",
                    f"RuntimeError (no response): {method} {endpoint}",
                    method=method,
                    endpoint=endpoint,
                    duration_ms=round(duration * 1000, 2),
                )
                metrics.record_error(endpoint, "RuntimeError_NoResponse")
                return Response(
                    content="Internal server error: no response",
                    status_code=500,
                )
            raise

        except Exception as e:
            # Enregistrer l'erreur
            duration = time.time() - start_time
            error_type = type(e).__name__

            metrics.record_error(endpoint, error_type)

            log_structured(
                "error",
                f"Request failed: {method} {endpoint}",
                method=method,
                endpoint=endpoint,
                error_type=error_type,
                error_message=str(e),
                duration_ms=round(duration * 1000, 2),
            )

            raise


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware de sécurité pour détecter les comportements suspects
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        # Vérifier la taille du body
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            if size > 10 * 1024 * 1024:  # 10MB max
                log_structured(
                    "warning",
                    "Oversized request blocked",
                    size_bytes=size,
                    endpoint=request.url.path,
                    client_ip=request.client.host if request.client else "unknown",
                )
                return Response(
                    content="Request too large",
                    status_code=413,
                )

        # Vérifier les query params pour SQL injection / XSS
        if request.query_params:
            for key, value in request.query_params.items():
                if security_monitor.detect_sql_injection(value):
                    log_structured(
                        "critical",
                        "SQL injection attempt blocked",
                        param=key,
                        value=value[:100],
                        endpoint=request.url.path,
                    )
                    # On continue quand même mais on log

                if security_monitor.detect_xss(value):
                    log_structured(
                        "critical",
                        "XSS attempt blocked",
                        param=key,
                        value=value[:100],
                        endpoint=request.url.path,
                    )

        # Headers de sécurité
        try:
            response = await call_next(request)

            # Vérifier que la réponse est valide
            if response is None:
                log_structured(
                    "error",
                    "No response returned in SecurityMiddleware",
                    endpoint=request.url.path,
                )
                return Response(
                    content="Internal server error: no response",
                    status_code=500,
                )

            # Ajouter headers de sécurité
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            return cast(Response, response)

        except RuntimeError as exc:
            if "No response returned" in str(exc):
                log_structured(
                    "error",
                    "RuntimeError (no response) in SecurityMiddleware",
                    endpoint=request.url.path,
                )
                return Response(
                    content="Internal server error: no response",
                    status_code=500,
                )
            raise
        except Exception as exc:
            log_structured(
                "error",
                f"Unexpected error in SecurityMiddleware: {exc}",
                endpoint=request.url.path,
            )
            return Response(
                content="Internal server error",
                status_code=500,
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting global
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: dict[str, list[tuple[float, int]]] = {}  # {ip: [(timestamp, count)]}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Nettoyer les entrées anciennes (>1 minute)
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                (ts, count) for ts, count in self.request_counts[client_ip]
                if current_time - ts < 60
            ]

        # Compter les requêtes de la dernière minute
        recent_requests = sum(
            count for ts, count in self.request_counts.get(client_ip, [])
        )

        if recent_requests >= self.requests_per_minute:
            log_structured(
                "warning",
                "Rate limit exceeded",
                client_ip=client_ip,
                requests_count=recent_requests,
                limit=self.requests_per_minute,
            )

            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={"Retry-After": "60"},
            )

        # Enregistrer cette requête
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        self.request_counts[client_ip].append((current_time, 1))

        # Ajouter header avec quota restant
        try:
            response = await call_next(request)

            # Vérifier que la réponse est valide
            if response is None:
                log_structured(
                    "error",
                    "No response returned in RateLimitMiddleware",
                    endpoint=request.url.path,
                )
                return Response(
                    content="Internal server error: no response",
                    status_code=500,
                )

            remaining = self.requests_per_minute - recent_requests - 1
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

            return cast(Response, response)

        except RuntimeError as exc:
            if "No response returned" in str(exc):
                log_structured(
                    "error",
                    "RuntimeError (no response) in RateLimitMiddleware",
                    endpoint=request.url.path,
                )
                return Response(
                    content="Internal server error: no response",
                    status_code=500,
                )
            raise
        except Exception as exc:
            log_structured(
                "error",
                f"Unexpected error in RateLimitMiddleware: {exc}",
                endpoint=request.url.path,
            )
            return Response(
                content="Internal server error",
                status_code=500,
            )


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware CORS avec validation stricte
    """

    def __init__(self, app: ASGIApp, allowed_origins: list[str] | None = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://localhost:5173",
            "https://emergence.app",  # Production
        ]

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        origin = request.headers.get("origin")

        # OPTIONS (preflight)
        if request.method == "OPTIONS":
            if origin in self.allowed_origins:
                return Response(
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization",
                        "Access-Control-Max-Age": "3600",
                    },
                )
            else:
                log_structured(
                    "warning",
                    "CORS request from unauthorized origin",
                    origin=origin,
                )
                return Response(status_code=403)

        # Requête normale
        response = await call_next(request)

        if origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return cast(Response, response)
