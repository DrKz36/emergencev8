# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Dernière mise à jour** : 2025-10-16 (Production deployment fixes + P1 Phase COMPLÉTÉE)

**🔄 SYNCHRONISATION AUTOMATIQUE ACTIVÉE** : Ce fichier est maintenant surveillé et mis à jour automatiquement par le système AutoSyncService

---

## 🔥 Lecture OBLIGATOIRE avant toute session de code

**Ordre de lecture pour tous les agents :**
1. Ce fichier (`AGENT_SYNC.md`) — état actuel du dépôt
2. [`AGENTS.md`](AGENTS.md) — consignes générales
3. [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md) — protocole multi-agents
4. [`docs/passation.md`](docs/passation.md) — 3 dernières entrées minimum
5. `git status` + `git log --oneline -10` — état Git

---

## 📍 État actuel du dépôt (2025-10-16)

### Branche active
- **Branche courante** : `main`
- **Derniers commits** (5 plus récents) :
  - `093dbdc` fix(production): Complete Cloud Run deployment configuration
  - `34cf697` fix(email): Configure SMTP environment variables in Cloud Run deployments
  - `5560ec4` feat(version): Centralize version management system
  - `29c20ea` fix(themes): Complete P1.2 - Light/Dark Theme System
  - `2cd8cc8` feat(memory): Integrate P1.1 - Proactive Hints UI in chat

### Working tree
- **Statut** : Modifications en cours (voir `git status`)
- **Fichiers modifiés** :
  - `reports/prod_report.json` (M) *(présent avant session — ne pas toucher)*
    - `src/backend/features/auth/service.py` (M)
    - `tests/backend/features/test_user_scope_persistence.py` (M)
    - `AGENT_SYNC.md` (M)
    - `docs/passation.md` (M)
    - `stable-service.yaml` (M)
    - `scripts/deploy-simple.ps1` (M)
- **Fichiers non suivis** :
  - Aucun

### Remotes configurés
- `origin` → HTTPS : `https://github.com/DrKz36/emergencev8.git`
- `codex` → SSH : `git@github.com:DrKz36/emergencev8.git`

---

## 🚀 Déploiement Cloud Run - État Actuel (2025-10-16)

### ✅ PRODUCTION STABLE ET OPÉRATIONNELLE

**Statut** : ✅ **Déploiement réussi - Tous les services fonctionnels**

#### Infrastructure
- **Projet GCP** : `emergence-469005`
- **Région** : `europe-west1`
- **Service** : `emergence-app` (conteneur unique, pas de canary)
- **Registry** : `europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app`

#### URLs de Production
| Service | URL | Statut |
|---------|-----|--------|
| **Application principale** | https://emergence-app.ch | ✅ Opérationnel |
| **URL directe Cloud Run** | https://emergence-app-486095406755.europe-west1.run.app | ✅ Opérationnel |
| **Health Check** | https://emergence-app.ch/api/health | ✅ 200 OK |

#### Révision Active (2025-10-16)
- **Révision** : `emergence-app-00364-xxx` (dernière déployée)
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app@sha256:340f3f39e6d99a37c5b15c2d4a4c8126f673c4acb0bafe83194b4ad2a439adf0`
- **Trafic** : 100% (stratégie unique, pas de split)
- **CPU** : 2 cores
- **Mémoire** : 4 Gi
- **Min instances** : 1
- **Max instances** : 10
- **Timeout** : 300s

#### Problèmes Résolus (Session 2025-10-16)

**1. ✅ Configuration Email SMTP**
- Variables SMTP ajoutées dans `stable-service.yaml`
- Secret SMTP_PASSWORD configuré via Google Secret Manager
- Test réussi : Email de réinitialisation envoyé avec succès

**2. ✅ Variables d'Environnement Manquantes**
- Toutes les API keys configurées (OPENAI, GEMINI, ANTHROPIC, ELEVENLABS)
- Configuration OAuth complète (CLIENT_ID, CLIENT_SECRET)
- Configuration des agents IA (ANIMA, NEO, NEXUS)

**3. ✅ Erreurs 500 sur les Fichiers Statiques**
- Liveness probe corrigé : `/health/liveness` → `/api/health`
- Tous les fichiers statiques retournent maintenant 200 OK

**4. ✅ Module Papaparse Manquant**
- Import map étendu dans `index.html` :
  - papaparse@5.4.1
  - jspdf@2.5.2
  - jspdf-autotable@3.8.3
- Module chat se charge maintenant sans erreurs

#### Configuration Complète

**Variables d'environnement configurées (93 variables)** :
- **Système** : GOOGLE_CLOUD_PROJECT, AUTH_DEV_MODE=0, SESSION_INACTIVITY_TIMEOUT_MINUTES=30
- **Email/SMTP** : EMAIL_ENABLED=1, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (secret)
- **API Keys** : OPENAI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, ELEVENLABS_API_KEY (tous via Secret Manager)
- **OAuth** : GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET (secrets)
- **AI Agents** : ANIMA (openai/gpt-4o-mini), NEO (google/gemini-1.5-flash), NEXUS (anthropic/claude-3-haiku)
- **Telemetry** : ANONYMIZED_TELEMETRY=False, CHROMA_DISABLE_TELEMETRY=1
- **Cache** : RAG_CACHE_ENABLED=true, RAG_CACHE_TTL_SECONDS=300

**Secrets configurés dans Secret Manager** :
- ✅ SMTP_PASSWORD (version 3)
- ✅ OPENAI_API_KEY
- ✅ GEMINI_API_KEY
- ✅ ANTHROPIC_API_KEY
- ✅ GOOGLE_OAUTH_CLIENT_ID
- ✅ GOOGLE_OAUTH_CLIENT_SECRET

#### Procédure de Déploiement

**🆕 PROCÉDURE RECOMMANDÉE : Déploiement Canary (2025-10-16)**

Pour éviter les rollbacks hasardeux, utiliser le **déploiement progressif canary** :

```bash
# Script automatisé (recommandé)
pwsh -File scripts/deploy-canary.ps1

# Ou manuel avec phases progressives (voir CANARY_DEPLOYMENT.md)
```

**Étapes du déploiement canary** :
1. Build + Push image Docker (avec tag timestamp)
2. Déploiement avec `--no-traffic` (0% initial)
3. Tests de validation sur URL canary
4. Routage progressif : 10% → 25% → 50% → 100%
5. Surveillance continue à chaque phase

**Documentation complète** : [CANARY_DEPLOYMENT.md](CANARY_DEPLOYMENT.md)

**Ancienne méthode (déconseillée)** :
```bash
# Build et push
docker build -t europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest .
docker push europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest

# Déploiement direct (risqué - préférer canary)
gcloud run services replace stable-service.yaml \
  --region=europe-west1 \
  --project=emergence-469005
```

**Vérification** :
```bash
# 1. Health check
curl https://emergence-app.ch/api/health

# 2. Fichiers statiques
curl -I https://emergence-app.ch/src/frontend/main.js

# 3. Logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app" \
  --project=emergence-469005 --limit=10 --freshness=5m
```

#### Monitoring et Logs

**Commandes utiles** :
```bash
# Logs en temps réel
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app" \
  --project=emergence-469005

# Métriques du service
gcloud run services describe emergence-app \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.conditions)"

# État des révisions
gcloud run revisions list \
  --service=emergence-app \
  --region=europe-west1 \
  --project=emergence-469005
```

#### Documentation
- 🆕 [CANARY_DEPLOYMENT.md](CANARY_DEPLOYMENT.md) - **Procédure officielle de déploiement canary** (2025-10-16)
- 🔧 [scripts/deploy-canary.ps1](scripts/deploy-canary.ps1) - Script automatisé de déploiement canary
- ✅ [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - Rapport complet de déploiement
- ✅ [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md) - Guide de résolution
- ✅ [stable-service.yaml](stable-service.yaml) - Configuration Cloud Run

---

## 📊 Roadmap & Progression (2025-10-16)

### ✅ PHASE P0 - QUICK WINS - **COMPLÉTÉE** (3/3)
- ✅ P0.1 - Archivage des Conversations (UI) - Complété 2025-10-15
- ✅ P0.2 - Graphe de Connaissances Interactif - Complété 2025-10-15
- ✅ P0.3 - Export Conversations (CSV/PDF) - Complété 2025-10-15

### ✅ PHASE P1 - UX ESSENTIELLE - **COMPLÉTÉE** (3/3)
- ✅ P1.1 - Hints Proactifs (UI) - Complété 2025-10-16
- ✅ P1.2 - Thème Clair/Sombre - Complété 2025-10-16
- ✅ P1.3 - Gestion Avancée des Concepts - Complété 2025-10-16

### 📊 Métriques Globales
```
Progression Totale : [████████░░] 14/23 (61%)

✅ Complètes    : 14/23 (61%)
🟡 En cours     : 0/23 (0%)
⏳ À faire      : 9/23 (39%)
```

### 🎯 PROCHAINE PHASE : P2 - ADMINISTRATION & SÉCURITÉ
**Statut** : ⏳ À démarrer
**Estimation** : 4-6 jours
**Fonctionnalités** :
- P2.1 - Dashboard Administrateur Avancé
- P2.2 - Gestion Multi-Sessions
- P2.3 - Authentification 2FA (TOTP)

### Documentation Roadmap
- 📋 [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) - Document unique et officiel
- 📊 [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) - Suivi quotidien de progression
- 📜 [CHANGELOG.md](CHANGELOG.md) - Historique des versions

---

## 🔧 Système de Versioning

**Version actuelle** : `beta-1.3.0` (Phase P1 complète)

**Format** : `beta-X.Y.Z`
- **X (Major)** : Phases complètes (P0→1, P1→2, P2→3, P3→4)
- **Y (Minor)** : Nouvelles fonctionnalités individuelles
- **Z (Patch)** : Corrections de bugs / Améliorations mineures

**Roadmap des Versions** :
- ✅ `beta-1.0.0` : État initial du projet (2025-10-15)
- ✅ `beta-1.1.0` : P0.1 - Archivage conversations (2025-10-15)
- ✅ `beta-1.2.0` : P0.2 - Graphe de connaissances (2025-10-15)
- ✅ `beta-1.3.0` : P0.3 - Export CSV/PDF (2025-10-15)
- ✅ `beta-2.0.0` : Phase P1 complète (2025-10-16)
- 🔜 `beta-3.0.0` : Phase P2 complète (TBD)
- ⏳ `beta-4.0.0` : Phase P3 complète (TBD)
- 🎯 `v1.0.0` : Release Production Officielle (TBD)

---

## 🚧 Zones de Travail en Cours

## 🧑‍💻 Codex - Journal 2025-10-16

- **Horodatage** : 20:45 CET
- **Objectif** : Audit UI mobile portrait + verrouillage paysage (authentification).
- **Fichiers impactés** : `index.html`, `src/frontend/styles/core/_layout.css`, `src/frontend/styles/core/_responsive.css`, `src/frontend/features/home/home.css`.
- **Tests** : `npm run build`
- **Notes** : Overlay d'orientation ajouté + variables responsive centralisées (`--responsive-*`) à généraliser sur les prochains modules.


### ✅ Session 2025-10-16 - Production Deployment (TERMINÉE)
- **Statut** : ✅ **PRODUCTION STABLE**
- **Priorité** : 🔴 **CRITIQUE** → ✅ **RÉSOLU**
- **Travaux effectués** :
  - Configuration complète SMTP pour emails
  - Ajout de toutes les API keys et secrets
  - Correction du liveness probe
  - Ajout de l'import map pour modules ESM
  - Déploiement révision `emergence-app-00364`
- **Résultat** : Application 100% fonctionnelle en production
- **Documentation** : [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md)

### ✅ Session 2025-10-15 - Phase P1 (TERMINÉE)
- **Statut** : ✅ **PHASE P1 COMPLÉTÉE** (3/3 fonctionnalités)
- **Fonctionnalités livrées** :
  - P1.1 - Hints Proactifs UI (~3 heures)
  - P1.2 - Thème Clair/Sombre (~2 heures)
  - P1.3 - Gestion Avancée Concepts (~4 heures)
- **Progression totale** : 61% (14/23 fonctionnalités)
- **Documentation** : [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md)

### ✅ Session 2025-10-15 - Phase P0 (TERMINÉE)
- **Statut** : ✅ **PHASE P0 COMPLÉTÉE** (3/3 fonctionnalités)
- **Fonctionnalités livrées** :
  - P0.1 - Archivage Conversations (~4 heures)
  - P0.2 - Graphe de Connaissances (~3 heures)
  - P0.3 - Export CSV/PDF (~4 heures)
- **Temps total** : ~11 heures (estimation : 3-5 jours)
- **Efficacité** : 3-4x plus rapide que prévu

---

## 📚 Documentation Essentielle

### Documents de Référence
- 📋 [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) - Roadmap unique et officielle (13 features)
- 📊 [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) - Suivi quotidien (61% complété)
- 🚀 [NEXT_SESSION_P2_4_TO_P2_9.md](NEXT_SESSION_P2_4_TO_P2_9.md) - Planification phases P2.4 à P2.9 (microservices migration)
- 📜 [CHANGELOG.md](CHANGELOG.md) - Historique détaillé des versions
- 📖 [README.md](README.md) - Documentation principale du projet

### Documentation Technique
- 🏗️ [docs/architecture/](docs/architecture/) - Architecture système
- 🔧 [docs/backend/](docs/backend/) - Documentation backend
- 🎨 [docs/frontend/](docs/frontend/) - Documentation frontend
- 📦 [docs/deployments/](docs/deployments/) - Guides de déploiement

### Guides Opérationnels
- 🚀 [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - État déploiement production
- 🔧 [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md) - Guide résolution problèmes
- 📝 [docs/passation.md](docs/passation.md) - Journal de passation (3 dernières entrées minimum)
- 🤖 [AGENTS.md](AGENTS.md) - Consignes pour agents IA
- 🔄 [CODEV_PROTOCOL.md](CODEV_PROTOCOL.md) - Protocole multi-agents

### Documentation Utilisateur
- 📚 [docs/TUTORIAL_SYSTEM.md](docs/TUTORIAL_SYSTEM.md) - Système de tutoriel
- 🎯 [GUIDE_INTERFACE_BETA.md](GUIDE_INTERFACE_BETA.md) - Guide interface bêta
- ❓ [docs/FAQ.md](docs/FAQ.md) - Questions fréquentes

### 🤖 Sub-Agents Claude Code - Système de Surveillance et Coordination

**IMPORTANT** : Les sub-agents Claude Code sont configurés pour **automatiquement suggérer la mise à jour de ce fichier (AGENT_SYNC.md)** quand ils détectent des changements structurels importants.

#### Sub-Agents Disponibles (Slash Commands)

**Anima - Gardien de Documentation** (`/check_docs`)
- **Rôle** : Vérifie la cohérence entre code et documentation
- **Responsabilité** : Suggère mise à jour AGENT_SYNC.md si nouvelle doc d'architecture, processus, ou guides ajoutés
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/scan_docs.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/docs_report.json`

**Neo - Gardien d'Intégrité** (`/check_integrity`)
- **Rôle** : Détecte incohérences backend/frontend et régressions
- **Responsabilité** : Suggère mise à jour AGENT_SYNC.md si breaking changes, nouveaux endpoints, ou changements d'architecture critiques
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/check_integrity.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/integrity_report.json`

**Nexus - Coordinateur** (`/guardian_report`)
- **Rôle** : Synthétise les rapports d'Anima et Neo
- **Responsabilité** : Propose mise à jour consolidée de AGENT_SYNC.md basée sur les changements systémiques détectés
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/generate_report.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/unified_report.json`

**ProdGuardian - Surveillance Production** (`/check_prod`)
- **Rôle** : Analyse logs Cloud Run et détecte anomalies en production
- **Responsabilité** : Suggère mise à jour AGENT_SYNC.md si problèmes récurrents ou changements de config nécessaires
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/prod_report.json`

#### Mécanisme de Synchronisation Automatique

Les sub-agents suivent ces règles :
1. ✅ **Détection** : Analyse des changements via leurs scripts respectifs
2. ✅ **Évaluation** : Détermination si changements impactent coordination multi-agents
3. ✅ **Suggestion** : Proposition de mise à jour de AGENT_SYNC.md avec contenu pré-rédigé
4. ⏸️ **Validation humaine** : Demande confirmation avant toute modification

**Formats de suggestion** : Chaque sub-agent utilise un format spécifique (📝, 🔧, 🎯, 🚨) pour identifier la source et le type de changement.

**Avantage pour Codex GPT** : Quand vous donnez une tâche à Codex GPT, il aura accès à une documentation AGENT_SYNC.md maintenue à jour par les sub-agents Claude Code, évitant malentendus et erreurs.

---

## ⚙️ Configuration Développement

### Environnement Local

**Prérequis** :
- Python 3.11+
- Node.js 18+
- Docker (pour tests et déploiement)

**Installation** :
```bash
# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
npm install

# Variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API
```

**Lancement** :
```bash
# Backend (dev)
uvicorn src.backend.main:app --reload --port 8000

# Frontend (dev)
npm run dev

# Build frontend
npm run build
```

**Tests** :
```bash
# Tests backend
pytest tests/backend/

# Tests frontend
npm run test

# Linting
ruff check src/backend/
mypy src/backend/
```

### Variables d'Environnement Essentielles

**Minimum requis pour développement local** :
```bash
# API Keys (au moins une)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...

# OAuth (optionnel en dev)
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...

# Email (optionnel)
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
```

---

## ✅ Synchronisation Cloud ↔ Local ↔ GitHub

### Statut
- ✅ **Machine locale** : Remotes `origin` et `codex` configurés et opérationnels
- ⚠️ **Environnement cloud GPT Codex** : Aucun remote (attendu et normal)
- ✅ **Solution** : Workflow de synchronisation via patches Git documenté

### Documentation
- 📚 [docs/CLOUD_LOCAL_SYNC_WORKFLOW.md](docs/CLOUD_LOCAL_SYNC_WORKFLOW.md) - Guide complet (3 méthodes)
- 📚 [docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md](docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md) - Instructions agent cloud
- 📚 [prompts/local_agent_github_sync.md](prompts/local_agent_github_sync.md) - Résumé workflow

### Workflow Recommandé
1. **Agent cloud** : Génère patch avec modifications
2. **Agent local** : Applique patch et push vers GitHub
3. **Validation** : Tests + review avant merge

---

## 🔒 Sécurité & Bonnes Pratiques

### Secrets
- ❌ **JAMAIS** commiter de secrets dans Git
- ✅ Utiliser `.env` local (ignoré par Git)
- ✅ Utiliser Google Secret Manager en production
- ✅ Référencer les secrets via `secretKeyRef` dans YAML

### Déploiement
- ✅ Toujours tester localement avant déploiement
- ✅ Utiliser des digests SHA256 pour les images Docker
- ✅ Vérifier les health checks après déploiement
- ✅ Monitorer les logs pendant 1h post-déploiement

### Code Quality
- ✅ Linter : `ruff check src/backend/`
- ✅ Type checking : `mypy src/backend/`
- ✅ Tests : `pytest tests/backend/`
- ✅ Coverage : Maintenir >80%

---

## 🎯 Prochaines Actions

### Immédiat (Cette semaine)
1. ✅ Phase P1 complète - **FAIT**
2. ✅ Production stable - **FAIT**
3. 🔜 Démarrer Phase P2 (Dashboard Admin Avancé)
4. 🔜 Tests d'intégration P1 en production

### Court Terme (1-2 semaines)
1. Phase P2 complète (Administration & Sécurité)
2. Tests E2E complets
3. Documentation utilisateur mise à jour
4. Monitoring et métriques Phase P2

### Moyen Terme (3-4 semaines)
1. Phase P3 (Fonctionnalités Avancées)
2. PWA (Mode hors ligne)
3. API Publique Développeurs
4. Webhooks et Intégrations

---

## 📞 Support & Contact

**Documentation Technique** :
- Guide de déploiement : [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md)
- Configuration YAML : [stable-service.yaml](stable-service.yaml)
- Roadmap officielle : [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md)

**Logs et Monitoring** :
- Cloud Logging : https://console.cloud.google.com/logs
- Cloud Run Console : https://console.cloud.google.com/run
- Projet GCP : emergence-469005

**En cas de problème** :
1. Vérifier les logs Cloud Run
2. Consulter [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md)
3. Vérifier l'état des secrets dans Secret Manager
4. Rollback si nécessaire (voir procédure dans documentation)

---

## 📋 Checklist Avant Nouvelle Session

**À vérifier TOUJOURS avant de commencer** :

- [ ] Lire ce fichier (`AGENT_SYNC.md`)
- [ ] Lire [`AGENTS.md`](AGENTS.md)
- [ ] Lire [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md)
- [ ] Lire les 3 dernières entrées de [`docs/passation.md`](docs/passation.md)
- [ ] Exécuter `git status`
- [ ] Exécuter `git log --oneline -10`
- [ ] Vérifier la [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md)
- [ ] Consulter [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) pour état production

**Avant de coder** :
- [ ] Créer une branche feature si nécessaire
- [ ] Mettre à jour les dépendances si ancien checkout
- [ ] Lancer les tests pour vérifier l'état de base
- [ ] Vérifier que le build frontend fonctionne

**Avant de commiter** :
- [ ] Lancer les tests : `pytest tests/backend/`
- [ ] Lancer le linter : `ruff check src/backend/`
- [ ] Vérifier le type checking : `mypy src/backend/`
- [ ] Build frontend : `npm run build`
- [ ] Mettre à jour [AGENT_SYNC.md](AGENT_SYNC.md)
- [ ] Mettre à jour [docs/passation.md](docs/passation.md)

---

**Dernière mise à jour** : 2025-10-16 par Claude Code Assistant
**Version** : beta-2.0.0
**Statut Production** : ✅ STABLE ET OPÉRATIONNEL
**Progression Roadmap** : 61% (14/23 fonctionnalités)
