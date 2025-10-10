# Déploiement Production — Phase P2 Sprint 3

**Date** : 2025-10-10 07:37 CEST  
**Agent** : Codex  
**Type** : Build & release Docker (Phase P2 Sprint 3 + correctif concept recall)  
**Révision déployée** : `emergence-app-00348-rih`  
**Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:p2-sprint3`  
**Digest Cloud Run** : `sha256:d15ae3f77822b662ee02f9903aeb7254700dbc37c5e802cf46443541edaf4340`

---

## 🎯 Objectif

Construire une image Docker à jour de la Phase **P2 Sprint 3** (Proactive Hints + Memory Dashboard), corriger le seuil de détection du Concept Recall (`SIMILARITY_THRESHOLD = 0.75`) et déployer une nouvelle révision Cloud Run après validation tests + métriques.

---

## ✅ Préparation & Tests locaux

```powershell
# Backend
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m pytest tests/backend/features/test_concept_recall_tracker.py
.\.venv\Scripts\python -m mypy src

# Frontend
npm run build

# Linter (échec connu – scripts QA legacy)
.\.venv\Scripts\python -m ruff check
# -> F401/F541 dans scripts/qa et tests existants (pas dans le scope de cette session)
```

---

## 🧱 Build & Publication Docker

```powershell
# 1. Build linux/amd64
docker build --platform linux/amd64 `
  -t emergence-app:p2-sprint3 `
  -f Dockerfile .

# 2. Tags locaux
docker tag emergence-app:p2-sprint3 emergence-app:50b4f34

# 3. Tags Artifact Registry
docker tag emergence-app:p2-sprint3 `
  europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:p2-sprint3
docker tag emergence-app:p2-sprint3 `
  europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:latest

# 4. Push registry
gcloud auth configure-docker europe-west1-docker.pkg.dev
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:p2-sprint3
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:latest
```

---

## 🚀 Déploiement Cloud Run

```powershell
# 5. Déployer la révision taggée p2-sprint3
gcloud run deploy emergence-app `
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:p2-sprint3 `
  --project emergence-469005 `
  --region europe-west1 `
  --platform managed `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300 `
  --max-instances 10 `
  --min-instances 1 `
  --concurrency 40 `
  --set-env-vars 'CONCEPT_RECALL_METRICS_ENABLED=true,PYTHONPATH=/app/src,GOOGLE_ALLOWED_EMAILS=gonzalefernando@gmail.com,AUTH_DEV_MODE=0' `
  --set-secrets 'OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5' `
  --tag p2-sprint3

# 6. Basculer le trafic
gcloud run services update-traffic emergence-app `
  --region europe-west1 `
  --to-tags p2-sprint3=100
```

Résultat :

- ✅ Révision active : `emergence-app-00348-rih` (tag `p2-sprint3`)
- ✅ Alias `canary` conservé sur `emergence-app-00279-kub` (0 %)
- ✅ URL service : https://emergence-app-47nct44nma-ew.a.run.app

---

## 🔍 Vérifications post-déploiement

- `curl https://emergence-app-47nct44nma-ew.a.run.app/api/health`
- `Invoke-RestMethod https://emergence-app-47nct44nma-ew.a.run.app/api/memory/user/stats -Headers "Authorization: Bearer <token admin>"`
- `curl https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep concept_recall_system_info`
- `curl -I https://emergence-app-47nct44nma-ew.a.run.app/`
- `gcloud run services logs read emergence-app --region europe-west1 --limit 50`
- `gcloud run revisions list --service emergence-app --region europe-west1`

Extraits clés :

```json
GET /api/memory/user/stats
{
  "preferences": {"total": 0, "top": [], "by_type": {"preference": 0, "intent": 0, "constraint": 0}},
  "concepts": {"total": 0, "top": []},
  "stats": {"sessions_analyzed": 27, "threads_archived": 3, "ltm_size_mb": 0.0}
}
```

```text
concept_recall_system_info{collection_name="emergence_knowledge",max_recalls_per_message="3",similarity_threshold="0.75",version="1.0"} 1.0
```

Logs Cloud Run : uniquement les requêtes de validation (200 OK) + un 401 attendu avant login (token manquant).

---

## ⚙️ Correctifs inclus

- `src/backend/features/memory/concept_recall.py`  
  → `SIMILARITY_THRESHOLD` relevé à **0.75** (évite les faux positifs signalés par `test_similarity_threshold_filtering`).

- `src/backend/features/memory/concept_recall_metrics.py`  
  → Alignement des métadonnées Prometheus (`similarity_threshold=0.75`, nouveaux buckets 0.5/0.75/0.8/0.9/1.0).

- Documentation synchronisée :
  - `docs/features/concept-recall-metrics-implementation.md`
  - `docs/deployments/2025-10-09-activation-metrics-phase3.md`
  - `docs/deployments/2025-10-09-validation-phase3-complete.md`

---

## 🔭 Actions de suivi

1. **Ruff** : nettoyer les imports/scripts QA (`scripts/qa/*.py`, `tests/backend/features/test_memory_performance.py`) pour rétablir un `ruff check` propre.
2. **Monitoring** : surveiller Prometheus (`concept_recall_similarity_score` + `concept_recall_system_info`) pour confirmer la baisse des faux positifs sous seuil 0.75.
3. **QA mémoire** : relancer `scripts/qa/trigger_preferences_extraction.py` (credentials disponibles dans `scripts/qa/.env.qa`) pour enrichir les métriques `memory_preferences_*`.
4. **Canary** : laisser `emergence-app-00279-kub` disponible via tag `canary` jusqu’à validation FG, planifier rollback rapide si anomalies identifiées.

---

## 📚 Références

- [PROMPT_DOCKER_BUILD_DEPLOY.md](../../PROMPT_DOCKER_BUILD_DEPLOY.md)
- [docs/features/concept-recall-metrics-implementation.md](../features/concept-recall-metrics-implementation.md)
- [docs/architecture/CONCEPT_RECALL.md](../architecture/CONCEPT_RECALL.md)
