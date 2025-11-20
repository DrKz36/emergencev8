# EMERGENCE V8

Multi agent conversation stack (Anima, Neo, Nexus) with cockpit, retrieval augmented generation, document tools, and interactive tutorial system.

> **📊 Dernier audit complet:** 2025-10-10 | [Voir le rapport](AUDIT_COMPLET_EMERGENCE_V8_20251010.md)
>
> **Score maintenabilité:** 47/100 → Cible 80/100 (roadmap 6 mois)
>
> **Bugs critiques:** 2 P0 en cours de correction | [Prompt fixes](PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md)
>
> **Note maintenance (2025-11-20)** : fallback WS r�tabli (chargement de session legacy via `get_session_by_id`), healthcheck front orient� vers le backend (plus de 404 `/ready` en dev), toggles RAG/TTS align�s sur le th�me Deep Aura et parseurs Documents/m�moire durcis (imports paresseux + hydratation threads s�curis�e).

## Features

- **Multi-Agent Conversations** : Chat avec agents spécialisés (Anima, Neo, Nexus)
- **RAG (Retrieval Augmented Generation)** : Recherche vectorielle dans documents
- **Memory System** : Mémoire à court terme (STM) et long terme (LTM)
- **Debate Mode** : Débats multi-agents structurés
- **Cockpit Dashboard** : Monitoring activité, coûts, tokens
- **Benchmarks & Metrics** *(v3.1.3)* : Évaluation performances agents avec métriques avancées (nDCG@k temporelle pour mesurer impact boosts fraîcheur/entropie)

See [docs/backend/](docs/backend/) for detailed module documentation.

## Local environment

The project targets Python 3.11 and Node.js 18 or newer. Always isolate work inside a virtual environment and a dedicated node installation to keep parity with CI.

### Python setup

Windows PowerShell 5.1+
```powershell
cd C:\dev\emergenceV8
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS / Linux
```bash
cd ~/dev/emergenceV8
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Optional: capture the exact wheel set once everything works with `pip freeze > requirements-dev.txt` or maintain a `requirements.lock` to document the environment used for a successful session.

### Node setup

Use Node 18 with nvm (or a compatible manager) and reinstall dependencies after each rebase if `package-lock.json` changed.
```bash
nvm install 18
nvm use 18
npm ci
npm run build
```

### Running the stack locally

Backend (FastAPI + Uvicorn)
```powershell
python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000
```

Frontend build smoke test
```bash
npm run build
```

Health check
```powershell
curl.exe -s http://127.0.0.1:8000/api/health
```

### Backend quality checks

Run all backend quality gates in one go (pytest, ruff, mypy).

```powershell
./scripts/run_backend_quality.ps1
```

Add `-FailFast` to stop after the first failure, or use `-Python` to point to a custom interpreter. Pass `-Paths src/backend` if you need to lint the whole backend.

Generate the production allowlist seed before a Cloud Run deploy:
```powershell
python scripts/generate_allowlist_seed.py --output allowlist_seed.json
python scripts/generate_allowlist_seed.py --push AUTH_ALLOWLIST_SEED --create-secret
```
Without this secret (`AUTH_ALLOWLIST_SEED`) Cloud Run boots with an empty allowlist and every login fails with 401.

## Git remote configuration

When cloning from an archive or copying the folder you need to add the remote manually so that pulls and pushes work. Configure it once with git or use the helper scripts included in `scripts/`.

```powershell
git remote add origin https://github.com/DrKz36/emergencev8.git
```

```bash
git remote add origin https://github.com/DrKz36/emergencev8.git
```

On Windows/PowerShell you can run `pwsh -File scripts/bootstrap.ps1` and the script will ensure the `origin` remote points to `https://github.com/DrKz36/emergencev8.git` before starting `npm run start`. On Unix shells run `./scripts/bootstrap.sh` for the same behaviour. Pass `-SkipStart`/`--skip-start` if you only need to configure git or override the remote settings via the corresponding flags.

## Git workflow and branch hygiene

1. Start on a clean tree: `git status` should report no changes.
2. Discover the upstream default branch: `git remote show origin` highlights the HEAD (usually `main`).
3. Synchronise with upstream before coding.
   ```powershell
   git fetch --all --prune
   git checkout main
   git pull --rebase origin main
   git checkout your_feature_branch
   git rebase origin/main
   ```
4. Prefer rebases over merge commits when updating feature branches. If a rebase rewrites history, use `git push --force-with-lease` once tests pass.
5. Resolve conflicts locally, rerun tests, and document any decisions in the commit message.
6. Clean merged branches periodically.
   ```powershell
   git branch --merged
   git branch -d obsolete_branch
   git push origin --delete obsolete_branch
   ```

## Daily development checklist

1. `git status`
2. `git fetch --all` and `git rebase origin/<base_branch>`
3. Activate the Python virtual environment.
4. `python -m pip install -r requirements.txt` (repeat after rebases that touch `requirements.txt`).
5. `npm ci` (repeat after rebases that touch `package-lock.json`).
6. Run `./scripts/run_backend_quality.ps1` to execute pytest/ruff/mypy together (or the individual commands if you only touched a subset).
7. Run `npm run build` to catch front end issues.
8. Develop the feature, commit with an explicit message, and rerun `git rebase origin/<base_branch>` if long running work drifted.
9. `git push origin <branch>` and open the pull request.

Keeping these steps in sync between cloud and local runs eliminates version drift and makes conflicts predictable.

### Politique de merge

Le depot applique le **squash merge** pour toutes les Pull Requests. Apres merge, vos commits individuels sont regroupes dans un seul commit sur `main`. Pour connaitre la procedure complete (verification, suppression des branches, relance du script de sync), consulter `docs/git-workflow.md`.

## Co-développement multi-agents

Emergence V8 utilise une approche collaborative avec plusieurs agents IA (Claude Code, Codex) travaillant comme co-développeurs de niveau équivalent. Les principes clés :

- **Égalité technique** : tous les agents peuvent modifier n'importe quel fichier du dépôt.
- **Modification croisée** : un agent peut compléter ou corriger le travail d'un autre.
- **Validation humaine** : l'architecte valide les changements avant commit/push/deploy.
- **Communication asynchrone** : via Git (commits, branches) et `docs/passation.md` (journal inter-agents).

**Protocole complet** : voir [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md)

**Consignes agents** :
- Claude Code : [`AGENTS.md`](AGENTS.md) (section 13)
- Codex GPT : [`CODEX_GPT_GUIDE.md`](CODEX_GPT_GUIDE.md) (guide complet)
- Codex local : [`CODex_GUIDE.md`](CODex_GUIDE.md) (section 11)

**Journal de passation** : [`docs/passation.md`](docs/passation.md) (contexte récent, blocages, prochaines actions)

---

## 📚 Documentation Clé

- **[Audit Complet 2025-10-10](AUDIT_COMPLET_EMERGENCE_V8_20251010.md)** - Rapport audit global (bugs, architecture, optimisations)
- **[Plan de Nettoyage](CLEANUP_PLAN_20251010.md)** - Script suppression ~13 Mo fichiers obsolètes
- **[Architecture Overview](docs/architecture/00-Overview.md)** - Vue C4 Contexte & Conteneurs
- **[Architecture Components](docs/architecture/10-Components.md)** - Détail composants backend/frontend
- **[Mémoire Progressive](docs/Memoire.md)** - Système STM/LTM complet
- **[Testing Guide](TESTING.md)** - Guide tests (232 tests pytest)
- **[Monitoring Guide](docs/MONITORING_GUIDE.md)** - Prometheus + observabilité

### Backend Features (Phase P1.5 - V8)

Documentation technique des modules backend récents :

- **[Chat Feature](docs/backend/chat.md)** - MemoryContextBuilder avec cache préférences (P2.1)
  - Cache in-memory TTL 5min (hit rate >80%)
  - Injection automatique préférences actives (confidence >0.6)
  - Temporal weighting (boost items récents/fréquents)
  - Métriques Prometheus cache operations

- **[Memory Feature](docs/backend/memory.md)** - MemoryAnalyzer & HybridRetriever (V3.8 - P1.5+)
  - **NOUVEAU (V3.8)**: Feedback temps réel consolidation (WebSocket `ws:memory_progress`)
  - **NOUVEAU (V3.8)**: Barre de progression frontend (Centre Mémoire) avec phases traduites
  - **NOUVEAU (V3.8)**: UX améliorée (bouton "Consolider mémoire" + tooltip explicatif)
  - Extraction préférences/intentions automatique
  - Fallback cascade LLM (neo → nexus → anima)
  - Cache analyses TTL 1h avec éviction agressive
  - Recherche hybride BM25 + vectorielle (alpha=0.5)
  - Métriques complètes (succès/échecs, latence, cache hits)

- **[Metrics Feature](docs/backend/metrics.md)** - Endpoints Prometheus (V1.1)
  - `/metrics` - Export Prometheus (**activé par défaut** depuis V1.1)
  - `/metrics/rag` - Métriques RAG structurées (JSON)
  - `/health` - Healthcheck basique
  - **Changement majeur**: Observabilité production activée par défaut

- **[Monitoring Feature](docs/backend/monitoring.md)** - Health checks avancés K8s (V2.1.2)
  - **NOUVEAU (V2.1.2)**: `/api/system/info` - Informations système complètes pour About page
  - **NOUVEAU (V2.1.3)**: Version synchronisée `beta-2.1.3` via `BACKEND_VERSION` env var
  - `/health/liveness` - Liveness probe (processus vivant)
  - `/health/readiness` - Readiness probe (services up: DB, Vector, LLM)
  - `/api/monitoring/health` - Healthcheck basique avec version
  - `/api/monitoring/health/detailed` - Métriques système (CPU, RAM, disk)
  - Dashboards admin (sécurité, performance, slow queries, AI stats)

- **[Settings Feature](docs/backend/settings.md)** - Configuration dynamique
  - `/api/settings/rag` - Configuration RAG (strict_mode, score_threshold)
  - `/api/settings/models` - Paramètres LLM par agent
  - Persistence JSON (`data/settings.json`)
  - Hot-reload sans redémarrage

- **[Dashboard Feature](docs/backend/dashboard.md)** - API cockpit & timeline (V3.4 - Phase 1 Debug)
  - **NOUVEAU (V3.4)**: Gestion robuste des valeurs NULL avec pattern COALESCE
  - **NOUVEAU (V3.4)**: `/api/admin/costs/detailed` - Breakdown détaillé des coûts par utilisateur/module
  - **FIX (V3.4)**: Charts Cockpit timeline affichent maintenant des données (Phase 1.2)
  - **FIX (V3.4)**: Admin "Users" tab affiche tous les utilisateurs avec LEFT JOIN (Phase 1.3)
  - **FIX (V3.4)**: Admin "Cost Evolution" chart fonctionnel avec fallbacks robustes (Phase 1.4)
  - `/api/dashboard/costs/summary` - Résumé coûts/métriques (global ou par session)
  - `/api/dashboard/timeline/*` - Timelines temporelles (activité, coûts, tokens)
  - `/api/dashboard/distribution/{metric}` - Répartition par agent
  - `/api/admin/dashboard/global` - Statistiques globales (admin)
  - `/api/admin/dashboard/user/{user_id}` - Détails utilisateur (admin)
  - `/api/admin/allowlist/emails` - Liste emails pour invitations beta
  - `/api/admin/beta-invitations/send` - Envoi invitations beta
  - Périodes flexibles: 7j, 30j, 90j, 1 an
  - Isolation multi-utilisateurs (user_id) + filtrage session (X-Session-Id)
  - TimelineService pour graphiques temporels avec requêtes SQL optimisées
  - AdminDashboardService pour statistiques globales et gestion beta
  - Logging standardisé avec préfixes `[Timeline]` et `[admin_dashboard]`

- **[Auth Feature](docs/backend/auth.md)** - Authentification & Email (V2.1.2)
  - **FIX CRITIQUE (V2.1.2)**: Bug `password_must_reset` résolu définitivement
    - Fix SQL CASE dans `_upsert_allowlist()` (lignes 1218-1222)
    - UPDATE explicites post-changement de mot de passe
    - Les membres ne sont plus forcés de réinitialiser à chaque connexion
  - JWT authentication avec sessions management
  - Allowlist-based access control (admin/member/guest)
  - Password reset par email avec tokens sécurisés (1h expiration)
  - Email service avec templates HTML/text (Gmail SMTP)
  - `/api/auth/login` - Login email/password
  - `/api/auth/request-password-reset` - Demande réinitialisation
  - `/api/auth/reset-password` - Réinitialisation avec token
  - `/api/auth/change-password` - Changement mot de passe
  - **Fix V2.0**: Admins ne sont plus forcés à réinitialiser leur mot de passe
  - `password_must_reset = 0` automatique pour role admin
  - Rate limiting anti-brute force (5 tentatives/15min)
  - `verify_token()` restaure les sessions manquantes (Cloud Run multi-instance) tout en respectant révocation et expiration
  - Audit log complet de toutes les actions auth

- **[Beta Report Feature](docs/backend/beta_report.md)** - Système rapports beta (V1.0)
  - Formulaire HTML interactif 55 checkboxes (8 phases de test)
  - Approche mailto pour fiabilité maximale
  - Auto-détection navigateur/OS
  - Barre de progression temps réel
  - Email service pour invitations beta avec templates HTML
  - Interface admin `beta_invitations.html` pour gestion manuelle
  - Documentation complète (START_HERE.md, guides, etc.)

### Prompts Agents Actifs

- **[Corrections Bugs P0](PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md)** - ⚠️ **PRIORITÉ** : Fuite mémoire + Race conditions
- **[Session Générique](PROMPT_NEXT_SESSION.md)** - Template sessions standard
- **[Déploiement Docker](PROMPT_DOCKER_BUILD_DEPLOY.md)** - Build + push Cloud Run
- **[Mémoire P2](PROMPT_NEXT_SESSION_MEMORY_P2.md)** - Améliorations mémoire phase 2
- **[Frontend P3](PROMPT_NEXT_SESSION_SPRINT_P3_FRONTEND.md)** - Améliorations UI/UX phase 3
