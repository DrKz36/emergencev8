# 🧠 Capacités Mémoire du Système EMERGENCE

> **Version:** 2.0 - Mise à jour après audit complet (07/10/2025)
> **Statut:** ✅ Opérationnel avec accès archives activé

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

## 📚 9. EXEMPLES D'UTILISATION AGENTS

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

**Dernière mise à jour :** 2025-10-07
**Auteur :** Équipe EMERGENCE
**Licence :** Voir LICENSE
