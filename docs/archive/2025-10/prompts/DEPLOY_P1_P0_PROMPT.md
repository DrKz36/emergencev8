# Prompt Déploiement Production - Phase P1+P0

**Date** : 2025-10-10
**Commits à déployer** :
- `40ee8dc` - feat(P1.2): persistence préférences dans ChromaDB
- `0c95f9f` - feat(P0): consolidation threads archivés dans LTM

**Durée estimée** : 15-20 minutes

---

## 🎯 Objectif

Déployer les Phases P1 (persistance préférences) et P0 (consolidation threads archivés) en production via Google Cloud Run.

**Tâches** :
1. Build nouvelle image Docker backend
2. Push image vers Google Container Registry (GCR)
3. Deploy nouvelle revision Cloud Run
4. Valider déploiement + logs

---

## 📋 Contexte Déploiement

### Changements Phase P1+P0

**Phase P1.2** (commit `40ee8dc`) :
- Persistance préférences utilisateur dans ChromaDB
- Nouvelle méthode `_save_preferences_to_vector_db()` (analyzer.py)
- 10 nouveaux tests (38/38 passed)

**Phase P0** (commit `0c95f9f`) :
- Consolidation automatique threads archivés
- Endpoint `POST /api/memory/consolidate-archived`
- Hook archivage → consolidation async
- 10 nouveaux tests (48/48 passed, 0 régression)

### Tests Validés Localement
```bash
# Tests mémoire complets
pytest tests/backend/features/test_memory*.py -v
# Résultat: 48/48 passed ✅
```

---

## 🛠️ Commandes Déploiement

### Étape 1 : Build Image Docker Backend

**Localisation** : Racine projet `c:\dev\emergenceV8\`

**Dockerfile** : `Dockerfile` (backend Python/FastAPI)

**Commande** :
```bash
# Build image avec tag version
docker build -t emergencev8-backend:p1-p0-latest -f Dockerfile .

# Tag pour GCR (remplacer PROJECT_ID par l'ID projet GCP)
docker tag emergencev8-backend:p1-p0-latest \
  gcr.io/PROJECT_ID/emergencev8-backend:p1-p0-latest

# Vérifier image créée
docker images | grep emergencev8-backend
```

**Notes** :
- Remplacer `PROJECT_ID` par l'ID projet Google Cloud (ex: `emergence-prod-123456`)
- Tag `p1-p0-latest` indique version avec P1+P0 déployées
- Vérifier que Dockerfile pointe vers `/src/backend` comme workdir

---

### Étape 2 : Push Image vers GCR

**Prérequis** :
- `gcloud` CLI configuré et authentifié
- Permissions push vers GCR pour le projet

**Commandes** :
```bash
# Authentification Docker avec GCR (si nécessaire)
gcloud auth configure-docker

# Push image vers Google Container Registry
docker push gcr.io/PROJECT_ID/emergencev8-backend:p1-p0-latest

# Vérifier image dans GCR
gcloud container images list --repository=gcr.io/PROJECT_ID
gcloud container images describe gcr.io/PROJECT_ID/emergencev8-backend:p1-p0-latest
```

**Validation** :
- Image visible dans [GCP Console > Container Registry](https://console.cloud.google.com/gcr/images/)
- Tag `p1-p0-latest` présent
- Taille image ~500MB-1GB (Python + dépendances)

---

### Étape 3 : Deploy Nouvelle Revision Cloud Run

**Service Cloud Run** : `emergencev8-backend` (nom à confirmer)

**Région** : `us-central1` (ou région configurée)

**Commande déploiement** :
```bash
gcloud run deploy emergencev8-backend \
  --image gcr.io/PROJECT_ID/emergencev8-backend:p1-p0-latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300s \
  --max-instances 10 \
  --min-instances 1 \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "EMERGENCE_KNOWLEDGE_COLLECTION=emergence_knowledge" \
  --revision-suffix p1-p0-$(date +%Y%m%d-%H%M)
```

**Paramètres clés** :
- `--image` : Image GCR avec tag P1+P0
- `--memory 2Gi` : RAM nécessaire pour ChromaDB + FastAPI
- `--cpu 2` : 2 vCPUs pour consolidation async
- `--timeout 300s` : Timeout 5 min (consolidation batch peut être longue)
- `--max-instances 10` : Autoscaling jusqu'à 10 instances
- `--min-instances 1` : 1 instance toujours active (latence réduite)
- `--revision-suffix` : Nom revision avec timestamp (ex: `p1-p0-20251010-0200`)

**Variables d'environnement à vérifier** :
```bash
# Lister variables env actuelles
gcloud run services describe emergencev8-backend --region us-central1 --format="value(spec.template.spec.containers[0].env)"

# Ajouter/modifier si nécessaire
--set-env-vars "CHROMA_HOST=..." \
--set-env-vars "CHROMA_PORT=8000" \
--set-env-vars "DATABASE_URL=..." \
--set-env-vars "ANTHROPIC_API_KEY=..."
```

**Output attendu** :
```
Deploying container to Cloud Run service [emergencev8-backend] in project [PROJECT_ID] region [us-central1]
✓ Deploying new service... Done.
  ✓ Creating Revision... Revision deployment finished. Waiting for health check to begin.
  ✓ Routing traffic...
  ✓ Setting IAM Policy...
Done.
Service [emergencev8-backend] revision [emergencev8-backend-p1-p0-20251010-0200] has been deployed and is serving 100 percent of traffic.
Service URL: https://emergencev8-backend-xxxxx-uc.a.run.app
```

---

### Étape 4 : Validation Déploiement

#### 4.1 Vérifier Service Déployé

```bash
# Lister services Cloud Run
gcloud run services list --region us-central1

# Décrire service
gcloud run services describe emergencev8-backend --region us-central1

# Vérifier revision active
gcloud run revisions list --service emergencev8-backend --region us-central1 --limit 5
```

**Attendu** :
- Service `emergencev8-backend` ACTIVE
- Revision `p1-p0-YYYYMMDD-HHMM` en traffic 100%
- Status READY

---

#### 4.2 Tester Endpoints API

**Service URL** : Récupérer depuis output deploy ou :
```bash
gcloud run services describe emergencev8-backend --region us-central1 --format="value(status.url)"
```

**Tests santé** :
```bash
# Health check
curl https://emergencev8-backend-xxxxx-uc.a.run.app/health

# Attendu: {"status": "ok"}
```

**Tests endpoints P0** :
```bash
# Endpoint consolidation archivés (nouveau P0)
curl -X POST https://emergencev8-backend-xxxxx-uc.a.run.app/api/memory/consolidate-archived \
  -H "Content-Type: application/json" \
  -H "x-dev-bypass: 1" \
  -H "x-user-id: test_user_prod" \
  -d '{"limit": 5, "force": false}'

# Attendu: {"status": "success", "consolidated_count": ..., "skipped_count": ..., ...}
```

**Tests endpoints P1** :
```bash
# Tend garden (extraction + persistance préférences)
curl -X POST https://emergencev8-backend-xxxxx-uc.a.run.app/api/memory/tend-garden \
  -H "Content-Type: application/json" \
  -H "x-dev-bypass: 1" \
  -H "x-user-id: test_user_prod" \
  -d '{}'

# Attendu: {"status": "success", "consolidated_sessions": ..., "new_concepts": ...}
```

---

#### 4.3 Vérifier Logs Production

```bash
# Logs temps réel (dernières 50 lignes)
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 50 \
  --format "table(timestamp, severity, textPayload)"

# Filtrer logs Phase P0 (hook archivage)
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 100 | grep "Thread Archiving"

# Filtrer logs Phase P0 (task queue)
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 100 | grep "MemoryTaskQueue"

# Filtrer logs Phase P1 (persistance préférences)
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 100 | grep "save_preferences_to_vector_db"
```

**Logs attendus** :
```
[INFO] [Thread Archiving] Consolidation enqueued for thread abc123
[INFO] [MemoryTaskQueue] Consolidating archived thread abc123 (reason: archiving)
[INFO] [MemoryTaskQueue] Thread abc123 consolidated: 5 new concepts
[INFO] [analyzer] Saved 3 preferences to vector DB (user: user_123)
```

---

#### 4.4 Vérifier Métriques Cloud Run

**Console GCP** : [Cloud Run > emergencev8-backend > Metrics](https://console.cloud.google.com/run/detail/us-central1/emergencev8-backend/metrics)

**Métriques à surveiller** :
1. **Request count** : Augmentation requêtes POST `/api/memory/consolidate-archived`
2. **Request latency** : Archivage threads < 200ms (hook async non-bloquant)
3. **Container instance count** : Autoscaling fonctionne (1-10 instances)
4. **Memory utilization** : < 80% des 2Gi alloués
5. **CPU utilization** : < 70% (pics lors consolidation batch)
6. **Error rate** : < 1% (vérifier erreurs 500)

**Commande CLI** :
```bash
# Métriques requêtes (dernières 1h)
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count" AND resource.labels.service_name="emergencev8-backend"' \
  --format=json
```

---

## 🧪 Tests Post-Déploiement

### Test 1 : Archivage Thread → Consolidation Auto (P0)

**Scénario** : Archiver un thread doit déclencher consolidation async.

```bash
# 1. Créer thread
THREAD_ID=$(curl -X POST https://emergencev8-backend-xxxxx-uc.a.run.app/api/threads/ \
  -H "Content-Type: application/json" \
  -H "x-dev-bypass: 1" \
  -H "x-user-id: test_user_prod" \
  -H "x-session-id: session_test_123" \
  -d '{"type": "chat", "title": "Test P0 Archivage"}' \
  | jq -r '.id')

# 2. Ajouter message au thread
curl -X POST https://emergencev8-backend-xxxxx-uc.a.run.app/api/threads/$THREAD_ID/messages \
  -H "Content-Type: application/json" \
  -H "x-dev-bypass: 1" \
  -H "x-user-id: test_user_prod" \
  -H "x-session-id: session_test_123" \
  -d '{"role": "user", "content": "Je préfère utiliser Docker pour le déploiement"}'

# 3. Archiver thread (devrait déclencher consolidation)
curl -X PATCH https://emergencev8-backend-xxxxx-uc.a.run.app/api/threads/$THREAD_ID \
  -H "Content-Type: application/json" \
  -H "x-dev-bypass: 1" \
  -H "x-user-id: test_user_prod" \
  -H "x-session-id: session_test_123" \
  -d '{"archived": true}'

# 4. Vérifier logs (attendre 5-10s pour consolidation async)
sleep 10
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 20 | grep -E "(Thread Archiving|MemoryTaskQueue)"
```

**Résultat attendu** :
```
[INFO] [Thread Archiving] Consolidation enqueued for thread [THREAD_ID]
[INFO] [MemoryTaskQueue] Consolidating archived thread [THREAD_ID] (reason: archiving)
[INFO] [MemoryTaskQueue] Thread [THREAD_ID] consolidated: X new concepts
```

---

### Test 2 : Batch Consolidation Threads Archivés (P0)

**Scénario** : Consolider tous threads archivés existants.

```bash
# Endpoint batch consolidation
curl -X POST https://emergencev8-backend-xxxxx-uc.a.run.app/api/memory/consolidate-archived \
  -H "Content-Type: application/json" \
  -H "x-dev-bypass: 1" \
  -H "x-user-id: test_user_prod" \
  -d '{"limit": 100, "force": false}' \
  | jq '.'
```

**Résultat attendu** :
```json
{
  "status": "success",
  "consolidated_count": 12,
  "skipped_count": 3,
  "total_archived": 15,
  "errors": []
}
```

**Vérifier logs** :
```bash
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 50 | grep "consolidate_archived"
```

---

### Test 3 : Persistance Préférences (P1)

**Scénario** : Préférences extraites sont sauvegardées dans ChromaDB.

```bash
# Tend garden avec historique contenant préférences
curl -X POST https://emergencev8-backend-xxxxx-uc.a.run.app/api/memory/tend-garden \
  -H "Content-Type: application/json" \
  -H "x-dev-bypass: 1" \
  -H "x-user-id: test_user_prod" \
  -H "x-session-id: session_test_456" \
  -d '{}'
```

**Vérifier logs** :
```bash
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 30 | grep "save_preferences_to_vector_db"
```

**Résultat attendu** :
```
[INFO] [analyzer] Saved 2 preferences to vector DB (user: test_user_prod, thread: ...)
```

---

## 📊 Validation Finale

### Checklist Déploiement

- [ ] Image Docker buildée avec tag `p1-p0-latest`
- [ ] Image pushée vers GCR
- [ ] Nouvelle revision Cloud Run déployée
- [ ] Revision active reçoit 100% du traffic
- [ ] Service URL accessible
- [ ] Health check `/health` retourne 200 OK
- [ ] Endpoint `/api/memory/consolidate-archived` accessible
- [ ] Logs montrent `[Thread Archiving]` et `[MemoryTaskQueue]`
- [ ] Logs montrent `save_preferences_to_vector_db`
- [ ] Métriques Cloud Run normales (latence, erreurs)
- [ ] Tests post-déploiement réussis

### Métriques Succès (24h post-deploy)

**Phase P0** :
- [ ] Threads archivés consolidés > 0
- [ ] Latence archivage < 200ms (P50)
- [ ] Queue processing time < 5s/thread (P95)
- [ ] Taux erreur consolidation < 1%

**Phase P1** :
- [ ] Préférences sauvegardées > 0
- [ ] Préférences récupérées dans contexte RAG
- [ ] Déduplication fonctionne (même user + text → 1 doc)

---

## 🚨 Rollback Plan

### Si problème critique détecté

**Rollback vers revision précédente** :
```bash
# Lister revisions
gcloud run revisions list --service emergencev8-backend --region us-central1 --limit 5

# Rollback vers revision N-1
gcloud run services update-traffic emergencev8-backend \
  --region us-central1 \
  --to-revisions REVISION_PRECEDENTE=100
```

**Vérifier rollback** :
```bash
gcloud run services describe emergencev8-backend --region us-central1 \
  --format="value(status.traffic)"
```

---

## 📞 Support & Monitoring

### Monitoring Continu

**Logs temps réel** :
```bash
gcloud run services logs tail emergencev8-backend --region us-central1
```

**Alertes Cloud Monitoring** :
- Error rate > 5% pendant 5 min → alerte email
- Latency P95 > 10s → alerte Slack
- Memory utilization > 90% → alerte critique

### Debugging

**Erreurs 500** :
```bash
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 100 \
  --filter="severity=ERROR"
```

**Performance lente** :
```bash
# Logs avec latence > 5s
gcloud run services logs read emergencev8-backend \
  --region us-central1 \
  --limit 100 \
  --filter="httpRequest.latency>5s"
```

---

## ✅ Prochaines Actions

### Après Déploiement Réussi

1. **Migration batch threads archivés** (1 fois) :
   ```bash
   curl -X POST https://emergencev8-backend-xxxxx-uc.a.run.app/api/memory/consolidate-archived \
     -H "x-dev-bypass: 1" \
     -H "x-user-id: ALL_USERS" \
     -d '{"limit": 1000, "force": false}'
   ```

2. **Monitoring 24h** : Vérifier métriques, logs, erreurs

3. **Validation utilisateurs** : Tester "se souvenir conversations archivées"

4. **Documentation mise à jour** :
   - Ajouter URL service production dans README
   - Documenter endpoints P0/P1 dans API docs

5. **Phase P2** (si décidé) : Harmonisation Session/Thread

---

**Fin du prompt déploiement P1+P0** 🚀
