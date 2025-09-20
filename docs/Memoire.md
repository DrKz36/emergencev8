# Mémoire progressive — ÉMERGENCE V8

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
