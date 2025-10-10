# Analyse des Gaps Critiques - Mémoire à Long Terme (LTM)

**Date** : 2025-10-10
**Agent** : Claude Code
**Phase** : P1.2 - Post-déploiement PreferenceExtractor
**Statut** : 🔴 **CRITIQUE - Action immédiate requise**

---

## 📋 Vue d'ensemble

Suite au déploiement de la Phase P1 (extraction préférences + déportation async), une analyse approfondie révèle **3 gaps critiques** empêchant la mémoire à long terme (LTM) de fonctionner correctement.

**Symptôme utilisateur** :
> "Quand je demande aux agents de quoi nous avons parlé jusqu'à maintenant, les conversations archivées ne sont jamais évoquées et les concepts associés ne ressortent pas."

**Cause racine** : Les conversations archivées et les préférences extraites ne sont jamais intégrées dans ChromaDB (base vectorielle LTM).

---

## 🔴 Gap #1 : Threads archivés JAMAIS consolidés dans LTM

### Description du problème

**Workflow actuel** :
```
1. Utilisateur archive une conversation
   └─> UPDATE threads SET archived = 1, archival_reason = 'user_request'

2. Consolidation mémoire (tend-garden)
   └─> queries.get_threads(include_archived=False)  ← PAR DÉFAUT !
   └─> Récupère uniquement threads actifs (archived = 0)

3. Extraction concepts
   └─> Analyse uniquement conversations actives
   └─> Threads archivés IGNORÉS

4. ChromaDB (LTM)
   └─> Ne contient JAMAIS les concepts des threads archivés
   └─> Recherche vectorielle incomplète
```

### Preuves dans le code

**1. Filtre par défaut exclut archivés** ([queries.py](../../src/backend/core/database/queries.py))
```python
async def get_threads(
    db: DatabaseManager,
    session_id: str,
    user_id: Optional[str] = None,
    type_: Optional[str] = None,
    include_archived: bool = False,  # ← PAR DÉFAUT FALSE
    archived_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    # ...
    if archived_only:
        clauses.append("archived = 1")
    elif not include_archived:
        clauses.append("archived = 0")  # ← THREADS ARCHIVÉS EXCLUS
```

**2. Consolidation batch ignore threads** ([gardener.py:tend_the_garden](../../src/backend/features/memory/gardener.py))
```python
async def tend_the_garden(
    self,
    consolidation_limit: int = 10,
    thread_id: Optional[str] = None,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    # Mode thread unique : OK, peut traiter archivés si thread_id fourni
    if thread_id:
        return await self._tend_single_thread(...)

    # Mode batch : PROBLÈME - utilise sessions, pas threads
    sessions = await self._fetch_recent_sessions(
        limit=consolidation_limit, user_id=user_id
    )
    # ← Ne traite JAMAIS les threads directement
    # ← Sessions archivées probablement aussi ignorées
```

### Impact utilisateur

| Scénario | Comportement actuel | Comportement attendu |
|----------|---------------------|----------------------|
| User archive conversation "Projet Python" | Thread archivé → Concepts JAMAIS consolidés | Thread archivé → Consolidation immédiate → Concepts dans LTM |
| User demande "De quoi avons-nous parlé sur Python ?" | ❌ Aucun résultat (concepts absents de ChromaDB) | ✅ Rappel concepts de la conversation archivée |
| User rouvre conversation archivée | ✅ Messages disponibles (SQLite) mais ❌ Aucun contexte LTM | ✅ Messages + contexte LTM enrichi |

### Métriques manquantes

- **Taux archivage** : Combien de threads archivés par utilisateur ?
- **Coverage LTM** : % threads consolidés vs total threads
- **Latence consolidation archivage** : Temps entre archivage et intégration LTM

---

## 🔴 Gap #2 : Préférences extraites mais JAMAIS persistées

### Description du problème

**Workflow actuel** :
```
1. Consolidation mémoire déclenchée
   └─> MemoryAnalyzer.analyze_session_async()

2. PreferenceExtractor appelé
   └─> Extraction réussie (filtrage lexical + LLM)
   └─> Préférences identifiées avec confidence > 0.6

3. Logging uniquement
   └─> logger.debug(f"Extracted {len(preferences)} preferences")
   └─> # TODO P1.2: Sauvegarder dans Firestore collection memory_preferences_{user_sub}
   └─> ❌ STOP ICI - Jamais sauvegardé

4. ChromaDB
   └─> Aucune préférence dans la collection emergence_knowledge
   └─> _fetch_active_preferences() retourne TOUJOURS vide
```

**Code problématique** ([analyzer.py:386](../../src/backend/features/memory/analyzer.py#L386)) :
```python
if preferences:
    logger.info(
        f"[PreferenceExtractor] Extracted {len(preferences)} preferences/intents "
        f"for session {session_id}"
    )
    # TODO P1.2: Sauvegarder dans Firestore collection memory_preferences_{user_sub}
    # Pour l'instant, juste logger
    for pref in preferences:
        logger.debug(
            f"  [{pref.type}] {pref.topic}: {pref.text[:60]}... "
            f"(confidence={pref.confidence:.2f})"
        )
    # ❌ PAS DE SAUVEGARDE ICI
else:
    logger.debug(f"[PreferenceExtractor] No preferences found in session {session_id}")
```

### Architecture attendue vs réelle

**Architecture attendue** :
```
PreferenceExtractor → ChromaDB (emergence_knowledge)
                      ├─ type: "preference"
                      ├─ user_id: "user_123"
                      ├─ confidence: 0.85
                      ├─ topic: "programming_languages"
                      └─ text: "Je préfère Python pour le scripting"

MemoryContextBuilder → _fetch_active_preferences()
                      └─> WHERE user_id=X AND type="preference" AND confidence >= 0.6
                      └─> Injection contexte RAG
```

**Architecture réelle** :
```
PreferenceExtractor → Logger.debug()  ❌ PERDU

MemoryContextBuilder → _fetch_active_preferences()
                      └─> WHERE user_id=X AND type="preference" AND confidence >= 0.6
                      └─> ❌ Toujours vide (aucune donnée dans ChromaDB)
```

### Preuve : Code de récupération existe mais inutile

[memory_ctx.py:112-138](../../src/backend/features/chat/memory_ctx.py#L112-L138) :
```python
def _fetch_active_preferences(self, collection, user_id: str) -> str:
    """Fetch active preferences with high confidence (>0.6) for immediate injection."""
    try:
        where = {
            "$and": [
                {"user_id": user_id},
                {"type": "preference"},
                {"confidence": {"$gte": 0.6}},
            ]
        }
        got = collection.get(where=where, include=["documents", "metadatas"])
        docs = got.get("documents", []) or []

        if not docs:
            return ""  # ← TOUJOURS ICI car aucune donnée

        # Ce code n'est JAMAIS exécuté
        prefs = []
        for doc in docs[:5]:
            if doc and doc.strip():
                prefs.append(f"- {doc.strip()}")

        return "\n".join(prefs) if prefs else ""
    except Exception as e:
        logger.debug(f"_fetch_active_preferences: {e}")
        return ""
```

### Impact utilisateur

| Scénario | Comportement actuel | Comportement attendu |
|----------|---------------------|----------------------|
| User dit "Je préfère Python à JavaScript" | ✅ Extrait (logs) ❌ Perdu | ✅ Extrait → Sauvegardé → Rappelé |
| User demande conseil langage | ❌ Agent propose JS (préférence ignorée) | ✅ Agent rappelle "Tu préfères Python" |
| User revient 2 jours après | ❌ Préférences oubliées | ✅ Préférences réinjectées automatiquement |

### Métriques Prometheus inutiles

Les 5 métriques P1 sont exposées mais **ne peuvent jamais augmenter** en production :
```python
memory_preferences_extracted_total  # ← Incrémenté lors extraction
memory_preferences_confidence       # ← Histogram scores
# ...mais aucune donnée persistée, donc pas d'impact réel
```

---

## 🟡 Gap #3 : Architecture hybride Session vs Thread incohérente

### Description du problème

Le système utilise **deux architectures de données** incompatibles :

**1. Architecture legacy (Sessions)** :
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    session_data TEXT,              -- ← JSON historique messages
    summary TEXT,                   -- ← Résumé analyse
    extracted_concepts TEXT,        -- ← Concepts extraits
    extracted_entities TEXT,        -- ← Entités extraites
    created_at TEXT,
    updated_at TEXT
);
```

**2. Architecture moderne (Threads v6)** :
```sql
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    type TEXT CHECK(type IN ('chat','debate')),
    title TEXT,
    archived INTEGER DEFAULT 0,     -- ← Flag archivage
    archival_reason TEXT,
    message_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    role TEXT,
    content TEXT,
    created_at TEXT,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);
```

### Incohérences constatées

| Opération | Architecture utilisée | Problème |
|-----------|----------------------|----------|
| **Consolidation batch** (`tend_the_garden` sans `thread_id`) | ❌ Sessions | Ignore tous les threads modernes |
| **Consolidation thread unique** (`tend_the_garden` avec `thread_id`) | ✅ Threads + Messages | Fonctionne mais jamais appelé en batch |
| **Stockage concepts** | ✅ ChromaDB (sessions.extracted_concepts legacy) | Pas de lien direct avec threads |
| **Récupération contexte** | ✅ ChromaDB (user_id filter) | Fonctionne mais base incomplète |

### Code problématique

**Consolidation batch utilise sessions** ([gardener.py](../../src/backend/features/memory/gardener.py)) :
```python
async def tend_the_garden(self, ...):
    # ...
    sessions = await self._fetch_recent_sessions(
        limit=consolidation_limit, user_id=user_id
    )
    # ← Récupère table SESSIONS, pas THREADS

    for s in sessions:
        history = self._extract_history(s.get("session_data"))
        # ← session_data = JSON legacy, pas messages table
```

**Consolidation thread unique utilise architecture moderne** :
```python
async def _tend_single_thread(self, thread_id: str, ...):
    msgs = await queries.get_messages(
        self.db, thread_id, session_id=sid, user_id=uid, limit=1000
    )
    # ← Utilise table MESSAGES moderne ✅

    history = []
    for m in msgs:
        history.append({"role": m.get("role"), "content": m.get("content")})
```

### Impact

- **Nouvelles conversations (threads)** : Consolidées uniquement si `thread_id` fourni explicitement
- **Anciennes sessions** : Consolidées en batch mais format legacy
- **Threads archivés** : Jamais consolidés (double peine : architecture moderne + filtre archived)

---

## 🎯 Solutions - Plan d'Action Priorisé

### **Phase 1 : P1 - Persistance préférences (Impact immédiat, faible risque)**

**Pourquoi commencer par P1 ?**
1. ✅ **Indépendant** des autres gaps (pas de dépendance)
2. ✅ **Impact immédiat** : Préférences utilisables dès prochaine consolidation
3. ✅ **Tests existants** : 8/8 tests PreferenceExtractor passent
4. ✅ **Code infrastructure ready** : `VectorService.add_documents()` existe
5. ✅ **Faible risque** : Ajout de données, pas de modification workflow

**Changements requis** :

1. **Modifier `analyzer.py:386-402`** pour sauvegarder préférences
   ```python
   # AVANT (analyzer.py:386)
   # TODO P1.2: Sauvegarder dans Firestore collection memory_preferences_{user_sub}
   for pref in preferences:
       logger.debug(f"  [{pref.type}] {pref.topic}: {pref.text[:60]}...")

   # APRÈS
   await self._save_preferences_to_vector_db(
       preferences=preferences,
       user_id=user_sub,
       thread_id=thread_id,
       session_id=session_id
   )
   ```

2. **Créer méthode `_save_preferences_to_vector_db()`**
   - Utiliser `VectorService.add_documents()`
   - Format métadonnées compatible `_fetch_active_preferences()`
   - Gestion erreurs gracieuse (fallback si ChromaDB down)

3. **Métadonnées ChromaDB** :
   ```python
   {
       "user_id": user_sub,
       "type": pref.type,  # "preference" | "intent" | "constraint"
       "topic": pref.topic,
       "confidence": pref.confidence,
       "created_at": datetime.now(timezone.utc).isoformat(),
       "thread_id": thread_id,
       "session_id": session_id,
       "source": "preference_extractor_v1.2"
   }
   ```

4. **Tests** :
   - Test sauvegarde après extraction
   - Test récupération via `_fetch_active_preferences()`
   - Test workflow end-to-end : extraction → sauvegarde → réinjection contexte

**Fichiers impactés** :
- ✏️ `src/backend/features/memory/analyzer.py` (+40 lignes)
- ✏️ `tests/backend/features/test_memory_preferences_persistence.py` (nouveau, ~150 lignes)

**Durée estimée** : 45-60 min

---

### **Phase 2 : P0 - Consolidation threads archivés (Impact majeur, risque modéré)**

**Pourquoi après P1 ?**
1. ⚠️ **Risque modéré** : Modification workflow consolidation existant
2. 📦 **Dépendances** : Requiert tests approfondis (charge, performance)
3. 🎯 **Impact majeur** : Résout le problème principal utilisateur

**Changements requis** :

1. **Créer endpoint dédié** `POST /api/memory/consolidate-archived`
   ```python
   @router.post("/consolidate-archived")
   async def consolidate_archived_threads(
       request: Request,
       data: Dict[str, Any] = Body(default={})
   ) -> Dict[str, Any]:
       """
       Consolide tous les threads archivés non encore traités.
       Utile pour migration ou rattrapage batch.
       """
       user_id = await get_user_id(request)

       # Récupérer tous threads archivés
       threads = await queries.get_threads(
           db, session_id=session_id, user_id=user_id,
           archived_only=True, limit=100
       )

       # Consolider chaque thread
       for thread in threads:
           await gardener._tend_single_thread(
               thread_id=thread["id"],
               session_id=thread["session_id"],
               user_id=thread["user_id"]
           )

       return {"status": "success", "consolidated_count": len(threads)}
   ```

2. **Ajouter hook lors archivage** dans `PATCH /api/threads/{id}`
   ```python
   @router.patch("/{thread_id}")
   async def update_thread(thread_id: str, payload: ThreadUpdate, ...):
       # ... update thread ...

       # Si archivage demandé, déclencher consolidation async
       if payload.archived and not thread.get("archived"):
           from backend.features.memory.task_queue import get_memory_queue
           queue = get_memory_queue()
           await queue.enqueue(
               task_type="consolidate_thread",
               payload={"thread_id": thread_id, "reason": "archiving"}
           )

       return {"thread": thread}
   ```

3. **Modifier `tend_the_garden()` mode batch** pour inclure threads
   ```python
   # Option 1 : Ajouter flag include_archived
   async def tend_the_garden(
       self,
       consolidation_limit: int = 10,
       include_archived: bool = False,  # ← NOUVEAU
       ...
   ):
       threads = await queries.get_threads(
           db, user_id=user_id,
           include_archived=include_archived,  # ← Passé au query
           limit=consolidation_limit
       )
       # Traiter threads directement au lieu de sessions

   # Option 2 : Mode séparé pour migration
   async def consolidate_all_archived_threads(self, user_id: str):
       """Migration one-shot : consolider tous archivés."""
       pass
   ```

4. **Tests** :
   - Test consolidation thread archivé
   - Test hook archivage → consolidation async
   - Test endpoint `/consolidate-archived`
   - Test performance (100+ threads archivés)

**Fichiers impactés** :
- ✏️ `src/backend/features/memory/router.py` (+60 lignes)
- ✏️ `src/backend/features/memory/gardener.py` (+80 lignes)
- ✏️ `src/backend/features/threads/router.py` (+15 lignes)
- ✏️ `src/backend/features/memory/task_queue.py` (+30 lignes)
- ✏️ `tests/backend/features/test_memory_archived_consolidation.py` (nouveau, ~200 lignes)

**Durée estimée** : 90-120 min

---

### **Phase 3 : P2 - Harmonisation Session/Thread (Refactoring, risque élevé)**

**Pourquoi en dernier ?**
1. 🚧 **Risque élevé** : Refactoring majeur workflow consolidation
2. 📋 **Décision stratégique** : Migrer vers threads ou maintenir hybride ?
3. 🔄 **Dépendances** : Requiert validation architecture complète

**Options stratégiques** :

**Option A : Migration complète vers Threads**
- Supprimer utilisation `sessions.session_data` (JSON legacy)
- Migrer `tend_the_garden()` pour utiliser uniquement `threads` + `messages`
- Avantages : Architecture cohérente, performance améliorée
- Risques : Breaking changes, migration données existantes

**Option B : Maintenir hybride avec sync explicite**
- Conserver sessions pour rétrocompatibilité
- Ajouter sync bidirectionnel `sessions.extracted_concepts` ↔ `threads`
- Avantages : Pas de breaking changes
- Risques : Complexité accrue, dette technique

**Recommandation** : **Reporter après P0/P1**, décision FG requise.

---

## 📊 Métriques de succès

### Métriques Phase 1 (P1 - Préférences)

| Métrique | Baseline (avant) | Target (après) | Outil mesure |
|----------|------------------|----------------|--------------|
| Préférences persistées | 0 | > 80% extraites | Prometheus `memory_preferences_extracted_total` |
| Préférences réinjectées contexte | 0% | > 60% confidence >= 0.6 | Logs `[MemoryContextBuilder] Injected X preferences` |
| Latence sauvegarde | N/A | < 200ms | Prometheus `memory_preferences_extraction_duration_seconds` |

### Métriques Phase 2 (P0 - Threads archivés)

| Métrique | Baseline (avant) | Target (après) | Outil mesure |
|----------|------------------|----------------|--------------|
| Threads archivés consolidés | 0% | 100% | SQL `SELECT COUNT(*) FROM threads WHERE archived=1` vs ChromaDB |
| Latence consolidation archivage | N/A | < 5s (async) | Logs `MemoryTaskQueue` |
| Concepts LTM par utilisateur | Variable | +30% (archivés inclus) | ChromaDB count by user_id |

---

## 🔧 Commandes validation

### Vérifier préférences dans ChromaDB

```python
# Après implémentation P1
from backend.features.memory.vector_service import VectorService

vs = VectorService()
collection = vs.get_or_create_collection("emergence_knowledge")

# Requête préférences user
results = collection.get(
    where={
        "$and": [
            {"user_id": "user_123"},
            {"type": "preference"}
        ]
    },
    include=["documents", "metadatas"]
)

print(f"Préférences trouvées : {len(results['documents'])}")
```

### Vérifier threads archivés non consolidés

```sql
-- Threads archivés
SELECT COUNT(*) as archived_threads
FROM threads
WHERE archived = 1;

-- Comparer avec ChromaDB (manual check)
-- → Si archived_threads > ChromaDB documents with thread_id in archived list
-- → Gap de consolidation
```

### Logs consolidation

```bash
# Production logs
gcloud logging read "
  resource.type=cloud_run_revision
  AND severity>=INFO
  AND textPayload=~'\\[PreferenceExtractor\\]|MemoryTaskQueue|tend_single_thread'
" --limit 50 --format json

# Chercher :
# - "[PreferenceExtractor] Extracted X preferences" ← Extraction OK
# - "Saved X preferences to ChromaDB" ← Persistance OK (après P1)
# - "Consolidating archived thread" ← Archivés OK (après P0)
```

---

## 📚 Références

### Code source

- [analyzer.py](../../src/backend/features/memory/analyzer.py) - MemoryAnalyzer (ligne 386 : TODO préférences)
- [gardener.py](../../src/backend/features/memory/gardener.py) - Consolidation mémoire
- [memory_ctx.py](../../src/backend/features/chat/memory_ctx.py) - Récupération contexte LTM
- [preference_extractor.py](../../src/backend/features/memory/preference_extractor.py) - Extraction préférences
- [queries.py](../../src/backend/core/database/queries.py) - Requêtes threads/messages
- [router.py](../../src/backend/features/memory/router.py) - API endpoints mémoire

### Documentation

- [10-Memoire.md](10-Memoire.md) - Architecture mémoire (à créer/mettre à jour)
- [AGENT_SYNC.md](../../AGENT_SYNC.md) - État session P1 (ligne 199 : hotfix P1.1)
- [passation.md](../passation.md) - Logs sessions (3 dernières entrées)

### Tests

- [test_memory_enhancements.py](../../tests/backend/features/test_memory_enhancements.py) - Tests préférences existants
- Tests à créer : `test_memory_preferences_persistence.py`, `test_memory_archived_consolidation.py`

---

## ✅ Checklist validation

**Avant implémentation** :
- [x] Gaps identifiés et documentés
- [x] Priorités établies (P1 → P0 → P2)
- [x] Plan d'action détaillé
- [ ] Validation FG des priorités
- [ ] Création branche `fix/ltm-gaps-p1-p0`

**Phase 1 (P1 - Préférences)** :
- [ ] Méthode `_save_preferences_to_vector_db()` implémentée
- [ ] Tests unitaires persistance (3+ tests)
- [ ] Tests intégration end-to-end
- [ ] Validation locale (backend + ChromaDB)
- [ ] Métriques Prometheus vérifiées
- [ ] Commit + push branche

**Phase 2 (P0 - Threads archivés)** :
- [ ] Endpoint `/consolidate-archived` créé
- [ ] Hook archivage → consolidation async
- [ ] Tests consolidation archivés (5+ tests)
- [ ] Tests performance (100+ threads)
- [ ] Validation locale migration archivés
- [ ] Commit + push branche

**Déploiement** :
- [ ] Merge branche → main
- [ ] Build image Docker
- [ ] Deploy Cloud Run (canary 10% → 100%)
- [ ] Vérification logs production
- [ ] Validation métriques Prometheus
- [ ] Documentation passation.md mise à jour

---

**Prochaine action** : Attendre validation FG puis commencer implémentation P1 (persistance préférences).
