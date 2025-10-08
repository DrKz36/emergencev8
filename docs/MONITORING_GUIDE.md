# Guide de monitoring et observabilité

## 🚀 Quick Start

### 1. Activer le monitoring (5 min)

```python
# Dans src/backend/main.py
from backend.core.middleware import (
    MonitoringMiddleware,
    SecurityMiddleware,
    RateLimitMiddleware,
    CORSSecurityMiddleware,
)
from backend.features.monitoring.router import router as monitoring_router

# Créer l'app
app = FastAPI()

# Ajouter les middlewares (ordre important!)
app.add_middleware(MonitoringMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
app.add_middleware(
    CORSSecurityMiddleware,
    allowed_origins=["http://localhost:3000", "https://yourdomain.com"]
)

# Ajouter le router de monitoring
app.include_router(monitoring_router)
```

### 2. Vérifier que ça fonctionne

```bash
# Healthcheck
curl http://localhost:8000/api/monitoring/health

# Métriques (nécessite auth admin)
curl -H "Authorization: Bearer <admin_token>" \
     http://localhost:8000/api/monitoring/metrics
```

---

## 📊 Endpoints de monitoring

### Publics (sans auth)

#### `GET /api/monitoring/health`
Healthcheck basique
```json
{
  "status": "healthy",
  "timestamp": "2025-01-08T10:30:00Z",
  "version": "0.0.0"
}
```

#### `GET /api/monitoring/health/detailed`
Healthcheck avec métriques système
```json
{
  "status": "healthy",
  "system": {
    "cpu_percent": 45.2,
    "memory": {
      "total_gb": 16.0,
      "available_gb": 8.5,
      "percent_used": 46.9
    }
  }
}
```

### Admin uniquement

#### `GET /api/monitoring/metrics`
Métriques complètes de l'application

#### `GET /api/monitoring/security/alerts`
Alertes de sécurité

#### `GET /api/monitoring/performance/slow-queries`
Requêtes lentes détectées

---

## 🔍 Utilisation dans le code

### Monitorer un endpoint

```python
from backend.core.monitoring import monitor_endpoint

@monitor_endpoint("chat_completion")
async def generate_chat_response(message: str):
    # Automatiquement loggé et mesuré
    response = await ai_service.generate(message)
    return response
```

### Détecter une requête lente

```python
from backend.core.monitoring import performance_monitor

async def complex_query():
    start = time.time()
    result = await db.execute("SELECT * FROM large_table")
    duration = time.time() - start

    if duration > 1.0:  # >1s
        performance_monitor.record_slow_query(
            query="SELECT * FROM large_table",
            duration=duration
        )

    return result
```

### Logger de manière structurée

```python
from backend.core.monitoring import log_structured

# Au lieu de logger.info()
log_structured(
    "info",
    "User completed onboarding",
    user_id=user.id,
    email=user.email,
    duration_seconds=45
)
```

Résultat en JSON :
```json
{
  "timestamp": "2025-01-08T10:30:00Z",
  "level": "INFO",
  "message": "User completed onboarding",
  "user_id": 123,
  "email": "user@example.com",
  "duration_seconds": 45
}
```

### Enregistrer temps de réponse IA

```python
from backend.core.monitoring import performance_monitor

async def call_ai(prompt: str):
    start = time.time()
    response = await openai_client.chat.completions.create(...)
    duration = time.time() - start

    performance_monitor.record_ai_response_time(
        duration=duration,
        model="gpt-4"
    )

    return response
```

---

## 🛡️ Monitoring de sécurité

### Détection automatique

Les middlewares détectent automatiquement :

✅ **SQL Injection**
```bash
# Requête suspecte
GET /api/search?q=admin' OR '1'='1

# Log automatique
{
  "level": "WARNING",
  "message": "SECURITY: Possible SQL injection attempt detected",
  "input": "admin' OR '1'='1",
  "pattern": "' OR '1'='1"
}
```

✅ **XSS**
```bash
# Requête suspecte
POST /api/chat {"message": "<script>alert('xss')</script>"}

# Log automatique
{
  "level": "WARNING",
  "message": "SECURITY: Possible XSS attempt detected",
  "input": "<script>alert('xss')</script>",
  "pattern": "<script"
}
```

✅ **Brute Force**
```python
# Après 5 échecs de login en 5min
{
  "level": "CRITICAL",
  "message": "SECURITY ALERT: Multiple failed login attempts",
  "email": "admin@example.com",
  "ip": "192.168.1.100",
  "attempts": 6,
  "alert_type": "brute_force"
}
```

### Enregistrer manuellement

```python
from backend.core.monitoring import security_monitor

# Login échoué
security_monitor.record_failed_login(
    email=email,
    ip=request.client.host
)

# Vérifier input
if not security_monitor.check_input_size(user_message, max_size=50000):
    raise HTTPException(413, "Input too large")
```

---

## 📈 Métriques et dashboards

### Exporter les métriques

```python
from backend.core.monitoring import export_metrics_json

# Export manuel
metrics = export_metrics_json("logs/metrics.json")

# Ou via API
GET /api/monitoring/metrics/export
```

### Format des métriques

```json
{
  "application": {
    "total_requests": 1543,
    "total_errors": 12,
    "endpoints": {
      "POST:/api/chat": {
        "requests": 523,
        "avg_latency_ms": 245.32,
        "error_rate": 0.57
      }
    }
  },
  "security": {
    "failed_logins": 8,
    "suspicious_patterns": {
      "sql_injection": 2,
      "xss": 1
    }
  },
  "performance": {
    "slow_queries_count": 3,
    "avg_ai_response_time": 3.45
  }
}
```

### Intégration Grafana

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'emergence'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/monitoring/metrics'
```

---

## 🚨 Alertes et notifications

### Configuration Slack (exemple)

```python
# src/backend/core/alerts.py
import httpx

async def send_slack_alert(message: str, severity: str = "warning"):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    color = {
        "info": "#36a64f",
        "warning": "#ff9900",
        "critical": "#ff0000",
    }[severity]

    await httpx.AsyncClient().post(webhook_url, json={
        "attachments": [{
            "color": color,
            "text": message,
            "footer": "Emergence Monitoring",
            "ts": int(time.time())
        }]
    })
```

### Utilisation

```python
from backend.core.alerts import send_slack_alert

# Dans un endpoint
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    await send_slack_alert(
        f"🔥 Critical error: {str(exc)}\nEndpoint: {request.url.path}",
        severity="critical"
    )
    raise
```

---

## 📝 Logs structurés

### Configuration

```python
# src/backend/main.py
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### Parsing avec jq

```bash
# Filtrer erreurs critiques
cat logs/app.log | jq 'select(.level == "CRITICAL")'

# Compter par endpoint
cat logs/app.log | jq -r '.endpoint' | sort | uniq -c

# Latence moyenne par endpoint
cat logs/app.log | jq -r 'select(.duration_ms) | "\(.endpoint) \(.duration_ms)"' | \
  awk '{sum[$1]+=$2; count[$1]++} END {for (e in sum) print e, sum[e]/count[e]}'
```

---

## 🔧 Middlewares configurables

### Rate Limiting personnalisé

```python
# Different limits per endpoint
from fastapi import Request

class SmartRateLimitMiddleware(RateLimitMiddleware):
    LIMITS = {
        "/api/auth/login": 5,      # 5 req/min
        "/api/chat": 20,            # 20 req/min
        "default": 60               # 60 req/min
    }

    async def dispatch(self, request: Request, call_next):
        endpoint = request.url.path
        limit = self.LIMITS.get(endpoint, self.LIMITS["default"])

        # Use endpoint-specific limit
        self.requests_per_minute = limit
        return await super().dispatch(request, call_next)
```

### CORS dynamique

```python
class DynamicCORSMiddleware(CORSSecurityMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Charger allowed origins depuis DB
        allowed = await db.fetch_all("SELECT origin FROM allowed_origins")
        self.allowed_origins = [r["origin"] for r in allowed]

        return await super().dispatch(request, call_next)
```

---

## 📊 Dashboards recommandés

### 1. Operations Dashboard
- **Requests per minute** (line chart)
- **Error rate %** (gauge)
- **P50/P95/P99 latency** (histogram)
- **Active users** (counter)

### 2. Security Dashboard
- **Failed login attempts** (heatmap by IP)
- **Suspicious patterns detected** (bar chart)
- **Blocked requests** (counter)
- **Top attacking IPs** (table)

### 3. Performance Dashboard
- **AI response time** (line chart)
- **Slow queries** (table)
- **Memory/CPU usage** (area chart)
- **Database connections** (gauge)

---

## 🧪 Tests de monitoring

```python
# tests/test_monitoring.py
import pytest
from backend.core.monitoring import metrics, security_monitor

def test_metrics_recording():
    metrics.record_request("/api/test", "GET")
    summary = metrics.get_metrics_summary()
    assert summary["total_requests"] > 0

def test_security_detection():
    assert security_monitor.detect_sql_injection("admin' OR '1'='1")
    assert security_monitor.detect_xss("<script>alert(1)</script>")

@pytest.mark.asyncio
async def test_rate_limiting(client):
    # Faire 100 requêtes rapidement
    for _ in range(100):
        response = await client.get("/api/test")

    # La 61ème doit être bloquée (si limite = 60/min)
    response = await client.get("/api/test")
    assert response.status_code == 429
```

---

## 🚀 Mise en production

### Checklist

- [ ] Installer dépendances : `pip install psutil python-json-logger`
- [ ] Créer dossier logs : `mkdir -p logs`
- [ ] Configurer rotation logs (logrotate)
- [ ] Configurer alertes Slack/PagerDuty
- [ ] Tester healthcheck externe (UptimeRobot)
- [ ] Configurer Prometheus scraping
- [ ] Créer dashboards Grafana
- [ ] Documenter procédure d'incident

### Variables d'environnement

```bash
# .env.production
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SENTRY_DSN=https://...@sentry.io/...
LOG_LEVEL=INFO
METRICS_EXPORT_INTERVAL=300  # 5min
```

---

## 📚 Ressources

- [Documentation FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Prometheus Monitoring](https://prometheus.io/docs/introduction/overview/)
- [Grafana Dashboards](https://grafana.com/docs/)

---

## 🆘 Troubleshooting

### Logs non structurés
```python
# Vérifier la config
import logging
print(logging.getLogger().handlers)
```

### Métriques vides
```python
# Vérifier que les middlewares sont bien ajoutés
print(app.middleware_stack)
```

### Rate limit trop strict
```python
# Augmenter temporairement
app.add_middleware(RateLimitMiddleware, requests_per_minute=1000)
```
