# Concept Recall - Plan Monitoring & Métriques

**Date** : 2025-10-04
**Status** : 📋 Planification

## Objectif

Implémenter un système de monitoring pour suivre l'efficacité et l'utilisation du système de concept recall.

## Métriques à implémenter

### 1. Métriques de détection

#### Compteurs
- `concept_recall_detections_total` (counter)
  - Labels: `user_id`, `similarity_range` (0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8+)
  - Description: Nombre total de détections de concepts récurrents

- `concept_recall_events_emitted_total` (counter)
  - Labels: `user_id`
  - Description: Nombre d'événements WebSocket émis

#### Histogrammes
- `concept_recall_similarity_score` (histogram)
  - Buckets: [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
  - Description: Distribution des scores de similarité

- `concept_recall_detection_latency_seconds` (histogram)
  - Buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
  - Description: Temps de détection (recherche vectorielle + filtrage)

#### Gauges
- `concept_recall_concepts_total` (gauge)
  - Description: Nombre total de concepts dans le vector store

- `concept_recall_active_threads_count` (gauge)
  - Labels: `user_id`
  - Description: Nombre de threads avec concepts détectés

### 2. Métriques de qualité

#### Compteurs
- `concept_recall_false_positives_total` (counter)
  - Labels: `user_id`
  - Description: Détections ignorées par l'utilisateur (bouton "Ignorer")

- `concept_recall_interactions_total` (counter)
  - Labels: `user_id`, `action` (view_history, dismiss, auto_hide)
  - Description: Interactions utilisateur avec les banners

#### Taux
- `concept_recall_precision_rate` (gauge, calculé)
  - Formule: `(detections - false_positives) / detections`
  - Description: Précision du système (1.0 = parfait)

### 3. Métriques de performance

#### Histogrammes
- `concept_recall_vector_search_duration_seconds` (histogram)
  - Description: Durée recherche vectorielle ChromaDB

- `concept_recall_json_decode_duration_seconds` (histogram)
  - Description: Durée décodage JSON thread_ids

### 4. Métriques métier

#### Compteurs
- `concept_recall_cross_thread_detections_total` (counter)
  - Labels: `thread_count_range` (2, 3-5, 6-10, 10+)
  - Description: Détections cross-thread par plage

- `concept_recall_concept_reuse_total` (counter)
  - Labels: `user_id`
  - Description: Concepts réutilisés (mention_count > 1)

## Implémentation

### Phase 1: Infrastructure (2h)

1. **Créer module metrics** : `src/backend/features/memory/metrics.py`
   ```python
   from prometheus_client import Counter, Histogram, Gauge

   # Compteurs
   DETECTIONS = Counter(
       'concept_recall_detections_total',
       'Total concept recall detections',
       ['user_id', 'similarity_range']
   )

   # Histogrammes
   SIMILARITY_SCORE = Histogram(
       'concept_recall_similarity_score',
       'Similarity score distribution',
       buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
   )

   # ... autres métriques
   ```

2. **Intégrer dans ConceptRecallTracker**
   - Importer module metrics
   - Ajouter instrumentation après chaque détection
   - Logger métriques dans les logs structurés

3. **Exposer endpoint** : `GET /api/metrics` (Prometheus format)

### Phase 2: Collecte (1h)

1. **Instrumenter points clés** :
   - `detect_recurring_concepts()` → détections + latence
   - `_update_mention_metadata()` → réutilisation
   - `_emit_concept_recall_event()` → événements WS

2. **Ajouter labels contextuels** :
   - `similarity_range` : Catégoriser scores (0.5-0.6, 0.6-0.7, etc.)
   - `thread_count_range` : Plages de threads (2, 3-5, 6-10, 10+)

### Phase 3: Visualisation (2h)

1. **Tableau de bord Grafana** :
   - Panel détections/heure (time series)
   - Heatmap scores de similarité
   - Top utilisateurs avec détections
   - Taux de précision (gauge)

2. **Alertes Prometheus** :
   ```yaml
   - alert: ConceptRecallLowPrecision
     expr: concept_recall_precision_rate < 0.6
     for: 1h
     annotations:
       summary: "Precision below 60% for 1h"

   - alert: ConceptRecallHighLatency
     expr: histogram_quantile(0.95, concept_recall_detection_latency_seconds) > 1.0
     for: 5m
     annotations:
       summary: "P95 latency > 1s"
   ```

## Tests

### Tests unitaires
```python
# tests/backend/features/test_concept_recall_metrics.py

async def test_metrics_increment_on_detection():
    before = DETECTIONS._value.get()
    await tracker.detect_recurring_concepts(...)
    after = DETECTIONS._value.get()
    assert after > before

async def test_similarity_histogram_buckets():
    # Vérifier distribution dans buckets corrects
    pass
```

### Tests d'intégration
- Vérifier endpoint `/api/metrics` retourne format Prometheus
- Simuler 100 détections, vérifier agrégations

## Checklist de déploiement

- [ ] Créer `src/backend/features/memory/metrics.py`
- [ ] Instrumenter `ConceptRecallTracker`
- [ ] Ajouter endpoint `/api/metrics`
- [ ] Créer tests unitaires
- [ ] Configurer Prometheus scraping (si disponible)
- [ ] Créer dashboard Grafana (optionnel)
- [ ] Documenter métriques dans README

## Références

- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Best practices metrics naming](https://prometheus.io/docs/practices/naming/)
- [ChromaDB performance](https://docs.trychroma.com/usage-guide#performance)

## Notes

- **Opt-in** : Métriques désactivées par défaut (`CONCEPT_RECALL_METRICS_ENABLED=false`)
- **Privacy** : Hash user_id dans labels Prometheus
- **Rétention** : Recommandé 30 jours (Prometheus) pour analyse tendances
