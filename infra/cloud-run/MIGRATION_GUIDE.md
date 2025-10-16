# Guide de Migration vers l'Architecture Microservices

Ce guide vous accompagne pas à pas pour migrer votre application Emergence vers une architecture microservices sur Cloud Run.

## État actuel

✅ **Phase P2.2 et P2.3 complétées**:
- Service d'authentification créé et prêt à déployer
- Service de gestion des sessions créé et prêt à déployer
- Documentation et scripts de déploiement en place

## Avant de commencer

### Prérequis

- [ ] Accès administrateur au projet GCP `emergence-469005`
- [ ] Google Cloud SDK installé et configuré
- [ ] Docker installé et fonctionnel
- [ ] Accès en écriture au dépôt Git

### Préparation

1. **Backup de la base de données actuelle**
   ```bash
   # Sauvegarder la DB SQLite actuelle
   cp data/emergence.db data/emergence.db.backup.$(date +%Y%m%d)
   ```

2. **Créer les secrets requis** (voir section Secrets ci-dessous)

3. **Tester localement** avant de déployer

## Phase 1: Configuration des Secrets (15 min)

### Secrets obligatoires

```bash
# 1. JWT Secret (générer une clé aléatoire sécurisée)
openssl rand -hex 32 | gcloud secrets create AUTH_JWT_SECRET \
  --data-file=- \
  --replication-policy=automatic \
  --project=emergence-469005

# 2. Admin Emails (liste séparée par virgules)
echo "admin@example.com,owner@example.com" | gcloud secrets create AUTH_ADMIN_EMAILS \
  --data-file=- \
  --replication-policy=automatic \
  --project=emergence-469005

# 3. OpenAI API Key (si pas déjà créé)
echo "sk-..." | gcloud secrets create OPENAI_API_KEY \
  --data-file=- \
  --replication-policy=automatic \
  --project=emergence-469005

# 4. Anthropic API Key (si pas déjà créé)
echo "sk-ant-..." | gcloud secrets create ANTHROPIC_API_KEY \
  --data-file=- \
  --replication-policy=automatic \
  --project=emergence-469005
```

### Secrets optionnels (pour emails)

```bash
# Configuration SMTP pour reset de mot de passe
echo "smtp.gmail.com" | gcloud secrets create SMTP_HOST --data-file=- --replication-policy=automatic --project=emergence-469005
echo "your-email@gmail.com" | gcloud secrets create SMTP_USERNAME --data-file=- --replication-policy=automatic --project=emergence-469005
echo "your-app-password" | gcloud secrets create SMTP_PASSWORD --data-file=- --replication-policy=automatic --project=emergence-469005
echo "noreply@emergence.app" | gcloud secrets create SMTP_FROM_EMAIL --data-file=- --replication-policy=automatic --project=emergence-469005
```

### Donner accès aux secrets

```bash
# Service account à utiliser
SERVICE_ACCOUNT="486095406755-compute@developer.gserviceaccount.com"

# Donner accès à tous les secrets
for secret in AUTH_JWT_SECRET AUTH_ADMIN_EMAILS OPENAI_API_KEY ANTHROPIC_API_KEY GOOGLE_API_KEY SMTP_HOST SMTP_USERNAME SMTP_PASSWORD SMTP_FROM_EMAIL; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --project=emergence-469005 2>/dev/null || echo "Secret $secret may not exist"
done
```

## Phase 2: Déploiement du Service d'Authentification (20 min)

### 2.1 Build et test local (optionnel)

```bash
# Build l'image localement
docker build -f infra/cloud-run/auth-service.Dockerfile -t emergence-auth-local .

# Test local
docker run -p 8080:8080 \
  -e AUTH_JWT_SECRET="test-secret-change-me" \
  -e AUTH_ADMIN_EMAILS="admin@test.com" \
  -e LOG_LEVEL="DEBUG" \
  emergence-auth-local

# Dans un autre terminal
curl http://localhost:8080/api/health
```

### 2.2 Déploiement sur Cloud Run

```bash
# Déployer le service auth
./infra/cloud-run/deploy-auth-service.sh
```

### 2.3 Vérification

```bash
# Récupérer l'URL du service
AUTH_URL=$(gcloud run services describe emergence-auth-service \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.url)")

# Test health check
curl "$AUTH_URL/api/health"

# Test dev login (si AUTH_DEV_MODE activé)
curl -X POST "$AUTH_URL/api/auth/dev/login" -H "Content-Type: application/json"
```

## Phase 3: Déploiement du Service de Session (25 min)

### 3.1 Build et test local (optionnel)

```bash
# Build l'image localement
docker build -f infra/cloud-run/session-service.Dockerfile -t emergence-session-local .

# Test local
docker run -p 8081:8080 \
  -e LOG_LEVEL="DEBUG" \
  -e SESSION_INACTIVITY_TIMEOUT_MINUTES="30" \
  emergence-session-local

# Test
curl http://localhost:8081/api/health
```

### 3.2 Déploiement sur Cloud Run

```bash
# Déployer le service session
./infra/cloud-run/deploy-session-service.sh
```

### 3.3 Vérification

```bash
# Récupérer l'URL du service
SESSION_URL=$(gcloud run services describe emergence-session-service \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.url)")

# Test health check
curl "$SESSION_URL/api/health"

# Test metrics
curl "$SESSION_URL/metrics"
```

## Phase 4: Tests d'intégration (15 min)

```bash
# Lancer la suite de tests
chmod +x infra/cloud-run/test-services.sh
./infra/cloud-run/test-services.sh
```

Tous les tests doivent passer ✅

## Phase 5: Configuration du Frontend (30 min)

### 5.1 Mettre à jour les URLs de service

Modifier votre configuration frontend pour pointer vers les nouveaux services:

```javascript
// config/services.js
const SERVICES = {
  auth: process.env.REACT_APP_AUTH_SERVICE_URL || 'https://emergence-auth-service-XXX-ew.a.run.app',
  session: process.env.REACT_APP_SESSION_SERVICE_URL || 'https://emergence-session-service-XXX-ew.a.run.app',
  main: process.env.REACT_APP_MAIN_SERVICE_URL || 'https://emergence-app-XXX-ew.a.run.app'
};
```

### 5.2 Adapter les appels API

**Avant**:
```javascript
// Tout allait vers la même URL
fetch('/api/auth/login', ...)
fetch('/ws/session-id', ...)
```

**Après**:
```javascript
// Routing vers les microservices
fetch(`${SERVICES.auth}/api/auth/login`, ...)
new WebSocket(`${SERVICES.session.replace('https', 'wss')}/ws/session-id`)
```

### 5.3 Gestion des cookies cross-domain

Les services étant sur des domaines différents, configurez:

```javascript
// Activer credentials pour CORS
fetch(url, {
  credentials: 'include',  // Important pour les cookies
  ...
})
```

## Phase 6: Monitoring et Alerting (20 min)

### 6.1 Créer des dashboards Cloud Monitoring

```bash
# Accéder à Cloud Monitoring
open "https://console.cloud.google.com/monitoring/dashboards?project=emergence-469005"
```

Créer un dashboard avec:
- Request count par service
- Latency p50, p95, p99
- Error rate
- Instance count
- Sessions actives (custom metric)

### 6.2 Configurer des alertes

Exemples d'alertes recommandées:

1. **Taux d'erreur élevé** (>5% sur 5 min)
2. **Latence élevée** (p95 > 1000ms)
3. **Pas d'instances actives** (min instances = 0)
4. **Coûts excessifs** (seuil à définir)

## Phase 7: Optimisation (optionnel)

### 7.1 Ajuster les ressources

Après quelques jours d'utilisation, ajuster:

```bash
# Si le service auth est sur-dimensionné
gcloud run services update emergence-auth-service \
  --cpu=1 \
  --memory=512Mi \
  --region=europe-west1 \
  --project=emergence-469005

# Si le service session a besoin de plus de ressources
gcloud run services update emergence-session-service \
  --max-instances=30 \
  --region=europe-west1 \
  --project=emergence-469005
```

### 7.2 Activer CDN (si applicable)

Pour les assets statiques, configurer Cloud CDN devant le load balancer.

### 7.3 Optimiser les cold starts

```bash
# Augmenter min-instances pour les services critiques
gcloud run services update emergence-auth-service \
  --min-instances=2 \
  --region=europe-west1 \
  --project=emergence-469005
```

## Rollback Plan

Si quelque chose ne va pas:

### Rollback rapide

```bash
# Revenir à la révision précédente
gcloud run services update-traffic emergence-auth-service \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=europe-west1 \
  --project=emergence-469005
```

### Rollback complet

Rediriger le trafic vers l'application monolithique existante et désactiver les nouveaux services.

## Checklist de migration

Avant de passer en production:

- [ ] Tous les secrets sont configurés
- [ ] Services déployés avec succès
- [ ] Tests d'intégration passent à 100%
- [ ] Frontend mis à jour et testé
- [ ] Monitoring et alertes configurés
- [ ] Documentation à jour
- [ ] Plan de rollback testé
- [ ] Équipe formée sur la nouvelle architecture
- [ ] Période de test en staging réussie (recommandé: 1 semaine)

## Coûts estimés

**Service Auth**:
- Min: ~$10-15/mois (1 instance permanente)
- Max: ~$50-100/mois (pic à 10 instances)

**Service Session**:
- Min: ~$40-60/mois (2 instances permanentes)
- Max: ~$200-400/mois (pic à 20 instances)

**Total nouveau**: ~$50-500/mois selon l'utilisation

**Note**: Ajuster min-instances=0 en dev pour économiser.

## Support

### Problèmes courants

**Build Docker échoue**:
- Vérifier que tous les fichiers sources existent
- Nettoyer le cache: `docker system prune -a`

**Service ne démarre pas**:
- Vérifier les logs: `gcloud run services logs read SERVICE_NAME`
- Vérifier que les secrets existent et sont accessibles

**Erreurs 401/403**:
- Vérifier la configuration JWT
- Vérifier que les cookies sont transmis (CORS credentials)

### Ressources

- [Documentation complète](./MICROSERVICES_ARCHITECTURE.md)
- [README](./README.md)
- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Support GCP](https://cloud.google.com/support)

## Prochaines étapes

Après P2.2 et P2.3, planifier:

- **P2.4**: Migration du service Chat/LLM
- **P2.5**: Migration du service Documents
- **P2.6**: Migration du service Memory/RAG
- **P2.7**: Configuration du Load Balancer unifié
- **P2.8**: Migration vers Cloud SQL (PostgreSQL)

---

**Durée estimée totale**: 2-3 heures pour un déploiement initial complet.

**Difficulté**: Moyenne (nécessite connaissance de GCP et Docker)

**Impact utilisateurs**: Minimal si migration progressive avec tests adéquats
