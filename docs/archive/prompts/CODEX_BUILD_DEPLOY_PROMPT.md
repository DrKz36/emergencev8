# 🚀 PROMPT CODEX : BUILD & DEPLOY PHASE 3

**Date** : 2025-10-08
**Version cible** : V3.6 (analyzer) + Prometheus monitoring
**Contexte** : Phases 2 & 3 complétées, prêtes pour déploiement production

---

## 📋 CONTEXTE

Bonjour Codex,

Les **Phases 2 (Performance)** et **Phase 3 (Monitoring)** d'ÉMERGENCE V8 sont **terminées et commitées** sur `main`.

### Changements principaux
1. ✅ **Agent neo_analysis** (GPT-4o-mini) pour analyses rapides
2. ✅ **Cache in-memory** avec TTL 1h (max 100 entrées)
3. ✅ **Fix OpenAI prompt** (ajout mot "json" requis)
4. ✅ **Débats parallélisés** (round 1)
5. ✅ **Métriques Prometheus** (13 métriques exposées)

### Commits récents
```
dcffd45 docs: récapitulatif complet Phases 2 & 3 - guide déploiement
11ac853 feat(phase3): add Prometheus metrics for MemoryAnalyzer monitoring
611f06e fix: prompt OpenAI neo_analysis - ajout mot 'json' requis par API
```

---

## 🎯 MISSION

**Objectif** : Builder une nouvelle image Docker et déployer sur Cloud Run avec les optimisations Phase 2 & 3.

---

## 📦 ÉTAPE 1 : BUILD DOCKER

### 1.1 Incrémenter BUILD_ID

```bash
# Lire BUILD_ID actuel
export CURRENT_BUILD=$(cat build_tag.txt)
echo "Build actuel : $CURRENT_BUILD"

# Calculer nouveau BUILD_ID
export NEW_BUILD=$((CURRENT_BUILD + 1))
echo "Nouveau build : $NEW_BUILD"

# Sauvegarder
echo $NEW_BUILD > build_tag.txt
git add build_tag.txt
git commit -m "build: increment BUILD_ID to $NEW_BUILD (Phase 3)"
git push
```

### 1.2 Build Image Docker

**Important** : Utiliser le PROJECT_ID et REGION corrects.

```bash
# Variables d'environnement (à adapter)
export PROJECT_ID="ton-project-id-gcp"
export REGION="us-central1"  # ou ta région
export SERVICE_NAME="emergence-app"
export IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME:$NEW_BUILD"

# Build l'image
docker build -t $IMAGE_NAME .

# Push vers Google Container Registry
docker push $IMAGE_NAME
```

### 1.3 Vérifier l'image

```bash
# Lister les images
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Vérifier la nouvelle image
gcloud container images describe $IMAGE_NAME
```

---

## 🚀 ÉTAPE 2 : DEPLOY CLOUD RUN

### 2.1 Deploy la nouvelle image

```bash
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars "EMERGENCE_ENV=production"
```

### 2.2 Récupérer l'URL du service

```bash
export SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)')

echo "Service URL : $SERVICE_URL"
```

### 2.3 Vérifier le déploiement

```bash
# Test health endpoint
curl $SERVICE_URL/api/health

# Devrait retourner :
# {"status":"ok","message":"Emergence Backend is running."}
```

---

## ✅ ÉTAPE 3 : VALIDATION PHASE 2 & 3

### 3.1 Tester neo_analysis (Phase 2)

**Important** : Utiliser une vraie session avec messages.

```bash
# Récupérer une session existante (depuis logs ou BDD)
export TEST_SESSION="aa327d90-3547-4396-a409-f565182db61a"  # Exemple

# Déclencher analyse (force=true pour recalculer)
curl -X POST $SERVICE_URL/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$TEST_SESSION\",\"force\":true}"
```

**Résultat attendu** :
```json
{
  "status": "completed",
  "session_id": "...",
  "analysis": {
    "summary": "...",
    "concepts": [...],
    "entities": [...]
  }
}
```

### 3.2 Vérifier métriques Prometheus (Phase 3)

```bash
# Récupérer toutes les métriques
curl $SERVICE_URL/api/metrics | grep memory_analysis

# Métriques attendues :
# memory_analysis_success_total{provider="neo_analysis"} 1.0
# memory_analysis_cache_misses_total 1.0
# memory_analysis_duration_seconds_bucket{provider="neo_analysis",le="2.0"} 1.0
# ...
```

### 3.3 Tester cache HIT (Phase 2)

```bash
# 2e appel SANS force (devrait utiliser cache BDD)
curl -X POST $SERVICE_URL/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$TEST_SESSION\"}"
```

**Résultat attendu** :
```json
{
  "status": "skipped",
  "reason": "already_analyzed",
  "metadata": { ... }
}
```
Temps de réponse : **<100ms** (vs 4-17s sans cache)

### 3.4 Vérifier logs Cloud Run

```bash
# Afficher logs en temps réel
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
  --limit 50 \
  --format json \
  --freshness 10m

# Rechercher logs MemoryAnalyzer
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND textPayload=~\"MemoryAnalyzer\"" \
  --limit 20 \
  --format "value(textPayload)"
```

**Logs attendus** :
```
[MemoryAnalyzer] Analyse réussie avec neo_analysis pour session ...
[MemoryAnalyzer] Cache SAVED pour session ...
```

---

## 📊 ÉTAPE 4 : CONFIGURER PROMETHEUS (OPTIONNEL)

### 4.1 Créer fichier prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'emergence_production'
    scrape_interval: 15s
    static_configs:
      - targets: ['emergence-app-xxxxx.run.app']  # TON URL
    metrics_path: '/api/metrics'
    scheme: https
```

### 4.2 Lancer Prometheus localement (test)

```bash
# Si Prometheus installé localement
prometheus --config.file=prometheus.yml

# Accéder : http://localhost:9090
# Query test : memory_analysis_success_total
```

### 4.3 Dashboards Grafana suggérés

Voir documentation complète : `docs/deployments/2025-10-08-phase3-monitoring.md`

**5 panels principaux** :
1. Success Rate (Gauge) → >95%
2. Latence P95 (Time Series) → <2s
3. Cache Hit Rate (Stat) → 40-50%
4. Distribution Erreurs (Pie)
5. Taille Cache (Gauge) → <100

---

## 📝 ÉTAPE 5 : DOCUMENTER LE DÉPLOIEMENT

### 5.1 Logger la révision Cloud Run

```bash
# Récupérer info révision
gcloud run revisions list \
  --service $SERVICE_NAME \
  --region $REGION \
  --limit 1

# Exemple output :
# REVISION: emergence-app-00275-abc
# ACTIVE: yes
```

### 5.2 Créer log de déploiement

Créer fichier `docs/deployments/2025-10-08-deploy-phase3.md` :

```markdown
# 🚀 Déploiement Phase 3 Production

**Date** : 2025-10-08
**Build ID** : [NOUVEAU_BUILD_ID]
**Revision** : [emergence-app-00XXX]
**Image** : gcr.io/[PROJECT]/emergence-app:[BUILD_ID]

## Changements
- Phase 2 : neo_analysis + cache + débats parallèles
- Phase 3 : Métriques Prometheus (13 métriques)

## Tests Validation
- ✅ Health check OK
- ✅ neo_analysis fonctionne
- ✅ Métriques exposées /api/metrics
- ✅ Cache BDD opérationnel

## Métriques Initiales
- Success rate : [X]%
- Latence P95 : [X]s
- Cache hit rate : [X]%

## Issues
- [Aucune] ou [Liste des problèmes]

## Rollback
Si besoin :
```bash
gcloud run services update-traffic emergence-app \
  --to-revisions emergence-app-00274=100 \
  --region us-central1
```
```

### 5.3 Commiter le log

```bash
git add docs/deployments/2025-10-08-deploy-phase3.md
git commit -m "docs: log déploiement Phase 3 production (build $NEW_BUILD)"
git push
```

---

## ⚠️ TROUBLESHOOTING

### Problème 1 : Build Docker échoue

```bash
# Vérifier Dockerfile
cat Dockerfile

# Vérifier requirements.txt contient prometheus-client
grep prometheus requirements.txt

# Build avec logs verbeux
docker build -t $IMAGE_NAME . --progress=plain
```

### Problème 2 : Deploy Cloud Run échoue

```bash
# Vérifier quotas
gcloud compute project-info describe --project=$PROJECT_ID

# Vérifier rôles IAM
gcloud projects get-iam-policy $PROJECT_ID

# Vérifier logs build
gcloud builds log [BUILD_ID]
```

### Problème 3 : Métriques Prometheus non visibles

```bash
# Vérifier endpoint directement
curl $SERVICE_URL/api/metrics

# Si vide, vérifier logs démarrage
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~\"prometheus\"" \
  --limit 10
```

### Problème 4 : neo_analysis échoue

```bash
# Vérifier clé OpenAI configurée
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format "value(spec.template.spec.containers[0].env)"

# Vérifier logs erreur
gcloud logging read "resource.type=cloud_run_revision AND textPayload=~\"neo_analysis.*échec\"" \
  --limit 10
```

---

## 📊 MÉTRIQUES DE SUCCÈS

### Phase 2 (Performance)
- [ ] neo_analysis succès : >95%
- [ ] Latence analyses : 1-4s (selon taille)
- [ ] Cache BDD : <100ms sur 2e appel
- [ ] Aucune régression de performance

### Phase 3 (Monitoring)
- [ ] Endpoint `/api/metrics` répond
- [ ] 13 métriques visibles
- [ ] Compteurs incrementent correctement
- [ ] Histogrammes avec buckets corrects

### Global
- [ ] Service accessible et stable
- [ ] Aucune erreur 500 dans logs
- [ ] Temps démarrage <60s
- [ ] Memory usage <2Gi

---

## 🎯 CHECKLIST FINALE

### Pré-déploiement
- [ ] Code Phase 2 & 3 sur `main`
- [ ] Tests locaux validés
- [ ] BUILD_ID incrémenté
- [ ] Variables d'environnement configurées

### Build & Push
- [ ] Image Docker buildée
- [ ] Image pushée vers GCR
- [ ] Image visible dans GCR

### Déploiement
- [ ] Cloud Run deploy réussi
- [ ] Service URL récupérée
- [ ] Health check OK

### Validation
- [ ] Analyse mémoire fonctionne
- [ ] Métriques Prometheus visibles
- [ ] Cache BDD opérationnel
- [ ] Aucune erreur dans logs

### Documentation
- [ ] Log déploiement créé
- [ ] Révision Cloud Run notée
- [ ] Métriques initiales enregistrées
- [ ] Commit documentation

---

## 📚 RESSOURCES

### Documentation
- **Phase 2 Spec** : `docs/deployments/2025-10-08-phase2-perf.md`
- **Phase 2 Logs** : `docs/deployments/2025-10-08-phase2-logs-analysis.md`
- **Phase 3 Monitoring** : `docs/deployments/2025-10-08-phase3-monitoring.md`
- **Récapitulatif** : `docs/deployments/PHASES_RECAP.md`

### Commandes utiles
```bash
# Rollback rapide si problème
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions [PREVIOUS_REVISION]=100 \
  --region $REGION

# Scaler à 0 (urgence)
gcloud run services update $SERVICE_NAME \
  --max-instances 0 \
  --region $REGION

# Logs temps réel
gcloud logging tail "resource.type=cloud_run_revision" \
  --filter "resource.labels.service_name=$SERVICE_NAME"
```

---

## ✅ OBJECTIF FINAL

À la fin de cette mission, tu devrais avoir :

1. ✅ Une **nouvelle image Docker** (build $NEW_BUILD) poussée sur GCR
2. ✅ Un **service Cloud Run** mis à jour avec Phase 2 & 3
3. ✅ **Tests validés** : neo_analysis + métriques Prometheus
4. ✅ **Documentation** du déploiement commitée
5. ✅ **Métriques initiales** enregistrées pour baseline

---

## 🆘 SUPPORT

Si tu rencontres un problème :
1. Consulte la section **Troubleshooting**
2. Vérifie les **logs Cloud Run**
3. Reviens avec le message d'erreur précis
4. En cas de doute : **ne déploie pas**, demande confirmation

---

**Bon déploiement Codex! 🚀**

*Ce prompt a été généré automatiquement par Claude Code*
*Date : 2025-10-08*
*Version : 1.0*
