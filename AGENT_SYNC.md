# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Dernière mise à jour** : 2025-10-07 06:30 CEST (Claude Code - Polish UI Dialogue)

---

## 🔥 Lecture OBLIGATOIRE avant toute session de code

**Ordre de lecture pour tous les agents :**
1. Ce fichier (`AGENT_SYNC.md`) — état actuel du dépôt
2. [`AGENTS.md`](AGENTS.md) — consignes générales
3. [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md) — protocole multi-agents
4. [`docs/passation.md`](docs/passation.md) — 3 dernières entrées minimum
5. `git status` + `git log --oneline -10` — état Git

---

## 📍 État actuel du dépôt (2025-10-06)

### Branche active
- **Branche courante** : `main`
- **Derniers commits** :
  - `a6b1ee6` feat: refonte complète des personnalités des agents ANIMA, NEO et NEXUS
  - `32e5382` feat: optimize sidebar layout and improve mobile navigation
  - `67cbf32` feat: enrich Genesis section with comprehensive timeline and documentation

### Remotes configurés
- `origin` → HTTPS : `https://github.com/DrKz36/emergencev8.git`
- `codex` → SSH : `git@github.com:DrKz36/emergencev8.git`

### Déploiement Cloud Run
- **Révision active** : `emergence-app-00268-9s8`
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251006-060538`
- **URL** : https://emergence-app-486095406755.europe-west1.run.app
- **Déployé** : 2025-10-06 06:06 CEST
- **Trafic** : 100% sur nouvelle révision
- **Documentation** : [docs/deployments/2025-10-06-agents-ui-refresh.md](docs/deployments/2025-10-06-agents-ui-refresh.md)

### Working tree
- ⚠️ Dirty (modifs front existantes + fichiers sources extraites)

---

## 🚧 Zones de travail en cours

### Claude Code (moi)
- **Statut** : ✅ Routine doc collaborative intégrée + Polish UI terminé
- **Session 2025-10-07 (06:00-06:45)** :
  1. ✅ Analyse et correction des marges latérales déséquilibrées (dialogue)
  2. ✅ Correction largeur app-container (100vw, suppression marges excessives)
  3. ✅ Harmonisation scrollbar (rgba(71,85,105,.45)) appliquée globalement
  4. ✅ Optimisation responsive layout (compensation sidebar visuelle)
  5. ✅ **Intégration routine doc collaborative automatique**
  6. ✅ Documentation mise à jour (AGENT_SYNC.md, passation.md)
- **Fichiers touchés** :
  - `src/frontend/styles/core/_layout.css` (app-container width, app-content padding)
  - `src/frontend/styles/core/reset.css` (scrollbar globale + body/html overflow fix)
  - `src/frontend/features/chat/chat.css` (messages padding, chat-container width)
  - `.claude/instructions/style-fr-cash.md` (routine doc ajoutée)
  - `.claude/instructions/doc-sync-routine.md` (NOUVEAU - guide complet)
  - `AGENTS.md` (checklist clôture mise à jour)
  - `.git/hooks/pre-commit-docs-reminder.ps1` (NOUVEAU - hook optionnel)
  - `docs/README-DOC-SYNC.md` (NOUVEAU - documentation système)
- **Changements clés** :
  - Scrollbar globale fine (8px) avec couleur harmonisée sur tous les modules
  - App-container à 100vw (plus de largeur fixe)
  - Padding dialogue équilibré visuellement (compense sidebar 258px)
  - **Routine doc collaborative intégrée dans instructions Claude Code**
  - Rappel automatique : "Mets à jour AGENT_SYNC.md et docs/passation.md"
- **Tests effectués** : Analyse visuelle avec captures d'écran utilisateur
- **Prochain chantier** : Tests responsives mobile + validation QA complète

### Codex (cloud)
- **Dernier sync** : 2025-10-06 09:30
- **Fichiers touchés** : `docs/passation.md` (ajout remote config)
- **Blocage** : Accès réseau GitHub (HTTP 403)
- **Actions recommandées** : `git fetch --all --prune` puis `git rebase origin/main` une fois réseau OK

### Codex (local)
- **Dernier sync** : 2025-10-07 03:19
- **Statut** : Burger menu mobile interactif (backdrop clair); build front OK
- **Fichiers touches** :
  - `src/frontend/styles/overrides/mobile-menu-fix.css`
  - `docs/passation.md`
  - `AGENT_SYNC.md`
- **Tests** :
  - ok `npm run build` (warning importmap existant)
  - a relancer `python -m pytest` (7 erreurs fixture `app`)
  - a relancer `ruff check` (28 erreurs existantes)
  - a relancer `mypy src` (12 erreurs existantes)
  - non lance `pwsh -File tests/run_all.ps1`
- **Next** :
  - QA responsive mobile (<=760px) pour valider burger/backdrop/Escape.
  - Fusionner/rationaliser les overrides `mobile-menu-fix.css` & `ui-hotfix` après validation.
  - Traiter l'avertissement importmap dans `index.html` quand possible.
- **Blocages** :
  - `scripts/sync-workdir.ps1` echoue (working tree dirty; rebase impossible tant que les autres modifs front ne sont pas commit/stash).
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
