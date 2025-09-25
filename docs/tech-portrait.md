# Portrait technique d'Emergence

## Vue d'ensemble
- Monorepo Python 3.11 / Node 18 : backend FastAPI + WebSocket, frontend Vite/JS vanilla modulaire, orchestration via scripts PowerShell.
- Services clefs: authentification locale (allowlist + JWT HS256), chat multi-agents temps reel, memoire progressive (STM/LTM), RAG documents, debat oriente scenario, dashboard couts.
- Environnements cibles: dev local (scripts `run-local.ps1`, `scripts/sync-workdir.ps1`), preview Cloud Run, production containerisee.

## Chiffres actuels (2025-09-25)
- `src/backend` ~ 12 300 lignes (services, routes, conteneur DI, outils memoire/RAG).
- `src/frontend` ~ 16 700 lignes (modules UI, state manager, websocket client, styles).
- `docs` ~ 13 300 lignes (architecture, roadmap, memoire, QA), renforcees a chaque iteration.
- Autres repertoires suivis (`prompts/`, `tests/`, `scripts/`, assets) portent l'ensemble a ~393 000 lignes traquees par Git.
- Tests: suites `pytest` + scripts smoke PowerShell (`tests/run_all.ps1`, `tests/test_vector_store_reset.ps1`).

## Architecture modulaire
- Conteneur DI (`src/backend/containers.py`) instancie toutes les dependances (DB, services, vector store, websocket manager).
- Chaque domaine (`auth`, `chat`, `memory`, `documents`, `debate`, `dashboard`) dispose de son router REST + service dedie, partageant un socle commun (schemas Pydantic, middleware, config).
- Frontend decoupe par module fonctionnel: `HomeModule`, `ChatModule`, `DocumentsModule`, `DebateModule`, `DashboardModule`, chacun branche sur `StateManager` et `EventBus` pour rester autonome.

## Donnees, memoire et RAG
- Persistence principale: SQLite (threads/messages, auth, memoire STM/LTM, couts, documents) avec migrations ligees.
- Vectorisation: Chroma local (collection `emergence_knowledge`) + SentenceTransformer, auto-backup et reset en cas de corruption via `VectorService`.
- Memoire progressive: `MemoryGardener` orchestre les consolidations, `MemoryAnalyzer` extrait resumes/faits/concepts, bandeau memoire diffuse via WebSocket.
- RAG: `ChatService` filtre les documents par thread et surveille les statuts via `ws:rag_status`, injection des sources verifiee en temps reel.

## Orchestration temps reel
- WebSocket unique `/ws/{session_id}` avec sous-protocole `jwt`.
- Stream chat: `ws:chat_stream_start/chunk/end` + meta `model_info`, `model_fallback`, `memory_banner`.
- Debats: evenements `ws:debate_status_update`, `ws:debate_turn_update`, `ws:debate_result` avec tracabilite couts par agent.
- Auth: handshake refuse toute session revoquee (`auth_sessions.revoked_at`) et notifie le front via `ws:auth_required`.

## Observabilite et operations
- Journaux structurels (`model_fallback`, `memory:garden`, `rag:active`, `ws:handshake`) et traces QA exposees dans `docs/passation.md`.
- Scripts d'entretien: `scripts/sync-workdir.ps1` (fetch/rebase/tests), `tests/run_all.ps1` (smoke end-to-end), `scripts/smoke/scenario-memory-clear.ps1`.
- Tableau de bord: `DashboardService` agrege couts par fenetre (jour/semaine/mois/total) et sessions/documents.

## Prochaines extensions prevues
- Personnalisation d'agents (schemas publics, editeur de traits) partagee avec le chantier UI d'accueil.
- Surveillance vector store renforcee (taches planifiees) et instrumentation additionnelle pour les toasts d'erreur auth.
- Exploration des canaux vocaux et multimodaux (voir `docs/Roadmap Strategique.txt`).

## Pour aller plus loin
- Contexte et conteneurs: `docs/architecture/00-Overview.md`.
- Sequences et flux detailles: `docs/architecture/20-Sequences.md`.
- Contrats API: `docs/architecture/30-Contracts.md`.
- Memoire progressive: `docs/Memoire.md`.
- Roadmap strategique: `docs/Roadmap Strategique.txt`.
