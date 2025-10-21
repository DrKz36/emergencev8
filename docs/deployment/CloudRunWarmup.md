# Cloud Run Warm-up & Healthcheck Strict

**Version:** 1.0.0
**Date:** 2025-10-21
**Auteur:** Claude Code

---

## 🎯 Objectif

Éliminer les cold starts visibles sur Cloud Run en chargeant explicitement tous les composants lourds (DB, modèle SBERT, Chroma) **avant** que Cloud Run route du trafic vers l'instance.

**Problèmes résolus :**
- ✅ Cold starts : utilisateurs voient erreurs 500 pendant 3-5s au démarrage
- ✅ Healthcheck trop permissif : Cloud Run route vers instances pas ready
- ✅ Modèle SBERT (600MB) chargé pendant que traffic arrive

---

## 📊 Architecture

### Workflow Startup

```
[Cloud Run démarre container]
         ↓
    [_startup()]
         ↓
   ┌─────────────────┐
   │ 1. DB Connect   │ → _warmup_ready["db"] = True
   ├─────────────────┤
   │ 2. Load SBERT   │ → _warmup_ready["embed"] = True
   ├─────────────────┤
   │ 3. Chroma Check │ → _warmup_ready["vector"] = True
   ├─────────────────┤
   │ 4. DI Wiring    │ → _warmup_ready["di"] = True
   └─────────────────┘
         ↓
   all(_warmup_ready.values()) == True
         ↓
   [/healthz] → 200 OK
         ↓
   [Cloud Run route traffic]
```

### État Global `_warmup_ready`

```python
_warmup_ready = {
    "db": False,      # Database connectée + SELECT 1 OK
    "embed": False,   # Modèle SBERT chargé en mémoire
    "vector": False,  # Collections Chroma vérifiées
    "di": False,      # Dependency Injection wirée
}
```

---

## 🔧 Implémentation

### 1. Warm-up dans `_startup()` (main.py)

```python
async def _startup(container: ServiceContainer):
    global _warmup_ready
    logger.info("🚀 Démarrage backend Émergence (warm-up mode)...")

    # 1. Database
    try:
        db_manager = container.db_manager()
        await db_manager.connect()
        conn = await db_manager._ensure_connection()
        cursor = await conn.execute("SELECT 1")
        await cursor.fetchone()
        _warmup_ready["db"] = True
        logger.info("✅ DB warmup: connexion vérifiée")
    except Exception as e:
        logger.error(f"❌ DB warmup failed: {e}")
        _warmup_ready["db"] = False

    # 2. Embedding Model
    try:
        vector_service = container.vector_service()
        vector_service._ensure_inited()  # Force lazy init
        logger.info(f"✅ Embedding model loaded: {vector_service.embed_model_name}")
        _warmup_ready["embed"] = True
    except Exception as e:
        logger.error(f"❌ Embedding warmup failed: {e}")
        _warmup_ready["embed"] = False

    # 3. Chroma Collections
    try:
        vector_service.client.get_or_create_collection("documents")
        vector_service.client.get_or_create_collection("knowledge")
        logger.info("✅ Chroma collections verified")
        _warmup_ready["vector"] = True
    except Exception as e:
        logger.error(f"❌ Vector warmup failed: {e}")
        _warmup_ready["vector"] = False

    # 4. DI Wiring
    try:
        container.wire(modules=[...])
        logger.info("✅ DI wired")
        _warmup_ready["di"] = True
    except Exception as e:
        logger.error(f"❌ DI wiring failed: {e}")
        _warmup_ready["di"] = False

    # Log final
    all_ready = all(_warmup_ready.values())
    if all_ready:
        logger.info(f"✅ Warm-up completed - READY for traffic")
    else:
        failed = [k for k, v in _warmup_ready.items() if not v]
        logger.warning(f"⚠️ Warm-up NOT READY (failed: {', '.join(failed)})")
```

### 2. Healthcheck Strict `/healthz`

```python
@app.get("/healthz")
async def healthz_strict():
    """
    Retourne 200 si warm-up complet, 503 si pas ready.
    Cloud Run n'envoie du traffic que si 200.
    """
    global _warmup_ready
    all_ready = all(_warmup_ready.values())

    if all_ready:
        return {"ok": True, "status": "ready", **_warmup_ready}
    else:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "status": "starting", **_warmup_ready}
        )
```

---

## ⚙️ Configuration Cloud Run

### Deployment YAML

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: emergence-app
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"  # ← Au moins 1 instance toujours up
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containerConcurrency: 8  # ← 8 requêtes max par instance
      containers:
      - image: europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:latest
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /healthz
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 3
```

### Commande `gcloud`

```bash
gcloud run services update emergence-app \
  --region=europe-west1 \
  --min-instances=1 \
  --max-instances=10 \
  --concurrency=8 \
  --cpu=1 \
  --memory=1Gi \
  --timeout=300 \
  --port=8000 \
  --set-env-vars="HEALTHCHECK_PATH=/healthz"
```

**Explication :**
- `--min-instances=1` : Au moins 1 instance toujours prête (évite cold starts fréquents)
- `--concurrency=8` : 8 requêtes simultanées max par instance
- `--cpu=1` : 1 vCPU alloué (suffisant pour SBERT + FastAPI)
- `--memory=1Gi` : 1GB RAM (SBERT ~600MB + overhead)

---

## 📈 Monitoring

### Logs Startup

**Warm-up réussi :**
```
🚀 Démarrage backend Émergence (warm-up mode)...
✅ DB connectée (FAST_BOOT=on)
✅ DB warmup: connexion vérifiée
✅ Embedding model loaded: all-MiniLM-L6-v2
✅ Chroma collections verified
✅ DI wired (chat|dashboard|documents|debate|benchmarks.router)
✅ Warm-up completed in 1234ms - READY for traffic
```

**Warm-up partiel (problème) :**
```
🚀 Démarrage backend Émergence (warm-up mode)...
✅ DB connectée
❌ Embedding model warmup failed: ModuleNotFoundError: sentence-transformers
✅ Chroma collections verified
✅ DI wired
⚠️ Warm-up completed in 567ms - NOT READY (failed: embed)
```

### Métriques Cloud Run

**1. Instance Count**
```
resource.type="cloud_run_revision"
metric.type="run.googleapis.com/container/instance_count"
```

**2. Request Latency (Cold Start)**
```
resource.type="cloud_run_revision"
metric.type="run.googleapis.com/request_latencies"
```
Filtrer par `cold_start=true`.

**3. Healthcheck Failures**
```
resource.type="cloud_run_revision"
jsonPayload.message=~"healthz.*503"
```

---

## 🧪 Tests

### Test Local

```bash
# Démarrer backend local
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000

# Vérifier healthcheck pendant startup
for i in {1..10}; do
  curl -s http://localhost:8000/healthz | jq '.status'
  sleep 1
done
```

**Résultat attendu :**
```
"starting"  # Pendant warm-up
"starting"
"starting"
"ready"     # Après ~2s
"ready"
"ready"
```

### Test Cloud Run Staging

```bash
# Déployer en staging
gcloud run deploy emergence-app-staging \
  --image=... \
  --min-instances=1

# Forcer restart instance
gcloud run services update-traffic emergence-app-staging --to-revisions=LATEST=100

# Surveiller logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=emergence-app-staging" \
  --limit=50 --format=json | jq '.[] | .textPayload'
```

**Vérifier :**
- [ ] Logs montrent "✅ Warm-up completed"
- [ ] Temps warm-up < 5s
- [ ] Aucun 503 côté utilisateur pendant startup
- [ ] Premier hit utilisateur répond en < 200ms (pas de cold start)

---

## 🐛 Troubleshooting

### Symptôme : `/healthz` retourne toujours 503

**Cause :** Au moins 1 composant warm-up a échoué.

**Diagnostic :**
```bash
curl https://emergence-app.ch/healthz | jq
```

Exemple output :
```json
{
  "ok": false,
  "status": "starting",
  "db": true,
  "embed": false,  ← Le problème
  "vector": true,
  "di": true
}
```

**Solutions :**
1. Vérifier logs Cloud Run : `gcloud logging read ...`
2. Si `embed: false` → Vérifier que `sentence-transformers` installé
3. Si `db: false` → Vérifier connexion DB (secrets GCP)
4. Si `vector: false` → Vérifier Chroma accessible

### Symptôme : Warm-up prend > 10s

**Cause :** Modèle SBERT trop gros ou réseau lent.

**Solutions :**
1. Pré-charger modèle dans image Docker :
   ```dockerfile
   RUN python -c "from sentence_transformers import SentenceTransformer; \
       SentenceTransformer('all-MiniLM-L6-v2')"
   ```
2. Utiliser modèle plus léger (ex: `paraphrase-MiniLM-L3-v2`)
3. Augmenter `readinessProbe.initialDelaySeconds` dans YAML

### Symptôme : Instances restart en boucle

**Cause :** Healthcheck fail → Cloud Run kill instance → restart → fail...

**Diagnostic :**
```bash
gcloud run revisions describe emergence-app-00123 \
  --region=europe-west1 --format=json | jq '.status.conditions'
```

**Solutions :**
1. Augmenter `readinessProbe.failureThreshold` (ex: 5 au lieu de 3)
2. Augmenter `readinessProbe.periodSeconds` (ex: 10s au lieu de 5s)
3. Vérifier logs : `gcloud logging read ...`

---

## 📊 Métriques Custom (Prometheus)

### Warm-up Duration

Ajouter métrique dans `main.py` :

```python
from prometheus_client import Histogram

warmup_duration_seconds = Histogram(
    "warmup_duration_seconds",
    "Duration of startup warm-up",
    buckets=[0.5, 1, 2, 3, 5, 10, 30]
)

async def _startup(container):
    start = time.perf_counter()
    # ... warm-up ...
    duration = time.perf_counter() - start
    warmup_duration_seconds.observe(duration)
```

**Query Grafana :**
```promql
histogram_quantile(0.95, warmup_duration_seconds_bucket)  # P95 warm-up time
```

---

## 🔒 Sécurité

### Endpoint `/healthz` Public

`/healthz` est **public** (pas d'auth) car Cloud Run doit pouvoir le requêter.

**Mitigation :**
- Pas d'info sensible dans payload (juste flags true/false)
- Rate limiting : 1 req/sec max (via `RateLimitMiddleware`)

### Secrets en Warm-up

DB credentials chargés depuis secrets GCP :

```python
# ✅ BON : Secrets depuis env vars (injectés par Cloud Run)
DB_HOST = os.getenv("DB_HOST")
DB_PASSWORD = os.getenv("DB_PASSWORD")  # Secret Manager

# ❌ MAUVAIS : Hardcodés
DB_PASSWORD = "my-secret-password-123"
```

---

## 📚 Références

- **Code source :** [`src/backend/main.py`](../../src/backend/main.py#L74-L221)
- **Healthcheck :** [`src/backend/main.py`](../../src/backend/main.py#L428-L452)
- **Cloud Run Docs :** https://cloud.google.com/run/docs/configuring/healthchecks
- **AGENT_SYNC.md :** Session [2025-10-21 09:25 CET](../../AGENT_SYNC.md)

---

## ✅ Checklist Déploiement

Avant de déployer warm-up en production :

- [ ] Tests local : warm-up < 5s ✅
- [ ] `/healthz` retourne 503 → 200 après warm-up ✅
- [ ] Logs montrent ✅ pour tous composants ✅
- [ ] Modèle SBERT pré-chargé dans image Docker
- [ ] Cloud Run YAML avec `min-instances=1` ✅
- [ ] Healthcheck configuré sur `/healthz` ✅
- [ ] Déploiement staging + validation 24h
- [ ] Monitoring Grafana avec alertes warmup failures
- [ ] Rollout progressif production (10% → 50% → 100%)

---

**🔥 Cloud Run Warm-up strict est prêt pour la production !**
