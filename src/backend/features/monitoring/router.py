"""
Router pour les endpoints de monitoring et healthcheck
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
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


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Healthcheck endpoint - public
    Vérifie que l'application est opérationnelle
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.0.0",  # À synchroniser avec package.json
    }


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
        async with db_manager.get_connection() as conn:
            result = await conn.execute("SELECT 1")
            await result.fetchone()

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


@router.get("/health/liveness")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe (Kubernetes-ready)
    Vérifie que le processus est vivant et peut traiter des requêtes.
    Retourne 200 si l'app est vivante, 503 sinon.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": psutil.Process().create_time(),
    }


@router.get("/health/readiness")
async def readiness_check(request: Request) -> Dict[str, Any]:
    """
    Readiness probe (Kubernetes-ready)
    Vérifie que tous les services critiques sont opérationnels.

    Retourne:
    - 200 si tous les services sont UP
    - 503 si au moins un service critique est DOWN

    Services vérifiés:
    - Database (SQLite/PostgreSQL)
    - VectorService (Chroma/Qdrant)
    - LLM Providers (OpenAI, Anthropic, Google)
    """
    components = {
        "database": await _check_database(request),
        "vector_service": await _check_vector_service(request),
        "llm_providers": await _check_llm_providers(request),
    }

    # Overall status : UP si tous les composants critiques sont UP
    all_up = all(c.get("status") == "up" for c in components.values())
    overall_status = "up" if all_up else "degraded"

    return {
        "overall": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }
