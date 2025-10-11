# Chat Feature - Memory Context Builder

**Module**: `src/backend/features/chat/memory_ctx.py`
**Version**: V1.1 (Phase P2.1)
**Dernière mise à jour**: 2025-10-11

## Vue d'ensemble

Le `MemoryContextBuilder` est responsable de construire le contexte mémoire pour les conversations. Il combine plusieurs sources d'information pour enrichir les réponses de l'assistant avec des connaissances pertinentes et des préférences utilisateur.

## Fonctionnalités principales

### 1. Cache in-memory préférences (P2.1)

**Performance optimisée** pour l'injection des préférences utilisateur:

- **TTL**: 5 minutes (couvre ~8-10 messages)
- **Hit rate attendu**: >80% après warmup
- **Latence**:
  - Cache HIT: ~2ms (80% des cas)
  - Cache MISS: ~35ms (requête ChromaDB)

**Métriques Prometheus**:
```python
memory_cache_operations_total{operation="hit|miss", type="preferences"}
```

**Garbage collection automatique**: suppression des entrées expirées lors des mises à jour du cache.

### 2. Injection automatique préférences actives

Les préférences utilisateur sont automatiquement injectées dans le contexte RAG si:
- **Confidence ≥ 0.6** (haute confiance)
- **Type**: `preference` (stocké dans ChromaDB)
- **Limit**: Top 5 préférences les plus pertinentes

**Format d'injection**:
```
### Préférences actives
- topic: preference_text
- topic: preference_text
...
```

### 3. Temporal Weighting

Système de pondération temporelle pour booster la pertinence des résultats RAG:

**Freshness boost** (basé sur l'âge):
- Items < 7 jours: **+30%** (boost 1.3x)
- Items < 30 jours: **+15%** (boost 1.15x)
- Items > 30 jours: aucun boost

**Usage boost** (basé sur la fréquence):
- +2% par utilisation, **max +20%**
- Formule: `1.0 + min(0.2, usage_count * 0.02)`

**Score final**:
```python
boosted_score = original_score × freshness_boost × usage_boost
```

### 4. Construction du contexte RAG

Le contexte mémoire est construit en 3 étapes:

1. **Préférences actives** (cache, haute confiance)
2. **Recherche vectorielle** (concepts/faits liés à la requête)
3. **Pondération temporelle** (boost items récents/fréquents)

**Exemple de contexte généré**:
```markdown
### Préférences actives
- programmation: préfère Python pour le scripting
- documentation: aime les exemples de code concrets

### Connaissances pertinentes
- Introduction à FastAPI (1ère mention: 5 oct, 3 fois)
- Configuration Uvicorn (abordé le 8 oct à 14h32)
- Tests pytest avec fixtures (1ère mention: 3 oct, 5 fois)
```

## API publique

### `build_memory_context(session_id, last_user_message, top_k=5) → str`

Construit le contexte mémoire pour une requête utilisateur.

**Paramètres**:
- `session_id` (str): ID de la session active
- `last_user_message` (str): Dernier message utilisateur
- `top_k` (int): Nombre maximum de résultats à retourner (défaut: 5)

**Retour**:
- Contexte formaté en Markdown avec sections (préférences + connaissances)
- Chaîne vide si aucun résultat pertinent

### `invalidate_preferences_cache(user_id: str) → None`

Invalide le cache préférences pour un utilisateur spécifique.

**Utilisation**: Appelée après mise à jour des préférences (analyse mémoire, jardinage) pour forcer le rechargement depuis ChromaDB.

## Configuration

**Variables d'environnement**:
- `EMERGENCE_KNOWLEDGE_COLLECTION`: Nom de la collection ChromaDB (défaut: `emergence_knowledge`)

**Paramètres internes**:
- `_cache_ttl`: 5 minutes (non configurable)
- `preference_confidence_threshold`: 0.6 (non configurable)
- `max_preferences`: 5 (non configurable)

## Intégration

### Avec ChatService

```python
from backend.features.chat.memory_ctx import MemoryContextBuilder

memory_builder = MemoryContextBuilder(
    session_manager=session_manager,
    vector_service=vector_service
)

# Construire contexte
context = await memory_builder.build_memory_context(
    session_id="session_123",
    last_user_message="Comment configurer FastAPI?",
    top_k=5
)

# Invalider cache après mise à jour préférences
memory_builder.invalidate_preferences_cache(user_id="user_456")
```

### Avec MemoryAnalyzer

Le `MemoryAnalyzer` invalide automatiquement le cache après extraction/sauvegarde de nouvelles préférences.

## Métriques et monitoring

**Métriques Prometheus disponibles**:
```
memory_cache_operations_total{operation="hit", type="preferences"}
memory_cache_operations_total{operation="miss", type="preferences"}
```

**Logs structurés**:
- `[Cache HIT]` - Préférences servies depuis le cache (avec âge)
- `[Cache MISS]` - Fetch ChromaDB nécessaire
- `[Cache GC]` - Nettoyage entrées expirées

## Performance et optimisation

### Benchmarks P2.1

| Opération | Latence | Notes |
|-----------|---------|-------|
| Cache HIT | ~2ms | 80% des requêtes après warmup |
| Cache MISS | ~35ms | Requête ChromaDB + indexation |
| Recherche vectorielle | ~50ms | Top 5 résultats avec filtres |
| Temporal weighting | <1ms | Calcul en mémoire |

### Recommandations

1. **Warmup**: Le cache atteint son efficacité maximale après 2-3 messages par utilisateur
2. **Invalidation**: Utiliser `invalidate_preferences_cache()` uniquement après modifications réelles (éviter invalidations excessives)
3. **TTL**: 5 minutes est optimal pour équilibrer fraîcheur et performance

## Limitations connues

1. **Cache global**: Pas de limite de taille (GC uniquement sur TTL)
2. **Préférences statiques**: Les préférences changent rarement mais sont rechargées toutes les 5 minutes
3. **Pas de warm-up proactif**: Le premier message d'un utilisateur subit toujours un MISS

## Roadmap

- **P2.2**: Warm-up proactif au début de session
- **P2.3**: Cache distribué (Redis) pour déploiement multi-instances
- **P3.0**: Adaptive TTL basé sur la fréquence de modification des préférences

## Références

- [Memory Analyzer](memory.md) - Extraction et sauvegarde des préférences
- [VectorService](../architecture/10-Components.md#vectorservice) - Recherche vectorielle ChromaDB
- [Monitoring Guide](../MONITORING_GUIDE.md) - Métriques Prometheus

## Changelog

### V1.1 (P2.1) - 2025-10-11
- Ajout cache in-memory préférences (TTL 5min)
- Métriques Prometheus cache operations
- Temporal weighting (freshness + usage boost)
- Enrichissement format temporal hints

### V1.0 - 2025-09-15
- Implémentation initiale MemoryContextBuilder
- Injection préférences actives (confidence >0.6)
- Recherche vectorielle ChromaDB
