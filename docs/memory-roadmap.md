# Memory Roadmap — Reference

## Contexte

Ce document synthétise l'état actuel et la trajectoire de la mémoire d'Emergence (STM, LTM et composants conceptuels), en se basant sur l'audit précédent. Il sert de référence rapide pour prioriser les travaux, partager les arbitrages techniques et suivre l'avancement.

## Diagnostic

### Forces existantes
- **SessionManager** conserve l'historique court terme et déclenche l'analyse sémantique via `MemoryAnalyzer` lors de la persistance.
- **MemoryGardener** relit les sessions, extrait concepts et faits « mot-code », puis les vectorise dans le magasin de connaissances.
- **Vitalité des souvenirs** : le jardinier applique un score de vitalité (decay périodique + boost à la consultation) et purge les entrées passées sous le seuil minimal.
- Les réponses agents injectent déjà résumé STM + faits LTM dans le prompt et exposent des événements WebSocket (`ws:memory_banner`, `ws:analysis_status`).

### Limites identifiées
- L'analyse et la vectorisation sont déclenchées dans la boucle WS, ce qui peut bloquer l'event loop.
- (RESOLU 2025-09-20) Seuils de vitalite et reporting recalibres : base=0.03, stale=14j, archive=45j, nouvelles metriques (buckets, percentiles).
- Les « faits » se limitent aux `mot-code`; aucun suivi de préférences, objectifs ou décisions récurrentes.
- L'UI n'enregistre pas systématiquement les messages utilisateurs et ne recharge pas la STM depuis la base lors d'une reconnexion.
- Aucun mécanisme proactif pour signaler des concepts récurrents ou déclencher des suggestions.

## Feuille de route

### P0 — Alignement persistance & cross-device
1. **Persistance côté client**
   - Envoyer chaque message utilisateur via `POST /api/threads/{id}/messages` (fait côté frontend).
   - Continuer de persister les messages assistants en fallback lorsque le backend ne l'a pas déjà fait.
2. **Restauration à la connexion**
   - Charger la session depuis la base lors du handshake WS si elle n'est pas active (implémenté côté backend).
   - Alignement `session_id ↔ thread_id` côté UI (le `sessionId` WS est désormais le `threadId`).
3. **Étapes suivantes (P0 restant)**
   - [FAIT] Route REST `/api/memory/sync-stm` pour reconstituer la STM et hydrater SessionManager.
   - [FAIT] Injection de l'historique restauré dans le flux UI (`ws:session_restored`).

### P1 — Hors boucle WS & enrichissement conceptuel ✅ COMPLÉTÉ (2025-10-09)
- ✅ **P1.1 - Déportation asynchrone** : `MemoryTaskQueue` avec workers asyncio pour éviter blocage event loop WebSocket
  - `task_queue.py` (195 lignes) : file asyncio.Queue avec 2 workers background
  - `analyze_session_async()` non-bloquante dans `MemoryAnalyzer`
  - Lifecycle startup/shutdown dans `main.py`
  - Tests unitaires : 5/5 passent
- ✅ **P1.2 - Extension extraction de faits** : Pipeline hybride préférences/intentions/contraintes
  - `preference_extractor.py` (273 lignes) : `PreferenceExtractor` modulaire
  - Filtrage lexical (réduction >70% appels LLM) + classification LLM (gpt-4o-mini via ChatService)
  - Normalisation : topic, action, timeframe, sentiment, confidence, entities
  - Déduplication par `(user_sub, topic, type)`
  - Tests unitaires : 8/8 passent
- ✅ **P1.3 - Instrumentation métriques** : 5 nouvelles métriques Prometheus préférences
  - `memory_preferences_extracted_total{type}`
  - `memory_preferences_confidence` (histogram)
  - `memory_preferences_extraction_duration_seconds` (histogram)
  - `memory_preferences_lexical_filtered_total`
  - `memory_preferences_llm_calls_total`
- ✅ **Métriques cache** (Phase 3 existantes) : hits, misses, size
- ✅ **Commit** : `588c5dc` feat(P1): enrichissement mémoire (862 lignes, 6 fichiers)
- [FAIT] Mécanisme d'oubli par vitalité (décroissance périodique + purge sous seuil).

### P2 — Performance & Réactivité proactive ✅ COMPLÉTÉ (2025-10-10)
- ✅ **P2 Sprint 1 - Optimisations Performance** : -71% latence contexte LTM
  - ✅ Fix critique coûts Gemini (count_tokens avant/après génération)
  - ✅ Configuration HNSW ChromaDB optimisée (M=16, cosine) → -82.5% latence queries
  - ✅ Cache in-memory préférences (5min TTL) → 100% hit rate
  - ✅ Tests performance : 5/5 passent (benchmarks latence, cache, batch)
  - ✅ Commit : `8205e3b` perf(P2.1): fix Gemini costs + HNSW optimization
- ✅ **P2 Sprint 2 - Proactive Hints Backend** : Suggestions contextuelles opérationnelles
  - ✅ ProactiveHintEngine créé (192 lignes, 100% typed)
  - ✅ ConceptTracker : compteur récurrence concepts (trigger at 3 mentions)
  - ✅ Intégration ChatService complète (4 modifications)
    - Initialisation hint_engine dans __init__
    - Méthode _emit_proactive_hints_if_any() (44 lignes)
    - Appel asyncio.create_task après réponse agent
  - ✅ Event WebSocket `ws:proactive_hint` implémenté
  - ✅ 2 métriques Prometheus (hints_generated, hints_relevance)
  - ✅ Tests : 16/16 passants (0.10s)
  - ✅ Commits : `5ce75ce` + `7fd4674` feat(P2 Sprint2): ProactiveHints backend
- ✅ **Gains cumulés P2** :
  - Performance : -71% latence (120ms → 35ms), -50% queries, 100% cache hit rate
  - Features : 3-5 hints/session, système proactif vs 100% réactif
  - Qualité : 21 nouveaux tests (tous passants), 0 erreurs mypy
- 🔄 **P2 Sprint 3 (À FAIRE)** : Frontend UI + Dashboard
  - [ ] Composant ProactiveHintsUI (affichage banners, actions)
  - [ ] Dashboard mémoire utilisateur
  - [ ] Tests E2E Playwright

### P3 — Gouvernance & Observabilité
- Journaliser la durée des consolidations et la taille des lots injectés pour suivre le coût / perf.
- Ajouter des tests d'intégration couvrant `memory.tend-garden`, `memory.clear` et la cohérence thread ↔ session.

## Décisions techniques

| Sujet | Décision | Statut |
|-------|----------|--------|
| Vector store | Ajout d'un backend Qdrant optionnel (HTTP) avec fallback automatique sur Chroma | ✅ livré ici |
| Persist. messages utilisateur | Envoi systématique via `api.appendMessage` dans le frontend | ✅ livré ici |
| Restauration session WS | `ConnectionManager` charge la session depuis la BDD avant de créer une nouvelle STM | ✅ livré ici |
| Mécanisme d'oubli | Score de vitalité + decay + purge via MemoryGardener | ✅ livré ici |
| Calibrage vitalite | Base=0.03, stale=14j, archive=45j, min=0.12 + metrics JSON (vitality_before/after, age_days, buckets) | livre ici |
| Proactivité concepts | Compteurs + événements à concevoir (P2) | ⏳ à faire |

## Prochaines étapes immédiates
- ✅ [FAIT - P0] Synchronisation STM côté backend (hydratation `SessionManager` + push `ws:session_restored`)
- ✅ [FAIT - P0] Vectorisation déportée via tâche asynchrone (`asyncio.to_thread`)
- ✅ [FAIT - P0] Décroissance vitalité + purge via `MemoryGardener._decay_knowledge`
- ✅ [FAIT - P0] Calibrage vitalite + export metriques (vitality_*, age_days, bucket_counts)
- ✅ [FAIT - P1 complété 2025-10-09] Extension extraction préférences/intentions
  - Pipeline hybride : filtrage lexical + classification LLM + normalisation
  - Déportation analyses via `MemoryTaskQueue` (workers asyncio)
  - 8 nouvelles métriques Prometheus (5 préférences + 3 cache)
  - Tests : 15/15 passent
- ✅ [FAIT - P2 Sprint 1 complété 2025-10-10] Optimisations performance
  - Fix coûts Gemini + HNSW ChromaDB optimisé + cache préférences
  - Gains : -71% latence, 100% cache hit rate, -50% queries
  - Tests : 5/5 performance benchmarks
- ✅ [FAIT - P2 Sprint 2 complété 2025-10-10] Réactivité proactive backend
  - ProactiveHintEngine + intégration ChatService
  - Event `ws:proactive_hint` + métriques Prometheus
  - Tests : 16/16 hints tests passants
- ⏳ [NEXT - P2 Sprint 3] Frontend UI hints proactifs + Dashboard mémoire utilisateur
- ⏳ [APRÈS P2] Gap #3 : Décision architecture hybride Sessions/Threads (migration vs maintien)

## Spécification détaillée — Extension MemoryGardener (préférences & intentions)
- [FAIT] Normalisation des cles JSON du classifieur (prevention de la localisation des champs).

### Objectif
Capturer et capitaliser les préférences explicites (goûts, contraintes, canaux favoris) ainsi que les intentions déclarées (prochaines actions, objectifs, engagements) exprimées par l'utilisateur afin d'enrichir la mémoire à long terme et d'améliorer la personnalisation des agents.

### Pipeline hybride
1. **Filtrage lexical immédiat** : détecter les phrases contenant des verbes cibles (préférer, aimer, vouloir, éviter, planifier, décider) et des formes impératives pour réduire le bruit avant appel LLM.
2. **Classification LLM ciblée** : utiliser un prompt spécialisé (modèle `gpt-4o-mini` par défaut, fallback `claude-3-haiku`) pour catégoriser chaque extrait en `preference`, `intent`, `constraint` ou `neutral`, avec score de confiance.
3. **Normalisation** : standardiser le sujet (`topic`), l'action (`action`), la temporalite (`timeframe`) et extraire les entites cles (personnes, outils, lieux) via regles Spacy, enrichies par le JSON renvoye par le LLM, avec post-traitement pour conserver les cles canoniques (`items`, `id`, `type`, etc.).

### Modèle de données et vectorisation
- Nouvelle collection `memory_preferences` (Chroma/Qdrant) avec clé composite `{user_sub, topic, type}`.
- Métadonnées stockées avec chaque vecteur :
  - `type` (`preference` | `intent` | `constraint`)
  - `topic` (chaîne normalisée)
  - `action` (verbe à l'infinitif)
  - `timeframe` (ISO 8601 si date reconnue, sinon `ongoing`)
  - `sentiment` (positif, négatif, neutre — dérivé du LLM)
  - `confidence` (float 0–1)
  - `source_message_id` + `thread_id`
  - `captured_at` (UTC ISO timestamp)
- Embedding calculé via `text-embedding-3-large` (fallback `text-embedding-004`).
- Déduplication par `(user_sub, topic, type)` avec fusion pondérée des scores de confiance.

### Intégration dans MemoryGardener
- Ajout d'une étape `extract_preference_intent(nodes: list[Message]) -> list[PreferenceRecord]` appelée après `extract_concepts` dans `garden_thread`.
- Injection des nouveaux enregistrements dans la même file de travail que les `mot-code`, en conservant la traçabilité via `MemoryEvent(preference_id=...)`.
- Publication d'un événement `ws:memory_banner` de type `preference_captured` lorsque la confiance dépasse 0,6 pour informer l'UI et permettre une confirmation utilisateur.

### Validation et instrumentation
- Corpus d'évaluation de 100 messages réels anonymisés + 50 cas synthétiques edge-cases pour mesurer précision (>0,85) et rappel (>0,75).
- Tests unitaires ciblant la déduplication et la normalisation (`tests/memory/test_preferences.py`).
- Dashboard Grafana : métriques `memory_preferences_captured_total`, `memory_preferences_confidence_bucket`.
- Revue hebdomadaire des extraits capturés (échantillon aléatoire de 20) pour ajuster les règles lexicales et le prompt LLM.

---
**Derniere mise a jour** : 2025-10-10 (Phase P2 Sprints 1+2 complétés - performance + hints proactifs backend)

**Historique** :
- 2025-10-10 : Phase P2 Sprint 1+2 complétés
  - Sprint 1 : Optimisations performance (-71% latence, 100% cache hit rate, fix coûts Gemini)
  - Sprint 2 : ProactiveHintEngine backend + intégration ChatService (16 tests)
  - Documentation : 3 nouveaux docs status (P2_COMPLETION_FINAL_STATUS.md + 2 sprints)
- 2025-10-09 : Phase P1 complétée (MemoryTaskQueue, PreferenceExtractor, 8 métriques Prometheus)
- 2025-09-20 : Calibrage vitalité + métriques decay
- Phase P0 : Persistance cross-device + restauration STM

**Références Phase P2** :
- [P2_COMPLETION_FINAL_STATUS.md](validation/P2_COMPLETION_FINAL_STATUS.md) - Résumé complet
- [P2_SPRINT1_COMPLETION_STATUS.md](validation/P2_SPRINT1_COMPLETION_STATUS.md) - Sprint 1 détails
- [P2_SPRINT2_PROACTIVE_HINTS_STATUS.md](validation/P2_SPRINT2_PROACTIVE_HINTS_STATUS.md) - Sprint 2 détails
- [MEMORY_P2_PERFORMANCE_PLAN.md](optimizations/MEMORY_P2_PERFORMANCE_PLAN.md) - Plan P2 original
