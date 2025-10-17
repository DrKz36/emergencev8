# 🧠 Agent Memory Isolation - Documentation Technique

## 📋 Vue d'ensemble

Le système d'isolation mémoire agent-spécifique garantit que chaque agent (Anima, Neo, Nexus) possède son propre contexte mémoire isolé. Quand un utilisateur demande à un agent "de quoi on a parlé", l'agent ne voit que les sujets abordés avec lui, et non ceux discutés avec d'autres agents.

### Problème résolu

**Avant :** Tous les agents partageaient la même mémoire globale
- Neo te répondait avec les sujets discutés avec Anima
- Confusion totale dans les résumés chronologiques
- Impossible de distinguer les conversations par agent

**Après :** Chaque agent a sa propre mémoire isolée
- Neo ne voit que ses propres conversations avec l'utilisateur
- Anima a ses propres souvenirs distincts
- Nexus garde ses propres échanges séparés

---

## 🏗️ Architecture

### Composants principaux

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (WebSocket)                  │
│  - Écoute HELLO/ACK/SYNC                                 │
│  - Stocke contexte par agent dans state manager          │
│  - Envoie ACK en réponse au HELLO                        │
└─────────────────────────────────────────────────────────┘
                           ▼ ▲
                   WebSocket Protocol
                           ▼ ▲
┌─────────────────────────────────────────────────────────┐
│              Backend (Connection Manager)                │
│  - HandshakeHandler pour HELLO/ACK/SYNC                  │
│  - MemorySyncManager pour isolation contexte             │
└─────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Memory Layer                           │
│  - MemoryContextBuilder (filtrage agent_id)              │
│  - MemoryQueryTool (requêtes chronologiques)             │
│  - ChromaDB (stockage avec agent_id metadata)            │
└─────────────────────────────────────────────────────────┘
```

---

## 📡 Protocole de Handshake (HELLO/ACK/SYNC)

### Flux de communication

```
Agent Backend              WebSocket               Frontend Client
     │                        │                          │
     │───── HELLO ──────────>│─────────────────────────>│
     │   (context_id, rev)    │                          │
     │                        │                          │
     │                        │<───── ACK ───────────────│
     │<────────────────────────│   (confirm context)      │
     │                        │                          │
     │── SYNC (if needed) ───>│─────────────────────────>│
     │   (resync data)        │                          │
```

### Message HELLO (Backend → Frontend)

Envoyé avant chaque réponse d'agent pour synchroniser le contexte.

**Format :**
```json
{
  "type": "ws:handshake_hello",
  "payload": {
    "agent_id": "neo",
    "model": "gemini-1.5-flash",
    "provider": "google",
    "context_id": "conv:6f2e91a1",
    "context_rev": "rev:0027a",
    "last_seen_at": "2025-10-17T12:03:11Z",
    "capabilities": ["rag:on", "tools:web", "memory:stm+ltm"],
    "memory_stats": {
      "stm": 5,
      "ltm": 42
    }
  }
}
```

**Champs :**
- `agent_id`: Identifiant agent (anima, neo, nexus)
- `context_id`: ID contexte conversation (format `conv:{session_id[:12]}`)
- `context_rev`: Hash révision contexte (change à chaque mise à jour mémoire)
- `capabilities`: Capacités de l'agent (RAG, tools, etc.)
- `memory_stats`: Compteurs STM (court-terme) et LTM (long-terme)

### Message ACK (Frontend → Backend)

Réponse du client pour confirmer la réception du HELLO.

**Format :**
```json
{
  "type": "handshake.ack",
  "payload": {
    "agent_id": "neo",
    "context_id": "conv:6f2e91a1",
    "context_rev": "rev:0027a",
    "user_id": "user_abc123"
  }
}
```

### Message SYNC (Backend → Frontend)

Envoyé si le client est désynchronisé (révisions différentes).

**Format :**
```json
{
  "type": "ws:handshake_sync",
  "payload": {
    "agent_id": "neo",
    "context_id": "conv:6f2e91a1",
    "context_rev": "rev:0028b",
    "status": "desync",
    "memory_stats": {
      "stm": 5,
      "ltm": 43
    },
    "timestamp": "2025-10-17T12:03:15Z"
  }
}
```

**Status possibles :**
- `ok`: Synchronisé
- `desync`: Révisions différentes (resync nécessaire)
- `stale`: Contexte périmé

---

## 🗄️ Stockage et filtrage mémoire

### Structure ChromaDB

Chaque item mémoire est tagué avec `agent_id` :

```python
{
  "id": "concept_123",
  "document": "CI/CD pipeline",
  "metadata": {
    "user_id": "user_abc",
    "agent_id": "neo",  # 🆕 Tag agent
    "type": "concept",
    "first_mentioned_at": "2025-10-05T14:32:00Z",
    "last_mentioned_at": "2025-10-08T09:15:00Z",
    "mention_count": 3
  }
}
```

### Filtrage par agent

**MemoryContextBuilder** (memory_ctx.py) :
```python
# Filtre combiné user_id + agent_id
where_filter = {
    "$and": [
        {"user_id": uid},
        {"agent_id": agent_id.lower()}
    ]
}
```

**MemoryQueryTool** (memory_query_tool.py) :
```python
# Liste sujets abordés avec Neo uniquement
topics = await memory_query_tool.list_discussed_topics(
    user_id="user_abc",
    agent_id="neo",
    timeframe="week"
)
```

---

## 🔧 Utilisation pour développeurs

### Backend : Envoyer HELLO avant réponse agent

Dans [service.py:2507-2518](src/backend/features/chat/service.py#L2507-L2518) :

```python
# Envoi du HELLO après model_info
if uid and hasattr(connection_manager, 'send_agent_hello'):
    await connection_manager.send_agent_hello(
        session_id=session_id,
        agent_id=agent_id,
        model=primary_model,
        provider=primary_provider,
        user_id=uid
    )
```

### Frontend : Gérer les messages HELLO/SYNC

Dans [websocket.js:380-448](src/frontend/core/websocket.js#L380-L448) :

```javascript
// Handler HELLO
if (msg?.type === 'ws:handshake_hello') {
  const p = msg.payload || {};

  // Stocker contexte dans state
  this.state?.set?.(`agents.${p.agent_id}.context`, {
    context_id: p.context_id,
    context_rev: p.context_rev,
    capabilities: p.capabilities || [],
    memory_stats: p.memory_stats || {}
  });

  // Envoyer ACK
  this.send({
    type: 'handshake.ack',
    payload: {
      agent_id: p.agent_id,
      context_id: p.context_id,
      context_rev: p.context_rev,
      user_id: this.state?.get?.('user.id')
    }
  });
}
```

### Ajouter agent_id lors du stockage mémoire

Utiliser `MemorySyncManager.add_agent_tag_to_memory()` :

```python
from backend.core.memory.memory_sync import MemorySyncManager

# Enrichir item avant stockage
memory_item = {
    "id": "concept_xyz",
    "document": "Docker containers",
    "metadata": {
        "user_id": "user_123",
        "type": "concept"
    }
}

# Ajouter tag agent
memory_sync = MemorySyncManager(vector_service)
tagged_item = memory_sync.add_agent_tag_to_memory(
    memory_item,
    agent_id="anima"
)

# → metadata contiendra désormais "agent_id": "anima"
```

---

## 🧪 Tests et validation

### Vérifier isolation mémoire

1. **Créer souvenirs distincts par agent :**
   ```python
   # Avec Anima
   await chat_service.process_message(
       session_id="sess1",
       agent_id="anima",
       message="On discute de Python"
   )

   # Avec Neo
   await chat_service.process_message(
       session_id="sess1",
       agent_id="neo",
       message="On discute de Kubernetes"
   )
   ```

2. **Demander résumé à chaque agent :**
   ```python
   # Anima doit voir seulement "Python"
   response_anima = await chat_service.process_message(
       session_id="sess1",
       agent_id="anima",
       message="De quoi on a parlé ?"
   )

   # Neo doit voir seulement "Kubernetes"
   response_neo = await chat_service.process_message(
       session_id="sess1",
       agent_id="neo",
       message="De quoi on a parlé ?"
   )
   ```

3. **Vérifier logs :**
   ```
   [MemoryContext] Chronological context for timeframe 'all' (agent: anima)
   [MemoryQueryTool] Récupéré 1 sujets pour user 'user_123' (timeframe=all, limit=50)
   → Python

   [MemoryContext] Chronological context for timeframe 'all' (agent: neo)
   [MemoryQueryTool] Récupéré 1 sujets pour user 'user_123' (timeframe=all, limit=50)
   → Kubernetes
   ```

### Tester handshake protocol

**Console navigateur :**
```javascript
// Observer les messages HELLO
window.addEventListener('message', (e) => {
  if (e.data?.type === 'ws:handshake_hello') {
    console.log('HELLO reçu:', e.data.payload);
  }
});

// Vérifier contexte stocké
app.state.get('agents.neo.context');
// → {context_id: "conv:...", context_rev: "rev:...", ...}
```

---

## 📊 Métriques et monitoring

### Logs importants

**Backend :**
- `[MemorySync] Context created for {agent_id}` : Contexte créé
- `[Handshake] HELLO sent → {agent_id}` : HELLO envoyé
- `[MemoryContext] Chronological context for timeframe '{tf}' (agent: {agent_id})` : Requête chronologique filtrée

**Frontend :**
- `[WebSocket] HELLO received: {agent_id}` : HELLO reçu
- `[WebSocket] SYNC received: {agent_id} status: {status}` : SYNC reçu

### Compteurs mémoire par agent

Dans state manager frontend :
```javascript
// Accéder aux stats mémoire d'un agent
const neoStats = app.state.get('agents.neo.context.memory_stats');
// → {stm: 5, ltm: 42}
```

---

## 🐛 Troubleshooting

### Problème : Agents voient toujours la mémoire globale

**Cause :** Anciens items mémoire sans tag `agent_id`

**Solution :** Migration des données existantes
```python
# Script de migration
collection = vector_service.get_or_create_collection("emergence_knowledge")
results = collection.get(where={"type": "concept"})

for i, item_id in enumerate(results["ids"]):
    metadata = results["metadatas"][i]

    # Si pas d'agent_id, inférer depuis le contexte
    if "agent_id" not in metadata:
        # Stratégie : assigner à "anima" par défaut
        metadata["agent_id"] = "anima"

        collection.update(
            ids=[item_id],
            metadatas=[metadata]
        )
```

### Problème : HELLO pas reçu côté frontend

**Cause :** HandshakeHandler non initialisé

**Vérif backend :**
```python
# Dans logs au démarrage
✅ Handshake handler initialized for agent-specific context sync
```

**Si absent :**
- Vérifier que `vector_service` est bien injecté dans `ConnectionManager`
- Vérifier imports dans [websocket.py:27-28](src/backend/core/websocket.py#L27-L28)

### Problème : Contexte désynchronisé (SYNC fréquents)

**Cause :** Révisions changent trop souvent

**Solution :** Ajuster logique `update_context_revision()` dans [memory_sync.py:95-116](src/backend/core/memory/memory_sync.py#L95-L116)

---

## 🔮 Évolutions futures

### Phase 2 : Mémoire partagée sélective

Permettre à un agent d'accéder aux souvenirs d'un autre agent avec permission explicite.

**Use case :** "Neo, peux-tu expliquer à Nexus ce qu'on a discuté sur Kubernetes ?"

**Implémentation :**
```python
# Nouvelle méthode MemorySyncManager
async def share_memory_across_agents(
    self,
    source_agent_id: str,
    target_agent_id: str,
    user_id: str,
    topic_filter: Optional[str] = None
):
    # Dupliquer souvenirs source → target avec flag "shared_from"
    ...
```

### Phase 3 : Timeline inter-agents

Vue chronologique unifiée avec indication de l'agent.

**Format :**
```
**Cette semaine:**
- CI/CD pipeline (Neo, 5 oct 14h32) - 3 conversations
- Docker containers (Anima, 8 oct 09h15) - 2 conversations
```

---

## 📚 Références

### Fichiers clés

**Backend :**
- [memory_sync.py](src/backend/core/memory/memory_sync.py) - Gestionnaire isolation contexte
- [handshake.py](src/backend/core/ws/handlers/handshake.py) - Handler protocole HELLO/ACK
- [websocket.py](src/backend/core/websocket.py) - ConnectionManager avec handshake
- [memory_ctx.py](src/backend/features/chat/memory_ctx.py) - MemoryContextBuilder (filtrage)
- [memory_query_tool.py](src/backend/features/memory/memory_query_tool.py) - Requêtes chronologiques
- [service.py](src/backend/features/chat/service.py) - ChatService (envoi HELLO)

**Frontend :**
- [websocket.js](src/frontend/core/websocket.js) - Client WebSocket (handlers HELLO/SYNC)

### Diagrammes de séquence

Voir : [AGENT_SYNC.md](AGENT_SYNC.md) (à créer) pour diagrammes détaillés.

---

## ✅ Checklist d'intégration

Pour intégrer l'isolation mémoire dans un nouveau composant :

- [ ] Import `MemorySyncManager` si manipulation contexte
- [ ] Passer `agent_id` aux méthodes de requête mémoire
- [ ] Ajouter tag `agent_id` lors du stockage (via `add_agent_tag_to_memory`)
- [ ] Émettre HELLO avant envoi réponse agent
- [ ] Gérer ACK/SYNC côté frontend si nouveau canal WebSocket
- [ ] Logger événements avec `[{component}] Agent: {agent_id}` pour debug
- [ ] Tester isolation avec 2+ agents différents

---

**Auteur :** Système Emergence V8
**Date :** 17 octobre 2025
**Version :** 1.0
