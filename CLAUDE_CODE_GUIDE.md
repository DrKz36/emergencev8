# Guide Claude Code — Emergence V8

**Version** : 1.0
**Date** : 2025-10-16
**Agent** : Claude Code (Anthropic)
**Architecte** : FG (validation finale avant commit/push/deploy)

---

## 0. Bienvenue Claude Code

Ce document est votre **guide de référence** pour collaborer efficacement sur le projet Emergence V8 en tant que co-développeur IA principal.

Vous travaillez en **égalité technique** avec Codex GPT et d'autres agents IA. Chacun peut modifier n'importe quel fichier du dépôt, sous validation finale de l'architecte humain (FG).

---

## 1. Lecture obligatoire avant toute session

**Ordre de lecture (RESPECTER CET ORDRE)** :

1. **[AGENT_SYNC.md](AGENT_SYNC.md)** — État actuel du dépôt, progression, déploiement
2. **Ce fichier (CLAUDE_CODE_GUIDE.md)** — Consignes spécifiques Claude Code
3. **[CODEV_PROTOCOL.md](CODEV_PROTOCOL.md)** — Protocole de co-développement multi-agents
4. **[docs/passation.md](docs/passation.md)** — Dernières 3 entrées minimum (contexte, blocages, next actions)
5. **`git status` + `git log --oneline -10`** — État Git actuel

**Temps de lecture estimé** : 10-15 minutes (investissement OBLIGATOIRE pour éviter erreurs et conflits)

---

## 2. Principes fondamentaux

### 2.1 Égalité technique
- ✅ Vous êtes un **co-développeur** de niveau ingénieur équivalent à Codex GPT
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

**Claude Code privilégie (mais n'est pas limité à)** :

### Backend Python
- Services : `src/backend/features/*` (chat, memory, auth, admin, etc.)
- Core : `src/backend/core/*` (database, DI, services centraux)
- Shared : `src/backend/shared/*` (utilitaires partagés)
- Tests : `tests/backend/*`

### Architecture et Refactoring
- Documentation architecture : `docs/architecture/*` (modèles C4)
- Amélioration structure et dette technique
- Optimisation performance et scalabilité
- Patterns et bonnes pratiques

### Documentation Technique
- Architecture système : `docs/architecture/*`
- Documentation backend : `docs/backend/*`
- Guides techniques : `docs/Memoire.md`, conventions
- Diagrammes et modèles C4

### Tests et Qualité
- Tests backend : `pytest`
- Type checking : `mypy`
- Linting : `ruff`
- Smoke tests : PowerShell (`tests/run_all.ps1`)

**Important** : Ces zones sont **indicatives**. Vous pouvez intervenir partout si nécessaire, y compris sur le frontend ou les scripts.

---

## 4. Workflow de session

### 4.1 Démarrage de session

**Checklist obligatoire** :

- [ ] Lire `AGENT_SYNC.md` (état actuel du dépôt)
- [ ] Lire ce fichier (`CLAUDE_CODE_GUIDE.md`)
- [ ] Lire `CODEV_PROTOCOL.md` (protocole inter-agents)
- [ ] Lire les 3 dernières entrées de `docs/passation.md`
- [ ] Exécuter `git status` et `git log --oneline -10`
- [ ] Vérifier que l'environnement est propre (pas de fichiers non suivis suspects)

**Environnement** :
- Python 3.11 dans un virtualenv
- Node.js 18+ (via nvm recommandé)
- Docker (pour tests et déploiement)

**Configuration des permissions** :
- Le fichier `.claude/settings.local.json` contient la configuration des permissions d'exécution automatique
- `"allow": ["*"]` active l'exécution automatique de toutes les opérations sans demande d'autorisation
- Cette configuration permet un workflow fluide et continu sans interruption
- Les commandes spécifiques listées après le wildcard sont maintenues pour référence

### 4.2 Pendant le développement

**Règles d'or** :

1. **Avancer sans interruption** : bouclage de l'ensemble des tâches identifiées avant de solliciter l'utilisateur, sauf dépendance bloquante
2. **Respecter la structure** : `src/backend`, `src/frontend`, `docs`, etc.
3. **Code complet obligatoire** : pas d'ellipses, pas de fragments (voir ARBO-LOCK)
4. **Tests systématiques** : créer les tests pour tout nouveau fichier
5. **Documentation synchronisée** : mettre à jour `docs/` si changement d'architecture ou de responsabilités

**Anti-patterns à éviter** :

- ❌ Livrer des fragments de code
- ❌ Modifier sans tester
- ❌ Ignorer l'architecture existante
- ❌ Oublier de documenter dans `docs/passation.md`

### 4.3 Clôture de session

**Checklist obligatoire** :

- [ ] **Tests backend** (si modifié) : `pytest` ✅
- [ ] **Tests frontend** (si modifié) : `npm run build` ✅
- [ ] **Smoke tests** (si modifié) : `pwsh -File tests/run_all.ps1` ✅
- [ ] **Linters** : `ruff check`, `mypy` (backend) ✅
- [ ] **Documentation** : mise à jour `docs/passation.md` (nouvelle entrée complète en haut) ✅
- [ ] **AGENT_SYNC.md** : mise à jour section "Claude Code" avec timestamp et fichiers touchés ✅
- [ ] **Git propre** : `git status` sans fichiers non suivis suspects ✅
- [ ] **Passation** : entrée complète dans `docs/passation.md` avec format standard ✅

**Format de passation** (template) :

```markdown
## [YYYY-MM-DD HH:MM] — Agent: Claude Code (Sonnet 4.5)

### Fichiers modifiés
- `src/backend/features/chat/service.py` (ajout méthode export)
- `src/backend/features/chat/router.py` (nouvel endpoint /export)
- `docs/passation.md` (cette entrée)

### Contexte
Implémentation feature export conversations en CSV/PDF selon roadmap P0.3.
Ajout endpoint `POST /api/chat/export` avec support formats multiples.
Service intègre génération CSV via csv.writer et PDF via reportlab.

### Tests
- ✅ `pytest tests/backend/features/test_export.py` (nouveau)
- ✅ Tests manuels : export CSV fonctionne
- ✅ Tests manuels : export PDF fonctionne
- ✅ `ruff check` + `mypy` sans erreur

### Prochaines actions recommandées
1. Ajouter tests d'intégration pour endpoint /export
2. Intégrer frontend avec bouton export (délégué à Codex GPT)
3. Documenter feature dans guide utilisateur

### Blocages
Aucun.
```

---

## 5. Tests et qualité

### 5.1 Tests backend

**Obligatoire avant toute soumission** :

```bash
# Tests backend complets
pytest

# Tests backend ciblés
pytest tests/backend/features/test_chat.py

# Linting backend
ruff check src/backend/
mypy src/backend/
```

### 5.2 Tests frontend (si modifié)

```bash
# Build frontend (OBLIGATOIRE)
npm run build

# Tests unitaires (si configurés)
npm run test

# Linting (si configuré)
npm run lint
```

### 5.3 Smoke tests

```bash
# Tests rapides endpoints critiques
pwsh -File tests/run_all.ps1
```

### 5.4 Critères de qualité

- ✅ **Aucune erreur** dans `pytest`
- ✅ **Coverage >80%** pour nouveau code (si tests unitaires configurés)
- ✅ **Pas de secrets** dans le code (vérifier `git diff`)
- ✅ **Documentation à jour** (`docs/passation.md`, architecture si impacté)

---

## 6. Conventions de code

### 6.1 Backend Python

**Style** :
- PEP 8 (enforced by ruff)
- Type hints systématiques (checked by mypy)
- snake_case pour variables/fonctions
- PascalCase pour classes
- UPPER_SNAKE_CASE pour constantes

**Exemple** :
```python
# ✅ Bon
class ChatService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._cache: dict[str, Any] = {}

    async def send_message(self, text: str, user_id: int) -> Message:
        """Send a message and return the created message."""
        result = await self.db.execute(
            "INSERT INTO messages (text, user_id) VALUES (?, ?)",
            (text, user_id)
        )
        return Message(id=result.lastrowid, text=text, user_id=user_id)

# ❌ Mauvais
class chatService:  # Mauvaise casse
    def sendMessage(self, text, userId):  # Pas de type hints, camelCase
        result = self.db.execute("INSERT INTO messages (text, user_id) VALUES (?, ?)", (text, userId))
        return result  # Type de retour non clair
```

**Structure** :
- Un module par feature (pas de mega-fichiers)
- Séparation router / service / models
- Dependency injection via dependency.py
- Logs structurés avec prefixes

### 6.2 Frontend JavaScript (si modifié)

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
├── CLAUDE_CODE_GUIDE.md  # Ce fichier
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

**NE PAS déployer sans validation architecte** ❌

---

## 9. Sub-Agents et outils de surveillance

### 9.1 Sub-Agents disponibles (Slash Commands)

**Anima** (`/check_docs`) : Vérifie cohérence code/documentation
**Neo** (`/check_integrity`) : Détecte incohérences backend/frontend
**Nexus** (`/guardian_report`) : Synthétise rapports Anima et Neo
**ProdGuardian** (`/check_prod`) : Analyse logs Cloud Run

**Ces agents suggèrent automatiquement la mise à jour de AGENT_SYNC.md** quand ils détectent des changements structurels importants.

### 9.2 Utilisation des sub-agents

**Quand utiliser** :
- Après modifications structurelles importantes
- Avant soumission pour validation
- Pour vérifier cohérence globale du projet
- Pour détecter régressions potentielles

**Comment utiliser** :
```bash
# Via slash commands
/check_docs        # Anima vérifie documentation
/check_integrity   # Neo vérifie intégrité code
/guardian_report   # Nexus synthétise tout
/check_prod        # ProdGuardian analyse production
```

---

## 10. Ressources et support

### 10.1 Documentation clé

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

### 10.2 Support

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

## 11. Checklist express

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
- [ ] `pytest` ✅
- [ ] `npm run build` (si frontend modifié) ✅
- [ ] `git diff` relu (pas de secrets)
- [ ] `docs/passation.md` mis à jour ✅
- [ ] `AGENT_SYNC.md` mis à jour ✅

---

## 12. Évolution du guide

Ce guide est **vivant** et peut être amendé par :
1. Proposition dans `docs/passation.md`
2. Discussion avec l'architecte
3. Mise à jour de ce fichier avec version incrémentée

---

**En cas de doute, toujours privilégier : tests > documentation > communication.**

**Bienvenue dans l'équipe Claude Code ! 🚀**
