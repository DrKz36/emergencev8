# 🎯 PROMPT CODEX : ACTIVER MÉTRIQUES PROMETHEUS

**Date** : 2025-10-09
**Objectif** : Déployer Cloud Run avec `CONCEPT_RECALL_METRICS_ENABLED=true`
**Contexte** : Phase 2 validée ✅, Phase 3 code présent mais métriques désactivées

---

## 📋 PROBLÈME RENCONTRÉ

### Tentatives échouées (Claude)
1. ❌ `gcloud run services update --set-env-vars` → Rebuild échoué (`ModuleNotFoundError: backend`)
2. ❌ `gcloud run deploy --source` avec timeout invalide → Build réussi mais déploiement échoué
3. ❌ `gcloud run deploy --image` réutilise anciennes révisions cassées

### Cause racine
- Cloud Run **cache/réutilise** les révisions avec même configuration
- Changement variable d'env déclenche rebuild qui échoue si code manquant
- Révisions cassées bloquent nouveaux déploiements

---

## ✅ SOLUTION PROPRE ET SOLIDE

### Fichier `env.yaml` créé
```yaml
# env.yaml (racine projet)
CONCEPT_RECALL_METRICS_ENABLED: "true"
PYTHONPATH: "/app/src"
GOOGLE_ALLOWED_EMAILS: "gonzalefernando@gmail.com"
AUTH_DEV_MODE: "0"
```

### Commande de déploiement
```bash
gcloud run deploy emergence-app \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi \
  --max-instances 10 \
  --min-instances 0
```

**Important** :
- `--timeout 600` (secondes, max 3600) pour container startup
- `--source .` force un build complet from scratch (15-20 min)
- `--env-vars-file` charge toutes variables depuis fichier
- `--update-secrets` préserve les secrets API

---

## 📦 ÉTAPES DÉTAILLÉES

### 1. Pré-vérifications

```bash
# Vérifier fichier env.yaml existe
cat env.yaml

# Vérifier Dockerfile valide
cat Dockerfile | grep "CMD"
# Doit contenir : python -m uvicorn --app-dir src backend.main:app

# Vérifier .gcloudignore n'exclut pas src/
cat .gcloudignore | grep -E "^src/"
# Ne doit PAS matcher (src/ doit être inclus)

# Vérifier requirements.txt contient prometheus-client
grep prometheus-client requirements.txt
```

### 2. Build & Deploy (15-20 min)

```bash
# Variables projet
export PROJECT_ID="emergence-469005"
export REGION="europe-west1"
export SERVICE_NAME="emergence-app"

# Lancer déploiement
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi \
  --max-instances 10 \
  --min-instances 0
```

**Output attendu** :
```
Building using Dockerfile...
Uploading sources... done
Building Container... (10-15 min)
Setting IAM Policy... done
Creating Revision... done
Service [emergence-app] revision [emergence-app-00XXX-xxx] deployed
Service URL: https://emergence-app-486095406755.europe-west1.run.app
```

### 3. Vérifier déploiement

```bash
# Récupérer URL service
export SERVICE_URL="https://emergence-app-486095406755.europe-west1.run.app"

# Vérifier health
curl $SERVICE_URL/api/health

# ✅ Vérifier métriques ACTIVÉES
curl $SERVICE_URL/api/metrics | head -20

# AVANT (désactivé) :
# # Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.

# APRÈS (activé) :
# # HELP memory_analysis_duration_seconds Time spent analyzing session memory
# # TYPE memory_analysis_duration_seconds histogram
# memory_analysis_duration_seconds_bucket{le="0.5",provider="neo_analysis"} 0.0
# ...
```

### 4. Valider révision déployée

```bash
# Lister révisions
gcloud run revisions list \
  --service $SERVICE_NAME \
  --region $REGION \
  --limit 3

# Vérifier variable dans révision active
gcloud run revisions describe $(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.latestReadyRevisionName)") \
  --region $REGION \
  --format="value(spec.containers[0].env)" | grep CONCEPT_RECALL

# Doit afficher :
# {'name': 'CONCEPT_RECALL_METRICS_ENABLED', 'value': 'true'}
```

---

## 🧪 TESTS VALIDATION PHASE 3

### Test 1 : Métriques Prometheus exposées

```bash
# Récupérer toutes les métriques
curl -s $SERVICE_URL/api/metrics > metrics.txt

# Vérifier 13 métriques attendues
grep -E "^# TYPE" metrics.txt

# Métriques attendues :
# - memory_analysis_duration_seconds (histogram)
# - memory_analysis_success_total (counter)
# - memory_analysis_failures_total (counter)
# - memory_analysis_cache_hits_total (counter)
# - memory_analysis_cache_misses_total (counter)
# - memory_analysis_cache_size (gauge)
# - memory_analysis_messages_processed_total (counter)
# - memory_analysis_concepts_extracted_total (counter)
# - memory_analysis_entities_extracted_total (counter)
```

### Test 2 : Analyse mémoire + métriques

```bash
# Trouver session avec messages
# (depuis logs validation Phase 2)
export TEST_SESSION="aa327d90-3547-4396-a409-f565182db61a"

# 1er appel : Analyse complète
curl -X POST $SERVICE_URL/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$TEST_SESSION\",\"force\":true}" \
  -w "\nTime: %{time_total}s\n"

# Attendre 2s pour métriques

# Vérifier métriques mises à jour
curl -s $SERVICE_URL/api/metrics | grep -E "(success_total|cache_misses)"

# Attendu :
# memory_analysis_success_total{provider="neo_analysis"} 1.0
# memory_analysis_cache_misses_total 1.0
```

### Test 3 : Cache hit + métriques

```bash
# 2e appel : Cache hit
curl -X POST $SERVICE_URL/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$TEST_SESSION\"}" \
  -w "\nTime: %{time_total}s\n"

# Temps attendu : <0.3s (vs 6s 1er appel)

# Vérifier métriques cache
curl -s $SERVICE_URL/api/metrics | grep cache_hits

# Attendu :
# memory_analysis_cache_hits_total 1.0
```

### Test 4 : Logs Cloud Run

```bash
# Vérifier logs métriques
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND textPayload=~\"metrics\"" \
  --limit 10 \
  --freshness 5m \
  --format "value(textPayload)"

# Logs attendus :
# [Metrics] Prometheus endpoint exposed at /api/metrics
# [Metrics] 13 metrics registered
```

---

## 📊 CRITÈRES DE SUCCÈS

### Phase 3 validée si :
- ✅ Endpoint `/api/metrics` retourne métriques Prometheus (pas message disabled)
- ✅ Au moins 10/13 métriques visibles
- ✅ Compteurs `success_total` incrémente après analyse
- ✅ Compteurs `cache_hits_total` incrémente après 2e appel
- ✅ Aucune erreur 500 dans logs
- ✅ Service stable et accessible

---

## 🚨 TROUBLESHOOTING

### Problème 1 : Build échoue "ModuleNotFoundError: backend"

**Cause** : `src/` non copié dans image Docker

**Solution** :
```bash
# Vérifier .gcloudignore n'exclut pas src/
cat .gcloudignore | grep "^src/"

# Doit être vide ou commenté
# Si présent, commenter et rebuild
```

### Problème 2 : Révision cassée bloque deploy

**Symptôme** :
```
ERROR: Revision 'emergence-app-00277-mzh' is not ready and cannot serve traffic
```

**Solution** :
```bash
# 1. Rollback vers dernière révision stable
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions emergence-app-00275-2jb=100 \
  --region $REGION

# 2. Supprimer révision cassée (après rollback)
gcloud run revisions delete emergence-app-00277-mzh \
  --region $REGION \
  --quiet

# 3. Relancer deploy avec --revision-suffix
gcloud run deploy ... --revision-suffix="metrics-v2"
```

### Problème 3 : Métriques toujours disabled

**Cause** : Variable d'env pas chargée au démarrage container

**Vérification** :
```bash
# Vérifier variable dans révision
gcloud run revisions describe [REVISION_NAME] \
  --region $REGION \
  --format="value(spec.containers[0].env)"

# Doit contenir :
# {'name': 'CONCEPT_RECALL_METRICS_ENABLED', 'value': 'true'}
```

**Solution** :
```bash
# Si variable absente, redeployer avec env.yaml explicite
gcloud run deploy ... --env-vars-file env.yaml
```

### Problème 4 : Build trop long (>20 min)

**Cause** : Téléchargement modèle `all-MiniLM-L6-v2` (100MB+)

**Normal** : 1er build 15-20 min, builds suivants 5-10 min (cache Docker layers)

**Vérifier progression** :
```bash
# Logs build en cours
gcloud builds list --ongoing --format json

# Si vide après 25 min, annuler et relancer
# (CTRL+C puis recommencer)
```

---

## 📝 DOCUMENTATION POST-DÉPLOIEMENT

### Créer rapport validation Phase 3

**Fichier** : `docs/deployments/2025-10-09-validation-phase3.md`

**Template** :
```markdown
# Validation Phase 3 : Métriques Prometheus

**Date** : 2025-10-09
**Révision** : emergence-app-00XXX-xxx
**Statut** : ✅ SUCCÈS

## Tests
- ✅ Métriques exposées : 13/13
- ✅ Analyse neo_analysis : 6.2s
- ✅ Cache hit : 0.2s
- ✅ Compteurs incrémentés correctement

## Métriques initiales
- `memory_analysis_success_total` : 2.0
- `memory_analysis_cache_hits_total` : 1.0
- `memory_analysis_cache_misses_total` : 1.0

## Configuration
- Variable : `CONCEPT_RECALL_METRICS_ENABLED=true`
- CPU : 2 vCPU
- Memory : 4Gi
- Timeout : 600s
```

### Commit
```bash
git add docs/deployments/2025-10-09-validation-phase3.md env.yaml
git commit -m "docs: validation Phase 3 Prometheus metrics enabled

✅ Métriques Prometheus activées en production
✅ 13 métriques exposées sur /api/metrics
✅ Tests cache + analyses validés

Config: env.yaml avec CONCEPT_RECALL_METRICS_ENABLED=true

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

---

## 🎯 OBJECTIF FINAL

À la fin, tu dois avoir :

1. ✅ **Service Cloud Run déployé** avec nouvelle révision
2. ✅ **Métriques activées** : `/api/metrics` retourne données Prometheus
3. ✅ **Tests validés** : analyses + cache fonctionnent + métriques incrémentent
4. ✅ **Documentation** : Rapport Phase 3 commité
5. ✅ **Phase 2 & 3 complètes** en production

---

## 📚 RÉFÉRENCES

- [Validation Phase 2](docs/deployments/2025-10-08-validation-phase2.md) ✅
- [Phase 3 Spec](docs/deployments/2025-10-08-phase3-monitoring.md)
- [CODEX Build/Deploy](CODEX_BUILD_DEPLOY_PROMPT.md)
- [Récap Phases](docs/deployments/PHASES_RECAP.md)

---

**Bon déploiement Codex ! 🚀**

*Généré par Claude Code - 2025-10-09*
