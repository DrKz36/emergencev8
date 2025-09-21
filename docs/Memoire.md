# Mémoire progressive — ÉMERGENCE V8

## 0. Table des matières cible
- 1. Objectifs & portée
- 2. Architecture technique
- 3. Flux opérationnels
- 4. Observabilité & tests
- 5. UX & actions utilisateur
- 6. Étapes immédiates
- 7. Parcours utilisateur détaillés
- 8. Assets visuels & schémas à produire
- 9. Checklist QA manuelle

## 1. Objectifs & portée
- Assurer une **mémoire courte terme (STM)** pour résumer chaque session et réduire le contexte envoyé aux modèles.
- Maintenir une **mémoire long terme (LTM)** partageable entre sessions (faits, concepts, entités) et exploitable par le RAG.
- Offrir à l’utilisateur le contrôle : analyse à la demande, purge ciblée, visibilité sur les données injectées.

## 2. Architecture technique

### Backend
- **`MemoryGardener`** (features/memory/gardener.py)
  - Agrège l’historique des threads (global ou filtré par `thread_id`).
  - Détermine si la consolidation doit être persistée (`persist=True/False`).
  - Publie les statuts via `ConnectionManager` (`ws:analysis_status`).
- **`MemoryAnalyzer`** (features/memory/analyzer.py)
  - Appelle les LLM (ordre Google → Anthropic → OpenAI) pour produire :
    - Résumé STM (texte court)
    - Concepts / faits clés
    - Entités nommées
  - Persiste dans SQLite (`memory_items`) et déclenche la vectorisation via `VectorService`.
- **`VectorService`**
  - Stocke les embeddings mémoire dans la collection `emergence_knowledge` (partagée avec les documents).
  - Surveille la corruption SQLite → backup + reset auto (`vector_store_backup_*`).
- **Endpoints REST**
  - `POST /api/memory/tend-garden` : lance une consolidation (option `thread_id`, `mode`).
  - `GET /api/memory/tend-garden` : renvoie l’état consolidé (`summaries`, `facts`, compteurs LTM).
  - `POST /api/memory/clear` : purge STM puis LTM (scope global ou thread).

### Frontend
- **`ChatModule`**
  - Expose les actions `tendMemory()` / `clearMemory()` via l’UI.
  - Écoute `ws:analysis_status` pour afficher les loaders/badges.
- **`ChatUI`**
  - Affiche le bandeau mémoire (`ws:memory_banner`) : état STM/LTM, modèle utilisé, compteur d’items injectés.
  - Propose les boutons `Analyser` (POST) et `Clear` (POST clear) + toasts de confirmation.
- **State Manager**
  - Stocke `state.memory.lastRunAt`, `state.memory.status`, `state.memory.items` pour informer l’utilisateur.

## 3. Flux opérationnels
1. **Analyse globale**
   - Trigger : clic `Analyser` sans `thread_id`.
   - `MemoryGardener` récupère toutes les sessions actives, passe `persist=True`.
   - Résultats persistés + vectorisés, diffusion `ws:analysis_status(status="done")`.
2. **Analyse ciblée (thread)**
   - Trigger : action depuis un thread → `thread_id` envoyé.
   - `persist=False` possible (lecture seule) ou `persist=True` pour enregistrement.
   - Résumé disponible immédiatement via `GET /api/memory/tend-garden`.
3. **Clear mémoire**
   - `POST /api/memory/clear` → supprime d’abord STM (`memory_sessions`), puis LTM filtrée (`memory_items` + embeddings Chroma).
   - Diffusion `ws:memory_banner` indiquant mémoire vide.

## 4. Observabilité & tests
- Logs : `memory:garden:start`, `memory:garden:done`, `memory:clear`.
- Tests recommandés :
  - `tests/run_all.ps1` (vérifie `/api/memory/tend-garden`).
  - Ajout à prévoir : scénario dédié `tests/test_memory_clear.ps1` (statut TODO).
- Métriques front : affichage du modèle, TTFB mémoire, nombre d’items injectés.

## 5. UX & actions utilisateur
- **Badges mémoire** : indiquer clairement si STM/LTM ont été injectées dans la dernière réponse agent.
- **Journal** : prévoir un panneau listant les dernières consolidations (`lastRunAt`, `thread_id`, `model`).
- **CTA Clear** : confirmer avant purge (modal).

## 6. Étapes immédiates
1. Ajouter une remontée UI lorsqu’une consolidation échoue (toast + bouton retry).
2. Exposer dans l’UI l’historique renvoyé par `GET /api/memory/tend-garden`.
3. Documenter un guide QA (checklist) pour valider la cohérence STM vs LTM après `memory:clear`.
4. Script de test `tests/test_memory_clear.ps1` (à créer) pour couvrir la purge (STM + LTM + embeddings).

## 7. Parcours utilisateur détaillés
### 7.1. Consolidation globale
- **Acteurs** : opérateur support / membre produit.
- **Objectif** : déclencher une consolidation complète pour rafraîchir la mémoire partagée.
- **Étapes** :
  1. Ouvrir l’espace conversationnel sans filtre thread.
  2. Cliquer sur le bouton `Analyser` dans le bandeau mémoire.
  3. Suivre le loader et les statuts diffusés via `ws:analysis_status`.
  4. Consulter la synthèse STM et les faits clés affichés dans le panneau mémoire.
- **Points de vigilance** : vérifier la cohérence du compteur d’items et la présence d’un toast succès.
- **Captures à intégrer** :
  - ![Capture bandeau consolidation](assets/memoire/bandeau-analyse.png)
  - ![Capture toast succès analyse](assets/memoire/toast-analyse.png)

### 7.2. Analyse ciblée par thread
- **Acteurs** : agent conversationnel, analyste QA.
- **Objectif** : auditer la mémoire pour un thread spécifique sans polluer la LTM.
- **Étapes** :
  1. Depuis un thread, ouvrir le panneau mémoire contextuel.
  2. Lancer `Analyser` avec `thread_id` (option `persist=False` par défaut).
  3. Lire le résumé retourné immédiatement.
  4. Choisir de persister ou non la consolidation selon la pertinence détectée.
- **Points de vigilance** :
  - Statut `lecture seule` clairement indiqué si `persist=False`.
  - Présence d’un historique horodaté `lastRunAt`.
- **Captures à intégrer** :
  - ![Capture panneau thread](assets/memoire/panneau-thread.png)
  - ![Capture choix persistance](assets/memoire/option-persist.png)

### 7.3. Purge STM + LTM
- **Acteurs** : admin projet, référent sécurité.
- **Objectif** : supprimer toutes les traces de mémoire (session + long terme) pour conformité.
- **Étapes** :
  1. Cliquer sur `Clear` dans le bandeau mémoire.
  2. Valider la modal de confirmation détaillant l’impact.
  3. Vérifier le retour `memory:clear` côté backend (journalisation) et la notification UI.
  4. Confirmer que le bandeau indique une mémoire vide et que les listes STM/LTM sont purgées.
- **Points de vigilance** : l’ordre STM → LTM → embeddings doit être respecté, et la modal doit résumer les effets.
- **Captures à intégrer** :
  - ![Capture modal clear](assets/memoire/modal-clear.png)
  - ![Capture bandeau vide](assets/memoire/bandeau-vide.png)

### 7.4. Gestion des erreurs de consolidation
- **Acteurs** : utilisateur final, équipe SRE.
- **Objectif** : identifier et corriger les consolidations échouées.
- **Étapes** :
  1. Simuler une indisponibilité LLM (forcer un timeout ou utiliser un environnement de test).
  2. Déclencher `Analyser` et observer l’état `error` dans le bandeau.
  3. Utiliser le bouton `Retry` proposé dans le toast d’échec.
  4. Vérifier la remontée correspondante dans les logs `memory:garden:done` avec statut erreur.
- **Points de vigilance** : message d’erreur doit guider l’utilisateur (inclure ID de corrélation) et ne pas exposer de données sensibles.
- **Captures à intégrer** :
  - ![Capture toast erreur](assets/memoire/toast-erreur.png)
  - ![Capture logs erreur](assets/memoire/logs-erreur.png)

## 8. Assets visuels & schémas à produire
- **Captures UI** : bandeau mémoire (états `idle`, `loading`, `error`, `empty`), modal Clear, panneau thread, toasts succès/erreur.
- **Schémas** :
  - Diagramme séquence `ChatUI → MemoryGardener → MemoryAnalyzer → VectorService`.
  - Schéma de flux purge STM/LTM/embeddings (ordre et webhooks associés).
- **Exports données** : anonymiser un exemple de réponse `GET /api/memory/tend-garden` pour illustrer la doc.
- **Formats recommandés** : PNG pour captures (largeur 1440px), SVG pour schémas.

## 9. Checklist QA manuelle
- [ ] Déclencher une **consolidation globale** et vérifier l’affichage du loader puis du résumé STM (capture : `assets/memoire/bandeau-analyse.png`).
- [ ] Exécuter une **analyse ciblée** avec `persist=False` et confirmer que la LTM ne change pas (capture : `assets/memoire/panneau-thread.png`).
- [ ] Lancer une **analyse ciblée persistée** (`persist=True`) et valider l’incrément du compteur d’items LTM (capture : `assets/memoire/option-persist.png`).
- [ ] Réaliser un **clear complet** et contrôler la purge STM/LTM + embeddings (captures : `assets/memoire/modal-clear.png`, `assets/memoire/bandeau-vide.png`).
- [ ] **Tester le scénario d’erreur** (LLM indisponible) et confirmer la présence du toast + bouton retry (capture : `assets/memoire/toast-erreur.png`).
- [ ] Vérifier la **cohérence des logs** `memory:garden:*` et `memory:clear` avec les actions réalisées (capture : `assets/memoire/logs-erreur.png`).
