# Metrics Feature - Prometheus Endpoints

**Module**: `src/backend/features/metrics/router.py`
**Version**: V1.0 (Émergence V8)
**Dernière mise à jour**: 2025-10-11

## Vue d'ensemble

Le module Metrics expose des endpoints pour l'observabilité et le monitoring de l'application ÉMERGENCE via Prometheus.

## Endpoints disponibles

### 1. `/metrics` - Export Prometheus

**GET** `/metrics`

Expose les métriques au format Prometheus pour scraping.

**Configuration**:
- Variable d'environnement: `CONCEPT_RECALL_METRICS_ENABLED=true`
- Par défaut: **désactivé** (retourne message informatif)

**Format de sortie**: `text/plain` (Prometheus exposition format)

**Exemple de réponse** (quand activé):
```prometheus
# HELP memory_cache_operations_total Memory cache operations (hit/miss)
# TYPE memory_cache_operations_total counter
memory_cache_operations_total{operation="hit",type="preferences"} 1247.0
memory_cache_operations_total{operation="miss",type="preferences"} 153.0

# HELP memory_analysis_success_total Nombre total d'analyses réussies
# TYPE memory_analysis_success_total counter
memory_analysis_success_total{provider="neo_analysis"} 432.0
memory_analysis_success_total{provider="nexus"} 28.0
memory_analysis_success_total{provider="anima"} 5.0

# HELP memory_analysis_duration_seconds Durée des analyses mémoire
# TYPE memory_analysis_duration_seconds histogram
memory_analysis_duration_seconds_bucket{provider="neo_analysis",le="1.0"} 380.0
memory_analysis_duration_seconds_bucket{provider="neo_analysis",le="2.0"} 425.0
memory_analysis_duration_seconds_sum{provider="neo_analysis"} 521.3
memory_analysis_duration_seconds_count{provider="neo_analysis"} 432.0

# HELP rag_queries_hybrid_total Total hybrid RAG queries
# TYPE rag_queries_hybrid_total counter
rag_queries_hybrid_total{status="success"} 1852.0
rag_queries_hybrid_total{status="error"} 12.0

# HELP rag_avg_score Average RAG result score
# TYPE rag_avg_score gauge
rag_avg_score 0.742
```

**Usage avec Prometheus**:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'emergence'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**Erreur si désactivé**:
```
# Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.
```

---

### 2. `/health` - Health Check Simple

**GET** `/health`

Vérifie que l'application est opérationnelle (healthcheck basique).

**Réponse** (JSON):
```json
{
  "status": "healthy",
  "metrics_enabled": false
}
```

**Status codes**:
- `200 OK`: Application fonctionnelle

**Usage**: Idéal pour load balancers simples ou monitoring basique.

---

### 3. `/rag` - Métriques RAG Structurées

**GET** `/rag`

Retourne les métriques RAG en JSON structuré pour dashboards.

**Réponse** (JSON):
```json
{
  "hybrid_queries_total": 1852,
  "avg_score": 0.742,
  "filtered_results": 234,
  "successful_queries": 1840,
  "success_rate": 0.993,
  "avg_results_per_query": 4.2
}
```

**Champs**:
- `hybrid_queries_total` (int): Nombre total de requêtes hybrides (BM25 + vectoriel)
- `avg_score` (float): Score moyen des résultats RAG [0.0-1.0]
- `filtered_results` (int): Nombre de résultats filtrés (sous seuil)
- `successful_queries` (int): Requêtes réussies (non filtrées)
- `success_rate` (float): Taux de succès [0.0-1.0]
- `avg_results_per_query` (float): Nombre moyen de résultats retournés

**Calcul success_rate**:
```python
success_rate = successful_queries / hybrid_queries_total
successful_queries = max(0, hybrid_queries_total - filtered_results)
```

**Gestion erreurs**:
- En cas d'erreur, retourne valeurs par défaut avec champ `"error"`
- Status code: `200 OK` (dégradation gracieuse)

**Usage**: Intégration dashboards frontend (Cockpit, Grafana, etc.)

---

## Métriques collectées

### Métriques Memory (MemoryAnalyzer)

**Succès/Échecs analyses**:
```
memory_analysis_success_total{provider="neo_analysis|nexus|anima"}
memory_analysis_failure_total{provider="...", error_type="TimeoutError|..."}
```

**Latence analyses** (histogram):
```
memory_analysis_duration_seconds{provider="..."}
# Buckets: [0.5, 1.0, 2.0, 4.0, 6.0, 10.0, 15.0, 20.0, 30.0]
```

**Cache analyses**:
```
memory_analysis_cache_hits_total
memory_analysis_cache_misses_total
memory_cache_size (gauge)
```

**Échecs extraction préférences**:
```
memory_preference_extraction_failures_total{reason="user_identifier_missing|extraction_error|persistence_error"}
```

### Métriques Memory (MemoryContextBuilder)

**Cache préférences**:
```
memory_cache_operations_total{operation="hit|miss", type="preferences"}
```

### Métriques RAG (HybridRetriever)

**Queries hybrides**:
```
rag_queries_hybrid_total{status="success|error"}
```

**Scores et résultats**:
```
rag_avg_score (gauge)
rag_results_count (histogram)
rag_results_filtered_total{reason="below_threshold|..."}
```

---

## Configuration

### Variables d'environnement

**`CONCEPT_RECALL_METRICS_ENABLED`**:
- Valeur: `"true"` pour activer, `"false"` (défaut) pour désactiver
- Active l'endpoint `/metrics` au format Prometheus
- **Recommandation production**: Activer uniquement si Prometheus est configuré

**Exemple `.env`**:
```bash
CONCEPT_RECALL_METRICS_ENABLED=true
```

---

## Intégration

### Avec Prometheus

**1. Activer les métriques**:
```bash
export CONCEPT_RECALL_METRICS_ENABLED=true
```

**2. Configurer Prometheus** (`prometheus.yml`):
```yaml
scrape_configs:
  - job_name: 'emergence_backend'
    scrape_interval: 15s
    scrape_timeout: 10s
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

**3. Requêtes PromQL utiles**:

**Cache hit rate préférences**:
```promql
rate(memory_cache_operations_total{operation="hit"}[5m]) /
rate(memory_cache_operations_total[5m])
```

**Latence p95 analyses mémoire**:
```promql
histogram_quantile(0.95,
  rate(memory_analysis_duration_seconds_bucket[5m])
)
```

**Success rate RAG**:
```promql
rate(rag_queries_hybrid_total{status="success"}[5m]) /
rate(rag_queries_hybrid_total[5m])
```

### Avec Grafana

**Dashboard RAG**:
```json
{
  "title": "ÉMERGENCE RAG Metrics",
  "panels": [
    {
      "title": "Hybrid Queries Rate",
      "targets": [{
        "expr": "rate(rag_queries_hybrid_total[5m])"
      }]
    },
    {
      "title": "Average RAG Score",
      "targets": [{
        "expr": "rag_avg_score"
      }]
    },
    {
      "title": "Memory Analysis Latency (p95)",
      "targets": [{
        "expr": "histogram_quantile(0.95, rate(memory_analysis_duration_seconds_bucket[5m]))"
      }]
    }
  ]
}
```

### Avec Frontend (Cockpit)

**Fetch métriques RAG**:
```typescript
async function fetchRAGMetrics() {
  const response = await fetch('/metrics/rag');
  const data = await response.json();

  console.log(`RAG Success Rate: ${(data.success_rate * 100).toFixed(1)}%`);
  console.log(`Average Score: ${data.avg_score.toFixed(3)}`);
  console.log(`Total Queries: ${data.hybrid_queries_total}`);

  return data;
}
```

---

## Sécurité et bonnes pratiques

### Production

1. **Limiter l'accès `/metrics`**: Utiliser un firewall ou authentification
   ```nginx
   location /metrics {
       allow 10.0.0.0/8;  # Réseau interne uniquement
       deny all;
   }
   ```

2. **Rate limiting**: Limiter le scraping Prometheus (max 1 req/15s)

3. **Désactiver par défaut**: `CONCEPT_RECALL_METRICS_ENABLED=false` si pas de Prometheus

### Monitoring

1. **Alerting Prometheus** (exemple):
   ```yaml
   groups:
     - name: emergence_alerts
       rules:
         - alert: HighRAGFailureRate
           expr: rate(rag_queries_hybrid_total{status="error"}[5m]) > 0.1
           for: 5m
           annotations:
             summary: "RAG failure rate > 10%"

         - alert: HighMemoryAnalysisLatency
           expr: histogram_quantile(0.95, rate(memory_analysis_duration_seconds_bucket[5m])) > 20
           for: 10m
           annotations:
             summary: "Memory analysis p95 latency > 20s"
   ```

2. **Dashboard SLIs**:
   - Success rate RAG > 95%
   - Latence p95 analyses < 10s
   - Cache hit rate préférences > 80%

---

## Limitations connues

1. **Pas d'authentification native**: L'endpoint `/metrics` est public (à sécuriser via reverse proxy)
2. **Pas de filtrage par utilisateur**: Métriques agrégées uniquement
3. **Pas de rétention**: Prometheus doit être configuré pour la rétention long-terme

---

## Roadmap

- **V1.1**: Authentification optionnelle (API key)
- **V1.2**: Métriques par utilisateur/tenant
- **V1.3**: Export CloudWatch/DataDog natif
- **V2.0**: Dashboard Grafana pré-configuré

---

## Références

- [Monitoring](monitoring.md) - Health checks avancés (liveness/readiness)
- [Memory](memory.md) - MemoryAnalyzer (source des métriques)
- [Chat](chat.md) - MemoryContextBuilder (cache préférences)
- [Monitoring Guide](../MONITORING_GUIDE.md) - Guide observabilité complet
- [Prometheus Documentation](https://prometheus.io/docs/introduction/overview/)

---

## Changelog

### V1.0 - 2025-10-11
- Endpoint `/metrics` format Prometheus (activable via env var)
- Endpoint `/rag` métriques RAG structurées (JSON)
- Endpoint `/health` healthcheck basique
- Support métriques Memory + RAG + Cache
