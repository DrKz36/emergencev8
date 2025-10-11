# ÉMERGENCE V8 - État du Projet au 11 Octobre 2025

> **Document de référence** pour Chat GPT et futurs agents
>
> **Version**: V8 Phase P2 Complétée
>
> **Dernière mise à jour**: 2025-10-11
>
> **Révision Cloud Run**: emergence-app-00298-g8j (deploy-20251011-143736)

---

## 📊 Vue d'Ensemble

**ÉMERGENCE** est une plateforme conversationnelle multi-agents avec système de mémoire progressive (STM/LTM), RAG (Retrieval-Augmented Generation), et orchestration intelligente de 3 agents IA spécialisés.

### Agents Principaux

1. **ANIMA** (Empathie & Créativité) - GPT-4 Turbo / Claude 3.5 Sonnet
2. **NEO** (Analyse & Logique) - GPT-4o-mini (optimisé coûts/performance)
3. **NEXUS** (Synthèse & Coordination) - GPT-4 Turbo / Claude 3.5 Sonnet

### Stack Technique

- **Backend**: Python 3.11 + FastAPI + SQLite + ChromaDB
- **Frontend**: Vanilla JS (ES6+) + WebSocket + Vite
- **Infrastructure**: Google Cloud Run (Europe-West1)
- **CI/CD**: GitHub → Docker → Artifact Registry → Cloud Run
- **Monitoring**: Prometheus + métriques custom

---

## 🏗️ Architecture Système

### Backend (FastAPI)

```
src/backend/
├── main.py                    # Point d'entrée, routers, middleware
├── containers.py              # Dependency Injection (ServiceContainer)
├── core/
│   ├── database/
│   │   ├── manager.py         # DatabaseManager (SQLite)
│   │   ├── queries.py         # Queries SQL (threads, messages, sessions)
│   │   └── migrate.py         # Migrations schéma
│   └── monitoring/            # Logs structurés, health checks
├── features/
│   ├── auth/
│   │   ├── service.py         # JWT (HS256), allowlist, sessions
│   │   ├── router.py          # POST /api/auth/login, /logout
│   │   └── rate_limiter.py    # Rate limiting IP+email
│   ├── chat/
│   │   ├── service.py         # ChatService (multi-agents, WS)
│   │   ├── router.py          # WebSocket /ws/{session_id}, REST threads
│   │   ├── memory_ctx.py      # MemoryContextBuilder (cache préférences 5min TTL)
│   │   └── models.py          # ChatMessage, Thread
│   ├── memory/
│   │   ├── analyzer.py        # MemoryAnalyzer (extraction préférences/concepts)
│   │   ├── gardener.py        # Consolidation STM→LTM
│   │   ├── vector_service.py  # ChromaDB + SentenceTransformer
│   │   ├── proactive_hints.py # ProactiveHintEngine (suggestions contextuelles)
│   │   └── router.py          # GET /api/memory/* (search, stats)
│   ├── documents/
│   │   ├── service.py         # Upload, parsing, chunking, vectorisation
│   │   ├── parser.py          # ParserFactory (PDF, DOCX, TXT, MD)
│   │   └── router.py          # POST /api/documents/upload
│   ├── debate/
│   │   ├── service.py         # DebateService (tours multi-agents)
│   │   └── router.py          # POST /api/debates/create
│   ├── dashboard/
│   │   ├── service.py         # DashboardService (coûts, métriques)
│   │   └── router.py          # GET /api/dashboard/costs/summary
│   ├── benchmarks/
│   │   ├── service.py         # BenchmarksService (ARE, Gaia2)
│   │   ├── runner.py          # BenchmarksRunner
│   │   └── router.py          # GET /api/benchmarks/runs
│   └── metrics/
│       └── router.py          # GET /api/metrics (Prometheus)
└── shared/
    └── llm_router.py          # Routage multi-provider (Google, Anthropic, OpenAI)
```

### Frontend (Vanilla JS)

```
src/frontend/
├── main.js                    # Bootstrap EventBus, State, Auth
├── core/
│   ├── state-manager.js       # Store global (threads, messages, auth)
│   ├── websocket.js           # WebSocket client (jwt sub-protocol)
│   ├── event-bus.js           # EventBus (pub/sub)
│   └── api-client.js          # fetchWithAuth (REST wrapper)
├── features/
│   ├── home/
│   │   └── home-module.js     # Landing page (auth, login form)
│   ├── chat/
│   │   ├── chat-module.js     # Chat principal (WS send/receive)
│   │   ├── chat-ui.js         # Rendu messages, sources RAG
│   │   └── memory_ctx.js      # Injection contexte mémoire
│   ├── memory/
│   │   ├── memory-dashboard.js    # Dashboard mémoire (stats, préférences)
│   │   ├── proactive-hints-ui.js  # Banners hints proactifs
│   │   └── concept-search.js      # Recherche concepts/archives
│   ├── documents/
│   │   └── documents.js       # Drag-and-drop, upload, liste
│   ├── debate/
│   │   └── debate.js          # Configuration débat, suivi temps réel
│   ├── dashboard/
│   │   ├── dashboard.js       # Cockpit (coûts, sessions)
│   │   └── benchmarks.js      # Matrice benchmarks
│   ├── references/
│   │   └── references.js      # Module "À propos" (agents, docs)
│   └── admin/
│       └── auth-admin-module.js   # Admin allowlist, sessions
└── styles/
    ├── index.css              # Styles globaux
    └── components/
        └── proactive-hints.css    # Styles hints proactifs
```

---

## 🎯 Fonctionnalités Principales

### 1. Chat Multi-Agents

**Endpoint WebSocket**: `ws://localhost:8000/ws/{session_id}?token={jwt}`

**Frames WebSocket**:
- `chat.message` (user → agents)
- `chat.opinion` (demande avis agent spécifique)
- `ws:chat_stream_start/delta/complete` (réponse streaming)
- `ws:model_info` (métadonnées modèle utilisé)

**Features**:
- Réponses streaming (SSE-like sur WS)
- Fallback automatique Google → Anthropic → OpenAI
- Injection contexte mémoire (STM+LTM) automatique
- Cache préférences in-memory (5min TTL, hit rate ~100%)
- Demande d'avis circulaire (boutons agents)
- Détection doublons (buckets 1.2s)

**Optimisations Phase P2**:
- Agent **neo_analysis** → GPT-4o-mini (coût -40%, latence -43%)
- Cache analyses mémoire (TTL 1h, éviction agressive)
- Débats parallèles Round 1 (asyncio.gather, latence -40%)

---

### 2. Système Mémoire Progressive

#### **Architecture 3 Couches**

```
┌─────────────────────────────────────────────────────────┐
│                    AGENTS (ANIMA/NEO/NEXUS)             │
└───────────────┬─────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        │  API UNIFIÉE   │ (/api/memory/search/unified)
        └───────┬────────┘
                │
    ┌───────────┼───────────┬───────────────┐
    │           │           │               │
┌───▼───┐  ┌───▼────┐  ┌───▼────┐  ┌──────▼──────┐
│  STM  │  │  LTM   │  │THREADS │  │  MESSAGES   │
│(SQL)  │  │(Vector)│  │ (SQL)  │  │    (SQL)    │
└───────┘  └────────┘  └────────┘  └─────────────┘
```

#### **STM (Short-Term Memory)**

**Table `sessions`**:
- `summary` (TEXT) - Résumé IA conversation
- `extracted_concepts` (JSON) - Liste concepts clés
- `extracted_entities` (JSON) - Entités nommées

**API**:
- `GET /api/memory/tend-garden?limit=20` - Liste résumés sessions

#### **LTM (Long-Term Memory)**

**Collection ChromaDB `emergence_knowledge`**:
- Embeddings vectoriels (all-MiniLM-L6-v2)
- Métadonnées enrichies:
  - `first_mentioned_at`, `last_mentioned_at` (ISO 8601)
  - `mention_count` (compteur récurrences)
  - `thread_ids_json` (threads associés)
  - `vitality` (score pertinence 0-1)

**API**:
- `GET /api/memory/concepts/search?q=docker&limit=10`
- `GET /api/memory/search/unified` - Recherche globale STM+LTM+Threads+Messages

**Optimisations HNSW** (Phase P2):
- `hnsw:space=cosine`, `hnsw:M=16`
- Latence queries: 200ms → **35ms** (-82.5%)

#### **Threads & Messages**

**Table `threads`** (enrichie v2.0):
- `archived` (INT) - 0=actif, 1=archivé
- `archival_reason` (TEXT) - Motif archivage
- `last_message_at` (TEXT) - Date dernier message
- `message_count` (INT) - Nombre messages (trigger auto)

**API**:
- `GET /api/threads/?include_archived=true` - Liste threads (avec archives)
- `GET /api/threads/archived/list` - Archives uniquement
- `GET /api/threads/{thread_id}/messages?limit=50`

**Triggers SQL automatiques**:
- Mise à jour `last_message_at` à chaque message
- Incrémentation/décrémentation `message_count`

#### **Recherche Temporelle**

**TemporalSearch Engine**:
- Fulltext search dans messages archivés
- Filtres dates (start_date, end_date)

**API**:
- `GET /api/memory/search?q=docker&start_date=2025-01-01&end_date=2025-10-11`

---

### 3. Hints Proactifs (Phase P2)

**ProactiveHintEngine** - Suggestions contextuelles automatiques

**Stratégies**:

| Type | Trigger | Exemple |
|------|---------|---------|
| `preference_reminder` | Concept récurrent (3+ mentions) match préférence | "💡 Tu as mentionné 'python' 3 fois. Rappel: I prefer Python for scripting" |
| `intent_followup` | Intention non complétée | "📋 Rappel: Tu voulais configurer Docker la semaine dernière" |
| `constraint_warning` | Violation contrainte (futur) | "⚠️ Attention: Cette approche contredit ta contrainte X" |

**Configuration**:
- Max 3 hints/appel
- Seuil récurrence: 3 mentions
- Score relevance minimum: 0.6
- Auto-dismiss après 10s

**Event WebSocket**: `ws:proactive_hint`

**Payload**:
```json
{
  "type": "ws:proactive_hint",
  "payload": {
    "hints": [{
      "id": "hint_abc123",
      "type": "preference_reminder",
      "title": "Rappel: Préférence détectée",
      "message": "💡 Tu as mentionné 'python' 3 fois...",
      "relevance_score": 0.85,
      "action_label": "Appliquer",
      "action_payload": { "preference": "I prefer Python for scripting" }
    }]
  }
}
```

**UI Component**: `ProactiveHintsUI.js`
- Banners top-right, non-intrusif
- Actions: Appliquer / Ignorer / Plus tard (snooze 1h)
- Styles CSS: gradients bleu-violet (preference), rose (intent), orange (warning)

**Métriques Prometheus**:
```python
memory_proactive_hints_generated_total  # Compteur par type
memory_proactive_hints_relevance_score  # Histogram scores
```

---

### 4. RAG (Retrieval-Augmented Generation)

**DocumentService** - Upload, parsing, chunking, vectorisation

**Formats supportés**:
- PDF, DOCX, TXT, MD, HTML

**Pipeline**:
1. Upload → `POST /api/documents/upload`
2. Parsing → `ParserFactory` (PyPDF2, python-docx, BeautifulSoup)
3. Chunking → 512 tokens/chunk, overlap 50 tokens
4. Vectorisation → SentenceTransformer (all-MiniLM-L6-v2)
5. Stockage → ChromaDB collection `emergence_documents`

**HybridRetriever** (BM25 + Vector):
- Alpha = 0.5 (pondération BM25/Vector)
- Top-k = 5 documents/requête
- Fallback cascade si échec

**API**:
- `POST /api/documents/upload` (multipart/form-data)
- `GET /api/documents/list` (métadonnées)
- `DELETE /api/documents/{doc_id}` (purge embeddings)

**Injection sources**:
- Sources affichées dans chat-ui (expandable)
- Métadonnées: `doc_title`, `page`, `similarity_score`

---

### 5. Débats Multi-Agents

**DebateService** - Orchestration tours agents avec isolation contextes

**Modes**:
- Sequential (tour par tour)
- Parallel Round 1 (asyncio.gather)

**Configuration**:
- Nombre rounds (1-5)
- Agents participants (2-3)
- RAG activé/désactivé

**Events WebSocket**:
- `ws:debate_start` (métadonnées débat)
- `ws:debate_round_start` (round N/M)
- `ws:debate_agent_turn` (agent X parle)
- `ws:debate_stream_delta` (streaming réponse)
- `ws:debate_complete` (synthèse finale)

**API**:
- `POST /api/debates/create` (config débat)
- `GET /api/debates/{debate_id}` (historique)

---

### 6. Dashboard & Monitoring

#### **Cockpit (DashboardService)**

**Métriques agrégées**:
- Coûts LLM (jour/semaine/mois/total)
- Sessions actives
- Documents traités
- Top agents (utilisation)

**API**:
- `GET /api/dashboard/costs/summary`
- `GET /api/dashboard/costs/details`
- `GET /api/dashboard/sessions/active`

#### **Prometheus**

**Endpoint**: `GET /api/metrics` (activable env var `CONCEPT_RECALL_METRICS_ENABLED`)

**Métriques custom**:

| Métrique | Type | Description |
|----------|------|-------------|
| `memory_analysis_success_total` | Counter | Analyses mémoire réussies |
| `memory_analysis_failure_total` | Counter | Analyses mémoire échouées |
| `memory_cache_operations_total` | Counter | Opérations cache (hit/miss/save) |
| `memory_proactive_hints_generated_total` | Counter | Hints proactifs générés (par type) |
| `memory_proactive_hints_relevance_score` | Histogram | Scores relevance hints |
| `memory_preferences_extracted_total` | Counter | Préférences extraites |
| `memory_analysis_duration_seconds` | Histogram | Latence analyses mémoire |
| `chat_message_latency_seconds` | Histogram | Latence réponses chat |
| `debate_rounds_total` | Counter | Rounds débats (par agent) |

**Intégration Grafana**:
```promql
# Cache hit rate mémoire
sum(rate(memory_cache_operations_total{operation="hit"}[5m]))
/ sum(rate(memory_cache_operations_total[5m]))

# Hints générés par type
sum by (type) (rate(memory_proactive_hints_generated_total[5m]))

# Latence p95 analyses mémoire
histogram_quantile(0.95, rate(memory_analysis_duration_seconds_bucket[5m]))
```

#### **Health Checks**

**Endpoints**:
- `GET /api/health` - Basic health (200 OK)
- `GET /health/liveness` - Liveness probe K8s
- `GET /health/readiness` - Readiness probe (DB, Vector, LLM)
- `GET /api/monitoring/health/detailed` - Métriques système (CPU, RAM, disk)

**Cloud Run Logs**:
```bash
gcloud run services logs read emergence-app \
  --region europe-west1 --project emergence-469005 --limit 100
```

---

### 7. Authentification & Sécurité

**AuthService** - JWT locaux (HS256, TTL 7 jours)

**Méthodes auth**:
1. **Allowlist email** (production)
   - Table `auth_allowlist` (email, allowed=1)
   - POST `/api/auth/login` (email → JWT si allowlist)
2. **Dev mode** (local uniquement)
   - `AUTH_DEV_MODE=1` (env var)
   - POST `/api/auth/dev/login` (bypass allowlist)

**Rate Limiting**:
- Fenêtre glissante IP+email
- Max 5 tentatives/minute
- Implémenté dans `rate_limiter.py`

**Sessions audit**:
- Table `auth_sessions` (login_at, expires_at, ip_address)
- Révocation possible (admin)

**Admin Panel**:
- UI: `auth-admin-module.js`
- Endpoints: `/api/auth/admin/*` (allowlist, sessions)
- Accès réservé emails admin

**JWT Payload**:
```json
{
  "sub": "user_abc123",
  "email": "user@example.com",
  "exp": 1728691200,
  "iat": 1728086400
}
```

**WebSocket Auth**:
- Sub-protocol: `jwt`
- Token passé dans query param: `ws://host/ws/{session_id}?token={jwt}`

---

## 🚀 Workflow de Développement

### Configuration Initiale

**Prérequis**:
- Python 3.11+
- Node.js 18+
- Docker Desktop (pour builds locaux)
- gcloud CLI (pour déploiements)

**Setup Python**:
```powershell
cd C:\dev\emergenceV8
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Setup Node**:
```bash
nvm use 18
npm ci
npm run build
```

### Environnement Local

**Variables d'environnement** (`.env.local`):
```bash
# LLM API Keys
GOOGLE_API_KEY=xxx              # Gemini (alias GEMINI_API_KEY)
ANTHROPIC_API_KEY=xxx           # Claude
OPENAI_API_KEY=xxx              # GPT

# Auth
AUTH_DEV_MODE=1                 # 0=prod (allowlist), 1=dev (bypass)
JWT_SECRET=xxx                  # HS256 secret

# Database
SQLITE_DB_PATH=./data/emergence.db

# Monitoring
CONCEPT_RECALL_METRICS_ENABLED=1   # Activer Prometheus metrics
```

**Lancer le backend**:
```powershell
python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Health check**:
```bash
curl http://127.0.0.1:8000/api/health
# {"status":"ok","message":"Emergence Backend is running."}
```

### Tests

**Backend (pytest)**:
```powershell
# Tous les tests
pytest tests/backend/ -v

# Tests spécifiques
pytest tests/backend/features/test_memory_performance.py -v
pytest tests/backend/features/test_proactive_hints.py -v

# Quality checks (pytest + ruff + mypy)
./scripts/run_backend_quality.ps1
```

**Frontend (Playwright)**:
```bash
npx playwright test tests/e2e/proactive-hints.spec.js
```

**Coverage**:
- **Backend**: 232 tests pytest (auth, memory, chat, debate, documents)
- **Frontend**: 10 tests E2E (hints, dashboard, UI flows)

### Git Workflow

**Branches**:
- `main` - Production (Cloud Run)
- `dev` - Développement (optionnel)
- `feature/*` - Features isolées

**Commits**:
```bash
git add -A
git commit -m "feat(memory): add proactive hints engine

- ProactiveHintEngine with 3 strategies
- WebSocket event ws:proactive_hint
- Frontend ProactiveHintsUI component
- Prometheus metrics
- Tests coverage (16 backend + 10 E2E)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

**Politique merge**:
- Squash merge sur `main` (tous les commits de la PR en 1 commit)
- Branch auto-supprimée après merge

---

## 🐳 Build & Déploiement

### Docker Build

**Dockerfile** (multi-stage):
```dockerfile
FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download SBERT model (cache image)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2')"

# Copy app
COPY . .

CMD ["uvicorn", "--app-dir", "src", "backend.main:app", \
     "--host", "0.0.0.0", "--port", "8080"]
```

**Build local**:
```bash
timestamp=$(date +%Y%m%d-%H%M%S)
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp .
```

### Push Artifact Registry

```bash
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp
```

### Déploiement Cloud Run

**Commande**:
```bash
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp \
  --platform managed \
  --region europe-west1 \
  --project emergence-469005 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY,AUTH_DEV_MODE=0
```

**Révision actuelle** (2025-10-11):
- Nom: `emergence-app-00298-g8j`
- Image: `deploy-20251011-143736`
- Trafic: 100%
- Status: ✅ Active

**URL Production**: `https://emergence-app-486095406755.europe-west1.run.app`

**Rollback**:
```bash
# Lister révisions (max 3 conservées)
gcloud run revisions list --service emergence-app --region europe-west1

# Rollback vers révision précédente
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00297-6pr=100 \
  --region europe-west1
```

---

## 📈 Performance & Optimisations

### Métriques Phase P2

| Métrique | Avant P2 | Après P2 | Amélioration |
|----------|----------|----------|--------------|
| **Latence contexte LTM** | ~120ms | **35ms** | **-71%** ✅ |
| **Cache hit rate préférences** | 0% | **100%** | **+100%** ✅ |
| **Queries ChromaDB/message** | 2 | **1** | **-50%** ✅ |
| **Latence analyses mémoire** | ~8s | **4.2s** | **-48%** ✅ |
| **Coût agent neo_analysis** | $0.015/k tokens | **$0.009/k** | **-40%** ✅ |

### Optimisations Backend

1. **Cache préférences in-memory** (MemoryContextBuilder)
   - TTL: 5 minutes
   - Couvre ~10 messages typiques
   - Hit rate: 100%

2. **Configuration HNSW ChromaDB**
   - `hnsw:space=cosine`
   - `hnsw:M=16` (balance précision/vitesse)
   - Résultat: Latence -82.5% (200ms → 35ms)

3. **Agent neo_analysis → GPT-4o-mini**
   - Analyses mémoire uniquement (non-critique)
   - Fallback cascade: neo → nexus → anima
   - Coût -40%, latence -43%

4. **Débats parallèles Round 1**
   - `asyncio.gather` (agents simultanés)
   - Latence -40% pour débats 3 agents

5. **Cache analyses mémoire**
   - TTL: 1h
   - Éviction agressive (LRU max 100 entrées)
   - Clé: `user_id + thread_id + timestamp_day`

### Optimisations Frontend

1. **Anti-duplication frames WS**
   - Buckets glissants 1.2s
   - Cache `messageId → bucket`
   - Évite doublons `chat.opinion`

2. **Lazy loading modules**
   - `loadModule()` dynamique (import async)
   - Modules chargés à la demande

3. **Event debouncing**
   - Throttle search inputs (300ms)
   - Coalesce resize events

---

## 🔧 Système Multi-Agents Autonome

### Agents d'Orchestration (Monitoring)

**Système Integrity & Docs Guardian v2.0**

#### **ANIMA (DocKeeper)**
- **Rôle**: Détection gaps documentation
- **Script**: `scan_docs.py`
- **Slash command**: `/check_docs`
- **Output**: `docs_report.json`
- **Triggers**: Git hooks pre-commit/post-commit

**Critères détection**:
- Backend modifié sans docs
- Endpoints API non documentés
- Schémas changés sans update OpenAPI

#### **NEO (IntegrityWatcher)**
- **Rôle**: Cohérence backend/frontend
- **Script**: `check_integrity.py`
- **Slash command**: `/check_integrity`
- **Output**: `integrity_report.json`

**Vérifications**:
- Endpoints supprimés mais appelés (CRITICAL)
- Schémas déphasés (WARNING)
- OpenAPI validation (15 endpoints, 6 schemas)

#### **NEXUS (Coordinator)**
- **Rôle**: Fusion rapports Anima + Neo
- **Script**: `generate_report.py`
- **Slash command**: `/guardian_report`
- **Output**: `unified_report.json`

**Actions prioritaires** (P0 > P1 > P2 > P3):
- P0: Breaking changes (blocage déploiement)
- P1: High severity (fix < 24h)
- P2: Medium severity (fix < 1 semaine)

#### **ProdGuardian**
- **Rôle**: Monitoring production Cloud Run
- **Script**: `check_prod_logs.py`
- **Slash command**: `/check_prod`
- **Output**: `prod_report.json`

**Métriques surveillées**:
- Erreurs (ERROR logs)
- Warnings
- Signaux critiques (crash, OOM)
- Latence (p95, p99)

**Status actuel** (2025-10-11 14:30 UTC):
- Logs analysés: 80 (1h)
- Erreurs: 4 (pré-déploiement fix DB)
- Warnings: 1
- Status: 🟡 DEGRADED → ✅ OK (post-deploy)

#### **Orchestrateur Global**
- **Rôle**: Coordination 4 agents + sync Git
- **Script**: `merge_reports.py` + `sync_all.sh`
- **Slash command**: `/sync_all`
- **Output**: `global_report.json`

**Workflow**:
1. Exécute Anima + Neo + ProdGuardian (parallèle)
2. Fusionne rapports
3. Détermine statut global (OK/DEGRADED/CRITICAL)
4. Sync GitHub (si OK)
5. Génère rapport actionnable

**Git Hooks** (`.git/hooks/`):
- `pre-commit` → Anima + Neo (validation avant commit)
- `post-commit` → Nexus (rapport unifié post-commit)

---

## 🔍 Débogage & Troubleshooting

### Problèmes Fréquents

#### **1. Erreurs WebSocket "Database connection is not available"**

**Symptôme**: Erreurs `RuntimeError: Database connection is not available` dans logs Cloud Run

**Cause**: Perte connexion SQLite après inactivité

**Fix** (commit f1d2877):
```python
# src/backend/core/database/manager.py:58-73
async def _ensure_connection(self):
    if self._engine is None or self._session_maker is None:
        logger.warning("Database connection lost, attempting reconnection...")
        try:
            await self.initialize()
        except Exception as e:
            raise RuntimeError(
                "Failed to reconnect to database after connection loss"
            ) from e
```

**Déployé**: 2025-10-11 (révision 00298-g8j)

#### **2. Cache préférences hit rate < 80%**

**Diagnostic**:
```promql
# Prometheus query
sum(rate(memory_cache_operations_total{operation="hit"}[5m]))
/ sum(rate(memory_cache_operations_total[5m]))
```

**Fixes possibles**:
- Augmenter TTL cache (5min → 10min)
- Pré-charger préférences au login
- Vérifier éviction LRU (max 100 entrées)

#### **3. Latence analyses mémoire > 8s**

**Diagnostic**:
```promql
histogram_quantile(0.95, rate(memory_analysis_duration_seconds_bucket[5m]))
```

**Fixes**:
- Vérifier fallback cascade LLM (neo → nexus → anima)
- Augmenter cache analyses (TTL 1h → 2h)
- Réduire top-k ChromaDB (10 → 5)

#### **4. Cold start Cloud Run > 10s**

**Cause**: Téléchargement modèle SBERT au démarrage

**Fix**: Pre-download dans Dockerfile (déjà fait)
```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2')"
```

---

## 📚 Documentation Complète

### Architecture

- [Overview (C4 Context)](docs/architecture/00-Overview.md)
- [Components (C4 Component)](docs/architecture/10-Components.md)
- [Sequences (C4 Sequence)](docs/architecture/20-Sequences.md)
- [Contracts (API/WS)](docs/architecture/30-Contracts.md)
- [Concept Recall](docs/architecture/CONCEPT_RECALL.md)

### Features

- [Capacités Mémoire](docs/MEMORY_CAPABILITIES.md)
- [Concept Recall Monitoring](docs/features/concept-recall-monitoring.md)
- [Hints Proactifs](docs/features/proactive-hints.md)
- [Auto-Sync](docs/features/auto-sync.md)

### Backend

- [Chat Feature](docs/backend/chat.md)
- [Memory Feature](docs/backend/memory.md)
- [Metrics Feature](docs/backend/metrics.md)
- [Monitoring Feature](docs/backend/monitoring.md)
- [Settings Feature](docs/backend/settings.md)

### Déploiements

- [README Déploiements](docs/deployments/README.md)
- [2025-10-11 Hotfix DB Reconnection](docs/deployments/2025-10-11-hotfix-db-reconnection.md)
- [2025-10-10 Deploy P1+P0](docs/deployments/2025-10-10-deploy-p1-p0.md)
- [2025-10-09 Deploy P1 Memory](docs/deployments/2025-10-09-deploy-p1-memory.md)

### Validation

- [P2 Completion Final Status](docs/validation/P2_COMPLETION_FINAL_STATUS.md)
- [P2 Sprint 1 Completion](docs/validation/P2_SPRINT1_COMPLETION_STATUS.md)
- [P2 Sprint 2 Proactive Hints](docs/validation/P2_SPRINT2_PROACTIVE_HINTS_STATUS.md)
- [P2 Sprint 3 Frontend](docs/validation/P2_SPRINT3_FRONTEND_STATUS.md)

### Monitoring

- [Monitoring Guide](docs/MONITORING_GUIDE.md)
- [Prometheus Phase 3 Setup](docs/monitoring/prometheus-phase3-setup.md)
- [Production Logs Analysis](docs/monitoring/production-logs-analysis-20251009.md)

### QA

- [Cockpit QA Playbook](docs/qa/cockpit-qa-playbook.md)
- [Concept Recall Manual QA](docs/qa/concept-recall-manual-qa.md)

---

## 🎯 Roadmap & Next Steps

### Phase P3 (Prévu Q4 2025)

#### **Frontend UX Enhancements**

1. **Timeline Visuelle**
   - Component: `TimelineModule` (déjà présent, intégration partielle)
   - Visualisation chronologique conversations/documents
   - Filtres par type/agent/période

2. **Dark Theme**
   - Support `prefers-color-scheme: dark`
   - Toggle manuel (localStorage)
   - Styles CSS variables

3. **Mobile Responsive**
   - Breakpoints < 768px
   - Navigation hamburger
   - Chat mobile-first

4. **Notifications Push**
   - Web Push API
   - Notification hints proactifs
   - Alertes débats terminés

#### **Backend Optimisations**

1. **Connexion Pooling**
   - SQLite → PostgreSQL (production scale)
   - Connection pool (min 5, max 20)
   - Transactions ACID

2. **Cache Distribuée**
   - Redis cache layer
   - Cache préférences/analyses partagé
   - Session storage

3. **Queue Asynchrone**
   - Celery + RabbitMQ
   - Analyses mémoire async (background)
   - Export documents async

#### **Features Avancées**

1. **Voice Interface**
   - VoiceService (déjà présent, peu utilisé)
   - STT: OpenAI Whisper
   - TTS: Google Cloud TTS
   - UI micro/speaker buttons

2. **Multi-Language**
   - i18n frontend (react-i18next)
   - Détection langue auto
   - Préférences utilisateur

3. **Benchmarks Étendus**
   - BenchmarksService (ARE, Gaia2 déjà supportés)
   - UI matrice benchmarks (déjà présent)
   - Export CSV/JSON résultats

---

## 🔐 Sécurité & Compliance

### Données Sensibles

**Isolation utilisateur**:
- Tous les appels DB/Vector filtrés par `user_id` (JWT sub claim)
- Aucune fuite cross-user possible (tests validés)

**Secrets**:
- Variables env Cloud Run (secrets chiffrés)
- `.env.local` gitignored
- JWT secret rotable (env var `JWT_SECRET`)

**Rate Limiting**:
- 5 tentatives login/minute (IP+email)
- WebSocket: 1 connexion/session
- API REST: 100 req/min/user (future)

### GDPR & Privacy

**Données stockées**:
- Conversations (threads, messages) → SQLite
- Embeddings vectoriels (concepts, documents) → ChromaDB
- Sessions auth (JWT, IP, timestamps) → SQLite

**Droit à l'oubli**:
- Endpoint `/api/users/delete` (future)
- Purge complète: threads + messages + embeddings + sessions

**Consentement**:
- Acceptation CGU au premier login (future)
- Opt-out analytics (future)

---

## 📞 Support & Contact

**Repository**: [github.com/DrKz36/emergencev8](https://github.com/DrKz36/emergencev8)

**Issues**: [GitHub Issues](https://github.com/DrKz36/emergencev8/issues)

**Documentation**: `/docs/` (Markdown + architecture diagrams)

**Cloud Console**: [GCP Emergence Project](https://console.cloud.google.com/run/detail/europe-west1/emergence-app?project=emergence-469005)

**Prometheus Metrics**: `https://emergence-app-486095406755.europe-west1.run.app/api/metrics`

---

## 📝 Changelog Récent

### 2025-10-11

**Commits**:
- `f1d2877` - fix(database): add automatic reconnection for lost DB connections
  - Fix CRITICAL: Erreurs WebSocket production (6 erreurs → 0)
  - Reconnexion automatique DatabaseManager
  - Déployé: révision 00298-g8j

- `3e1ff80` - chore: sync documentation, monitoring reports, and agent orchestration
  - Documentation backend complète (docs/backend/)
  - Rapports monitoring (prod_report.json)
  - Hotfix deployment guide

**Déploiement**:
- Image: `deploy-20251011-143736`
- Révision: `emergence-app-00298-g8j`
- Status: ✅ Active (100% trafic)

### 2025-10-10

**Commits**:
- `f5f4fa5` - chore: commit backlog state before handoff
- `b08d866` - feat(rag): integrate hybrid monitoring backlog
- `3a93647` - feat: complete system upgrade for ÉMERGENCE multi-agent orchestration

**Features**:
- Phase P2 Sprint 3 complétée (hints proactifs frontend)
- Dashboard mémoire (stats, préférences, concepts)
- Optimisations performance (-71% latence contexte)

---

## 🏆 Crédits

**Développement**:
- **Architecte Principal**: Fernando Gonzalez (gonzalefernando@gmail.com)
- **Agents IA**: Claude Code, Codex (co-développement)

**Technologies**:
- FastAPI (backend framework)
- ChromaDB (vector database)
- SentenceTransformers (embeddings)
- Prometheus (monitoring)
- Google Cloud Run (infrastructure)

**Licence**: Voir [LICENSE](LICENSE)

---

**Document généré le**: 2025-10-11
**Version ÉMERGENCE**: V8 Phase P2
**Révision Cloud Run**: emergence-app-00298-g8j
**Statut Production**: ✅ Opérationnel

---

*Ce document est destiné à être utilisé comme référence pour Chat GPT et autres agents IA collaborant sur le projet ÉMERGENCE. Il doit être mis à jour à chaque changement majeur d'architecture ou déploiement.*
