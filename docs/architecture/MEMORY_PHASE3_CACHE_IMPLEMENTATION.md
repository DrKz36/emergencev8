# Mémoire Phase 3 : Implémentation du Cache de Recherche Consolidée

**Date:** 2025-10-15
**Statut:** ✅ Implémenté et Testé
**Objectif:** Réduire la latence des questions temporelles de 1.95s → 0.5s via cache intelligent

---

## 📋 Résumé

Cette implémentation ajoute un **cache de recherche consolidée** pour les questions temporelles, réutilisant l'infrastructure RAGCache existante. Le cache évite les recherches répétées dans ChromaDB pour les mêmes questions utilisateur.

### Gains Attendus

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Latence (cache hit) | 1.95s | ~0.5s | 75% |
| Requêtes ChromaDB | 100% | 60-70% | -30-40% |
| Cache hit rate | 0% | 30-40% | +30-40% |

---

## 🏗️ Architecture

### Composants Modifiés

1. **[service.py](../../src/backend/features/chat/service.py)**
   - Nouvelle méthode: `_get_cached_consolidated_memory()` (lignes 1130-1246)
   - Modification: `_build_temporal_history_context()` (lignes 1277-1288)

2. **[rag_cache.py](../../src/backend/features/chat/rag_cache.py)** (existant)
   - Réutilisé sans modification
   - Support Redis + fallback mémoire
   - TTL configurable (5 minutes par défaut)

3. **[rag_metrics.py](../../src/backend/features/chat/rag_metrics.py)** (existant)
   - Métriques Prometheus existantes réutilisées
   - `record_cache_hit()` / `record_cache_miss()`

### Nouveaux Tests

4. **[test_consolidated_memory_cache.py](../../tests/backend/features/chat/test_consolidated_memory_cache.py)** (nouveau)
   - 7 tests unitaires pour valider le cache
   - Coverage: hit/miss, performance, isolation, métriques

---

## 🔧 Implémentation Détaillée

### 1. Méthode `_get_cached_consolidated_memory()`

**Fichier:** `src/backend/features/chat/service.py:1130-1246`

**Responsabilités:**
- Vérifier le cache avant d'interroger ChromaDB
- Gérer le fingerprinting des requêtes (avec préfixe `__CONSOLIDATED_MEMORY__`)
- Stocker les résultats en cache après un miss
- Enregistrer les métriques Prometheus

**Flux de Données:**

```
User Query
    │
    ├──> Cache.get(prefixed_query, user_id)
    │
    ├─[HIT]──> Return cached_entries (< 10ms)
    │           └──> record_cache_hit()
    │
    └─[MISS]─> ChromaDB.query(query, n_results)
                └──> Parse results → entries
                └──> Cache.set(prefixed_query, entries)
                └──> record_cache_miss()
                └──> Return entries (~1.95s)
```

**Code Clé:**

```python
async def _get_cached_consolidated_memory(
    self,
    user_id: str,
    query_text: str,
    n_results: int = 5
) -> List[Dict[str, Any]]:
    """Récupère concepts consolidés depuis cache ou ChromaDB."""

    # Préfixe pour isoler du cache RAG documents
    cache_query = f"__CONSOLIDATED_MEMORY__:{query_text}"
    where_filter = {"user_id": user_id} if user_id else None

    # Tenter cache hit
    cached_result = self.rag_cache.get(
        cache_query,
        where_filter,
        agent_id="memory_consolidation",
        selected_doc_ids=None
    )

    if cached_result:
        # Cache HIT - retour immédiat
        rag_metrics.record_cache_hit()
        return cached_result.get('doc_hits', [])

    # Cache MISS - recherche ChromaDB
    results = self._knowledge_collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter,
        include=["metadatas", "documents"]
    )

    # Parse et stocke en cache
    consolidated_entries = [...]  # Parsing logic
    self.rag_cache.set(cache_query, where_filter, "memory_consolidation",
                       doc_hits=consolidated_entries, rag_sources=[])

    rag_metrics.record_cache_miss()
    return consolidated_entries
```

### 2. Modification de `_build_temporal_history_context()`

**Avant (Phase 2):**
```python
# Recherche ChromaDB directe, sans cache
results = self._knowledge_collection.query(
    query_texts=[last_user_message],
    n_results=5,
    where={"user_id": user_id},
    include=["metadatas", "documents"]
)
# Parse results...
```

**Après (Phase 3):**
```python
# Utilise n_results dynamique
n_results = min(5, max(3, len(messages) // 4)) if messages else 5

# Utilise la méthode cachée
consolidated_entries = await self._get_cached_consolidated_memory(
    user_id=user_id,
    query_text=last_user_message,
    n_results=n_results
)
```

**Bénéfices:**
- ✅ Cache automatique
- ✅ n_results adaptatif (évite warning ChromaDB si peu d'entrées)
- ✅ Code plus modulaire et testable

---

## 🧪 Tests

### Suite de Tests

**Fichier:** `tests/backend/features/chat/test_consolidated_memory_cache.py`

| Test | Objectif | Statut |
|------|----------|--------|
| `test_cache_miss_first_call` | Vérifier que la 1ère recherche = miss | ✅ PASS |
| `test_cache_hit_second_call` | Vérifier que la 2ème recherche = hit | ✅ PASS |
| `test_cache_performance_improvement` | Mesurer speedup hit vs miss | ✅ PASS |
| `test_dynamic_n_results` | Valider logique n_results adaptatif | ✅ PASS |
| `test_cache_prefix_isolation` | Vérifier préfixe `__CONSOLIDATED_MEMORY__` | ✅ PASS |
| `test_metrics_recorded_on_hit` | Vérifier métriques Prometheus | ✅ PASS |
| `test_metrics_recorded_on_miss` | Vérifier métriques Prometheus | ✅ PASS |

**Exécution:**
```bash
pytest tests/backend/features/chat/test_consolidated_memory_cache.py -v
# Résultat: 7 passed, 2 warnings in 12.19s
```

---

## 📊 Métriques Prometheus

### Métriques Existantes Réutilisées

1. **`rag_cache_hits_total`** (Counter)
   - Incrémenté par `record_cache_hit()`
   - Labels: aucun
   - Usage: Compter les hits de cache (documents + mémoire consolidée)

2. **`rag_cache_misses_total`** (Counter)
   - Incrémenté par `record_cache_miss()`
   - Labels: aucun
   - Usage: Compter les misses de cache

### Calcul du Hit Rate

```promql
# Hit rate global (tous caches confondus)
rag_cache_hits_total / (rag_cache_hits_total + rag_cache_misses_total)

# Exemple: 30 hits, 70 misses → 30/100 = 30% hit rate
```

### Exposition

Les métriques sont exposées via `/metrics` (endpoint FastAPI standard).

**Exemple de scraping:**
```bash
curl http://localhost:8000/metrics | grep rag_cache
```

**Sortie attendue (après quelques requêtes):**
```
# HELP rag_cache_hits_total Number of RAG cache hits
# TYPE rag_cache_hits_total counter
rag_cache_hits_total 12.0

# HELP rag_cache_misses_total Number of RAG cache misses
# TYPE rag_cache_misses_total counter
rag_cache_misses_total 28.0
```

---

## 🔑 Configuration

### Variables d'Environnement

Le cache utilise les variables d'env existantes de `RAGCache`:

| Variable | Défaut | Description |
|----------|--------|-------------|
| `RAG_CACHE_REDIS_URL` | `None` | URL Redis (ex: `redis://localhost:6379/0`) |
| `RAG_CACHE_TTL_SECONDS` | `3600` | TTL du cache (1 heure) |
| `RAG_CACHE_MAX_MEMORY_ITEMS` | `500` | Taille max du cache mémoire (fallback) |
| `RAG_CACHE_ENABLED` | `true` | Activer/désactiver le cache |

### Recommandations Production

**Avec Redis (recommandé):**
```bash
RAG_CACHE_REDIS_URL=redis://localhost:6379/0
RAG_CACHE_TTL_SECONDS=300  # 5 minutes pour mémoire consolidée
RAG_CACHE_ENABLED=true
```

**Sans Redis (développement):**
```bash
# RAG_CACHE_REDIS_URL non défini → fallback mémoire
RAG_CACHE_TTL_SECONDS=300
RAG_CACHE_MAX_MEMORY_ITEMS=100  # Limite mémoire
RAG_CACHE_ENABLED=true
```

---

## 🚀 Performance

### Benchmarks Théoriques

| Scénario | Latence | Requête ChromaDB | Notes |
|----------|---------|------------------|-------|
| Cache MISS (1ère requête) | ~1.95s | Oui | ChromaDB query + parsing |
| Cache HIT (2ème requête) | ~0.1-0.5s | Non | Récupération mémoire/Redis |
| Erreur ChromaDB | ~0.1s | Tentative | Fallback gracieux, miss comptabilisé |

### Calcul du Gain

**Avec 30% hit rate:**
- Avant: 100 requêtes × 1.95s = 195s
- Après: 70 misses × 1.95s + 30 hits × 0.5s = 136.5s + 15s = 151.5s
- **Gain:** (195 - 151.5) / 195 = **22% de réduction de latence moyenne**

**Avec 40% hit rate:**
- Après: 60 × 1.95s + 40 × 0.5s = 117s + 20s = 137s
- **Gain:** (195 - 137) / 195 = **30% de réduction**

### Test de Charge (Recommandé)

Pour valider en production, exécuter:

```bash
# 1. Poser une question temporelle
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quand avons-nous parlé de Docker?", "session_id": "test"}'

# 2. Noter le temps de réponse (T1)

# 3. Reposer la même question
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Quand avons-nous parlé de Docker?", "session_id": "test"}'

# 4. Noter le temps de réponse (T2)
# T2 devrait être ~75% plus rapide que T1
```

---

## 🛡️ Sécurité & Isolation

### Isolation du Cache

Le cache de mémoire consolidée est **isolé** du cache RAG documents via un préfixe:

```python
cache_query = f"__CONSOLIDATED_MEMORY__:{query_text}"
```

**Raisons:**
1. Éviter collisions entre documents et concepts consolidés
2. Permettre invalidation sélective (futur)
3. Faciliter debugging (logs distincts)

**Vérification:**
```python
# Test: test_cache_prefix_isolation
assert cache_query.startswith("__CONSOLIDATED_MEMORY__:")
```

### Sécurité User ID

Les résultats sont filtrés par `user_id` via:
1. **ChromaDB where filter:** `{"user_id": user_id}`
2. **Cache fingerprinting:** Hash inclut `user_id` + `query_text`

→ Impossible qu'un utilisateur récupère les résultats d'un autre

---

## 🐛 Debugging

### Logs à Surveiller

**Cache HIT:**
```
[DEBUG] [TemporalCache] HIT: 2.3ms pour 'Quand avons-nous parlé de Docker?'
```

**Cache MISS:**
```
[DEBUG] [TemporalCache] MISS: Recherche ChromaDB pour 'Quand avons-nous parlé de Docker?'
[INFO] [TemporalCache] ChromaDB search: 1950ms, found 4 concepts
```

**Erreur:**
```
[WARNING] [TemporalHistory] Erreur recherche knowledge: <exception>
```

### Vérifier le Cache

**Redis (si configuré):**
```bash
redis-cli
> KEYS rag:query:*
> GET rag:query:<fingerprint>
```

**Mémoire (fallback):**
```python
# Dans le code
logger.info(f"Cache size: {len(service.rag_cache.memory_cache)}")
```

---

## ✅ Critères de Succès Phase 3 - Priorité 1

| Critère | Cible | Statut |
|---------|-------|--------|
| Implémentation cache | ✅ | ✅ COMPLÉTÉ |
| Tests unitaires | 100% pass | ✅ 7/7 PASS |
| Cache hit rate | 30-40% | ⏳ À mesurer en prod |
| Latence cache hit | < 500ms | ⏳ À mesurer en prod |
| Pas de warning ChromaDB | n_results dynamique | ✅ IMPLÉMENTÉ |
| Documentation | Complète | ✅ CE DOCUMENT |

---

## 📚 Références

### Code Source

1. **Implémentation principale:**
   - [service.py:1130-1246](../../src/backend/features/chat/service.py#L1130-L1246) - `_get_cached_consolidated_memory()`
   - [service.py:1277-1288](../../src/backend/features/chat/service.py#L1277-L1288) - `_build_temporal_history_context()` modifié

2. **Infrastructure réutilisée:**
   - [rag_cache.py](../../src/backend/features/chat/rag_cache.py) - Cache Redis/mémoire
   - [rag_metrics.py](../../src/backend/features/chat/rag_metrics.py) - Métriques Prometheus

3. **Tests:**
   - [test_consolidated_memory_cache.py](../../tests/backend/features/chat/test_consolidated_memory_cache.py) - Suite de tests

### Documentation Liée

- [MEMORY_PHASE3_PROMPT.md](MEMORY_PHASE3_PROMPT.md) - Plan Phase 3 complet
- [MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md](MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md) - Phase 2 (base)
- [MEMORY_NEXT_INSTANCE_PROMPT.md](MEMORY_NEXT_INSTANCE_PROMPT.md) - Roadmap générale

---

## 🔮 Prochaines Étapes

### Phase 3 - Priorités Restantes

**Priorité 2: Métriques Prometheus Avancées** (1-2h)
- Ajouter `memory_temporal_queries_total` (compteur questions temporelles)
- Ajouter `memory_temporal_search_duration_seconds` (histogram latence)
- Ajouter `memory_temporal_cache_hit_rate` (gauge hit rate)
- Dashboard Grafana

**Priorité 3: Groupement Thématique** (3-4h)
- Clustering concepts similaires avec embeddings
- Extraction titres intelligents
- Format groupé plus concis

**Priorité 4: Résumé Adaptatif** (2h)
- Résumer threads longs (>30 événements)
- Garder 10 plus récents en détail

---

**Créé le:** 2025-10-15
**Par:** Session de développement Phase 3
**Statut:** ✅ Implémentation validée et testée
**Prochaine étape:** Mesure performance en production + Priorité 2 (Métriques avancées)
