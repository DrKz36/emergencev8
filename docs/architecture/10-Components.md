# ÉMERGENCE — Components (C4-Component)

## Backend
- **`main.py`** : instancie `ServiceContainer`, exécute migrations SQLite, monte routers REST (`/api/*`) et WS (`/ws/{session_id}`), gère middleware deny-list + statiques.
- **`containers.py`** : centralise la DI (DB, `SessionManager`, `ConnectionManager`, `VectorService`, `MemoryAnalyzer`, `ChatService`, `DocumentService`, `DebateService`, `DashboardService`).
- **`features/auth/service.py`** : gère l'allowlist email, génère les JWT locaux (HS256, 7 jours), trace les sessions (`auth_sessions`), expose la révocation + métadonnées OTP ; bootstrap l'allowlist depuis `AUTH_ALLOWLIST_SEED` / `_PATH` lors du démarrage Cloud Run ; le helper `dev_login` n'est accessible que quand `AUTH_DEV_MODE=1` (sinon 404 côté router). **V2.1.2:** Fix critique `password_must_reset` - SQL CASE statement dans `_upsert_allowlist()` (lignes 1218-1222) + UPDATE explicites dans `change_own_password()` / `set_allowlist_password()` garantissent que les membres ne sont plus forcés de réinitialiser après chaque login.
- **`features/auth/router.py`** : endpoints login/logout (`POST /api/auth/*`), opérations admin (allowlist, sessions), route DEV (`POST /api/auth/dev/login`) qui renvoie 404 tant que `AUTH_DEV_MODE=0`, et branche le rate limiting côté FastAPI.
- **`features/auth/rate_limiter.py`** : garde-fou IP+email (fenêtre glissante), utilisé par le router pour limiter les tentatives.
- **`features/chat/router.py`** : REST threads/messages, montage WS ; valide JWT (`get_user_id`) ; fallback REST si WS indisponible et dédoublonne les trames `chat.message` / `chat.opinion` avant d'attaquer le service (comparaison texte + meta).
- **`features/chat/service.py`** : orchestration multi-agents (ordre préférentiel Google → Anthropic → OpenAI), injection mémoire/RAG, diffusion WS (`ws:chat_stream_*`, `ws:model_info`, `ws:memory_banner`).
- **`features/memory/analyzer.py` & `memory/gardener.py`** : analyse STM/LTM via LLM, extraction faits/concepts, consolidation ciblée (thread) ou globale, publication `ws:analysis_status`.
- **`features/documents/service.py`** : upload, parsing (`ParserFactory`), chunking, vectorisation, suppression (purge embeddings associés).
- **`features/debate/service.py`** : gère `debate:create`, chaîne les tours agents, isole les contextes, publie `ws:debate_*`.
- **`features/dashboard/service.py`** : agrège coûts (jour/semaine/mois/total), sessions actives, documents traités.
- **`features/monitoring/router.py`** : healthchecks (`/api/monitoring/health`, `/api/monitoring/health/detailed`) et endpoint system info (`/api/system/info`) pour About page. **V2.1.2:** Version synchronisée `beta-2.1.2` via `BACKEND_VERSION` env var (lignes 38, 384), exposée dans tous les healthchecks et system info.
- **`features/dashboard/timeline_service.py`** (V3.4 - Phase 1.2) : service dédié aux graphiques temporels du Cockpit (activité, coûts, tokens par jour), gère les valeurs NULL avec pattern COALESCE robuste, isolation multi-utilisateurs (user_id) + filtrage optionnel par session (X-Session-Id), périodes flexibles (7j, 30j, 90j, 1 an).
- **`features/dashboard/admin_service.py`** (V3.4 - Phase 1.3-1.5) : service admin pour statistiques globales, breakdown utilisateurs avec LEFT JOIN flexible, métriques temporelles avec fallbacks robustes, nouveau endpoint breakdown détaillé des coûts par utilisateur/module.
- **`features/benchmarks/service.py`** : orchestre le `BenchmarksRunner`, charge le catalogue de scénarios (ARE/Gaia2), persiste les runs en SQLite et (optionnellement) Firestore (`EMERGENCE_FIRESTORE_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`) et expose les endpoints `/api/benchmarks/*` (fallback SQLite forcé si `EDGE_MODE=1`).
- **`benchmarks/`** : noyau de benchmarking (runner, scénarios, executors, sinks).
- **`shared/vector_service.py`** : gère Chroma + SentenceTransformer, détecte corruption, déclenche backup + reset automatique.

## Frontend
- **`core/state-manager.js`** : store global, bootstrap auth + threads (REST), conserve map des threads/messages.
- **`core/websocket.js`** : ouverture WS post-auth (sub-proto `jwt`), gestion reconnexion, diffusion evenements sur `EventBus` et anti-duplication des frames `chat.opinion` (cache glissant 1,2 s).
- **`main.js`** : bootstrap EventBus/State, badge auth et instrumentation QA (`window.__EMERGENCE_QA_METRICS__.authRequired`) via `installAuthRequiredInstrumentation` (trace des états auth sans bannière visible).
- **`features/dashboard/benchmarks.js`** : matrice benchmarks (statut, coût, latence) avec styles dark mode.
- **`components/onboarding/onboarding-tour.js`** : legacy overlay (desactive v20250926, conserver pour audit historique).
- **`features/agents/agents.js`** : module retire (profils agents fusionnes dans `ReferencesModule`).
- **`features/home/home-module.js`** : landing auth (full screen), formulaire email allowlist, appels `POST /api/auth/login`, pilotage badge auth + bootstrap App après succès.
- **`features/references/references.js`** : module 'A propos' (markdown + viewer) + galerie horizontale des copilotes (Anima/Neo/Nexus) avec ancrages vers `/docs/agents-profils.md`.
- **`features/auth/auth-admin-module.js`** : interface admin (allowlist, sessions, révocation), réservée aux emails listés, s'appuie sur les endpoints `/api/auth/admin/*`.
- **`features/admin/admin.js`** : point d'entree dynamique pour AuthAdminModule, gere mount/unmount et expose l'API attendue par App.loadModule (charge uniquement les roles admin).
- **`shared/api-client.js`** : `fetchWithAuth` (Authorization Bearer), gère erreurs `auth:missing`, uniformise réponses et expose `authDevLogin()` (utilisé seulement si `AUTH_DEV_MODE=1`, sinon le front tolère le 404 renvoyé par l'API).
- **`features/chat/chat-module.js`** : synchronise state threads ↔ UI, gère envoi message (WS + watchdog REST), toasts, toggles RAG/mémoire et pilote les demandes d'avis (`chat.opinion`) : trace les clics (event `ui:guidance:opinion_request` + métriques), détecte les doublons via l'historique/buckets, route les réponses d'avis vers le bucket de l'agent commenté et maintient un cache `messageId -> bucket`.
- **`features/chat/chat-ui.js`** : rendu messages, sources RAG, badges mémoire (STM/LTM, modèle), actions `Analyser` / `Clear`, overlay « Connexion requise » quand l'auth est absente et boutons circulaires pour solliciter un autre agent.
- **`features/documents/`** : drag-and-drop, upload multi, rafraîchissement liste, suppressions.
- **`features/debate/`** : configuration débat (agents, rounds, RAG), suivi temps réel des événements.
- **`features/dashboard/`** : vue coûts + monitoring sessions/documents.

## Modules Frontend Additionnels

### Timeline Module

**Fichier** : `src/frontend/features/timeline/timeline.js`
**Styles** : `src/frontend/features/timeline/timeline.css`

**Responsabilité** : Visualisation chronologique des événements.

**Fonctionnalités** :
- Affichage timeline interactive
- Filtrage par type/agent/période
- Liens vers conversations/documents

**Événements consommés** :
- `EVENTS.TIMELINE_UPDATE`

**État** : ⚠️ Module présent, intégration partielle.

---

### Costs Module

**Fichier** : `src/frontend/features/costs/costs.js`
**UI** : `src/frontend/features/costs/costs-ui.js`
**Styles** : `src/frontend/features/costs/costs.css`

**Responsabilité** : Visualisation détaillée des coûts LLM.

**Fonctionnalités** :
- Graphiques coûts par agent/provider
- Export CSV/JSON
- Filtrage temporel

**API** :
- `GET /api/dashboard/costs/summary`
- `GET /api/dashboard/costs/details`

**État** : ✅ Module autonome, complément au Cockpit.

---

### Voice Module

**Fichier** : `src/frontend/features/voice/voice.js`
**README** : `src/frontend/features/voice/README.md`

**Responsabilité** : Interface audio (micro, lecture).

**Fonctionnalités** :
- Enregistrement audio navigateur (MediaRecorder API)
- Upload → transcription STT
- Lecture synthèse TTS

**Dépendances backend** :
- `POST /api/voice/transcribe`
- `POST /api/voice/synthesize`

**État** : ✅ Module optionnel, activé si VoiceService configuré.

---

### Preferences Module

**Fichier** : `src/frontend/features/preferences/preferences.js`
**Styles** : `src/frontend/features/preferences/preferences.css`

**Responsabilité** : Configuration utilisateur (modèles, UI, notifications).

**Fonctionnalités** :
- Sélection modèles IA par agent
- Thème clair/sombre (future)
- Préférences RAG (seuils, nb docs)
- Notifications push

**Stockage** :
- LocalStorage (clé `emergence_preferences`)
- Sync backend (future, endpoint `/api/users/preferences`)

**État** : ✅ Module actif, référencé dans navigation.

---

## Interfaces & Contrats
- WebSocket frames et REST détaillés dans `30-Contracts.md` (chat, mémoire, débat, monitoring).
- Les endpoints mémoire : `POST/GET /api/memory/tend-garden`, `POST /api/memory/clear` ; threads : `/api/threads` (liste, création auto, messages paginés).

## Services Backend Additionnels

### TimelineService

**Fichier** : `src/backend/features/timeline/service.py`
**Router** : `src/backend/features/timeline/router.py`
**Modèles** : `src/backend/features/timeline/models.py`

**Responsabilité** : Gestion de la chronologie des événements système.

**Fonctionnalités** :
- Enregistrement événements horodatés
- Filtrage par type/période
- Agrégation statistiques temporelles

**Endpoints** :
- `GET /api/timeline` - Liste événements
- `POST /api/timeline/event` - Enregistrer événement
- `GET /api/timeline/stats` - Statistiques

**État** : ⚠️ Service présent mais peu documenté, à auditer.

---

### VoiceService

**Fichier** : `src/backend/features/voice/service.py`
**Router** : `src/backend/features/voice/router.py`
**README** : `src/backend/features/voice/README.md`

**Responsabilité** : Interface audio (Speech-to-Text, Text-to-Speech).

**Fonctionnalités** :
- STT : Transcription audio → texte
- TTS : Synthèse texte → audio
- Intégration providers externes (OpenAI Whisper, Google Cloud Speech)

**Dépendances** :
- `httpx` (requêtes async vers APIs externes)
- `aiofiles` (gestion fichiers audio)

**Endpoints** :
- `POST /api/voice/transcribe` - Transcription audio
- `POST /api/voice/synthesize` - Génération audio

**État** : ✅ Service optionnel, activé si clés API configurées.

---

### MetricsRouter (Prometheus)

**Fichier** : `src/backend/features/metrics/router.py`

**Responsabilité** : Exposition métriques Prometheus pour observabilité.

**Fonctionnalités** :
- Endpoint `/api/metrics` (format Prometheus)
- Métriques applicatives (requêtes, latence, erreurs)
- Métriques métier (coûts LLM, tokens, débats)

**Dépendances** :
- `prometheus-client` (instrumentation)

**Endpoints** :
- `GET /api/metrics` - Export métriques Prometheus

**Intégration** :
```yaml
# Prometheus config
scrape_configs:
  - job_name: 'emergence-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
```

**État** : ✅ Activé en production Cloud Run.

---

## Qualité / Observabilité
- Logs structurés (niveau service) + toasts front pour surfacer auth/token manquants.
- Tests rapides : `tests/run_all.ps1` (smoke API), `tests/test_vector_store_reset.ps1`, `tests/test_vector_store_force_backup.ps1`.
- Auth : nouveaux tests `tests/backend/features/test_auth_login.py` + `tests/backend/features/test_auth_admin.py`; limiter rate et tables auditées.
- Points de vigilance : latence chargement SBERT (première requête), dépendances clés (`GOOGLE_API_KEY` (alias `GEMINI_API_KEY`), `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).

