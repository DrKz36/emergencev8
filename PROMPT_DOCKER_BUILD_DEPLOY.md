# 🐳 PROMPT - Docker Build & Deploy Révision

**Date création** : 2025-10-10
**Objectif** : Build image Docker et déployer nouvelle révision de l'application Emergence
**Environnement** : Production Cloud Run (GCP)

---

## 🎯 Objectif Session

Construire l'image Docker de l'application avec les dernières modifications (Phase P2 Sprint 3 complété) et déployer une nouvelle révision sur Cloud Run.

---

## 📋 Prérequis

### ✅ Vérifications Avant Build

1. **Phase P2 Sprint 3 complétée** ✅
   - ProactiveHintsUI frontend opérationnel
   - MemoryDashboard fonctionnel
   - Endpoint `/api/memory/user/stats` implémenté
   - Tests E2E passants
   - Commit : `50b4f34` feat(P2 Sprint3)

2. **Environnement local** :
   ```bash
   # Vérifier Docker installé
   docker --version
   # Docker version 20.10+ requis

   # Vérifier gcloud CLI
   gcloud --version
   # gcloud 400.0.0+ requis

   # Vérifier authentification GCP
   gcloud auth list
   # Doit afficher compte authentifié
   ```

3. **Configuration GCP** :
   - Project ID : `emergence-prod` (à confirmer)
   - Region : `us-central1` (à confirmer)
   - Service name : `emergence-api` (à confirmer)
   - Artifact Registry : `gcr.io` ou `us-central1-docker.pkg.dev`

---

## 🔨 Étapes de Build & Deploy

### 1️⃣ Vérifier le Dockerfile

**Fichier** : `Dockerfile` (racine du projet)

**Vérifications** :
```bash
# Lire le Dockerfile actuel
cat Dockerfile

# Vérifier présence fichiers requis
ls -la requirements.txt
ls -la src/frontend/
ls -la src/backend/
```

**Points critiques à vérifier** :
- ✅ COPY frontend (HTML, CSS, JS)
- ✅ COPY backend (Python sources)
- ✅ Installation requirements.txt
- ✅ EXPOSE port correct (8080 pour Cloud Run)
- ✅ CMD/ENTRYPOINT pour démarrage uvicorn

**Exemple Dockerfile minimal** (si manquant) :
```dockerfile
# Base image Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY public/ ./public/

# Copy frontend assets
COPY src/frontend/ ./src/frontend/

# Expose port
EXPOSE 8080

# Environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Start application
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

### 2️⃣ Build l'Image Docker Localement

**Commandes** :
```bash
# 1. Vérifier emplacement
cd c:\dev\emergenceV8

# 2. Build image (tag avec version)
docker build -t emergence-app:p2-sprint3 .

# Alternative avec tag commit SHA
docker build -t emergence-app:50b4f34 .

# 3. Vérifier image créée
docker images | grep emergence-app

# 4. Tester image localement (optionnel)
docker run -p 8080:8080 \
  -e DATABASE_URL="sqlite:///./test.db" \
  -e OPENAI_API_KEY="sk-test..." \
  emergence-app:p2-sprint3

# 5. Tester health endpoint
curl http://localhost:8080/health
# Doit retourner {"status": "ok"}

# 6. Arrêter container test
docker ps
docker stop <container_id>
```

---

### 3️⃣ Tag et Push vers Artifact Registry

**Option A : Google Container Registry (gcr.io)** :
```bash
# 1. Configurer Docker pour GCP
gcloud auth configure-docker

# 2. Tag image pour GCR
PROJECT_ID="emergence-prod"  # À confirmer
IMAGE_NAME="emergence-app"
TAG="p2-sprint3"

docker tag emergence-app:p2-sprint3 \
  gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${TAG}

# Tag également avec 'latest'
docker tag emergence-app:p2-sprint3 \
  gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest

# 3. Push vers GCR
docker push gcr.io/${PROJECT_ID}/${IMAGE_NAME}:${TAG}
docker push gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest

# 4. Vérifier upload
gcloud container images list --repository=gcr.io/${PROJECT_ID}
```

**Option B : Artifact Registry (Recommandé GCP moderne)** :
```bash
# 1. Configurer Docker pour Artifact Registry
REGION="us-central1"  # À confirmer
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 2. Tag image
PROJECT_ID="emergence-prod"
REPO_NAME="emergence-repo"  # À confirmer
IMAGE_NAME="emergence-app"
TAG="p2-sprint3"

docker tag emergence-app:p2-sprint3 \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}

docker tag emergence-app:p2-sprint3 \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest

# 3. Push vers Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${TAG}
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:latest
```

---

### 4️⃣ Déployer sur Cloud Run

**Commande de déploiement** :

```bash
# Variables (à adapter selon config)
SERVICE_NAME="emergence-api"
REGION="us-central1"
PROJECT_ID="emergence-prod"
IMAGE_URL="gcr.io/${PROJECT_ID}/emergence-app:p2-sprint3"

# OU si Artifact Registry
# IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/emergence-repo/emergence-app:p2-sprint3"

# Deploy nouvelle révision
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_URL} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 1 \
  --concurrency 80 \
  --set-env-vars "ENVIRONMENT=production,LOG_LEVEL=info" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,DATABASE_URL=database-url:latest" \
  --tag p2-sprint3

# Flags expliqués :
# --image           : URL complète de l'image Docker
# --platform        : 'managed' pour Cloud Run entièrement géré
# --region          : Région de déploiement
# --allow-unauthenticated : Accès public (si applicable)
# --port            : Port exposé dans le container
# --memory          : RAM allouée (ajuster selon besoins)
# --cpu             : vCPUs alloués
# --timeout         : Timeout requêtes (300s = 5min)
# --max-instances   : Auto-scaling maximum
# --min-instances   : Instances minimum (1 = always warm)
# --concurrency     : Requêtes simultanées par instance
# --set-env-vars    : Variables d'environnement publiques
# --set-secrets     : Secrets depuis Secret Manager
# --tag             : Tag pour traffic splitting (blue/green)
```

**Déploiement progressif (Blue/Green)** :
```bash
# 1. Deploy nouvelle révision avec tag (sans traffic)
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_URL} \
  --platform managed \
  --region ${REGION} \
  --no-traffic \
  --tag p2-sprint3

# 2. Vérifier nouvelle révision
REVISION_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --format 'value(status.traffic[0].url)')

echo "Test URL: ${REVISION_URL}"

# 3. Tester nouvelle révision
curl ${REVISION_URL}/health
curl ${REVISION_URL}/api/memory/user/stats  # Test endpoint P2

# 4. Si OK, router 10% du traffic
gcloud run services update-traffic ${SERVICE_NAME} \
  --region ${REGION} \
  --to-revisions LATEST=10,PREVIOUS=90

# 5. Vérifier métriques (erreurs, latence)
# Attendre 10-15 minutes

# 6. Si OK, router 100% du traffic
gcloud run services update-traffic ${SERVICE_NAME} \
  --region ${REGION} \
  --to-latest

# 7. Si KO, rollback immédiat
gcloud run services update-traffic ${SERVICE_NAME} \
  --region ${REGION} \
  --to-revisions LATEST=0,PREVIOUS=100
```

---

### 5️⃣ Vérifier le Déploiement

**Commandes de vérification** :
```bash
# 1. Vérifier statut service
gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --format yaml

# 2. Lister révisions
gcloud run revisions list \
  --service ${SERVICE_NAME} \
  --region ${REGION}

# 3. Obtenir URL publique
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --format 'value(status.url)')

echo "Service URL: ${SERVICE_URL}"

# 4. Tester endpoints critiques
curl ${SERVICE_URL}/health
# Attendu: {"status": "ok"}

curl ${SERVICE_URL}/api/memory/user/stats \
  -H "Authorization: Bearer <TOKEN>"
# Attendu: {"preferences": {...}, "concepts": {...}, "stats": {...}}

# 5. Tester frontend
curl ${SERVICE_URL}/
# Attendu: HTML page d'accueil

# 6. Vérifier logs
gcloud run services logs read ${SERVICE_NAME} \
  --region ${REGION} \
  --limit 50

# 7. Vérifier métriques Cloud Monitoring
gcloud monitoring dashboards list
# Puis accéder via console GCP
```

---

## 🔍 Tests Post-Déploiement

### Tests Fonctionnels

```bash
# Variables
SERVICE_URL="https://emergence-api-xxxxx.a.run.app"  # URL réelle
AUTH_TOKEN="<votre_token_jwt>"  # Token valide

# 1. Health check
curl -X GET ${SERVICE_URL}/health

# 2. Test endpoint ProactiveHints (nouveau P2 Sprint 3)
curl -X GET ${SERVICE_URL}/api/memory/user/stats \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# 3. Test WebSocket (si applicable)
# Utiliser wscat ou client WebSocket
wscat -c wss://emergence-api-xxxxx.a.run.app/ws/test-session

# 4. Test frontend ProactiveHintsUI
# Ouvrir dans navigateur
open ${SERVICE_URL}
# Vérifier console JavaScript (pas d'erreurs)
# Vérifier Network tab (fichiers CSS/JS chargés)

# 5. Test dashboard mémoire
# Naviguer vers /memory (si route configurée)
open ${SERVICE_URL}/memory
```

### Vérifications Métriques

**Via gcloud** :
```bash
# Latence moyenne (dernière 1h)
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/request_latencies"' \
  --format json

# Taux d'erreur
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class!="2xx"' \
  --format json

# Utilisation mémoire
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/container/memory/utilizations"' \
  --format json
```

**Via Console GCP** :
1. Ouvrir [Cloud Run Console](https://console.cloud.google.com/run)
2. Sélectionner service `emergence-api`
3. Onglet **Metrics** :
   - Request count
   - Request latency (p50, p95, p99)
   - Container instance count
   - Memory utilization
   - CPU utilization
4. Vérifier alertes (si configurées)

---

## 🚨 Rollback Rapide

**Si problème détecté** :

```bash
# Option 1 : Rollback vers révision précédente
gcloud run services update-traffic ${SERVICE_NAME} \
  --region ${REGION} \
  --to-revisions PREVIOUS=100

# Option 2 : Rollback vers révision spécifique
# Lister révisions
gcloud run revisions list \
  --service ${SERVICE_NAME} \
  --region ${REGION}

# Identifier révision stable (ex: emergence-api-00042-abc)
STABLE_REVISION="emergence-api-00042-abc"

gcloud run services update-traffic ${SERVICE_NAME} \
  --region ${REGION} \
  --to-revisions ${STABLE_REVISION}=100

# Option 3 : Supprimer révision problématique
PROBLEMATIC_REVISION="emergence-api-00043-def"

gcloud run revisions delete ${PROBLEMATIC_REVISION} \
  --region ${REGION} \
  --quiet
```

---

## 📊 Monitoring Continu

### Logs en Temps Réel

```bash
# Tail logs (stream continu)
gcloud run services logs tail ${SERVICE_NAME} \
  --region ${REGION}

# Filter logs par niveau
gcloud run services logs read ${SERVICE_NAME} \
  --region ${REGION} \
  --log-filter 'severity>=ERROR' \
  --limit 100

# Filter logs par endpoint
gcloud run services logs read ${SERVICE_NAME} \
  --region ${REGION} \
  --log-filter 'httpRequest.requestUrl=~"/api/memory/user/stats"' \
  --limit 50
```

### Alertes (à configurer si pas déjà fait)

```bash
# Créer alerte sur taux d'erreur > 5%
gcloud alpha monitoring policies create \
  --notification-channels="<channel_id>" \
  --display-name="Emergence API - High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.label.response_code_class!="2xx"'

# Créer alerte sur latence p99 > 2s
gcloud alpha monitoring policies create \
  --notification-channels="<channel_id>" \
  --display-name="Emergence API - High Latency" \
  --condition-display-name="P99 latency > 2s" \
  --condition-threshold-value=2000 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_latencies"'
```

---

## 🐛 Troubleshooting

### Problème : Image build échoue

```bash
# Vérifier logs build
docker build -t emergence-app:debug . 2>&1 | tee build.log

# Problèmes fréquents :
# 1. requirements.txt manquant
ls -la requirements.txt

# 2. Fichiers sources manquants
ls -la src/backend/
ls -la src/frontend/

# 3. Dépendances système
# Ajouter au Dockerfile si erreur compilation :
# RUN apt-get install -y build-essential python3-dev
```

### Problème : Push GCR échoue

```bash
# Vérifier auth
gcloud auth list
gcloud auth login  # Si nécessaire

# Vérifier permissions
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:$(gcloud config get-value account)"

# Vérifier quota
gcloud compute project-info describe --project=${PROJECT_ID}
```

### Problème : Déploiement Cloud Run échoue

```bash
# Vérifier logs déploiement
gcloud run services logs read ${SERVICE_NAME} \
  --region ${REGION} \
  --limit 100

# Problèmes fréquents :
# 1. Port incorrect (doit être 8080)
# 2. Health check timeout (augmenter --timeout)
# 3. Secrets manquants (vérifier Secret Manager)
# 4. Memory insuffisante (augmenter --memory)
```

### Problème : Frontend assets non chargés

```bash
# Vérifier COPY dans Dockerfile
grep -n "COPY.*frontend" Dockerfile

# Vérifier structure dans image
docker run -it emergence-app:p2-sprint3 ls -la src/frontend/

# Vérifier serveur static files dans backend
# Fichier: src/backend/main.py
# Doit contenir :
# app.mount("/static", StaticFiles(directory="src/frontend"), name="static")
```

---

## ✅ Checklist Finale

### Avant Build
- [ ] Vérifier commit récent (50b4f34 Sprint P3)
- [ ] Vérifier Dockerfile à jour
- [ ] Vérifier requirements.txt complet
- [ ] Tests locaux passants

### Build & Push
- [ ] Image Docker buildée localement
- [ ] Tests container local OK
- [ ] Image taggée correctement (p2-sprint3 + latest)
- [ ] Push vers GCR/Artifact Registry OK
- [ ] Image visible dans registry

### Déploiement
- [ ] Nouvelle révision déployée
- [ ] Health check OK
- [ ] Logs sans erreurs critiques
- [ ] Endpoints API testés
- [ ] Frontend accessible
- [ ] ProactiveHintsUI fonctionnel
- [ ] Dashboard mémoire accessible

### Post-Déploiement
- [ ] Métriques normales (latence, erreurs)
- [ ] Traffic 100% sur nouvelle révision
- [ ] Révisions anciennes conservées (rollback possible)
- [ ] Documentation déploiement mise à jour
- [ ] Équipe notifiée

---

## 📚 Références

### Documentation GCP
- [Cloud Run Quickstart](https://cloud.google.com/run/docs/quickstarts/build-and-deploy)
- [Container Registry](https://cloud.google.com/container-registry/docs)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Cloud Run Traffic Management](https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)

### Commandes Utiles
```bash
# Résumé déploiement
echo "
SERVICE_NAME=${SERVICE_NAME}
REGION=${REGION}
PROJECT_ID=${PROJECT_ID}
IMAGE_TAG=p2-sprint3
COMMIT_SHA=50b4f34
"

# Quick deploy (tout en une commande)
gcloud run deploy emergence-api \
  --image gcr.io/emergence-prod/emergence-app:p2-sprint3 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --tag p2-sprint3
```

---

**Date dernière mise à jour** : 2025-10-10
**Auteur** : Claude Code
**Version** : 1.0 (Phase P2 Sprint 3)
**Statut** : Prêt pour exécution

---

## 🎯 Résumé Session Attendu

À la fin de cette session, vous devriez avoir :
1. ✅ Image Docker buildée avec Phase P2 Sprint 3
2. ✅ Image pushée vers GCR/Artifact Registry
3. ✅ Nouvelle révision déployée sur Cloud Run
4. ✅ Tests fonctionnels passants (health, API, frontend)
5. ✅ Métriques validées (latence, erreurs)
6. ✅ Documentation déploiement mise à jour

**Temps estimé** : 30-45 minutes (avec tests)

**Prêt à déployer ! 🚀**
