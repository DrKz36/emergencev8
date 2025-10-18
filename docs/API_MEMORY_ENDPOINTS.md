# 📋 API Memory Endpoints - Sprint 5

**Date création**: 2025-10-18
**Version**: 1.0
**Roadmap**: MEMORY_REFACTORING_ROADMAP.md Sprint 5

---

## 🎯 Endpoints Disponibles

### 🏠 Dashboard & Stats

#### `GET /api/memory/dashboard`
**🆕 Sprint 5 - Dashboard Unifié**

Retourne vue complète mémoire utilisateur.

**Response**:
```json
{
  "stats": {
    "conversations_total": 47,
    "conversations_active": 5,
    "conversations_archived": 42,
    "concepts_total": 156,
    "preferences_active": 12,
    "memory_size_mb": 4.2
  },
  "top_preferences": [
    {
      "text": "Préfère Docker pour containerisation",
      "confidence": 0.9,
      "topic": "tech"
    }
  ],
  "top_concepts": [
    {
      "text": "Docker containerisation",
      "mentions": 8,
      "last_mentioned": "2025-10-18T14:30:00Z"
    }
  ],
  "recent_archives": [
    {
      "thread_id": "thread_123",
      "title": "Discussion Docker",
      "archived_at": "2025-10-15T14:30:00Z",
      "message_count": 15,
      "consolidated": true
    }
  ],
  "timeline": [...]
}
```

---

#### `GET /api/memory/user/stats`
**Stats utilisateur détaillées**

Retourne statistiques mémoire détaillées (legacy endpoint).

**Response**:
```json
{
  "preferences": {
    "total": 12,
    "top": [...],
    "by_type": {"preference": 8, "intent": 3, "constraint": 1}
  },
  "concepts": {
    "total": 47,
    "top": [...]
  },
  "stats": {
    "sessions_analyzed": 23,
    "threads_archived": 5,
    "ltm_size_mb": 2.4
  }
}
```

---

### 💾 Export / Import

#### `GET /api/memory/concepts/export`
**Export tous concepts utilisateur**

Format JSON pour backup/transfert.

**Response**:
```json
{
  "concepts": [
    {
      "id": "concept_123",
      "concept_text": "Docker containerisation",
      "description": "Technologie containerisation",
      "tags": ["tech", "devops"],
      "relations": [],
      "occurrence_count": 8,
      "first_mentioned": "2025-10-10T10:00:00Z",
      "last_mentioned": "2025-10-18T14:30:00Z",
      "thread_ids": ["thread_1", "thread_2"]
    }
  ],
  "total": 156,
  "exported_at": "2025-10-18T15:00:00Z",
  "user_id": "user_123"
}
```

---

#### `POST /api/memory/concepts/import`
**Import concepts depuis backup**

**Body**:
```json
{
  "concepts": [...],
  "mode": "merge"  // "merge" | "replace"
}
```

**Response**:
```json
{
  "status": "success",
  "imported": 156,
  "mode": "merge"
}
```

---

### 🔍 Recherche & Requêtes

#### `GET /api/memory/search?q={query}&limit={limit}`
**Recherche vectorielle concepts**

Recherche sémantique dans concepts utilisateur.

**Query Params**:
- `q`: Requête texte (required)
- `limit`: Nombre résultats (default: 10)
- `start_date`: Filtre date début (optionnel)

---

#### `GET /api/memory/search/unified?q={query}`
**Recherche unifiée (concepts + préférences)**

Recherche combinée tous types mémoire.

---

#### `GET /api/memory/concepts/search?q={query}`
**Recherche concepts spécifique**

Recherche limitée aux concepts uniquement.

---

### 🧠 Gestion Concepts

#### `GET /api/memory/concepts/graph`
**Graph visualisation concepts**

Retourne données pour visualisation graphe relations concepts.

**Response**:
```json
{
  "nodes": [
    {
      "id": "concept_123",
      "label": "Docker",
      "mentions": 8
    }
  ],
  "edges": [
    {
      "source": "concept_123",
      "target": "concept_456",
      "type": "related"
    }
  ]
}
```

---

### 📝 Gestion Threads / Conversations

**Endpoints dans `/api/threads/`**:

#### `GET /api/threads/`
Liste threads utilisateur (actifs).

#### `GET /api/threads/archived/list`
Liste threads archivés uniquement.

#### `PATCH /api/threads/{thread_id}`
Modifier thread (archiver, désarchiver, renommer).

**Body**:
```json
{
  "archived": true,
  "archival_reason": "conversation_finished"
}
```

#### `DELETE /api/threads/{thread_id}`
Supprimer thread définitivement.

#### `GET /api/threads/{thread_id}/messages`
Récupérer messages d'un thread.

#### `POST /api/threads/{thread_id}/export`
Exporter thread en JSON.

---

### 🔧 Maintenance & Consolidation

#### `POST /api/memory/tend-garden`
**Consolidation mémoire manuelle**

Lance consolidation LTM pour session/thread.

**Body**:
```json
{
  "session_id": "session_123",  // Optionnel
  "thread_id": "thread_456"     // Optionnel
}
```

**Response**:
```json
{
  "status": "success",
  "new_concepts": 5,
  "new_preferences": 2
}
```

---

#### `POST /api/memory/consolidate_archived`
**Consolidation batch threads archivés**

**Sprint 2**: Consolide tous threads archivés non consolidés.

**Body**:
```json
{
  "user_id": "user_123",  // Optionnel (admin only si vide)
  "limit": 100            // Optionnel (default: 100)
}
```

**Response**:
```json
{
  "status": "success",
  "consolidated_count": 42,
  "skipped_count": 5,
  "total_archived": 47,
  "errors": []
}
```

---

## 🚀 Nouveautés Sprints 3-4-5

### Sprint 3: UnifiedMemoryRetriever
- Récupération contexte depuis STM + LTM + Archives
- Rappel proactif conversations archivées
- Endpoint: Pas d'endpoint dédié (intégré dans backend)

### Sprint 4: Isolation Agent Stricte
- Feature flag `STRICT_AGENT_ISOLATION`
- Monitoring violations cross-agent
- Script CLI: `python src/backend/cli/backfill_agent_ids.py`

### Sprint 5: Dashboard & Interface
- ✅ **Endpoint dashboard unifié**: `GET /api/memory/dashboard`
- ✅ Export/import concepts existants
- ✅ Endpoints threads existants (list, archive, delete)
- ✅ Recherche unifiée

---

## 📊 Format Réponses Standard

Tous endpoints retournent:
- **Success** (200): JSON data
- **Unauthorized** (401): `{"detail": "Authentication required"}`
- **Not Found** (404): `{"detail": "Resource not found"}`
- **Server Error** (500): `{"detail": "Error message"}`

---

## 🔐 Authentification

Tous endpoints requièrent authentification utilisateur via:
- Header `Authorization: Bearer <token>`
- Cookie session
- User ID extrait automatiquement via `shared_dependencies.get_user_id()`

---

## 📖 Documentation Interactive

API docs disponibles à:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

**🤖 Généré avec Claude Code**
**Version**: 1.0 (2025-10-18)
