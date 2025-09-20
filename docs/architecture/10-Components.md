# ÉMERGENCE — Components (C4-Component)

## Backend
- **`main.py`** : instancie `ServiceContainer`, exécute migrations SQLite, monte routers REST (`/api/*`) et WS (`/ws/{session_id}`), gère middleware deny-list + statiques.
- **`containers.py`** : centralise la DI (DB, `SessionManager`, `ConnectionManager`, `VectorService`, `MemoryAnalyzer`, `ChatService`, `DocumentService`, `DebateService`, `DashboardService`).
- **`features/chat/router.py`** : REST threads/messages, montage WS ; valide JWT (`get_user_id`) ; fallback REST si WS indisponible.
- **`features/chat/service.py`** : orchestration multi-agents (ordre préférentiel Google → Anthropic → OpenAI), injection mémoire/RAG, diffusion WS (`ws:chat_stream_*`, `ws:model_info`, `ws:memory_banner`).
- **`features/memory/analyzer.py` & `memory/gardener.py`** : analyse STM/LTM via LLM, extraction faits/concepts, consolidation ciblée (thread) ou globale, publication `ws:analysis_status`.
- **`features/documents/service.py`** : upload, parsing (`ParserFactory`), chunking, vectorisation, suppression (purge embeddings associés).
- **`features/debate/service.py`** : gère `debate:create`, chaîne les tours agents, isole les contextes, publie `ws:debate_*`.
- **`features/dashboard/service.py`** : agrège coûts (jour/semaine/mois/total), sessions actives, documents traités.
- **`shared/vector_service.py`** : gère Chroma + SentenceTransformer, détecte corruption, déclenche backup + reset automatique.

## Frontend
- **`core/state-manager.js`** : store global, bootstrap auth + threads (REST), conserve map des threads/messages.
- **`core/websocket.js`** : ouverture WS post-auth (sub-proto `jwt`), gestion reconnexion, diffusion événements sur `EventBus`.
- **`shared/api-client.js`** : `fetchWithAuth` (Authorization Bearer), gère erreurs `auth:missing`, uniformise réponses.
- **`features/chat/chat-module.js`** : synchronise state threads ↔ UI, gère envoi message (WS + watchdog REST), toasts, toggles RAG/mémoire.
- **`features/chat/chat-ui.js`** : rendu messages, sources RAG, badges mémoire (STM/LTM, modèle), actions `Analyser` / `Clear`.
- **`features/documents/`** : drag-and-drop, upload multi, rafraîchissement liste, suppressions.
- **`features/debate/`** : configuration débat (agents, rounds, RAG), suivi temps réel des événements.
- **`features/dashboard/`** : vue coûts + monitoring sessions/documents.

## Interfaces & Contrats
- WebSocket frames et REST détaillés dans `30-Contracts.md` (chat, mémoire, débat, monitoring).
- Les endpoints mémoire : `POST/GET /api/memory/tend-garden`, `POST /api/memory/clear` ; threads : `/api/threads` (liste, création auto, messages paginés).

## Qualité / Observabilité
- Logs structurés (niveau service) + toasts front pour surfacer auth/token manquants.
- Tests rapides : `tests/run_all.ps1` (smoke API), `tests/test_vector_store_reset.ps1`, `tests/test_vector_store_force_backup.ps1`.
- Points de vigilance : latence chargement SBERT (première requête), dépendances clés (`GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
