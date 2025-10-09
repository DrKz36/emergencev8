# Monitoring Prometheus Phase 3 - Emergence

**Date**: 2025-10-09
**Statut**: Production active (révision `emergence-app-metrics001`)
**Endpoint**: https://emergence-app-47nct44nma-ew.a.run.app/api/metrics

---

## 1. Métriques exposées

### Memory Analysis (5 métriques)

| Métrique | Type | Description |
|----------|------|-------------|
| `memory_analysis_success_total` | Counter | Nombre total d'analyses mémoire réussies |
| `memory_analysis_failure_total` | Counter | Nombre total d'analyses échouées |
| `memory_analysis_cache_hits_total` | Counter | Nombre de cache hits (TTL 1h) |
| `memory_analysis_cache_misses_total` | Counter | Nombre de cache misses |
| `memory_analysis_duration_seconds` | Histogram | Distribution latence analyses (buckets: 0.5s→30s) |

### Concept Recall (8 métriques)

| Métrique | Type | Description |
|----------|------|-------------|
| `concept_recall_detections_total` | Counter | Détections de concepts récurrents |
| `concept_recall_events_emitted_total` | Counter | Events WebSocket émis vers frontend |
| `concept_recall_false_positives_total` | Counter | Détections ignorées par utilisateur (bouton "Ignorer") |
| `concept_recall_interactions_total` | Counter | Interactions utilisateur avec banners (labels: action) |
| `concept_recall_similarity_score` | Histogram | Distribution scores similarité (buckets: 0.5→1.0) |
| `concept_recall_detection_latency_seconds` | Histogram | Latence totale détection (buckets: 0.01s→5s) |
| `concept_recall_vector_search_duration_seconds` | Histogram | Durée recherche vectorielle ChromaDB uniquement |
| `concept_recall_system_info` | Gauge | Métadonnées système (labels: collection_name, threshold, max_recalls) |

---

## 2. Configuration Grafana

### Import du dashboard

1. **Upload JSON**:
   ```bash
   # Fichier: monitoring/grafana-dashboard-prometheus-phase3.json
   ```

2. **Configuration datasource**:
   - Type: Prometheus
   - URL: `http://prometheus:9090` (ou Cloud Monitoring endpoint)
   - Access: Server (Default)

3. **Variables**:
   - `${DS_PROMETHEUS}`: Auto-détecté lors de l'import

### Panels inclus

- **Gauge**: Total analyses + Cache hit rate
- **Timeseries**: Rates (success/failure), latency percentiles (p50/p95/p99)
- **Histogram**: Similarity scores distribution
- **Breakdown**: Latence totale vs vector search

---

## 3. Scraping Prometheus

### Configuration minimale

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'emergence-app'
    scrape_interval: 30s
    scrape_timeout: 10s
    metrics_path: '/api/metrics'
    scheme: https
    static_configs:
      - targets:
          - 'emergence-app-47nct44nma-ew.a.run.app'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'emergence-prod'
```

### Google Cloud Monitoring (alternative)

```bash
# Activer Prometheus scraping via Cloud Run
gcloud run services update emergence-app \
  --region=europe-west1 \
  --set-env-vars="PROMETHEUS_MULTIPROC_DIR=/tmp"

# Configurer Cloud Monitoring pour scraper l'endpoint
# Docs: https://cloud.google.com/monitoring/api/metrics_prometheus
```

---

## 4. Alertes recommandées

### Latence analyse mémoire élevée

```yaml
- alert: MemoryAnalysisHighLatency
  expr: histogram_quantile(0.95, rate(memory_analysis_duration_seconds_bucket[5m])) > 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Latence p95 analyses mémoire > 10s"
    description: "{{ $value }}s latence p95 sur 5min"
```

### Taux d'échec analyses élevé

```yaml
- alert: MemoryAnalysisHighFailureRate
  expr: rate(memory_analysis_failure_total[5m]) / rate(memory_analysis_success_total[5m]) > 0.1
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Taux échec analyses > 10%"
```

### Cache hit rate bas

```yaml
- alert: MemoryCacheLowHitRate
  expr: |
    100 * (
      memory_analysis_cache_hits_total /
      (memory_analysis_cache_hits_total + memory_analysis_cache_misses_total)
    ) < 30
  for: 15m
  labels:
    severity: info
  annotations:
    summary: "Cache hit rate < 30% (optimisation possible)"
```

### Concept recall: trop de faux positifs

```yaml
- alert: ConceptRecallHighFalsePositives
  expr: rate(concept_recall_false_positives_total[10m]) / rate(concept_recall_detections_total[10m]) > 0.5
  for: 20m
  labels:
    severity: warning
  annotations:
    summary: "> 50% détections concept recall ignorées par utilisateurs"
    description: "Revoir seuil similarité ou filtres"
```

---

## 5. Requêtes PromQL utiles

### Taux de succès analyses (5min)
```promql
rate(memory_analysis_success_total[5m])
```

### Latence p99 analyses
```promql
histogram_quantile(0.99, rate(memory_analysis_duration_seconds_bucket[5m]))
```

### Efficacité concept recall (ratio events émis / détections)
```promql
rate(concept_recall_events_emitted_total[5m]) / rate(concept_recall_detections_total[5m])
```

### Top 3 buckets similarité (dernière heure)
```promql
topk(3, increase(concept_recall_similarity_score_bucket[1h]))
```

### Latence recherche vectorielle moyenne
```promql
rate(concept_recall_vector_search_duration_seconds_sum[5m]) /
rate(concept_recall_vector_search_duration_seconds_count[5m])
```

---

## 6. Validation QA

### Test manuel endpoint

```bash
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep memory_analysis
```

### Script validation automatique (cockpit unifié)

```bash
python qa_metrics_validation.py \
  --base-url https://emergence-app-47nct44nma-ew.a.run.app \
  --login-email gonzalefernando@gmail.com \
  --login-password '***' \
  --trigger-memory \
  --json-output qa-report.json
```

- Enchaîne la stimulation des métriques Prometheus + scénario timeline + analyse mémoire.
- Imprime un résumé console et écrit un rapport JSON (`qa-report.json`) pour la revue FG.
- Options clefs : `--skip-timeline`, `--skip-metrics`, `--chat-prompts ...`, `--use-rag`, `--force-read-only-probe`.

### Scénario timeline cockpit (mode standalone)

```bash
python scripts/qa/qa_timeline_scenario.py \
  --base-url https://emergence-app-47nct44nma-ew.a.run.app \
  --login-email gonzalefernando@gmail.com \
  --login-password '***' \
  --agent anima
```

- Wrapper `qa_metrics_validation.py --skip-metrics`, conserve la CLI historique.
- Échoue si les deltas `messages`, `tokens` ou `costs` restent nuls.
- Paramètres propagés : `--timeline-period 30d`, `--use-rag`, `--ws-timeout`, `--json-output`.

### Routine planifiée (timeline + smoke suite)

```powershell
pwsh -File scripts/qa/run_cockpit_qa.ps1 `
  -BaseUrl https://emergence-app-47nct44nma-ew.a.run.app `
  -LoginEmail gonzalefernando@gmail.com `
  -LoginPassword '***' `
  -TriggerMemory `
  -RunCleanup
```

- Enchaîne `qa_metrics_validation.py`, `tests/run_all.ps1` puis `purge_test_documents.py`.
- Programmable via Windows Task Scheduler (quotidien 07:30) ou cron (`0 6 * * * pwsh …`).
- Permet `-SkipTimeline`, `-SkipMetrics`, `-SkipTests`, `-UseRag`, `-RunCleanup`.

### Nettoyage automatisé des artefacts QA

```bash
python scripts/qa/purge_test_documents.py \
  --base-url https://emergence-app-47nct44nma-ew.a.run.app \
  --pattern test_upload \
  --dry-run
```

- Supprime les documents dont le nom contient `pattern` (ID filtrable via `--min-id`).
- Fallback `/api/auth/dev/login` disponible sauf `--no-dev-login`.
- Intégré par défaut dans `run_cockpit_qa.ps1 -RunCleanup`.

### Logs Cloud Run

```bash
gcloud logging read \
  'resource.type="cloud_run_revision"
   AND resource.labels.revision_name="emergence-app-metrics001"
   AND textPayload=~"metrics"' \
  --limit=50 \
  --format=json
```

---

## 7. Prochaines étapes

1. ✅ **Déploiement**: Métriques actives en prod
2. ✅ **Dashboard**: JSON Grafana créé
3. ✅ **QA fonctionnelle**: `qa_metrics_validation.py` (fallback bypass) + `qa_timeline_scenario.py` (auth complète) pour alimenter cockpit
4. ⏸️ **Alerting**: Configurer alerts Prometheus/Alertmanager
5. ⏸️ **SLO**: Définir objectifs (ex: p95 latency < 5s, cache hit > 40%)

---

## 8. Références

- [Documentation Prometheus](https://prometheus.io/docs/)
- [Grafana Dashboard JSON Model](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/view-dashboard-json-model/)
- [Cloud Run Metrics](https://cloud.google.com/run/docs/monitoring)
- Code source métriques: [src/backend/features/memory/analyzer.py](../../src/backend/features/memory/analyzer.py)
- Config activation: [docs/deployments/2025-10-09-activation-metrics-phase3.md](../deployments/2025-10-09-activation-metrics-phase3.md)
