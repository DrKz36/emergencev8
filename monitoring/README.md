# Emergence V8 - Monitoring Stack

Ce répertoire contient la configuration complète du stack de monitoring pour Emergence V8, incluant Prometheus pour la collecte de métriques et Grafana pour la visualisation.

## 🏗️ Architecture

```
┌─────────────────┐
│  Emergence API  │
│   (port 8000)   │──┐
└─────────────────┘  │
                     │ Scrape metrics
                     ▼
                ┌─────────────┐
                │ Prometheus  │
                │ (port 9090) │
                └─────────────┘
                     │
                     │ Query metrics
                     ▼
                ┌─────────────┐
                │   Grafana   │
                │ (port 3000) │
                └─────────────┘
```

## 🚀 Démarrage Rapide

### 1. Activer les métriques dans l'API

Définir la variable d'environnement dans votre backend :

```bash
export CONCEPT_RECALL_METRICS_ENABLED=true
```

Ou dans votre fichier `.env` :

```env
CONCEPT_RECALL_METRICS_ENABLED=true
```

### 2. Démarrer le stack de monitoring

```bash
cd monitoring
docker-compose up -d
```

### 3. Accéder aux services

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `emergence2025`

### 4. Visualiser les dashboards

Grafana sera automatiquement configuré avec :
- Source de données Prometheus
- Dashboard "Emergence RAG Hybrid Metrics"

Accédez au dashboard via : **Dashboards → Emergence V8 → Emergence RAG Hybrid Metrics**

## 📊 Métriques RAG Disponibles

### Compteurs (Counters)

| Métrique | Description | Labels |
|----------|-------------|--------|
| `rag_queries_hybrid_total` | Total des requêtes RAG hybrides | `collection`, `status` |
| `rag_queries_vector_only_total` | Total des requêtes vectorielles pures | `collection`, `status` |
| `rag_queries_bm25_only_total` | Total des requêtes BM25 pures | `collection`, `status` |
| `rag_results_filtered_total` | Total des résultats filtrés | `collection`, `reason` |

### Jauges (Gauges)

| Métrique | Description | Labels |
|----------|-------------|--------|
| `rag_avg_score` | Score moyen de pertinence | `collection`, `query_type` |
| `rag_score_component` | Scores composants (BM25/Vector) | `collection`, `component` |

### Histogrammes (Histograms)

| Métrique | Description | Labels |
|----------|-------------|--------|
| `rag_query_duration_seconds` | Durée d'exécution des requêtes | `collection`, `query_type` |
| `rag_results_count` | Nombre de résultats retournés | `collection`, `query_type` |

## 🎨 Dashboard Grafana

Le dashboard "Emergence RAG Hybrid Metrics" inclut :

### Vue d'ensemble
- **Hybrid RAG Queries** : Taux de requêtes hybrides (5min)
- **Average RAG Score** : Score de pertinence moyen (gauge)
- **Filtered Results** : Résultats filtrés par seuil
- **Success Rate** : Taux de succès des requêtes

### Détails des requêtes
- **RAG Query Types** : Comparaison Hybrid/Vector/BM25 par statut
- **Score Components** : Évolution des scores BM25 vs Vector
- **Filtered Results by Reason** : Répartition des raisons de filtrage

### Performance
- **Query Duration** : Distribution des latences (p50, p95, p99)
- **Results Count Distribution** : Nombre de résultats retournés
- **Queries by Collection** : Tableau par collection et statut

### Santé système
- **System Health** : Statut du backend (Up/Down)

## 🔧 Configuration

### Prometheus

Fichier : `prometheus/prometheus.yml`

Configuration principale :
- **Scrape interval** : 15s (configurable)
- **Target** : `host.docker.internal:8000/api/metrics`
- **Job name** : `emergence-backend`

### Grafana

Fichiers de provisioning :
- `grafana/provisioning/datasources/prometheus.yml` : Source de données
- `grafana/provisioning/dashboards/dashboards.yml` : Configuration dashboards
- `grafana/dashboards/rag-metrics-dashboard.json` : Dashboard RAG

## 📝 Requêtes Prometheus Utiles

### Taux de requêtes hybrides (succès)
```promql
sum(rate(rag_queries_hybrid_total{status="success"}[5m]))
```

### Score moyen de pertinence
```promql
rag_avg_score
```

### Taux de filtrage
```promql
sum(rate(rag_results_filtered_total[5m]))
```

### Latence p95
```promql
histogram_quantile(0.95, sum(rate(rag_query_duration_seconds_bucket[5m])) by (le, query_type))
```

### Taux de succès
```promql
sum(rate(rag_queries_hybrid_total{status="success"}[5m])) /
sum(rate(rag_queries_hybrid_total[5m]))
```

## 🚨 Alerting (Optionnel)

Pour activer les alertes :

1. Créer des règles dans `prometheus/alerts/*.yml`
2. Configurer AlertManager dans `alertmanager/alertmanager.yml`
3. Redémarrer les services : `docker-compose restart`

Exemple de règle d'alerte :

```yaml
groups:
  - name: rag_alerts
    interval: 30s
    rules:
      - alert: RAGLowSuccessRate
        expr: |
          (sum(rate(rag_queries_hybrid_total{status="success"}[5m])) /
           sum(rate(rag_queries_hybrid_total[5m]))) < 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RAG success rate below 80%"
          description: "Current success rate: {{ $value | humanizePercentage }}"
```

## 📦 Volumes Docker

Les données sont persistées dans des volumes Docker :

- `prometheus-data` : Données de séries temporelles Prometheus
- `grafana-data` : Configuration et dashboards Grafana
- `alertmanager-data` : État AlertManager

Pour réinitialiser :
```bash
docker-compose down -v
docker-compose up -d
```

## 🔍 Debugging

### Vérifier que les métriques sont exposées

```bash
curl http://localhost:8000/api/metrics
```

Devrait retourner les métriques au format Prometheus.

### Vérifier que Prometheus scrape correctement

1. Ouvrir http://localhost:9090
2. Aller dans **Status → Targets**
3. Vérifier que `emergence-backend` est **UP**

### Vérifier les requêtes dans Grafana

1. Ouvrir http://localhost:3000
2. Aller dans **Explore**
3. Tester une requête : `rag_queries_hybrid_total`

## 🛠️ Maintenance

### Mettre à jour le dashboard

1. Modifier `grafana/dashboards/rag-metrics-dashboard.json`
2. Redémarrer Grafana : `docker-compose restart grafana`
3. Le dashboard sera automatiquement mis à jour

### Changer le mot de passe admin

```bash
docker exec -it emergence-grafana grafana-cli admin reset-admin-password newpassword
```

### Backup des données

```bash
# Backup Prometheus
docker run --rm -v emergence-prometheus-data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz /data

# Backup Grafana
docker run --rm -v emergence-grafana-data:/data -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz /data
```

## 📚 Ressources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Guide](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)

## 🤝 Support

Pour tout problème ou question :
1. Vérifier les logs : `docker-compose logs -f`
2. Consulter la documentation Prometheus/Grafana
3. Ouvrir une issue dans le projet
