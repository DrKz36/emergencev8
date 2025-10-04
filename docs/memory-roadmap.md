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

### P1 — Hors boucle WS & enrichissement conceptuel
- Déporter `MemoryAnalyzer` et `MemoryGardener` dans une file de tâches (worker/scheduler) pour éviter de bloquer l'event loop.
- Étendre l'extraction de faits (préférences explicites, intentions, projets) via pipeline hybride règles + LLM, puis vectoriser dans la collection dédiée du store mémoire.
- [FAIT] Mécanisme d'oubli par vitalité (décroissance périodique + purge sous seuil).

### P2 — Réactivité proactive & UX
- Maintenir un compteur de vivacité par concept et déclencher des événements `ws:proactive_hint` lorsque des seuils sont franchis.
- Côté UI, afficher un bandeau ou un bouton contextuel pour rappeler un souvenir ou proposer une action.
- Envoyer `thread_id` au endpoint `/api/memory/tend-garden` pour éviter les consolidations globales.

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
- [FAIT] Synchronisation STM côté backend (hydratation `SessionManager` + push `ws:session_restored`).
- [FAIT] Vectorisation déportée via tâche asynchrone (`asyncio.to_thread`).
- [FAIT] Décroissance vitalité + purge via `MemoryGardener._decay_knowledge` (journalisation métriques).
- [FAIT] Calibrage vitalite + export metriques (events vitality_*, age_days, bucket_counts) + overrides MEMORY_DECAY_*.
- [VALIDÉ] Extension `MemoryGardener` pour analyser préférences et intentions en plus des `mot-code` (voir la spécification détaillée ci-dessous).

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
Derniere mise a jour : texte actualise automatiquement suite aux travaux du __2025-09-20__.
