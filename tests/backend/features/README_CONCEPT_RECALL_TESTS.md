# Tests Concept Recall - Notes importantes

## Problème ChromaDB et listes dans les métadonnées

**Date** : 2025-10-04
**Statut** : ✅ **CORRIGÉ**

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

### Solution implémentée

**✅ Correction appliquée le 2025-10-04 (commit f4e12e1)**

1. **Migration `thread_ids` → `thread_ids_json`** :
   - [gardener.py:1501](../../../src/backend/features/memory/gardener.py#L1501) : Stockage JSON string
     ```python
     "thread_ids_json": json.dumps([thread_id] if thread_id else [])
     ```

   - [concept_recall.py:97,170](../../../src/backend/features/memory/concept_recall.py#L97) : Décodage JSON
     ```python
     thread_ids_json = meta.get("thread_ids_json", "[]")
     thread_ids = json.loads(thread_ids_json) if thread_ids_json else []
     ```

   - [concept_recall.py:178](../../../src/backend/features/memory/concept_recall.py#L178) : Encodage lors mise à jour
     ```python
     updated_meta["thread_ids_json"] = json.dumps(thread_ids)
     ```

2. **Correction formule distance → score** :
   - ChromaDB utilise la distance L2² pour vecteurs normalisés
   - Formule corrigée : `score = 1.0 - (distance / 2.0)` au lieu de `1.0 - distance`
   - Seuil ajusté : `SIMILARITY_THRESHOLD = 0.5` (au lieu de 0.75)

3. **Correction métadonnées NULL** :
   - Remplacement `None` → `""` pour `thread_id` et `message_id`
   - ChromaDB rejette les valeurs `None` dans les métadonnées

### Statut des tests (2025-10-04 - Après correction)

**✅ Tous les tests passent : 12/12**

#### Tests concept_recall_tracker.py (8/8)
- ✅ `test_detect_recurring_concepts_first_mention`
- ✅ `test_detect_recurring_concepts_second_mention`
- ✅ `test_detect_recurring_concepts_excludes_same_thread`
- ✅ `test_update_mention_metadata`
- ✅ `test_query_concept_history`
- ✅ `test_max_recalls_per_message_limit`
- ✅ `test_emit_events_disabled_by_default`
- ✅ `test_similarity_threshold_filtering`

#### Tests memory_gardener_enrichment.py (4/4)
- ✅ `test_vectorize_concepts_with_enriched_metadata`
- ✅ `test_vectorize_concepts_without_thread_id`
- ✅ `test_migration_script_compatibility`
- ✅ `test_enriched_metadata_timestamps_iso8601`

### Configuration requise

1. **Variable d'environnement** (`.env.local`) :
   ```bash
   CONCEPT_RECALL_EMIT_EVENTS=true
   ```

2. **Backend** :
   - Le système s'initialise automatiquement au démarrage
   - Log confirmation : `ConceptRecallTracker initialisé`

### Prochaines étapes

1. ✅ Migration données production : Aucune donnée existante détectée (vector store vide)
2. 📊 **TODO** : Monitoring métriques Prometheus
   - Taux de détection de concepts récurrents
   - Scores de similarité moyens
   - Fréquence des rappels par utilisateur
3. 🎨 **TODO** : Modal "Voir l'historique"
   - Afficher les threads passés où le concept a été mentionné
   - Permettre navigation vers conversation antérieure
4. 🧪 **TODO** : QA manuelle complète
   - Tester banner concept recall en conditions réelles
   - Valider événements WebSocket `ws:concept_recall`
   - Vérifier auto-hide après 15 secondes

### Références

- [ChromaDB documentation](https://docs.trychroma.com/guides)
- [Commit correction](https://github.com/DrKz36/emergencev8/commit/f4e12e1)
- [Documentation passation](../../../docs/passation.md)
- Tests : `test_concept_recall_tracker.py`, `test_memory_gardener_enrichment.py`

### Notes techniques

#### Distance vs Similarité
ChromaDB retourne des **distances L2²** (squared euclidean) pour les vecteurs normalisés.
Conversion en similarité cosine :
```python
# Pour vecteurs normalisés : distance_l2² = 2 * (1 - cosine_similarity)
# Donc : cosine_similarity = 1 - (distance / 2)
distance = res.get("distance", 2.0)
score = 1.0 - (distance / 2.0)
```

#### Seuils de similarité
- **Detection** : 0.5 (50%) - Détection de concepts récurrents
- **Query explicite** : 0.6 (60%) - Recherche manuelle "on a déjà parlé de X ?"
- **Max recalls** : 3 par message - Évite spam UI
