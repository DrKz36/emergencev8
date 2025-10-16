# Emergence Cloud Run Infrastructure

Ce dossier contient tous les fichiers nécessaires pour déployer l'application Emergence sur Google Cloud Run avec une architecture microservices.

## Structure

```
infra/cloud-run/
├── README.md                           # Ce fichier
├── MICROSERVICES_ARCHITECTURE.md       # Documentation complète de l'architecture
│
├── auth-service.yaml                   # Configuration Cloud Run - Auth
├── auth-service.Dockerfile             # Dockerfile - Auth Service
├── auth-requirements.txt               # Dépendances Python - Auth
├── deploy-auth-service.sh              # Script de déploiement - Auth
│
├── session-service.yaml                # Configuration Cloud Run - Session
├── session-service.Dockerfile          # Dockerfile - Session Service
├── session-requirements.txt            # Dépendances Python - Session
├── deploy-session-service.sh           # Script de déploiement - Session
│
├── deploy-all-services.sh              # Script de déploiement global
└── svc_from_canary.yaml                # Configuration existante (legacy)
```

## Quick Start

### Prérequis

1. **Google Cloud SDK** installé et configuré
   ```bash
   gcloud auth login
   gcloud config set project emergence-469005
   ```

2. **Docker** installé et fonctionnel
   ```bash
   docker --version
   ```

3. **Secrets configurés** dans Google Secret Manager:
   - `AUTH_JWT_SECRET` - Secret pour les JWT
   - `AUTH_ADMIN_EMAILS` - Liste des emails administrateurs
   - `OPENAI_API_KEY` - Clé API OpenAI
   - `ANTHROPIC_API_KEY` - Clé API Anthropic
   - `GOOGLE_API_KEY` - Clé API Google

### Déploiement complet

```bash
# Depuis la racine du projet
cd /path/to/emergenceV8

# Rendre les scripts exécutables
chmod +x infra/cloud-run/*.sh

# Déployer tous les services
./infra/cloud-run/deploy-all-services.sh
```

Le script interactif vous demandera quels services déployer.

### Déploiement individuel

#### Service d'authentification

```bash
./infra/cloud-run/deploy-auth-service.sh
```

#### Service de session

```bash
./infra/cloud-run/deploy-session-service.sh
```

## Services déployés

### 1. Service d'Authentification

**URL**: `https://emergence-auth-service-XXXXXXXXXX-ew.a.run.app`

**Endpoints principaux**:
- `POST /api/auth/login` - Connexion
- `POST /api/auth/logout` - Déconnexion
- `GET /api/auth/session` - Info session
- `POST /api/auth/change-password` - Changer mot de passe
- Admin endpoints sous `/api/auth/admin/`

**Configuration**:
- CPU: 2 cores
- Memory: 1Gi
- Min instances: 1
- Max instances: 10
- Timeout: 300s

### 2. Service de Session

**URL**: `https://emergence-session-service-XXXXXXXXXX-ew.a.run.app`

**Endpoints principaux**:
- `WS /ws/{session_id}` - WebSocket pour chat
- `GET /api/health` - Health check
- Thread et memory management endpoints

**Configuration**:
- CPU: 4 cores
- Memory: 2Gi
- Min instances: 2
- Max instances: 20
- Timeout: 900s (15 min)

## Configuration des secrets

### Créer un nouveau secret

```bash
# Depuis un fichier
gcloud secrets create SECRET_NAME \
  --data-file=/path/to/secret.txt \
  --replication-policy=automatic \
  --project=emergence-469005

# Depuis stdin
echo "secret-value" | gcloud secrets create SECRET_NAME \
  --data-file=- \
  --replication-policy=automatic \
  --project=emergence-469005
```

### Mettre à jour un secret existant

```bash
echo "new-value" | gcloud secrets versions add SECRET_NAME \
  --data-file=- \
  --project=emergence-469005
```

### Donner accès aux secrets au service account

```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:486095406755-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=emergence-469005
```

## Tests

### Test du service Auth

```bash
# Récupérer l'URL
AUTH_URL=$(gcloud run services describe emergence-auth-service \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.url)")

# Health check
curl "$AUTH_URL/api/health"

# Login (mode dev si activé)
curl -X POST "$AUTH_URL/api/auth/dev/login" \
  -H "Content-Type: application/json"
```

### Test du service Session

```bash
# Récupérer l'URL
SESSION_URL=$(gcloud run services describe emergence-session-service \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.url)")

# Health check
curl "$SESSION_URL/api/health"
```

## Monitoring

### Logs

```bash
# Logs en temps réel
gcloud run services logs tail emergence-auth-service \
  --region=europe-west1 \
  --project=emergence-469005

# Logs des dernières 24h
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-auth-service" \
  --project=emergence-469005 \
  --limit=100 \
  --freshness=1d
```

### Métriques

Les services exposent des métriques Prometheus sur `/metrics`.

**Métriques clés du service Session**:
- `sessions_timeout_total` - Sessions fermées par timeout
- `sessions_warning_sent_total` - Avertissements envoyés
- `sessions_active_current` - Sessions actives
- `session_inactivity_duration_seconds` - Durée d'inactivité

### Cloud Monitoring

Dashboard disponible dans:
https://console.cloud.google.com/run?project=emergence-469005

## Troubleshooting

### Le service ne démarre pas

1. Vérifier les logs:
   ```bash
   gcloud run services logs read SERVICE_NAME \
     --region=europe-west1 \
     --project=emergence-469005
   ```

2. Vérifier la configuration:
   ```bash
   gcloud run services describe SERVICE_NAME \
     --region=europe-west1 \
     --project=emergence-469005
   ```

3. Vérifier les secrets:
   ```bash
   gcloud secrets list --project=emergence-469005
   ```

### Problèmes de build Docker

1. Vérifier que Docker est lancé
2. Nettoyer les images:
   ```bash
   docker system prune -a
   ```

3. Rebuild sans cache:
   ```bash
   docker build --no-cache -f DOCKERFILE_PATH -t IMAGE_NAME .
   ```

### Rollback

Revenir à une version précédente:

```bash
# Lister les révisions
gcloud run revisions list \
  --service=SERVICE_NAME \
  --region=europe-west1 \
  --project=emergence-469005

# Basculer le trafic
gcloud run services update-traffic SERVICE_NAME \
  --to-revisions=REVISION_NAME=100 \
  --region=europe-west1 \
  --project=emergence-469005
```

## Optimisations

### Réduire les coûts

1. **Ajuster min-instances**: Mettre à 0 pour les environnements de dev
   ```bash
   gcloud run services update SERVICE_NAME \
     --min-instances=0 \
     --region=europe-west1 \
     --project=emergence-469005
   ```

2. **Réduire les ressources** pour les services peu utilisés
3. **Activer CPU throttling** si approprié

### Améliorer les performances

1. **Augmenter min-instances** pour réduire le cold start
2. **Activer startup-cpu-boost** (déjà fait)
3. **Optimiser les images Docker** (multi-stage builds)
4. **Utiliser le cache de build**

## Prochaines étapes

Voir [MICROSERVICES_ARCHITECTURE.md](./MICROSERVICES_ARCHITECTURE.md) pour:
- Architecture détaillée
- Roadmap de migration (phases P2.4 - P2.9)
- Considérations de scaling et sécurité
- Guide de migration vers PostgreSQL

## Support

- **Documentation Cloud Run**: https://cloud.google.com/run/docs
- **Emergence Project**: [Github](https://github.com/your-org/emergence)
- **Issues**: Créer un ticket sur Github
