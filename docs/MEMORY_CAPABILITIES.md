# 🧠 Capacités Mémoire du Système EMERGENCE

> **Version:** 3.0 - Mise à jour Phase P2 (10/10/2025)
> **Statut:** ✅ Opérationnel avec optimisations performance + hints proactifs

---

## 📊 Vue d'Ensemble

Le système EMERGENCE dispose de **3 couches mémorielles** interconnectées :

```
┌─────────────────────────────────────────────────────────┐
│                    AGENTS (ANIMA/NEO/NEXUS)             │
└───────────────┬─────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        │  API UNIFIÉE   │ (/api/memory/search/unified)
        └───────┬────────┘
                │
    ┌───────────┼───────────┬───────────────┐
    │           │           │               │
┌───▼───┐  ┌───▼────┐  ┌───▼────┐  ┌──────▼──────┐
│  STM  │  │  LTM   │  │THREADS │  │  MESSAGES   │
│(SQL)  │  │(Vector)│  │ (SQL)  │  │    (SQL)    │
└───────┘  └────────┘  └────────┘  └─────────────┘
```

---

## 🔍 1. STM (Short-Term Memory)

### **Table `sessions`**

**Fonction:** Résumés conversationnels et métadonnées extraites

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | TEXT | UUID session |
| `user_id` | TEXT | Propriétaire |
| `summary` | TEXT | **Résumé IA de la conversation** |
| `extracted_concepts` | JSON | **Liste concepts clés** |
| `extracted_entities` | JSON | **Entités nommées** |
| `created_at` | TEXT | Date création (ISO 8601) |
| `updated_at` | TEXT | Dernière modification |

### **API REST**

```http
GET /api/memory/tend-garden?limit=20
Authorization: Bearer {token}
```

**Réponse:**
```json
{
  "status": "ok",
  "summaries": [
    {
      "session_id": "abc123",
      "updated_at": "2025-10-07T14:32:15+00:00",
      "summary": "Discussion sur Docker et containerisation",
      "concept_count": 5,
      "entity_count": 3
    }
  ],
  "total": 42
}
```

---

## 🧬 2. LTM (Long-Term Memory)

### **Collection ChromaDB `emergence_knowledge`**

**Fonction:** Embeddings vectoriels avec métadonnées enrichies

| Métadonnée | Type | Description |
|------------|------|-------------|
| `type` | str | `concept`, `fact`, `preference` |
| `concept_text` | str | **Texte du concept** |
| `user_id` | str | Propriétaire |
| `first_mentioned_at` | ISO 8601 | **📅 Première mention** |
| `last_mentioned_at` | ISO 8601 | **📅 Dernière mention** |
| `mention_count` | int | **Compteur récurrences** |
| `thread_ids_json` | str | **Liste threads (JSON)** |
| `vitality` | float | Score pertinence (0-1) |
| `similarity_score` | float | Similarité cosinus |

### **API REST**

```http
GET /api/memory/concepts/search?q=docker&limit=10
Authorization: Bearer {token}
```

**Réponse:**
```json
{
  "query": "docker",
  "results": [
    {
      "concept_text": "CI/CD pipeline avec Docker",
      "first_mentioned_at": "2025-10-02T14:32:00+00:00",
      "last_mentioned_at": "2025-10-07T09:15:00+00:00",
      "mention_count": 3,
      "thread_ids": ["thread_xyz", "thread_abc"],
      "similarity_score": 0.87
    }
  ],
  "count": 1
}
```

---

## 💬 3. THREADS & MESSAGES

### **Table `threads` (enrichie)**

**Fonction:** Conversations archivables avec métadonnées temps réel

| Colonne | Type | Description | 🆕 |
|---------|------|-------------|----|
| `id` | TEXT | UUID thread | |
| `user_id` | TEXT | Propriétaire | |
| `type` | TEXT | `chat` ou `debate` | |
| `title` | TEXT | Titre conversation | |
| `archived` | INT | 0=actif, 1=archivé | |
| `archival_reason` | TEXT | Motif archivage | ✅ |
| `last_message_at` | TEXT | Date dernier message | ✅ |
| `message_count` | INT | Nombre messages | ✅ |
| `created_at` | TEXT | Date création | |
| `updated_at` | TEXT | Dernière modification | |

### **🔓 ACCÈS ARCHIVES DÉBLOQUÉ**

#### **Avant (v1.x) :**
```python
# ❌ Archives INACCESSIBLES
clauses = ["archived = 0"]  # Filtre dur
```

#### **Maintenant (v2.0) :**
```python
# ✅ Archives ACCESSIBLES
async def get_threads(
    db, user_id,
    include_archived: bool = False,  # ← NOUVEAU
    archived_only: bool = False      # ← NOUVEAU
)
```

### **API REST**

#### **Liste threads (avec/sans archives)**
```http
GET /api/threads/?include_archived=true
Authorization: Bearer {token}
```

#### **Liste UNIQUEMENT archives**
```http
GET /api/threads/archived/list?limit=20
Authorization: Bearer {token}
```

**Réponse:**
```json
{
  "items": [
    {
      "id": "thread_xyz",
      "title": "Discussion Docker",
      "archived": 1,
      "archival_reason": "Résolu - conteneurisation OK",
      "last_message_at": "2025-09-28T18:45:00+00:00",
      "message_count": 42,
      "created_at": "2025-09-28T10:00:00+00:00"
    }
  ]
}
```

---

## 🕰️ 4. RECHERCHE TEMPORELLE

### **TemporalSearch Engine**

**Fonction:** Fulltext search dans messages archivés avec filtres dates

```http
GET /api/memory/search?q=docker&start_date=2025-01-01&end_date=2025-10-07
Authorization: Bearer {token}
```

**Réponse:**
```json
{
  "query": "docker",
  "results": [
    {
      "id": "msg_123",
      "thread_id": "thread_xyz",
      "role": "user",
      "content": "Comment configurer Docker avec Nginx ?",
      "created_at": "2025-09-28T14:30:00+00:00",
      "agent_id": "neo"
    }
  ],
  "count": 1,
  "filters": {
    "start_date": "2025-01-01",
    "end_date": "2025-10-07"
  }
}
```

---

## 🎯 5. RECHERCHE UNIFIÉE (NOUVEAU)

### **Endpoint `/api/memory/search/unified`**

**Fonction:** Recherche simultanée dans **STM + LTM + Threads + Messages**

```http
GET /api/memory/search/unified?q=docker&limit=10&include_archived=true
Authorization: Bearer {token}
```

**Réponse:**
```json
{
  "query": "docker",
  "stm_summaries": [
    {
      "session_id": "sess_123",
      "summary": "Discussion Docker et CI/CD",
      "created_at": "2025-10-05T10:00:00+00:00",
      "concept_count": 5
    }
  ],
  "ltm_concepts": [
    {
      "concept_text": "Docker containerisation",
      "first_mentioned_at": "2025-09-28T10:15:00+00:00",
      "mention_count": 3,
      "thread_ids": ["thread_abc", "thread_def"]
    }
  ],
  "threads": [
    {
      "thread_id": "thread_xyz",
      "title": "Setup Docker production",
      "archived": true,
      "last_message_at": "2025-09-30T16:20:00+00:00",
      "message_count": 28
    }
  ],
  "messages": [
    {
      "id": "msg_456",
      "content": "Docker Compose configuration...",
      "created_at": "2025-09-28T14:30:00+00:00"
    }
  ],
  "total_results": 42
}
```

---

## 🤖 6. CAPACITÉS DES AGENTS

### **Ce que les agents PEUVENT faire :**

| Fonctionnalité | Endpoint | Exemple |
|----------------|----------|---------|
| ✅ Rechercher concepts | `GET /api/memory/concepts/search` | "Quand ai-je parlé de Docker ?" |
| ✅ Accéder archives | `GET /api/threads/?include_archived=true` | "Retrouve notre discussion de septembre" |
| ✅ Dates précises (h:min:sec) | Métadonnées ISO 8601 | "Rappelle-moi ce que j'ai dit le 28/09 à 14h30" |
| ✅ Compter récurrences | `mention_count` | "Combien de fois ai-je parlé de CI/CD ?" |
| ✅ Identifier threads | `thread_ids_json` | "Dans quelles conversations ai-je évoqué ça ?" |
| ✅ Recherche temporelle | `GET /api/memory/search` | "Messages contenant 'nginx' en septembre" |
| ✅ Recherche unifiée | `GET /api/memory/search/unified` | "Tout ce qui concerne Docker" |
| ✅ **Suggestions proactives** | `ws:proactive_hint` (auto) | **"💡 Rappel: Tu préfères Python" (après 3 mentions)** |
| ✅ **Cache préférences** | Automatique (5min TTL) | **Performance: -71% latence contexte** |

### **Limitations connues :**

| ❌ Limitation | Raison | Workaround |
|--------------|--------|------------|
| Pas de fuzzy search | Matching exact uniquement | Utiliser synonymes ou variantes |
| Limite 50 résultats/requête | Protection performance | Requêtes multiples avec pagination |
| Pas de tri custom | Tri timestamp fixe | Filtrer côté client si besoin |

---

## 📈 7. FORMATS TEMPORELS

### **Standard ISO 8601 partout**

```
Format complet: 2025-10-07T14:32:15.234567+00:00
               ┬────┬──┬──┬──┬──┬──┬──────────┬──────
               │    │  │  │  │  │  │          └─ Timezone UTC
               │    │  │  │  │  │  └─ Microsecondes
               │    │  │  │  │  └─ Secondes
               │    │  │  │  └─ Minutes
               │    │  │  └─ Heures (24h)
               │    │  └─ Jour
               │    └─ Mois
               └─ Année
```

### **Affichage UI (français)**

```javascript
new Intl.DateTimeFormat('fr-FR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',    // ✅ HEURE
  minute: '2-digit'   // ✅ MINUTE
})

// Résultat: "07/10/2025, 14:32"
```

---

## 🔧 8. MIGRATION BASE DE DONNÉES

### **Appliquer les enrichissements (v2.0)**

```bash
# Exécuter la migration
python -m backend.core.database.migrate

# Vérifier les nouvelles colonnes
sqlite3 emergence.db "PRAGMA table_info(threads);"
```

**Colonnes ajoutées :**
- `last_message_at TEXT`
- `message_count INTEGER DEFAULT 0`
- `archival_reason TEXT`

**Triggers automatiques :**
- Mise à jour `last_message_at` à chaque nouveau message
- Incrémentation `message_count` automatique
- Décrémentation lors de suppression

---

## ⚡ 9. OPTIMISATIONS PERFORMANCE (Phase P2)

### **Gains de Performance**

| Métrique | Avant P2 | Après P2 | Amélioration |
|----------|----------|----------|--------------|
| **Latence contexte LTM** | ~120ms | **35ms** | **-71%** ✅ |
| **Cache hit rate préférences** | 0% | **100%** | **+100%** ✅ |
| **Queries ChromaDB/message** | 2 | **1** | **-50%** ✅ |

### **1. Configuration HNSW ChromaDB**

**Optimisation**: [vector_service.py:595-638](../src/backend/features/memory/vector_service.py#L595-L638)

```python
metadata = {
    "hnsw:space": "cosine",  # Cosine similarity (standard embeddings)
    "hnsw:M": 16,            # Connexions par nœud (balance précision/vitesse)
}
```

**Résultat**: Latence queries **-82.5%** (200ms → 35ms)

### **2. Cache Préférences In-Memory**

**Implémentation**: [memory_ctx.py:32-35](../src/backend/features/chat/memory_ctx.py#L32-L35)

```python
self._prefs_cache: Dict[str, Tuple[str, datetime]] = {}
self._cache_ttl = timedelta(minutes=5)  # TTL 5 min
```

**Résultat**: Hit rate **100%** (couvre ~10 messages typiques)

### **3. Métriques Prometheus Performance**

```python
memory_cache_operations = Counter(
    "memory_cache_operations_total",
    "Memory cache operations (hit/miss)",
    ["operation", "type"]  # hit|miss, preferences|concepts
)
```

**Queries Prometheus**:
```promql
# Cache hit rate
sum(rate(memory_cache_operations_total{operation="hit"}[5m]))
/ sum(rate(memory_cache_operations_total[5m]))
```

---

## 🔔 10. HINTS PROACTIFS (Phase P2)

### **ProactiveHintEngine**

**Fonction**: Génération suggestions contextuelles basées sur préférences et récurrence concepts

**Fichier**: [proactive_hints.py](../src/backend/features/memory/proactive_hints.py)

### **Stratégies de Hints**

| Type | Trigger | Exemple |
|------|---------|---------|
| **preference_reminder** | Concept récurrent (3 mentions) match préférence | "💡 Tu as mentionné 'python' 3 fois. Rappel: I prefer Python for scripting" |
| **intent_followup** | Intention non complétée | "📋 Rappel: Tu voulais configurer Docker la semaine dernière" |
| **constraint_warning** | Violation contrainte (futur) | "⚠️ Attention: Cette approche contredit ta contrainte X" |

### **Configuration**

```python
max_hints_per_call = 3        # Max hints par réponse
recurrence_threshold = 3      # Trigger après 3 mentions
min_relevance_score = 0.6     # Score minimum émission
```

### **Event WebSocket `ws:proactive_hint`**

```json
{
  "type": "ws:proactive_hint",
  "payload": {
    "hints": [
      {
        "id": "hint_abc123",
        "type": "preference_reminder",
        "title": "Rappel: Préférence détectée",
        "message": "💡 Tu as mentionné 'python' 3 fois...",
        "relevance_score": 0.85,
        "source_preference_id": "pref_123",
        "action_label": "Appliquer",
        "action_payload": {...}
      }
    ]
  }
}
```

### **Métriques Prometheus Hints**

```python
proactive_hints_generated = Counter(
    "memory_proactive_hints_generated_total",
    "Proactive hints generated by type",
    ["type"]  # preference_reminder | intent_followup | constraint_warning
)

proactive_hints_relevance = Histogram(
    "memory_proactive_hints_relevance_score",
    "Relevance scores of generated hints",
    buckets=[0.0, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
```

**Queries Prometheus**:
```promql
# Hints générés par type
sum by (type) (rate(memory_proactive_hints_generated_total[5m]))

# Score relevance moyen
histogram_quantile(0.5, rate(memory_proactive_hints_relevance_score_bucket[5m]))
```

---

## 📚 11. EXEMPLES D'UTILISATION AGENTS

### **Exemple 1 : Recherche historique**

```python
# Agent NEO répond à: "Quand avons-nous parlé de containerisation ?"

tracker = ConceptRecallTracker(db, vector_service)
results = await tracker.query_concept_history(
    concept_text="containerisation",
    user_id=current_user_id,
    limit=10
)

response = f"Nous avons évoqué la containerisation {results[0]['mention_count']} fois :\n"
response += f"- Première mention : {format_date(results[0]['first_mentioned_at'])}\n"
response += f"- Dernière mention : {format_date(results[0]['last_mentioned_at'])}\n"
response += f"- Conversations concernées : {', '.join(results[0]['thread_ids'])}"
```

### **Exemple 2 : Récupération archives**

```python
# Agent ANIMA répond à: "Retrouve notre discussion de septembre sur Docker"

threads = await queries.get_threads(
    db,
    user_id=current_user_id,
    include_archived=True,
    limit=50
)

# Filtrer par date
from datetime import datetime
sept_threads = [
    t for t in threads
    if "docker" in (t.get("title") or "").lower()
    and "2025-09" in (t.get("created_at") or "")
]

# Charger messages du thread
messages = await queries.get_messages(
    db,
    thread_id=sept_threads[0]["id"],
    user_id=current_user_id,
    limit=200
)
```

### **Exemple 3 : Recherche temporelle précise**

```python
# Agent NEXUS répond à: "Qu'ai-je dit sur nginx le 28 septembre à 14h ?"

temporal = TemporalSearch(db)
results = await temporal.search_messages(
    query="nginx",
    limit=50
)

# Filtrer par timestamp précis
target_date = "2025-09-28T14:"
matching = [
    r for r in results
    if target_date in r.get("created_at", "")
]
```

---

## 🎨 10. INTERFACE UTILISATEUR

### **ConceptSearch Component**

**Features :**
- ✅ Filtres temporels (date début/fin)
- ✅ Checkbox "Inclure archives"
- ✅ Bouton "Recherche complète" (unified)
- ✅ Affichage timestamps précis
- ✅ Compteurs de récurrences

**Emplacement :**
- `/memory` → Centre mémoire principal
- Intégré dans ThreadsPanel (sidebar)

---

## 🚀 11. DÉPLOIEMENT & TESTS

### **Checklist déploiement**

```bash
# 1. Vérifier migrations
python -m backend.core.database.migrate

# 2. Tester endpoint archives
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/threads/archived/list

# 3. Tester recherche unifiée
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/memory/search/unified?q=test"

# 4. Vérifier triggers SQL
sqlite3 emergence.db "SELECT * FROM sqlite_master WHERE type='trigger';"
```

### **Tests unitaires**

```python
# tests/test_memory_archives.py
async def test_archived_threads_accessible():
    threads = await queries.get_threads(
        db, user_id="test_user", include_archived=True
    )
    assert any(t["archived"] == 1 for t in threads)

async def test_unified_search():
    results = await unified_memory_search(
        request, q="docker", limit=10, include_archived=True
    )
    assert results["total_results"] > 0
    assert len(results["ltm_concepts"]) > 0
```

---

## 📞 SUPPORT

**Problèmes connus :** [GitHub Issues](https://github.com/emergence/issues)
**Documentation complète :** `/docs/architecture/memory.md`
**Changelog :** `/CHANGELOG.md`

---

**Dernière mise à jour :** 2025-10-10 (Phase P2 complétée)
**Auteur :** Équipe EMERGENCE
**Licence :** Voir LICENSE

---

## 📖 Références Phase P2

### Documentation
- [P2_COMPLETION_FINAL_STATUS.md](validation/P2_COMPLETION_FINAL_STATUS.md) - Résumé complet Phase P2
- [P2_SPRINT1_COMPLETION_STATUS.md](validation/P2_SPRINT1_COMPLETION_STATUS.md) - Sprint 1 (Performance)
- [P2_SPRINT2_PROACTIVE_HINTS_STATUS.md](validation/P2_SPRINT2_PROACTIVE_HINTS_STATUS.md) - Sprint 2 (Hints)
- [MEMORY_P2_PERFORMANCE_PLAN.md](optimizations/MEMORY_P2_PERFORMANCE_PLAN.md) - Plan détaillé P2

### Tests
- [test_memory_performance.py](../tests/backend/features/test_memory_performance.py) - 5 tests performance
- [test_proactive_hints.py](../tests/backend/features/test_proactive_hints.py) - 16 tests hints
