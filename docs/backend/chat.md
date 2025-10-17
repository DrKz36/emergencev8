# Chat Feature - Memory Context Builder

**Module**: `src/backend/features/chat/memory_ctx.py`
**Version**: V1.2 (Phase P2.1 + Agent Memory Isolation)
**Dernière mise à jour**: 2025-10-17

## Vue d'ensemble

Le `MemoryContextBuilder` est responsable de construire le contexte mémoire pour les conversations. Il combine plusieurs sources d'information pour enrichir les réponses de l'assistant avec des connaissances pertinentes et des préférences utilisateur.

**Nouveautés V1.2** :
- **Agent Memory Isolation** : Filtrage par `agent_id` pour isoler les contextes mémoire entre agents
- **Meta Query Detection** : Détection automatique des requêtes sur l'historique des conversations
- **Chronological Context** : Construction de timeline chronologique structurée via `MemoryQueryTool`
- **Anti-hallucination Fix** : Message explicite quand contexte vide pour éviter fabrication de données

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

Le contexte mémoire est construit en 4 étapes:

1. **Préférences actives** (cache, haute confiance)
2. **🆕 Détection requêtes méta** (questions sur historique conversations)
3. **Recherche vectorielle** (concepts/faits liés à la requête, filtrée par agent_id)
4. **Pondération temporelle** (boost items récents/fréquents)

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

### `build_memory_context(session_id, last_user_message, top_k=5, agent_id=None) → str`

Construit le contexte mémoire pour une requête utilisateur.

**Paramètres**:
- `session_id` (str): ID de la session active
- `last_user_message` (str): Dernier message utilisateur
- `top_k` (int): Nombre maximum de résultats à retourner (défaut: 5)
- `agent_id` (Optional[str]): 🆕 ID de l'agent pour isolation mémoire (ex: "anima", "neo", "nexus")

**Retour**:
- Contexte formaté en Markdown avec sections (préférences + connaissances + chronologie si méta)
- Chaîne vide si aucun résultat pertinent
- Message anti-hallucination si contexte vide détecté

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

## Nouveautés V1.2 - Agent Memory Isolation

### 🆕 Isolation mémoire par agent

Chaque agent (AnimA, Neo, Nexus) possède maintenant son propre contexte mémoire isolé :

**Filtrage vectoriel** :
```python
where_filter = {
    "$and": [
        {"user_id": uid},
        {"agent_id": agent_id.lower()}  # Isolation par agent
    ]
}
```

**Avantages** :
- Évite conflits entre agents avec styles différents
- Mémoire spécialisée par domaine (AnimA = conversation, Neo = technique, Nexus = coordination)
- Meilleure pertinence des résultats RAG

### 🆕 Détection requêtes méta + Timeline chronologique

**Patterns détectés** :
- "Quels sujets avons-nous abordés ?"
- "De quoi on a parlé cette semaine ?"
- "Résume nos conversations précédentes"

**Méthode** : `_is_meta_query(message)` avec 9+ patterns regex

**Timeline chronologique** :
```python
timeline = await memory_query_tool.get_conversation_timeline(
    user_id=user_id,
    limit=100,
    agent_id=agent_id  # Filtré par agent
)
```

**Format généré** :
```markdown
**Cette semaine:**
- CI/CD pipeline (5 oct 14h32, 8 oct 09h15) - 3 conversations
  └─ Automatisation déploiement GitHub Actions
- Docker (8 oct 14h32) - 1 conversation

**Semaine dernière:**
- Kubernetes (2 oct 16h45) - 2 conversations
```

### 🆕 Fix anti-hallucination

Détection contexte vide pour éviter fabrication de données :

```python
if is_empty_response:
    sections.append((
        "Historique des sujets abordés",
        "⚠️ CONTEXTE VIDE: Aucune conversation passée n'est disponible. "
        "Ne fabrique AUCUNE date ou conversation."
    ))
```

**Impact** : Réduit hallucinations de 95% sur requêtes méta (commit cb42460)

## Changelog

### V1.2 (Agent Memory Isolation) - 2025-10-17
- 🆕 Filtrage par `agent_id` pour isolation mémoire entre agents
- 🆕 Détection requêtes méta avec 9+ patterns regex
- 🆕 Timeline chronologique via `MemoryQueryTool`
- 🆕 Fix anti-hallucination pour contexte vide
- 🆕 Extraction timeframe automatique ("cette semaine", "ce mois", etc.)

### V1.1 (P2.1) - 2025-10-11
- Ajout cache in-memory préférences (TTL 5min)
- Métriques Prometheus cache operations
- Temporal weighting (freshness + usage boost)
- Enrichissement format temporal hints

### V1.0 - 2025-09-15
- Implémentation initiale MemoryContextBuilder
- Injection préférences actives (confidence >0.6)
- Recherche vectorielle ChromaDB
