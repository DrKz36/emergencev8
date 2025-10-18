# 🚨 DÉPLOIEMENT HOTFIX CRITIQUE - Database Reconnection

**Date**: 2025-10-11
**Priorité**: CRITICAL (Résolution erreurs production)
**Impact**: Corrige 11.25% d'erreurs WebSocket en production

---

## 📋 Résumé Exécutif

**Problème production**:
- 9 erreurs WebSocket/heure (11.25% du trafic)
- Erreur: `RuntimeError: Database connection is not available`
- Cause: Connexion DB SQLite perdue après inactivité, pas de reconnexion automatique

**Solution implémentée**:
- Reconnexion automatique transparente dans `DatabaseManager._ensure_connection()`
- Graceful degradation avec logging détaillé
- Zero breaking change, compatible avec toute l'application

**Commit**: `f1d2877` - `fix(database): add automatic reconnection for lost DB connections`

---

## 🔧 Étapes de Déploiement

### Prérequis

1. **Docker Desktop** doit être démarré
2. **gcloud** doit être authentifié:
   ```bash
   gcloud auth login
   gcloud config set project emergence-469005
   ```

---

### 1. Vérifier le code

```bash
# Vérifier que le commit est bien présent
git log --oneline -1
# Doit afficher: f1d2877 fix(database): add automatic reconnection for lost DB connections

# Vérifier le changement
git show f1d2877 --stat
```

---

### 2. Build Docker Image

```bash
# Démarrer Docker Desktop si nécessaire (Windows)
# Puis construire l'image

docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:hotfix-db-reconnect-20251011 .
```

**Temps estimé**: 3-5 minutes

**Vérification**:
```bash
docker images | grep hotfix-db-reconnect
# Doit afficher l'image avec le tag hotfix-db-reconnect-20251011
```

---

### 3. Push vers Artifact Registry

```bash
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:hotfix-db-reconnect-20251011
```

**Temps estimé**: 2-3 minutes

**Vérification**:
```bash
gcloud artifacts docker images list europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app \
  --filter="tags:hotfix-db-reconnect-20251011" \
  --format="table(IMAGE,TAGS,CREATE_TIME)"
```

---

### 4. Deploy sur Cloud Run

```bash
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:hotfix-db-reconnect-20251011 \
  --platform managed \
  --region europe-west1 \
  --project emergence-469005 \
  --allow-unauthenticated
```

**Temps estimé**: 1-2 minutes
**Impact**: Aucun downtime (rolling deployment)

**Confirmation attendue**:
```
Deploying container to Cloud Run service [emergence-app] in project [emergence-469005] region [europe-west1]
✓ Deploying new service... Done.
  ✓ Creating Revision...
  ✓ Routing traffic...
Done.
Service [emergence-app] revision [emergence-app-XXXXX-yyy] has been deployed and is serving 100 percent of traffic.
Service URL: https://emergence-app-486095406755.europe-west1.run.app
```

---

## ✅ Vérifications Post-Déploiement

### 1. Health Checks

```bash
# Basic health
curl https://emergence-app-486095406755.europe-west1.run.app/api/health

# Liveness probe
curl https://emergence-app-486095406755.europe-west1.run.app/health/liveness

# Readiness probe (vérifie DB)
curl https://emergence-app-486095406755.europe-west1.run.app/health/readiness
```

**Attendu**: Tous retournent 200 OK avec status "healthy"/"alive"/"up"

---

### 2. Monitoring Logs (15 minutes après déploiement)

```bash
# Vérifier absence erreurs DB connection
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=emergence-app \
  AND severity>=ERROR \
  AND textPayload=~'Database connection is not available'" \
  --limit=10 \
  --freshness=15m \
  --project=emergence-469005
```

**Attendu**: `Listed 0 items.` (aucune erreur)

---

```bash
# Vérifier les reconnexions DB (si présentes, doivent être rares)
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=emergence-app \
  AND textPayload=~'Database reconnected successfully'" \
  --limit=20 \
  --freshness=15m \
  --project=emergence-469005
```

**Attendu**: 0-5 événements max (uniquement après périodes d'inactivité)

---

### 3. Test Fonctionnel WebSocket

1. **Ouvrir l'application**: https://emergence-app-486095406755.europe-west1.run.app
2. **Se connecter** (ou mode dev si AUTH_DEV_MODE=true)
3. **Démarrer une conversation** (n'importe quel message)
4. **Vérifier**: Message envoyé et réponse reçue sans erreur

**Attendu**: Conversation fonctionne normalement, pas d'erreur WebSocket

---

### 4. Re-exécuter Check Production

```bash
# Dans le terminal Claude Code
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```

**Attendu après 30 min**:
```
🟢 Production Status: OK

✅ Aucune anomalie détectée
✅ Latence stable
✅ Pas d'erreurs WebSocket
```

---

## 📊 Métriques de Succès

| Métrique | Avant Hotfix | Cible Après Hotfix | Vérification |
|----------|--------------|---------------------|--------------|
| **WebSocket Error Rate** | 11.25% | <1% | Logs 1h |
| **DB Connection Errors** | 9 errors/h | 0 errors/h | Logs 1h |
| **Reconnection Events** | N/A | <5/h | Logs 1h |
| **User Impact** | Blocked | None | Test manuel |

---

## 🔄 Rollback (si nécessaire)

Si le hotfix cause des problèmes inattendus:

```bash
# 1. Lister les révisions récentes
gcloud run revisions list \
  --service=emergence-app \
  --region=europe-west1 \
  --project=emergence-469005 \
  --limit=3

# 2. Identifier la révision précédente stable
#    (exemple: emergence-app-00297-6pr)

# 3. Rollback vers révision stable
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00297-6pr=100 \
  --region=europe-west1 \
  --project=emergence-469005
```

**Impact rollback**: Immédiat, aucun downtime

---

## 📝 Documentation Complète

**Rapport déploiement**: [docs/deployments/2025-10-11-hotfix-db-reconnection.md](docs/deployments/2025-10-11-hotfix-db-reconnection.md)

**Contenu**:
- Root cause analysis détaillée
- Traceback complet de l'erreur
- Code changement (avant/après)
- Post-mortem et leçons apprises
- Améliorations futures planifiées

---

## 🚨 Si Problèmes Pendant le Déploiement

### Docker Build échoue

**Symptôme**: `Cannot connect to Docker daemon`

**Solution**:
1. Démarrer Docker Desktop (Windows)
2. Attendre que Docker soit complètement démarré (icône verte)
3. Relancer le build

---

### gcloud not authenticated

**Symptôme**: `ERROR: (gcloud.run.deploy) You do not currently have an active account selected.`

**Solution**:
```bash
gcloud auth login
gcloud config set project emergence-469005
gcloud auth application-default login
```

---

### Push Artifact Registry échoue

**Symptôme**: `denied: Permission "artifactregistry.repositories.uploadArtifacts" denied`

**Solution**:
```bash
# Configurer Docker pour Artifact Registry
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

---

## 📞 Support

**En cas de blocage**:
1. Vérifier les logs complets: `gcloud logging read ... --limit=50`
2. Consulter Cloud Console: https://console.cloud.google.com/run/detail/europe-west1/emergence-app
3. Rollback si nécessaire (procédure ci-dessus)

---

## ✅ Checklist Finale

Après déploiement réussi:

- [ ] Health checks OK (3 endpoints)
- [ ] Logs sans erreurs DB (15 min monitoring)
- [ ] Test WebSocket manuel réussi
- [ ] Métriques dans les cibles (<1% errors)
- [ ] `/check_prod` status OK (après 30 min)
- [ ] Mettre à jour [docs/deployments/README.md](docs/deployments/README.md) avec nouvelle révision
- [ ] Notifier équipe (si applicable)

---

**Auteur**: ProdGuardian (Agent ÉMERGENCE)
**Date**: 2025-10-11
**Commit**: f1d2877cba85c85e3eaac57e73fe8eb14e1e9514
