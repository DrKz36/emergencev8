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
- **`ChatService` (RAG guardrails)**
  - `_sanitize_doc_ids` filtre les identifiants envoyes par l'UI et supprime les doublons.
  - Les identifiants sont recoupes avec les documents rattaches au thread courant; si aucun ne correspond, le service retombe sur la liste autorisee renvoyee par l'API.
  - Les IDs valides sont reinjectees dans `meta.selected_doc_ids` sur `ws:chat_stream_*` et la progression RAG diffusee via `ws:rag_status` (searching/found/idle).
- **`AuthService`** (features/auth/service.py)
  - Verifie les JWT HS256 et enrichit les claims (`session_revoked`, `revoked_at`) consommes par `get_auth_claims`.
  - `logout` idempotent : marque `auth_sessions.revoked_at` et coupe les consolidations memoire/RAG en cas de session revoquee.
- **Endpoints REST**
  - `POST /api/memory/tend-garden` : lance une consolidation (option `thread_id`, `mode`).
  - `GET /api/memory/tend-garden` : renvoie l’état consolidé (`summaries`, `facts`, compteurs LTM).
  - `POST /api/memory/clear` : purge STM puis LTM (scope global ou thread).
  - Toutes les routes `/api/memory/*` valident le JWT via `shared_dependencies.get_user_id`; sans jeton valide la requête est rejetée en `401`. En DEV, le couple d'en-têtes `X-Dev-Bypass: 1` + `X-User-Id` reste accepté pour les environnements sans GIS.

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
4. **RAG sur selection de documents**
   - Declencheur : modification de `selected_doc_ids` dans l'UI avec RAG actif, meme sans nouveau message utilisateur.
   - `ChatService` lance la recherche Chroma si la liste est non vide alors que `last_user_message` est vide.
   - L'UI suit les transitions `ws:rag_status` et met a jour le bandeau documents et les toasts RAG.


## 4. Observabilité & tests
- Logs : `memory:garden:start`, `memory:garden:done`, `memory:clear`.
- WS meta : `meta.selected_doc_ids` expose les documents retenus et `ws:rag_status` trace les etats searching/found/idle pour la QA.
- Auth: les claims exposent `session_revoked`; apres un logout, toute reconnexion WS refuse la session tant que le token n'est pas renouvele.
- Tests recommandés :
  - `tests/run_all.ps1` (vérifie `/api/memory/tend-garden`).
  - `pytest tests/backend/features/test_memory_clear.py` : valide `POST /api/memory/clear` sans serveur actif (stubs DB/vector) et est invoque depuis `tests/run_all.ps1`.
  - `tests/test_memory_clear.ps1` (valide la purge STM/LTM et les embeddings). Pré-requis : backend local sur http://127.0.0.1:8000, dépendances Python installées, variable `EMERGENCE_ID_TOKEN` si auth activée. Exemple : `powershell -ExecutionPolicy Bypass -File tests/test_memory_clear.ps1 -BaseUrl http://localhost:8000`.
  - `scripts/smoke/scenario-memory-clear.ps1` (guide QA: health-check + injection auto + rappel des vérifications UI). Exemple : `pwsh -File scripts/smoke/scenario-memory-clear.ps1 -BaseUrl http://localhost:8000`.
  - `scripts/maintenance/run-vector-store-reset.ps1` (mode hebdo sans interaction, journalise sous `logs/vector-store/`).
  - `tests/test_vector_store_reset.ps1` (contrôle la remise à zéro et les backups du vector store).
- Métriques front : affichage du modèle, TTFB mémoire, nombre d’items injectés.

### Journal d'exécution (2025-09-21)
- `pytest tests/backend/shared/test_config.py`: ÉCHEC – 3 assertions sont tombées car `Settings` charge les clés définies dans `.env` (`GOOGLE_API_KEY`, `GEMINI_API_KEY`) avant les paramètres fournis; valider si les tests doivent neutraliser ces variables d'environnement.
- `tests/run_all.ps1`: OK – santé API, dashboard, documents et upload `test_upload.txt` (#14) validés, aucun code 5xx observé.
- `tests/test_memory_clear.ps1 -BaseUrl http://127.0.0.1:8000`: ÉCHEC – insertion de la session factice réussie mais aucun embedding n'est généré après `tend-garden` (compteur à 0, script arrêté avec «Aucun vecteur créé…»); investigation backend/vector store requise.
- `tests/test_memory_clear.ps1`: ÉCHEC (21/09 soir) – le script s'interrompt sur l'erreur Chromadb «Failed to send telemetry event ... capture() takes 1 positional argument but 3 were given». Ajout d'un `Settings(anonymized_telemetry=False)` sur `PersistentClient` et encapsulation des appels Python avec `$ErrorActionPreference = "Continue"` pour tolérer ces warnings.
- `tests/test_memory_clear.ps1`: OK (x2) – après le correctif, les runs successifs créent 2 vecteurs pour la session de test, `memory:clear` retourne `ltm_deleted = ltm_before = 2` et les colonnes `summary/concepts/entities` repassent à `NULL`. Les warnings Chromadb subsistent mais n'interrompent plus l'exécution (surveillance upstream).

## 5. UX & actions utilisateur
- **Badges mémoire** : indiquer clairement si STM/LTM ont été injectées dans la dernière réponse agent.
- **Journal** : prévoir un panneau listant les dernières consolidations (`lastRunAt`, `thread_id`, `model`).
- **CTA Clear** : confirmer avant purge (modal).

## 6. Étapes immédiates
1. Ajouter une remontée UI lorsqu’une consolidation échoue (toast + bouton retry).
2. Exposer dans l’UI l’historique renvoyé par `GET /api/memory/tend-garden`.
3. Documenter un guide QA (checklist) pour valider la cohérence STM vs LTM après `memory:clear`.
4. Intégrer le script `tests/test_memory_clear.ps1` (disponible) dans la checklist QA et l’automatiser après chaque purge majeure (voir section Observabilité & tests).
5. Planifier une exécution hebdomadaire de `tests/test_vector_store_reset.ps1` et `tests/test_memory_clear.ps1` (journaliser les résultats et les horodatages).

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
- **Préparation automatique** :
  - Lancer `pwsh -File scripts/smoke/scenario-memory-clear.ps1 -BaseUrl http://localhost:8000` (ajouter `-AuthToken` si l'auth est requise).
  - Le script vérifie `/api/health`, injecte un jeu de test via `tests/test_memory_clear.ps1`, puis rappelle les contrôles UI à effectuer.
- **Étapes UI** :
  1. Depuis le bandeau mémoire du chat, cliquer sur `Clear`.
  2. Lire le résumé de la modal et confirmer la purge.
  3. Observer le toast succès et le rafraîchissement `ws:memory_banner`.
  4. Recharger le thread et confirmer que STM/LTM sont à zéro (compteurs + liste vide).
- **Points de vigilance** : l'ordre STM → LTM → embeddings doit être respecté, et la modal doit résumer les effets (scope, session, agent).
    - Toute exécution `POST/DELETE /api/memory/clear` doit inclure un `Authorization: Bearer <JWT>` actif; sans cela, l'API renvoie immédiatement `401`. Conserver les en-têtes de contournement DEV uniquement sur les postes locaux.
- **Captures à intégrer** :
  - ![Capture modal clear](assets/memoire/modal-clear.png)
  - ![Capture bandeau vide](assets/memoire/bandeau-vide.png)
  - ![Capture console script](assets/memoire/scenario-memory-clear-log.png)
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
- **Dossier cible** : placer les captures et exports sous `docs/assets/memoire/` (ex. `memoire-clear-before.png`, `memoire-clear-after.png`, `memoire-toast-success.png`).
- **Captures UI** : bandeau mémoire (états `idle`, `loading`, `error`, `empty`), modal Clear, panneau thread, toasts succès/erreur, sortie console du script scénario.
- **Schémas** :
  - Diagramme séquence `ChatUI → MemoryGardener → MemoryAnalyzer → VectorService`.
  - Schéma de flux purge STM/LTM/embeddings (ordre et webhooks associés).
- **Exports données** : anonymiser un exemple de réponse `GET /api/memory/tend-garden` pour illustrer la doc.
- **Formats recommandés** : PNG pour captures (largeur 1440px), SVG pour schémas, TXT/MD pour journaux (ex. `scenario-memory-clear.log`).
## 9. Checklist QA manuelle
- [ ] Déclencher une **consolidation globale** et vérifier l’affichage du loader puis du résumé STM (capture : `assets/memoire/bandeau-analyse.png`).
- [ ] Exécuter une **analyse ciblée** avec `persist=False` et confirmer que la LTM ne change pas (capture : `assets/memoire/panneau-thread.png`).
- [ ] Lancer une **analyse ciblée persistée** (`persist=True`) et valider l’incrément du compteur d’items LTM (capture : `assets/memoire/option-persist.png`).
- [ ] Verifier qu'une selection de documents en dehors du thread est ignoree : le front affiche les ressources valides et `meta.selected_doc_ids` ne contient que les IDs autorisees.
- [ ] Activer RAG puis rafraichir la recherche sans message utilisateur en modifiant uniquement la selection; observer `ws:rag_status` et la mise a jour du bandeau documents.
- [ ] Exécuter `pwsh -File scripts/smoke/scenario-memory-clear.ps1` et archiver la sortie console (`docs/assets/memoire/scenario-memory-clear.log`).
- [ ] Réaliser un **clear complet** et contrôler la purge STM/LTM + embeddings (captures : `assets/memoire/modal-clear.png`, `assets/memoire/bandeau-vide.png`).
- [ ] **Tester le scénario d’erreur** (LLM indisponible) et confirmer la présence du toast + bouton retry (capture : `assets/memoire/toast-erreur.png`).
- [ ] Vérifier la **cohérence des logs** `memory:garden:*` et `memory:clear` avec les actions réalisées (capture : `assets/memoire/logs-erreur.png`).
