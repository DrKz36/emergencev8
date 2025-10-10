# PROMPT SESSION - Corrections Bugs P1-P2 Post-Audit

**Date:** 2025-10-10
**Priorité:** P1-P2 (Important - Non bloquant)
**Durée estimée:** 4-6 heures
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md (Section 2)

---

## 🎯 OBJECTIF DE LA SESSION

Corriger les **7 bugs non-critiques (P1-P2)** identifiés dans l'audit complet pour améliorer la robustesse et les performances du système avant la phase de refactoring architectural.

---

## 📋 CONTEXTE

### État actuel
✅ **Tous les bugs P0 résolus** (2025-10-10) :
- ✅ Bug #1 : Race condition `user_id` dans PreferenceExtractor
- ✅ Bug #2 : Fuite mémoire cache d'analyse
- ✅ Bug #3 : Absence de locks sur dictionnaires partagés

⚠️ **7 bugs P1-P2 restants** nécessitant correction :
- **P1** : 3 bugs impactant la fiabilité
- **P2** : 4 bugs impactant les performances

### Impact si non corrigés
- Risques de suppression globale accidentelle (vector_service)
- Cache préférences obsolète pendant 5min
- Requêtes N+1 → latence élevée
- Métadonnées concepts perdues
- Pas de retry sur échecs LLM
- Risque OOM sur grandes collections ChromaDB

### Documents de référence
1. **AUDIT_COMPLET_EMERGENCE_V8_20251010.md** - Section 2 (Bugs P1-P2)
2. **docs/passation.md** - Dernière entrée (2025-10-10 10:25)
3. **CODEV_PROTOCOL.md** - Protocole collaboration

---

## 🔴 BUGS P1 (PRIORITÉ HAUTE)

### Bug #4 : Inconsistance gestion `where_filter` vide (P1)
**Temps estimé :** 30 min

**Fichier :** [src/backend/features/memory/vector_service.py:768-772](src/backend/features/memory/vector_service.py#L768)

**Problème :**
```python
def delete_vectors(self, collection: Collection, where_filter: Dict[str, Any]) -> None:
    if not where_filter:
        logger.warning(f"Suppression annulée sur '{collection.name}' (pas de filtre).")
        return
```
Protection contre suppression globale, **MAIS** `where_filter = {"$and": [{"user_id": None}]}` → filtre vide accepté → suppression globale possible.

**Solution attendue :**
```python
def _is_filter_empty(self, where_filter: Dict[str, Any]) -> bool:
    """Vérifie récursivement si un filtre est vide ou sans critères valides."""
    if not where_filter:
        return True

    # Vérifier opérateurs logiques ($and, $or, $not)
    for op in ["$and", "$or"]:
        if op in where_filter:
            values = where_filter[op]
            if isinstance(values, list):
                # Si toutes les sous-conditions sont vides → filtre vide
                if all(self._is_filter_empty(v) for v in values):
                    return True

    # Vérifier si toutes les valeurs sont None
    non_operator_keys = [k for k in where_filter.keys() if not k.startswith("$")]
    if non_operator_keys and all(where_filter[k] is None for k in non_operator_keys):
        return True

    return False

def delete_vectors(self, collection: Collection, where_filter: Dict[str, Any]) -> None:
    if self._is_filter_empty(where_filter):
        logger.error(
            f"[VectorService] Suppression refusée sur '{collection.name}': "
            f"filtre vide ou invalide (protection suppression globale)"
        )
        raise ValueError("Cannot delete with empty or invalid filter (global deletion protection)")
```

**Tests à ajouter :**
```python
# tests/backend/features/test_vector_service_safety.py
async def test_delete_vectors_empty_filter_protection():
    """Test protection contre suppression globale avec filtres vides"""
    # Cas 1: Filtre vide direct
    with pytest.raises(ValueError, match="empty or invalid filter"):
        vector_service.delete_vectors(collection, {})

    # Cas 2: Filtre avec $and vide
    with pytest.raises(ValueError, match="empty or invalid filter"):
        vector_service.delete_vectors(collection, {"$and": []})

    # Cas 3: Filtre avec user_id=None
    with pytest.raises(ValueError, match="empty or invalid filter"):
        vector_service.delete_vectors(collection, {"user_id": None})

    # Cas 4: Filtre valide → devrait fonctionner
    vector_service.delete_vectors(collection, {"user_id": "user123"})  # OK
```

---

### Bug #5 : Cache préférences sans invalidation (P1)
**Temps estimé :** 45 min

**Fichier :** [src/backend/features/chat/memory_ctx.py:132-165](src/backend/features/chat/memory_ctx.py#L132)

**Problème :**
```python
self._prefs_cache: Dict[str, Tuple[str, datetime]] = {}
self._cache_ttl = timedelta(minutes=5)
```
Cache invalidé **uniquement** par TTL (5min). Si préférence mise à jour, l'utilisateur voit l'ancienne version pendant 5min.

**Solution attendue :**
```python
# memory_ctx.py - Ajouter méthode d'invalidation
def invalidate_preferences_cache(self, user_id: str):
    """Invalide le cache préférences pour un utilisateur donné."""
    cache_key = f"prefs:{user_id}"
    if cache_key in self._prefs_cache:
        del self._prefs_cache[cache_key]
        logger.info(f"[MemoryContext] Cache préférences invalidé pour {user_id}")

# router.py - Invalider après analyse
@router.post("/api/memory/analyze")
async def analyze_memory(...):
    # ... analyse existante ...

    # Invalider cache préférences après extraction
    memory_ctx = request.app.state.memory_context
    if memory_ctx and user_id:
        memory_ctx.invalidate_preferences_cache(user_id)

# gardener.py - Invalider après jardinage
async def tend_garden(...):
    # ... jardinage existant ...

    # Invalider cache après mise à jour préférences
    memory_ctx = self.get_memory_context()
    if memory_ctx and user_id:
        memory_ctx.invalidate_preferences_cache(user_id)
```

**Tests à ajouter :**
```python
# tests/backend/features/test_memory_ctx_cache.py
async def test_preferences_cache_invalidation():
    """Test que le cache est invalidé après mise à jour"""
    user_id = "test_user"

    # 1. Charger préférences (mise en cache)
    prefs1 = await memory_ctx.fetch_active_preferences(user_id, context="test")
    assert prefs1 == "preference v1"

    # 2. Mettre à jour préférences dans ChromaDB
    update_preferences_in_db(user_id, "preference v2")

    # 3. Sans invalidation → cache stale
    prefs2 = await memory_ctx.fetch_active_preferences(user_id, context="test")
    assert prefs2 == "preference v1"  # ❌ Ancienne version

    # 4. Avec invalidation → cache frais
    memory_ctx.invalidate_preferences_cache(user_id)
    prefs3 = await memory_ctx.fetch_active_preferences(user_id, context="test")
    assert prefs3 == "preference v2"  # ✅ Nouvelle version
```

---

### Bug #6 : Requêtes N+1 dans pipeline préférences (P1)
**Temps estimé :** 60 min

**Fichier :** [src/backend/features/memory/gardener.py:849-865](src/backend/features/memory/gardener.py#L849)

**Problème :**
```python
for record in records:
    existing = await self._get_existing_preference_record(record["id"])
    # ❌ Await dans boucle = N requêtes séquentielles
```

**Impact :** 50 préférences détectées → 50 requêtes ChromaDB séquentielles (~35ms/req = 1.75s total).

**Solution attendue :**
```python
async def _get_existing_preferences_batch(
    self, preference_ids: List[str]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Récupère plusieurs préférences existantes en une seule requête batch."""
    if not preference_ids:
        return {}

    try:
        result = self.preferences_collection.get(
            ids=preference_ids,
            include=["metadatas", "documents"]
        )

        # Construire dict {id: metadata}
        existing = {}
        if result and result["ids"]:
            for i, pref_id in enumerate(result["ids"]):
                existing[pref_id] = {
                    "metadata": result["metadatas"][i] if result["metadatas"] else {},
                    "document": result["documents"][i] if result["documents"] else ""
                }

        # Remplir les IDs manquants avec None
        for pref_id in preference_ids:
            if pref_id not in existing:
                existing[pref_id] = None

        return existing

    except Exception as e:
        logger.warning(f"[Gardener] Erreur batch fetch préférences: {e}")
        return {pid: None for pid in preference_ids}

async def _store_preference_records(self, records: List[Dict[str, Any]], ...):
    """Version optimisée avec batch fetch."""
    if not records:
        return 0

    # Batch fetch toutes les préférences existantes en 1 seule requête
    preference_ids = [r["id"] for r in records]
    existing_prefs = await self._get_existing_preferences_batch(preference_ids)

    saved = 0
    for record in records:
        existing = existing_prefs.get(record["id"])

        # ... logique upsert existante ...

        saved += 1

    return saved
```

**Tests à ajouter :**
```python
# tests/backend/features/test_gardener_batch.py
async def test_batch_preference_fetch_performance():
    """Test que le batch fetch est plus rapide que N+1"""
    import time

    # Simuler 50 préférences
    records = [{"id": f"pref_{i}", "text": f"Preference {i}"} for i in range(50)]

    # Mesurer temps avec batch fetch (nouvelle implémentation)
    start = time.time()
    await gardener._store_preference_records(records, ...)
    batch_time = time.time() - start

    # Batch fetch devrait être <500ms (vs 1.75s avec N+1)
    assert batch_time < 0.5, f"Batch fetch trop lent: {batch_time}s"
```

---

## 🟡 BUGS P2 (PRIORITÉ MOYENNE)

### Bug #7 : Métadonnées perdues dans concepts (P2)
**Temps estimé :** 30 min

**Fichier :** [src/backend/features/memory/gardener.py:1486-1514](src/backend/features/memory/gardener.py#L1486)

**Problème :**
```python
thread_id = session.get("thread_id")
message_id = session.get("message_id")
# ❌ Ces champs ne sont JAMAIS renseignés dans les stubs créés
```

**Solution :** Renseigner `thread_id` et `message_id` depuis le contexte réel de la session.

---

### Bug #8 : Pas de retry sur échecs LLM (P2)
**Temps estimé :** 45 min

**Fichier :** [src/backend/features/memory/preference_extractor.py:286-322](src/backend/features/memory/preference_extractor.py#L286)

**Solution :** Ajouter retry (max 2 tentatives) avec fallback sur agent alternatif.

---

### Bug #9 : Pas de timeout sur appels LLM (P2)
**Temps estimé :** 30 min

**Fichier :** [src/backend/features/memory/analyzer.py:246-322](src/backend/features/memory/analyzer.py#L246)

**Solution :** Wrap avec `asyncio.wait_for(timeout=30)`.

---

### Bug #10 : Chargement complet metadata sans pagination (P2)
**Temps estimé :** 60 min

**Fichier :** [src/backend/features/memory/gardener.py:1591-1599](src/backend/features/memory/gardener.py#L1591)

**Problème :**
```python
snapshot = self.knowledge_collection.get(include=["metadatas"])
# ❌ Charge TOUS les vecteurs de la collection en mémoire (potentiellement 100k+ items)
```

**Solution :** Implémenter pagination ChromaDB avec `offset`/`limit`.

---

## 📝 CHECKLIST D'EXÉCUTION

### Préparation (5 min)
- [ ] Lire AUDIT_COMPLET_EMERGENCE_V8_20251010.md Section 2
- [ ] Vérifier docs/passation.md (dernière entrée 10:25)
- [ ] S'assurer backend local fonctionne (`curl http://127.0.0.1:8000/api/health`)
- [ ] Activer venv Python

### Phase 1 - Bugs P1 (2h30)
- [ ] **Bug #4** : Validation récursive `where_filter` (30 min)
- [ ] **Bug #5** : Invalidation cache préférences (45 min)
- [ ] **Bug #6** : Batch fetch préférences (60 min)
- [ ] Tests P1 : `pytest tests/backend/features/ -k "safety or cache or batch" -v`

### Phase 2 - Bugs P2 (2h30)
- [ ] **Bug #7** : Métadonnées concepts (30 min)
- [ ] **Bug #8** : Retry LLM (45 min)
- [ ] **Bug #9** : Timeout LLM (30 min)
- [ ] **Bug #10** : Pagination ChromaDB (60 min)
- [ ] Tests P2 : `pytest tests/backend/features/ -k "metadata or retry or timeout or pagination" -v`

### Validation finale (30 min)
- [ ] Tous tests passent : `pytest tests/backend/features/ -v`
- [ ] Ruff : `ruff check src/backend/features/memory/`
- [ ] Mypy : `mypy src/backend/features/memory/`
- [ ] Build : `npm run build`

### Documentation (15 min)
- [ ] Mettre à jour `docs/passation.md` avec nouvelle entrée :
  - Agent: Claude Code
  - Date: 2025-10-10 [HH:MM]
  - Fichiers modifiés (liste complète)
  - Tests : X/X PASSED
  - Statut : ✅ Bugs P1-P2 résolus

---

## 🎯 CRITÈRES DE SUCCÈS

### Résultats attendus
✅ **Bug #4** : Protection suppression globale avec validation récursive
✅ **Bug #5** : Cache préférences invalidé après mise à jour
✅ **Bug #6** : Batch fetch préférences (<500ms vs 1.75s)
✅ **Bug #7** : Métadonnées concepts renseignées
✅ **Bug #8** : Retry LLM (max 2 tentatives)
✅ **Bug #9** : Timeout LLM (30s)
✅ **Bug #10** : Pagination ChromaDB implémentée

### Livrables
1. **Code modifié** : 6+ fichiers (vector_service, memory_ctx, gardener, preference_extractor, analyzer)
2. **Tests ajoutés** : 10+ tests (safety, cache, batch, retry, pagination)
3. **Documentation** : Entrée `docs/passation.md` complète

---

## ⚠️ POINTS D'ATTENTION

### Priorité des bugs
1. **P1 d'abord** : Bugs #4, #5, #6 (risques fiabilité)
2. **P2 ensuite** : Bugs #7, #8, #9, #10 (optimisations)

### Pièges à éviter
❌ **NE PAS** tester manuellement les suppressions globales (risque perte données)
❌ **NE PAS** oublier d'invalider cache dans tous les points d'entrée (router + gardener)
❌ **NE PAS** implémenter batch fetch sans tests de performance

### Bonnes pratiques
✅ Tests unitaires pour chaque bug corrigé
✅ Logger toutes les protections (suppressions refusées, cache invalidé)
✅ Mesurer gains performance (avant/après batch fetch)

---

## 📚 RESSOURCES

### Fichiers à consulter
1. **AUDIT_COMPLET_EMERGENCE_V8_20251010.md** (Section 2)
2. **src/backend/features/memory/vector_service.py**
3. **src/backend/features/chat/memory_ctx.py**
4. **src/backend/features/memory/gardener.py**
5. **src/backend/features/memory/preference_extractor.py**
6. **src/backend/features/memory/analyzer.py**

### Tests existants
- `tests/backend/features/test_memory_enhancements.py`
- `tests/backend/features/test_memory_cache_eviction.py`
- `tests/backend/features/test_memory_concurrency.py`

---

## 🚀 APRÈS CETTE SESSION

### Prochaines priorités (Phase 1 - Fin)
1. **Nettoyage projet** : ~13 Mo fichiers obsolètes (voir `CLEANUP_PLAN_20251010.md`)
2. **Mise à jour documentation** : Corriger incohérences Section 5 audit
3. **Déploiement production** : Déployer tous fixes P0/P1/P2 sur Cloud Run

### Session suivante suggérée
**PROMPT_NEXT_SESSION_CLEANUP.md** (nettoyage + documentation)

---

**Prompt généré le:** 2025-10-10 10:30
**Basé sur:** AUDIT_COMPLET_EMERGENCE_V8_20251010.md (Section 2)
**Priorité:** P1-P2 (Important)
**Durée estimée:** 4-6 heures
**Agent recommandé:** Claude Code (expertise Python/async/ChromaDB)

---

## 📊 ÉTAT ACTUEL DU PROJET

### Bugs Critiques (P0)
- ✅ Bug #1 : PreferenceExtractor user_id (RÉSOLU 2025-10-10 09:40)
- ✅ Bug #2 : Fuite mémoire cache (RÉSOLU 2025-10-10 10:25)
- ✅ Bug #3 : Race conditions locks (RÉSOLU 2025-10-10 10:25)

### Bugs Non-Critiques
- ⚠️ Bug #4-10 : 7 bugs P1-P2 à corriger (CETTE SESSION)

### Tests Actuels
- 232 tests pytest identifiés
- 16 tests P0 ajoutés aujourd'hui (éviction + concurrence)
- Couverture estimée : ~60%

**Objectif post-session :** 70% couverture, 0 bugs P1 restants
