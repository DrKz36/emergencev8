"""
Router pour les endpoints de monitoring et healthcheck
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Union
import psutil
import platform
import logging
from datetime import datetime, timezone

from backend.core.monitoring import (
    metrics,
    security_monitor,
    performance_monitor,
    export_metrics_json,
)

logger = logging.getLogger(__name__)

# Stub pour verify_admin - à remplacer par la vraie dépendance
def verify_admin():
    """Placeholder - À remplacer par la vraie authentification admin"""
    return {"role": "admin"}

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Note: Basic health endpoints are now in main.py at root level:
# - /api/health (simple OK check)
# - /healthz (liveness probe)
# - /ready (readiness probe with DB/Vector checks)
#
# This router only provides DETAILED monitoring endpoints.


@router.get("/health/ready")
async def health_ready(request: Request) -> Dict[str, Any]:
    """
    V13.2 - Readiness probe enrichi avec diagnostics vector store.

    Retourne:
    - status: "ok" (tous OK), "degraded" (vector readonly), "down" (DB KO)
    - vector_store: {reachable, mode, last_error}
    - HTTP 200 si ok/degraded, 503 si down

    Usage: Probes K8s/Cloud Run avec tolérance mode degraded.
    """
    try:
        # Check DB
        db_status = await _check_database(request)
        db_ok = db_status.get("status") == "up"

        # Check Vector Store avec diagnostics V13.2
        container = getattr(request.app.state, "service_container", None)
        vector_service = container.vector_service() if container else None

        if vector_service:
            vector_service._ensure_inited()  # Trigger lazy init
            vector_mode = vector_service.get_vector_mode()
            vector_reachable = vector_service.is_vector_store_reachable()
            vector_error = vector_service.get_last_init_error()
            backend = getattr(vector_service, "backend", "unknown")
        else:
            vector_mode = "unknown"
            vector_reachable = False
            vector_error = "VectorService not initialized"
            backend = "unknown"

        # Determine overall status
        if not db_ok:
            status = "down"
            http_code = 503
        elif vector_mode == "readonly":
            status = "degraded"
            http_code = 200  # Degraded mais accepté
        elif vector_reachable:
            status = "ok"
            http_code = 200
        else:
            status = "degraded"
            http_code = 200

        response = {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": {"reachable": db_ok},
            "vector_store": {
                "reachable": vector_reachable,
                "mode": vector_mode,
                "backend": backend,
                "last_error": vector_error if vector_error else None,
            },
        }

        # Return JSONResponse avec code HTTP approprié
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response, status_code=http_code)

    except Exception as e:
        logger.error(f"/health/ready check failed: {e}", exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content={
                "status": "down",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
            },
            status_code=503,
        )


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Healthcheck détaillé avec métriques système
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": disk.percent,
            },
        },
    }


@router.get("/metrics")
async def get_metrics(_: dict = Depends(verify_admin)) -> Dict[str, Any]:
    """
    Récupère les métriques de l'application
    Nécessite authentification admin
    """
    return {
        "application": metrics.get_metrics_summary(),
        "security": security_monitor.get_security_summary(),
        "performance": performance_monitor.get_performance_summary(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics/export")
async def export_metrics(_: dict = Depends(verify_admin)) -> Dict[str, Any]:
    """
    Exporte les métriques en JSON
    Nécessite authentification admin
    """
    return export_metrics_json()


@router.get("/metrics/endpoints")
async def get_endpoint_metrics(_: dict = Depends(verify_admin)) -> Dict[str, Any]:
    """
    Métriques détaillées par endpoint
    """
    return {
        "endpoints": metrics.get_metrics_summary()["endpoints"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/security/alerts")
async def get_security_alerts(_: dict = Depends(verify_admin)) -> Dict[str, Any]:
    """
    Récupère les alertes de sécurité
    """
    return {
        "summary": security_monitor.get_security_summary(),
        "failed_logins": {
            email: len(attempts)
            for email, attempts in security_monitor.failed_login_attempts.items()
        },
        "suspicious_patterns": dict(security_monitor.suspicious_patterns),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/performance/slow-queries")
async def get_slow_queries(_: dict = Depends(verify_admin)) -> Dict[str, Any]:
    """
    Liste des requêtes lentes
    """
    return {
        "slow_queries": performance_monitor.slow_queries[-50:],  # 50 dernières
        "count": len(performance_monitor.slow_queries),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/performance/ai-stats")
async def get_ai_stats(_: dict = Depends(verify_admin)) -> Dict[str, Any]:
    """
    Statistiques des temps de réponse IA
    """
    ai_times = performance_monitor.ai_response_times

    if not ai_times:
        return {
            "message": "No AI response data yet",
            "count": 0,
        }

    durations = [r["duration"] for r in ai_times]

    return {
        "count": len(durations),
        "avg_duration": round(sum(durations) / len(durations), 2),
        "min_duration": round(min(durations), 2),
        "max_duration": round(max(durations), 2),
        "recent_responses": ai_times[-20:],  # 20 dernières
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/alerts/test")
async def test_alert(_: dict = Depends(verify_admin)) -> Dict[str, str]:
    """
    Endpoint de test pour vérifier le système d'alertes
    """
    from backend.core.monitoring import log_structured

    log_structured(
        "critical",
        "TEST ALERT - This is a test alert",
        alert_type="test",
        triggered_by="admin",
    )

    return {
        "message": "Test alert sent to logging system",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.delete("/metrics/reset")
async def reset_metrics(_: dict = Depends(verify_admin)) -> Dict[str, str]:
    """
    Reset toutes les métriques (utile pour tests)
    """
    metrics.request_count.clear()
    metrics.error_count.clear()
    metrics.latency_sum.clear()
    metrics.latency_count.clear()

    security_monitor.failed_login_attempts.clear()
    security_monitor.suspicious_patterns.clear()

    performance_monitor.slow_queries.clear()
    performance_monitor.ai_response_times.clear()

    return {
        "message": "All metrics reset successfully",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# 🏥 HEALTH CHECKS AVANCÉS (P1.5 - Émergence V8)
# ============================================================

async def _check_database(request: Request) -> Dict[str, Any]:
    """Vérifie la connexion à la base de données"""
    try:
        container = getattr(request.app.state, "service_container", None)
        if not container:
            return {"status": "down", "error": "Container indisponible"}

        db_manager = container.db_manager()
        if not db_manager:
            return {"status": "down", "error": "DBManager non initialisé"}

        # Ping basique : exécuter une requête simple
        # Fix Phase 2: Utiliser _ensure_connection au lieu de get_connection
        conn = await db_manager._ensure_connection()
        cursor = await conn.execute("SELECT 1")
        await cursor.fetchone()

        return {"status": "up"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {"status": "down", "error": str(e)}


async def _check_vector_service(request: Request) -> Dict[str, Any]:
    """Vérifie le VectorService (Chroma/Qdrant)"""
    try:
        container = getattr(request.app.state, "service_container", None)
        if not container:
            return {"status": "down", "error": "Container indisponible"}

        vector_service = container.vector_service()
        if not vector_service:
            return {"status": "down", "error": "VectorService non initialisé"}

        # Vérifier que le backend est initialisé (lazy-load safe)
        vector_service._ensure_inited()
        backend = getattr(vector_service, "backend", "unknown")

        # Ping simple : lister les collections
        if backend == "chroma":
            client = getattr(vector_service, "client", None)
            if client:
                collections = client.list_collections()
                return {"status": "up", "backend": "chroma", "collections": len(collections)}
        elif backend == "qdrant":
            qdrant_client = getattr(vector_service, "qdrant_client", None)
            if qdrant_client:
                collections = qdrant_client.get_collections()
                return {"status": "up", "backend": "qdrant", "collections": len(collections.collections)}

        return {"status": "up", "backend": backend}
    except Exception as e:
        logger.error(f"VectorService health check failed: {e}", exc_info=True)
        return {"status": "down", "error": str(e)}


async def _check_llm_providers(request: Request) -> Dict[str, Any]:
    """Vérifie les clients LLM (OpenAI, Anthropic, Google)"""
    try:
        container = getattr(request.app.state, "service_container", None)
        if not container:
            return {"status": "down", "error": "Container indisponible"}

        chat_service = container.chat_service()
        if not chat_service:
            return {"status": "down", "error": "ChatService non initialisé"}

        providers = {}

        # Check OpenAI
        try:
            openai_client = getattr(chat_service, "openai_client", None)
            if openai_client:
                providers["openai"] = {"status": "up", "configured": True}
            else:
                providers["openai"] = {"status": "down", "configured": False}
        except Exception as e:
            providers["openai"] = {"status": "down", "error": str(e)}

        # Check Anthropic
        try:
            anthropic_client = getattr(chat_service, "anthropic_client", None)
            if anthropic_client:
                providers["anthropic"] = {"status": "up", "configured": True}
            else:
                providers["anthropic"] = {"status": "down", "configured": False}
        except Exception as e:
            providers["anthropic"] = {"status": "down", "error": str(e)}

        # Check Google (Gemini)
        try:
            # Google utilise genai configuré globalement
            providers["google"] = {"status": "up", "configured": True}
        except Exception as e:
            providers["google"] = {"status": "down", "error": str(e)}

        overall = "up" if any(p.get("status") == "up" for p in providers.values()) else "down"
        return {"status": overall, "providers": providers}
    except Exception as e:
        logger.error(f"LLM providers health check failed: {e}", exc_info=True)
        return {"status": "down", "error": str(e)}


# Liveness and readiness probes:
# - Primary endpoints in main.py: /healthz and /ready (root level for Cloud Run)
# - Legacy endpoints below for backward compatibility with existing monitoring tools


@router.get("/health/liveness")
async def liveness_probe() -> Dict[str, Any]:
    """
    Liveness probe - simple check that the process is alive.
    Legacy endpoint for backward compatibility.
    Use /healthz instead for new implementations.
    """
    return {"ok": True}


@router.get("/health/readiness", response_model=None)
async def readiness_probe(request: Request) -> Union[Dict[str, Any], JSONResponse]:
    """
    Readiness probe - checks that all critical services are ready.
    Legacy endpoint for backward compatibility.
    Use /ready instead for new implementations.
    """
    try:
        # Check DB
        db_check = await _check_database(request)
        # Check VectorService
        vector_check = await _check_vector_service(request)

        # Determine overall status
        db_ok = db_check.get("status") == "up"
        vector_ok = vector_check.get("status") == "up"

        if db_ok and vector_ok:
            return {"ok": True, "db": "up", "vector": "up"}
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "db": db_check.get("status", "unknown"),
                    "vector": vector_check.get("status", "unknown")
                }
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(e)}
        )


@router.get("/system/info")
async def get_system_info(request: Request) -> Dict[str, Any]:
    """
    Get comprehensive system information for About page.

    Provides:
    - Backend version and environment
    - Python version and platform
    - System resources (CPU, memory, disk)
    - Service status (database, vector, LLM)
    - Uptime and performance metrics

    Phase 2 Fix: Endpoint dédié pour About page
    """
    try:
        import os

        # Get process info
        process = psutil.Process()
        process_create_time = datetime.fromtimestamp(process.create_time(), tz=timezone.utc)
        now = datetime.now(timezone.utc)
        uptime_seconds = (now - process_create_time).total_seconds()

        # System resources
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Version info
        backend_version = os.getenv("APP_VERSION") or os.getenv("BACKEND_VERSION", "beta-2.1.4")
        env = os.getenv("ENVIRONMENT", "development")

        # Check services
        components = {
            "database": await _check_database(request),
            "vector_service": await _check_vector_service(request),
            "llm_providers": await _check_llm_providers(request),
        }

        return {
            "version": {
                "backend": backend_version,
                "python": platform.python_version(),
                "environment": env,
            },
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor() or "Unknown",
            },
            "resources": {
                "cpu_percent": round(cpu_percent, 2),
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": disk.percent,
                },
            },
            "uptime": {
                "seconds": int(uptime_seconds),
                "formatted": _format_uptime(uptime_seconds),
                "started_at": process_create_time.isoformat(),
            },
            "services": components,
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        logger.error(f"[system/info] Error fetching system info: {e}", exc_info=True)
        return {
            "version": {
                "backend": "unknown",
                "python": platform.python_version(),
                "environment": "unknown",
            },
            "platform": {
                "system": platform.system(),
                "release": "unknown",
                "machine": "unknown",
                "processor": "unknown",
            },
            "resources": {
                "cpu_percent": 0,
                "memory": {"total_gb": 0, "available_gb": 0, "used_percent": 0},
                "disk": {"total_gb": 0, "free_gb": 0, "used_percent": 0},
            },
            "uptime": {"seconds": 0, "formatted": "Unknown", "started_at": None},
            "services": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"
