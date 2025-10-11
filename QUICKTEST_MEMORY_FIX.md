# 🧪 Guide Test Rapide - Fix Timestamps Mémoire

> **Objectif** : Valider que les agents peuvent maintenant donner les dates réelles des conversations archivées

---

## ⚡ Test Express (5 minutes)

### 1. Démarrer l'environnement local

```bash
# Terminal 1 : Backend
npm run dev:backend

# Terminal 2 : Frontend (si nécessaire)
npm run dev:frontend
```

### 2. Créer un thread de test avec des messages datés

```bash
# Variables
export TOKEN="votre_token_local"
export BASE_URL="http://localhost:8000"

# 1. Créer un thread
THREAD_ID=$(curl -s -X POST "$BASE_URL/api/threads/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "chat", "title": "Test Docker Timestamps"}' | jq -r '.id')

echo "Thread créé : $THREAD_ID"

# 2. Envoyer 3 messages (simuler des dates différentes si possible)
curl -X POST "$BASE_URL/api/threads/$THREAD_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "Je veux apprendre Docker et la containerisation"
  }'

sleep 2

curl -X POST "$BASE_URL/api/threads/$THREAD_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "assistant",
    "content": "Docker est un outil de containerisation qui permet d isoler des applications."
  }'

sleep 2

curl -X POST "$BASE_URL/api/threads/$THREAD_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": "Comment configurer un CI/CD pipeline avec Docker ?"
  }'
```

### 3. Archiver le thread

```bash
curl -X PUT "$BASE_URL/api/threads/$THREAD_ID/archive" \
  -H "Authorization: Bearer $TOKEN"

echo "Thread archivé"
```

### 4. Consolider le thread

```bash
curl -X POST "$BASE_URL/api/memory/tend-garden" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"thread_id\": \"$THREAD_ID\"}"

echo "Consolidation lancée"
```

### 5. Interroger les concepts

```bash
# Rechercher "docker"
curl -s -X GET "$BASE_URL/api/memory/concepts/search?q=docker&limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.results[] | {concept: .concept_text, first_mentioned: .first_mentioned_at, last_mentioned: .last_mentioned_at, thread_ids: .thread_ids}'
```

### 6. ✅ Validation Attendue

**Résultat attendu** :

```json
{
  "concept": "Docker containerisation",
  "first_mentioned": "2025-10-11T10:30:15+00:00",  // ← Date du PREMIER message
  "last_mentioned": "2025-10-11T10:30:19+00:00",   // ← Date du DERNIER message
  "thread_ids": ["votre_thread_id"]
}
```

**❌ Comportement bugué (V2.9.0)** :
- `first_mentioned` et `last_mentioned` auraient la même date (celle de la consolidation)

**✅ Comportement corrigé (V2.10.0)** :
- `first_mentioned` = date du 1er message (~10:30:15)
- `last_mentioned` = date du 3ème message (~10:30:19)
- Écart de ~4 secondes entre les deux

---

## 🧪 Test Approfondi (via UI)

### Scénario Complet

1. **Créer une conversation** via l'interface UI
   - Parler de "Docker" et "containerisation"
   - Envoyer 5-6 messages sur plusieurs minutes

2. **Archiver la conversation**
   - Aller dans les threads
   - Archiver le thread

3. **Consolider via API ou attendre le gardener**
   ```bash
   curl -X POST "$BASE_URL/api/memory/tend-garden" \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"limit": 20}'
   ```

4. **Interroger un agent**
   - Dans une nouvelle conversation, demander : "Quand ai-je parlé de Docker ?"
   - **Réponse attendue** : L'agent doit donner la date et l'heure exactes du thread archivé

5. **Vérifier les métadonnées ChromaDB** (optionnel, pour debug)
   ```python
   from backend.features.memory.vector_service import VectorService

   vs = VectorService()
   collection = vs.get_or_create_collection("emergence_knowledge")

   # Rechercher concepts "docker"
   results = collection.query(
       query_texts=["docker"],
       n_results=5,
       where={"type": "concept"}
   )

   for meta in results['metadatas'][0]:
       print(f"Concept: {meta['concept_text']}")
       print(f"First: {meta['first_mentioned_at']}")
       print(f"Last: {meta['last_mentioned_at']}")
       print(f"Thread: {meta['thread_id']}")
       print("---")
   ```

---

## 🐞 Debugging

### Vérifier les logs du gardener

```bash
# Filtrer les logs de consolidation
grep "Consolidation thread" logs/app.log | tail -n 20

# Vérifier les logs de vectorisation
grep "concepts vectorisés" logs/app.log | tail -n 10
```

**Logs attendus** :

```
INFO [MemoryGardener] Consolidation thread OK.
INFO [MemoryGardener] 3 concepts vectorisés avec métadonnées enrichies.
```

### Inspecter la base de données

```bash
sqlite3 emergence.db

# Lister les threads archivés
SELECT id, title, archived, last_message_at FROM threads WHERE archived = 1 LIMIT 5;

# Lister les messages d'un thread
SELECT id, role, created_at, substr(content, 1, 50) FROM messages WHERE thread_id = 'votre_thread_id' ORDER BY created_at;
```

### Vérifier ChromaDB

```bash
# Compter les concepts vectorisés
python -c "
from backend.features.memory.vector_service import VectorService
vs = VectorService()
coll = vs.get_or_create_collection('emergence_knowledge')
print(f'Total concepts: {coll.count()}')
"
```

---

## 📊 Tests Automatisés

### Lancer les tests unitaires

```bash
# Test spécifique aux timestamps
pytest tests/memory/test_thread_consolidation_timestamps.py -v

# Tous les tests mémoire
pytest tests/memory/ -v

# Avec logs détaillés
pytest tests/memory/test_thread_consolidation_timestamps.py -v -s
```

**Tests attendus** :
- ✅ `test_thread_consolidation_preserves_real_timestamps` : PASSED
- ✅ `test_concept_query_returns_historical_dates` : PASSED
- ✅ `test_empty_thread_handles_gracefully` : PASSED

---

## ❓ FAQ

### Q: Comment reconsolider les threads déjà archivés en prod ?

```bash
curl -X POST https://emergence-app.ch/api/memory/consolidate-archived \
  -H "Authorization: Bearer $PROD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true, "limit": 10}'
```

**⚠️ Attention** : Cette opération peut être coûteuse en tokens LLM.

### Q: Les agents ne trouvent toujours pas les bonnes dates

**Vérifications** :
1. Vérifier que le thread a bien été consolidé :
   ```bash
   curl -s "$BASE_URL/api/memory/concepts/search?q=votre_sujet" \
     -H "Authorization: Bearer $TOKEN" | jq '.count'
   ```
   → Doit retourner > 0

2. Vérifier les métadonnées dans ChromaDB (voir section Debugging ci-dessus)

3. Vérifier que le gardener utilise bien la version V2.10.0 :
   ```bash
   grep "MemoryGardener V2.10.0" logs/app.log
   ```

### Q: Comment vérifier que les timestamps sont corrects ?

```bash
# 1. Récupérer les dates des messages du thread
sqlite3 emergence.db "SELECT created_at FROM messages WHERE thread_id = 'votre_thread_id' ORDER BY created_at"

# 2. Comparer avec les métadonnées ChromaDB
# (voir section "Vérifier les métadonnées ChromaDB" ci-dessus)

# Les dates doivent correspondre à ±1 seconde près
```

---

## ✅ Critères de Succès

Le fix est validé si :

1. ✅ **Timestamps corrects** : `first_mentioned_at` correspond à la date du **premier message** du thread
2. ✅ **Timestamps différents** : `first_mentioned_at` ≠ `last_mentioned_at` (si plusieurs messages espacés)
3. ✅ **Thread IDs présents** : `thread_ids` contient le bon `thread_id`
4. ✅ **Agents répondent** : L'agent peut dire "Tu as parlé de X le [date] à [heure]"
5. ✅ **Tests passent** : Tous les tests unitaires sont verts

---

## 📞 Support

En cas de problème :
1. Vérifier les logs : `logs/app.log`
2. Vérifier les tests : `pytest tests/memory/ -v`
3. Consulter la doc : [docs/fixes/MEMORY_FIX_TIMESTAMPS_ARCHIVED_THREADS.md](docs/fixes/MEMORY_FIX_TIMESTAMPS_ARCHIVED_THREADS.md)

---

**Bon test ! 🚀**
