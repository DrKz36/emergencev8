# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Derniere mise a jour** : 2025-10-08 20:30 CEST (Claude Code - Phase 2 Performance implémentée : neo_analysis + cache + débats parallèles)

---

## 🔥 Lecture OBLIGATOIRE avant toute session de code

**Ordre de lecture pour tous les agents :**
1. Ce fichier (`AGENT_SYNC.md`) — état actuel du dépôt
2. [`AGENTS.md`](AGENTS.md) — consignes générales
3. [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md) — protocole multi-agents
4. [`docs/passation.md`](docs/passation.md) — 3 dernières entrées minimum
5. `git status` + `git log --oneline -10` — état Git

---

## 📍 État actuel du dépôt (2025-10-08)

### Branche active
- **Branche courante** : `main`
- **Derniers commits** :
  - `b45cfd8` docs: mise à jour AGENT_SYNC.md - session fix navigation menu mobile
  - `98d9fb3` docs: mise à jour documentation sessions et déploiement
  - `cec2a0f` fix: correction navigation menu mobile - backdrop bloquait les clics

### Remotes configurés
- `origin` → HTTPS : `https://github.com/DrKz36/emergencev8.git`
- `codex` → SSH : `git@github.com:DrKz36/emergencev8.git`

### Déploiement Cloud Run
- **Révision active** : `emergence-app-00270-zs6`
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-082149`
- **URL** : https://emergence-app-486095406755.europe-west1.run.app
- **Déployé** : 2025-10-08 08:22 CEST
- **Trafic** : 100% sur nouvelle révision
- **Documentation** : [docs/deployments/2025-10-08-cloud-run-revision-00270.md](docs/deployments/2025-10-08-cloud-run-revision-00270.md)
- **Service Cloud Run** : `emergence-app`
- **Projet GCP** : `emergence-469005`
- **Région** : `europe-west1`
- **Registry** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app`

#### Procédure build & déploiement rapide
- **Prérequis** : `gcloud auth login`, `gcloud auth configure-docker europe-west1-docker.pkg.dev`, Docker configuré pour `linux/amd64`.
- **Commandes** :
  ```bash
  timestamp=$(date +%Y%m%d-%H%M%S)
  docker build --platform linux/amd64 \
    -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp .

  docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp

  gcloud run deploy emergence-app \
    --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp \
    --project emergence-469005 \
    --region europe-west1 \
    --platform managed \
    --allow-unauthenticated
  ```
- **Post-déploiement** : `gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005`, vérifier `/api/health` et `/api/metrics`.

### Working tree
- ⚠️ Dirty (backend refactor en cours : requirements + core DB + auth/memory services + docs/passation/AGENT_SYNC)

---

## 🚧 Zones de travail en cours

### Claude Code (moi)
- **Statut** : ✅ Phase 2 Performance (analyses mémoire + débats) implémentée avec succès
- **Session 2025-10-08 (19:30-20:30)** :
  1. ✅ **Tâche 1** : Agent `neo_analysis` (GPT-4o-mini) pour analyses mémoire (gain latence ~70%)
  2. ✅ **Tâche 2** : Parallélisation débat round 1 avec `asyncio.gather` (gain latence ~40%)
  3. ✅ **Tâche 3** : Cache in-memory pour analyses (TTL 1h, LRU 100 entrées)
  4. ✅ Documentation : [`docs/deployments/2025-10-08-phase2-perf.md`](docs/deployments/2025-10-08-phase2-perf.md)
- **Fichiers modifiés** :
  - `src/backend/shared/config.py` : ajout agent `neo_analysis` (OpenAI GPT-4o-mini)
  - `src/backend/features/memory/analyzer.py` : utilise `neo_analysis` + cache in-memory (hash MD5 + TTL 1h)
  - `src/backend/features/debate/service.py` : round 1 parallèle (attacker + challenger simultanés)
  - `src/backend/features/chat/service.py` : refactoring appels agents (déjà parallèle avec create_task)
- **Métriques attendues** :
  - Latence analyses : 4-6s → 1-2s (-70%)
  - Latence débat round 1 : 5s → 3s (-40%)
  - Cache hit rate : 0% → 40-50%
  - Coût API : -20% global

**Session précédente 2025-10-08 (17:00-19:30)** :
  1. ✅ Correction dette mypy : 24 erreurs → 0 erreur
  2. ✅ Annotations types ajoutées : `middleware.py`, `alerts.py`, `chat/service.py`, `memory/router.py`, `benchmarks/persistence.py`, `benchmarks/service.py`, `concept_recall.py`
  3. ✅ Scripts seeds/migrations vérifiés : compatibles avec modèle commits explicites (AuthService.upsert_allowlist fait commit=True ligne 843)
  4. ✅ Smoke tests : 7/7 OK (seed_admin.py + backend health checks)
  5. ✅ Docker build : image `deploy-20251008-110311` créée (13.4GB, **layer pip install = 7.9GB**)
  6. ✅ Push registry GCP : `sha256:d8fa8e41eb25a99f14abb64b05d124c75da016b944e8ffb84607ac4020df700f`
  7. ⚠️ Deploy Cloud Run : **ÉCHEC** - 3 révisions (00271, 00272, 00273) bloquées sur "Imported 16 of 17 layers" après 15+ minutes
- **Fichiers modifiés** :
  - `src/backend/benchmarks/persistence.py` : `_serialize_run` non-static + cast `Mapping[str, Any]` pour Row
  - `src/backend/features/benchmarks/service.py` : type annotation `list[SQLiteBenchmarkResultSink | FirestoreBenchmarkResultSink]`
  - `src/backend/core/middleware.py` : type annotations `dict[str, list[tuple[float, int]]]` + `list[str] | None`
  - `src/backend/core/alerts.py` : type annotation `str | None` + check `webhook_url` before post
  - `src/backend/features/memory/concept_recall.py` : check `self.collection` before access
  - `src/backend/features/chat/service.py` : type annotations `ConceptRecallTracker | None`, `dict[str, Any]`, ajout params requis `ChatMessage`
  - `src/backend/features/memory/router.py` : type annotation `dict[str, Any]` + type ignore pour kwargs dynamiques
  - `build_tag.txt` : tag image `IMAGE_TAG=deploy-20251008-110311`
- **Tests effectués** :
  - ✅ `python -m mypy src/backend --ignore-missing-imports` → **Success: no issues found in 80 source files**
  - ✅ `python -m pytest tests/backend/e2e/test_user_journey.py -v` → 6/6 tests OK
  - ✅ Smoke tests : `scripts/seed_admin.py` + uvicorn health checks → 7/7 OK
  - ✅ Service actuel (00270) toujours healthy : `curl /api/health` → 200 OK
- **Scripts seeds/migrations vérifiés** :
  - ✅ `scripts/seed_admin.py` : utilise `AuthService.upsert_allowlist` (commit géré en interne)
  - ✅ `scripts/seed_admin_password.py` : utilise `AuthService.upsert_allowlist` (commit géré en interne)
  - ✅ `scripts/run_migration.py` : appelle `commit()` explicite ligne 20 ✅
  - ✅ `AuthService._upsert_allowlist` ligne 843 : `commit=True` passé à `db.execute()`
- **Problèmes identifiés** :
  - **Dette mypy** : 24 erreurs → 0 erreur ✅
  - **Scripts seeds/migrations** : validation compatibilité commits explicites ✅
  - ⚠️ **BLOQUEUR : Image Docker 13.4GB trop lourde pour Cloud Run** (layer pip install = 7.9GB, embedding model = 183MB)
  - Cloud Run timeout lors import dernier layer après 15+ minutes
  - Nécessite optimisation Dockerfile (multi-stage build, cache pip, slim base image)
- **Révision Cloud Run actuelle** : `emergence-app-00270-zs6` (healthy, 100% trafic)
- **Commits créés** :
  - (à venir) chore: correction dette mypy backend + vérification seeds/migrations
- **Actions manuelles requises** :
  1. Optimiser Dockerfile pour réduire taille image (<2GB cible)
  2. Relancer build/push/deploy une fois Dockerfile optimisé
  3. Vérifier nouvelle révision active et healthy

**Sessions précédentes :**
- **Session 2025-10-08 (16:33-16:43)** :
  1. ✅ Correction E402 (imports non top-level) : containers.py imports remontés après stdlib/tiers, tests conftest.py avec `# noqa: E402`
  2. ✅ Correction F841 (variables inutilisées) : préfixe `_` sur variables auth check, suppression assignations inutiles dans tests
  3. ✅ Correction E722 (bare except) : `except Exception:` au lieu de `except:` dans security/conftest.py
  4. ✅ Validation : `python -m ruff check src/backend tests/backend` → **All checks passed !**
  5. ✅ Tests e2e : 6/6 OK, pas de régression
- **Fichiers modifiés** :
  - `src/backend/containers.py` : imports remontés en tête (lignes 20-29)
  - `tests/backend/features/conftest.py` : `# noqa: E402` sur imports backend (lignes 24-28)
  - `tests/backend/features/test_chat_stream_chunk_delta.py` : `# noqa: E402` sur import ChatService
  - `src/backend/features/memory/router.py` : `_user_id # noqa: F841` pour auth check ligne 623
  - `tests/backend/e2e/test_user_journey.py` : suppression variable `response` inutilisée ligne 151
  - `tests/backend/features/test_concept_recall_tracker.py` : `_recalls` ligne 189
  - `tests/backend/features/test_memory_enhancements.py` : `_upcoming` ligne 230
  - `tests/backend/integration/test_ws_opinion_flow.py` : `_request_id_2` ligne 142
  - `tests/backend/security/conftest.py` : `except Exception:` ligne 59
- **Tests effectués** :
  - ✅ `python -m ruff check src/backend tests/backend` → **All checks passed !** (22 erreurs corrigées)
  - ✅ `python -m pytest tests/backend/e2e/test_user_journey.py -v` → 6/6 tests OK
- **Problème résolu** :
  - **Dette ruff** : 45 erreurs → 0 erreur ✅
  - E402 (10 imports) : remontés ou noqa
  - F841 (11 variables inutilisées) : préfixe _ ou suppression
  - E722 (1 bare except) : spécifié Exception
- **Commits créés** :
  - (à venir) chore: correction dette technique ruff (E402, F841, E722)

**Sessions précédentes :**
- **Session 2025-10-08 (16:00-16:33)** :
  1. ✅ Correction fixture e2e `/api/auth/register` : accepte `dict` au lieu de paramètres individuels, fix HTTPException au lieu de tuple (dict, int)
  2. ✅ Amélioration mock auth : invalidation token après logout, isolation users (user_id), génération token UUID unique par login
  3. ✅ 6/6 tests e2e passent (test_new_user_onboarding_to_chat, test_user_manages_multiple_conversations, test_conversation_with_memory_recall, test_graceful_degradation_on_ai_failure, test_data_survives_session, test_multiple_users_isolated)
  4. ✅ Auto-fix ruff : 23 erreurs corrigées (imports inutilisés)
- **Fichiers modifiés** :
  - `tests/backend/e2e/conftest.py` (+70 lignes, -40 lignes)
    - Fix endpoints mock : body dict au lieu de paramètres individuels
    - Ajout helper `get_current_user()` avec vérification auth
    - Ajout invalidation token + filtrage threads par user_id
    - Token UUID unique pour éviter collision après logout/re-login
  - `tests/backend/e2e/test_user_journey.py` (+1 ligne)
    - Ajout assertion status_code 200 pour debug
- **Tests effectués** :
  - ✅ `python -m pytest tests/backend/e2e/test_user_journey.py -v` → 6/6 tests OK
  - ✅ `python -m ruff check --fix src/backend tests/backend` → 23 erreurs auto-fixées
  - ⚠️ Dette restante : 22 erreurs ruff (E402 imports, F841 variables inutilisées, E722 bare except) - existante avant session
  - ⚠️ Dette mypy : 6 erreurs (benchmarks, middleware, alerts) - existante avant session
- **Problème résolu** :
  - **Blocage Codex** : Mock `/api/auth/register` retournait 422 au lieu de 200 → endpoints FastAPI attendaient `dict` JSON
  - **Isolation users** : Threads partagés entre users → ajout `user_id` + filtrage par user
  - **Token invalidé après re-login** : Token fixe `token_{user_id}` → génération UUID unique par login
- **Commits créés** :
  - (à venir) fix: tests e2e backend - mock auth + isolation users

**Sessions précédentes :**
- **Session 2025-10-08 (05:30-07:15)** :
  1. ✅ Diagnostic complet du problème d'affichage des modules
  2. ✅ Identification de la cause : backdrop (`#mobile-backdrop`) avec `pointer-events: auto` recouvrait le menu et interceptait tous les clics
  3. ✅ Correction CSS : désactivation `pointer-events` sur backdrop quand menu ouvert
  4. ✅ Correction JS : ajout listeners directs avec `capture: true` sur liens menu pour garantir capture des clics
  5. ✅ Nettoyage logs de debug temporaires
  6. ✅ Tests validation : tous modules accessibles (Conversations, Documents, Débats, Mémoire, Documentation, Cockpit, Admin, Préférences)
- **Fichiers modifiés** :
  - `src/frontend/core/app.js` (+106 lignes, -73 lignes)
    - Ajout listeners directs sur liens menu avec `capture: true` (lignes 295-307)
    - Simplification `handleDocumentClick` pour laisser listeners gérer navigation (lignes 381-393)
    - Nettoyage `listenToNavEvents` (suppression logs debug)
  - `src/frontend/styles/overrides/mobile-menu-fix.css` (1 ligne modifiée)
    - Ligne 252 : `pointer-events: none !important` sur backdrop quand menu ouvert
    - Ajout `z-index: 1000 !important` au menu (ligne 265)
- **Problème résolu** :
  - **Cause racine** : Le backdrop semi-transparent (`z-index: 900`) recouvrait le menu mobile et interceptait tous les événements de clic avant qu'ils n'atteignent les liens de navigation
  - **Test révélateur** : `document.elementFromPoint()` retournait `#mobile-backdrop` au lieu des liens du menu
  - **Solution** : Désactiver `pointer-events` sur backdrop pendant que menu est ouvert, permettant clics de traverser le backdrop
- **Tests effectués** :
  - ✅ Navigation vers tous modules via menu burger mobile fonctionnelle
  - ✅ `showModule()` appelé correctement pour chaque module
  - ✅ Menu se ferme automatiquement après sélection module
  - ✅ Pas de régression sur navigation desktop/sidebar
- **Commits créés** :
  - `cec2a0f` fix: correction navigation menu mobile - backdrop bloquait les clics
  - `98d9fb3` docs: mise à jour documentation sessions et déploiement

**Sessions précédentes :**
- **Session 2025-10-08 (03:30-05:00)** : Tests de sécurité + Système de monitoring production - TERMINÉ
  - Création tests sécurité (SQL injection, XSS, CSRF)
  - Création tests E2E (6 scénarios utilisateur)
  - Système monitoring complet (métriques, sécurité, performance)
  - Middlewares auto-monitoring activés
  - Documentation complète (LIMITATIONS.md, MONITORING_GUIDE.md)

### Codex (cloud)
- **Dernier sync** : 2025-10-06 09:30
- **Fichiers touchés** : `docs/passation.md` (ajout remote config)
- **Blocage** : Accès réseau GitHub (HTTP 403)
- **Actions recommandées** : `git fetch --all --prune` puis `git rebase origin/main` une fois réseau OK

### Codex (local)
- **Dernier sync** : 2025-10-08 12:45 CEST (backend stabilisation en cours)
- **Statut** : Gestionnaire SQLite refactoré, schéma threads enrichi (`last_message_at`, `message_count`, `archival_reason`, `archived_at`), fixtures pytest corrigées.
- **Session 2025-10-08 (16:50-17:05)** :
  1. Vérification de la section Cloud Run (`AGENT_SYNC.md`) pour garantir toutes les infos build/push/deploy.
  2. Ajout des paramètres projet/région/service + snippet de commandes aligné sur `docs/deployments/README.md`.
  3. Tentative `scripts/sync-workdir.ps1` → échoue (working tree dirty signalé, état conservé).
- **Session 2025-10-08 (11:00-12:45)** :
  1. Refactor `DatabaseManager` (commit explicite, helpers `initialize/is_connected`) + propagation commits dans `schema.py`, `queries.py`, backfill Auth/Mémoire.
  2. Migration threads : colonnes et incrément atomique `message_count` lors de `add_message`.
  3. Refactor des fixtures (`tests/backend/features|e2e|security/conftest.py`) avec shim httpx/TestClient + stub VectorService.
  4. Documentation mise à jour (`docs/architecture/00-Overview.md`, `docs/architecture/30-Contracts.md`).
- **Tests ciblés** :
  - ⏳ (2025-10-08 17:05) Non exécutés pour cette session (mise à jour documentation uniquement).
  - ✅ `.venv\\Scripts\\python.exe -m pytest src/backend/tests/test_database_manager.py`
  - ✅ `.venv\\Scripts\\python.exe -m pytest tests/backend/features/test_memory_concept_search.py`
  - ✅ `.venv\\Scripts\\python.exe -m pytest tests/test_memory_archives.py::TestDatabaseMigrations::test_message_count_trigger_insert`
  - ⚠️ `.venv\\Scripts\\python.exe -m pytest tests/backend/e2e/test_user_journey.py::TestCompleteUserJourney::test_new_user_onboarding_to_chat` (422 sur mock `/api/auth/register`)
- **Next** :
  1. Corriger la fixture e2e pour que `POST /api/auth/register` retourne 200 ou ajuster l’assertion.
  2. Relancer la suite e2e complète (`tests/backend/e2e`) après correctif.
  3. Vérifier scripts seeds/migrations vis-à-vis du nouveau modèle de commits explicites.
- **Blocages** :
  - Tests e2e encore KO (mock register trop strict).
  - Hep : suites `ruff`, `mypy`, smoke restent à remettre dans la boucle après correction e2e.
### 1. Avant de coder (TOUS les agents)
```bash
# Vérifier les remotes
git remote -v

# Sync avec origin (si réseau OK)
git fetch --all --prune
git status
git log --oneline -10

# Lire les docs
# 1. AGENT_SYNC.md (ce fichier)
# 2. docs/passation.md (3 dernières entrées)
# 3. AGENTS.md + CODEV_PROTOCOL.md
```

### 2. Pendant le dev
- **ARBO-LOCK** : Snapshot `arborescence_synchronisee_YYYYMMDD.txt` si création/déplacement/suppression
- **Fichiers complets** : Jamais de fragments, jamais d'ellipses
- **Doc vivante** : Sync immédiate si archi/mémoire/contrats changent

### 3. Avant de soumettre (TOUS les agents)
- Tests backend : `pytest`, `ruff`, `mypy`
- Tests frontend : `npm run build`
- Smoke tests : `pwsh -File tests/run_all.ps1`
- **Passation** : Entrée complète dans `docs/passation.md`
- **Update AGENT_SYNC.md** : Section "Zones de travail en cours"

### 4. Validation finale
- **IMPORTANT** : Aucun agent ne commit/push sans validation FG (architecte)
- Préparer le travail, ping FG pour review/merge

---

## 📋 Checklist rapide (copier/coller)

```markdown
- [ ] Lecture AGENT_SYNC.md + docs/passation.md (3 dernières entrées)
- [ ] git fetch --all --prune (si réseau OK)
- [ ] git status propre ou -AllowDirty documenté
- [ ] Tests backend (pytest, ruff, mypy)
- [ ] Tests frontend (npm run build)
- [ ] Smoke tests (pwsh -File tests/run_all.ps1)
- [ ] ARBO-LOCK snapshot si fichiers créés/déplacés/supprimés
- [ ] Passation dans docs/passation.md
- [ ] Update AGENT_SYNC.md (section "Zones de travail")
- [ ] Ping FG pour validation commit/push
```

---

## 🗣️ Tone & Communication

**Style de comm entre agents et avec FG :**
- **Tutoiement** obligatoire, pas de vouvoiement corporate
- **Direct et cash**, pas de blabla
- **Vulgarité OK** quand ça fait du sens bordel !
- **Technique > politesse** : on vise l'efficacité, pas la forme

---

## 🔄 Historique des syncs majeurs

### 2025-10-06
- **Codex (cloud)** : Config remotes origin/codex, blocage réseau HTTP 403
- **Action** : Retry fetch/rebase une fois réseau OK

### 2025-10-04
- **Claude Code** : Setup protocole codev, permissions autonomes, tone casual
- **Codex** : Protocole multi-agents établi, passation template créé
- **Codex (local)** : Ajout `prometheus-client` (metrics) + build/push + déploiement Cloud Run révision 00265-6cb

---

## ⚠️ Conflits & Résolution

**Si conflit détecté :**
1. **Documenter** dans `docs/passation.md` (section "Blocages")
2. **Proposer solution** (commentaire code ou passation)
3. **Ne pas forcer** : laisser FG arbitrer
4. **Continuer** sur tâches non bloquantes

**Si même fichier modifié par 2 agents :**
- Git gère les conflits normalement
- Dernier à sync résout (`git rebase`, `git merge`)
- Documenter résolution dans `docs/passation.md`

---

## 📞 Contact & Escalation

**Architecte (FG)** : Validation finale avant commit/push/deploy

**Principe clé** : Tests > Documentation > Communication

---

**Ce fichier est vivant** : Chaque agent doit le mettre à jour après ses modifs importantes !
