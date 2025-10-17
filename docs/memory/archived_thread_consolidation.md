# Solution : Consolidation Automatique des Threads Archivés

## Problème Identifié

Lorsqu'un agent est interrogé sur les concepts ou sujets abordés "jusqu'à maintenant", il ne peut accéder qu'à la **mémoire de la session active courante**. Les threads archivés ne sont pas automatiquement consolidés dans la Long-Term Memory (LTM), ce qui crée un **gap mémoriel** :

- ❌ Threads archivés → concepts/préférences NON accessibles cross-session
- ❌ Mémoire limitée à la session/conversation active
- ❌ Perte de contexte historique lors du changement de session

### Cause Racine

1. **Consolidation manuelle uniquement** : L'endpoint `/api/memory/consolidate-archived` existe mais doit être appelé manuellement
2. **Pas de tracking** : Aucun suivi de quels threads ont été consolidés
3. **Architecture confuse** : Session vs Thread créent une redondance conceptuelle

## Solution Implémentée

### 🎯 Architecture de la Solution

```
┌─────────────────────────────────────────────────────────┐
│        NOUVEAU FLUX DE CONSOLIDATION AUTOMATIQUE       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. User archives thread                                │
│     └→ PATCH /api/threads/{id} (archived=true)         │
│                                                         │
│  2. Hook automatique déclenché                          │
│     └→ threads/router.py:193-213                        │
│     └→ Enqueue consolidation task                       │
│                                                         │
│  3. Memory Gardener consolide le thread                 │
│     └→ gardener._tend_single_thread()                   │
│     └→ Extrait concepts, préférences, faits            │
│     └→ Vectorise vers ChromaDB (LTM)                    │
│     └→ Marque threads.consolidated_at = NOW()           │
│                                                         │
│  4. Agent accède à la mémoire consolidée                │
│     └→ Recherche unifiée : STM + LTM + threads archivés│
│     └→ GET /api/memory/search/unified?q=docker          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 📝 Changements Implémentés

#### 1. **Migration Database : Tracking de Consolidation**

**Fichier** : `migrations/009_add_thread_consolidation_tracking.sql`

```sql
-- Add consolidated_at column to track when thread memory was consolidated
ALTER TABLE threads ADD COLUMN consolidated_at TEXT;

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_threads_consolidated_at
ON threads(consolidated_at);

CREATE INDEX IF NOT EXISTS idx_threads_archived_unconsolidated
ON threads(archived, consolidated_at)
WHERE archived = 1 AND consolidated_at IS NULL;
```

**Impact** :
- ✅ Permet de tracker quels threads sont consolidés
- ✅ Index optimisés pour requêtes de batch consolidation
- ✅ Évite de reconsolider inutilement

#### 2. **Memory Gardener : Marquage Post-Consolidation**

**Fichier** : `src/backend/features/memory/gardener.py:851-863`

```python
async def _tend_single_thread(...):
    # ... consolidation logic ...

    # Mark thread as consolidated in database
    if added_any:
        try:
            await self.db.execute(
                "UPDATE threads SET consolidated_at = ? WHERE id = ?",
                (_now_iso(), tid),
                commit=True
            )
            logger.info(f"[Gardener] Thread {tid} marked as consolidated")
        except Exception as e:
            logger.warning(f"[Gardener] Failed to mark thread {tid} as consolidated: {e}")
```

**Impact** :
- ✅ Chaque thread consolidé est marqué avec timestamp
- ✅ Évite les doublons de consolidation
- ✅ Permet audit et monitoring

#### 3. **Hook Automatique Existant**

**Fichier** : `src/backend/features/threads/router.py:192-213`

Le hook était **déjà implémenté** dans le router threads (Phase P0) :

```python
# Hook consolidation automatique lors archivage
if payload.archived and not was_archived:
    try:
        from backend.features.memory.task_queue import get_memory_queue

        queue = get_memory_queue()
        await queue.enqueue(
            task_type="consolidate_thread",
            payload={
                "thread_id": thread_id,
                "session_id": session.session_id,
                "user_id": session.user_id,
                "reason": "archiving"
            }
        )

        logger.info(f"[Thread Archiving] Consolidation enqueued for thread {thread_id}")

    except Exception as e:
        logger.warning(f"[Thread Archiving] Failed to enqueue consolidation: {e}")
```

**Impact** :
- ✅ **Nouveaux archivages** sont automatiquement consolidés
- ✅ Asynchrone via task queue (ne bloque pas l'UI)
- ✅ Résilience : échec de consolidation ne bloque pas l'archivage

#### 4. **CLI Script : Batch Consolidation**

**Fichier** : `src/backend/cli/consolidate_archived_threads.py`

Script CLI pour consolider les **threads déjà archivés** (migration rétroactive) :

```bash
# Consolider tous les threads archivés non encore consolidés
python -m backend.cli.consolidate_archived_threads

# Consolider pour un utilisateur spécifique
python -m backend.cli.consolidate_archived_threads --user-id user123 --verbose

# Dry run (voir ce qui serait fait sans faire)
python -m backend.cli.consolidate_archived_threads --dry-run --verbose

# Forcer reconsolidation (use with caution)
python -m backend.cli.consolidate_archived_threads --force --limit 10
```

**Fonctionnalités** :
- ✅ Détection automatique des threads non consolidés (`consolidated_at IS NULL`)
- ✅ Support user_id filter
- ✅ Dry-run mode
- ✅ Verbose logging avec statistiques
- ✅ Gestion d'erreurs robuste
- ✅ Résumé final avec métriques

**Options** :

| Option | Description |
|--------|-------------|
| `--user-id TEXT` | Consolider uniquement pour un utilisateur spécifique |
| `--limit INTEGER` | Nombre max de threads à traiter |
| `--force` | Reconsolider même si déjà consolidé |
| `--dry-run` | Afficher ce qui serait fait sans faire de changements |
| `--verbose, -v` | Afficher la progression détaillée |

## 🚀 Guide d'Utilisation

### Pour les Nouveaux Archivages

**Rien à faire !** La consolidation est automatique :

1. User archive un thread via l'UI
2. Backend enqueue automatiquement la consolidation
3. Memory Gardener consolide en arrière-plan
4. Thread marqué `consolidated_at = NOW()`

### Pour les Threads Déjà Archivés (Migration)

**Étape 1 : Appliquer la migration database**

```bash
# La migration sera appliquée automatiquement au prochain démarrage
# Ou manuellement :
python -m backend.core.database.schema
```

**Étape 2 : Exécuter le script de consolidation batch**

```bash
# Test en dry-run d'abord
python -m backend.cli.consolidate_archived_threads --dry-run --verbose

# Si OK, exécuter la consolidation réelle
python -m backend.cli.consolidate_archived_threads --verbose
```

**Sortie attendue** :

```
2025-10-17 14:30:00 - INFO - Initializing services...
2025-10-17 14:30:01 - INFO - Fetching archived threads...
2025-10-17 14:30:01 - INFO - Found 42 archived thread(s) to consolidate

2025-10-17 14:30:01 - INFO - Starting consolidation of 42 thread(s)...

[1/42] Thread: a1b2c3d4...
  Processing thread: a1b2c3d4... (messages: 87)
    ✓ Success: 12 concepts/items added to LTM

[2/42] Thread: e5f6g7h8...
  Processing thread: e5f6g7h8... (messages: 143)
    ✓ Success: 23 concepts/items added to LTM

...

============================================================
CONSOLIDATION SUMMARY
============================================================
Total threads processed:    42
Successfully consolidated:  39
Skipped (no new items):     2
Errors:                     1
Total concepts/items added: 487
Duration:                   23.45 seconds
============================================================

✓ All threads consolidated successfully!
```

### Pour les Agents : Accès à la Mémoire Consolidée

Les agents peuvent maintenant accéder à **toute la mémoire consolidée** via l'API unifiée :

**Endpoint** : `GET /api/memory/search/unified`

```http
GET /api/memory/search/unified?q=docker&limit=10&include_archived=true
```

**Réponse** :

```json
{
  "query": "docker",
  "stm_summaries": [
    {
      "session_id": "session_123",
      "summary": "Discussion sur containerization avec Docker...",
      "created_at": "2025-09-15T10:30:00Z",
      "concept_count": 5
    }
  ],
  "ltm_concepts": [
    {
      "concept": "Docker containerization",
      "first_mentioned": "2025-08-20T14:00:00Z",
      "last_mentioned": "2025-10-12T09:15:00Z",
      "mention_count": 8,
      "thread_ids": ["thread_1", "thread_5", "thread_12"]
    }
  ],
  "threads": [
    {
      "thread_id": "thread_12",
      "title": "Docker setup for production",
      "archived": 1,
      "message_count": 87
    }
  ],
  "messages": [
    {
      "message_id": "msg_456",
      "content": "Pour Docker, je préfère utiliser docker-compose...",
      "created_at": "2025-10-12T09:15:00Z",
      "thread_id": "thread_12"
    }
  ],
  "total_results": 42
}
```

**Impact pour l'Agent** :
- ✅ Accès à **tous les concepts** abordés historiquement
- ✅ Contexte temporel (first/last mentioned)
- ✅ Threads sources pour creuser si nécessaire
- ✅ Messages exacts pour précision

## 📊 Monitoring & Métriques

### Vérifier l'État de Consolidation

```sql
-- Nombre de threads archivés consolidés vs non consolidés
SELECT
  COUNT(*) FILTER (WHERE consolidated_at IS NOT NULL) AS consolidated,
  COUNT(*) FILTER (WHERE consolidated_at IS NULL) AS unconsolidated,
  COUNT(*) AS total
FROM threads
WHERE archived = 1;
```

### Métriques LTM par Thread

```sql
-- Concepts consolidés par thread
SELECT
  thread_id,
  COUNT(*) as concept_count
FROM monitoring
WHERE event_type = 'knowledge_concept'
  AND JSON_EXTRACT(event_details, '$.thread_id') IS NOT NULL
GROUP BY thread_id
ORDER BY concept_count DESC
LIMIT 10;
```

### Performance de Consolidation

```sql
-- Dernières consolidations
SELECT
  id,
  SUBSTR(id, 1, 8) || '...' as thread_id_short,
  message_count,
  archived_at,
  consolidated_at,
  ROUND((JULIANDAY(consolidated_at) - JULIANDAY(archived_at)) * 24, 2) as hours_to_consolidate
FROM threads
WHERE consolidated_at IS NOT NULL
ORDER BY consolidated_at DESC
LIMIT 20;
```

## 🔍 Troubleshooting

### Problème : Threads non consolidés automatiquement

**Symptôme** : Nouveaux threads archivés n'ont pas `consolidated_at`

**Solutions** :

1. Vérifier que la task queue fonctionne :
   ```python
   # Dans logs backend
   [Thread Archiving] Consolidation enqueued for thread abc123
   ```

2. Vérifier les logs du Memory Gardener :
   ```python
   [Gardener] Thread abc123 marked as consolidated
   ```

3. Forcer consolidation manuelle :
   ```bash
   python -m backend.cli.consolidate_archived_threads --user-id USER_ID --verbose
   ```

### Problème : Consolidation échoue avec erreur

**Symptôme** : `_tend_single_thread()` retourne `status: error`

**Solutions** :

1. Vérifier que ChromaDB est accessible
2. Vérifier que le thread a des messages :
   ```sql
   SELECT COUNT(*) FROM messages WHERE thread_id = 'abc123';
   ```

3. Vérifier les permissions user_id (isolation)

### Problème : Agent ne voit toujours pas l'historique

**Symptôme** : Agent répond "je ne vois que la session active"

**Solutions** :

1. Vérifier que la recherche unifiée est utilisée :
   ```http
   GET /api/memory/search/unified?q=concept&include_archived=true
   ```

2. Vérifier que les concepts sont bien en LTM :
   ```python
   # Via memory router
   GET /api/memory/concepts?limit=50
   ```

3. S'assurer que l'agent utilise l'API de mémoire proactive

## 📈 Prochaines Étapes (Optionnel)

### Amélioration 1 : Consolidation Incrémentale

Actuellement, `_tend_single_thread()` retraite tout le thread. On pourrait optimiser :

```python
# Consolider seulement les nouveaux messages depuis dernière consolidation
last_consolidated_message_id = metadata.get('last_consolidated_message_id')
new_messages = await queries.get_messages(
    db, thread_id, after=last_consolidated_message_id
)
```

### Amélioration 2 : Webhook Post-Consolidation

Notifier l'UI quand consolidation terminée :

```python
# Après consolidation
await connection_manager.send_personal_message({
    "type": "ws:memory_consolidated",
    "payload": {
        "thread_id": thread_id,
        "concepts_added": new_concepts
    }
}, session_id)
```

### Amélioration 3 : Scheduled Job

Ajouter un cron job pour consolidation périodique :

```python
# tasks/scheduled.py
@schedule.every(6).hours
async def consolidate_old_archived_threads():
    """Consolide threads archivés il y a > 24h mais pas encore consolidés"""
    pass
```

## 📚 Références

### Fichiers Modifiés/Créés

| Fichier | Type | Description |
|---------|------|-------------|
| `migrations/009_add_thread_consolidation_tracking.sql` | Migration | Ajoute `consolidated_at` à threads |
| `src/backend/features/memory/gardener.py` | Modification | Marque threads comme consolidés |
| `src/backend/cli/consolidate_archived_threads.py` | Nouveau | Script CLI batch consolidation |
| `src/backend/cli/__init__.py` | Nouveau | Module CLI |
| `docs/memory/archived_thread_consolidation.md` | Nouveau | Cette documentation |

### APIs Concernées

| Endpoint | Méthode | Usage |
|----------|---------|-------|
| `/api/threads/{id}` | PATCH | Archive thread → trigger auto-consolidation |
| `/api/memory/tend-garden` | POST | Consolidation manuelle (avec `thread_id`) |
| `/api/memory/consolidate-archived` | POST | Batch consolidation (existe déjà) |
| `/api/memory/search/unified` | GET | Recherche unifiée STM+LTM+archives |
| `/api/memory/concepts` | GET | Liste tous les concepts consolidés |

### Concepts Clés

- **STM (Short-Term Memory)** : `sessions` table, metadata JSON
- **LTM (Long-Term Memory)** : ChromaDB `emergence_knowledge` collection
- **Thread** : Conversation isolée (chat ou debate)
- **Consolidation** : Processus d'extraction concepts → vectorisation → LTM
- **Memory Gardener** : Service qui orchestre la consolidation et decay

## ✅ Checklist de Déploiement

- [ ] Appliquer migration 009
- [ ] Redémarrer backend (applique migration auto)
- [ ] Exécuter consolidation batch (dry-run first)
- [ ] Vérifier métriques consolidation
- [ ] Tester recherche unifiée avec agent
- [ ] Monitorer logs pour erreurs
- [ ] Documenter dans README principal

---

**Date de création** : 2025-10-17
**Auteur** : Claude Code Agent
**Version** : 1.0
**Status** : ✅ Ready for Production
