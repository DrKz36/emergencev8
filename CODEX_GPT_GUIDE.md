# Guide Codex GPT — Emergence V8

**Version** : 1.0
**Date** : 2025-10-16
**Agent** : Codex GPT (OpenAI)
**Architecte** : FG (validation finale avant commit/push/deploy)

---

## 0. Bienvenue Codex GPT

Ce document est votre **guide de référence** pour collaborer efficacement sur le projet Emergence V8 en tant que co-développeur IA.

Vous travaillez en **égalité technique** avec Claude Code et d'autres agents IA. Chacun peut modifier n'importe quel fichier du dépôt, sous validation finale de l'architecte humain (FG).

---

## 1. Lecture obligatoire avant toute session

**Ordre de lecture (RESPECTER CET ORDRE)** :

1. **[AGENT_SYNC.md](AGENT_SYNC.md)** — État actuel du dépôt, progression, déploiement
2. **Ce fichier (CODEX_GPT_GUIDE.md)** — Consignes spécifiques Codex GPT
3. **[CODEV_PROTOCOL.md](CODEV_PROTOCOL.md)** — Protocole de co-développement multi-agents
4. **[docs/passation.md](docs/passation.md)** — Dernières 3 entrées minimum (contexte, blocages, next actions)
5. **[docs/MYPY_STYLE_GUIDE.md](docs/MYPY_STYLE_GUIDE.md)** ⭐ — Guide mypy (type hints OBLIGATOIRES pour code Python)
6. **`git status` + `git log --oneline -10`** — État Git actuel

**Temps de lecture estimé** : 10-15 minutes (investissement OBLIGATOIRE pour éviter erreurs et conflits)

---

## 2. Principes fondamentaux

### 2.1 Égalité technique
- ✅ Vous êtes un **co-développeur** de niveau ingénieur équivalent à Claude Code
- ✅ Vous pouvez modifier **n'importe quel fichier** du dépôt (backend Python, frontend JavaScript, docs, scripts)
- ✅ Vous pouvez **compléter ou corriger** le travail d'autres agents
- ❌ Vous ne pouvez **jamais bloquer** un fichier ou une fonctionnalité

### 2.2 Validation architecte
- **L'architecte (FG)** est le seul point de validation avant :
  - `git commit`
  - `git push`
  - Déploiement Google Cloud Run
- **Vous ne committez jamais seuls** : vous préparez les changements et les soumettez pour revue

### 2.3 Communication asynchrone
- **Via Git** : commits atomiques, branches explicites
- **Via documentation** : `docs/passation.md` (journal chronologique), `AGENT_SYNC.md` (état global)
- **Pas de canal externe** : tout passe par le dépôt

---

## 3. Zones de responsabilité suggérées (non bloquantes)

**Codex GPT privilégie (mais n'est pas limité à)** :

### Frontend JavaScript
- Modules UI : `src/frontend/features/*`
- Core frontend : `src/frontend/core/*` (state-manager, websocket, event-bus)
- Composants : `src/frontend/components/*`
- Styles : `src/frontend/styles/*`

### Scripts PowerShell
- `scripts/bootstrap.ps1`, `scripts/sync-workdir.ps1`
- `scripts/deploy-*.ps1`
- Tests PowerShell : `tests/*.ps1`

### Documentation utilisateur
- `README.md`
- `GUIDE_INTERFACE_BETA.md`
- `docs/FAQ.md`
- Guides tutoriels

### UI/UX
- Responsive design
- Accessibilité
- Branding et thèmes
- Intégration graphique

**Important** : Ces zones sont **indicatives**. Vous pouvez intervenir partout si nécessaire, y compris sur le backend Python ou l'architecture.

---

## 4. Workflow de session

### 4.1 Démarrage de session

**Checklist obligatoire** :

- [ ] Lire `AGENT_SYNC.md` (état actuel du dépôt)
- [ ] Lire ce fichier (`CODEX_GPT_GUIDE.md`)
- [ ] Lire `CODEV_PROTOCOL.md` (protocole inter-agents)
- [ ] Lire les 3 dernières entrées de `docs/passation.md`
- [ ] Exécuter `git status` et `git log --oneline -10`
- [ ] Vérifier que l'environnement est propre (pas de fichiers non suivis suspects)

**Environnement** :
- Python 3.11 dans un virtualenv
- Node.js 18+ (via nvm recommandé)
- Docker (pour tests et déploiement)

**Note sur Claude Code** :
- Claude Code utilise `.claude/settings.local.json` avec `"allow": ["*"]` pour l'exécution automatique
- Cette configuration permet à Claude Code de travailler en mode continu sans interruption
- Si tu travailles avec l'architecte, sache que Claude Code peut maintenant exécuter toutes les tâches automatiquement

### 4.2 Pendant le développement

**Règles d'or** :

1. **Avancer sans interruption** : bouclage de l'ensemble des tâches identifiées avant de solliciter l'utilisateur, sauf dépendance bloquante
2. **Respecter la structure** : `src/backend`, `src/frontend`, `docs`, etc.
3. **Code complet obligatoire** : pas d'ellipses, pas de fragments
4. **Tests systématiques** : créer les tests pour tout nouveau fichier
5. **Documentation synchronisée** : mettre à jour `docs/` si changement d'architecture ou de responsabilités

**Anti-patterns à éviter** :

- ❌ Livrer des fragments de code
- ❌ Modifier sans tester
- ❌ Ignorer l'architecture existante
- ❌ **Coder Python sans type hints** (voir `docs/MYPY_STYLE_GUIDE.md`)
- ❌ Oublier de documenter dans `docs/passation.md`

### 4.3 Clôture de session

**Checklist obligatoire** :

- [ ] **Tests frontend** : `npm run build` ✅
- [ ] **Tests backend** (si modifié) : `pytest` ✅
- [ ] **Smoke tests** (si modifié) : `pwsh -File tests/run_all.ps1` ✅
- [ ] **Linters** : `ruff check src/backend/`, `mypy src/backend/` (STRICT - 0 erreurs), ESLint (frontend si configuré) ✅
- [ ] **Documentation** : mise à jour `docs/passation.md` (nouvelle entrée complète en haut) ✅
- [ ] **AGENT_SYNC.md** : mise à jour section "Codex GPT" avec timestamp et fichiers touchés ✅
- [ ] **Git propre** : `git status` sans fichiers non suivis suspects ✅
- [ ] **Passation** : entrée complète dans `docs/passation.md` avec format standard ✅

**Format de passation** (template) :

```markdown
## [YYYY-MM-DD HH:MM] — Agent: Codex GPT

### Fichiers modifiés
- `src/frontend/features/chat/chat-ui.js` (ajout bouton export)
- `src/frontend/styles/modules/chat.css` (styles bouton)
- `docs/passation.md` (cette entrée)

### Contexte
Implémentation feature export conversations en CSV/PDF selon roadmap P0.3.
Ajout bouton "Exporter" dans l'interface chat avec menu déroulant (CSV/PDF).
Intégration avec backend endpoint `POST /api/export/conversation`.

### Tests
- ✅ `npm run build` (aucune erreur)
- ✅ Test manuel : export CSV fonctionne
- ✅ Test manuel : export PDF fonctionne
- ❌ Tests automatisés frontend à ajouter (TODO)

### Prochaines actions recommandées
1. Ajouter tests automatisés frontend pour export (Jest ou Cypress)
2. Améliorer UX : toast de confirmation après export
3. Documenter feature dans `GUIDE_INTERFACE_BETA.md`

### Blocages
Aucun.
```

---

## 5. Tests et qualité

### 5.1 Tests frontend

**Obligatoire avant toute soumission** :

```bash
# Build frontend (OBLIGATOIRE)
npm run build

# Tests unitaires (si configurés)
npm run test

# Linting (si configuré)
npm run lint
```

### 5.2 Tests backend (si modifié)

```bash
# Tests backend complets
pytest

# Tests backend ciblés
pytest tests/backend/features/test_chat.py

# Linting backend
ruff check src/backend/
mypy src/backend/
```

### 5.3 Smoke tests

```bash
# Tests rapides endpoints critiques
pwsh -File tests/run_all.ps1
```

### 5.4 Critères de qualité

- ✅ **Aucune erreur** dans `npm run build`
- ✅ **Coverage >80%** pour nouveau code (si tests unitaires configurés)
- ✅ **Pas de secrets** dans le code (vérifier `git diff`)
- ✅ **Documentation à jour** (`docs/passation.md`, architecture si impacté)

---

## 6. Conventions de code

### 6.1 Frontend JavaScript

**Style** :
- ES6+ moderne (async/await, arrow functions, destructuring)
- Modules ESM (import/export)
- PascalCase pour classes/composants
- camelCase pour variables/fonctions
- UPPER_SNAKE_CASE pour constantes

**Exemple** :
```javascript
// ✅ Bon
class ChatModule {
  async sendMessage(text) {
    const result = await this.apiClient.post('/api/chat/message', { text });
    return result;
  }
}

// ❌ Mauvais
function send_message(text) {  // snake_case non recommandé en JS
  return fetch('/api/chat/message', { method: 'POST', body: text });  // pas async/await
}
```

**Structure** :
- Un module par fichier (pas de mega-fichiers)
- Séparation UI / logique métier
- EventBus pour communication inter-modules
- StateManager pour état global

### 6.2 PowerShell

**Style** :
- PascalCase pour paramètres (`-SkipTests`, `-NoPush`)
- kebab-case pour noms de fichiers (`sync-workdir.ps1`)
- Commentaires explicites
- Gestion d'erreurs robuste (`try/catch`, `$ErrorActionPreference`)

**Exemple** :
```powershell
# ✅ Bon
param(
  [switch]$SkipTests,
  [switch]$NoPush
)

try {
  Write-Host "Building frontend..." -ForegroundColor Green
  npm run build
  if ($LASTEXITCODE -ne 0) {
    throw "Build failed"
  }
} catch {
  Write-Error "Error: $_"
  exit 1
}
```

### 6.3 Documentation Markdown

**Style** :
- Titres hiérarchiques (`#`, `##`, `###`)
- Listes à puces ou numérotées
- Blocs de code avec syntaxe highlight (```bash, ```javascript, ```python)
- Tables pour données structurées
- Émojis pour signalisation visuelle (✅, ❌, ⚠️, 🚀, 📋)

---

## 7. Architecture et références

### 7.1 Documentation architecture

**Lire avant toute modification structurelle** :

- [docs/architecture/00-Overview.md](docs/architecture/00-Overview.md) — Vue C4 Contexte & Conteneurs
- [docs/architecture/10-Components.md](docs/architecture/10-Components.md) — Composants backend/frontend
- [docs/architecture/30-Contracts.md](docs/architecture/30-Contracts.md) — Contrats API et WebSocket
- [docs/Memoire.md](docs/Memoire.md) — Système mémoire STM/LTM

### 7.2 Structure du projet

```
emergenceV8/
├── src/
│   ├── backend/          # Backend Python (FastAPI)
│   │   ├── core/         # Services centraux (DB, DI)
│   │   ├── features/     # Features (chat, memory, auth, etc.)
│   │   └── shared/       # Utilitaires partagés
│   └── frontend/         # Frontend JavaScript (ESM)
│       ├── core/         # StateManager, WebSocket, EventBus
│       ├── features/     # Modules UI (chat, dashboard, etc.)
│       ├── components/   # Composants réutilisables
│       └── styles/       # CSS global et modules
├── docs/                 # Documentation technique
│   ├── architecture/     # Docs architecture (C4)
│   ├── backend/          # Docs backend par feature
│   └── passation.md      # Journal inter-agents
├── scripts/              # Scripts PowerShell/Bash
├── tests/                # Tests backend/frontend
├── AGENT_SYNC.md         # État synchronisation inter-agents
├── CODEV_PROTOCOL.md     # Protocole co-développement
├── CODEX_GPT_GUIDE.md    # Ce fichier
└── README.md             # Documentation principale
```

### 7.3 Endpoints backend principaux

**Chat** :
- `POST /api/chat/message` — Envoyer un message
- `GET /api/threads` — Liste des conversations
- `WS /ws/{session_id}` — WebSocket temps réel

**Mémoire** :
- `POST /api/memory/tend-garden` — Consolidation mémoire
- `POST /api/memory/clear` — Reset mémoire
- `GET /api/memory/stats` — Statistiques mémoire

**Dashboard** :
- `GET /api/dashboard/costs/summary` — Résumé coûts
- `GET /api/dashboard/timeline/activity` — Timeline activité
- `GET /api/admin/dashboard/global` — Stats globales (admin)

**Auth** :
- `POST /api/auth/login` — Connexion
- `POST /api/auth/logout` — Déconnexion
- `POST /api/auth/request-password-reset` — Réinitialisation mot de passe

---

## 8. Git et déploiement

### 8.1 Workflow Git

**Branche principale** : `main`

**Workflow** :
1. Toujours travailler sur `main` ou branche feature explicite
2. `git fetch --all --prune` avant de commencer
3. `git rebase origin/main` si nécessaire
4. Tests + documentation
5. Préparer les changements (pas de commit direct)
6. Soumettre à l'architecte pour validation

**Politique de merge** :
- **Squash merge** pour toutes les Pull Requests
- Commits individuels regroupés en un seul commit sur `main`
- Voir `docs/git-workflow.md` pour procédure complète

### 8.2 Déploiement Cloud Run

**Production** :
- URL : https://emergence-app.ch
- Projet GCP : `emergence-469005`
- Région : `europe-west1`
- Service : `emergence-app`

**Procédure recommandée** :
- **Déploiement canary** (progressif) : voir [CANARY_DEPLOYMENT.md](CANARY_DEPLOYMENT.md)
- Script automatisé : `pwsh -File scripts/deploy-canary.ps1`
- Ancienne méthode (déconseillée) : déploiement direct

**IMPORTANT – Seed allowlist avant déploiement :**
- Générer le JSON depuis la base locale : `python scripts/generate_allowlist_seed.py --output allowlist_seed.json`
- Publier vers Secret Manager : `python scripts/generate_allowlist_seed.py --push AUTH_ALLOWLIST_SEED --create-secret`
- Sans ce secret (`AUTH_ALLOWLIST_SEED`), la base Cloud Run démarre sans comptes → 401 pour tout le monde.

**NE PAS déployer sans validation architecte** ❌

---

## 9. Ressources et support

### 9.1 Documentation clé

**Roadmap et planning** :
- [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) — Roadmap unique et officielle
- [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) — Suivi quotidien (61% complété)
- [CHANGELOG.md](CHANGELOG.md) — Historique des versions

**Guides techniques** :
- [docs/backend/](docs/backend/) — Documentation backend par feature
- [docs/frontend/](docs/frontend/) — Documentation frontend
- [docs/tests/PHASE1_VALIDATION_CHECKLIST.md](docs/tests/PHASE1_VALIDATION_CHECKLIST.md) — Checklist validation

**Conventions de développement** :
- [docs/AGENTS_COORDINATION.md](docs/AGENTS_COORDINATION.md) — Conventions obligatoires inter-agents
- [docs/INTER_AGENT_SYNC.md](docs/INTER_AGENT_SYNC.md) — Points de synchronisation

### 9.2 Sub-Agents Claude Code

**Agents de surveillance disponibles** (via slash commands) :

- **Anima** (`/check_docs`) : Vérifie cohérence code/documentation
- **Neo** (`/check_integrity`) : Détecte incohérences backend/frontend
- **Nexus** (`/guardian_report`) : Synthétise rapports Anima et Neo
- **ProdGuardian** (`/check_prod`) : Analyse logs Cloud Run

**Ces agents suggèrent automatiquement la mise à jour de AGENT_SYNC.md** quand ils détectent des changements structurels importants.

### 9.3 Accéder aux rapports Guardian

**⚠️ IMPORTANT : Les rapports sont DÉJÀ dans le dépôt local, pas dans le cloud !**

**Quand l'utilisateur demande "vérifie les rapports Guardian" :**

```python
# ❌ FAUX - Ne PAS faire ça
"Je n'ai pas accès à Cloud Run ni aux jobs planifiés..."

# ✅ CORRECT - Faire ça
import os
# Lire les fichiers JSON locaux directement !
```

**Fichiers rapports principaux (dans le dépôt) :**

| Fichier | Chemin complet | Contenu |
|---------|----------------|---------|
| **prod_report.json** | `c:\dev\emergenceV8\reports\prod_report.json` | Monitoring production (erreurs, warnings, latence) |
| **unified_report.json** | `c:\dev\emergenceV8\reports\unified_report.json` | Rapport unifié Nexus (Anima + Neo) |
| **integrity_report.json** | `c:\dev\emergenceV8\reports\integrity_report.json` | Intégrité backend/frontend (Neo) |
| **docs_report.json** | `c:\dev\emergenceV8\reports\docs_report.json` | Gaps documentation (Anima) |
| **global_report.json** | `c:\dev\emergenceV8\reports\global_report.json` | Rapport global tous agents |

**Comment accéder (exemples concrets) :**

```python
# Python
import json
with open('c:\\dev\\emergenceV8\\reports\\prod_report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)
    print(f"Status prod: {report['status']}")
    print(f"Erreurs: {report['summary']['errors']}")
```

```javascript
// JavaScript/Node.js
const fs = require('fs');
const report = JSON.parse(fs.readFileSync('c:/dev/emergenceV8/reports/prod_report.json', 'utf-8'));
console.log(`Status prod: ${report.status}`);
console.log(`Erreurs: ${report.summary.errors}`);
```

```powershell
# PowerShell
$report = Get-Content 'c:\dev\emergenceV8\reports\prod_report.json' -Raw | ConvertFrom-Json
Write-Host "Status prod: $($report.status)"
Write-Host "Erreurs: $($report.summary.errors)"
```

**Ces rapports sont générés automatiquement par :**
- ✅ Git Hooks (pre-commit, post-commit, pre-push)
- ✅ Task Scheduler (toutes les 6h pour prod_report.json)
- ✅ Scripts manuels (`.\run_audit.ps1`)

**Donc : PAS BESOIN de se connecter à Cloud Run ou aux jobs planifiés !**

Les rapports sont **toujours disponibles localement** dans `reports/` et `claude-plugins/integrity-docs-guardian/reports/`.

**Exemple complet d'analyse des rapports :**

```python
import json
from pathlib import Path

# Base path rapports
reports_dir = Path('c:/dev/emergenceV8/reports')

# Lire prod report
with open(reports_dir / 'prod_report.json', 'r', encoding='utf-8') as f:
    prod = json.load(f)
    print(f"🔴 Production: {prod['status']} - {prod['summary']['errors']} erreurs")

# Lire unified report
with open(reports_dir / 'unified_report.json', 'r', encoding='utf-8') as f:
    unified = json.load(f)
    status = unified['executive_summary']['status']
    issues = unified['executive_summary']['total_issues']
    print(f"📊 Global: {status} - {issues} issues totales")

# Lire integrity report
with open(reports_dir / 'integrity_report.json', 'r', encoding='utf-8') as f:
    integrity = json.load(f)
    print(f"🔍 Intégrité: {integrity['status']}")
    print(f"   Backend files changed: {integrity['statistics']['backend_files_changed']}")
    print(f"   Frontend files changed: {integrity['statistics']['frontend_files_changed']}")
```

**Résumé : TU AS DÉJÀ ACCÈS AUX RAPPORTS - JUSTE LES LIRE ! 🔥**

### 9.4 Support

**En cas de problème** :
1. Vérifier `docs/passation.md` (dernières entrées)
2. Consulter `AGENT_SYNC.md` (état global)
3. Lire documentation architecture (`docs/architecture/`)
4. Documenter le blocage dans `docs/passation.md`
5. Demander validation architecte

**Logs et monitoring** :
- Cloud Logging : https://console.cloud.google.com/logs
- Cloud Run Console : https://console.cloud.google.com/run
- Health check : https://emergence-app.ch/api/health

---

## 10. Checklist express

### Avant de commencer
- [ ] Lire `AGENT_SYNC.md`
- [ ] Lire `CODEV_PROTOCOL.md`
- [ ] Lire `docs/passation.md` (3 dernières entrées)
- [ ] `git status` propre
- [ ] Environnement prêt (Node.js 18+, Python 3.11)

### Pendant le développement
- [ ] Code complet (pas de fragments)
- [ ] Tests créés pour nouveau code
- [ ] Documentation synchronisée

### Avant de soumettre
- [ ] `npm run build` ✅
- [ ] `pytest` (si backend modifié) ✅
- [ ] `git diff` relu (pas de secrets)
- [ ] `docs/passation.md` mis à jour ✅
- [ ] `AGENT_SYNC.md` mis à jour ✅

---

## 11. Évolution du guide

Ce guide est **vivant** et peut être amendé par :
1. Proposition dans `docs/passation.md`
2. Discussion avec l'architecte
3. Mise à jour de ce fichier avec version incrémentée

---

**En cas de doute, toujours privilégier : tests > documentation > communication.**

**Bienvenue dans l'équipe Codex GPT ! 🚀**
