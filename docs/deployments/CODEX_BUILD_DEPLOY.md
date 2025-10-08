# 🚀 Guide Build & Deploy Cloud Run - Pour Codex

**Date**: 2025-10-08
**Contexte**: Phase 2 Performance terminée, prêt pour build/deploy
**Révision actuelle**: `emergence-app-00270-zs6` (healthy, 100% trafic)

---

## ⚡ TL;DR - Commandes Rapides

```bash
# 1. Vérifier état Git
git status  # Doit être "working tree clean"
git log --oneline -3

# 2. Build & Push & Deploy (one-liner)
timestamp=$(date +%Y%m%d-%H%M%S) && \
docker build --platform linux/amd64 -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp . && \
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp && \
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated

# 3. Vérifier révision
gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005 --limit 3

# 4. Tester health
curl https://emergence-app-486095406755.europe-west1.run.app/api/health
```

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
gcloud auth configure-docker europe-west1-docker.pkg.dev

# Projet GCP actif
gcloud config get-value project  # emergence-469005
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

### Commande deploy
```bash
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated
```

### Surveillance deploy
```bash
# Suivre progression
gcloud run operations list --region europe-west1

# Vérifier révisions
gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005
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

**Fallback** : Révision `00270-zs6` reste active (pas d'impact prod)

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
- [ ] Commits pushed (4 commits : c7079f0, 69f7f50, 4f30be9, 2bdbde1)
- [ ] Docker auth GCP configuré
- [ ] Build Docker réussi (timestamp sauvegardé)
- [ ] Push registry GCP réussi
- [ ] Deploy Cloud Run réussi
- [ ] Révision active avec 100% trafic
- [ ] Health check OK (curl /api/health)
- [ ] Tests endpoints critiques OK
- [ ] Logs analyses récupérés (neo_analysis, cache)
- [ ] Logs débats récupérés (latence round 1)
- [ ] Métriques calculées (hit rate, latence)
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
