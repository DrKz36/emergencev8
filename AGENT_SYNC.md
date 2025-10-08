# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Derniere mise a jour** : 2025-10-08 12:45 CEST (Codex - Backend stabilisation tests)

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

### Working tree
- ⚠️ Dirty (backend refactor en cours : requirements + core DB + auth/memory services + docs/passation/AGENT_SYNC)

---

## 🚧 Zones de travail en cours

### Claude Code (moi)
- **Statut** : ✅ Navigation menu mobile corrigée - TERMINÉ
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
- **Session 2025-10-08 (11:00-12:45)** :
  1. Refactor `DatabaseManager` (commit explicite, helpers `initialize/is_connected`) + propagation commits dans `schema.py`, `queries.py`, backfill Auth/Mémoire.
  2. Migration threads : colonnes et incrément atomique `message_count` lors de `add_message`.
  3. Refactor des fixtures (`tests/backend/features|e2e|security/conftest.py`) avec shim httpx/TestClient + stub VectorService.
  4. Documentation mise à jour (`docs/architecture/00-Overview.md`, `docs/architecture/30-Contracts.md`).
- **Tests ciblés** :
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
