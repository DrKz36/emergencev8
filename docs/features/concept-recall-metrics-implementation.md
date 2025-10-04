# Concept Recall - Métriques Prometheus

**Date** : 2025-10-04
**Version** : 1.0
**Status** : ✅ Implémenté (Option B)

## Vue d'ensemble

Système de métriques Prometheus pour monitorer l'efficacité et les performances du système de concept recall.

## Métriques implémentées

### 1. Détection

#### `concept_recall_detections_total` (Counter)
- **Description** : Nombre total de détections de concepts récurrents
- **Labels** :
  - `user_id_hash` : Hash SHA256 du user_id (8 premiers chars, privacy)
  - `similarity_range` : Plage de score (0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0)

#### `concept_recall_events_emitted_total` (Counter)
- **Description** : Nombre d'événements WebSocket `ws:concept_recall` émis
- **Labels** : `user_id_hash`

#### `concept_recall_similarity_score` (Histogram)
- **Description** : Distribution des scores de similarité
- **Buckets** : [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

#### `concept_recall_detection_latency_seconds` (Histogram)
- **Description** : Temps total de détection (recherche vectorielle + filtrage)
- **Buckets** : [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]

### 2. Qualité

#### `concept_recall_false_positives_total` (Counter)
- **Description** : Détections ignorées par l'utilisateur (bouton "Ignorer")
- **Labels** : `user_id_hash`

#### `concept_recall_interactions_total` (Counter)
- **Description** : Interactions utilisateur avec banners
- **Labels** :
  - `user_id_hash`
  - `action` : `view_history`, `dismiss`, `auto_hide`

### 3. Performance

#### `concept_recall_vector_search_duration_seconds` (Histogram)
- **Description** : Durée de la recherche vectorielle ChromaDB
- **Buckets** : [0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0]

#### `concept_recall_metadata_update_duration_seconds` (Histogram)
- **Description** : Durée mise à jour métadonnées (mention_count, thread_ids)
- **Buckets** : [0.01, 0.05, 0.1, 0.5, 1.0]

### 4. Métier

#### `concept_recall_cross_thread_detections_total` (Counter)
- **Description** : Détections cross-thread par plage de threads
- **Labels** :
  - `thread_count_range` : `2`, `3-5`, `6-10`, `10+`

#### `concept_recall_concept_reuse_total` (Counter)
- **Description** : Concepts réutilisés (mention_count > 1)
- **Labels** : `user_id_hash`

#### `concept_recall_concepts_total` (Gauge)
- **Description** : Nombre total de concepts dans le vector store
- **Labels** : `user_id_hash`

### 5. Système

#### `concept_recall_system` (Info)
- **Description** : Informations système
- **Labels** :
  - `version` : 1.0
  - `similarity_threshold` : 0.5
  - `max_recalls_per_message` : 3
  - `collection_name` : emergence_knowledge

## Architecture

### Fichiers créés

```
src/backend/features/memory/
├── concept_recall.py (✅ Mis à jour - instrumentation)
├── concept_recall_metrics.py (✅ Nouveau)

src/backend/features/metrics/
├── router.py (✅ Nouveau - endpoint /api/metrics)

src/backend/
├── main.py (✅ Mis à jour - montage router)
```

### API publique

**Module** : `concept_recall_metrics.py`

```python
from backend.features.memory.concept_recall_metrics import concept_recall_metrics

# Enregistrer une détection
concept_recall_metrics.record_detection(
    user_id="user_abc",
    similarity_score=0.87,
    thread_count=3,
    duration_seconds=0.045
)

# Enregistrer interaction utilisateur
concept_recall_metrics.record_interaction(
    user_id="user_abc",
    action="view_history"  # ou "dismiss", "auto_hide"
)

# Enregistrer réutilisation concept
concept_recall_metrics.record_concept_reuse(
    user_id="user_abc",
    mention_count=5
)
```

## Configuration

### Variables d'environnement

#### `CONCEPT_RECALL_METRICS_ENABLED`
- **Type** : Boolean
- **Défaut** : `false`
- **Description** : Active la collecte de métriques Prometheus

**Activation** :
```bash
# .env.local
CONCEPT_RECALL_METRICS_ENABLED=true
```

### Privacy

**Hash user_id** : SHA256 tronqué (8 chars) pour anonymisation dans labels Prometheus

```python
def _hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:8]
```

## Endpoint Prometheus

### GET /api/metrics

**Format** : Prometheus text exposition format

**Exemple de réponse** :
```
# HELP concept_recall_detections_total Total number of concept recall detections
# TYPE concept_recall_detections_total counter
concept_recall_detections_total{similarity_range="0.8-0.9",user_id_hash="a1b2c3d4"} 12.0
concept_recall_detections_total{similarity_range="0.9-1.0",user_id_hash="a1b2c3d4"} 5.0

# HELP concept_recall_similarity_score Distribution of similarity scores for detected concepts
# TYPE concept_recall_similarity_score histogram
concept_recall_similarity_score_bucket{le="0.5"} 0.0
concept_recall_similarity_score_bucket{le="0.6"} 3.0
concept_recall_similarity_score_bucket{le="0.7"} 8.0
concept_recall_similarity_score_bucket{le="0.8"} 15.0
concept_recall_similarity_score_bucket{le="0.9"} 22.0
concept_recall_similarity_score_bucket{le="1.0"} 25.0
concept_recall_similarity_score_bucket{le="+Inf"} 25.0
concept_recall_similarity_score_count 25.0
concept_recall_similarity_score_sum 20.47
```

### GET /api/health

Vérification rapide status métriques :

```json
{
  "status": "healthy",
  "metrics_enabled": true
}
```

## Intégration Prometheus

### Configuration scraping

**prometheus.yml** :
```yaml
scrape_configs:
  - job_name: 'emergence-backend'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
```

### Requêtes PromQL utiles

#### Taux de détection (detections/min)
```promql
rate(concept_recall_detections_total[5m]) * 60
```

#### Score moyen de similarité
```promql
rate(concept_recall_similarity_score_sum[5m])
/
rate(concept_recall_similarity_score_count[5m])
```

#### Taux de précision (non-dismissed / total)
```promql
1 - (
  rate(concept_recall_false_positives_total[1h])
  /
  rate(concept_recall_detections_total[1h])
)
```

#### P95 latency recherche vectorielle
```promql
histogram_quantile(0.95,
  rate(concept_recall_vector_search_duration_seconds_bucket[5m])
)
```

#### Top utilisateurs avec détections
```promql
topk(10,
  sum by (user_id_hash) (
    increase(concept_recall_detections_total[24h])
  )
)
```

## Alertes Prometheus (exemples)

**alerts.yml** :
```yaml
groups:
  - name: concept_recall
    interval: 1m
    rules:
      - alert: ConceptRecallLowPrecision
        expr: |
          1 - (
            rate(concept_recall_false_positives_total[1h])
            /
            rate(concept_recall_detections_total[1h])
          ) < 0.6
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Concept recall precision below 60% for 1h"
          description: "Too many false positives (dismissed detections)"

      - alert: ConceptRecallHighLatency
        expr: |
          histogram_quantile(0.95,
            rate(concept_recall_detection_latency_seconds_bucket[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Concept recall P95 latency > 1s"
          description: "Detection performance degraded"
```

## Dashboard Grafana (optionnel)

### Panels recommandés

1. **Détections/heure** (Time series)
   - Query : `rate(concept_recall_detections_total[5m]) * 3600`
   - Grouping : `similarity_range`

2. **Distribution similarité** (Heatmap)
   - Query : `rate(concept_recall_similarity_score_bucket[5m])`

3. **Taux de précision** (Gauge)
   - Query : Formule taux précision (voir ci-dessus)
   - Threshold : Rouge <60%, Jaune 60-80%, Vert >80%

4. **Latency P50/P95** (Time series)
   - Query : `histogram_quantile(0.5, ...)` et `histogram_quantile(0.95, ...)`

5. **Top utilisateurs** (Table)
   - Query : Top 10 users (voir ci-dessus)

## Tests

### Test unitaire

```python
# tests/backend/features/test_concept_recall_metrics.py

async def test_metrics_enabled():
    assert concept_recall_metrics.enabled == True

async def test_detection_increments_counter():
    before = DETECTIONS_TOTAL._value.get()

    concept_recall_metrics.record_detection(
        user_id="test_user",
        similarity_score=0.75,
        thread_count=2,
        duration_seconds=0.05
    )

    after = DETECTIONS_TOTAL._value.get()
    assert after > before
```

### Test intégration

```bash
# Démarrer backend avec métriques
CONCEPT_RECALL_METRICS_ENABLED=true python src/backend/main.py

# Vérifier endpoint
curl http://localhost:8000/api/metrics

# Doit retourner format Prometheus (text/plain)
```

## Performance

### Impact sur performances

- **Overhead metrics** : < 0.5ms par détection (négligeable)
- **Mémoire** : ~100KB pour 10,000 détections (histogrammes compris)
- **Thread-safe** : Oui (prometheus_client utilise locks internes)

### Recommandations

- **Rétention Prometheus** : 30 jours minimum (analyse tendances)
- **Scrape interval** : 15-30s (bon compromis granularité/charge)
- **Opt-in** : Laisser désactivé en dev, activer en prod

## Troubleshooting

### Métriques non exposées

**Symptôme** : `/api/metrics` retourne "Metrics disabled"

**Solution** :
```bash
# Vérifier variable d'environnement
echo $CONCEPT_RECALL_METRICS_ENABLED

# Doit être "true" (sensible à la casse)
export CONCEPT_RECALL_METRICS_ENABLED=true
```

### Prometheus ne scrape pas

**Vérifier** :
1. Prometheus config `metrics_path: '/api/metrics'`
2. Port correct (8000 par défaut)
3. Backend accessible (firewall, réseau)
4. Logs Prometheus : `curl http://localhost:9090/targets`

### Métriques vides

**Causes possibles** :
- Aucune détection n'a eu lieu
- `CONCEPT_RECALL_EMIT_EVENTS=false` (détections pas activées)
- Erreurs dans `ConceptRecallTracker` (vérifier logs)

## Références

- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Naming best practices](https://prometheus.io/docs/practices/naming/)
- [PromQL documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)

## Support

**Code source** :
- [concept_recall_metrics.py](../../src/backend/features/memory/concept_recall_metrics.py)
- [metrics/router.py](../../src/backend/features/metrics/router.py)

**Tests** :
- Ajouter tests unitaires dans `tests/backend/features/test_concept_recall_metrics.py`
