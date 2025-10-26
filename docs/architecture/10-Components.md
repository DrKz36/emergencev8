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
- **`features/monitoring/router.py`** : healthchecks (`/api/monitoring/health`, `/api/monitoring/health/detailed`) et endpoint system info (`/api/system/info`) pour About page. **V2.1.3:** Version synchronisée `beta-2.1.3` via `BACKEND_VERSION` env var (lignes 38, 384), exposée dans tous les healthchecks et system info.
- **`features/dashboard/timeline_service.py`** (V3.4 - Phase 1.2) : service dédié aux graphiques temporels du Cockpit (activité, coûts, tokens par jour), gère les valeurs NULL avec pattern COALESCE robuste, isolation multi-utilisateurs (user_id) + filtrage optionnel par session (X-Session-Id), périodes flexibles (7j, 30j, 90j, 1 an).
- **`features/dashboard/admin_service.py`** (V3.4 - Phase 1.3-1.5) : service admin pour statistiques globales, breakdown utilisateurs avec LEFT JOIN flexible, métriques temporelles avec fallbacks robustes, nouveau endpoint breakdown détaillé des coûts par utilisateur/module.
- **`features/benchmarks/service.py`** : orchestre le `BenchmarksRunner`, charge le catalogue de scénarios (ARE/Gaia2), persiste les runs en SQLite et (optionnellement) Firestore (`EMERGENCE_FIRESTORE_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`) et expose les endpoints `/api/benchmarks/*` (fallback SQLite forcé si `EDGE_MODE=1`). **V3.1.3:** Méthode `calculate_temporal_ndcg()` pour évaluer la qualité d'un classement avec pénalisation temporelle exponentielle (formule nDCG@k temporelle : DCG^time@k = Σ (2^rel_i - 1) * exp(-λ * Δt_i) / log2(i+1)), utilisée pour mesurer l'impact des boosts fraîcheur/entropie dans le moteur de ranking ; implémentation complète dans `features/benchmarks/metrics/temporal_ndcg.py` avec 18 tests unitaires.
- **`benchmarks/`** : noyau de benchmarking (runner, scénarios, executors, sinks).
- **`shared/vector_service.py`** : gère Chroma + SentenceTransformer, détecte corruption, déclenche backup + reset automatique.

## Frontend
- **`core/state-manager.js`** : store global, bootstrap auth + threads (REST), conserve map des threads/messages.
- **`core/websocket.js`** : ouverture WS post-auth (sub-proto `jwt`), gestion reconnexion, diffusion evenements sur `EventBus` et anti-duplication des frames `chat.opinion` (cache glissant 1,2 s).
- **`main.js`** : bootstrap EventBus/State, badge auth et instrumentation QA (`window.__EMERGENCE_QA_METRICS__.authRequired`) via `installAuthRequiredInstrumentation` (trace des états auth sans bannière visible).
- **`features/pwa/sync-manager.js` / `features/pwa/offline-storage.js`** : enregistrement service worker, détection offline, snapshots IndexedDB (threads/messages) et file d'attente WS persistée.
- **`/sw.js` & `manifest.webmanifest`** : shell PWA cache-first (Cache API) + manifeste installable (icônes, thème, start_url).
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

### Cockpit Module

**Fichier** : `src/frontend/features/cockpit/cockpit.js`
**Styles** : `src/frontend/features/cockpit/cockpit.css`

**Responsabilité** : Dashboard principal avec métriques temps réel, graphiques activité et coûts.

**Fonctionnalités** :
- Vue d'ensemble activité (messages, tokens, coûts)
- Graphiques temporels (7j, 30j, 90j, 1 an)
- Statistiques par agent/provider
- Export données

**API** :
- `GET /api/dashboard/timeline/activity`
- `GET /api/dashboard/timeline/costs`
- `GET /api/dashboard/costs/summary`

**État** : ✅ Module actif, dashboard principal de l'app.

---

### Settings Module

**Fichier** : `src/frontend/features/settings/settings.js`
**Styles** : `src/frontend/features/settings/settings.css`

**Responsabilité** : Configuration utilisateur (préférences système, modèles, notifications).

**Fonctionnalités** :
- Sélection modèles IA par agent (GPT-4, Claude, Gemini)
- Thème clair/sombre
- Préférences RAG (seuils, nb docs)
- Notifications

**Stockage** :
- LocalStorage (clé `emergence_settings`)
- Sync backend futur

**État** : ✅ Module actif.

---

### Threads Module

**Fichier** : `src/frontend/features/threads/threads.js`
**Styles** : `src/frontend/features/threads/threads.css`

**Responsabilité** : Gestion des threads de conversation (liste, création, archivage, suppression).

**Fonctionnalités** :
- Liste threads avec preview dernier message
- Création nouveau thread
- Archivage threads anciens
- Suppression avec confirmation

**API** :
- `GET /api/threads`
- `POST /api/threads`
- `DELETE /api/threads/{id}`

**État** : ✅ Module actif, panneau latéral gauche.

---

### Conversations Module

**Fichier** : `src/frontend/features/conversations/conversations.js`

**Responsabilité** : Module legacy pour compatibilité historique.

**État** : ⚠️ Module legacy, utilisé pour migration données anciennes versions. Considérer archivage.

---

### Hymn Module

**Fichier** : `src/frontend/features/hymn/hymn.js`
**Styles** : `src/frontend/features/hymn/hymn.css`

**Responsabilité** : Easter egg / module artistique (animation audio-visuelle).

**Fonctionnalités** :
- Animation visuelle synchronisée
- Easter egg caché dans UI

**État** : ✅ Module actif, feature bonus.

---

### Documentation Module

**Fichier** : `src/frontend/features/documentation/documentation.js`
**Styles** : `src/frontend/features/documentation/documentation.css`

**Responsabilité** : Viewer markdown pour documentation intégrée (guides, aide).

**Fonctionnalités** :
- Rendu markdown
- Navigation sections
- Recherche documentation

**État** : ✅ Module actif, accessible via menu aide.

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

### GmailService (Phase 3 Guardian Cloud)

**Fichier** : `src/backend/features/gmail/service.py`
**Router** : `src/backend/features/gmail/router.py`

**Responsabilité** : Intégration Gmail API pour lecture emails Guardian (Codex GPT).

**Fonctionnalités** :
- OAuth2 flow Gmail (admin uniquement)
- Lecture emails avec query `subject:(emergence OR guardian OR audit)`
- Auth via API key `X-Codex-API-Key` pour Codex
- Stockage tokens OAuth dans Firestore (encrypted)

**Endpoints** :
- `GET /auth/gmail` - Initier OAuth2 flow
- `GET /auth/callback/gmail` - Callback OAuth2
- `GET /api/gmail/read-reports` - Lire emails Guardian (Codex auth)
- `GET /api/gmail/status` - Vérifier status OAuth

**État** : ✅ Service actif, utilisé par Codex GPT (Phase 3 Guardian Cloud).

---

### GuardianService

**Fichier** : `src/backend/features/guardian/router.py`

**Responsabilité** : Auto-fix et audit rapports Guardian (hooks Git).

**Fonctionnalités** :
- Endpoint pour déclencher audit manuel
- Intégration avec Guardian agents (Anima, Neo, Nexus, ProdGuardian)
- Génération rapports unifiés

**Endpoints** :
- `POST /api/guardian/run-audit` - Déclencher audit manuel

**État** : ✅ Service actif, intégré Git hooks.

---

### TracingService (Phase 3)

**Fichier** : `src/backend/features/tracing/router.py`
**Core** : `src/backend/core/tracing/trace_manager.py`

**Responsabilité** : Distributed tracing pour observabilité (spans retrieval, llm_generate).

**Fonctionnalités** :
- Création spans avec attributs (agent, provider, model)
- Export traces pour analyse
- Métriques Prometheus associées (duration, status)

**Endpoints** :
- `GET /api/tracing/spans` - Export spans récents

**État** : ✅ Service actif, instrumentation ChatService complète.

---

### UsageService (Phase 2 Guardian Cloud)

**Fichier** : `src/backend/features/usage/router.py`
**Middleware** : `src/backend/core/middleware/usage_tracker.py`

**Responsabilité** : Tracking usage endpoints pour monitoring prod (Guardian Cloud).

**Fonctionnalités** :
- Middleware auto-tracking toutes requêtes HTTP
- Persistance usage dans SQLite (table `api_usage`)
- Statistiques par endpoint/user/période

**Endpoints** :
- `GET /api/usage/stats` - Statistiques usage API

**État** : ✅ Service actif, middleware global activé.

---

### SyncService

**Fichier** : `src/backend/features/sync/router.py`

**Responsabilité** : Auto-sync inter-agents (AGENT_SYNC.md updates automatiques).

**Fonctionnalités** :
- Monitoring fichiers AGENT_SYNC.md, docs/passation.md
- Notifications WebSocket quand changements détectés
- Auto-update documentation

**Endpoints** :
- `GET /api/sync/status` - Status synchronisation

**État** : ✅ Service actif, intégration Guardian.

---

### BetaReportService

**Fichier** : `src/backend/features/beta_report/router.py`

**Responsabilité** : Collecte feedback beta testeurs.

**Fonctionnalités** :
- Formulaire feedback bug/feature request
- Catégorisation automatique
- Export rapports pour équipe

**Endpoints** :
- `POST /api/beta/report` - Soumettre rapport beta
- `GET /api/beta/reports` - Liste rapports (admin)

**État** : ✅ Service actif, utilisé par beta testeurs.

---

### SettingsService

**Fichier** : `src/backend/features/settings/router.py`

**Responsabilité** : Gestion settings application (config système, toggles features).

**Fonctionnalités** :
- Get/Set settings globaux
- Feature flags
- Configuration agents (modèles par défaut)

**Endpoints** :
- `GET /api/settings` - Récupérer settings
- `PUT /api/settings` - Modifier settings (admin)

**État** : ✅ Service actif.

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

## Tables et Nomenclature Critique

### ⚠️ Distinction SESSIONS vs THREADS (IMPORTANT)

**PROBLÈME LEGACY RÉSOLU (2025-10-18)** : Le système utilise DEUX tables différentes avec des noms similaires qui peuvent prêter à confusion.

#### Table `sessions` (Threads de conversation)

**Usage** : Stocker les threads de chat/conversation persistantes
**Structure** : `id`, `user_id`, `created_at`, `updated_at`, `session_data`, `metadata`, `summary`, etc.
**Endpoints** :
- `GET /api/admin/analytics/threads` - Dashboard admin (anciennement `/admin/analytics/sessions`)
- `POST /api/chat/messages` - Opérations chat

**Note** : Le nom legacy "sessions" est conservé en DB pour éviter une migration lourde, mais les endpoints/UI utilisent désormais "threads" pour clarifier.

#### Table `auth_sessions` (Sessions d'authentification JWT)

**Usage** : Stocker les sessions d'authentification JWT actives
**Structure** : `id`, `email`, `role`, `ip_address`, `issued_at`, `expires_at`, `revoked_at`, `revoked_by`
**Endpoints** :
- `GET /api/auth/admin/sessions` - Gestion sessions JWT (module Auth Admin)
- `POST /api/auth/admin/sessions/{id}/revoke` - Révocation session JWT

**Note** : Ce sont les vraies sessions d'authentification, gérées par `AuthService`.

#### Mapping user_id (Format inconsistant - 3 formats supportés)

**PROBLÈME CONNU** : Le champ `user_id` dans la table `sessions` (threads) et autres tables peut avoir **TROIS formats différents** :

1. **Format legacy** : Hash SHA256 de l'email (ex: `a3c5f8d9e1b2...`)
   - Utilisé par les anciennes sessions
   - Privacy-friendly mais illisible

2. **Format actuel** : Email en clair (ex: `user@example.com`)
   - Utilisé par les nouvelles sessions
   - Lisible, facile à debugger
   - Recommandé pour les apps internes

3. **Format OAuth** : Google OAuth `sub` (ex: `1234567890` - numeric)
   - Utilisé pour les utilisateurs Google OAuth
   - Identifiant unique Google
   - Priorité 1 dans le matching (le plus fiable)

**Solution actuelle** : `AdminDashboardService._build_user_email_map()` (lignes 92-127) supporte **les trois formats** simultanément pour rétrocompatibilité :
```python
# Ligne 116-125 de admin_service.py
if oauth_sub:
    email_map[oauth_sub] = (email, role)  # Priority 1

email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
email_map[email_hash] = (email, role)  # Legacy support

email_map[email] = (email, role)  # Current format
```

**Décision Phase 2 (2025-10-19)** : **NE PAS MIGRER** les user_id existants.
- Migration DB trop risquée (pourrait casser les références historiques)
- Le code actuel gère les 3 formats correctement
- Documenter le comportement au lieu de le changer

**Recommandation future** : Lors de la création de **nouveaux users**, utiliser systématiquement :
- OAuth `sub` si disponible (Google OAuth)
- Email en clair sinon

**Référence** : Voir [AUDIT_COMPLET_2025-10-18.md](../AUDIT_COMPLET_2025-10-18.md) et [PROMPT_SUITE_AUDIT.md](../PROMPT_SUITE_AUDIT.md) pour contexte complet.

---

## Qualité / Observabilité
- Logs structurés (niveau service) + toasts front pour surfacer auth/token manquants.
- Tests rapides : `tests/run_all.ps1` (smoke API), `tests/test_vector_store_reset.ps1`, `tests/test_vector_store_force_backup.ps1`.
- Auth : nouveaux tests `tests/backend/features/test_auth_login.py` + `tests/backend/features/test_auth_admin.py`; limiter rate et tables auditées.
- Points de vigilance : latence chargement SBERT (première requête), dépendances clés (`GOOGLE_API_KEY` (alias `GEMINI_API_KEY`), `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
