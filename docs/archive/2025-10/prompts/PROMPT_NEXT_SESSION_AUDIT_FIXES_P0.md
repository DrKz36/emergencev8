# PROMPT SESSION - Corrections Bugs Critiques Post-Audit

**Date:** 2025-10-10
**Priorité:** P0 (Critique - Urgent)
**Durée estimée:** 2-3 heures
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md

---

## 🎯 OBJECTIF DE LA SESSION

Corriger les **2 bugs critiques P0 restants** identifiés dans l'audit complet, qui présentent des risques de production (fuite mémoire, race conditions).

---

## 📋 CONTEXTE

### État actuel
✅ **Bug #1 RÉSOLU** : Race condition `user_id` dans PreferenceExtractor (déployé le 2025-10-10)

⚠️ **Bug #2 NON RÉSOLU** : Fuite mémoire dans le cache d'analyse
⚠️ **Bug #3 NON RÉSOLU** : Absence de locks sur dictionnaires partagés

### Impact si non corrigés
- **Bug #2** : Consommation mémoire croissante → OOM (Out of Memory) en production
- **Bug #3** : Race conditions → corruption données, comportement non déterministe

### Documents de référence
1. **AUDIT_COMPLET_EMERGENCE_V8_20251010.md** - Rapport complet (Section 1: Bugs Critiques)
2. **docs/passation.md** - Journal inter-agents (dernière entrée: 2025-10-10 09:40)
3. **CODEV_PROTOCOL.md** - Protocole collaboration

---

## 🔴 BUG #2 : FUITE MÉMOIRE DANS CACHE D'ANALYSE

### Localisation
**Fichier:** [src/backend/features/memory/analyzer.py:70, 358-362](src/backend/features/memory/analyzer.py#L70)

### Code problématique

```python
# Ligne 70
_ANALYSIS_CACHE: Dict[str, tuple[Dict[str, Any], datetime]] = {}

# Lignes 358-362
if len(_ANALYSIS_CACHE) > 100:
    oldest_key = min(_ANALYSIS_CACHE.keys(), key=lambda k: _ANALYSIS_CACHE[k][1])
    del _ANALYSIS_CACHE[oldest_key]  # ❌ Supprime SEULEMENT 1 élément
```

### Problème
Si burst de 200+ consolidations → le cache grandit indéfiniment car on ne supprime qu'1 élément alors que 100+ entrées existent déjà.

### Solution attendue

```python
# Ligne 70 - Ajouter constantes
_ANALYSIS_CACHE: Dict[str, tuple[Dict[str, Any], datetime]] = {}
MAX_CACHE_SIZE = 100
EVICTION_THRESHOLD = 80  # Éviction agressive quand >80 entrées

# Lignes 358-370 - Remplacer par éviction agressive
if len(_ANALYSIS_CACHE) > EVICTION_THRESHOLD:
    # Trier par timestamp et garder les 50 plus récents
    sorted_keys = sorted(
        _ANALYSIS_CACHE.keys(),
        key=lambda k: _ANALYSIS_CACHE[k][1],
        reverse=True
    )
    # Supprimer les anciennes entrées (garder top 50)
    for key in sorted_keys[50:]:
        del _ANALYSIS_CACHE[key]

    logger.info(
        f"[MemoryAnalyzer] Cache éviction: {len(sorted_keys) - 50} entrées "
        f"supprimées (cache size: {len(_ANALYSIS_CACHE)})"
    )
```

### Tests à ajouter

```python
# tests/backend/features/test_memory_cache_eviction.py
import pytest
from backend.features.memory.analyzer import MemoryAnalyzer, _ANALYSIS_CACHE
from datetime import datetime, timedelta

@pytest.fixture
def analyzer(mock_db_manager, mock_chat_service):
    return MemoryAnalyzer(mock_db_manager, mock_chat_service)

async def test_cache_eviction_aggressive():
    """Test que l'éviction est agressive (supprime 50+ entrées)"""
    # Simuler 100 entrées
    for i in range(100):
        _ANALYSIS_CACHE[f"session_{i}"] = (
            {"summary": f"test_{i}"},
            datetime.now() - timedelta(minutes=i)
        )

    assert len(_ANALYSIS_CACHE) == 100

    # Ajouter 1 entrée supplémentaire pour déclencher éviction
    _ANALYSIS_CACHE["session_100"] = ({"summary": "test_100"}, datetime.now())

    # Simuler éviction (appeler méthode privée ou déclencher via consolidation)
    # L'éviction devrait ramener cache à ~50 entrées

    # Vérifier que cache réduit à ~50 (pas juste -1)
    assert len(_ANALYSIS_CACHE) <= 55  # Tolérance ±5

async def test_cache_keeps_most_recent():
    """Test que l'éviction garde les plus récents"""
    # Simuler 100 entrées avec timestamps échelonnés
    old_keys = []
    recent_keys = []

    for i in range(80):
        key = f"old_{i}"
        _ANALYSIS_CACHE[key] = ({"summary": "old"}, datetime.now() - timedelta(hours=i))
        old_keys.append(key)

    for i in range(30):
        key = f"recent_{i}"
        _ANALYSIS_CACHE[key] = ({"summary": "recent"}, datetime.now())
        recent_keys.append(key)

    # Déclencher éviction
    # ...

    # Vérifier que les récents sont gardés
    for key in recent_keys[:20]:  # Au moins 20 récents gardés
        assert key in _ANALYSIS_CACHE

    # Vérifier que les anciens sont supprimés
    for key in old_keys[50:]:  # Anciens >50 supprimés
        assert key not in _ANALYSIS_CACHE
```

### Validation

```bash
# Tests
pytest tests/backend/features/test_memory_cache_eviction.py -v

# Linting
ruff check src/backend/features/memory/analyzer.py

# Type checking
mypy src/backend/features/memory/analyzer.py
```

---

## 🔴 BUG #3 : ABSENCE DE LOCKS SUR DICTIONNAIRES PARTAGÉS

### Localisations multiples

1. [src/backend/features/memory/analyzer.py:70](src/backend/features/memory/analyzer.py#L70) → `_ANALYSIS_CACHE`
2. [src/backend/features/memory/incremental_consolidation.py:29](src/backend/features/memory/incremental_consolidation.py#L29) → `self.message_counters`
3. [src/backend/features/memory/proactive_hints.py:66-67](src/backend/features/memory/proactive_hints.py#L66) → `self._concept_counters`
4. [src/backend/features/memory/intent_tracker.py:65](src/backend/features/memory/intent_tracker.py#L65) → `self.reminder_counts`

### Problème
Dictionnaires partagés modifiés sans lock → **race conditions** si 2+ analyses concurrentes → corruption données.

### Solution attendue

#### 1. MemoryAnalyzer (analyzer.py)

```python
import asyncio
from typing import Dict, Any, Tuple
from datetime import datetime

class MemoryAnalyzer:
    def __init__(self, db_manager, ...):
        self._cache_lock = asyncio.Lock()
        self._cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        # ... reste init

    async def _get_from_cache(self, key: str) -> Optional[Tuple[Dict[str, Any], datetime]]:
        """Récupère entrée du cache de manière thread-safe"""
        async with self._cache_lock:
            return self._cache.get(key)

    async def _put_in_cache(self, key: str, value: Dict[str, Any], timestamp: datetime):
        """Ajoute entrée au cache de manière thread-safe"""
        async with self._cache_lock:
            self._cache[key] = (value, timestamp)

            # Éviction agressive (ici, sous lock)
            if len(self._cache) > EVICTION_THRESHOLD:
                sorted_keys = sorted(
                    self._cache.keys(),
                    key=lambda k: self._cache[k][1],
                    reverse=True
                )
                for key in sorted_keys[50:]:
                    del self._cache[key]

                logger.info(f"[Cache] Éviction: {len(sorted_keys) - 50} entrées supprimées")

    async def _remove_from_cache(self, key: str):
        """Supprime entrée du cache de manière thread-safe"""
        async with self._cache_lock:
            self._cache.pop(key, None)
```

#### 2. IncrementalConsolidator (incremental_consolidation.py)

```python
import asyncio
from typing import Dict

class IncrementalConsolidator:
    def __init__(self, ...):
        self._counter_lock = asyncio.Lock()
        self.message_counters: Dict[str, int] = {}

    async def increment_counter(self, session_id: str) -> int:
        """Incrémente compteur de manière thread-safe"""
        async with self._counter_lock:
            self.message_counters[session_id] = self.message_counters.get(session_id, 0) + 1
            return self.message_counters[session_id]

    async def get_counter(self, session_id: str) -> int:
        """Récupère compteur de manière thread-safe"""
        async with self._counter_lock:
            return self.message_counters.get(session_id, 0)

    async def reset_counter(self, session_id: str):
        """Remet compteur à zéro de manière thread-safe"""
        async with self._counter_lock:
            self.message_counters[session_id] = 0
```

#### 3. ProactiveHintEngine (proactive_hints.py)

```python
import asyncio

class ConceptTracker:
    def __init__(self):
        self._counter_lock = asyncio.Lock()
        self._concept_counters: Dict[str, int] = {}

    async def increment(self, concept_id: str) -> int:
        async with self._counter_lock:
            self._concept_counters[concept_id] = self._concept_counters.get(concept_id, 0) + 1
            return self._concept_counters[concept_id]

    async def get_count(self, concept_id: str) -> int:
        async with self._counter_lock:
            return self._concept_counters.get(concept_id, 0)
```

#### 4. IntentTracker (intent_tracker.py)

```python
import asyncio

class IntentTracker:
    def __init__(self, ...):
        self._reminder_lock = asyncio.Lock()
        self.reminder_counts: Dict[str, int] = {}

    async def increment_reminder(self, intent_id: str) -> int:
        async with self._reminder_lock:
            self.reminder_counts[intent_id] = self.reminder_counts.get(intent_id, 0) + 1
            return self.reminder_counts[intent_id]

    async def get_reminder_count(self, intent_id: str) -> int:
        async with self._reminder_lock:
            return self.reminder_counts.get(intent_id, 0)
```

### Tests à ajouter

```python
# tests/backend/features/test_memory_concurrency.py
import pytest
import asyncio
from backend.features.memory.analyzer import MemoryAnalyzer

async def test_cache_concurrent_access():
    """Test que le cache gère correctement les accès concurrents"""
    analyzer = MemoryAnalyzer(...)

    async def write_cache(i: int):
        await analyzer._put_in_cache(f"key_{i}", {"data": i}, datetime.now())

    # Lancer 100 écritures concurrentes
    tasks = [write_cache(i) for i in range(100)]
    await asyncio.gather(*tasks)

    # Vérifier aucune corruption
    cache_size = len(analyzer._cache)
    assert cache_size > 0  # Au moins quelques entrées gardées
    assert cache_size <= 100  # Pas de dépassement

async def test_counter_concurrent_increments():
    """Test que les compteurs gèrent correctement les incréments concurrents"""
    consolidator = IncrementalConsolidator(...)
    session_id = "test_session"

    async def increment():
        await consolidator.increment_counter(session_id)

    # Lancer 50 incréments concurrents
    tasks = [increment() for _ in range(50)]
    await asyncio.gather(*tasks)

    # Vérifier compteur correct (pas de race condition)
    count = await consolidator.get_counter(session_id)
    assert count == 50  # Tous les incréments comptés
```

### Validation

```bash
# Tests concurrence
pytest tests/backend/features/test_memory_concurrency.py -v

# Tests existants (non-régression)
pytest tests/backend/features/test_memory_enhancements.py -v

# Type checking
mypy src/backend/features/memory/
```

---

## 📝 CHECKLIST D'EXÉCUTION

### Préparation (5 min)

- [ ] Lire AUDIT_COMPLET_EMERGENCE_V8_20251010.md Section 1
- [ ] Vérifier docs/passation.md (dernière entrée)
- [ ] S'assurer backend local fonctionne (`curl http://127.0.0.1:8000/api/health`)
- [ ] Activer venv Python (`.venv/Scripts/Activate.ps1` ou `source .venv/bin/activate`)

### Bug #2 - Fuite mémoire cache (45 min)

- [ ] Lire code actuel `src/backend/features/memory/analyzer.py:70, 358-362`
- [ ] Implémenter constantes `MAX_CACHE_SIZE`, `EVICTION_THRESHOLD`
- [ ] Remplacer éviction simple par éviction agressive (garder top 50)
- [ ] Ajouter log `[MemoryAnalyzer] Cache éviction: X entrées supprimées`
- [ ] Créer tests `tests/backend/features/test_memory_cache_eviction.py`
- [ ] Exécuter tests : `pytest tests/backend/features/test_memory_cache_eviction.py -v`
- [ ] Vérifier ruff : `ruff check src/backend/features/memory/analyzer.py`
- [ ] Vérifier mypy : `mypy src/backend/features/memory/analyzer.py`

### Bug #3 - Locks dictionnaires (90 min)

**3.1 MemoryAnalyzer (20 min)**
- [ ] Ajouter `self._cache_lock = asyncio.Lock()`
- [ ] Créer méthodes `_get_from_cache()`, `_put_in_cache()`, `_remove_from_cache()`
- [ ] Remplacer tous accès directs `_ANALYSIS_CACHE` par méthodes lockées
- [ ] Tester

**3.2 IncrementalConsolidator (20 min)**
- [ ] Ajouter `self._counter_lock = asyncio.Lock()`
- [ ] Créer méthodes `increment_counter()`, `get_counter()`, `reset_counter()`
- [ ] Remplacer accès directs `self.message_counters` par méthodes lockées
- [ ] Tester

**3.3 ProactiveHintEngine (20 min)**
- [ ] Ajouter `self._counter_lock = asyncio.Lock()` dans `ConceptTracker`
- [ ] Créer méthodes `increment()`, `get_count()`
- [ ] Remplacer accès directs `self._concept_counters` par méthodes lockées
- [ ] Tester

**3.4 IntentTracker (20 min)**
- [ ] Ajouter `self._reminder_lock = asyncio.Lock()`
- [ ] Créer méthodes `increment_reminder()`, `get_reminder_count()`
- [ ] Remplacer accès directs `self.reminder_counts` par méthodes lockées
- [ ] Tester

**3.5 Tests concurrence (10 min)**
- [ ] Créer `tests/backend/features/test_memory_concurrency.py`
- [ ] Test `test_cache_concurrent_access()`
- [ ] Test `test_counter_concurrent_increments()`
- [ ] Exécuter : `pytest tests/backend/features/test_memory_concurrency.py -v`

### Validation finale (15 min)

- [ ] Tous tests passent : `pytest tests/backend/features/ -v`
- [ ] Tests mémoire : `pytest tests/backend/features/ -k memory -v`
- [ ] Ruff : `ruff check src/backend/features/memory/`
- [ ] Mypy : `mypy src/backend/features/memory/`
- [ ] Build : `npm run build`
- [ ] Backend démarre : `python -m uvicorn --app-dir src backend.main:app`

### Documentation (10 min)

- [ ] Mettre à jour `docs/passation.md` avec nouvelle entrée :
  - Agent: Claude Code
  - Date: 2025-10-10 [HH:MM]
  - Fichiers modifiés (liste complète)
  - Tests : X/X PASSED
  - Statut : ✅ Bugs P0 #2 et #3 résolus

---

## 🎯 CRITÈRES DE SUCCÈS

### Résultats attendus

✅ **Bug #2** : Éviction agressive implémentée (garde top 50 au lieu de supprimer 1)
✅ **Bug #3** : Locks `asyncio.Lock()` sur tous dictionnaires partagés (4 fichiers)
✅ **Tests** : Nouveaux tests concurrence passent (100%)
✅ **Non-régression** : Tests existants mémoire passent (100%)
✅ **Qualité** : Ruff + Mypy sans erreur

### Livrables

1. **Code modifié** :
   - `src/backend/features/memory/analyzer.py` (éviction + locks)
   - `src/backend/features/memory/incremental_consolidation.py` (locks)
   - `src/backend/features/memory/proactive_hints.py` (locks)
   - `src/backend/features/memory/intent_tracker.py` (locks)

2. **Tests ajoutés** :
   - `tests/backend/features/test_memory_cache_eviction.py` (2+ tests)
   - `tests/backend/features/test_memory_concurrency.py` (2+ tests)

3. **Documentation** :
   - Entrée `docs/passation.md` (date, fichiers, tests, statut)

---

## ⚠️ POINTS D'ATTENTION

### Pièges à éviter

❌ **NE PAS** utiliser `threading.Lock()` → utiliser `asyncio.Lock()` (code async)
❌ **NE PAS** oublier les locks dans les méthodes privées (ex: `_evict_cache()`)
❌ **NE PAS** deadlock → toujours libérer lock (`async with` garantit release)
❌ **NE PAS** accéder dictionnaires partagés en dehors des méthodes lockées

### Bonnes pratiques

✅ Toujours wrapper accès dictionnaire dans `async with self._lock:`
✅ Garder sections critiques (sous lock) courtes
✅ Logger évictions cache pour observabilité
✅ Tester concurrence avec `asyncio.gather()` (simule charge)

---

## 📚 RESSOURCES

### Fichiers à consulter

1. **AUDIT_COMPLET_EMERGENCE_V8_20251010.md** (Section 1, 2, 7)
2. **src/backend/features/memory/analyzer.py**
3. **src/backend/features/memory/incremental_consolidation.py**
4. **src/backend/features/memory/proactive_hints.py**
5. **src/backend/features/memory/intent_tracker.py**
6. **docs/passation.md**

### Documentation Python

- [asyncio.Lock](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [mypy async](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html#coroutines-and-asyncio)

---

## 🚀 APRÈS CETTE SESSION

### Prochaines priorités (Phase 1 - Suite)

1. **Bugs P1-P2** (7 bugs non-critiques identifiés dans audit)
2. **Nettoyage projet** (exécuter `CLEANUP_PLAN_20251010.md`)
3. **Mise à jour documentation** (corriger incohérences Section 5 audit)

### Session suivante suggérée

**PROMPT_NEXT_SESSION_AUDIT_FIXES_P1.md** (bugs non-critiques + nettoyage)

---

**Prompt généré le:** 2025-10-10
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md
**Priorité:** P0 - Critique
**Durée estimée:** 2-3 heures
**Agent recommandé:** Claude Code (expertise Python/async)
