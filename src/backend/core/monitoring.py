"""
Monitoring et observabilité de l'application
Centralise logging, métriques et alertes
"""

import logging
import time
from functools import wraps
from typing import Optional, Any, cast
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
import json

# Configuration logging structuré
# Créer le dossier logs s'il n'existe pas
log_dir = Path(__file__).resolve().parents[3] / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collecteur de métriques pour monitoring"""

    def __init__(self):
        self.request_count = defaultdict(int)
        self.error_count = defaultdict(int)
        self.latency_sum = defaultdict(float)
        self.latency_count = defaultdict(int)

    def record_request(self, endpoint: str, method: str) -> None:
        """Enregistre une requête"""
        key = f"{method}:{endpoint}"
        self.request_count[key] += 1

    def record_error(self, endpoint: str, error_type: str) -> None:
        """Enregistre une erreur"""
        key = f"{endpoint}:{error_type}"
        self.error_count[key] += 1

    def record_latency(self, endpoint: str, duration: float) -> None:
        """Enregistre la latence d'une requête"""
        self.latency_sum[endpoint] += duration
        self.latency_count[endpoint] += 1

    def get_avg_latency(self, endpoint: str) -> float:
        """Calcule la latence moyenne"""
        if self.latency_count[endpoint] == 0:
            return 0.0
        return cast(float, self.latency_sum[endpoint] / self.latency_count[endpoint])

    def get_error_rate(self, endpoint: str) -> float:
        """Calcule le taux d'erreur"""
        total_requests = sum(
            count for key, count in self.request_count.items()
            if endpoint in key
        )
        total_errors = sum(
            count for key, count in self.error_count.items()
            if endpoint in key
        )
        if total_requests == 0:
            return 0.0
        return cast(float, (total_errors / total_requests) * 100)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Retourne un résumé des métriques"""
        return {
            "total_requests": sum(self.request_count.values()),
            "total_errors": sum(self.error_count.values()),
            "endpoints": {
                endpoint: {
                    "requests": self.request_count[endpoint],
                    "avg_latency_ms": round(self.get_avg_latency(endpoint) * 1000, 2),
                    "error_rate": round(self.get_error_rate(endpoint), 2),
                }
                for endpoint in set(
                    list(self.request_count.keys()) +
                    list(self.latency_count.keys())
                )
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Instance globale
metrics = MetricsCollector()


def monitor_endpoint(endpoint_name: Optional[str] = None) -> Any:
    """
    Décorateur pour monitorer un endpoint

    Usage:
        @monitor_endpoint("chat")
        async def chat_handler():
            ...
    """
    def decorator(func: Any) -> Any:
        name = endpoint_name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            metrics.record_request(name, "async")

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_latency(name, duration)

                # Log si latence élevée (>2s)
                if duration > 2.0:
                    logger.warning(
                        f"Slow endpoint: {name} took {duration:.2f}s",
                        extra={
                            "endpoint": name,
                            "duration": duration,
                            "args": str(args)[:100],
                        }
                    )

                return result

            except Exception as e:
                error_type = type(e).__name__
                metrics.record_error(name, error_type)

                logger.error(
                    f"Error in {name}: {error_type} - {str(e)}",
                    extra={
                        "endpoint": name,
                        "error_type": error_type,
                        "error_message": str(e),
                        "args": str(args)[:100],
                    },
                    exc_info=True
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            metrics.record_request(name, "sync")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_latency(name, duration)

                if duration > 2.0:
                    logger.warning(f"Slow endpoint: {name} took {duration:.2f}s")

                return result

            except Exception as e:
                error_type = type(e).__name__
                metrics.record_error(name, error_type)
                logger.error(f"Error in {name}: {error_type} - {str(e)}", exc_info=True)
                raise

        # Retourner le wrapper approprié
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class SecurityMonitor:
    """Moniteur de sécurité pour détecter les comportements suspects"""

    def __init__(self):
        self.failed_login_attempts = defaultdict(list)
        self.suspicious_patterns = defaultdict(int)

    def record_failed_login(self, email: str, ip: str) -> None:
        """Enregistre une tentative de login échouée"""
        now = datetime.now(timezone.utc)
        self.failed_login_attempts[email].append({
            "timestamp": now,
            "ip": ip,
        })

        # Alerte si >5 échecs en 5 minutes
        recent_failures = [
            attempt for attempt in self.failed_login_attempts[email]
            if (now - attempt["timestamp"]).total_seconds() < 300
        ]

        if len(recent_failures) >= 5:
            logger.critical(
                f"SECURITY ALERT: Multiple failed login attempts for {email}",
                extra={
                    "email": email,
                    "ip": ip,
                    "attempts": len(recent_failures),
                    "alert_type": "brute_force",
                }
            )

    def detect_sql_injection(self, input_string: str) -> bool:
        """Détecte des patterns d'injection SQL"""
        patterns = [
            "' OR '1'='1",
            "'; DROP TABLE",
            "UNION SELECT",
            "1' OR 1=1--",
            "admin'--",
        ]

        for pattern in patterns:
            if pattern.lower() in input_string.lower():
                self.suspicious_patterns["sql_injection"] += 1
                logger.warning(
                    "SECURITY: Possible SQL injection attempt detected",
                    extra={
                        "input": input_string[:100],
                        "pattern": pattern,
                    }
                )
                return True

        return False

    def detect_xss(self, input_string: str) -> bool:
        """Détecte des patterns XSS"""
        patterns = [
            "<script",
            "javascript:",
            "onerror=",
            "<iframe",
            "onclick=",
        ]

        for pattern in patterns:
            if pattern.lower() in input_string.lower():
                self.suspicious_patterns["xss"] += 1
                logger.warning(
                    "SECURITY: Possible XSS attempt detected",
                    extra={
                        "input": input_string[:100],
                        "pattern": pattern,
                    }
                )
                return True

        return False

    def check_input_size(self, input_string: str, max_size: int = 100000) -> bool:
        """Vérifie la taille de l'input"""
        if len(input_string) > max_size:
            logger.warning(
                "SECURITY: Oversized input detected",
                extra={
                    "size": len(input_string),
                    "max_allowed": max_size,
                }
            )
            return False
        return True

    def get_security_summary(self) -> dict[str, Any]:
        """Retourne un résumé des événements de sécurité"""
        return {
            "failed_logins": sum(len(attempts) for attempts in self.failed_login_attempts.values()),
            "suspicious_patterns": dict(self.suspicious_patterns),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Instance globale
security_monitor = SecurityMonitor()


class PerformanceMonitor:
    """Moniteur de performance"""

    def __init__(self):
        self.slow_queries = []
        self.ai_response_times = []

    def record_slow_query(self, query: str, duration: float) -> None:
        """Enregistre une requête lente"""
        self.slow_queries.append({
            "query": query[:200],
            "duration": duration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.warning(
            "PERFORMANCE: Slow database query detected",
            extra={
                "query": query[:200],
                "duration": duration,
            }
        )

    def record_ai_response_time(self, duration: float, model: str) -> None:
        """Enregistre le temps de réponse de l'IA"""
        self.ai_response_times.append({
            "duration": duration,
            "model": model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Alerte si >10s
        if duration > 10.0:
            logger.error(
                "PERFORMANCE: AI response timeout risk",
                extra={
                    "duration": duration,
                    "model": model,
                }
            )

    def get_performance_summary(self) -> dict[str, Any]:
        """Retourne un résumé des performances"""
        avg_ai_time = (
            sum(r["duration"] for r in self.ai_response_times) / len(self.ai_response_times)
            if self.ai_response_times else 0
        )

        return {
            "slow_queries_count": len(self.slow_queries),
            "avg_ai_response_time": round(avg_ai_time, 2),
            "slowest_queries": sorted(
                self.slow_queries,
                key=lambda x: x["duration"],
                reverse=True
            )[:5],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Instance globale
performance_monitor = PerformanceMonitor()


def export_metrics_json(filepath: str = "logs/metrics.json") -> dict[str, Any]:
    """Exporte toutes les métriques en JSON"""
    all_metrics = {
        "application": metrics.get_metrics_summary(),
        "security": security_monitor.get_security_summary(),
        "performance": performance_monitor.get_performance_summary(),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(filepath, 'w') as f:
        json.dump(all_metrics, f, indent=2)

    logger.info(f"Metrics exported to {filepath}")
    return all_metrics


# Fonction utilitaire pour logging structuré
def log_structured(level: str, message: str, **kwargs: Any) -> None:
    """
    Log avec structure JSON pour parsing facile

    Usage:
        log_structured("info", "User logged in", user_id=123, session_id="abc")
    """
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
        **kwargs
    }

    getattr(logger, level.lower())(json.dumps(log_data))
