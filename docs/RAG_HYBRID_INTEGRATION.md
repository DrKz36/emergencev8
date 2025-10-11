# RAG Hybrid System - Complete Integration Report

## 📋 Vue d'ensemble

Ce document détaille l'intégration complète du système RAG hybride (BM25 + Vector) dans Emergence V8, incluant l'interface utilisateur, les métriques Prometheus, les tests E2E, et le monitoring Grafana.

## 🎯 Objectifs Atteints

### 1. ✅ Interface Utilisateur - Settings RAG

**Fichiers créés:**
- `src/frontend/features/settings/settings-rag.js` - Module de configuration RAG
- Intégré dans `src/frontend/features/settings/settings-main.js`

**Fonctionnalités:**
- **Toggle Mode Strict**: Active/désactive le filtrage par seuil de score
- **Slider Seuil**: Ajuste le score minimum (0.0 - 1.0) pour accepter un résultat
- **Métriques Live**: Affiche les statistiques RAG en temps réel
  - Requêtes hybrides totales
  - Score moyen
  - Résultats filtrés
  - Taux de succès
- **Bouton Refresh**: Recharge les métriques à la demande
- **Explications contextuelles**: Guide l'utilisateur selon le seuil choisi
  - 0.0-0.6: Permissif
  - 0.6-0.8: Équilibré
  - 0.8-1.0: Strict

**Navigation:**
Paramètres → RAG → Configuration

---

### 2. ✅ Métriques Prometheus pour RAG Hybride

**Fichiers créés:**
- `src/backend/features/memory/rag_metrics.py` - Définition des métriques Prometheus
- Intégré dans `src/backend/features/memory/hybrid_retriever.py`

**Métriques exposées:**

#### Compteurs (Counters)
| Métrique | Description | Labels |
|----------|-------------|--------|
| `rag_queries_hybrid_total` | Total requêtes hybrides | `collection`, `status` |
| `rag_queries_vector_only_total` | Total requêtes vectorielles | `collection`, `status` |
| `rag_queries_bm25_only_total` | Total requêtes BM25 | `collection`, `status` |
| `rag_results_filtered_total` | Résultats filtrés par seuil | `collection`, `reason` |

#### Jauges (Gauges)
| Métrique | Description | Labels |
|----------|-------------|--------|
| `rag_avg_score` | Score moyen de pertinence | `collection`, `query_type` |
| `rag_score_component` | Scores BM25 et vectoriels | `collection`, `component` |

#### Histogrammes (Histograms)
| Métrique | Description | Labels | Buckets |
|----------|-------------|--------|---------|
| `rag_query_duration_seconds` | Durée d'exécution | `collection`, `query_type` | 0.001s - 2.5s |
| `rag_results_count` | Nombre de résultats | `collection`, `query_type` | 0 - 100 |

**Helper class: `RAGMetricsTracker`**
```python
with RAGMetricsTracker("concepts", "hybrid") as tracker:
    results = hybrid_query(...)
    tracker.record_results(results)
    tracker.record_filtered(filtered_count)
```

---

### 3. ✅ API Backend - Settings & Metrics

**Fichiers créés:**
- `src/backend/features/settings/router.py` - Endpoints de configuration
- Mis à jour: `src/backend/features/metrics/router.py` - Endpoint métriques RAG
- Intégré dans `src/backend/main.py`

**Endpoints disponibles:**

#### Settings RAG
- `GET /api/settings/rag` - Récupère la configuration RAG
- `POST /api/settings/rag` - Met à jour la configuration RAG
  ```json
  {
    "strict_mode": true,
    "score_threshold": 0.7
  }
  ```

#### Settings Modèles
- `GET /api/settings/models` - Configuration par agent
- `POST /api/settings/models` - Met à jour les modèles

#### Métriques
- `GET /api/metrics/rag` - Résumé JSON des métriques RAG
- `GET /api/metrics` - Métriques Prometheus (format texte)

**Persistance:**
Les settings sont sauvegardés dans `src/data/settings.json`

---

### 4. ✅ Tests E2E avec Playwright

**Fichier créé:**
- `tests/e2e/rag-hybrid.spec.js` - Suite de tests complète

**Tests implémentés:**

#### Backend API
- ✅ VectorService initialisé (health check)
- ✅ Récupération settings RAG
- ✅ Mise à jour settings RAG
- ✅ Récupération métriques RAG
- ✅ Exposition métriques Prometheus

#### Interface Utilisateur
- ✅ Affichage onglet RAG
- ✅ Toggle mode strict
- ✅ Ajustement slider seuil
- ✅ Affichage métriques live
- ✅ Refresh métriques
- ✅ Sauvegarde settings

#### Health Checks
- ✅ Statut système
- ✅ Disponibilité endpoints

**Exécution:**
```bash
npx playwright test tests/e2e/rag-hybrid.spec.js
```

---

### 5. ✅ Dashboard Grafana

**Fichiers créés:**
- `monitoring/grafana/dashboards/rag-metrics-dashboard.json`
- `monitoring/docker-compose.yml`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/grafana/provisioning/*`
- `monitoring/README.md`

**Panneaux du Dashboard:**

#### Vue d'ensemble (Row 1)
1. **Hybrid RAG Queries** - Taux requêtes/sec (5min)
2. **Average RAG Score** - Gauge score moyen
3. **Filtered Results** - Résultats filtrés/sec
4. **Success Rate** - Taux de succès en temps réel

#### Détails requêtes (Row 2)
5. **RAG Query Types** - Comparaison Hybrid/Vector/BM25
6. **Score Components** - Évolution BM25 vs Vector

#### Analyse (Row 3)
7. **Filtered Results by Reason** - Pie chart raisons
8. **Queries by Collection** - Tableau par collection
9. **Results Count Distribution** - Histogramme p50/p95

#### Performance (Row 4)
10. **Query Duration** - Latence p50/p95/p99
11. **System Health** - Statut backend Up/Down

**Refresh automatique:** 30 secondes

---

### 6. ✅ Alerting avec AlertManager

**Fichiers créés:**
- `monitoring/alertmanager/alertmanager.yml`
- `monitoring/prometheus/alerts/rag-alerts.yml`

**Alertes configurées:**

#### Performance
- ⚠️ `RAGLowSuccessRate` - Taux de succès < 80% (5min)
- ⚠️ `RAGLowAverageScore` - Score moyen < 0.5 (5min)
- ⚠️ `RAGHighFilterRate` - Plus de 50% filtrés (5min)
- ⚠️ `RAGHighLatency` - Latence p95 > 1s (5min)

#### Santé
- 🚨 `RAGNoQueries` - Aucune requête (10min) [CRITICAL]
- 🚨 `EmergenceBackendDown` - Backend down (1min) [CRITICAL]
- ⚠️ `RAGHighErrorRate` - Taux d'erreur > 10% (5min)

#### Capacité
- ⚠️ `RAGHighQueryRate` - > 100 req/sec (2min)
- ⚠️ `RAGLowResultsCount` - < 1 résultat moyen (10min)

---

## 🚀 Déploiement et Utilisation

### Prérequis
1. Docker & docker-compose installés
2. Backend Emergence V8 en cours d'exécution
3. Variable d'environnement activée:
   ```bash
   export CONCEPT_RECALL_METRICS_ENABLED=true
   ```

### Démarrage Monitoring

#### Windows
```cmd
cd monitoring
start-monitoring.bat
```

#### Linux/Mac
```bash
cd monitoring
chmod +x start-monitoring.sh
./start-monitoring.sh
```

#### Manuel
```bash
cd monitoring
docker-compose up -d
```

### Accès aux Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin / emergence2025 |
| AlertManager | http://localhost:9093 | - |

### Configuration Settings RAG

1. Ouvrir l'application: http://localhost:5173
2. Naviguer vers **Paramètres** → **RAG**
3. Activer/désactiver **Mode Strict**
4. Ajuster le **Seuil de Score** (0.0 - 1.0)
5. Cliquer sur **Sauvegarder**

**Effet:**
- Mode strict désactivé: Tous les résultats sont retournés
- Mode strict activé: Seuls les résultats avec `score >= threshold` sont retournés

---

## 📊 Requêtes PromQL Utiles

### Monitoring RAG

```promql
# Taux de requêtes hybrides (succès)
sum(rate(rag_queries_hybrid_total{status="success"}[5m]))

# Score moyen
rag_avg_score

# Taux de filtrage
sum(rate(rag_results_filtered_total[5m])) /
sum(rate(rag_queries_hybrid_total[5m]))

# Latence p95
histogram_quantile(0.95,
  sum(rate(rag_query_duration_seconds_bucket[5m])) by (le)
)

# Taux de succès
sum(rate(rag_queries_hybrid_total{status="success"}[5m])) /
(sum(rate(rag_queries_hybrid_total[5m])) + 0.001)

# Résultats moyens par requête
sum(rate(rag_results_count_sum[5m])) /
sum(rate(rag_results_count_count[5m]))
```

---

## 🧪 Tests et Validation

### Tests E2E
```bash
# Installer Playwright (si pas déjà fait)
npm install -D @playwright/test

# Exécuter les tests RAG
npx playwright test tests/e2e/rag-hybrid.spec.js

# Mode debug
npx playwright test tests/e2e/rag-hybrid.spec.js --debug

# Avec interface
npx playwright test tests/e2e/rag-hybrid.spec.js --ui
```

### Validation manuelle

1. **Backend Health:**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Metrics endpoint:**
   ```bash
   curl http://localhost:8000/api/metrics
   # Devrait contenir "rag_queries_hybrid_total"
   ```

3. **Settings API:**
   ```bash
   curl http://localhost:8000/api/settings/rag
   ```

4. **RAG Metrics:**
   ```bash
   curl http://localhost:8000/api/metrics/rag
   ```

---

## 🔧 Maintenance et Troubleshooting

### Logs monitoring
```bash
cd monitoring
docker-compose logs -f
```

### Redémarrer services
```bash
cd monitoring
docker-compose restart
```

### Vérifier targets Prometheus
1. Ouvrir http://localhost:9090
2. Status → Targets
3. Vérifier que `emergence-backend` est **UP**

### Backup données
```bash
# Prometheus
docker run --rm -v emergence-prometheus-data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/prometheus-backup.tar.gz /data

# Grafana
docker run --rm -v emergence-grafana-data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/grafana-backup.tar.gz /data
```

### Reset complet
```bash
cd monitoring
docker-compose down -v  # Supprime volumes
docker-compose up -d
```

---

## 📁 Structure des Fichiers

```
emergenceV8/
├── src/
│   ├── frontend/
│   │   └── features/
│   │       └── settings/
│   │           ├── settings-rag.js          ✅ NEW
│   │           └── settings-main.js         🔧 UPDATED
│   └── backend/
│       ├── main.py                          🔧 UPDATED
│       └── features/
│           ├── memory/
│           │   ├── rag_metrics.py           ✅ NEW
│           │   └── hybrid_retriever.py      🔧 UPDATED
│           ├── metrics/
│           │   └── router.py                🔧 UPDATED
│           └── settings/
│               └── router.py                ✅ NEW
├── tests/
│   └── e2e/
│       └── rag-hybrid.spec.js               ✅ NEW
├── monitoring/                              ✅ NEW
│   ├── docker-compose.yml
│   ├── start-monitoring.sh
│   ├── start-monitoring.bat
│   ├── README.md
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts/
│   │       └── rag-alerts.yml
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   │   └── prometheus.yml
│   │   │   └── dashboards/
│   │   │       └── dashboards.yml
│   │   └── dashboards/
│   │       └── rag-metrics-dashboard.json
│   └── alertmanager/
│       └── alertmanager.yml
└── docs/
    └── RAG_HYBRID_INTEGRATION.md            ✅ THIS FILE
```

---

## 🎓 Concepts Clés

### RAG Hybride
Combine deux approches de recherche:
- **BM25 (Lexical)**: Recherche par mots-clés, basée sur TF-IDF
- **Vector (Semantic)**: Recherche par similarité sémantique via embeddings

**Avantages:**
- BM25 excelle sur les correspondances exactes
- Vector capture le sens et les synonymes
- La fusion (RRF) donne les meilleurs résultats des deux mondes

### Score Threshold
- Filtre les résultats avec `score < threshold`
- Permet de garantir une qualité minimale
- Trade-off: Qualité vs Quantité de résultats

### Métriques Prometheus
- **Counters**: Valeurs qui ne font qu'augmenter (requêtes totales)
- **Gauges**: Valeurs qui varient (score moyen)
- **Histograms**: Distribution de valeurs (latence, nombre résultats)

---

## 🚀 Prochaines Étapes (Recommandations)

1. **Tuning des Paramètres BM25**
   - Ajuster `k1` et `b` selon le corpus
   - Actuellement: `k1=1.5`, `b=0.75` (valeurs par défaut)

2. **Optimisation Alpha**
   - Tester différents poids BM25/Vector
   - Actuellement: `alpha=0.5` (50/50)

3. **Monitoring Avancé**
   - Intégrer Slack/Email pour alertes critiques
   - Ajouter des dashboards par collection

4. **A/B Testing**
   - Comparer performances Hybrid vs Vector-only
   - Mesurer impact sur qualité des réponses agents

5. **Auto-tuning**
   - Ajuster automatiquement le threshold selon feedback utilisateur
   - Machine learning pour optimiser alpha

---

## 📚 Références

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Playwright Testing](https://playwright.dev/)

---

## 👥 Contributeurs

**Développé par:** Fernando Gonzalez
**Version:** 1.0
**Date:** 2025-10-11
**Projet:** Émergence V8
