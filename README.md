# EMERGENCE V8

Multi agent conversation stack (Anima, Neo, Nexus) with cockpit, retrieval augmented generation, document tools, and interactive tutorial system.

> **📊 Dernier audit complet:** 2025-10-10 | [Voir le rapport](AUDIT_COMPLET_EMERGENCE_V8_20251010.md)
>
> **Score maintenabilité:** 47/100 → Cible 80/100 (roadmap 6 mois)
>
> **Bugs critiques:** 2 P0 en cours de correction | [Prompt fixes](PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md)

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

**Consignes agents** : voir [`AGENTS.md`](AGENTS.md) (section 13) et [`CODex_GUIDE.md`](CODex_GUIDE.md) (section 11)

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

- **[Memory Feature](docs/backend/memory.md)** - MemoryAnalyzer & HybridRetriever (P1.5)
  - Extraction préférences/intentions automatique
  - Fallback cascade LLM (neo → nexus → anima)
  - Cache analyses TTL 1h avec éviction agressive
  - Recherche hybride BM25 + vectorielle (alpha=0.5)
  - Métriques complètes (succès/échecs, latence, cache hits)

- **[Metrics Feature](docs/backend/metrics.md)** - Endpoints Prometheus
  - `/metrics` - Export Prometheus (activable via env var)
  - `/metrics/rag` - Métriques RAG structurées (JSON)
  - `/health` - Healthcheck basique

- **[Monitoring Feature](docs/backend/monitoring.md)** - Health checks avancés K8s
  - `/health/liveness` - Liveness probe (processus vivant)
  - `/health/readiness` - Readiness probe (services up: DB, Vector, LLM)
  - `/api/monitoring/health/detailed` - Métriques système (CPU, RAM, disk)
  - Dashboards admin (sécurité, performance, slow queries, AI stats)

- **[Settings Feature](docs/backend/settings.md)** - Configuration dynamique
  - `/api/settings/rag` - Configuration RAG (strict_mode, score_threshold)
  - `/api/settings/models` - Paramètres LLM par agent
  - Persistence JSON (`data/settings.json`)
  - Hot-reload sans redémarrage

### Prompts Agents Actifs

- **[Corrections Bugs P0](PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md)** - ⚠️ **PRIORITÉ** : Fuite mémoire + Race conditions
- **[Session Générique](PROMPT_NEXT_SESSION.md)** - Template sessions standard
- **[Déploiement Docker](PROMPT_DOCKER_BUILD_DEPLOY.md)** - Build + push Cloud Run
- **[Mémoire P2](PROMPT_NEXT_SESSION_MEMORY_P2.md)** - Améliorations mémoire phase 2
- **[Frontend P3](PROMPT_NEXT_SESSION_SPRINT_P3_FRONTEND.md)** - Améliorations UI/UX phase 3
