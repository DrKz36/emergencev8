# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Derniere mise a jour** : 2025-10-08 03:30 CEST (Claude Code - fix layout CSS Grid)

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
- **Statut** : ✅ Fix CSS Grid layout + marges équilibrées - TERMINÉ
- **Session 2025-10-08 (01:00-03:30)** :
  1. ✅ Investigation marge droite excessive sur tous les modules
  2. ✅ Identification problème : CSS Grid avec 3 enfants au lieu de 2 (app-header comptait dans la grille)
  3. ✅ Fix `.app-header` retiré du flux Grid en desktop avec `position: absolute`
  4. ✅ Ajustement padding `.app-content` : 16px gauche, 24px droite
  5. ✅ Documentation complète dans AGENT_SYNC.md et passation.md
- **Fichiers touchés** :
  - `src/frontend/styles/core/_layout.css` (fix .app-header grid-area + position absolute, padding .app-content)
  - `src/frontend/styles/overrides/ui-hotfix-20250823.css` (padding .app-content desktop)
- **Problème résolu** :
  - **Cause racine** : `.app-header` présent dans le DOM avec 3 enfants directs de `.app-container` causait un grid-template-columns erroné (257px 467px 0px 197px au lieu de 258px 1fr)
  - **Solution** : `.app-header` forcé en `position: absolute` + `display: none !important` en desktop pour le retirer complètement du flux Grid
  - **Résultat** : Contenu principal prend maintenant toute la largeur disponible avec marges équilibrées (16px gauche / 24px droite)
- **Tests effectués** :
  - Analyse DevTools (grid-template-columns vérifié)
  - Validation visuelle sur Dialogue, Documents, Conversations, Débats, Mémoire
  - npm run build ✅
- **Prochain chantier** : Tests responsives mobile + validation QA complète

### Codex (cloud)
- **Dernier sync** : 2025-10-06 09:30
- **Fichiers touchés** : `docs/passation.md` (ajout remote config)
- **Blocage** : Accès réseau GitHub (HTTP 403)
- **Actions recommandées** : `git fetch --all --prune` puis `git rebase origin/main` une fois réseau OK

### Codex (local)
- **Dernier sync** : 2025-10-07 19:30 CEST (Codex - alignement marge droite)
- **Statut** : Marges gauche/droite synchronisées, overrides de centrage neutralisés sur Dialogue/Documents/Cockpit.
- **Fichiers touchés** :
  - `src/frontend/styles/core/_layout.css`
  - `src/frontend/styles/overrides/ui-hotfix-20250823.css`
  - `src/frontend/features/threads/threads.css`
  - `src/frontend/features/cockpit/cockpit-{metrics,charts,insights}.css`
  - `src/frontend/features/documentation/documentation.css`
  - `src/frontend/features/settings/settings-{ui,security}.css`
  - `index.html` (ordre importmap / modulepreload)
- **Tests** :
  - ok `npm run build` (warning importmap toujours présent)
- **Next** :
  - QA visuelle desktop (1280/1440/1920) + responsive 1024/768 sur Dialogue/Documents/Cockpit pour valider l'alignement.
  - Contrôler Admin/Timeline/Memory pour repérer d'éventuels overrides de centrage restants.
  - Planifier la correction de l'avertissement importmap dans `index.html`.
- **Blocages** :
  - `scripts/sync-workdir.ps1` échoue (working tree toujours dirty : fichiers admin/icons hors scope).
  - Suites backend (`python -m pytest`, `ruff check`, `mypy src`) encore KO (sessions précédentes).
  - `pwsh -File tests/run_all.ps1` non lancé sur cette branche.
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
