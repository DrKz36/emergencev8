# Memory Feature - Analyzer & Hybrid Retriever

**Modules**:
- `src/backend/features/memory/analyzer.py`
- `src/backend/features/memory/hybrid_retriever.py`
- `src/backend/features/memory/gardener.py`
- `src/backend/features/memory/memory_query_tool.py`

**Version**: V3.9 (Agent Memory Isolation)
**Dernière mise à jour**: 2025-10-17

## Vue d'ensemble

Le système de mémoire ÉMERGENCE combine deux composants complémentaires:

1. **MemoryAnalyzer**: Analyse sémantique des conversations et extraction des préférences utilisateur
2. **HybridRetriever**: Recherche hybride (BM25 + vectorielle) pour améliorer la pertinence du RAG

## 1. Memory Analyzer (V3.8)

### Fonctionnalités principales

#### 1.0 Consolidation mémoire avec feedback temps réel (V3.8 - 2025-10-15)

**Nouveauté**: Le MemoryGardener envoie désormais des événements WebSocket `ws:memory_progress` pour notifier l'avancement en temps réel.

**Événements émis**:
- **Phase in_progress**: Notification session par session
  ```json
  {
    "type": "ws:memory_progress",
    "payload": {
      "session_id": "session_123",
      "current": 2,
      "total": 5,
      "phase": "extracting_concepts",
      "status": "in_progress"
    }
  }
  ```

- **Phase completed**: Résumé final de la consolidation
  ```json
  {
    "type": "ws:memory_progress",
    "payload": {
      "session_id": "session_123",
      "current": 5,
      "total": 5,
      "phase": "completed",
      "status": "completed",
      "consolidated_sessions": 5,
      "new_items": 23
    }
  }
  ```

**Phases disponibles**:
- `extracting_concepts`: Extraction concepts/entités/faits
- `analyzing_preferences`: Classification préférences/intentions
- `vectorizing`: Sauvegarde ChromaDB
- `completed`: Consolidation terminée

**Impact UX**:
- Barre de progression affichée dans le frontend (Centre Mémoire)
- Labels traduits : "Extraction des concepts... (2/5 sessions)"
- Message final : "✓ Consolidation terminée : 5 sessions, 23 nouveaux items"
- Durée estimée affichée : 30s-2min selon volume

**Implémentation**: Voir [gardener.py:572-695](../../src/backend/features/memory/gardener.py#L572-L695)

#### 1.1 Analyse sémantique multi-provider

Extraction automatique de:
- **Summary**: Résumé concis de la conversation (2-3 phrases)
- **Concepts**: 3-5 concepts clés abordés (spécifiques, ex: "éthique de l'IA dans le diagnostic médical")
- **Entities**: Entités nommées (noms propres, lieux, titres)

**Fallback cascade** pour garantir la fiabilité:
```
neo_analysis (GPT-4o-mini, rapide)
  ↓ échec
nexus (Anthropic Claude, fiable)
  ↓ échec
anima (OpenAI GPT-4, dernière chance)
  ↓ échec
offline_analysis (heuristique, tests/dégradation)
```

**Timeout**: 30s par provider pour éviter blocages indéfinis.

#### 1.2 Extraction préférences/intentions (Phase P1)

Extraction automatique via `PreferenceExtractor`:

**Types de préférences**:
- `preference`: Préférence générale ("préfère Python pour le scripting")
- `intent`: Intention déclarée ("veut apprendre FastAPI")
- `constraint`: Contrainte/limitation ("éviter les frameworks lourds")

**Seuils de confiance**:
- Haute confiance (≥0.6): Injection automatique dans RAG
- Moyenne confiance (0.3-0.6): Sauvegardé mais non injecté
- Basse confiance (<0.3): Ignoré

**Métadonnées enrichies**:
```python
{
    "user_id": "user_123",
    "type": "preference",
    "topic": "programmation",
    "confidence": 0.85,
    "sentiment": "positive",
    "timeframe": "permanent",
    "created_at": "2025-10-11T13:45:00Z",
    "thread_id": "session_456",
    "source": "preference_extractor_v1.2"
}
```

#### 1.3 Cache analyses (TTL 1h)

**Performance optimisée**:
- Cache key: `memory_analysis:{session_id}:{history_hash}`
- TTL: 1 heure
- Éviction agressive: Garde top 50 entrées les plus récentes quand >80 entrées

**Thread-safety**:
- Utilise `asyncio.Lock` pour accès concurrent sécurisé
- Évite race conditions (Bug #3 fix)

**Métriques**:
```
memory_analysis_cache_hits_total
memory_analysis_cache_misses_total
memory_cache_size (gauge)
```

#### 1.4 Métriques Prometheus complètes

**Succès/Échecs par provider**:
```
memory_analysis_success_total{provider="neo_analysis|nexus|anima"}
memory_analysis_failure_total{provider="...", error_type="TimeoutError|..."}
```

**Latence analyses**:
```
memory_analysis_duration_seconds{provider="..."}
# Buckets: [0.5, 1.0, 2.0, 4.0, 6.0, 10.0, 15.0, 20.0, 30.0]
```

**Échecs extraction préférences (HOTFIX P1.3)**:
```
memory_preference_extraction_failures_total{reason="user_identifier_missing|extraction_error|persistence_error"}
```

### API publique

#### `analyze_session_for_concepts(session_id, history, force=False, user_id=None)`

Analyse une session complète et persiste les résultats dans la base de données.

**Paramètres**:
- `session_id` (str): ID session à analyser
- `history` (List[Dict]): Historique messages (format: `[{"role": "user|assistant", "content": "..."}]`)
- `force` (bool): Force nouvelle analyse même si déjà analysée
- `user_id` (str, optionnel): ID utilisateur pour extraction préférences

**Retour**: Dict avec `summary`, `concepts`, `entities`

**Side-effects**:
- Sauvegarde dans DB (table `sessions`)
- Extraction et sauvegarde préférences dans ChromaDB
- Invalidation cache préférences (MemoryContextBuilder)

#### `analyze_history(session_id, history)`

Analyse un historique sans persister dans la DB (mode thread-only).

**Usage**: Analyses ponctuelles, tests, ou threads temporaires.

#### `analyze_session_async(session_id, force=False, callback=None)`

Version non-bloquante utilisant la `MemoryTaskQueue`.

**Usage**: Enqueue l'analyse pour exécution asynchrone en arrière-plan.

### Configuration

**Variables d'environnement**:
- `MEMORY_ANALYZER_ALLOW_OFFLINE`: Active mode offline (fallback heuristique)
- `PYTEST_CURRENT_TEST`: Détection automatique mode test (offline auto)
- `EMERGENCE_KNOWLEDGE_COLLECTION`: Collection ChromaDB (défaut: `emergence_knowledge`)

**Paramètres internes**:
- Cache TTL: 1 heure
- Cache max size: 100 entrées
- Cache eviction threshold: 80 entrées
- Timeout LLM: 30 secondes

### Intégration

```python
from backend.features.memory.analyzer import MemoryAnalyzer

# Initialisation
analyzer = MemoryAnalyzer(
    db_manager=db_manager,
    chat_service=chat_service,
    enable_offline_mode=False
)

# Analyse avec extraction préférences
result = await analyzer.analyze_session_for_concepts(
    session_id="session_123",
    history=[
        {"role": "user", "content": "J'aime Python pour le scripting"},
        {"role": "assistant", "content": "Python est excellent pour ça!"}
    ],
    force=False,
    user_id="user_456"  # Important pour extraction préférences
)

# Résultat
{
    "summary": "Discussion sur Python pour le scripting",
    "concepts": ["Python", "scripting", "langage de programmation"],
    "entities": ["Python"]
}
```

---

## 2. Hybrid Retriever (V1.0)

### Fonctionnalités principales

#### 2.1 Scoring hybride BM25 + Vectoriel

**Approche**: Combine recherche lexicale (BM25) et sémantique (embeddings) pour améliorer la pertinence.

**Formule de fusion**:
```python
hybrid_score = (1 - alpha) × bm25_score + alpha × vector_score
```

**Paramètres par défaut**:
- `alpha = 0.5`: Équilibre 50/50 entre BM25 et vectoriel
- `score_threshold = 0.0`: Pas de filtrage par défaut
- `top_k = 5`: Retourne top 5 résultats

#### 2.2 BM25 Scorer (Okapi BM25)

Algorithme de ranking lexical basé sur TF-IDF amélioré.

**Formule BM25**:
```
score(D, Q) = Σ IDF(qi) · (f(qi, D) · (k1 + 1)) / (f(qi, D) + k1 · (1 - b + b · |D| / avgdl))
```

**Paramètres**:
- `k1 = 1.5`: Contrôle saturation du term frequency
- `b = 0.75`: Contrôle importance de la longueur du document

**Avantages BM25**:
- Capture les matchs lexicaux exacts (mots-clés)
- Robuste aux synonymes et variations orthographiques
- Rapide (pas d'embedding nécessaire)

#### 2.3 Fusion des scores

**Processus**:
1. Normalisation scores BM25 dans [0, 1]
2. Normalisation scores vectoriels (distance → similarité)
3. Pondération selon `alpha`
4. Filtrage par `score_threshold`
5. Tri par score décroissant
6. Retour top_k résultats

**Détails par résultat**:
```python
{
    "text": "contenu du document",
    "score": 0.85,          # Score hybride final
    "bm25_score": 0.78,     # Composante BM25
    "vector_score": 0.92,   # Composante vectorielle
    "metadata": {...}       # Métadonnées du document
}
```

#### 2.4 Métriques RAG

Tracking automatique via `RAGMetricsTracker`:

```
rag_queries_hybrid_total{status="success|error"}
rag_results_count (histogram)
rag_avg_score (gauge)
rag_results_filtered_total{reason="below_threshold|..."}
```

### API publique

#### `hybrid_query(vector_service, collection, query_text, ...)`

Helper pour recherche hybride complète sur une collection.

**Paramètres**:
- `vector_service`: Instance VectorService
- `collection`: Collection Chroma/Qdrant
- `query_text` (str): Requête utilisateur
- `n_results` (int): Nombre de résultats (défaut: 5)
- `where_filter` (dict, optionnel): Filtres métadonnées
- `alpha` (float): Poids vectoriel (défaut: 0.5)
- `score_threshold` (float): Seuil minimum (défaut: 0.0)
- `bm25_k1` (float): Paramètre BM25 (défaut: 1.5)
- `bm25_b` (float): Paramètre BM25 (défaut: 0.75)

**Retour**: Liste de résultats hybrides avec scores détaillés

#### `HybridRetriever.retrieve(query, corpus, vector_results, ...)`

Méthode bas-niveau pour fusion scores BM25 + vectoriels.

**Usage avancé**: Permet de customiser le corpus BM25 et pré-calculer les résultats vectoriels.

### Configuration

**Tuning alpha** (poids vectoriel):
- `alpha = 0.0`: Full BM25 (lexical pur)
- `alpha = 0.5`: Équilibre (recommandé)
- `alpha = 1.0`: Full vectoriel (sémantique pur)

**Tuning score_threshold**:
- `0.0`: Pas de filtrage (retourne tous les top_k)
- `0.3-0.5`: Filtrage modéré (élimine résultats peu pertinents)
- `0.7+`: Filtrage strict (mode haute précision)

**Tuning BM25**:
- `k1 = 1.5` (standard): Bon équilibre pour la plupart des corpus
- `b = 0.75` (standard): Normalisation longueur documents

### Intégration

```python
from backend.features.memory.hybrid_retriever import hybrid_query

# Recherche hybride complète
results = hybrid_query(
    vector_service=vector_service,
    collection=knowledge_collection,
    query_text="Comment configurer FastAPI avec Uvicorn?",
    n_results=5,
    where_filter={"user_id": "user_123"},
    alpha=0.5,  # Équilibre BM25/vectoriel
    score_threshold=0.3  # Filtrage modéré
)

# Résultats
for r in results:
    print(f"Score: {r['score']:.3f} (BM25: {r['bm25_score']:.3f}, Vector: {r['vector_score']:.3f})")
    print(f"Text: {r['text'][:100]}...")
```

### Performance

**Benchmarks P1.5**:

| Opération | Latence | Notes |
|-----------|---------|-------|
| BM25 scoring | ~10ms | Corpus 100 docs |
| Vectoriel | ~50ms | ChromaDB query top 10 |
| Fusion | ~2ms | Normalisation + tri |
| **Total** | **~60ms** | Top 5 résultats hybrides |

**Trade-offs**:
- BM25 rapide mais moins sémantique
- Vectoriel plus lent mais meilleure compréhension contexte
- Hybride: meilleur compromis précision/vitesse

## Limitations connues

### MemoryAnalyzer
1. **Timeout fixe 30s**: Peut être insuffisant pour conversations très longues (>10k tokens)
2. **Pas de batch processing**: Analyse sessions une par une (pas de parallelisation)
3. **Cache non distribué**: Chaque instance a son propre cache (problème multi-instances)

### HybridRetriever
1. **Corpus full reload**: BM25 reconstruit l'index à chaque query (pas de persistence)
2. **Pas de reranking cross-encoder**: Pas de réordonnancement final (phase P2+)
3. **Alpha statique**: Pas d'adaptation dynamique selon la requête

## Roadmap

### MemoryAnalyzer
- **P2.0**: Batch processing pour analyses multiples
- **P2.1**: Cache distribué Redis pour multi-instances
- **P2.2**: Incremental analysis (analyse uniquement nouveaux messages)

### HybridRetriever
- **P2.0**: Persistence index BM25 (éviter reconstruction)
- **P2.1**: Cross-encoder reranking (LLM final pass)
- **P2.2**: Dynamic alpha tuning basé sur query type

## Références

- [Chat Feature](chat.md) - MemoryContextBuilder (utilise HybridRetriever)
- [Metrics](metrics.md) - Endpoints Prometheus pour métriques RAG
- [VectorService](../architecture/10-Components.md#vectorservice) - Recherche vectorielle
- [Monitoring Guide](../MONITORING_GUIDE.md) - Observabilité complète

## 3. Memory Query Tool (timeline agents)

**Module** : `src/backend/features/memory/memory_query_tool.py`

### 3.1 Liste des sujets discutés

**API** :
```python
list_discussed_topics(
    user_id: str,
    timeframe: str = "week",
    limit: int = 50,
    min_mention_count: int = 1,
    agent_id: Optional[str] = None  # 🆕 V3.9
)
```

**Paramètres** :
- `user_id` : Identifiant utilisateur
- `timeframe` : Période (`today`, `week`, `month`, `all`)
- `limit` : Nombre maximum de sujets
- `min_mention_count` : Nombre minimum de mentions
- `agent_id` : 🆕 **Filtrage par agent** pour isolation mémoire

**Retour** : Liste de `TopicSummary` (dates ISO, conversations, thread_ids, vitalité)

### 3.2 Timeline conversationnelle

**API** :
```python
get_conversation_timeline(
    user_id: str,
    limit: int = 120,
    agent_id: Optional[str] = None  # 🆕 V3.9
)
```

**Fonctionnement** :
- Regroupe sujets en 4 fenêtres temporelles : `this_week`, `last_week`, `this_month`, `older`
- Tri chronologique (plus récent d'abord) : `last_date` → `first_date`
- Cutoffs calculés backend (1 sem, 2 sem, 30 jours)
- 🆕 **Filtrage par agent_id** pour contexte isolé

### 3.3 Formatage naturel pour les LLMs
- `format_timeline_natural_fr(timeline)` retourne un bloc Markdown prêt pour injection dans le prompt :
  ```markdown
  ### Historique des sujets abordés

  **Cette semaine:**
  - CI/CD pipeline (5 oct 14h32, 8 oct 09h15) - 3 conversations
    └─ Automatisation déploiement GitHub Actions
  ```
- Utilisé par les agents pour répondre aux questions « qu’avons-nous abordé récemment ? ».

### 3.4 Données requises
- S’appuie sur `VectorService` et la collection `emergence_knowledge`.
- Les consolidations mémoires doivent injecter `first_date`, `last_date`, `summary`, `thread_ids`, `mention_count`.

## Changelog

### V3.9 (Agent Memory Isolation) - 2025-10-17
- 🆕 **Isolation mémoire par agent**: Filtrage `agent_id` dans `MemoryQueryTool`
- 🆕 **Timeline par agent**: `get_conversation_timeline()` et `list_discussed_topics()` supportent `agent_id`
- 🆕 **Contexte agent-specific**: Chaque agent (AnimA, Neo, Nexus) a sa propre timeline
- 🆕 **Anti-hallucination**: Message explicite quand timeline vide pour éviter fabrication

### V3.8 (UX Improvements) - 2025-10-15
- **Feedback temps réel**: Événements WebSocket `ws:memory_progress` pour suivi consolidation
- **Barre de progression frontend**: Affichage (X/Y sessions) avec phases traduites
- **UX améliorée**: Bouton renommé "Consolider mémoire" + tooltip explicatif
- **Documentation enrichie**: Tutoriel + guide technique mis à jour

### V3.7 (P1) - 2025-10-11
- Extraction préférences/intentions avec PreferenceExtractor
- Fallback cascade LLM (neo → nexus → anima)
- Cache thread-safe avec asyncio.Lock
- Métriques échecs extraction préférences (HOTFIX P1.3)

### V3.6 - 2025-09-20
- Cache analyses TTL 1h avec éviction agressive
- Timeout 30s par provider
- Métriques Prometheus succès/échecs/latence

### V1.0 (HybridRetriever) - 2025-10-05
- Implémentation BM25 + vectoriel
- Métriques RAG via RAGMetricsTracker
- Helper `hybrid_query()` pour usage simplifié
