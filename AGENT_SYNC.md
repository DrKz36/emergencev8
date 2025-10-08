# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Derniere mise a jour** : 2025-10-08 07:15 CEST (Claude Code - fix navigation menu mobile)

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
  - `98d9fb3` docs: mise à jour documentation sessions et déploiement
  - `cec2a0f` fix: correction navigation menu mobile - backdrop bloquait les clics
  - `da5b625` feat: harmonisation UI cockpit et hymne avec design system

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
