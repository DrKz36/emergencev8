# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Dernière mise à jour** : 2025-10-05 12:50 CET (Claude Code - Déploiement)

---

## 🔥 Lecture OBLIGATOIRE avant toute session de code

**Ordre de lecture pour tous les agents :**
1. Ce fichier (`AGENT_SYNC.md`) — état actuel du dépôt
2. [`AGENTS.md`](AGENTS.md) — consignes générales
3. [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md) — protocole multi-agents
4. [`docs/passation.md`](docs/passation.md) — 3 dernières entrées minimum
5. `git status` + `git log --oneline -10` — état Git

---

## 📍 État actuel du dépôt (2025-10-05)

### Branche active
- **Branche courante** : `main`
- **Derniers commits** :
  - `d5ee4a4` docs: update passation and agent sync after audit fixes
  - `4bad1fe` fix: apply audit corrections (critical + major + minor)
  - `6c30f2e` feat: add comprehensive metrics tracking and documentation system

### Remotes configurés
- `origin` → HTTPS : `https://github.com/DrKz36/emergencev8.git`
- `codex` → SSH : `git@github.com:DrKz36/emergencev8.git`

### Déploiement Cloud Run
- **Révision active** : `emergence-app-00266-jc4`
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251005-123837`
- **URL** : https://emergence-app-486095406755.europe-west1.run.app
- **Déployé** : 2025-10-05 12:45 CET
- **Trafic** : 100% sur nouvelle révision
- **Documentation** : [docs/deployments/2025-10-05-audit-fixes-deployment.md](docs/deployments/2025-10-05-audit-fixes-deployment.md)

### Working tree
✅ Clean (tous changements commités et pushés)

---

## 🚧 Zones de travail en cours

### Claude Code (moi)
- **Statut** : ✅ Déploiement Cloud Run terminé (révision 00266-jc4 active)
- **Session complète** :
  1. ✅ Corrections audit (13 fixes: 3 critiques + 6 majeurs + 4 mineurs)
  2. ✅ Tests backend (8/8 passent, httpx v0.27.2 installé)
  3. ✅ Build frontend (succès 756ms, bundle conversations généré)
  4. ✅ Build Docker image (13.3 GB, push Artifact Registry)
  5. ✅ Deploy Cloud Run (révision 00266-jc4, 100% trafic)
  6. ✅ Documentation déploiement créée
- **Fichiers touchés** :
  - `requirements.txt`, `package.json`
  - `src/frontend/core/app.js`, `websocket.js`, `shared/constants.js`
  - `docs/architecture/10-Components.md`, `30-Contracts.md`
  - `docs/TUTORIAL_SYSTEM.md`, `docs/passation.md`
  - `docs/deployments/2025-10-05-audit-fixes-deployment.md` (nouveau)
  - `docs/deployments/README.md` (nouveau)
  - `AGENT_SYNC.md` (ce fichier)
- **Prochain chantier** : QA manuelle Cloud Run + monitoring métriques Prometheus

### Codex (cloud)
- **Dernier sync** : 2025-10-06 09:30
- **Fichiers touchés** : `docs/passation.md` (ajout remote config)
- **Blocage** : Accès réseau GitHub (HTTP 403)
- **Actions recommandées** : `git fetch --all --prune` puis `git rebase origin/main` une fois réseau OK

### Codex (local)
- **Dernier sync** : 2025-10-04 21:10
- **Statut** : Build Docker + déploiement Cloud Run (révision 00265-6cb)
- **Fichiers touchés** :
  - `requirements.txt` (ajout bloc Monitoring + `prometheus-client`)
  - `docs/passation.md` (entrée session)
- **Tests** :
  - `pytest tests/backend/features/test_concept_recall_tracker.py`
  - Vérification santé Cloud Run (`/api/health`)
- **Next** :
  - Surveiller logs `severity>=ERROR`
  - Lancer smoke WS Cloud Run
  - Ajouter garde-fou CI pour dépendances metrics

---

## 🔒 Règles anti-collision

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
