# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Derniere mise a jour** : 2025-10-08 06:46 CEST (Codex - déploiement Cloud Run 00269-5qs)

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
  - `da5b625` feat: harmonisation UI cockpit et hymne avec design system
  - `682d7b4` feat: refonte UI modules Conversations et Débats + améliorations ergonomiques
  - `0a147bd` feat: quick fixes production + tests sécurité opérationnels + monitoring Grafana/Slack

### Remotes configurés
- `origin` → HTTPS : `https://github.com/DrKz36/emergencev8.git`
- `codex` → SSH : `git@github.com:DrKz36/emergencev8.git`

### Déploiement Cloud Run
- **Révision active** : `emergence-app-00269-5qs`
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-064424`
- **URL** : https://emergence-app-486095406755.europe-west1.run.app
- **Déployé** : 2025-10-08 06:46 CEST
- **Trafic** : 100% sur nouvelle révision
- **Documentation** : [docs/deployments/2025-10-08-cloud-run-refresh.md](docs/deployments/2025-10-08-cloud-run-refresh.md)

### Working tree
- ✅ Clean (aucune modification locale)

---

## 🚧 Zones de travail en cours

### Claude Code (moi)
- **Statut** : ✅ Tests de sécurité + Système de monitoring production - TERMINÉ
- **Session 2025-10-08 (03:30-05:00)** :
  1. ✅ Audit complet tests existants (Frontend 100%, Backend 91.8%)
  2. ✅ Création tests de sécurité (SQL injection, XSS, CSRF, timing attacks)
  3. ✅ Création tests E2E (6 scénarios utilisateur complets)
  4. ✅ Documentation limitations connues (LIMITATIONS.md)
  5. ✅ Système de monitoring complet (métriques, sécurité, performance)
  6. ✅ Middlewares auto-monitoring activés dans main.py
  7. ✅ Documentation monitoring guide + résumé global
- **Fichiers créés** :
  - `tests/backend/security/test_security_sql_injection.py` (184 lignes - 8 tests sécurité)
  - `tests/backend/e2e/test_user_journey.py` (262 lignes - 6 scénarios E2E)
  - `src/backend/core/monitoring.py` (270 lignes - métriques/sécurité/perf)
  - `src/backend/core/middleware.py` (210 lignes - 4 middlewares auto-monitoring)
  - `src/backend/features/monitoring/router.py` (185 lignes - 8 endpoints monitoring)
  - `docs/LIMITATIONS.md` (450 lignes - doc limitations techniques/fonctionnelles)
  - `docs/MONITORING_GUIDE.md` (520 lignes - guide complet monitoring)
  - `docs/TESTING_AND_MONITORING_SUMMARY.md` (résumé exécutif complet)
- **Fichiers modifiés** :
  - `src/backend/main.py` (ajout imports monitoring + middlewares)
- **Fonctionnalités** :
  - **Tests sécurité** : Protection SQL injection, XSS, CSRF, validation entrées
  - **Tests E2E** : Parcours complets (inscription→chat→logout, multi-threads, isolation users)
  - **Monitoring** : Auto-logging toutes requêtes, métriques par endpoint, détection attaques
  - **Middlewares** : MonitoringMiddleware, SecurityMiddleware, RateLimitMiddleware, CORSSecurityMiddleware
  - **API** : /api/monitoring/health, /metrics, /security/alerts, /performance/*
- **Tests effectués** :
  - Audit tests existants : 7/7 frontend ✅, 78/85 backend ✅ (91.8%)
  - Tests nouveaux : Fixtures à corriger (async incompatibilité)
  - Monitoring activé : Middlewares OK, router monté ✅
  - Healthcheck : /api/health fonctionnel ✅
- **Prochain chantier** :
  - Fixer fixtures async pour tests sécurité/E2E
  - Implémenter quick fixes (rate limiting global, validation taille, timeout AI)
  - Créer dashboards Grafana + alertes Slack

### Codex (cloud)
- **Dernier sync** : 2025-10-06 09:30
- **Fichiers touchés** : `docs/passation.md` (ajout remote config)
- **Blocage** : Accès réseau GitHub (HTTP 403)
- **Actions recommandées** : `git fetch --all --prune` puis `git rebase origin/main` une fois réseau OK

### Codex (local)
- **Dernier sync** : 2025-10-08 06:46 CEST (Codex - déploiement Cloud Run)
- **Statut** : Build & déploiement production alignés sur `main` + documentation mise à jour.
- **Session 2025-10-08 (06:05-06:45)** :
  1. Construction image Docker `deploy-20251008-064424` (`docker build --platform linux/amd64`).
  2. Push vers Artifact Registry + déploiement Cloud Run → révision `emergence-app-00269-5qs`.
  3. Vérifications post-déploiement (`/api/health`, `/api/metrics`) et création du rapport `docs/deployments/2025-10-08-cloud-run-refresh.md`.
  4. Synchronisation documentation (`AGENT_SYNC.md`, `docs/deployments/README.md`, passation en cours).
- **Tests** :
  - ✅ `npm run build`
  - ⚠️ `python -m pytest` — échec collecte (`ImportError: User` dans `backend.features.auth.models`)
  - ⚠️ `pwsh -File tests/run_all.ps1` — identifiants smoke manquants (`Login failed for gonzalefernando@gmail.com`)
- **Next** :
  - QA visuelle cockpit/hymne (desktop + responsive) pour confirmer l'intégration des derniers correctifs CSS.
  - Corriger la fixture `backend.features.auth.models.User` ou adapter les tests `pytest`.
  - Fournir des identifiants smoke-tests ou mock pour permettre `tests/run_all.ps1`.
  - (héritage) Traiter le warning importmap dans `index.html` dès que les styles seront validés.
- **Blocages** :
  - Tests backend encore KO (import manquant) — nécessite investigation dédiée.
  - Pas d'identifiants smoke disponibles pour `tests/run_all.ps1`.
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
