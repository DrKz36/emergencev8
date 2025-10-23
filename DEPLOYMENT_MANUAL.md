# 🚀 Déploiement Manuel - ÉMERGENCE V8

**Date de création** : 2025-10-23
**Statut** : ✅ Procédure officielle (déploiement automatique désactivé)
**Raison** : Contrôle total des déploiements, éviter 15 révisions par jour pour des virgules

---

## 🎯 Philosophie

**Déploiement manuel UNIQUEMENT** pour éviter les déploiements automatiques intempestifs.

### Pourquoi manuel ?

- ❌ **Avant** : Chaque push sur `main` → deploy automatique → 15+ révisions/jour
- ✅ **Maintenant** : Deploy uniquement quand TU décides → contrôle total
- 🎯 **Avantages** :
  - Grouper plusieurs commits avant de déployer
  - Tester localement avant de pousser en prod
  - Éviter les révisions Cloud Run inutiles
  - Économiser les coûts GCP (moins de builds)

---

## 📋 Quand déployer ?

**Deploy quand c'est pertinent :**
- ✅ Feature complète et testée
- ✅ Bug critique fixé
- ✅ Changements backend/frontend stables
- ✅ Après validation locale complète

**Ne PAS deploy pour :**
- ❌ Typo dans un commentaire
- ❌ Changements de docs uniquement
- ❌ WIP (work in progress)
- ❌ Commits de développement intermédiaires

---

## 🚀 Méthodes de Déploiement

### Méthode 1 : Script PowerShell (Recommandé)

**Le plus simple et rapide :**

```powershell
# Déploiement basique
pwsh -File scripts/deploy-manual.ps1

# Avec raison (traçabilité)
pwsh -File scripts/deploy-manual.ps1 -Reason "Fix bug auth critique"
```

**Ce que fait le script :**
1. Vérifie que `gh` CLI est installé et authentifié
2. S'assure que la branche `main` est à jour
3. Affiche le dernier commit qui sera déployé
4. Demande confirmation
5. Déclenche le workflow GitHub Actions
6. Propose de suivre le déploiement en temps réel

---

### Méthode 2 : GitHub CLI

**Si tu préfères la ligne de commande directe :**

```bash
# Déploiement simple
gh workflow run deploy.yml

# Avec raison
gh workflow run deploy.yml -f reason="Fix auth bug"

# Suivre le déploiement
gh run watch
```

---

### Méthode 3 : GitHub UI

**Via l'interface web :**

1. Aller sur https://github.com/ton-repo/actions
2. Sélectionner "Deploy to Cloud Run" dans la liste des workflows
3. Cliquer sur "Run workflow"
4. Choisir la branche `main`
5. (Optionnel) Ajouter une raison
6. Cliquer sur "Run workflow"

---

## 🛠️ Prérequis

### Installation GitHub CLI (si pas déjà fait)

**Windows :**
```powershell
winget install GitHub.cli
```

**macOS :**
```bash
brew install gh
```

**Linux :**
```bash
# Voir https://github.com/cli/cli/blob/trunk/docs/install_linux.md
```

### Authentification GitHub CLI

**Première fois uniquement :**
```bash
gh auth login
# Suivre les instructions interactives
```

**Vérifier l'authentification :**
```bash
gh auth status
```

---

## 📊 Workflow de Déploiement

### Étapes automatiques (GitHub Actions)

Une fois le workflow déclenché, GitHub Actions fait automatiquement :

1. **Build Docker** :
   - Compile le backend Python
   - Build le frontend (Vite)
   - Crée l'image Docker

2. **Push vers GCR** :
   - Envoi vers Google Container Registry
   - Tag avec SHA du commit + `latest`

3. **Deploy sur Cloud Run** :
   - Utilise `stable-service.yaml`
   - Préserve la config IAM et auth
   - Met à jour la révision

4. **Health Check** :
   - Vérifie que `/health` répond 200 OK
   - Attend 10s avant de tester

**Durée totale** : ~5-7 minutes

---

## 🔍 Suivre le Déploiement

### Via GitHub CLI (recommandé)

```bash
# Suivre le dernier workflow
gh run watch

# Lister les derniers runs
gh run list --workflow=deploy.yml
```

### Via GitHub UI

**URL directe** : https://github.com/ton-repo/actions

**Voir les logs en temps réel** :
1. Cliquer sur le workflow en cours
2. Cliquer sur le job "Build & Deploy to Cloud Run"
3. Voir les logs de chaque étape

---

## ✅ Vérification Post-Déploiement

### 1. Health Check

```bash
curl https://emergence-app-469005.europe-west1.run.app/health
# Réponse attendue: {"status":"ok","timestamp":"..."}
```

### 2. Vérifier la révision déployée

```bash
gcloud run revisions list \
  --service=emergence-app \
  --region=europe-west1 \
  --limit=3
```

### 3. Tester l'app complète

**Ouvrir dans le navigateur** :
- https://emergence-app-469005.europe-west1.run.app
- Tester login/chat/features principales

---

## 🚨 En Cas de Problème

### Rollback rapide

**Si la nouvelle révision plante :**

```bash
# Lister les révisions
gcloud run revisions list \
  --service=emergence-app \
  --region=europe-west1

# Rollback vers la révision précédente
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-XXXXX=100 \
  --region=europe-west1
```

### Logs en temps réel

```bash
# Logs Cloud Run
gcloud run services logs read emergence-app \
  --region=europe-west1 \
  --limit=50 \
  --format=json

# Ou via Logs Explorer
# https://console.cloud.google.com/logs/query
```

---

## 📚 Configuration Actuelle

### Workflow GitHub Actions

**Fichier** : [.github/workflows/deploy.yml](.github/workflows/deploy.yml)

**Trigger** : `workflow_dispatch` (manuel uniquement)

**Variables d'environnement** :
- `GCP_PROJECT_ID`: emergence-469005
- `GCP_REGION`: europe-west1
- `SERVICE_NAME`: emergence-app
- `IMAGE_NAME`: gcr.io/emergence-469005/emergence-app

### Script de Déploiement

**Fichier** : [scripts/deploy-manual.ps1](scripts/deploy-manual.ps1)

**Fonctionnalités** :
- Vérifie prérequis (gh CLI, auth)
- S'assure que `main` est à jour
- Affiche le commit à déployer
- Demande confirmation
- Déclenche le workflow
- Permet de suivre le déploiement

---

## 🎓 Bonnes Pratiques

### Avant de déployer

```bash
# 1. Tests backend
pytest tests/backend/ && ruff check src/backend/ && mypy src/backend/

# 2. Build frontend
npm run build

# 3. Git propre
git status
git push origin main

# 4. Déployer
pwsh -File scripts/deploy-manual.ps1
```

### Après déploiement

1. ✅ Vérifier health check
2. ✅ Tester les fonctionnalités critiques
3. ✅ Vérifier les logs (pas d'erreurs)
4. ✅ Documenter dans `AGENT_SYNC.md` si changement majeur

---

## 📝 Exemples de Raisons de Déploiement

**Exemples clairs et traçables :**

```bash
# Feature
pwsh -File scripts/deploy-manual.ps1 -Reason "feat: Ajout détection topic shift"

# Bug fix
pwsh -File scripts/deploy-manual.ps1 -Reason "fix: Bug auth allowlist"

# Performance
pwsh -File scripts/deploy-manual.ps1 -Reason "perf: Optimisation RAG chunking"

# Security
pwsh -File scripts/deploy-manual.ps1 -Reason "security: Fix CORS origin validation"
```

---

## 🔗 Ressources

**URLs Production** :
- App principale : https://emergence-app-469005.europe-west1.run.app
- Health : https://emergence-app-469005.europe-west1.run.app/health
- Console GCP : https://console.cloud.google.com/run?project=emergence-469005

**Documentation** :
- [CANARY_DEPLOYMENT.md](CANARY_DEPLOYMENT.md) - Déploiement canary (avancé)
- [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - État production actuel
- [docs/DEPLOYMENT_AUTH_PROTECTION.md](docs/DEPLOYMENT_AUTH_PROTECTION.md) - Auth & sécurité

**Scripts** :
- [scripts/deploy-manual.ps1](scripts/deploy-manual.ps1) - Déploiement manuel
- [scripts/run-backend.ps1](scripts/run-backend.ps1) - Backend local
- [scripts/deploy-canary.ps1](scripts/deploy-canary.ps1) - Déploiement canary

---

## ✅ Checklist Rapide

Avant chaque déploiement :

- [ ] Tests passent localement ✅
- [ ] Build frontend OK ✅
- [ ] Branch `main` à jour ✅
- [ ] Commit poussé sur GitHub ✅
- [ ] Raison de déploiement claire (optionnel mais recommandé) ✅
- [ ] Confirmation avant de déclencher ✅

Après déploiement :

- [ ] Health check OK ✅
- [ ] App fonctionne correctement ✅
- [ ] Pas d'erreurs dans les logs ✅
- [ ] Documentation mise à jour si besoin ✅

---

**🚀 Contrôle total. Deploy quand TU veux. Plus de spam de révisions.**
