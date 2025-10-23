# Plan Optimisation Mémoire LTM - Phase P2

**Date** : 2025-10-10
**Agent** : Claude Code
**Objectif** : Rendre la mémoire LTM plus performante et proactive
**Statut** : 📋 PRÊT POUR IMPLÉMENTATION

---

## ⚠️ NOTE IMPORTANTE

**Ce plan P2 Mémoire est PRIORITAIRE sur le Sprint 0 Cockpit.**

Pour les fixes cockpit (UI dashboard, coûts Gemini, métriques Prometheus), voir :
→ **[docs/cockpit/COCKPIT_GAPS_AND_FIXES.md](../cockpit/COCKPIT_GAPS_AND_FIXES.md)**

Timeline :
1. **P2 Mémoire** (ce document) : 6-9 jours
2. **Sprint 0 Cockpit** : 1-2 jours après P2

---

## 📊 État Actuel (Post-P0/P1)

### ✅ Acquis
- **Phase P0** : Persistance cross-device + consolidation threads archivés
- **Phase P1** : Extraction + persistence préférences ChromaDB
- **Tests** : 48/48 mémoire, 132/132 backend
- **Production** : 100% opérationnel (révision `emergence-app-p1-p0-20251010-040147`)

### 📈 Métriques Actuelles

#### ChromaDB Collections
```python
emergence_knowledge: {
  "concepts": ~500 entrées,
  "preferences": ~150 entrées,
  "facts": ~200 entrées
}
```

#### Temps Réponse Moyens
- `build_memory_context()` : **~120ms** (query vectorielle + fetch preferences)
- `_fetch_active_preferences()` : **~35ms** (filter ChromaDB)
- `save_preferences_to_vector_db()` : **~180ms** (embedding + insert)

#### Goulots d'Étranglement Identifiés
1. **Aucune indexation metadata** → Queries ChromaDB lentes sur `user_id`, `type`, `confidence`
2. **Pas de cache préférences** → Re-fetch à chaque message (overhead réseau)
3. **Queries séquentielles** → `fetch_preferences` puis `vector_search` (2 round-trips)
4. **Aucune proactivité** → Système 100% réactif (attend requête user)

---

## 🎯 Objectifs Phase P2

### Performance
- ⚡ **Réduire latence contexte LTM** : 120ms → **<50ms** (-58%)
- 🚀 **Cache hit rate préférences** : 0% → **>80%**
- 📉 **Réduire queries ChromaDB** : 2/message → **1/message** (-50%)

### UX Proactive
- 🔔 **Suggestions contextuelles** : 0 → **3-5/session** (ws:proactive_hint)
- 🧠 **Rappels intelligents** : Détection concepts récurrents + notification
- 📊 **Dashboard mémoire utilisateur** : Visualisation préférences + concepts top

### Observabilité
- 📈 **Métriques Prometheus** : +8 nouvelles métriques performance
- 🔍 **Logging structuré** : Temps queries, cache stats, hint triggers
- 📊 **Grafana dashboard** : Visualisation latences + hit rates

---

## 🔧 Optimisations Techniques

### 🟢 Opt #1 : Indexation Metadata ChromaDB

#### Problème
ChromaDB utilise scan complet pour filtres metadata complexes :
```python
where = {
    "$and": [
        {"user_id": user_id},        # ← Scan complet
        {"type": "preference"},       # ← Pas d'index
        {"confidence": {"$gte": 0.6}} # ← Comparaison lente
    ]
}
```

#### Solution
Créer indexes metadata au niveau collection :
```python
# vector_service.py
def create_indexed_collection(self, name: str, metadata_indexes: List[str]):
    """
    Créer collection avec indexes metadata pour queries rapides.

    Args:
        name: Nom collection
        metadata_indexes: Champs à indexer (ex: ["user_id", "type", "confidence"])
    """
    collection = self.client.get_or_create_collection(
        name=name,
        metadata={
            "hnsw:space": "cosine",
            "hnsw:M": 16,  # Connexions par nœud (trade-off précision/vitesse)
            "indexes": metadata_indexes  # ← Nouveau : indexes metadata
        }
    )
    logger.info(f"Collection '{name}' created with indexes: {metadata_indexes}")
    return collection
```

**Gains attendus** :
- Query `_fetch_active_preferences()` : **35ms → 8ms** (-77%)
- Réduction CPU ChromaDB : **~40%**

---

### 🟡 Opt #2 : Cache Préférences Utilisateur

#### Problème
Préférences re-fetchées à **chaque message** (même si inchangées) :
```python
# memory_ctx.py (appelé à chaque message)
prefs = self._fetch_active_preferences(collection, user_id)  # ← Query ChromaDB
```

#### Solution A : Cache In-Memory (Quick Win)
```python
# memory_ctx.py
from functools import lru_cache
from datetime import datetime, timedelta

class MemoryContextBuilder:
    def __init__(self, session_manager, vector_service):
        self.session_manager = session_manager
        self.vector_service = vector_service
        self._prefs_cache = {}  # {user_id: (prefs, timestamp)}
        self._cache_ttl = timedelta(minutes=5)  # TTL 5 min

    def _fetch_active_preferences_cached(self, collection, user_id: str) -> str:
        """Fetch preferences with in-memory cache (5min TTL)."""
        now = datetime.now()

        # Check cache
        if user_id in self._prefs_cache:
            prefs, cached_at = self._prefs_cache[user_id]
            if now - cached_at < self._cache_ttl:
                logger.debug(f"[Cache HIT] Preferences for user {user_id}")
                return prefs

        # Cache miss → fetch ChromaDB
        prefs = self._fetch_active_preferences(collection, user_id)
        self._prefs_cache[user_id] = (prefs, now)
        logger.debug(f"[Cache MISS] Preferences cached for user {user_id}")

        return prefs
```

**Gains attendus** :
- Hit rate : **>80%** (5min TTL couvre ~8-10 messages typiques)
- Latence message cached : **120ms → 85ms** (-29%)
- Réduction charge ChromaDB : **~75%**

#### Solution B : Cache Redis (Production Scale)
```python
# cache_service.py
import redis.asyncio as redis
import json

class MemoryCacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def get_user_preferences(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached preferences from Redis."""
        key = f"prefs:{user_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set_user_preferences(self, user_id: str, prefs: List[Dict], ttl: int = 300):
        """Cache preferences in Redis (5min TTL)."""
        key = f"prefs:{user_id}"
        await self.redis.setex(key, ttl, json.dumps(prefs))
```

---

### 🟠 Opt #3 : Batch Prefetch Contexte LTM

#### Problème
Contexte construit via **2 queries séquentielles** :
```python
# 1. Fetch preferences (query metadata)
prefs = self._fetch_active_preferences(collection, user_id)  # 35ms

# 2. Vector search concepts
results = self.vector_service.query(
    collection=collection,
    query_text=last_user_message,
    n_results=top_k,
    where_filter={"user_id": user_id}
)  # 85ms

# Total: 120ms (2 round-trips)
```

#### Solution : Query Unifiée avec Post-Filtering
```python
async def build_memory_context_optimized(
    self, session_id: str, last_user_message: str, top_k: int = 10
) -> str:
    """
    Build memory context with single optimized query.

    Strategy:
    1. Fetch top_k*2 results (preferences + concepts combined)
    2. Post-filter client-side:
       - Extract preferences (type="preference", confidence>=0.6)
       - Extract top concepts (cosine similarity sort)
    """
    knowledge_col = self.vector_service.get_or_create_collection("emergence_knowledge")
    uid = self.try_get_user_id(session_id)

    # Single query: fetch 2x results for filtering
    results = self.vector_service.query(
        collection=knowledge_col,
        query_text=last_user_message,
        n_results=top_k * 2,  # ← Over-fetch for filtering
        where_filter={"user_id": uid} if uid else None,
        include_metadata=True
    )

    # Post-filter client-side (fast in-memory)
    preferences = []
    concepts = []

    for r in results:
        meta = r.get("metadata", {})
        if meta.get("type") == "preference" and meta.get("confidence", 0) >= 0.6:
            preferences.append(r)
        else:
            concepts.append(r)

    # Build sections
    sections = []
    if preferences[:5]:  # Top 5 preferences
        sections.append(("Préférences actives", self._format_preferences(preferences[:5])))
    if concepts[:top_k]:  # Top concepts
        sections.append(("Connaissances pertinentes", self._format_concepts(concepts[:top_k])))

    return self.merge_blocks(sections)
```

**Gains attendus** :
- Queries : **2 → 1** (-50%)
- Latence : **120ms → 60ms** (-50%)
- Post-filtering overhead : **~2ms** (négligeable)

---

## 🚀 Features Proactives (Phase P2)

### 🔔 Feature #1 : Suggestions Contextuelles (ws:proactive_hint)

#### Objectif
Système proactif qui suggère actions/rappels basés sur préférences et intentions utilisateur.

#### Mécanisme
```python
# concept_recall.py
class ProactiveHintTracker:
    """Track concept recurrence and trigger proactive hints."""

    def __init__(self, db: DatabaseManager, vector_service: VectorService):
        self.db = db
        self.vector_service = vector_service
        self._concept_counters = {}  # {concept: {user_id: count}}

    async def track_concept_mention(
        self,
        concept: str,
        user_id: str,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Track concept mention and trigger hint if threshold reached.

        Returns:
            Hint payload if triggered, None otherwise
        """
        # Increment counter
        key = f"{user_id}:{concept}"
        self._concept_counters[key] = self._concept_counters.get(key, 0) + 1
        count = self._concept_counters[key]

        # Trigger hint at 3rd mention (within 24h)
        if count == 3:
            # Fetch related preferences
            prefs = await self._fetch_related_preferences(user_id, concept)

            if prefs:
                hint = {
                    "type": "preference_reminder",
                    "concept": concept,
                    "message": f"💡 Rappel : Tu as mentionné '{concept}' 3 fois aujourd'hui. "
                               f"Tes préférences : {prefs[0]['text']}",
                    "preferences": prefs,
                    "session_id": session_id
                }

                # Reset counter
                self._concept_counters[key] = 0

                return hint

        return None
```

#### Intégration WebSocket
```python
# chat/service.py
async def process_message_with_hints(self, user_message: str, session_id: str, user_id: str):
    """Process message and emit proactive hints if triggered."""

    # Extract concepts from message
    concepts = await self.extract_concepts(user_message)

    # Track and check hints
    for concept in concepts:
        hint = await self.hint_tracker.track_concept_mention(concept, user_id, session_id)

        if hint:
            # Emit proactive hint via WebSocket
            await self.connection_manager.emit(
                session_id=session_id,
                event_type="ws:proactive_hint",
                payload=hint
            )

            logger.info(f"[ProactiveHint] Emitted hint for concept '{concept}' (user={user_id})")
```

#### UI Handler (Frontend)
```javascript
// main.js
EventBus.on('ws:proactive_hint', (hint) => {
  // Afficher bandeau suggestion
  const banner = document.createElement('div');
  banner.className = 'proactive-hint-banner';
  banner.innerHTML = `
    <div class="hint-icon">💡</div>
    <div class="hint-message">${hint.message}</div>
    <button class="hint-dismiss">Compris</button>
  `;

  document.body.appendChild(banner);

  // Auto-dismiss après 10s
  setTimeout(() => banner.remove(), 10000);

  // Metrics
  metrics.proactive_hints_shown.inc();
});
```

**Gains attendus** :
- **3-5 hints/session** (contextuels et pertinents)
- **Engagement utilisateur** : +25% (rappels utiles)
- **Satisfaction** : Mémoire perçue comme "intelligente"

---

### 🧠 Feature #2 : Dashboard Mémoire Utilisateur

#### Objectif
Interface visualisation préférences + concepts top + stats LTM.

#### Endpoint API
```python
# router.py
@router.get("/user/memory-stats")
async def get_user_memory_stats(
    request: Request,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Get user's memory statistics and top items.

    Returns:
        {
          "preferences": {
            "total": 12,
            "top": [{"topic": "python", "confidence": 0.92, ...}, ...],
            "by_type": {"preference": 8, "intent": 3, "constraint": 1}
          },
          "concepts": {
            "total": 47,
            "top": [{"concept": "containerization", "mentions": 5, ...}, ...],
            "timeline": [...]
          },
          "stats": {
            "sessions_analyzed": 23,
            "threads_archived": 5,
            "ltm_size_mb": 2.4
          }
        }
    """
    container = _get_container(request)
    vector_service = container.vector_service()
    collection = vector_service.get_or_create_collection("emergence_knowledge")

    # Fetch user's preferences
    prefs = collection.get(
        where={"user_id": user_id, "type": "preference"},
        include=["documents", "metadatas"]
    )

    # Fetch user's concepts
    concepts = collection.get(
        where={"user_id": user_id, "type": "concept"},
        include=["documents", "metadatas"]
    )

    # Compute stats
    stats = {
        "preferences": {
            "total": len(prefs.get("ids", [])),
            "top": _extract_top_items(prefs, limit=10),
            "by_type": _count_by_field(prefs, "type")
        },
        "concepts": {
            "total": len(concepts.get("ids", [])),
            "top": _extract_top_items(concepts, limit=10),
            "timeline": _build_timeline(concepts)
        },
        "stats": {
            "sessions_analyzed": await _count_analyzed_sessions(container.db_manager(), user_id),
            "threads_archived": await _count_archived_threads(container.db_manager(), user_id),
            "ltm_size_mb": _estimate_ltm_size(prefs, concepts)
        }
    }

    return stats
```

#### UI Component (Frontend)
```javascript
// features/memory/memory-dashboard.js
export class MemoryDashboard {
  async render(container) {
    const stats = await this.fetchMemoryStats();

    container.innerHTML = `
      <div class="memory-dashboard">
        <h2>🧠 Ta Mémoire à Long Terme</h2>

        <div class="stats-grid">
          <div class="stat-card">
            <h3>Préférences</h3>
            <div class="stat-value">${stats.preferences.total}</div>
            <div class="stat-top">
              ${stats.preferences.top.slice(0, 5).map(p => `
                <div class="pref-item">
                  <span class="topic">${p.topic}</span>
                  <span class="confidence">${(p.confidence * 100).toFixed(0)}%</span>
                </div>
              `).join('')}
            </div>
          </div>

          <div class="stat-card">
            <h3>Concepts</h3>
            <div class="stat-value">${stats.concepts.total}</div>
            <canvas id="concepts-timeline"></canvas>
          </div>
        </div>
      </div>
    `;

    // Render timeline chart
    this.renderTimelineChart(stats.concepts.timeline);
  }
}
```

---

## 📊 Métriques Prometheus (Phase P2)

### Nouvelles Métriques

```python
# memory/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Performance
memory_context_build_duration = Histogram(
    "memory_context_build_duration_seconds",
    "Time to build memory context for LLM",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

memory_cache_operations = Counter(
    "memory_cache_operations_total",
    "Cache operations (hit/miss)",
    ["operation", "type"]  # operation=hit|miss, type=preferences|concepts
)

# Proactivité
proactive_hints_triggered = Counter(
    "proactive_hints_triggered_total",
    "Proactive hints triggered",
    ["type"]  # type=preference_reminder|concept_recurrence|intent_expiring
)

proactive_hints_dismissed = Counter(
    "proactive_hints_dismissed_total",
    "Proactive hints dismissed by user",
    ["type", "reason"]  # reason=clicked_dismiss|auto_timeout|clicked_action
)

# LTM Stats
ltm_collection_size = Gauge(
    "ltm_collection_size_bytes",
    "Size of LTM collection in bytes",
    ["collection", "user_id"]
)

ltm_query_results = Histogram(
    "ltm_query_results_count",
    "Number of results returned by LTM queries",
    buckets=[0, 1, 3, 5, 10, 20, 50]
)
```

---

## 🧪 Plan de Tests

### Performance Benchmarks

```python
# tests/benchmarks/test_memory_performance.py
import pytest
import time
from backend.features.chat.memory_ctx import MemoryContextBuilder

@pytest.mark.benchmark
async def test_memory_context_performance(benchmark_db, benchmark_vector_service):
    """Benchmark build_memory_context() performance."""
    builder = MemoryContextBuilder(
        session_manager=mock_session_manager,
        vector_service=benchmark_vector_service
    )

    # Pre-populate ChromaDB with 1000 entries
    await populate_test_data(benchmark_vector_service, count=1000)

    # Benchmark
    start = time.perf_counter()
    context = await builder.build_memory_context(
        session_id="test_session",
        last_user_message="Tell me about containerization",
        top_k=5
    )
    duration = time.perf_counter() - start

    # Assertions
    assert context is not None
    assert duration < 0.050  # < 50ms (target P2)
    assert len(context) > 0

@pytest.mark.benchmark
async def test_cache_hit_rate():
    """Test cache hit rate with realistic traffic pattern."""
    builder = MemoryContextBuilder(...)

    hits = 0
    total = 100

    for i in range(total):
        # Simulate 80% repeat queries (same user_id)
        user_id = f"user_{i % 20}"  # 20 unique users, 5 queries each

        start = time.perf_counter()
        await builder._fetch_active_preferences_cached(collection, user_id)
        duration = time.perf_counter() - start

        if duration < 0.010:  # < 10ms = likely cache hit
            hits += 1

    hit_rate = hits / total
    assert hit_rate > 0.80  # Target: >80% hit rate
```

---

## 📅 Roadmap Phase P2

### Sprint 1 (2-3 jours)
- ✅ Opt #1 : Indexation metadata ChromaDB
- ✅ Opt #2 : Cache in-memory préférences
- ✅ Tests performance + benchmarks

### Sprint 2 (2-3 jours)
- ✅ Opt #3 : Batch prefetch contexte
- ✅ Feature #1 : Proactive hints (backend)
- ✅ Métriques Prometheus P2

### Sprint 3 (2-3 jours)
- ✅ Feature #1 : Proactive hints (frontend UI)
- ✅ Feature #2 : Dashboard mémoire utilisateur
- ✅ Documentation + déploiement

**Durée totale estimée** : 6-9 jours

---

## 🎯 KPIs Succès Phase P2

| Métrique | Baseline (P1) | Target (P2) | Gain |
|----------|--------------|------------|------|
| Latence contexte LTM | 120ms | <50ms | **-58%** |
| Cache hit rate | 0% | >80% | **+80%** |
| Queries ChromaDB/message | 2 | 1 | **-50%** |
| Proactive hints/session | 0 | 3-5 | **+∞** |
| User engagement | baseline | +25% | **+25%** |

---

**Document créé le** : 2025-10-10 18:30 UTC
**Auteur** : Claude Code
**Statut** : 📋 PLAN VALIDÉ - Prêt implémentation
