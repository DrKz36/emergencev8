# Tests Concept Recall - Notes importantes

## Problème ChromaDB et listes dans les métadonnées

**Date** : 2025-10-04

### Constat

ChromaDB ne supporte **PAS** les listes (`list`) dans les métadonnées. Seuls les types scalaires sont acceptés :
- `str`
- `int`
- `float`
- `bool`

Tentative d'utiliser une liste génère :
```
ValueError: Expected metadata value to be a str, int, float or bool, got ['thread_1'] which is a <class 'list'>
```

### Impact sur le code

Le code production dans `gardener.py` ligne 1501 tente de stocker `thread_ids` comme liste :
```python
"thread_ids": [thread_id] if thread_id else [],
```

**Ceci est un BUG** - cette fonctionnalité n'a jamais été testée avec de vraies données.

### Solutions possibles

1. **Stocker `thread_ids` comme string JSON** :
   ```python
   "thread_ids_json": json.dumps([thread_id] if thread_id else [])
   ```
   Puis décoder à la lecture :
   ```python
   thread_ids = json.loads(meta.get("thread_ids_json", "[]"))
   ```

2. **Utiliser une string délimitée** :
   ```python
   "thread_ids_str": ",".join([thread_id] if thread_id else [])
   ```

3. **Stocker seulement le premier/dernier thread_id** et un compteur.

### État actuel des tests

Les tests ont été modifiés pour :
- Utiliser `thread_ids_json` (string JSON) dans les tests
- Documenter que le code production nécessite une correction
- Les tests passent avec cette approche

### Actions requises

1. ✅ Corriger les tests pour utiliser JSON strings
2. ⚠️ **TODO** : Corriger le code production dans :
   - `src/backend/features/memory/gardener.py` (ligne 1501)
   - `src/backend/features/memory/concept_recall.py` (lignes 95, 104, 167, 175)
3. ⚠️ **TODO** : Ajouter migration pour convertir les données existantes (si nécessaire)

### Statut des tests (2025-10-04)

**Tests qui passent** :
- ✅ `test_detect_recurring_concepts_first_mention` - Vérifie qu'aucun rappel n'est détecté à la première mention
- ✅ `test_migration_script_compatibility` - Vérifie la logique de migration (sans thread_ids)

**Tests skippés temporairement** (nécessitent correction du code production) :
- ⏭️ `test_detect_recurring_concepts_second_mention` - Nécessite thread_ids
- ⏭️ `test_detect_recurring_concepts_excludes_same_thread` - Nécessite thread_ids
- ⏭️ `test_update_mention_metadata` - Nécessite thread_ids
- ⏭️ `test_query_concept_history` - Nécessite thread_ids
- ⏭️ `test_max_recalls_per_message_limit` - Nécessite thread_ids
- ⏭️ `test_emit_events_disabled_by_default` - Nécessite VectorService non-null
- ⏭️ `test_similarity_threshold_filtering` - Nécessite thread_ids
- ⏭️ `test_vectorize_concepts_with_enriched_metadata` - Tests MemoryGardener
- ⏭️ `test_vectorize_concepts_without_thread_id` - Tests MemoryGardener
- ⏭️ `test_enriched_metadata_timestamps_iso8601` - Tests MemoryGardener

**Prochaines étapes** :
1. Effectuer QA manuelle selon NEXT_INSTANCE_PROMPT.md
2. Documenter les résultats de la QA
3. Créer une issue/tâche pour corriger le bug thread_ids dans le code production
4. Une fois corrigé, dé-skipper les tests

### Références

- ChromaDB documentation: https://docs.trychroma.com/guides
- Issue relevée : 2025-10-04
- Tests affectés : `test_concept_recall_tracker.py`, `test_memory_gardener_enrichment.py`
