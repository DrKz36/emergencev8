"""
Router pour les endpoints de monitoring et healthcheck
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import psutil
import platform
from datetime import datetime, timezone

from backend.core.monitoring import (
    metrics,
    security_monitor,
    performance_monitor,
    export_metrics_json,
)

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
