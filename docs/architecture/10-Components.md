# ÉMERGENCE — Components (C4-Component)

## Backend
- **`main.py`** : instancie `ServiceContainer`, exécute migrations SQLite, monte routers REST (`/api/*`) et WS (`/ws/{session_id}`), gère middleware deny-list + statiques.
- **`containers.py`** : centralise la DI (DB, `SessionManager`, `ConnectionManager`, `VectorService`, `MemoryAnalyzer`, `ChatService`, `DocumentService`, `DebateService`, `DashboardService`).
- **`features/auth/service.py`** : gère l'allowlist email, génère les JWT locaux (HS256, 7 jours), trace les sessions (`auth_sessions`), expose la révocation + métadonnées OTP **et fournit** `dev_login` (auto-session DEV via `AUTH_DEV_MODE=1` & `AUTH_DEV_DEFAULT_EMAIL`).
- **`features/auth/router.py`** : endpoints login/logout (`POST /api/auth/*`), opérations admin (allowlist, sessions), route DEV (`POST /api/auth/dev/login`) et branche le rate limiting côté FastAPI.
- **`features/auth/rate_limiter.py`** : garde-fou IP+email (fenêtre glissante), utilisé par le router pour limiter les tentatives.
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
- **`main.js`** : bootstrap EventBus/State, badge auth et instrumentation QA (`window.__EMERGENCE_QA_METRICS__.authRequired`) via `installAuthRequiredInstrumentation` (trace des états auth sans bannière visible).
- **`components/onboarding/onboarding-tour.js`** : legacy overlay (desactive v20250926, conserver pour audit historique).
- **`features/agents/agents.js`** : module retire (profils agents fusionnes dans `ReferencesModule`).
- **`features/home/home-module.js`** : landing auth (full screen), formulaire email allowlist, appels `POST /api/auth/login`, pilotage badge auth + bootstrap App après succès.
- **`features/references/references.js`** : module 'A propos' (markdown + viewer) + galerie horizontale des copilotes (Anima/Neo/Nexus) avec ancrages vers `/docs/agents-profils.md`.
- **`features/auth/auth-admin-module.js`** : interface admin (allowlist, sessions, révocation), réservée aux emails listés, s'appuie sur les endpoints `/api/auth/admin/*`.
- **`features/admin/admin.js`** : point d'entree dynamique pour AuthAdminModule, gere mount/unmount et expose l'API attendue par App.loadModule (charge uniquement les roles admin).
- **`shared/api-client.js`** : `fetchWithAuth` (Authorization Bearer), gère erreurs `auth:missing`, uniformise réponses et expose `authDevLogin()` pour le bypass DEV.
- **`features/chat/chat-module.js`** : synchronise state threads ↔ UI, gère envoi message (WS + watchdog REST), toasts, toggles RAG/mémoire.
- **`features/chat/chat-ui.js`** : rendu messages, sources RAG, badges mémoire (STM/LTM, modèle), actions `Analyser` / `Clear`, overlay « Connexion requise » quand l'auth est absente.
- **`features/documents/`** : drag-and-drop, upload multi, rafraîchissement liste, suppressions.
- **`features/debate/`** : configuration débat (agents, rounds, RAG), suivi temps réel des événements.
- **`features/dashboard/`** : vue coûts + monitoring sessions/documents.

## Interfaces & Contrats
- WebSocket frames et REST détaillés dans `30-Contracts.md` (chat, mémoire, débat, monitoring).
- Les endpoints mémoire : `POST/GET /api/memory/tend-garden`, `POST /api/memory/clear` ; threads : `/api/threads` (liste, création auto, messages paginés).

## Qualité / Observabilité
- Logs structurés (niveau service) + toasts front pour surfacer auth/token manquants.
- Tests rapides : `tests/run_all.ps1` (smoke API), `tests/test_vector_store_reset.ps1`, `tests/test_vector_store_force_backup.ps1`.
- Auth : nouveaux tests `tests/backend/features/test_auth_login.py` + `tests/backend/features/test_auth_admin.py`; limiter rate et tables auditées.
- Points de vigilance : latence chargement SBERT (première requête), dépendances clés (`GOOGLE_API_KEY` (alias `GEMINI_API_KEY`), `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
