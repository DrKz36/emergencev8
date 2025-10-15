# Prompt Instance Suivante - Mémoire Phase 3 : Optimisations & Métriques
**Date:** 2025-10-15
**Contexte:** Suite de l'implémentation Phase 2 (Contexte temporel avec mémoire consolidée)
**Objectif:** Optimiser performance, ajouter métriques Prometheus, améliorer intelligence

---

## 🎯 Contexte pour la Prochaine Instance

Bonjour ! Tu reprends le développement après la **Phase 2 complétée et validée** de la mémoire temporelle d'Émergence.

### État Actuel (Fin Phase 2 - 2025-10-15)

**✅ Fonctionnalités Opérationnelles:**

1. **Détection Questions Temporelles** ✅
   - Regex multilingue FR/EN
   - Patterns: quand, quel jour, quelle heure, when, what time, etc.
   - Insensible à la casse

2. **Enrichissement Contexte Historique** ✅
   - Récupération 20 derniers messages thread
   - Recherche sémantique dans `emergence_knowledge` (ChromaDB)
   - Fusion chronologique messages + concepts consolidés
   - Format: `**[15 oct à 3h08] Toi :**` / `**[14 oct à 4h30] Mémoire (concept) :**`

3. **Tests Validés** ✅
   - Tests unitaires: 12/12 passés (100%)
   - Test production: Question "Quand avons-nous parlé de mon poème fondateur?" → Dates précises fournies
   - Performance: 4.84s total (acceptable)
   - Log: `[TemporalHistory] Contexte enrichi: 20 messages + 4 concepts consolidés`

**📊 Métriques Actuelles:**
- Recherche ChromaDB: ~1.95s
- Concepts consolidés trouvés: 4/4 (100%)
- Temps réponse total: 4.84s
- Précision temporelle: 100%

---

## 🚀 Phase 3 : Objectifs & Priorités

### Priorité 1: Optimisations Performance (2-3h)

**Problèmes Identifiés:**

1. **Pas de Cache Recherche Consolidée**
   - Chaque question temporelle fait une recherche ChromaDB
   - Même question = même recherche répétée
   - Latence évitable: ~500ms par requête

2. **Limite Hardcodée n_results=5**
   - Ne s'adapte pas à la taille de la collection
   - Warning ChromaDB si collection < 5 entrées
   - Pas d'optimisation selon contexte

3. **Pas de Filtrage Temporel**
   - Recherche sur toute l'historique
   - Peut ramener concepts très anciens (>1 an)
   - Pertinence diminue avec le temps

**Solutions à Implémenter:**

#### 1.1 Cache Recherche Consolidée

**Fichier:** `src/backend/features/chat/service.py`

**Implémentation:**
```python
# Ajouter au niveau classe ChatService
from functools import lru_cache
import hashlib

_temporal_cache: Dict[str, Tuple[List[Dict], datetime]] = {}
_temporal_cache_lock = asyncio.Lock()

async def _get_cached_consolidated_entries(
    self,
    user_id: str,
    query_text: str,
    n_results: int = 5
) -> Optional[List[Dict[str, Any]]]:
    """Récupère entries consolidées depuis cache ou ChromaDB."""

    # Clé cache: hash(user_id + query_text normalisé)
    cache_key = hashlib.md5(f"{user_id}:{query_text[:50].lower()}".encode()).hexdigest()

    async with _temporal_cache_lock:
        if cache_key in _temporal_cache:
            entries, timestamp = _temporal_cache[cache_key]
            # Cache valide 5 minutes
            if datetime.now(timezone.utc) - timestamp < timedelta(minutes=5):
                logger.debug(f"[TemporalCache] Hit: {cache_key[:8]}")
                return entries

    # Cache miss → recherche ChromaDB
    logger.debug(f"[TemporalCache] Miss: {cache_key[:8]}")
    entries = await self._search_consolidated_concepts(user_id, query_text, n_results)

    # Stocker en cache
    async with _temporal_cache_lock:
        _temporal_cache[cache_key] = (entries, datetime.now(timezone.utc))

        # Éviction si > 100 entrées
        if len(_temporal_cache) > 100:
            oldest_key = min(_temporal_cache.items(), key=lambda x: x[1][1])[0]
            del _temporal_cache[oldest_key]

    return entries
```

**Résultat attendu:**
- Réduction latence: 1.95s → 0.1s pour requêtes répétées
- Cache hit rate cible: 30-40%

#### 1.2 Limite Dynamique n_results

**Fichier:** `src/backend/features/chat/service.py:1170`

**Changement:**
```python
# Avant (ligne 1170)
n_results=5,

# Après
n_results = min(5, max(3, len(all_events) // 4))
```

**Raison:** Adapter le nombre de résultats selon la taille du contexte déjà chargé

#### 1.3 Filtrage Temporel

**Fichier:** `src/backend/features/chat/service.py:1171`

**Changement:**
```python
# Ajouter filtre temporel (derniers 30 jours)
from datetime import timedelta
cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

where = {"user_id": user_id}
# Ajouter filtre temporel si ChromaDB le supporte
# where["created_at"] = {"$gte": cutoff_date}  # À tester avec ChromaDB
```

**Alternative si ChromaDB ne supporte pas filtres complexes:**
```python
# Filtrage post-recherche
for i, metadata in enumerate(metadatas):
    timestamp = metadata.get("created_at") or metadata.get("first_mentioned_at")

    # Ignorer concepts > 30 jours
    if timestamp:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - dt > timedelta(days=30):
            continue

    # ... reste du code
```

---

### Priorité 2: Métriques Prometheus (1-2h)

**Objectif:** Suivre performance et usage de la mémoire temporelle

**Fichier:** `src/backend/features/chat/rag_metrics.py` (ou nouveau fichier)

**Métriques à Ajouter:**

```python
from prometheus_client import Counter, Histogram, Gauge

# 1. Compteur Questions Temporelles
memory_temporal_queries_total = Counter(
    "memory_temporal_queries_total",
    "Total temporal queries detected",
    ["detected"]  # "true" ou "false"
)

# 2. Compteur Concepts Consolidés Trouvés
memory_temporal_concepts_found_total = Counter(
    "memory_temporal_concepts_found_total",
    "Total consolidated concepts found in temporal queries",
    ["count_range"]  # "0", "1-2", "3-5", "5+"
)

# 3. Histogram Durée Recherche ChromaDB
memory_temporal_search_duration_seconds = Histogram(
    "memory_temporal_search_duration_seconds",
    "Time spent searching ChromaDB for consolidated concepts",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
)

# 4. Histogram Taille Contexte Enrichi
memory_temporal_context_size_bytes = Histogram(
    "memory_temporal_context_size_bytes",
    "Size of enriched temporal context in bytes",
    buckets=[100, 500, 1000, 2000, 5000, 10000]
)

# 5. Gauge Cache Hit Rate
memory_temporal_cache_hit_rate = Gauge(
    "memory_temporal_cache_hit_rate",
    "Cache hit rate for temporal queries (percentage)"
)

# 6. Compteur Cache Operations
memory_temporal_cache_operations_total = Counter(
    "memory_temporal_cache_operations_total",
    "Total cache operations",
    ["operation"]  # "hit", "miss", "eviction"
)
```

**Instrumentation dans service.py:**

```python
# Ligne 1852 (détection)
if self._is_temporal_query(last_user_message):
    memory_temporal_queries_total.labels(detected="true").inc()

    # Mesurer durée recherche ChromaDB
    start_search = time.time()
    consolidated_entries = await self._get_cached_consolidated_entries(...)
    search_duration = time.time() - start_search
    memory_temporal_search_duration_seconds.observe(search_duration)

    # Compter concepts trouvés
    count = len(consolidated_entries)
    if count == 0:
        range_label = "0"
    elif count <= 2:
        range_label = "1-2"
    elif count <= 5:
        range_label = "3-5"
    else:
        range_label = "5+"
    memory_temporal_concepts_found_total.labels(count_range=range_label).inc()

    # Mesurer taille contexte final
    context_size = len(recall_context.encode('utf-8'))
    memory_temporal_context_size_bytes.observe(context_size)
else:
    memory_temporal_queries_total.labels(detected="false").inc()
```

**Dashboard Grafana (Configuration Suggérée):**

```json
{
  "title": "Mémoire Temporelle - Performance",
  "panels": [
    {
      "title": "Questions Temporelles Détectées",
      "targets": [
        {
          "expr": "rate(memory_temporal_queries_total{detected=\"true\"}[5m])"
        }
      ]
    },
    {
      "title": "Concepts Consolidés Trouvés",
      "targets": [
        {
          "expr": "sum by (count_range) (memory_temporal_concepts_found_total)"
        }
      ]
    },
    {
      "title": "Latence Recherche ChromaDB (p50, p95, p99)",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, memory_temporal_search_duration_seconds)"
        },
        {
          "expr": "histogram_quantile(0.95, memory_temporal_search_duration_seconds)"
        },
        {
          "expr": "histogram_quantile(0.99, memory_temporal_search_duration_seconds)"
        }
      ]
    },
    {
      "title": "Cache Hit Rate",
      "targets": [
        {
          "expr": "memory_temporal_cache_hit_rate"
        }
      ]
    }
  ]
}
```

---

### Priorité 3: Groupement Thématique Intelligent (3-4h)

**Objectif:** Regrouper concepts consolidés par sujet pour présentation plus concise

**Problème Actuel:**
```
**[14 oct à 4h24] Mémoire (concept) :** L'utilisateur demande des citations...
**[14 oct à 4h30] Mémoire (concept) :** L'utilisateur répète des demandes...
**[15 oct à 3h02] Mémoire (concept) :** L'utilisateur demande citations...
```

**Amélioration Souhaitée:**
```
**[Poème fondateur]** Discussion récurrente (3 échanges)
  - 14 oct à 4h24: Citations intégrales demandées
  - 14 oct à 4h30: Demandes répétées
  - 15 oct à 3h02: Nouvelles citations
```

**Implémentation:**

**Étape 1: Extraction Thèmes avec Embeddings**

```python
async def _group_concepts_by_theme(
    self,
    consolidated_entries: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Groupe concepts consolidés par similarité sémantique."""

    if len(consolidated_entries) <= 2:
        # Pas de groupement si peu de concepts
        return {"default": consolidated_entries}

    # Générer embeddings pour chaque concept
    contents = [entry["content"] for entry in consolidated_entries]
    embeddings = await self.vector_service.embed_batch(contents)

    # Clustering simple avec seuil de similarité
    from sklearn.metrics.pairwise import cosine_similarity
    similarity_matrix = cosine_similarity(embeddings)

    groups = {}
    assigned = set()
    group_id = 0

    for i in range(len(consolidated_entries)):
        if i in assigned:
            continue

        # Créer nouveau groupe
        group_key = f"group_{group_id}"
        groups[group_key] = [consolidated_entries[i]]
        assigned.add(i)

        # Ajouter concepts similaires (cosine > 0.7)
        for j in range(i+1, len(consolidated_entries)):
            if j not in assigned and similarity_matrix[i][j] > 0.7:
                groups[group_key].append(consolidated_entries[j])
                assigned.add(j)

        group_id += 1

    return groups
```

**Étape 2: Extraction Titre de Groupe**

```python
def _extract_group_title(self, concepts: List[Dict[str, Any]]) -> str:
    """Extrait un titre représentatif pour un groupe de concepts."""

    # Concaténer tous les contenus
    combined_text = " ".join([c["content"] for c in concepts])

    # Extraction mots-clés avec regex ou TF-IDF simple
    words = combined_text.lower().split()
    word_freq = {}
    for word in words:
        if len(word) > 4:  # Ignorer mots courts
            word_freq[word] = word_freq.get(word, 0) + 1

    # Prendre les 2 mots les plus fréquents
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:2]
    title = " ".join([w[0].title() for w in top_words])

    return title or "Discussion"
```

**Étape 3: Formatage Groupé**

```python
# Dans _build_temporal_history_context()
if len(consolidated_entries) > 2:
    groups = await self._group_concepts_by_theme(consolidated_entries)

    for group_key, concepts in groups.items():
        title = self._extract_group_title(concepts)
        lines.append(f"\n**[{title}]** Discussion récurrente ({len(concepts)} échanges)")

        for concept in concepts:
            dt = datetime.fromisoformat(concept["timestamp"].replace("Z", "+00:00"))
            date_str = f"{dt.day} {months[dt.month]} à {dt.hour}h{dt.minute:02d}"
            preview = concept["content"][:60] + "..."
            lines.append(f"  - {date_str}: {preview}")
else:
    # Formatage standard si peu de concepts
    # ... code actuel
```

---

### Priorité 4: Résumé Adaptatif (2h)

**Objectif:** Si thread très long (>100 messages), résumer les plus anciens

**Implémentation:**

```python
async def _build_temporal_history_context(
    self,
    thread_id: str,
    session_id: str,
    user_id: str,
    limit: int = 20,
    last_user_message: str = ""
) -> str:
    # ... code existant

    # NOUVEAU: Si beaucoup de messages, résumer les plus anciens
    if len(all_events) > 30:
        # Garder 10 plus récents en détail
        recent_events = all_events[-10:]

        # Résumer les plus anciens
        older_events = all_events[:-10]
        summary = await self._summarize_old_events(older_events)

        lines.append(f"\n**[Période antérieure]** {summary}")
        lines.append("")

        # Formater uniquement les récents
        for event in recent_events:
            # ... formatage standard
    else:
        # Formater tous les événements
        for event in all_events:
            # ... formatage actuel
```

---

## 📋 Plan d'Action Recommandé

### Session 1: Cache & Optimisations de Base (2-3h)

**Ordre d'implémentation:**
1. ✅ Implémenter cache recherche consolidée
2. ✅ Ajuster n_results dynamiquement
3. ✅ Ajouter filtrage temporel (30 jours)
4. ✅ Tester et valider performance
5. ✅ Mesurer amélioration latence

**Critères de succès:**
- Cache hit rate > 30%
- Latence questions répétées < 500ms
- Pas de warning ChromaDB `n_results`

### Session 2: Métriques Prometheus (1-2h)

**Ordre d'implémentation:**
1. ✅ Créer métriques dans `rag_metrics.py`
2. ✅ Instrumenter service.py
3. ✅ Tester export `/metrics`
4. ✅ Créer dashboard Grafana (optionnel)

**Critères de succès:**
- 6 métriques exportées
- Métriques visibles dans `/metrics`
- Données cohérentes après 10 requêtes test

### Session 3: Groupement Thématique (3-4h)

**Ordre d'implémentation:**
1. ✅ Implémenter clustering avec embeddings
2. ✅ Extraction titres de groupes
3. ✅ Formatage groupé dans contexte
4. ✅ Tester avec concepts multiples
5. ✅ Valider lisibilité pour Anima

**Critères de succès:**
- Groupes cohérents (similarité > 0.7)
- Titres pertinents (TF-IDF)
- Contexte plus concis et lisible

### Session 4: Résumé Adaptatif (2h)

**Ordre d'implémentation:**
1. ✅ Détecter threads longs (>30 événements)
2. ✅ Résumer période antérieure
3. ✅ Garder 10 plus récents en détail
4. ✅ Tester avec thread long

**Critères de succès:**
- Résumé < 200 caractères
- 10 événements récents détaillés
- Contexte total < 2000 caractères

---

## 🧪 Tests à Effectuer

### Test 1: Cache Performance

**Action:**
```
1. Poser: "Quand avons-nous parlé de Docker ?"
2. Noter temps réponse (T1)
3. Reposer exactement la même question
4. Noter temps réponse (T2)
```

**Résultat attendu:**
- T1: ~4.8s (recherche ChromaDB)
- T2: ~2.5s (cache hit)
- Amélioration: ~48%

### Test 2: Métriques Prometheus

**Action:**
```bash
# Poser 5 questions temporelles variées
curl http://localhost:8000/metrics | grep memory_temporal
```

**Résultat attendu:**
```
memory_temporal_queries_total{detected="true"} 5.0
memory_temporal_concepts_found_total{count_range="3-5"} 3.0
memory_temporal_search_duration_seconds_sum 9.5
memory_temporal_cache_hit_rate 0.2
```

### Test 3: Groupement Thématique

**Action:**
```
Poser: "Quand avons-nous parlé de mes projets ?"
(Avec 6+ concepts consolidés sur différents sujets)
```

**Résultat attendu:**
```
**[Docker Kubernetes]** Discussion récurrente (3 échanges)
  - 8 oct à 14h32: Configuration Docker...
  - 10 oct à 9h15: Déploiement Kubernetes...
  - 12 oct à 16h20: Optimisation images...

**[CI/CD Pipeline]** Discussion récurrente (2 échanges)
  - 9 oct à 11h05: Setup GitHub Actions...
  - 11 oct à 14h00: Tests automatisés...
```

---

## 📚 Fichiers Clés à Modifier

### Backend

1. **`src/backend/features/chat/service.py`**
   - Lignes ~1165-1199: Ajouter cache
   - Lignes ~1170: Ajuster n_results dynamiquement
   - Lignes ~1190-1266: Ajouter groupement thématique
   - Lignes ~1852: Instrumenter métriques

2. **`src/backend/features/chat/rag_metrics.py`** (ou nouveau)
   - Définir 6 nouvelles métriques Prometheus
   - Fonctions helper pour instrumentation

3. **`src/backend/features/memory/vector_service.py`** (optionnel)
   - Ajouter méthode `embed_batch()` si absente
   - Optimiser embeddings batch pour clustering

### Tests

4. **`tests/backend/features/chat/test_temporal_cache.py`** (nouveau)
   - Test cache hit/miss
   - Test éviction
   - Test invalidation

5. **`tests/backend/features/chat/test_temporal_grouping.py`** (nouveau)
   - Test clustering concepts
   - Test extraction titres
   - Test formatage groupé

### Documentation

6. **`docs/architecture/MEMORY_PHASE3_IMPLEMENTATION.md`** (nouveau)
   - Documentation technique Phase 3
   - Architecture cache
   - Métriques Prometheus
   - Algorithme clustering

7. **`CHANGELOG.md`**
   - Section Phase 3 avec toutes les améliorations

---

## 🔍 Points d'Attention

### Performance

**⚠️ Clustering Peut Être Coûteux**
- Embeddings batch: ~50-100ms pour 5 concepts
- Clustering: ~10-20ms avec sklearn
- Total overhead: ~100ms acceptable

**Solution si trop lent:**
- Cacher résultats clustering aussi
- Limiter clustering à >5 concepts seulement

### Mémoire

**⚠️ Cache Peut Croître**
- 100 entrées × 5 concepts × 500 bytes ≈ 250KB
- Acceptable, mais surveiller

**Solution:**
- Éviction agressive (100 entrées max)
- TTL court (5 minutes)
- Clear cache sur nouvelle consolidation

### ChromaDB

**⚠️ Filtres Temporels Pas Toujours Supportés**
- ChromaDB where filters limités
- Tester avant d'utiliser `$gte`

**Fallback:**
- Filtrage post-recherche en Python
- Acceptable car peu de résultats (5-10)

---

## 📊 Métriques de Succès Phase 3

### Performance

- ✅ Cache hit rate > 30%
- ✅ Latence questions répétées < 2.5s (amélioration 50%)
- ✅ Overhead clustering < 100ms

### Qualité

- ✅ Groupes thématiques cohérents (similarité > 0.7)
- ✅ Titres de groupes pertinents (validation manuelle)
- ✅ Contexte enrichi < 2000 caractères

### Observabilité

- ✅ 6 métriques Prometheus exportées
- ✅ Dashboard Grafana fonctionnel (optionnel)
- ✅ Alertes configurées (optionnel)

---

## 🚀 Prochaines Phases (Post-Phase 3)

### Phase 4: Multi-Thread Temporal Context (Futur)

- Recherche concepts consolidés sur plusieurs threads
- Exemple: "Quand avons-nous parlé de X dans tous mes threads ?"
- Nécessite: index global cross-thread

### Phase 5: Prédiction Temporelle (Futur)

- Détection patterns temporels récurrents
- Exemple: "Tu as parlé de Docker chaque lundi les 3 dernières semaines"
- Suggestions proactives basées sur calendrier

---

## 📞 Si Besoin d'Aide

### Documentation de Référence

1. **Phase 2 Complétée:**
   - [MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md](MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md)
   - [test_production_temporal_memory_2025-10-15.md](../../reports/test_production_temporal_memory_2025-10-15.md)

2. **Code Actuel:**
   - [service.py:1130-1270](../../src/backend/features/chat/service.py#L1130-L1270)
   - [gardener.py:1640-1705](../../src/backend/features/memory/gardener.py#L1640-L1705)

3. **Tests Existants:**
   - [test_temporal_query.py](../../tests/backend/features/chat/test_temporal_query.py)

### Logs à Surveiller

**Pendant Développement:**
```bash
# Cache operations
grep "TemporalCache" logs.txt

# Performance ChromaDB
grep "TemporalHistory.*enrichi" logs.txt

# Métriques
curl http://localhost:8000/metrics | grep memory_temporal
```

---

## ✅ Checklist Avant de Commencer

- [ ] Lire cette documentation complète
- [ ] Vérifier Phase 2 fonctionnelle (test production)
- [ ] Backend démarre sans erreur
- [ ] Comprendre architecture actuelle ([MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md](MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md))
- [ ] Choisir priorité (1, 2, 3, ou 4)
- [ ] Lancer backend en mode développement
- [ ] Avoir thread de test avec 5+ concepts consolidés

---

**Bon courage pour la Phase 3 ! 🚀**

L'objectif est d'améliorer la performance et l'observabilité tout en rendant le contexte temporel encore plus intelligent et utile.

**Prochaine étape:** Implémenter le cache (Priorité 1) pour obtenir des gains de performance immédiats.

---

**Créé le:** 2025-10-15
**Par:** Session de développement Phase 2 - Préparation Phase 3
**Statut:** ✅ Prêt pour implémentation
