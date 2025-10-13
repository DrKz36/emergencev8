# 🚀 Guide Build & Deploy Cloud Run - Pour Codex

**Date**: 2025-10-11
**Contexte**: Architecture simplifiée - conteneur unique sans canary
**Service**: `emergence-app` (100% trafic sur conteneur principal-source)
**Stratégie**: Déploiement direct - toute nouvelle révision remplace la précédente

---

## ⚡ TL;DR - Commandes Rapides

### Méthode Recommandée (Build Local + Push GCR)
```bash
# 1. Vérifier état Git
git status  # Doit être "working tree clean"
git log --oneline -3

# 2. Build local de l'image Docker
docker build -t gcr.io/emergence-469005/emergence-app:latest .

# 3. Push vers Google Container Registry
docker push gcr.io/emergence-469005/emergence-app:latest

# 4. Deploy sur Cloud Run
gcloud run deploy emergence-app \
  --image gcr.io/emergence-469005/emergence-app:latest \
  --region europe-west1 \
  --platform managed

# 5. Vérifier révision (seules les 3 dernières sont conservées)
gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005 --limit 3

# 6. Tester health
curl https://emergence-app-486095406755.europe-west1.run.app/api/health
```

> **⚡ Pourquoi cette méthode ?** Le build local est **beaucoup plus rapide et fiable** que `gcloud builds submit`. Les builds Cloud prennent 10-15min et ont des timeouts fréquents. Le build local prend 1-2min et utilise le cache Docker.

> **📌 Note importante** : Il n'y a plus de service canary. Toutes les nouvelles révisions sont déployées directement sur le conteneur principal `emergence-app` avec 100% du trafic. Seules les 3 dernières révisions fonctionnelles sont conservées automatiquement.

---

## 📋 Prérequis

### Outils requis
- ✅ Docker (build multi-platform activé)
- ✅ gcloud CLI (authentifié)
- ✅ Accès GCP projet `emergence-469005`

### Vérifications avant build
```bash
# Git propre
git status  # "nothing to commit, working tree clean"

# Docker auth GCP
gcloud auth configure-docker gcr.io

# Projet GCP actif
gcloud config get-value project  # emergence-469005
```

### Configuration SMTP pour les emails (Production)

Pour que les emails de réinitialisation de mot de passe fonctionnent en production, vous devez configurer les variables SMTP sur Cloud Run.

**Variables d'environnement requises** :
- `EMAIL_ENABLED=1`
- `SMTP_HOST=smtp.gmail.com`
- `SMTP_PORT=587`
- `SMTP_USER=<votre_email>@gmail.com`
- `SMTP_PASSWORD=<app_password>` (stocké en tant que secret)
- `SMTP_FROM_EMAIL=<votre_email>@gmail.com`
- `SMTP_FROM_NAME=ÉMERGENCE`
- `SMTP_USE_TLS=1`

**Créer un App Password Gmail** :
1. Allez sur https://myaccount.google.com/security
2. Activez la validation en 2 étapes
3. Créez un mot de passe d'application pour "Mail"
4. Copiez le mot de passe généré (16 caractères)

**Configurer le secret SMTP_PASSWORD** :
```bash
# Créer ou mettre à jour le secret
echo -n "votre_app_password" | gcloud secrets create SMTP_PASSWORD --data-file=- --replication-policy=automatic
# OU si le secret existe déjà
echo -n "votre_app_password" | gcloud secrets versions add SMTP_PASSWORD --data-file=-

# Mettre à jour Cloud Run pour utiliser le secret
gcloud run services update emergence-app \
  --region europe-west1 \
  --update-secrets "SMTP_PASSWORD=SMTP_PASSWORD:latest"

# Configurer les autres variables d'environnement
gcloud run services update emergence-app \
  --region europe-west1 \
  --update-env-vars "EMAIL_ENABLED=1,SMTP_HOST=smtp.gmail.com,SMTP_PORT=587,SMTP_USER=votre_email@gmail.com,SMTP_FROM_EMAIL=votre_email@gmail.com,SMTP_FROM_NAME=ÉMERGENCE"
```

---

## 🔨 Build Docker

### Commande standard
```bash
timestamp=$(date +%Y%m%d-%H%M%S)
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp .
```

### Surveillance build
```bash
# Build peut prendre 5-10 minutes
# Surveiller progress :
docker build --progress=plain ...  # Mode verbeux
```

### ⚠️ Problème connu : Image lourde (13.4GB)
**Symptôme** : Session précédente, deploy bloqué sur import dernier layer (timeout 15+ min)

**Cause** : Layer `pip install` = 7.9GB

**Solutions** (si deploy échoue) :
1. **Multi-stage build** (recommandé) :
   ```dockerfile
   # Stage 1: Build
   FROM python:3.11 AS builder
   COPY requirements.txt .
   RUN pip install --prefix=/install -r requirements.txt

   # Stage 2: Runtime
   FROM python:3.11-slim
   COPY --from=builder /install /usr/local
   COPY src/ /app/src/
   ```

2. **BuildKit cache mount** :
   ```dockerfile
   RUN --mount=type=cache,target=/root/.cache/pip \
       pip install -r requirements.txt
   ```

3. **Slim base image** :
   ```dockerfile
   FROM python:3.11-slim  # Au lieu de python:3.11
   ```

**Action** : Tester deploy d'abord, optimiser seulement si timeout.

---

## ⬆️ Push Registry GCP

```bash
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp
```

**Durée attendue** : 3-5 minutes (upload ~13GB)

**Vérification** :
```bash
# Lister images dans registry
gcloud container images list --repository=europe-west1-docker.pkg.dev/emergence-469005/app

# Voir digest image
gcloud container images describe europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp
```

---

## 🚀 Deploy Cloud Run

### Commande deploy (conteneur unique)
```bash
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated
```

> **Architecture simplifiée** :
> - **1 seul service** : `emergence-app` (conteneur principal-source)
> - **Pas de canary** : Le déploiement bascule directement 100% du trafic
> - **Gestion des révisions** : Seules les 3 dernières révisions fonctionnelles sont conservées

### Surveillance deploy
```bash
# Suivre progression
gcloud run operations list --region europe-west1

# Vérifier révisions (max 3 conservées)
gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005

# Lister tous les services (doit montrer uniquement emergence-app)
gcloud run services list --platform=managed --region=europe-west1
```

### Cas d'échec : Timeout import layer
**Symptôme** : Révision bloquée sur "Imported 16 of 17 layers" après 15+ min

**Action** :
1. Annuler révision bloquée :
   ```bash
   gcloud run revisions delete emergence-app-00XXX-yyy --region europe-west1
   ```
2. Optimiser Dockerfile (voir section Build ci-dessus)
3. Rebuild + redeploy

**Rollback** : En cas de problème, une des 3 dernières révisions conservées peut être réactivée :
```bash
# Lister les révisions disponibles
gcloud run revisions list --service emergence-app --region europe-west1 --limit 3

# Rollback vers une révision spécifique
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00XXX-yyy=100 \
  --region europe-west1
```

---

## ✅ Vérification Post-Deploy

### 1. Révision active
```bash
gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005 --limit 3

# Vérifier colonne "TRAFFIC" (doit être 100% sur nouvelle révision)
```

### 2. Health check
```bash
curl https://emergence-app-486095406755.europe-west1.run.app/api/health

# Attendu : {"status": "healthy", ...}
```

### 3. Tests endpoints critiques
```bash
# Metrics
curl https://emergence-app-486095406755.europe-west1.run.app/api/metrics

# Auth (doit retourner 401)
curl https://emergence-app-486095406755.europe-west1.run.app/api/chat/sessions

# Docs
curl https://emergence-app-486095406755.europe-west1.run.app/docs
```

---

## 📊 Logs Phase 2 (pour validation métriques)

### Logs analyses mémoire
```bash
# Chercher utilisation neo_analysis
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.message=~'MemoryAnalyzer.*neo_analysis'" \
  --project emergence-469005 \
  --limit 50 \
  --format json

# Chercher cache HIT/MISS
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.message=~'Cache (HIT|SAVED)'" \
  --project emergence-469005 \
  --limit 50

# Logs attendus :
# "[MemoryAnalyzer] Analyse réussie avec neo_analysis pour session xxx"
# "[MemoryAnalyzer] Cache HIT pour session xxx (hash=abc12345)"
# "[MemoryAnalyzer] Cache SAVED pour session xxx"
```

### Logs débats
```bash
# Chercher débats avec latence
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.message=~'debate'" \
  --project emergence-469005 \
  --limit 50

# Analyser :
# - Timestamps round 1 attacker + challenger (doivent se chevaucher)
# - Latence totale débat (cible ~11s vs ~15s avant)
```

### Calcul métriques
```bash
# Cache hit rate
# Compter lignes "Cache HIT" vs "Cache SAVED" (ratio HIT/(HIT+SAVED) = hit rate)

# Latence analyses
# Mesurer timestamp entre début analyse et "Analyse réussie"
# Cible : <2s (vs 4-6s avant)
```

---

## 🐛 Troubleshooting

### Problème : Build échoue (out of memory)
**Solution** : Augmenter RAM Docker
```bash
# Docker Desktop → Settings → Resources → Memory = 8GB minimum
```

### Problème : Push timeout
**Solution** : Retry avec compression
```bash
docker push --compress europe-west1-docker.pkg.dev/...
```

### Problème : Deploy bloqué sur "Importing layers"
**Solution** : Voir section "Cas d'échec" ci-dessus

### Problème : Révision unhealthy
**Logs** :
```bash
gcloud run revisions describe emergence-app-00XXX-yyy --region europe-west1 --format yaml

# Voir section "status.conditions"
```

**Actions** :
1. Vérifier variables env (API keys)
2. Vérifier health endpoint : `/api/health`
3. Rollback révision précédente :
   ```bash
   gcloud run services update-traffic emergence-app --to-revisions=emergence-app-00270-zs6=100 --region europe-west1
   ```

---

## 📝 Checklist Déploiement

- [ ] Git status clean
- [ ] Commits pushed
- [ ] Docker auth GCP configuré
- [ ] Build Docker réussi (timestamp sauvegardé)
- [ ] Push registry GCP réussi
- [ ] Deploy Cloud Run réussi sur `emergence-app` (conteneur unique)
- [ ] Vérification : un seul service actif (`gcloud run services list`)
- [ ] Révision active avec 100% trafic
- [ ] Seules 3 révisions conservées maximum
- [ ] Health check OK (curl /api/health)
- [ ] Tests endpoints critiques OK
- [ ] Métriques Prometheus exposées (/api/metrics)
- [ ] Documentation mise à jour (si modifications)

---

## 🎯 Objectifs Phase 2 (à valider en prod)

| Métrique | Avant | Cible | Validation |
|----------|-------|-------|------------|
| **Latence analyses** | 4-6s | 1-2s | Logs timestamp |
| **Latence débat round 1** | 5s | 3s | Logs timestamp overlap |
| **Cache hit rate** | 0% | 40-50% | Count HIT/(HIT+SAVED) |
| **Coût API** | 100% | 80% | Metrics endpoint |

---

## 📞 Contact Phase 3

**Si tout fonctionne** :
- Documenter métriques réelles dans `docs/deployments/2025-10-08-phase2-results.md`
- Passer Phase 3 (Redis, Prometheus, optimisations futures)

**Si problèmes** :
- Copier logs complets dans issue GitHub
- Tag @Claude Code pour analyse
- Rollback révision si critique

---

**Bonne chance Codex ! 🚀**
