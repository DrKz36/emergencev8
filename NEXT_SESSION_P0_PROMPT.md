# Prompt Prochaine Session - Phase P0 : Consolidation Threads Archivés

**Date création** : 2025-10-10
**Priorité** : 🔴 **CRITIQUE** - Résout le problème principal utilisateur
**Durée estimée** : 90-120 minutes
**Prérequis** : Phase P1 complétée et déployée (commit `40ee8dc`)

---

## 🎯 Objectif Session

Implémenter la **consolidation automatique des threads archivés** dans la mémoire à long terme (LTM/ChromaDB), pour résoudre le **Gap #1** identifié dans [MEMORY_LTM_GAPS_ANALYSIS.md](docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md).

**Problème utilisateur** :
> "Quand je demande aux agents de quoi nous avons parlé, les conversations archivées ne sont jamais évoquées."

**Cause racine** :
Les threads archivés (`archived = 1`) sont systématiquement exclus de la consolidation mémoire, donc leurs concepts ne sont **jamais** ajoutés à ChromaDB.

---

## 📋 Contexte - Session Précédente (P1.2)

### Ce qui a été fait

✅ **Phase P1 complétée** : Persistance préférences dans ChromaDB
- Commit : `40ee8dc` - feat(P1.2): persistence préférences dans ChromaDB
- Tests : 38/38 memory tests passants (10 nouveaux tests ajoutés)
- Documentation : [MEMORY_LTM_GAPS_ANALYSIS.md](docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md)

### Fichiers créés/modifiés P1

```
✏️  src/backend/features/memory/analyzer.py (+90 lignes)
    └─> Méthode _save_preferences_to_vector_db()
    └─> Intégration workflow extraction

📄 docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md (nouveau, 450+ lignes)
    └─> Analyse complète 3 gaps (P1/P0/P2)

🧪 tests/backend/features/test_memory_preferences_persistence.py (nouveau, 520 lignes)
    └─> 10 tests persistance préférences

📋 SESSION_P1_2_RECAP.txt (nouveau)
    └─> Résumé complet session P1.2
```

---

## 🔴 Gap #1 - Threads Archivés Jamais Consolidés (Détails)

### Workflow actuel (PROBLÉMATIQUE)

```
1. User archive une conversation
   └─> UPDATE threads SET archived = 1, archival_reason = 'user_request'

2. Consolidation mémoire POST /api/memory/tend-garden
   └─> queries.get_threads(include_archived=False)  ← PAR DÉFAUT !
   └─> Récupère uniquement threads ACTIFS (archived = 0)

3. Extraction concepts
   └─> Analyse uniquement conversations actives
   └─> Threads archivés IGNORÉS

4. ChromaDB (LTM)
   └─> Ne contient JAMAIS les concepts des threads archivés
   └─> Recherche vectorielle incomplète
```

### Workflow attendu (À IMPLÉMENTER)

```
1. User archive une conversation
   └─> UPDATE threads SET archived = 1
   └─> 🆕 TRIGGER: Consolidation async du thread archivé

2. Consolidation automatique
   └─> MemoryTaskQueue.enqueue(type="consolidate_thread", thread_id=...)
   └─> gardener._tend_single_thread(thread_id, include_archived=True)

3. Extraction concepts
   └─> Récupère messages du thread archivé
   └─> Analyse sémantique (même workflow que threads actifs)

4. ChromaDB (LTM)
   └─> ✅ Concepts archivés sauvegardés
   └─> Recherche vectorielle complète
```

### Preuves dans le code

**1. Filtre par défaut exclut archivés** ([queries.py](src/backend/core/database/queries.py)) :
```python
async def get_threads(
    db: DatabaseManager,
    session_id: str,
    user_id: Optional[str] = None,
    include_archived: bool = False,  # ← PAR DÉFAUT FALSE
    archived_only: bool = False,
    ...
):
    if archived_only:
        clauses.append("archived = 1")
    elif not include_archived:
        clauses.append("archived = 0")  # ← THREADS ARCHIVÉS EXCLUS
```

**2. Consolidation batch ignore threads** ([gardener.py](src/backend/features/memory/gardener.py)) :
```python
async def tend_the_garden(self, consolidation_limit: int = 10, ...):
    # Mode batch : PROBLÈME - utilise sessions, pas threads
    sessions = await self._fetch_recent_sessions(limit=consolidation_limit, user_id=user_id)
    # ← Ne traite JAMAIS les threads directement
```

**3. Mode thread unique fonctionne** mais jamais appelé automatiquement :
```python
async def _tend_single_thread(self, thread_id: str, ...):
    # ✅ Cette méthode PEUT traiter archivés si thread_id fourni
    # ❌ Mais jamais appelée en batch ou lors archivage
```

---

## 🎯 Plan d'Implémentation P0

### Tâche 1 : Endpoint consolidation archivés en batch

**Fichier** : `src/backend/features/memory/router.py`

**Action** : Créer endpoint `POST /api/memory/consolidate-archived`

```python
@router.post("/consolidate-archived")
async def consolidate_archived_threads(
    request: Request,
    data: Dict[str, Any] = Body(default={})
) -> Dict[str, Any]:
    """
    Consolide tous les threads archivés non encore traités.
    Utile pour migration ou rattrapage batch.

    Body params:
    - user_id (optional): Limiter à un utilisateur
    - limit (optional): Nombre max threads (défaut 100)
    - force (optional): Forcer reconsolidation même si déjà fait

    Returns:
    - status: "success" | "error"
    - consolidated_count: Nombre threads consolidés
    - skipped_count: Nombre threads déjà consolidés
    - errors: Liste erreurs éventuelles
    """
    user_id = await shared_dependencies.get_user_id(request)
    gardener = _get_gardener_from_request(request)

    limit = data.get("limit", 100)
    force = data.get("force", False)

    # Récupérer tous threads archivés
    db = gardener.db
    threads = await queries.get_threads(
        db,
        session_id=None,  # Tous sessions
        user_id=user_id,
        archived_only=True,
        limit=limit
    )

    consolidated = 0
    skipped = 0
    errors = []

    for thread in threads:
        try:
            # Vérifier si déjà consolidé (concepts dans ChromaDB)
            if not force and await _thread_already_consolidated(thread["id"]):
                skipped += 1
                continue

            # Consolider thread
            result = await gardener._tend_single_thread(
                thread_id=thread["id"],
                session_id=thread["session_id"],
                user_id=thread["user_id"]
            )

            if result.get("new_concepts", 0) > 0:
                consolidated += 1

        except Exception as e:
            errors.append({
                "thread_id": thread["id"],
                "error": str(e)
            })

    return {
        "status": "success",
        "consolidated_count": consolidated,
        "skipped_count": skipped,
        "total_archived": len(threads),
        "errors": errors
    }
```

**Helper à créer** :
```python
async def _thread_already_consolidated(thread_id: str) -> bool:
    """
    Vérifie si thread déjà consolidé en cherchant dans ChromaDB.
    """
    # Implémenter requête ChromaDB avec filter thread_id
    pass
```

---

### Tâche 2 : Hook consolidation lors archivage

**Fichier** : `src/backend/features/threads/router.py`

**Action** : Ajouter trigger async lors `PATCH /api/threads/{id}` avec `archived=True`

**Localisation** : Fonction `update_thread()` (ligne ~164)

```python
@router.patch("/{thread_id}")
async def update_thread(
    thread_id: str,
    payload: ThreadUpdate,
    session: SessionContext = Depends(get_session_context),
    db: DatabaseManager = Depends(get_db),
):
    if not await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id):
        raise HTTPException(status_code=404, detail="Thread introuvable")

    # Récupérer état actuel AVANT mise à jour
    thread_before = await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id)
    was_archived = thread_before.get("archived", False)

    # Appliquer mise à jour
    await queries.update_thread(
        db,
        thread_id,
        session.session_id,
        user_id=session.user_id,
        title=payload.title,
        agent_id=payload.agent_id,
        archived=payload.archived,
        meta=payload.meta,
    )

    # 🆕 NOUVEAU : Si archivage demandé, déclencher consolidation async
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
            # Ne pas bloquer l'archivage si consolidation échoue
            logger.warning(f"[Thread Archiving] Failed to enqueue consolidation: {e}")

    thread = await queries.get_thread(db, thread_id, session.session_id, user_id=session.user_id)
    return {"thread": thread}
```

---

### Tâche 3 : Support task_type "consolidate_thread" dans MemoryTaskQueue

**Fichier** : `src/backend/features/memory/task_queue.py`

**Action** : Ajouter handler pour type "consolidate_thread"

**Localisation** : Méthode `_process_task()` (ligne ~120)

```python
async def _process_task(self, task: Dict[str, Any]) -> None:
    """Process une tâche de la queue."""
    task_type = task.get("type")
    payload = task.get("payload", {})

    try:
        if task_type == "analyze":
            # Existant - analyse session
            session_id = payload.get("session_id")
            force = payload.get("force", False)

            # ... code existant ...

        elif task_type == "consolidate_thread":
            # 🆕 NOUVEAU - consolidation thread archivé
            thread_id = payload.get("thread_id")
            session_id = payload.get("session_id")
            user_id = payload.get("user_id")
            reason = payload.get("reason", "manual")

            if not thread_id:
                logger.warning("[MemoryTaskQueue] consolidate_thread sans thread_id")
                return

            # Récupérer gardener
            from backend.features.memory.gardener import MemoryGardener

            gardener = MemoryGardener(
                db_manager=self.db_manager,
                vector_service=self.vector_service,
                memory_analyzer=self.analyzer
            )

            # Consolider thread
            logger.info(
                f"[MemoryTaskQueue] Consolidating archived thread {thread_id} "
                f"(reason: {reason})"
            )

            result = await gardener._tend_single_thread(
                thread_id=thread_id,
                session_id=session_id,
                user_id=user_id
            )

            new_concepts = result.get("new_concepts", 0)
            logger.info(
                f"[MemoryTaskQueue] Thread {thread_id} consolidated: "
                f"{new_concepts} new concepts"
            )

            # Callback si fourni
            callback = task.get("callback")
            if callback and callable(callback):
                await callback(result)

        else:
            logger.warning(f"[MemoryTaskQueue] Unknown task type: {task_type}")

    except Exception as e:
        logger.error(
            f"[MemoryTaskQueue] Task processing failed (type={task_type}): {e}",
            exc_info=True
        )
```

---

### Tâche 4 : Tests complets

**Fichier** : `tests/backend/features/test_memory_archived_consolidation.py` (nouveau)

**Tests à créer** (minimum 8) :

```python
"""
Tests consolidation threads archivés dans LTM.
Phase P0 - Résolution gap #1
"""

import pytest
from unittest.mock import Mock, AsyncMock

# Tests unitaires
def test_consolidate_archived_endpoint_success():
    """Test endpoint /consolidate-archived - succès."""
    pass

def test_consolidate_archived_endpoint_no_archived_threads():
    """Test endpoint - aucun thread archivé."""
    pass

def test_consolidate_archived_endpoint_partial_failure():
    """Test endpoint - échec partiel (continue avec les autres)."""
    pass

# Tests intégration hook archivage
def test_update_thread_triggers_consolidation():
    """Test PATCH /threads/{id} avec archived=True déclenche consolidation."""
    pass

def test_update_thread_no_trigger_if_already_archived():
    """Test pas de trigger si thread déjà archivé."""
    pass

# Tests task queue
def test_task_queue_consolidate_thread_type():
    """Test MemoryTaskQueue traite type 'consolidate_thread'."""
    pass

def test_task_queue_consolidate_thread_saves_concepts():
    """Test consolidation sauvegarde concepts dans ChromaDB."""
    pass

# Tests performance
def test_consolidate_archived_batch_100_threads():
    """Test consolidation batch 100 threads - performance."""
    pass
```

**Commandes test** :
```bash
# Tests unitaires nouveaux
python -m pytest tests/backend/features/test_memory_archived_consolidation.py -v

# Tests mémoire globaux (régression)
python -m pytest tests/backend/features/test_memory*.py -v

# Tests intégration threads (régression)
python -m pytest tests/backend/features/test_threads*.py -v
```

---

### Tâche 5 : Validation locale

**Scénario test manuel** :

```bash
# 1. Démarrer backend local
pwsh -File scripts/run-backend.ps1

# 2. Créer thread + messages
curl -X POST http://localhost:8000/api/threads/ \
  -H "x-dev-bypass: 1" -H "x-user-id: test_user" \
  -H "Content-Type: application/json" \
  -d '{"type": "chat", "title": "Test Thread Archive"}'

# Récupérer thread_id depuis réponse

# 3. Ajouter messages au thread
curl -X POST http://localhost:8000/api/threads/{thread_id}/messages \
  -H "x-dev-bypass: 1" -H "x-user-id: test_user" \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Je préfère Python pour l'\''IA"}'

# 4. Archiver thread (devrait déclencher consolidation)
curl -X PATCH http://localhost:8000/api/threads/{thread_id} \
  -H "x-dev-bypass: 1" -H "x-user-id: test_user" \
  -H "Content-Type: application/json" \
  -d '{"archived": true}'

# 5. Vérifier logs backend
# → Chercher "[Thread Archiving] Consolidation enqueued"
# → Chercher "[MemoryTaskQueue] Consolidating archived thread"
# → Chercher "[MemoryTaskQueue] Thread ... consolidated: X new concepts"

# 6. Vérifier ChromaDB contient concepts thread archivé
# (Utiliser script Python ou outil ChromaDB)
```

---

## 📊 Critères de Succès

### Tests

- [ ] 8+ nouveaux tests consolidation archivés (100% passants)
- [ ] 38+ tests mémoire globaux (0 régression)
- [ ] Tests threads (0 régression)

### Fonctionnel

- [ ] Endpoint `/consolidate-archived` retourne 200 OK
- [ ] PATCH thread avec `archived=true` déclenche consolidation async
- [ ] Logs backend montrent consolidation exécutée
- [ ] ChromaDB contient concepts threads archivés
- [ ] Recherche vectorielle retourne résultats threads archivés

### Performance

- [ ] Consolidation 1 thread archivé : < 5s
- [ ] Consolidation batch 100 threads : < 2 min (async)
- [ ] Pas de dégradation latence archivage thread (< 200ms)

---

## 🚨 Points d'Attention

### Risques

1. **Performance batch** : 100+ threads archivés peuvent surcharger queue
   → Limite à 100 par requête, pagination si besoin

2. **Race condition** : Consolidation pendant que thread encore actif
   → Vérifier état archived=1 avant consolidation

3. **Concepts dupliqués** : Si thread déjà consolidé puis re-consolidé
   → Implémenter `_thread_already_consolidated()` avec check ChromaDB

4. **Échec consolidation** : Ne pas bloquer archivage si consolidation échoue
   → Try/except avec logging, archivage réussit quand même

### Dépendances

- ✅ Phase P1 complétée (préférences persistées)
- ✅ MemoryTaskQueue opérationnel (depuis P1.1)
- ✅ `gardener._tend_single_thread()` existe et fonctionne
- ✅ ChromaDB collection `emergence_knowledge` configurée

---

## 📝 Checklist Implémentation

### Avant de commencer

- [ ] Lire [MEMORY_LTM_GAPS_ANALYSIS.md](docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md) section Gap #1
- [ ] Lire [SESSION_P1_2_RECAP.txt](SESSION_P1_2_RECAP.txt) pour contexte P1
- [ ] Lire ce prompt entièrement
- [ ] Vérifier `git status` propre (commit P1 : `40ee8dc`)
- [ ] Lancer tests mémoire existants : `pytest tests/backend/features/test_memory*.py -v`

### Pendant implémentation

- [ ] **Tâche 1** : Endpoint `/consolidate-archived` (router.py +60 lignes)
- [ ] **Tâche 2** : Hook archivage thread (threads/router.py +20 lignes)
- [ ] **Tâche 3** : Support task_type dans queue (task_queue.py +40 lignes)
- [ ] **Tâche 4** : Tests complets (nouveau fichier test_memory_archived_consolidation.py ~250 lignes)
- [ ] **Tâche 5** : Validation locale (scénario test manuel)

### Après implémentation

- [ ] Tous tests nouveaux passent (8+/8+)
- [ ] Tous tests mémoire passent (38+/38+, 0 régression)
- [ ] Validation locale réussie (logs + ChromaDB)
- [ ] Documentation mise à jour (voir section ci-dessous)

---

## 📚 Documentation à Mettre à Jour

### Après implémentation P0

1. **docs/passation.md** (nouvelle entrée) :
   ```markdown
   ## [2025-10-10 XX:XX] - Agent: Claude Code (Phase P0 - Consolidation Threads Archivés)

   ### Fichiers modifiés
   - src/backend/features/memory/router.py (+60 lignes)
   - src/backend/features/threads/router.py (+20 lignes)
   - src/backend/features/memory/task_queue.py (+40 lignes)
   - tests/backend/features/test_memory_archived_consolidation.py (nouveau, ~250 lignes)

   ### Contexte
   Résolution Gap #1 : Threads archivés jamais consolidés dans LTM

   ### Actions réalisées
   1. Endpoint POST /api/memory/consolidate-archived pour batch
   2. Hook archivage → consolidation async dans PATCH /threads/{id}
   3. Support task_type "consolidate_thread" dans MemoryTaskQueue
   4. Tests complets (8+ tests, 100% passants)
   5. Validation locale réussie

   ### Tests
   - ✅ X/X tests consolidation archivés
   - ✅ XX/XX tests mémoire globaux (0 régression)

   ### Résultats
   - ✅ Threads archivés maintenant consolidés automatiquement
   - ✅ Concepts archivés dans ChromaDB
   - ✅ Recherche vectorielle complète (actifs + archivés)

   ### Prochaines actions
   1. Déployer P1+P0 ensemble en production
   2. Déclencher consolidation batch threads archivés existants
   3. Valider métriques Prometheus production
   ```

2. **AGENT_SYNC.md** (section zones de travail) :
   - Mettre à jour section "Claude Code - Session actuelle"
   - Ajouter détails P0 implémentée
   - Statut : ✅ P1+P0 prêt pour déploiement

3. **SESSION_P0_RECAP.txt** (nouveau fichier) :
   - Copier structure de SESSION_P1_2_RECAP.txt
   - Adapter pour Phase P0
   - Inclure métriques tests, fichiers modifiés, prochaines étapes

---

## 🚀 Commandes Git (Après implémentation)

```bash
# Vérifier état
git status

# Ajouter fichiers
git add -A

# Commit avec message détaillé
git commit -m "feat(P0): consolidation threads archivés dans LTM - résolution gap critique #1

**Contexte**:
Threads archivés exclus de consolidation mémoire, causant 'amnésie' complète
des conversations passées (gap #1 identifié).

**Changements**:

1. Endpoint batch consolidation (router.py +60):
   - POST /api/memory/consolidate-archived
   - Traite tous threads archivés d'un user
   - Limite 100/requête, skip si déjà consolidé

2. Hook archivage automatique (threads/router.py +20):
   - PATCH /threads/{id} avec archived=true déclenche consolidation async
   - Enqueue task_type='consolidate_thread' dans MemoryTaskQueue
   - Graceful degradation si queue échoue

3. Support task queue (task_queue.py +40):
   - Handler 'consolidate_thread' type
   - Appelle gardener._tend_single_thread()
   - Logging détaillé + métriques

4. Tests complets (test_memory_archived_consolidation.py nouveau, ~250 lignes):
   - 8+ tests consolidation archivés
   - Tests endpoint, hook, task queue
   - Tests performance batch

**Impact**:
AVANT: Threads archivés → ❌ Jamais consolidés → Absents LTM
APRÈS: Threads archivés → ✅ Consolidation auto → Concepts dans ChromaDB

**Tests**: XX/XX nouveaux tests + XX/XX tests mémoire (0 régression)

**Ready**: P1+P0 prêt pour déploiement production

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push
git push origin main
```

---

## 🎯 Résultat Attendu Session

À la fin de cette session, tu devrais avoir :

✅ **Code** :
- Endpoint `/consolidate-archived` fonctionnel
- Hook archivage → consolidation automatique
- Support task queue "consolidate_thread"

✅ **Tests** :
- 8+ nouveaux tests consolidation archivés (100%)
- Tests mémoire globaux sans régression

✅ **Validation** :
- Test manuel local réussi
- Logs montrent consolidation exécutée
- ChromaDB contient concepts archivés

✅ **Documentation** :
- passation.md mis à jour
- AGENT_SYNC.md mis à jour
- SESSION_P0_RECAP.txt créé

✅ **Git** :
- Commit P0 avec message détaillé
- Push vers origin/main

✅ **Prêt déploiement** :
- P1+P0 validés localement
- Documentation déploiement prête
- Plan rollback documenté

---

## 📞 Contact & Validation

**Questions/Blocages** : Documenter dans SESSION_P0_RECAP.txt section "Blocages"

**Validation FG requise avant** :
- [ ] Déploiement production P1+P0
- [ ] Migration threads archivés existants (batch consolidation)

**Prochaine session après P0** :
→ Déploiement production P1+P0 + validation métriques
→ Ou Phase P2 (harmonisation Session/Thread) si décision architecture prise

---

## ✅ Pour Démarrer

```bash
# 1. Vérifier état git
git status
git log --oneline -5

# 2. Lire documentation
cat docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md | grep -A 50 "Gap #1"
cat SESSION_P1_2_RECAP.txt

# 3. Valider tests existants
python -m pytest tests/backend/features/test_memory*.py -v

# 4. Commencer implémentation
# → Tâche 1: Endpoint /consolidate-archived
```

---

**Bonne chance pour la Phase P0 ! 🚀**
