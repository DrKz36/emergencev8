# Phase 3 RAG : Re-ranking Sémantique Avancé + Monitoring + Cache

**Date**: 2025-10-12
**Status**: ✅ Implémenté
**Auteur**: Assistant IA (Claude)

---

## 🎯 Objectifs Phase 3

Améliorer la **qualité** et les **performances** du système RAG en implémentant :

1. **Re-ranking multi-critères** avec signaux sémantiques avancés
2. **Métriques Prometheus** pour monitoring temps réel de la qualité RAG
3. **Cache intelligent** (Redis optionnel + mémoire locale) pour réduire latence

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RAG Query Flow                          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                  [Parse User Intent]
                           │
                           ▼
           ┌───────────────┴────────────────┐
           │   Check Cache (fingerprint)     │
           │   - Redis (if configured)       │
           │   - In-memory LRU (fallback)    │
           └───────────────┬────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
            [Cache HIT]          [Cache MISS]
                │                     │
                │                     ▼
                │          [Hybrid Vector Query]
                │          (ChromaDB 30 results)
                │                     │
                │                     ▼
                │          [Merge Adjacent Chunks]
                │          (Reconstitution contenus)
                │                     │
                │                     ▼
                │      [Multi-Criteria Semantic Scoring]
                │      • 40% Vector similarity
                │      • 20% Completeness boost
                │      • 15% Keyword relevance
                │      • 10% Recency
                │      • 10% Diversity
                │      • 05% Content type match
                │                     │
                │                     ▼
                │          [Store in Cache + Metrics]
                │                     │
                └─────────────────────┴─────────┐
                                                 │
                                                 ▼
                                    [Return Top 10 Blocks]
                                                 │
                                                 ▼
                                      [Update Prometheus Metrics]
```

---

## 🔧 Composants Implémentés

### 1. Module `rag_metrics.py`

**Localisation**: `src/backend/features/chat/rag_metrics.py`

**Métriques Prometheus exposées** :

#### Counters (événements cumulatifs)
- `rag_queries_total{agent_id, has_intent}` : Total requêtes RAG
- `rag_cache_hits_total` : Nombre de cache hits
- `rag_cache_misses_total` : Nombre de cache misses
- `rag_chunks_merged_total` : Chunks fusionnés (Phase 2)
- `rag_queries_by_content_type_total{content_type}` : Requêtes par type

#### Histograms (latences)
- `rag_query_duration_seconds` : Latence vector query
- `rag_merge_duration_seconds` : Latence fusion chunks
- `rag_scoring_duration_seconds` : Latence scoring sémantique
- `rag_total_duration_seconds` : Latence totale end-to-end

#### Gauges (moyennes rolling)
- `rag_avg_chunks_returned` : Moyenne chunks retournés
- `rag_avg_merge_ratio` : Ratio fusion (merged/raw)
- `rag_avg_relevance_score` : Score pertinence moyen
- `rag_avg_source_diversity` : Diversité sources (docs uniques)

#### Info
- `rag_config` : Configuration système (n_results, max_blocks, cache, etc.)

**Usage** :
```python
from backend.features.chat import rag_metrics

# Enregistrer une requête
rag_metrics.record_query(agent_id="neo", has_intent=True)

# Mesurer durée
with rag_metrics.track_duration(rag_metrics.rag_query_duration_seconds):
    results = vector_service.hybrid_query(...)

# Mettre à jour agrégats
aggregator = rag_metrics.get_aggregator()
aggregator.add_result(
    chunks_returned=10,
    raw_chunks=30,
    merged_blocks=10,
    top_score=0.15,
    unique_docs=5
)
```

---

### 2. Module `rag_cache.py`

**Localisation**: `src/backend/features/chat/rag_cache.py`

**Features** :
- Support Redis (optionnel) avec fallback mémoire locale (OrderedDict LRU)
- Fingerprinting intelligent : `sha256(query + filters + agent_id + doc_ids)`
- TTL configurable via env
- Invalidation sélective par document_id

**Configuration ENV** :
```bash
# Activer/désactiver le cache
RAG_CACHE_ENABLED=true

# URL Redis (optionnel, fallback sur mémoire si absent)
RAG_CACHE_REDIS_URL=redis://localhost:6379/0

# TTL du cache (secondes)
RAG_CACHE_TTL_SECONDS=3600

# Taille max cache mémoire (si pas Redis)
RAG_CACHE_MAX_MEMORY_ITEMS=500
```

**API** :
```python
from backend.features.chat.rag_cache import create_rag_cache

cache = create_rag_cache()

# Get
cached = cache.get(query_text, where_filter, agent_id, selected_doc_ids)
if cached:
    doc_hits = cached['doc_hits']
    rag_sources = cached['rag_sources']

# Set
cache.set(query_text, where_filter, agent_id, doc_hits, rag_sources, selected_doc_ids)

# Invalidate
cache.invalidate_by_document(document_id=123)
cache.invalidate_all()

# Stats
stats = cache.get_stats()
# {'backend': 'redis', 'keyspace_hits': 42, 'keyspace_misses': 15}
```

---

### 3. Fonction `_compute_semantic_score()`

**Localisation**: `src/backend/features/chat/service.py:482-642`

**Algorithme de scoring multi-critères** :

```python
score = (
    0.40 * vector_similarity         # Distance ChromaDB normalisée
  + 0.20 * completeness_normalized   # Bonus fusion + longueur + is_complete
  + 0.15 * keyword_score             # Match mots-clés user_intent
  + 0.10 * recency_score             # Documents récents favorisés
  + 0.10 * diversity_score           # Pénalité surreprésentation
  + 0.05 * content_type_score        # Alignement type recherché
)
```

**Détails des signaux** :

#### 1. Vector Similarity (40%)
- Normalisation distance ChromaDB : `min(distance / 2.0, 1.0)`
- Distance 0 = match parfait, >2 = très dissimilaire

#### 2. Completeness (20%)
- **Fusion de chunks** : `-0.05` par chunk fusionné (max `-0.15`)
- **Longueur** :
  - `>= 40 lignes` : `-0.10`
  - `>= 25 lignes` : `-0.05`
- **Flag is_complete** : `-0.05`
- Normalisation finale : `[0, 1]`

#### 3. Keyword Relevance (15%)
- Match ratio : `matches / total_keywords`
- Score : `1.0 - (match_ratio * 0.5)` → max `-50%`
- Boost spécial "fondateur" : `* 0.7` additionnel

#### 4. Recency (10%)
- `< 7 jours` : score `0.2`
- `< 30 jours` : score `0.4`
- `< 180 jours` : score `0.6`
- `> 180 jours` : dépréciation progressive

#### 5. Diversity (10%)
- `1 occurrence` : score `0.3` (bonus)
- `2-3 occurrences` : score `0.5` (neutre)
- `> 3 occurrences` : pénalité +`0.15` par occurrence

#### 6. Content Type Match (5%)
- Match exact : score `0.0`
- Match partiel (ex: poem/verse) : score `0.2`
- Pas de match : score `0.8`

---

### 4. Intégration dans `ChatService`

**Modifications** :

#### `__init__` (lignes 143-155)
```python
# Initialiser cache et métriques
self.rag_cache: RAGCache = create_rag_cache()
self.rag_metrics_aggregator = rag_metrics.get_aggregator()

# Configurer métriques Prometheus
rag_metrics.set_rag_config(
    n_results=30,
    max_blocks=10,
    chunk_tolerance=30,
    cache_enabled=self.rag_cache.enabled,
    cache_ttl=self.rag_cache.ttl_seconds
)
```

#### Flux RAG principal (lignes 1799-1915)
```python
# 1. Parse user intent (Phase 2)
user_intent = self._parse_user_intent(last_user_message)

# 2. Enregistrer métriques
rag_metrics.record_query(agent_id, has_intent=bool(user_intent.get('content_type')))

# 3. Check cache
cached_result = self.rag_cache.get(query_text, where_filter, agent_id, selected_doc_ids)

if cached_result:
    # Cache HIT
    rag_metrics.record_cache_hit()
    doc_hits = cached_result['doc_hits']
    rag_sources = cached_result['rag_sources']
else:
    # Cache MISS
    rag_metrics.record_cache_miss()

    # Query vectorielle avec métriques
    with rag_metrics.track_duration(rag_metrics.rag_query_duration_seconds):
        raw_doc_hits = self.vector_service.hybrid_query(...)

    # Merge + scoring avec métriques
    with rag_metrics.track_duration(rag_metrics.rag_merge_duration_seconds):
        doc_hits = self._merge_adjacent_chunks(
            raw_doc_hits,
            max_blocks=10,
            user_intent=user_intent  # ✅ Nouveau : scoring avancé
        )

    # Construire rag_sources
    rag_sources = [...]

    # Stocker dans cache
    self.rag_cache.set(query_text, where_filter, agent_id, doc_hits, rag_sources, selected_doc_ids)

# 4. Collecter métriques qualité
self.rag_metrics_aggregator.add_result(
    chunks_returned=len(doc_hits),
    raw_chunks=len(raw_doc_hits),
    merged_blocks=len(doc_hits),
    top_score=doc_hits[0]['distance'],
    unique_docs=len(set(doc_ids))
)
```

---

## 📈 Métriques de Performance Attendues

### Avant Phase 3 (Phase 2)
- **Latence moyenne requête RAG** : ~800ms
- **Taux de cache** : 0% (pas de cache)
- **Diversité sources** : Variable (pas de contrôle)
- **Scoring** : Multiplicateurs fixes (boost 12.5x poèmes)

### Après Phase 3 (attendu)
- **Latence moyenne requête RAG** :
  - Cache HIT : ~10ms (99% plus rapide)
  - Cache MISS : ~850ms (légère augmentation due au scoring)
- **Taux de cache** : 30-50% (selon patterns utilisateurs)
- **Diversité sources** : 4-6 documents uniques / top-10 (vs 1-3 avant)
- **Scoring** : Multi-critères pondéré → meilleure pertinence

---

## 🔍 Monitoring en Production

### Accès aux métriques Prometheus

Les métriques sont exposées sur l'endpoint standard `/metrics` :

```bash
# Exemple de requêtes Prometheus
curl http://localhost:8080/metrics | grep rag_

# Exemples de métriques utiles
rag_queries_total{agent_id="neo",has_intent="true"} 142
rag_cache_hits_total 38
rag_cache_misses_total 104
rag_avg_chunks_returned 8.7
rag_avg_merge_ratio 0.35
rag_avg_relevance_score 0.23
rag_avg_source_diversity 4.2
```

### Dashboard Grafana recommandé

**Panels à créer** :

1. **RAG Query Rate**
   - Metric: `rate(rag_queries_total[5m])`
   - Type: Time series
   - Group by: `agent_id`

2. **Cache Hit Rate**
   - Formula: `rate(rag_cache_hits_total[5m]) / (rate(rag_cache_hits_total[5m]) + rate(rag_cache_misses_total[5m]))`
   - Type: Gauge (0-100%)

3. **P95 Query Latency**
   - Metric: `histogram_quantile(0.95, rate(rag_query_duration_seconds_bucket[5m]))`
   - Type: Time series

4. **Source Diversity**
   - Metric: `rag_avg_source_diversity`
   - Type: Gauge
   - Target: 4-6 documents uniques

5. **Merge Efficiency**
   - Metric: `rag_avg_merge_ratio`
   - Type: Stat
   - Description: Ratio chunks fusionnés / chunks bruts

---

## 🧪 Tests de Validation

### Test 1 : Cache Hit/Miss

```bash
# Requête 1 (cache miss attendu)
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Cite-moi le poème fondateur intégral",
    "agent_id": "neo",
    "use_rag": true
  }'

# Vérifier logs : "[RAG Cache] Memory MISS"

# Requête 2 (identique → cache hit attendu)
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Cite-moi le poème fondateur intégral",
    "agent_id": "neo",
    "use_rag": true
  }'

# Vérifier logs : "[RAG Cache] Memory HIT"
```

### Test 2 : Diversité des Sources

```python
# Script Python pour analyser diversité
import requests

response = requests.post(
    "http://localhost:8080/api/chat",
    json={
        "message": "Parle-moi des concepts clés du projet",
        "agent_id": "neo",
        "use_rag": True
    }
)

sources = response.json().get("meta", {}).get("sources", [])
unique_docs = len(set(s["document_id"] for s in sources))

print(f"Documents uniques : {unique_docs}/10")
# Attendu : >= 4 (diversité)
```

### Test 3 : Scoring Keyword Relevance

```bash
# Requête avec keyword spécifique
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quel est le poème fondateur ?",
    "agent_id": "neo",
    "use_rag": true
  }'

# Vérifier logs :
# - "[RAG Intent] keywords=['fondateur', 'poème']"
# - Top résultat doit contenir "fondateur" dans keywords
```

---

## 🐛 Debugging

### Logs à surveiller

```bash
# Activer logs détaillés
export LOG_LEVEL=DEBUG

# Patterns importants
grep "RAG Cache" app.log
grep "RAG Merge" app.log
grep "RAG Intent" app.log
```

### Problèmes courants

#### 1. Cache toujours MISS
**Symptôme** : `rag_cache_hits_total` reste à 0

**Causes possibles** :
- `RAG_CACHE_ENABLED=false` dans env
- Fingerprinting inclut paramètres variables (ex: timestamp)
- TTL trop court

**Solution** :
```bash
# Vérifier config
curl http://localhost:8080/metrics | grep rag_config

# Vérifier stats cache
# Dans logs : "[Phase 3 RAG] Cache initialisé: {'backend': 'memory', 'size': 0}"
```

#### 2. Métriques Prometheus non exposées
**Symptôme** : `/metrics` ne contient pas `rag_*`

**Causes possibles** :
- Import `prometheus_client` échoue
- Module `rag_metrics` non importé

**Solution** :
```bash
# Vérifier logs au démarrage
grep "RAG Metrics" app.log
# Attendu : "[RAG Metrics] Module initialized (Prometheus available: True)"

# Installer prometheus_client si manquant
pip install prometheus-client>=0.20
```

#### 3. Scoring semble cassé
**Symptôme** : Résultats incohérents vs Phase 2

**Debug** :
- Vérifier logs `[RAG Merge] Top X: ...` pour scores
- Si `user_intent=None`, système fallback sur ancien scoring
- Vérifier parsing intent : `[RAG Intent] content_type=...`

---

## 🔄 Migration depuis Phase 2

### Changements breaking
**Aucun** : Phase 3 est 100% rétrocompatible.

- Si `user_intent` non fourni → fallback automatique sur scoring Phase 2
- Cache désactivable via `RAG_CACHE_ENABLED=false`
- Métriques Prometheus graceful (pas d'erreur si package absent)

### Déploiement progressif recommandé

1. **Déployer sans cache** (pour tester scoring)
   ```bash
   RAG_CACHE_ENABLED=false
   ```

2. **Activer cache mémoire** (pas de Redis requis)
   ```bash
   RAG_CACHE_ENABLED=true
   # RAG_CACHE_REDIS_URL non défini → utilise mémoire locale
   ```

3. **Migrer vers Redis** (production)
   ```bash
   RAG_CACHE_ENABLED=true
   RAG_CACHE_REDIS_URL=redis://redis-service:6379/0
   RAG_CACHE_TTL_SECONDS=7200  # 2h
   ```

---

## 📝 Variables d'Environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `RAG_CACHE_ENABLED` | `true` | Activer/désactiver le cache |
| `RAG_CACHE_REDIS_URL` | `None` | URL Redis (optionnel) |
| `RAG_CACHE_TTL_SECONDS` | `3600` | TTL cache (1h) |
| `RAG_CACHE_MAX_MEMORY_ITEMS` | `500` | Taille max cache mémoire |

---

## 🚀 Prochaines Étapes (Phase 4+)

### Améliorations potentielles

1. **Learning-to-Rank** :
   - Collecter feedback utilisateur (👍/👎 sur résultats RAG)
   - Entraîner modèle LTR pour ajuster pondérations

2. **Query Expansion avancée** :
   - Utiliser embeddings pour synonymes automatiques
   - Reformulation de requête via LLM

3. **Cache distribué avancé** :
   - Pre-warming du cache (requêtes fréquentes)
   - Invalidation intelligente par similarité sémantique

4. **A/B Testing** :
   - Comparer scoring Phase 2 vs Phase 3
   - Métriques : taux de satisfaction, longueur réponse, citations exactes

---

## 📚 Références

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Learning to Rank for IR](https://en.wikipedia.org/wiki/Learning_to_rank)

---

**Fin de la documentation Phase 3 RAG**
