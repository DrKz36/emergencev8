# 🚀 ÉMERGENCE - Guide de Déploiement Rapide

## ⚡ Déploiement Immédiat (Recommandé)

Pour déployer rapidement l'application en production :

```powershell
# Déploiement complet (build + tests + deploy)
.\scripts\deploy-simple.ps1

# Déploiement rapide (sans tests)
.\scripts\deploy-simple.ps1 -SkipTests

# Déploiement ultra-rapide (image déjà construite)
.\scripts\deploy-simple.ps1 -SkipBuild -SkipTests
```

**Durée estimée** : 8-12 minutes (build compris)

---

## 📋 Prérequis

### Outils installés
- ✅ **gcloud CLI** - [Installer](https://cloud.google.com/sdk/docs/install)
- ✅ **Docker Desktop** - [Installer](https://www.docker.com/products/docker-desktop/)
- ✅ **PowerShell 7+** (Windows) ou Bash (Linux/Mac)

### Authentification
```bash
# S'authentifier avec gcloud
gcloud auth login

# Configurer le projet
gcloud config set project emergence-469005

# Vérifier
gcloud config get-value project  # Doit afficher: emergence-469005
```

---

## 🎯 Options de Déploiement

### Option 1: Déploiement Simple (100% trafic)

**Recommandé pour** : Déploiements rapides, environnements de dev/staging

```powershell
.\scripts\deploy-simple.ps1
```

**Workflow** :
1. ✅ Vérifications pré-déploiement (gcloud, docker, auth)
2. 🧪 Tests backend (optionnel avec `-SkipTests`)
3. 🐳 Build Docker image (platform linux/amd64)
4. 📤 Push Artifact Registry
5. 🚀 Deploy Cloud Run (100% trafic)
6. ✅ Health check

**Durée** : ~10 minutes

### Option 2: Déploiement Canary (En cours d'implémentation)

**Recommandé pour** : Production avec validation progressive

```powershell
.\scripts\deploy.ps1
```

**Workflow** :
1. ✅ Vérifications + Tests
2. 🐳 Build + Push
3. 🚀 Cloud Deploy Release → Canary (20% trafic)
4. 🔍 Vérifications automatiques (health, metrics, smoke tests)
5. ✅ Promotion → Stable (100% trafic)

**Status** : Pipeline configuré, promotion manuelle pour l'instant

---

## 🔧 Configuration Cloud Deploy (Avancée)

Le pipeline Cloud Deploy a été initialisé :

### Pipeline créé
```bash
# Vérifier le pipeline
gcloud deploy delivery-pipelines describe emergence-pipeline \
  --region=europe-west1 \
  --project=emergence-469005

# Lister les targets
gcloud deploy targets list \
  --region=europe-west1 \
  --project=emergence-469005
```

### Créer une release Cloud Deploy
```bash
# 1. Build & Push (comme d'habitude)
timestamp=$(date +%Y%m%d-%H%M%S)
image="europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp"

docker build --platform linux/amd64 -t $image .
docker push $image

# 2. Créer la release Cloud Deploy
gcloud deploy releases create rel-$timestamp \
  --project=emergence-469005 \
  --region=europe-west1 \
  --delivery-pipeline=emergence-pipeline \
  --skaffold-file=skaffold.yaml \
  --images=app=$image

# 3. Monitor le rollout
gcloud deploy rollouts list \
  --delivery-pipeline=emergence-pipeline \
  --region=europe-west1 \
  --project=emergence-469005
```

### Promotion manuelle (si nécessaire)
```bash
# Promouvoir vers stable après validation canary
gcloud deploy releases promote \
  --release=rel-$timestamp \
  --delivery-pipeline=emergence-pipeline \
  --region=europe-west1 \
  --project=emergence-469005 \
  --to-target=run-stable
```

---

## 🔄 Rollback

En cas de problème avec un déploiement :

### Rollback automatique
```powershell
# Rollback vers dernière révision stable
.\scripts\rollback.ps1

# Rollback vers révision spécifique
.\scripts\rollback.ps1 -TargetRevision emergence-app-00298-g8j

# Simulation (dry run)
.\scripts\rollback.ps1 -DryRun
```

### Rollback manuel
```bash
# Lister les révisions disponibles
gcloud run revisions list \
  --service emergence-app \
  --region europe-west1 \
  --project emergence-469005

# Basculer vers une révision précédente
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00XXX-yyy=100 \
  --region europe-west1 \
  --project emergence-469005
```

---

## 🔍 Vérification Post-Déploiement

### Endpoints à tester
```bash
SERVICE_URL="https://emergence-app-486095406755.europe-west1.run.app"

# Health check
curl $SERVICE_URL/api/health

# Readiness
curl $SERVICE_URL/health/readiness

# Metrics Prometheus
curl $SERVICE_URL/api/metrics

# Frontend
curl $SERVICE_URL/
```

### Logs Cloud Run
```bash
# Logs en temps réel (derniers 100 messages)
gcloud run services logs read emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --limit 100

# Logs avec filtre (erreurs uniquement)
gcloud run services logs read emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --limit 50 \
  | grep -i error
```

### Console Cloud Run
```
https://console.cloud.google.com/run/detail/europe-west1/emergence-app?project=emergence-469005
```

---

## 📊 Monitoring

### Métriques Prometheus
```bash
# Métriques mémoire
curl -s $SERVICE_URL/api/metrics | grep memory_analysis

# Cache hit rate
curl -s $SERVICE_URL/api/metrics | grep memory_cache_operations_total

# Latence chat
curl -s $SERVICE_URL/api/metrics | grep chat_message_latency
```

### Critères de santé
- ✅ **Health check** : HTTP 200 sur `/api/health`
- ✅ **Readiness** : HTTP 200 sur `/health/readiness`
- ✅ **Memory failures** : `memory_analysis_failure_total ≤ 2`
- ✅ **Cache hit rate** : `> 80%`
- ✅ **Frontend** : HTTP 200 sur `/`

---

## 🛠️ Troubleshooting

### Erreur: "gcloud command not found"
```bash
# Installer gcloud CLI
# Windows: https://cloud.google.com/sdk/docs/install
# Mac: brew install --cask google-cloud-sdk
# Linux: curl https://sdk.cloud.google.com | bash
```

### Erreur: "Docker daemon not running"
```bash
# Démarrer Docker Desktop
# Windows: Ouvrir Docker Desktop
# Linux: sudo systemctl start docker
```

### Erreur: "Permission denied" (IAM)
```bash
# Vérifier les permissions IAM (nécessite role Owner)
gcloud projects get-iam-policy emergence-469005

# Ajouter permissions si nécessaire (déjà fait normalement)
gcloud projects add-iam-policy-binding emergence-469005 \
  --member="user:gonzalefernando@gmail.com" \
  --role="roles/owner"
```

### Erreur: Health check fail après déploiement
```bash
# 1. Vérifier les logs
gcloud run services logs read emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --limit 100

# 2. Vérifier les variables d'environnement
gcloud run services describe emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --format="value(spec.template.spec.containers[0].env)"

# 3. Tester manuellement
curl -v https://emergence-app-486095406755.europe-west1.run.app/api/health
```

---

## 📚 Documentation Complète

- **Architecture déploiement** : [`docs/deployments/README.md`](docs/deployments/README.md)
- **Pipeline Cloud Deploy** : [`clouddeploy.yaml`](clouddeploy.yaml)
- **Targets Cloud Run** : [`targets.yaml`](targets.yaml)
- **Configuration Skaffold** : [`skaffold.yaml`](skaffold.yaml)
- **Vérifications canary** : [`verify.yaml`](verify.yaml)

---

## 🎯 Checklist Pré-Déploiement

Avant de déployer en production, vérifier :

- [ ] Tests backend passent (`pytest tests/backend/ -v`)
- [ ] Frontend build OK (`npm run build`)
- [ ] Variables d'environnement OK (`.env.production`)
- [ ] Secrets Cloud Run à jour (API keys)
- [ ] Authentification gcloud active
- [ ] Docker Desktop en cours d'exécution
- [ ] Branche `main` à jour avec GitHub
- [ ] Commit message descriptif
- [ ] Documentation mise à jour (si changements API)

---

## 📞 Support

**Issues GitHub** : [github.com/DrKz36/emergencev8/issues](https://github.com/DrKz36/emergencev8/issues)

**Documentation** : [`docs/`](docs/)

**Logs production** :
```bash
gcloud run services logs read emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --limit 100
```

**Console GCP** : [console.cloud.google.com](https://console.cloud.google.com/run/detail/europe-west1/emergence-app?project=emergence-469005)

---

**Dernière mise à jour** : 2025-10-14
**Version ÉMERGENCE** : V8 Phase P2
**Pipeline Cloud Deploy** : ✅ Configuré
**Status Production** : 🟢 Opérationnel
