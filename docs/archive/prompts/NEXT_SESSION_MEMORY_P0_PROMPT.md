# Prompt Session Prochaine Instance - Implémentation Mémoire P0

**Date création** : 2025-10-10 17:00 UTC
**Agent cible** : Claude Code / Codex
**Priorité** : 🔴 **CRITIQUE** - Gaps bloquants mémoire LTM
**Durée estimée** : 4-6h (session complète)

---

## 🎯 Objectif de la session

Résoudre les **3 gaps critiques** empêchant la mémoire à long terme (LTM) de fonctionner correctement, identifiés dans [docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md](docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md).

**Symptôme utilisateur** :
> "Quand je demande aux agents de quoi nous avons parlé jusqu'à maintenant, les conversations archivées ne sont jamais évoquées et les concepts associés ne ressortent pas."

**Impact business** : La mémoire P1 (extraction préférences) est déployée mais **NON UTILISABLE** car les threads archivés ne sont jamais consolidés dans ChromaDB.

---

## 📚 Lecture OBLIGATOIRE avant de commencer

**Ordre de lecture** (⏱️ 15-20 minutes) :

1. **[AGENT_SYNC.md](AGENT_SYNC.md)** (sections clés)
   - État actuel du dépôt (branche, commits récents, déploiements)
   - Zones de travail en cours (sessions Claude Code + Codex récentes)
   - Checklist de travail obligatoire

2. **[docs/passation.md](docs/passation.md)** (3 dernières entrées)
   - [2025-10-10 16:45] Optimisations Performance Frontend
   - [2025-10-10 14:30] Hotfix P1.3 - user_sub Context
   - [2025-10-10 03:20] Déploiement P1+P0 production

3. **[docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md](docs/architecture/MEMORY_LTM_GAPS_ANALYSIS.md)** ⭐
   - **DOCUMENT CLÉ** : Analyse détaillée des 3 gaps critiques
   - Preuves code, impact utilisateur, métriques manquantes
   - Solutions proposées pour chaque gap

4. **[docs/memory-roadmap.md](docs/memory-roadmap.md)**
   - Vue d'ensemble architecture mémoire (STM, LTM, vitalité)
   - État Phase P0 (persistance cross-device) ✅ COMPLÉTÉ
   - État Phase P1 (déportation async + préférences) ✅ COMPLÉTÉ
   - Phase P2 à venir (réactivité proactive)

5. **`git status` + `git log --oneline -10`**
   - Vérifier état working tree
   - Derniers commits (c550fac perf(frontend), 2523713 fix(P1.3), etc.)

---

## 🔴 Gap #1 : Threads archivés JAMAIS consolidés dans LTM

### Problème

**Workflow actuel** :
```
1. User archive conversation
   └─> UPDATE threads SET archived = 1
2. Consolidation mémoire (tend-garden)
   └─> queries.get_threads(include_archived=False)  ← PAR DÉFAUT !
   └─> Récupère uniquement threads actifs
3. Extraction concepts
   └─> Analyse uniquement conversations actives
   └─> Threads archivés IGNORÉS
4. ChromaDB (LTM)
   └─> Ne contient JAMAIS les concepts des threads archivés
```

### Solution à implémenter

#### 1. Nouvel endpoint `/api/memory/consolidate-archived` (PRIORITÉ 1)

**Fichier** : `src/backend/features/memory/router.py`

```python
@router.post("/consolidate-archived")
async def consolidate_archived_threads(
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Header(None, alias="x-user-id"),
    batch_size: int = Query(10, ge=1, le=50),
    force: bool = Query(False),
    gardener: MemoryGardener = Depends(get_memory_gardener),
) -> Dict[str, Any]:
    """
    Consolide tous les threads archivés dans ChromaDB.

    - batch_size : nombre de threads traités par batch (défaut 10)
    - force : si True, re-consolide même si déjà fait (défaut False)
    - Retourne : {total_archived, consolidated, skipped, errors, duration_ms}
    """
    start_time = time.time()

    # Récupérer tous threads archivés non consolidés
    threads = await queries.get_threads(
        db=gardener.db,
        session_id=None,  # Tous utilisateurs ou filtrer par user_id
        user_id=user_id,
        archived_only=True,  # Nouveau paramètre à ajouter dans queries.py
        limit=batch_size
    )

    total_archived = len(threads)
    consolidated = 0
    skipped = 0
    errors = []

    for thread in threads:
        try:
            # Vérifier si déjà consolidé (metadata archived_consolidated_at)
            if not force and thread.get("metadata", {}).get("archived_consolidated_at"):
                skipped += 1
                continue

            # Consolider via tend_single_thread
            result = await gardener._tend_single_thread(
                thread_id=thread["id"],
                user_id=thread.get("user_id"),
                session_id=thread.get("session_id")
            )

            # Marquer comme consolidé dans metadata
            if result.get("status") == "completed":
                await queries.update_thread_metadata(
                    db=gardener.db,
                    thread_id=thread["id"],
                    metadata={
                        **thread.get("metadata", {}),
                        "archived_consolidated_at": datetime.now(UTC).isoformat()
                    }
                )
                consolidated += 1
            else:
                errors.append({
                    "thread_id": thread["id"],
                    "error": result.get("error", "Unknown error")
                })
        except Exception as e:
            logger.error(f"Error consolidating archived thread {thread['id']}: {e}")
            errors.append({
                "thread_id": thread["id"],
                "error": str(e)
            })

    duration_ms = int((time.time() - start_time) * 1000)

    # Métriques Prometheus
    MEMORY_ARCHIVED_CONSOLIDATED.inc(consolidated)

    return {
        "status": "completed",
        "total_archived": total_archived,
        "consolidated": consolidated,
        "skipped": skipped,
        "errors": errors,
        "duration_ms": duration_ms
    }
```

#### 2. Modifier `queries.get_threads()` (PRIORITÉ 1)

**Fichier** : `src/backend/core/database/queries.py`

Ajouter paramètre `archived_only`:

```python
async def get_threads(
    db: DatabaseManager,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    type_: Optional[str] = None,
    include_archived: bool = False,
    archived_only: bool = False,  # ← NOUVEAU PARAMÈTRE
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Récupère les threads selon filtres.

    - archived_only : si True, ne retourne QUE les threads archivés (archived = 1)
    - include_archived : si True (et archived_only False), inclut archivés et actifs
    - Par défaut : uniquement threads actifs (archived = 0)
    """
    clauses = []
    params = []

    # ... autres filtres (session_id, user_id, type_) ...

    # Filtre archivage
    if archived_only:
        clauses.append("archived = 1")
    elif not include_archived:
        clauses.append("archived = 0")

    # ... reste de la fonction ...
```

#### 3. Endpoint trigger auto après archivage (PRIORITÉ 2)

**Fichier** : `src/backend/features/threads/router.py`

Dans l'endpoint `PUT /api/threads/{thread_id}` (archivage) :

```python
@router.put("/{thread_id}")
async def update_thread(
    thread_id: str,
    update: ThreadUpdate,
    background_tasks: BackgroundTasks,
    db: DatabaseManager = Depends(get_db),
    gardener: MemoryGardener = Depends(get_memory_gardener),
    user_id: str = Depends(get_current_user_id),
):
    # ... validation et update thread ...

    # Si archivage détecté → trigger consolidation immédiate
    if update.archived and not existing_thread.get("archived"):
        logger.info(f"Thread {thread_id} archived, scheduling consolidation")

        # Background task asynchrone (ne bloque pas la réponse)
        background_tasks.add_task(
            gardener._tend_single_thread,
            thread_id=thread_id,
            user_id=user_id,
            session_id=existing_thread.get("session_id")
        )

        # Métrique Prometheus
        MEMORY_ARCHIVED_AUTO_TRIGGERED.inc()

    return updated_thread
```

#### 4. Tests unitaires (PRIORITÉ 1)

**Fichier** : `tests/backend/features/test_memory_archived_consolidation.py` (nouveau)

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_consolidate_archived_threads_success():
    """Test consolidation batch threads archivés."""
    # Setup mock threads archivés
    mock_threads = [
        {"id": "thread1", "archived": 1, "metadata": {}},
        {"id": "thread2", "archived": 1, "metadata": {}},
    ]

    with patch("src.backend.core.database.queries.get_threads", return_value=mock_threads):
        with patch.object(gardener, "_tend_single_thread", return_value={"status": "completed"}):
            result = await consolidate_archived_threads(
                background_tasks=BackgroundTasks(),
                batch_size=10,
                force=False,
                gardener=gardener
            )

    assert result["status"] == "completed"
    assert result["consolidated"] == 2
    assert result["skipped"] == 0
    assert len(result["errors"]) == 0

@pytest.mark.asyncio
async def test_consolidate_archived_threads_skip_already_done():
    """Test skip threads déjà consolidés."""
    mock_threads = [
        {"id": "thread1", "archived": 1, "metadata": {"archived_consolidated_at": "2025-10-10T12:00:00Z"}},
    ]

    with patch("src.backend.core.database.queries.get_threads", return_value=mock_threads):
        result = await consolidate_archived_threads(
            background_tasks=BackgroundTasks(),
            batch_size=10,
            force=False,
            gardener=gardener
        )

    assert result["consolidated"] == 0
    assert result["skipped"] == 1

@pytest.mark.asyncio
async def test_auto_trigger_on_archive():
    """Test trigger automatique lors archivage thread."""
    # ... test que background task est bien schedulée ...
```

#### 5. Métriques Prometheus (PRIORITÉ 2)

**Fichier** : `src/backend/features/memory/gardener.py`

```python
from prometheus_client import Counter

MEMORY_ARCHIVED_CONSOLIDATED = Counter(
    "memory_archived_consolidated_total",
    "Nombre total de threads archivés consolidés dans LTM"
)

MEMORY_ARCHIVED_AUTO_TRIGGERED = Counter(
    "memory_archived_auto_triggered_total",
    "Nombre de consolidations auto-déclenchées lors archivage"
)

MEMORY_ARCHIVED_CONSOLIDATION_ERRORS = Counter(
    "memory_archived_consolidation_errors_total",
    "Erreurs lors consolidation threads archivés",
    labelnames=["error_type"]
)
```

---

## 🟡 Gap #2 : Préférences extraites JAMAIS sauvées dans ChromaDB

### Problème

**Workflow actuel** :
```
1. PreferenceExtractor.extract()
   └─> Extraction préférences depuis messages ✅
   └─> Retourne liste PreferenceRecord ✅

2. MemoryAnalyzer.analyze_session()
   └─> Appelle preference_extractor.extract() ✅
   └─> Stocke résultats dans session.metadata["preferences"] ✅
   └─> NE SAUVEGARDE PAS dans ChromaDB ❌

3. ChromaDB collection 'memory_preferences'
   └─> Reste VIDE (0 embeddings)
```

### Solution à implémenter

#### 1. Méthode `save_preferences_to_vector_db()` (PRIORITÉ 1)

**Fichier** : `src/backend/features/memory/analyzer.py`

Ajouter après `analyze_session()` :

```python
async def save_preferences_to_vector_db(
    self,
    preferences: List[Dict[str, Any]],
    user_id: str,
    thread_id: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sauvegarde préférences extraites dans ChromaDB.

    Args:
        preferences : liste préférences depuis PreferenceExtractor
        user_id : identifiant utilisateur
        thread_id : identifiant thread
        session_id : identifiant session (optionnel)

    Returns:
        {saved: int, skipped: int, errors: List[str]}
    """
    if not preferences:
        logger.info("No preferences to save")
        return {"saved": 0, "skipped": 0, "errors": []}

    if not self.vector_service:
        logger.warning("VectorService not available, skipping preference save")
        return {"saved": 0, "skipped": len(preferences), "errors": ["VectorService unavailable"]}

    saved = 0
    skipped = 0
    errors = []

    for pref in preferences:
        try:
            # Générer embedding du texte préférence
            text = pref.get("topic", "") + " " + pref.get("action", "")
            embedding = await self._generate_embedding(text)

            if not embedding:
                skipped += 1
                continue

            # ID unique : {user_id}_{topic}_{type}
            pref_id = f"{user_id}_{pref['topic']}_{pref['type']}"

            # Metadata complète
            metadata = {
                "user_id": user_id,
                "thread_id": thread_id,
                "session_id": session_id or "unknown",
                "type": pref["type"],  # preference | intent | constraint
                "topic": pref["topic"],
                "action": pref.get("action", ""),
                "timeframe": pref.get("timeframe", "ongoing"),
                "sentiment": pref.get("sentiment", "neutral"),
                "confidence": pref.get("confidence", 0.5),
                "source_message_id": pref.get("source_message_id", ""),
                "captured_at": datetime.now(UTC).isoformat(),
                "entities": json.dumps(pref.get("entities", [])),
            }

            # Sauvegarder dans collection 'memory_preferences'
            await self.vector_service.add(
                collection_name="memory_preferences",
                ids=[pref_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )

            saved += 1
            logger.info(f"Saved preference {pref_id} to ChromaDB")

            # Métrique Prometheus
            MEMORY_PREFERENCES_SAVED.labels(type=pref["type"]).inc()

        except Exception as e:
            logger.error(f"Error saving preference to ChromaDB: {e}")
            errors.append(str(e))
            MEMORY_PREFERENCES_SAVE_ERRORS.inc()

    return {
        "saved": saved,
        "skipped": skipped,
        "errors": errors
    }
```

#### 2. Appeler `save_preferences_to_vector_db()` dans `analyze_session()` (PRIORITÉ 1)

**Fichier** : `src/backend/features/memory/analyzer.py`

Dans la méthode `analyze_session()`, après extraction préférences :

```python
async def analyze_session(
    self,
    session: Session,
    user_sub: Optional[str] = None,
    user_id: Optional[str] = None,
    persist: bool = False,
) -> Dict[str, Any]:
    # ... code existant (extraction concepts, préférences, etc.) ...

    # Nouvelle section : Sauvegarde préférences dans ChromaDB
    if persist and self.preference_extractor and preferences:
        logger.info(f"Saving {len(preferences)} preferences to ChromaDB")

        pref_save_result = await self.save_preferences_to_vector_db(
            preferences=preferences,
            user_id=user_identifier,  # user_sub or user_id
            thread_id=session.thread_id or "unknown",
            session_id=session.session_id
        )

        result["preferences_saved"] = pref_save_result["saved"]
        result["preferences_skipped"] = pref_save_result["skipped"]
        result["preferences_errors"] = pref_save_result["errors"]

        logger.info(
            f"Preferences saved: {pref_save_result['saved']}, "
            f"skipped: {pref_save_result['skipped']}, "
            f"errors: {len(pref_save_result['errors'])}"
        )

    return result
```

#### 3. Méthode helper `_generate_embedding()` (PRIORITÉ 1)

**Fichier** : `src/backend/features/memory/analyzer.py`

```python
async def _generate_embedding(self, text: str) -> Optional[List[float]]:
    """Génère embedding pour texte via ChatService."""
    if not self.chat_service:
        logger.warning("ChatService not available for embeddings")
        return None

    try:
        # Utiliser text-embedding-3-large (ou fallback)
        response = await self.chat_service.generate_embedding(
            text=text,
            model="text-embedding-3-large"
        )
        return response.get("embedding")
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None
```

#### 4. Tests unitaires (PRIORITÉ 1)

**Fichier** : `tests/backend/features/test_preference_persistence.py` (nouveau)

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_save_preferences_to_vector_db_success():
    """Test sauvegarde préférences dans ChromaDB."""
    preferences = [
        {
            "type": "preference",
            "topic": "python",
            "action": "préférer",
            "confidence": 0.85,
            "source_message_id": "msg123"
        }
    ]

    with patch.object(analyzer, "_generate_embedding", return_value=[0.1] * 1536):
        with patch.object(analyzer.vector_service, "add", return_value=None):
            result = await analyzer.save_preferences_to_vector_db(
                preferences=preferences,
                user_id="user123",
                thread_id="thread456",
                session_id="session789"
            )

    assert result["saved"] == 1
    assert result["skipped"] == 0
    assert len(result["errors"]) == 0

@pytest.mark.asyncio
async def test_save_preferences_vector_service_unavailable():
    """Test graceful degradation si VectorService indisponible."""
    analyzer.vector_service = None

    result = await analyzer.save_preferences_to_vector_db(
        preferences=[{"type": "preference", "topic": "test"}],
        user_id="user123",
        thread_id="thread456"
    )

    assert result["saved"] == 0
    assert result["skipped"] == 1
    assert "VectorService unavailable" in result["errors"]
```

#### 5. Métriques Prometheus (PRIORITÉ 2)

**Fichier** : `src/backend/features/memory/analyzer.py`

```python
MEMORY_PREFERENCES_SAVED = Counter(
    "memory_preferences_saved_total",
    "Nombre de préférences sauvegardées dans ChromaDB",
    labelnames=["type"]  # preference | intent | constraint
)

MEMORY_PREFERENCES_SAVE_ERRORS = Counter(
    "memory_preferences_save_errors_total",
    "Erreurs lors sauvegarde préférences dans ChromaDB"
)
```

---

## 🟢 Gap #3 : Aucune recherche préférences lors rappel LTM

### Problème

**Workflow actuel** :
```
1. Agent génère réponse
   └─> context_builder.build_context()
   └─> Recherche dans collection 'emergence_knowledge' (concepts) ✅
   └─> NE recherche PAS dans 'memory_preferences' ❌

2. Context final envoyé au LLM
   └─> Contient concepts généraux ✅
   └─> NE contient PAS préférences utilisateur ❌
```

### Solution à implémenter

#### 1. Méthode `search_preferences()` (PRIORITÉ 1)

**Fichier** : `src/backend/features/memory/vector_service.py`

```python
async def search_preferences(
    self,
    query: str,
    user_id: str,
    limit: int = 5,
    min_confidence: float = 0.6
) -> List[Dict[str, Any]]:
    """
    Recherche préférences utilisateur dans ChromaDB.

    Args:
        query : texte requête (embedded)
        user_id : filtre par utilisateur
        limit : nombre max résultats
        min_confidence : seuil confidence minimum

    Returns:
        Liste préférences {type, topic, action, confidence, ...}
    """
    try:
        # Générer embedding requête
        query_embedding = await self._generate_embedding(query)

        if not query_embedding:
            logger.warning("Could not generate embedding for preference search")
            return []

        # Recherche dans collection 'memory_preferences'
        results = await self.collection_preferences.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where={"user_id": user_id}  # Filtre par utilisateur
        )

        # Parser résultats
        preferences = []
        if results and results.get("metadatas"):
            for i, metadata in enumerate(results["metadatas"][0]):
                confidence = metadata.get("confidence", 0.5)

                # Filtre par confidence minimum
                if confidence >= min_confidence:
                    preferences.append({
                        "type": metadata.get("type"),
                        "topic": metadata.get("topic"),
                        "action": metadata.get("action"),
                        "confidence": confidence,
                        "sentiment": metadata.get("sentiment"),
                        "captured_at": metadata.get("captured_at"),
                        "distance": results["distances"][0][i] if results.get("distances") else 0.0
                    })

        logger.info(f"Found {len(preferences)} preferences for user {user_id}")
        return preferences

    except Exception as e:
        logger.error(f"Error searching preferences: {e}")
        return []
```

#### 2. Intégrer dans `ContextBuilder` (PRIORITÉ 1)

**Fichier** : `src/backend/features/chat/context_builder.py`

Dans la méthode `build_context()` :

```python
async def build_context(
    self,
    user_message: str,
    session: Session,
    user_id: Optional[str] = None,
    include_preferences: bool = True,  # ← NOUVEAU PARAMÈTRE
) -> str:
    """
    Construit contexte complet pour agent.

    - STM : résumé conversation courante
    - LTM concepts : recherche vectorielle concepts généraux
    - LTM préférences : recherche préférences utilisateur (NOUVEAU)
    """
    context_parts = []

    # 1. STM (court terme)
    stm_summary = self._build_stm_summary(session)
    if stm_summary:
        context_parts.append(f"## Contexte court terme\n{stm_summary}")

    # 2. LTM Concepts (concepts généraux)
    concepts = await self.vector_service.search_concepts(
        query=user_message,
        limit=5
    )
    if concepts:
        concepts_text = "\n".join([f"- {c['text']}" for c in concepts])
        context_parts.append(f"## Concepts pertinents\n{concepts_text}")

    # 3. LTM Préférences (NOUVEAU)
    if include_preferences and user_id:
        preferences = await self.vector_service.search_preferences(
            query=user_message,
            user_id=user_id,
            limit=5,
            min_confidence=0.6
        )

        if preferences:
            prefs_text = "\n".join([
                f"- {p['type'].upper()}: {p['topic']} ({p['action']}) "
                f"[confiance: {p['confidence']:.2f}]"
                for p in preferences
            ])
            context_parts.append(f"## Préférences utilisateur\n{prefs_text}")

    return "\n\n".join(context_parts)
```

#### 3. Tests unitaires (PRIORITÉ 1)

**Fichier** : `tests/backend/features/test_preference_retrieval.py` (nouveau)

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_search_preferences_success():
    """Test recherche préférences ChromaDB."""
    mock_results = {
        "metadatas": [[
            {
                "type": "preference",
                "topic": "python",
                "action": "préférer",
                "confidence": 0.85,
                "sentiment": "positive",
                "captured_at": "2025-10-10T12:00:00Z"
            }
        ]],
        "distances": [[0.15]]
    }

    with patch.object(vector_service.collection_preferences, "query", return_value=mock_results):
        preferences = await vector_service.search_preferences(
            query="python development",
            user_id="user123",
            limit=5,
            min_confidence=0.6
        )

    assert len(preferences) == 1
    assert preferences[0]["type"] == "preference"
    assert preferences[0]["topic"] == "python"
    assert preferences[0]["confidence"] == 0.85

@pytest.mark.asyncio
async def test_context_builder_includes_preferences():
    """Test intégration préférences dans contexte."""
    mock_preferences = [
        {"type": "preference", "topic": "python", "action": "préférer", "confidence": 0.85}
    ]

    with patch.object(context_builder.vector_service, "search_preferences", return_value=mock_preferences):
        context = await context_builder.build_context(
            user_message="Comment coder en Python ?",
            session=mock_session,
            user_id="user123",
            include_preferences=True
        )

    assert "Préférences utilisateur" in context
    assert "python" in context.lower()
```

---

## 📋 Checklist de travail

### Avant de commencer

- [ ] Lecture AGENT_SYNC.md (état dépôt, commits récents, déploiements)
- [ ] Lecture docs/passation.md (3 dernières entrées)
- [ ] Lecture MEMORY_LTM_GAPS_ANALYSIS.md ⭐ (document clé)
- [ ] Lecture docs/memory-roadmap.md (contexte architecture)
- [ ] `git fetch --all --prune` (sync avec remote)
- [ ] `git status` (vérifier working tree propre)
- [ ] `git log --oneline -10` (derniers commits)

### Pendant le développement

#### Gap #1 : Threads archivés

- [ ] Créer endpoint `POST /api/memory/consolidate-archived` (router.py)
- [ ] Modifier `queries.get_threads()` (ajouter `archived_only` param)
- [ ] Ajouter trigger auto dans `PUT /api/threads/{id}` (archivage)
- [ ] Créer tests `test_memory_archived_consolidation.py` (4-5 tests)
- [ ] Ajouter métriques Prometheus (MEMORY_ARCHIVED_*)
- [ ] Tests locaux : `pytest tests/backend/features/test_memory_archived_consolidation.py -v`

#### Gap #2 : Préférences ChromaDB

- [ ] Créer `save_preferences_to_vector_db()` dans analyzer.py
- [ ] Créer `_generate_embedding()` helper dans analyzer.py
- [ ] Appeler `save_preferences_to_vector_db()` dans `analyze_session()`
- [ ] Créer tests `test_preference_persistence.py` (3-4 tests)
- [ ] Ajouter métriques Prometheus (MEMORY_PREFERENCES_SAVED)
- [ ] Tests locaux : `pytest tests/backend/features/test_preference_persistence.py -v`

#### Gap #3 : Recherche préférences LTM

- [ ] Créer `search_preferences()` dans vector_service.py
- [ ] Intégrer dans `ContextBuilder.build_context()` (context_builder.py)
- [ ] Créer tests `test_preference_retrieval.py` (2-3 tests)
- [ ] Tests locaux : `pytest tests/backend/features/test_preference_retrieval.py -v`

### Tests & Qualité

- [ ] `pytest tests/backend/features/test_memory_*.py -v` (tous tests mémoire)
- [ ] `pytest` (suite complète backend)
- [ ] `ruff check src/backend` (linting)
- [ ] `mypy src/backend --ignore-missing-imports` (types)
- [ ] `npm run build` (frontend, vérifier 0 régression)

### Documentation

- [ ] Mise à jour `AGENT_SYNC.md` (section "Zones de travail en cours")
- [ ] Nouvelle entrée `docs/passation.md` (contexte, actions, tests, résultats)
- [ ] Mise à jour `docs/memory-roadmap.md` (marquer P0 gaps résolus)
- [ ] Créer `docs/deployments/2025-10-10-p0-gaps-resolution.md` (rapport complet)

### Commit & Push

- [ ] `git add` (fichiers modifiés + nouveaux tests + docs)
- [ ] `git commit -m "feat(P0): résolution 3 gaps critiques mémoire LTM"` (message détaillé)
- [ ] `git push origin main`
- [ ] Vérifier push GitHub OK

---

## 🎯 Résultat attendu

### Fonctionnalités opérationnelles

1. **Endpoint `/api/memory/consolidate-archived`**
   - Batch consolidation threads archivés
   - Skip threads déjà consolidés (sauf force=True)
   - Métriques exposées

2. **Trigger auto lors archivage**
   - `PUT /api/threads/{id}` avec `archived=True`
   - Background task consolidation immédiate
   - Métrique auto-trigger incrémentée

3. **Préférences sauvées ChromaDB**
   - Collection `memory_preferences` populée
   - Déduplication par `(user_id, topic, type)`
   - Métriques saved/errors exposées

4. **Recherche préférences LTM**
   - `ContextBuilder.build_context()` inclut préférences
   - Filtrage par user_id + confidence >= 0.6
   - Format lisible dans contexte agent

### Tests

- ✅ Tous tests mémoire passent (>15 tests)
- ✅ 0 régression tests existants
- ✅ Ruff + mypy clean
- ✅ Frontend build OK

### Métriques nouvelles exposées

```
# Gap #1 - Threads archivés
memory_archived_consolidated_total
memory_archived_auto_triggered_total
memory_archived_consolidation_errors_total{error_type}

# Gap #2 - Préférences ChromaDB
memory_preferences_saved_total{type}
memory_preferences_save_errors_total

# Existantes (P1)
memory_preferences_extracted_total{type}
memory_preferences_confidence (histogram)
memory_preferences_extraction_duration_seconds (histogram)
```

### Documentation

- `AGENT_SYNC.md` : section session P0 ajoutée
- `docs/passation.md` : entrée complète avec résultats
- `docs/memory-roadmap.md` : P0 gaps marqués résolved
- `docs/deployments/2025-10-10-p0-gaps-resolution.md` : rapport technique

---

## 🚀 Commande commit finale

```bash
git add \
  src/backend/features/memory/router.py \
  src/backend/features/memory/analyzer.py \
  src/backend/features/memory/vector_service.py \
  src/backend/features/threads/router.py \
  src/backend/features/chat/context_builder.py \
  src/backend/core/database/queries.py \
  tests/backend/features/test_memory_archived_consolidation.py \
  tests/backend/features/test_preference_persistence.py \
  tests/backend/features/test_preference_retrieval.py \
  docs/passation.md \
  docs/memory-roadmap.md \
  docs/deployments/2025-10-10-p0-gaps-resolution.md \
  AGENT_SYNC.md

git commit -m "feat(P0): résolution 3 gaps critiques mémoire LTM

Gap #1 - Threads archivés consolidés
- Endpoint POST /api/memory/consolidate-archived (batch processing)
- Trigger auto lors archivage (background task)
- Param archived_only dans queries.get_threads()
- Metadata archived_consolidated_at pour skip duplicatas
- Métriques: memory_archived_consolidated_total, auto_triggered_total

Gap #2 - Préférences sauvées ChromaDB
- Méthode save_preferences_to_vector_db() dans MemoryAnalyzer
- Helper _generate_embedding() pour embeddings
- Appel automatique dans analyze_session(persist=True)
- Collection memory_preferences populée
- Métriques: memory_preferences_saved_total{type}, save_errors_total

Gap #3 - Recherche préférences LTM
- Méthode search_preferences() dans VectorService
- Intégration ContextBuilder.build_context()
- Filtrage user_id + confidence >= 0.6
- Section 'Préférences utilisateur' dans contexte agent

Tests: 15+ nouveaux tests (100% passants), 0 régression
Docs: passation + roadmap + deployment report
Impact: LTM mémoire maintenant FONCTIONNELLE (threads archivés + préférences)"

git push origin main
```

---

## 📞 Contact & Questions

**Si blocage technique** :
1. Consulter `AGENT_SYNC.md` (section "Conflits & Résolution")
2. Documenter dans `docs/passation.md` (section "Blocages")
3. Continuer sur tâches non bloquantes
4. Ping FG (architecte) pour arbitrage

**Principe clé** : Tests > Documentation > Communication

---

**Ce prompt est exhaustif et autonome.** La prochaine instance peut commencer immédiatement après lecture des documents obligatoires.

**Bonne session ! 🚀**
