# Procédure de Déploiement Canary - ÉMERGENCE

**Date de création** : 2025-10-16
**Objectif** : Déploiement progressif sécurisé pour éviter les rollbacks hasardeux
**Statut** : ✅ Procédure officielle recommandée

---

## 🎯 Philosophie

La stratégie de déploiement canary permet de :
- ✅ Tester une nouvelle révision en production avec un trafic limité (10-25%)
- ✅ Valider la stabilité avant d'exposer tous les utilisateurs
- ✅ Faciliter le rollback en cas de problème (simple répartition de trafic)
- ✅ Éviter les déploiements "big bang" risqués

---

## 📋 Prérequis

Avant de démarrer un déploiement canary :

1. **Code validé localement** :
   ```bash
   # Tests backend
   pytest tests/backend/

   # Linting
   ruff check src/backend/
   mypy src/backend/

   # Build frontend
   npm run build
   ```

2. **Git propre et synchronisé** :
   ```bash
   git status
   git push origin main
   ```

3. **Authentification GCP** :
   ```bash
   gcloud auth list
   gcloud config set project emergence-469005
   ```

---

## 🚀 Procédure de Déploiement Canary

### Étape 1 : Build de l'image Docker

```bash
# Build avec double tag : latest + timestamp
docker build \
  -t europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest \
  -t europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:$(date +%Y%m%d-%H%M%S) \
  .
```

**Temps estimé** : 5-10 minutes
**Vérification** : `docker images | grep emergence-app`

---

### Étape 2 : Push vers Google Container Registry

```bash
# Push des deux tags
docker push europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest
docker push europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:$(date +%Y%m%d-%H%M%S)
```

**Temps estimé** : 3-5 minutes
**Vérification** : Vérifier dans [Google Container Registry](https://console.cloud.google.com/gcr/images/emergence-469005/europe-west1/emergence-repo/emergence-app)

---

### Étape 3 : Déploiement sans trafic (--no-traffic)

```bash
# Déployer la nouvelle révision SANS routage de trafic
gcloud run deploy emergence-app \
  --image=europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:20251016-082600 \
  --region=europe-west1 \
  --project=emergence-469005 \
  --no-traffic \
  --tag=canary-$(date +%Y%m%d)
```

**Paramètres importants** :
- `--no-traffic` : La révision reçoit 0% de trafic initialement
- `--tag=canary-YYYYMMDD` : Crée une URL dédiée pour tester la révision

**Résultat attendu** :
```
Service [emergence-app] revision [emergence-app-00445-xap] has been deployed and is serving 0 percent of traffic.
The revision can be reached directly at https://stable---emergence-app-47nct44nma-ew.a.run.app
```

**Temps estimé** : 2-3 minutes

---

### Étape 4 : Tests de validation de la nouvelle révision

#### 4.1 Health Check
```bash
# Tester l'endpoint health via l'URL de la révision canary
curl -s https://canary-20251016---emergence-app-47nct44nma-ew.a.run.app/api/health
```

**Résultat attendu** :
```json
{"status":"ok","message":"Emergence Backend is running."}
```

#### 4.2 Fichiers statiques
```bash
# Vérifier que les fichiers statiques sont accessibles
curl -I https://canary-20251016---emergence-app-47nct44nma-ew.a.run.app/src/frontend/main.js
```

**Résultat attendu** : `HTTP/1.1 200 OK`

#### 4.3 Vérification des logs (erreurs)
```bash
# Chercher les erreurs dans les 5 dernières minutes
gcloud logging read \
  "resource.type=cloud_run_revision AND \
   resource.labels.service_name=emergence-app AND \
   resource.labels.revision_name=emergence-app-00445-xap AND \
   severity>=ERROR" \
  --limit=10 \
  --project=emergence-469005 \
  --freshness=5m
```

**Résultat attendu** : Aucune erreur ou erreurs non-critiques

#### 4.4 Tests fonctionnels manuels (optionnel)
- Accéder à l'URL canary dans un navigateur
- Tester l'authentification
- Vérifier le chat
- Tester l'upload de documents

---

### Étape 5 : Routage progressif du trafic

#### 5.1 Phase 1 - 10% de trafic (Canary initial)

```bash
# Router 10% du trafic vers la nouvelle révision
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00445-xap=10 \
  --region=europe-west1 \
  --project=emergence-469005
```

**Temps d'observation recommandé** : 15-30 minutes

**Métriques à surveiller** :
```bash
# Logs en temps réel
gcloud logging tail \
  "resource.type=cloud_run_revision AND \
   resource.labels.service_name=emergence-app" \
  --project=emergence-469005
```

#### 5.2 Phase 2 - 25% de trafic (Si phase 1 OK)

```bash
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00445-xap=25 \
  --region=europe-west1 \
  --project=emergence-469005
```

**Temps d'observation recommandé** : 30 minutes - 1 heure

#### 5.3 Phase 3 - 50% de trafic (Si phase 2 OK)

```bash
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00445-xap=50 \
  --region=europe-west1 \
  --project=emergence-469005
```

**Temps d'observation recommandé** : 1-2 heures

#### 5.4 Phase 4 - 100% de trafic (Finalisation)

```bash
# Router 100% du trafic vers la nouvelle révision
gcloud run services update-traffic emergence-app \
  --to-latest \
  --region=europe-west1 \
  --project=emergence-469005
```

**Temps d'observation recommandé** : 24 heures minimum

---

## ⚠️ Procédure de Rollback

Si des problèmes sont détectés pendant le canary :

### Rollback immédiat (retour à 0% de trafic canary)

```bash
# Identifier la révision stable précédente
gcloud run revisions list \
  --service=emergence-app \
  --region=europe-west1 \
  --project=emergence-469005

# Router 100% du trafic vers la révision stable
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00366-jp2=100 \
  --region=europe-west1 \
  --project=emergence-469005
```

**Temps de rollback** : < 30 secondes

---

## 📊 Surveillance Post-Déploiement

### Métriques à surveiller (24-48h)

1. **Erreurs 5xx** :
   ```bash
   gcloud logging read \
     "resource.type=cloud_run_revision AND \
      resource.labels.service_name=emergence-app AND \
      httpRequest.status>=500" \
     --limit=50 \
     --project=emergence-469005 \
     --freshness=1h
   ```

2. **Latence** :
   - Accéder à [Cloud Run Metrics](https://console.cloud.google.com/run/detail/europe-west1/emergence-app/metrics)
   - Vérifier que la latence p95 < 500ms

3. **Taux d'erreur** :
   - Vérifier que le taux d'erreur < 1%

4. **Utilisation des ressources** :
   - CPU : < 80% en moyenne
   - Mémoire : < 3.5 Gi (sur 4 Gi alloués)

---

## 🔧 Commandes Utiles

### Lister les révisions
```bash
gcloud run revisions list \
  --service=emergence-app \
  --region=europe-west1 \
  --project=emergence-469005
```

### Voir la répartition actuelle du trafic
```bash
gcloud run services describe emergence-app \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.traffic)"
```

### Supprimer une révision défaillante
```bash
gcloud run revisions delete emergence-app-00445-xap \
  --region=europe-west1 \
  --project=emergence-469005
```

### Vérifier les variables d'environnement d'une révision
```bash
gcloud run revisions describe emergence-app-00445-xap \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(spec.containers[0].env)"
```

---

## 📋 Checklist de Déploiement

Avant de finaliser le déploiement (100% trafic) :

- [ ] ✅ Health check OK sur l'URL canary
- [ ] ✅ Aucune erreur 5xx dans les logs (15 min)
- [ ] ✅ Fichiers statiques accessibles
- [ ] ✅ Phase 1 (10%) : 15-30 min d'observation OK
- [ ] ✅ Phase 2 (25%) : 30 min - 1h d'observation OK
- [ ] ✅ Phase 3 (50%) : 1-2h d'observation OK
- [ ] ✅ Latence p95 < 500ms
- [ ] ✅ Taux d'erreur < 1%
- [ ] ✅ CPU < 80%, Mémoire < 3.5 Gi
- [ ] ✅ Tests fonctionnels manuels OK
- [ ] ✅ Pas de rapports d'erreur utilisateurs

---

## 🎯 Résumé de la Stratégie

```
┌─────────────────────────────────────────────────────────────┐
│ Déploiement Canary - Timeline Recommandée                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  T+0     : Déploiement --no-traffic (0%)                   │
│  T+5min  : Tests de validation                             │
│  T+10min : Phase 1 - 10% de trafic                         │
│  T+30min : Phase 2 - 25% de trafic (si OK)                 │
│  T+1h    : Phase 3 - 50% de trafic (si OK)                 │
│  T+3h    : Phase 4 - 100% de trafic (si OK)                │
│  T+24h   : Surveillance continue                           │
│                                                             │
│  ROLLBACK : Possible à tout moment (< 30s)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 Ressources

- **Cloud Run Documentation** : https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration
- **Monitoring Dashboard** : https://console.cloud.google.com/run/detail/europe-west1/emergence-app/metrics
- **Logs Explorer** : https://console.cloud.google.com/logs
- **Container Registry** : https://console.cloud.google.com/gcr/images/emergence-469005

---

## 📝 Historique

| Date | Révision | Trafic | Notes |
|------|----------|--------|-------|
| 2025-10-16 | emergence-app-00445-xap | 10% → 100% | Premier déploiement canary (procédure officielle) |
| 2025-10-16 | emergence-app-00366-jp2 | 100% → 0% | Révision stable précédente (SMTP fix) |

---

**Maintenu par** : Claude Code
**Dernière mise à jour** : 2025-10-16
**Version** : 1.0.0
