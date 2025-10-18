# Monitoring Feature - Advanced Health Checks

**Module**: `src/backend/features/monitoring/router.py`
**Version**: P1.5 (Émergence V8)
**Dernière mise à jour**: 2025-10-11

## Vue d'ensemble

Le module Monitoring fournit des endpoints de healthcheck avancés, compatibles Kubernetes, et des dashboards admin pour l'observabilité de l'application ÉMERGENCE.

## Architecture

Le système de monitoring repose sur 3 couches:

1. **Health Checks**: Probes K8s (liveness, readiness) + healthchecks détaillés
2. **Métriques Application**: Statistiques endpoints, erreurs, latences
3. **Monitoring Sécurité/Performance**: Détection patterns suspects, slow queries, temps IA

---

## Endpoints Health Checks

### 1. `/api/monitoring/health` - Health Check Basique

**GET** `/api/monitoring/health`

Healthcheck public simple pour vérifier que l'application répond.

**Réponse** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-11T13:45:00.000Z",
  "version": "beta-2.1.2"
}
```

**Usage**: Load balancers basiques, monitoring externe simple.

---

### 2. `/api/monitoring/health/detailed` - Health Check Détaillé

**GET** `/api/monitoring/health/detailed`

Healthcheck avec métriques système (CPU, RAM, disk).

**Réponse** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-11T13:45:00.000Z",
  "system": {
    "platform": "Linux",
    "python_version": "3.11.5",
    "cpu_percent": 12.4,
    "memory": {
      "total_gb": 16.0,
      "available_gb": 8.5,
      "percent_used": 46.9
    },
    "disk": {
      "total_gb": 500.0,
      "free_gb": 235.7,
      "percent_used": 52.9
    }
  }
}
```

**Usage**: Dashboards admin, alerting sur ressources système.

---

### 3. `/health/liveness` - Liveness Probe K8s

**GET** `/health/liveness`

**Kubernetes liveness probe**: Vérifie que le processus est vivant et peut traiter des requêtes.

**Réponse** (200 OK):
```json
{
  "status": "alive",
  "timestamp": "2025-10-11T13:45:00.000Z",
  "uptime_seconds": 3628800
}
```

**Status codes**:
- `200 OK`: Processus vivant
- `503 Service Unavailable`: Processus mort ou bloqué

**Configuration K8s** (`deployment.yaml`):
```yaml
livenessProbe:
  httpGet:
    path: /health/liveness
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

**Comportement**: Si 3 échecs consécutifs, Kubernetes redémarre le pod.

---

### 4. `/health/readiness` - Readiness Probe K8s

**GET** `/health/readiness`

**Kubernetes readiness probe**: Vérifie que tous les services critiques sont opérationnels.

**Services vérifiés**:
1. **Database** (SQLite/PostgreSQL): Connexion + requête simple (`SELECT 1`)
2. **VectorService** (Chroma/Qdrant): Backend initialisé + liste collections
3. **LLM Providers** (OpenAI, Anthropic, Google): Clients configurés

**Réponse** (200 OK - tous services UP):
```json
{
  "overall": "up",
  "timestamp": "2025-10-11T13:45:00.000Z",
  "components": {
    "database": {
      "status": "up"
    },
    "vector_service": {
      "status": "up",
      "backend": "chroma",
      "collections": 3
    },
    "llm_providers": {
      "status": "up",
      "providers": {
        "openai": {"status": "up", "configured": true},
        "anthropic": {"status": "up", "configured": true},
        "google": {"status": "up", "configured": true}
      }
    }
  }
}
```

**Réponse** (503 Service Unavailable - au moins 1 service DOWN):
```json
{
  "overall": "degraded",
  "timestamp": "2025-10-11T13:45:00.000Z",
  "components": {
    "database": {
      "status": "up"
    },
    "vector_service": {
      "status": "down",
      "error": "Connection refused"
    },
    "llm_providers": {
      "status": "up",
      "providers": {...}
    }
  }
}
```

**Configuration K8s** (`deployment.yaml`):
```yaml
readinessProbe:
  httpGet:
    path: /health/readiness
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

**Comportement**: Si 2 échecs consécutifs, Kubernetes retire le pod du load balancing (pas de trafic).

---

### 3. `/api/system/info` - System Information (Phase P2)

**GET** `/api/system/info`

**Endpoint dédié pour About page** - Informations système complètes pour la page "À propos".

**Services vérifiés**:
- Backend version et environnement
- Python version et platform
- System resources (CPU, memory, disk)
- Service status (database, vector, LLM)
- Uptime et performance metrics

**Réponse** (200 OK):
```json
{
  "version": {
    "backend": "beta-2.1.2",
    "python": "3.11.5",
    "environment": "production"
  },
  "platform": {
    "system": "Linux",
    "release": "5.15.0",
    "machine": "x86_64",
    "processor": "Intel Xeon"
  },
  "resources": {
    "cpu_percent": 12.4,
    "memory": {
      "total_gb": 16.0,
      "available_gb": 8.5,
      "used_percent": 46.9
    },
    "disk": {
      "total_gb": 500.0,
      "free_gb": 235.7,
      "used_percent": 52.9
    }
  },
  "uptime": {
    "seconds": 3628800,
    "formatted": "42 days, 0 hours",
    "started_at": "2025-09-01T12:00:00Z"
  },
  "services": {
    "database": {
      "status": "up"
    },
    "vector_service": {
      "status": "up",
      "backend": "chroma",
      "collections": 3
    },
    "llm_providers": {
      "status": "up",
      "providers": {
        "openai": {"status": "up", "configured": true},
        "anthropic": {"status": "up", "configured": true}
      }
    }
  },
  "timestamp": "2025-10-17T13:45:00.000Z"
}
```

**Configuration Version**:
- Version définie via variable d'environnement `BACKEND_VERSION` (défaut: `beta-2.1.2`)
- Synchronisée avec `package.json`, `index.html` et autres fichiers sources
- Utilise `os.getenv("BACKEND_VERSION", "beta-2.1.2")` dans le code (ligne 384)

**Usage**: Page "À propos" de l'application, diagnostics système, vérification déploiement.

---

## Endpoints Métriques Admin

**Authentification requise**: Tous les endpoints ci-dessous nécessitent `verify_admin()` (stub actuel, à remplacer par vraie auth).

### 5. `/api/monitoring/metrics` - Métriques Application

**GET** `/api/monitoring/metrics`

Métriques agrégées de l'application (endpoints, sécurité, performance).

**Réponse** (200 OK):
```json
{
  "application": {
    "endpoints": {
      "/api/chat": {
        "requests": 1523,
        "errors": 12,
        "avg_latency_ms": 342.5
      },
      "/api/sessions": {
        "requests": 856,
        "errors": 3,
        "avg_latency_ms": 125.7
      }
    }
  },
  "security": {
    "failed_login_attempts": 5,
    "suspicious_patterns": 2,
    "blocked_ips": 0
  },
  "performance": {
    "slow_queries": 12,
    "avg_ai_response_ms": 2450.3
  },
  "timestamp": "2025-10-11T13:45:00.000Z"
}
```

**Usage**: Dashboard admin global, alerting agrégé.

---

### 6. `/api/monitoring/metrics/export` - Export JSON Complet

**GET** `/api/monitoring/metrics/export`

Export JSON complet de toutes les métriques (pour archivage ou analyse externe).

**Réponse**: Objet JSON volumineux avec toutes les métriques détaillées.

**Usage**: Archivage journalier, analyse post-mortem, rapports.

---

### 7. `/api/monitoring/metrics/endpoints` - Métriques par Endpoint

**GET** `/api/monitoring/metrics/endpoints`

Métriques détaillées par endpoint API.

**Réponse** (200 OK):
```json
{
  "endpoints": {
    "/api/chat": {
      "requests": 1523,
      "errors": 12,
      "avg_latency_ms": 342.5,
      "error_rate": 0.0079
    },
    "/api/sessions": {
      "requests": 856,
      "errors": 3,
      "avg_latency_ms": 125.7,
      "error_rate": 0.0035
    }
  },
  "timestamp": "2025-10-11T13:45:00.000Z"
}
```

**Usage**: Identifier endpoints lents ou problématiques, tuning performance.

---

### 8. `/api/monitoring/security/alerts` - Alertes Sécurité

**GET** `/api/monitoring/security/alerts`

Récupère les alertes de sécurité (tentatives login, patterns suspects).

**Réponse** (200 OK):
```json
{
  "summary": {
    "failed_login_attempts": 5,
    "suspicious_patterns": 2,
    "blocked_ips": 0
  },
  "failed_logins": {
    "user@example.com": 3,
    "hacker@evil.com": 2
  },
  "suspicious_patterns": {
    "sql_injection_attempt": 1,
    "path_traversal_attempt": 1
  },
  "timestamp": "2025-10-11T13:45:00.000Z"
}
```

**Usage**: Dashboard sécurité, détection intrusions, alerting SOC.

---

### 9. `/api/monitoring/performance/slow-queries` - Requêtes Lentes

**GET** `/api/monitoring/performance/slow-queries`

Liste des 50 dernières requêtes lentes (seuil configurable dans `performance_monitor`).

**Réponse** (200 OK):
```json
{
  "slow_queries": [
    {
      "query": "SELECT * FROM sessions WHERE user_id = ?",
      "duration_ms": 1523.4,
      "timestamp": "2025-10-11T13:42:15.000Z"
    },
    {
      "query": "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at",
      "duration_ms": 987.2,
      "timestamp": "2025-10-11T13:40:32.000Z"
    }
  ],
  "count": 50,
  "timestamp": "2025-10-11T13:45:00.000Z"
}
```

**Usage**: Optimisation requêtes DB, détection N+1 queries, indexation.

---

### 10. `/api/monitoring/performance/ai-stats` - Statistiques IA

**GET** `/api/monitoring/performance/ai-stats`

Statistiques des temps de réponse des LLM (OpenAI, Anthropic, Google).

**Réponse** (200 OK):
```json
{
  "count": 1234,
  "avg_duration": 2450.3,
  "min_duration": 850.2,
  "max_duration": 8543.7,
  "recent_responses": [
    {
      "provider": "openai",
      "model": "gpt-4",
      "duration_ms": 2340.5,
      "timestamp": "2025-10-11T13:44:55.000Z"
    }
  ],
  "timestamp": "2025-10-11T13:45:00.000Z"
}
```

**Usage**: Monitoring latence LLM, choix provider optimal, SLA.

---

### 11. `/api/monitoring/alerts/test` - Test Alerting

**POST** `/api/monitoring/alerts/test`

Endpoint de test pour vérifier le système d'alertes (envoie une alerte test).

**Réponse** (200 OK):
```json
{
  "message": "Test alert sent to logging system",
  "timestamp": "2025-10-11T13:45:00.000Z"
}
```

**Usage**: Validation configuration alerting, tests post-déploiement.

---

### 12. `/api/monitoring/metrics/reset` - Reset Métriques

**DELETE** `/api/monitoring/metrics/reset`

Reset toutes les métriques in-memory (utile pour tests ou après maintenance).

**Réponse** (200 OK):
```json
{
  "message": "All metrics reset successfully",
  "timestamp": "2025-10-11T13:45:00.000Z"
}
```

**⚠️ Attention**: Perte de toutes les métriques non persistées. À utiliser avec précaution.

---

## Intégration Kubernetes

### Exemple Deployment complet

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: emergence-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: gcr.io/PROJECT_ID/emergence:latest
        ports:
        - containerPort: 8000

        # Liveness probe: processus vivant?
        livenessProbe:
          httpGet:
            path: /health/liveness
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3  # 3 échecs = restart pod

        # Readiness probe: services critiques up?
        readinessProbe:
          httpGet:
            path: /health/readiness
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2  # 2 échecs = retrait du LB

        # Startup probe: démarrage initial lent (ChromaDB, etc.)
        startupProbe:
          httpGet:
            path: /health/liveness
            port: 8000
          initialDelaySeconds: 0
          periodSeconds: 5
          failureThreshold: 30  # Max 150s pour démarrage
```

### Alerting Prometheus (exemple)

```yaml
groups:
  - name: emergence_health
    rules:
      - alert: PodNotReady
        expr: kube_pod_status_ready{pod=~"emergence-backend-.*"} == 0
        for: 2m
        annotations:
          summary: "Pod ÉMERGENCE not ready"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Error rate > 5%"
```

---

## Architecture Monitoring

### Composants Internes

Le module `backend.core.monitoring` fournit:

1. **`metrics`**: Collecteur métriques application
   - `request_count`: Compteur requêtes par endpoint
   - `error_count`: Compteur erreurs par endpoint
   - `latency_sum/count`: Latences moyennes

2. **`security_monitor`**: Détection patterns suspects
   - `failed_login_attempts`: Tentatives login par email
   - `suspicious_patterns`: Compteur patterns (SQL injection, etc.)

3. **`performance_monitor`**: Tracking performance
   - `slow_queries`: Liste requêtes DB lentes (>500ms)
   - `ai_response_times`: Historique latences LLM

### Helpers

- **`log_structured(level, message, **kwargs)`**: Logging structuré (JSON) pour agrégation
- **`export_metrics_json()`**: Export complet métriques en JSON

---

## Configuration

### Variables d'environnement

Aucune variable spécifique pour le monitoring de base. Les composants dépendent de:

- `DATABASE_URL`: Connexion DB pour health check database
- `VECTOR_BACKEND`: Type VectorService (chroma/qdrant) pour health check
- Clés API LLM: Pour health check providers (OpenAI, Anthropic, Google)

### Seuils Configurables

Dans `backend.core.monitoring`:

```python
# performance_monitor.py
SLOW_QUERY_THRESHOLD_MS = 500  # Seuil requêtes lentes

# security_monitor.py
MAX_FAILED_LOGINS = 5  # Alerting après 5 tentatives
SUSPICIOUS_PATTERN_THRESHOLD = 10  # Alerting après 10 patterns
```

---

## Bonnes Pratiques Production

### Kubernetes

1. **Toujours utiliser les 3 probes**:
   - `livenessProbe`: Détecte deadlocks
   - `readinessProbe`: Traffic routing intelligent
   - `startupProbe`: Gère démarrages lents (30-60s pour ChromaDB)

2. **Tuning timeouts**:
   - Liveness: `timeoutSeconds: 5` (rapide)
   - Readiness: `timeoutSeconds: 3` (très rapide, vérifie services)
   - Startup: `failureThreshold: 30` (150s max pour boot)

3. **Éviter restart loops**:
   - `initialDelaySeconds` suffisant pour initialisation
   - `failureThreshold` pas trop bas (éviter false positives)

### Monitoring Externe

1. **Prometheus + Grafana**:
   - Scraper `/metrics` pour métriques Prometheus (voir [metrics.md](metrics.md))
   - Dashboard Grafana avec panels pour health checks

2. **Alerting**:
   - PagerDuty/Opsgenie pour alertes critiques (pods down)
   - Slack/Email pour alertes non-critiques (slow queries)

3. **Logging Structuré**:
   - Centraliser logs JSON avec Loki/CloudWatch
   - Corréler avec métriques Prometheus

---

## Limitations Connues

1. **Stub authentification admin**: `verify_admin()` est un placeholder (TODO: implémenter vraie auth)
2. **Métriques in-memory**: Perte au restart (TODO: persistence Redis/PostgreSQL)
3. **Pas de rate limiting**: Endpoints admin non protégés contre spam

---

## Roadmap

- **P2.0**: Authentification admin complète (JWT + RBAC)
- **P2.1**: Persistence métriques (Redis/PostgreSQL)
- **P2.2**: Rate limiting endpoints admin
- **P3.0**: Dashboard Grafana pré-configuré embarqué
- **P3.1**: Intégration CloudWatch/DataDog native

---

## Références

- [Metrics](metrics.md) - Endpoints Prometheus pour métriques
- [Monitoring Guide](../MONITORING_GUIDE.md) - Guide observabilité complet
- [Architecture Components](../architecture/10-Components.md) - Détail composants
- [Kubernetes Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

---

## Changelog

### P2.1.2 - 2025-10-17
- **Synchronisation versioning** : `version` maintenant `beta-2.1.2` (ligne 38)
- **Endpoint /api/system/info** : Informations système complètes pour About page
- Version backend via variable `BACKEND_VERSION` (défaut: `beta-2.1.2`)
- Synchronisation avec `package.json`, `index.html` et autres fichiers sources

### P1.5 - 2025-10-11
- Health checks avancés (liveness, readiness, detailed)
- Support Kubernetes probes complet
- Endpoints métriques admin (sécurité, performance, AI stats)
- Vérification Database/VectorService/LLM providers

### P1.0 - 2025-09-15
- Health check basique `/api/monitoring/health`
- Métriques application initiales
- Security/Performance monitors

