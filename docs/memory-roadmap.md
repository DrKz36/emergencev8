# Memory Roadmap — Reference

## Contexte

Ce document synthétise l'état actuel et la trajectoire de la mémoire d'Emergence (STM, LTM et composants conceptuels), en se basant sur l'audit précédent. Il sert de référence rapide pour prioriser les travaux, partager les arbitrages techniques et suivre l'avancement.

## Diagnostic

### Forces existantes
- **SessionManager** conserve l'historique court terme et déclenche l'analyse sémantique via `MemoryAnalyzer` lors de la persistance.
- **MemoryGardener** relit les sessions, extrait concepts et faits « mot-code », puis les vectorise dans le magasin de connaissances.
- Les réponses agents injectent déjà résumé STM + faits LTM dans le prompt et exposent des évènements WebSocket (`ws:memory_banner`, `ws:analysis_status`).

### Limites identifiées
- L'analyse et la vectorisation sont déclenchées dans la boucle WS, ce qui peut bloquer l'event loop.
- `_decay_knowledge` ne met pas réellement en œuvre d'oubli pondéré ni de purge.
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
   - Exposer une route REST permettant de reconstituer la STM et l'injecter côté SessionManager.
   - Injecter l'historique restauré dans le flux UI immédiatement après handshake.

### P1 — Hors boucle WS & enrichissement conceptuel
- Déporter `MemoryAnalyzer` et `MemoryGardener` dans une file de tâches (worker/scheduler) pour éviter de bloquer l'event loop.
- Étendre l'extraction de faits (préférences, projets, décisions) via règles ou LLM et les vectoriser.
- Implémenter un mécanisme d'oubli (timestamp + purge/pénalisation périodique).

### P2 — Réactivité proactive & UX
- Maintenir un compteur de vivacité par concept et déclencher des évènements `ws:proactive_hint` lorsque des seuils sont franchis.
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
| Mécanisme d'oubli | À implémenter (P1) | ⏳ à faire |
| Proactivité concepts | Compteurs + événements à concevoir (P2) | ⏳ à faire |

## Prochaines étapes immédiates
- Compléter la synchronisation STM côté backend (hydrater `SessionManager` avec l'historique restauré).
- Déporter la vectorisation dans une tâche asynchrone dédiée (ex. `asyncio.to_thread` ou worker externe).
- Étendre `MemoryGardener` pour analyser préférences/intentions en plus des `mot-code`.

---
Dernière mise à jour : générée automatiquement par l'agent suite aux travaux du __2025-09-19__.
