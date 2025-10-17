# 🤝 Agent Memory Isolation - Synthèse Handshake Protocol

## 🎯 Objectif

**Problème résolu :** Les agents (Anima, Neo, Nexus) partageaient tous la même mémoire. Quand tu demandais à Neo "de quoi on a parlé", il te donnait les sujets abordés avec TOUS les agents, pas uniquement les siens.

**Solution implémentée :** Protocole de handshake HELLO/ACK/SYNC pour isoler la mémoire de chaque agent et synchroniser le contexte entre frontend et backend.

---

## 📡 Protocole HELLO/ACK/SYNC

### Flux complet

```
┌─────────────┐          ┌──────────────┐          ┌─────────────┐
│   Backend   │          │  WebSocket   │          │  Frontend   │
│  (Agent)    │          │              │          │  (Client)   │
└─────────────┘          └──────────────┘          └─────────────┘
       │                        │                          │
       │                        │                          │
       │──── 1. HELLO ────────>│─────────────────────────>│
       │  (context, révision)   │                          │
       │                        │                          │
       │                        │<──── 2. ACK ─────────────│
       │<───────────────────────│  (confirmation)          │
       │                        │                          │
       │── 3. SYNC (si besoin)─>│─────────────────────────>│
       │  (resynchronisation)   │                          │
       │                        │                          │
```

### 1. Message HELLO (Backend → Frontend)

**Quand :** Avant chaque réponse d'un agent

**Contenu :**
```json
{
  "type": "ws:handshake_hello",
  "payload": {
    "agent_id": "neo",
    "model": "gemini-1.5-flash",
    "provider": "google",
    "context_id": "conv:6f2e91a1",
    "context_rev": "rev:0027a",
    "capabilities": ["rag:on", "tools:web", "memory:stm+ltm"],
    "memory_stats": {
      "stm": 5,    // Court-terme
      "ltm": 42    // Long-terme
    }
  }
}
```

**Rôle :** Annonce le contexte mémoire de l'agent au client

### 2. Message ACK (Frontend → Backend)

**Quand :** En réponse immédiate au HELLO

**Contenu :**
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

**Rôle :** Confirme la bonne réception et synchronisation

### 3. Message SYNC (Backend → Frontend)

**Quand :** Si le client est désynchronisé (révisions différentes)

**Contenu :**
```json
{
  "type": "ws:handshake_sync",
  "payload": {
    "agent_id": "neo",
    "status": "desync",
    "context_rev": "rev:0028b",
    "memory_stats": {
      "stm": 5,
      "ltm": 43
    }
  }
}
```

**Status possibles :**
- `ok` : Tout est synchronisé
- `desync` : Révisions différentes
- `stale` : Contexte périmé

---

## 🗄️ Isolation mémoire : Comment ça marche ?

### Tagging des souvenirs

Chaque souvenir stocké dans ChromaDB est maintenant tagué avec `agent_id` :

```python
{
  "id": "concept_123",
  "document": "CI/CD pipeline",
  "metadata": {
    "user_id": "user_abc",
    "agent_id": "neo",        # 🆕 Tag agent
    "type": "concept",
    "first_mentioned_at": "2025-10-05T14:32:00Z",
    "mention_count": 3
  }
}
```

### Filtrage par agent

Quand Neo recherche ses souvenirs :

```python
where_filter = {
    "$and": [
        {"user_id": "user_abc"},
        {"agent_id": "neo"}        # Filtre sur agent_id
    ]
}
```

**Résultat :** Neo ne voit QUE les souvenirs où `agent_id = "neo"`

---

## 🔧 Fichiers modifiés/créés

### Backend (Python)

1. **[src/backend/core/memory/memory_sync.py](../src/backend/core/memory/memory_sync.py)** *(nouveau)*
   - `MemorySyncManager` : Gère les contextes par agent
   - `AgentContext` : Structure de données contexte
   - Méthodes : `create_agent_context()`, `update_context_revision()`, etc.

2. **[src/backend/core/ws/handlers/handshake.py](../src/backend/core/ws/handlers/handshake.py)** *(nouveau)*
   - `HandshakeHandler` : Gère HELLO/ACK/SYNC
   - Méthodes : `send_hello()`, `handle_ack()`, `send_sync_if_needed()`

3. **[src/backend/core/websocket.py](../src/backend/core/websocket.py)** *(modifié)*
   - Initialisation `HandshakeHandler` dans `ConnectionManager`
   - Nouvelle méthode `send_agent_hello()`

4. **[src/backend/features/chat/memory_ctx.py](../src/backend/features/chat/memory_ctx.py)** *(modifié)*
   - Ajout paramètre `agent_id` à `build_memory_context()`
   - Filtre vectoriel avec `agent_id`

5. **[src/backend/features/memory/memory_query_tool.py](../src/backend/features/memory/memory_query_tool.py)** *(modifié)*
   - Ajout paramètre `agent_id` à `list_discussed_topics()`
   - Ajout paramètre `agent_id` à `get_conversation_timeline()`
   - Filtre ChromaDB avec `agent_id`

6. **[src/backend/features/chat/service.py](../src/backend/features/chat/service.py)** *(modifié)*
   - Envoi HELLO après `model_info` (ligne 2507-2518)
   - Passage `agent_id` aux méthodes mémoire

### Frontend (JavaScript)

7. **[src/frontend/core/websocket.js](../src/frontend/core/websocket.js)** *(modifié)*
   - Handler `ws:handshake_hello` (ligne 380-415)
   - Handler `ws:handshake_sync` (ligne 417-448)
   - Stockage contexte agent dans state manager
   - Envoi ACK automatique

### Documentation

8. **[docs/AGENT_MEMORY_ISOLATION.md](AGENT_MEMORY_ISOLATION.md)** *(nouveau)*
   - Documentation technique complète
   - Guides d'utilisation pour développeurs
   - Exemples de tests et troubleshooting

9. **[docs/AGENT_SYNC.md](AGENT_SYNC.md)** *(ce fichier)*
   - Synthèse du protocole handshake
   - Vue d'ensemble pour utilisateurs

---

## ✅ Test rapide

### 1. Créer des souvenirs distincts

Parle de sujets différents avec chaque agent :

```
Toi → Anima : "On va discuter de Python aujourd'hui"
Anima : "D'accord, parlons de Python !"

Toi → Neo : "Je veux apprendre Kubernetes"
Neo : "Super, je vais t'expliquer Kubernetes"
```

### 2. Demander les résumés

```
Toi → Anima : "De quoi on a parlé ?"
Anima : "On a discuté de Python"  ✅ (uniquement Python)

Toi → Neo : "De quoi on a parlé ?"
Neo : "On a parlé de Kubernetes"  ✅ (uniquement Kubernetes)
```

### 3. Vérifier dans la console navigateur

Ouvre la console et observe les messages HELLO :

```javascript
// Observer HELLO
[WebSocket] HELLO received: anima rev:0027a STM:1 LTM:5
[WebSocket] HELLO received: neo rev:0028b STM:1 LTM:8

// Vérifier contexte stocké
app.state.get('agents.anima.context')
// → {context_rev: "rev:0027a", memory_stats: {stm: 1, ltm: 5}}

app.state.get('agents.neo.context')
// → {context_rev: "rev:0028b", memory_stats: {stm: 1, ltm: 8}}
```

---

## 🐛 Si ça ne marche pas

### Problème : Les agents voient toujours tout

**Cause probable :** Anciens souvenirs sans tag `agent_id`

**Solution :**
1. Vérifie dans ChromaDB si les items ont `agent_id` :
   ```python
   collection = vector_service.get_or_create_collection("emergence_knowledge")
   result = collection.get(limit=5)
   print(result["metadatas"])
   # Doit contenir "agent_id": "neo", etc.
   ```

2. Si absent, les nouveaux souvenirs seront bien taggés, mais les anciens non.

### Problème : Pas de HELLO dans la console

**Cause probable :** HandshakeHandler non initialisé

**Solution :**
1. Vérifie les logs backend au démarrage :
   ```
   ✅ Handshake handler initialized for agent-specific context sync
   ```

2. Si absent, vérifie que `vector_service` est bien dans `SessionManager`

---

## 🎨 Cas d'usage avancés

### Partage mémoire entre agents (futur)

Imaginez : "Neo, explique à Nexus ce qu'on a discuté sur Docker"

→ Phase 2 : permettre transfert sélectif de souvenirs entre agents

### Timeline unifiée (futur)

Vue chronologique montrant TOUS les sujets avec indication de l'agent :

```
**Cette semaine:**
- CI/CD (Neo, 5 oct) - 3 conversations
- Python (Anima, 8 oct) - 2 conversations
- Docker (Nexus, 10 oct) - 1 conversation
```

---

## 📚 En résumé

### Ce qui a été implémenté

✅ **Protocole HELLO/ACK/SYNC** pour synchronisation contexte agent
✅ **Isolation mémoire par agent** via tagging `agent_id`
✅ **Filtrage automatique** dans toutes les requêtes mémoire
✅ **Frontend synchronisé** avec état contexte par agent
✅ **Documentation complète** pour développeurs

### Ce que ça apporte

✅ **Clarté** : Chaque agent a ses propres souvenirs
✅ **Cohérence** : Les résumés correspondent aux conversations réelles
✅ **Évolutivité** : Base solide pour fonctionnalités avancées
✅ **Debuggabilité** : Logs et métriques par agent

### Prochaines étapes

🔜 **Tester en production** avec vrais utilisateurs
🔜 **Monitorer logs** pour détecter éventuels bugs
🔜 **Migrer anciens souvenirs** si nécessaire (assigner agent_id)
🔜 **Phase 2** : Partage mémoire sélectif entre agents

---

**Bravo ! Le système d'isolation mémoire agent est maintenant opérationnel ! 🎉**

Pour toute question : consulte [docs/AGENT_MEMORY_ISOLATION.md](AGENT_MEMORY_ISOLATION.md)
