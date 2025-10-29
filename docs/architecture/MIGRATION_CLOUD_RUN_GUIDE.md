# 🚀 Guide de Migration - ÉMERGENCE V8 vers Architecture Cloud Run Scalable

## 📋 Vue d'ensemble

Ce guide documente la migration de l'architecture actuelle (monolithique SQLite + Chroma local) vers une architecture Cloud Run scalable avec services managés GCP.

**Objectifs** :
- ✅ Persistance durable (Cloud SQL PostgreSQL + pgvector)
- ✅ Scalabilité horizontale (Workers Pub/Sub par agent)
- ✅ Cache haute performance (Memorystore Redis)
- ✅ Coûts optimisés (scale-to-zero, pay-per-use)

---

## 🏗️ Architecture Cible

```
┌──────────────┐
│  Frontend    │ (Cloud Run static ou CDN)
│  (Vite SPA)  │
└──────┬───────┘
       │ HTTPS
       ▼
┌──────────────────────┐
│  Orchestrateur       │ (Cloud Run service principal)
│  FastAPI + WebSocket│
└────────┬─────────────┘
         │ Pub/Sub
    ┌────┼────┐
    ▼    ▼    ▼
  ┌───┐┌───┐┌───┐
  │ A ││ N ││ N │ (Cloud Run Jobs/Services)
  │ N ││ E ││ E │ Workers agents
  │ I ││ O ││ X │
  │ M ││   ││ U │
  │ A ││   ││ S │
  └─┬─┘└─┬─┘└─┬─┘
    └────┼────┘
         │
    ┌────▼─────┐
    │ Cloud SQL│ (PostgreSQL + pgvector)
    │ Redis    │ (Memorystore cache)
    └──────────┘
```

---

## 📅 Plan de Migration (4 semaines)

### Semaine 1 : Infrastructure (Terraform)

#### Jour 1-2 : Provisionner Cloud SQL

```bash
# 1. Initialiser Terraform
cd infra/terraform
terraform init

# 2. Créer variables
cat > terraform.tfvars <<EOF
project_id = "emergence-469005"
region = "europe-west1"
db_password = "$(openssl rand -base64 32)"
redis_memory_size_gb = 1
environment = "prod"
EOF

# 3. Plan et apply Cloud SQL
terraform plan -target=google_sql_database_instance.emergence_postgres
terraform apply -target=google_sql_database_instance.emergence_postgres

# 4. Récupérer connection string
terraform output cloudsql_connection_name
# Output: emergence-469005:europe-west1:emergence-postgres-prod
```

**Vérification** :
```bash
# Test connexion via Cloud SQL Proxy
cloud-sql-proxy emergence-469005:europe-west1:emergence-postgres-prod &
psql -h localhost -U emergence-app -d emergence
# Password: <from terraform.tfvars>

# Vérifier pgvector
\dx
# Devrait montrer: vector | 0.5.1 | public | vector data type and ivfflat access method
```

#### Jour 3 : Provisionner Memorystore Redis

```bash
# Apply Redis
terraform apply -target=google_redis_instance.emergence_redis

# Récupérer host et port
terraform output redis_connection_string
# Output: redis://10.x.x.x:6379
```

**Vérification** :
```bash
# Test depuis Cloud Shell (même VPC)
redis-cli -h <REDIS_HOST>
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> SET test "hello"
OK
127.0.0.1:6379> GET test
"hello"
```

#### Jour 4-5 : Provisionner Pub/Sub

```bash
# Apply Pub/Sub topics + subscriptions
terraform apply -target=google_pubsub_topic.agent_anima
terraform apply -target=google_pubsub_topic.agent_neo
terraform apply -target=google_pubsub_topic.agent_nexus
terraform apply -target=google_pubsub_topic.dlq

# Vérifier topics
gcloud pubsub topics list
# Devrait montrer: agent-anima-tasks, agent-neo-tasks, agent-nexus-tasks, agent-tasks-dlq
```

---

### Semaine 2 : Migration Base de Données

#### Jour 1 : Créer schema PostgreSQL

```bash
# 1. Appliquer schema
psql -h <CLOUD_SQL_HOST> -U emergence-app -d emergence -f infra/sql/schema_postgres.sql

# 2. Vérifier tables
psql -h <CLOUD_SQL_HOST> -U emergence-app -d emergence -c "\dt"
# Devrait montrer 15+ tables (auth_allowlist, sessions, messages, documents, etc.)

# 3. Vérifier extensions
psql -h <CLOUD_SQL_HOST> -U emergence-app -d emergence -c "SELECT * FROM pg_extension;"
# Devrait montrer: pgvector, pg_trgm
```

#### Jour 2-3 : Migrer données SQLite → PostgreSQL

```bash
# 1. Configurer env vars
export CLOUD_SQL_HOST="<IP_FROM_TERRAFORM>"
export DB_PASSWORD="<PASSWORD_FROM_TFVARS>"
export CLOUD_SQL_DATABASE="emergence"
export CLOUD_SQL_USER="emergence-app"

# 2. Lancer migration
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite-path src/backend/data/db/emergence_v7.db \
  --batch-size 1000

# Output attendu:
# ============================================================
# Starting SQLite → PostgreSQL migration
# ============================================================
# Migrating table: auth_allowlist
#   ✓ auth_allowlist: 5 rows migrated
# Migrating table: sessions
#   ✓ sessions: 142 rows migrated
# ...
# ============================================================
# Migration complete!
# ============================================================
#   auth_allowlist                      5 rows
#   sessions                          142 rows
#   messages                         3421 rows
#   ...
#   TOTAL                            4582 rows
```

#### Jour 4 : Vérification migration

```bash
# Vérifier counts
python scripts/migrate_sqlite_to_postgres.py --verify-only

# Output attendu:
# ============================================================
# Verifying migration...
# ============================================================
#   ✓ auth_allowlist                SQLite:      5  PostgreSQL:      5
#   ✓ sessions                      SQLite:    142  PostgreSQL:    142
#   ✓ messages                      SQLite:   3421  PostgreSQL:   3421
#   ...
# ============================================================
# ✓ All tables verified successfully!
```

**Vérification manuelle** :
```sql
-- Check vector embeddings (pgvector)
SELECT id, filename, embedding <-> '[0.1, 0.2, ...]'::vector AS distance
FROM document_chunks
LIMIT 5;

-- Check indexes
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename = 'document_chunks';
-- Devrait montrer: idx_chunks_embedding_ivfflat
```

#### Jour 5 : Backup et snapshot

```bash
# Créer backup manuel
gcloud sql backups create \
  --instance=emergence-postgres-prod \
  --project=emergence-469005

# Créer snapshot (pour rollback si besoin)
gcloud sql backups list \
  --instance=emergence-postgres-prod \
  --project=emergence-469005
```

---

### Semaine 3 : Déploiement Workers

#### Jour 1-2 : Build et deploy workers

```bash
# 1. Build image worker Anima
docker build -f workers/Dockerfile.worker -t gcr.io/emergence-469005/anima-worker:v1.0.0 .
docker push gcr.io/emergence-469005/anima-worker:v1.0.0

# 2. Deploy worker Cloud Run
gcloud run services replace infra/cloud-run/anima-worker.yaml \
  --region=europe-west1 \
  --project=emergence-469005

# 3. Vérifier deployment
gcloud run services describe anima-worker \
  --region=europe-west1 \
  --project=emergence-469005

# 4. Test health check
WORKER_URL=$(gcloud run services describe anima-worker --region=europe-west1 --format='value(status.url)')
curl $WORKER_URL/health
# Output: {"status":"healthy","database":"ok","worker":"anima"}
```

**Répéter pour Neo et Nexus** :
```bash
# Neo worker
docker build -f workers/Dockerfile.worker -t gcr.io/emergence-469005/neo-worker:v1.0.0 \
  --build-arg WORKER_MODULE=workers.neo_worker .
docker push gcr.io/emergence-469005/neo-worker:v1.0.0
gcloud run services replace infra/cloud-run/neo-worker.yaml --region=europe-west1

# Nexus worker
docker build -f workers/Dockerfile.worker -t gcr.io/emergence-469005/nexus-worker:v1.0.0 \
  --build-arg WORKER_MODULE=workers.nexus_worker .
docker push gcr.io/emergence-469005/nexus-worker:v1.0.0
gcloud run services replace infra/cloud-run/nexus-worker.yaml --region=europe-west1
```

#### Jour 3 : Configurer Pub/Sub push subscriptions

```bash
# Update subscription avec worker URL
ANIMA_URL=$(gcloud run services describe anima-worker --region=europe-west1 --format='value(status.url)')

gcloud pubsub subscriptions update anima-worker-sub \
  --push-endpoint="$ANIMA_URL/process" \
  --push-auth-service-account=anima-worker@emergence-469005.iam.gserviceaccount.com

# Tester Pub/Sub → Worker
gcloud pubsub topics publish agent-anima-tasks \
  --message='{"message_id":"test-123","session_id":"test-session","messages":[{"role":"user","content":"Hello"}]}'

# Vérifier logs worker
gcloud logs read --service=anima-worker --limit=10
```

#### Jour 4-5 : Tests end-to-end

```bash
# Test flow complet: Orchestrator → Pub/Sub → Worker → Database

# 1. Publier message test
python tests/test_pubsub_worker_flow.py

# 2. Vérifier résultat dans DB
psql -h <CLOUD_SQL_HOST> -U emergence-app -d emergence -c \
  "SELECT id, content, agent_id, cost_usd FROM messages WHERE agent_id='anima' ORDER BY created_at DESC LIMIT 1;"

# 3. Vérifier métriques
gcloud monitoring metrics list --filter="metric.type:run.googleapis.com"
```

---

### Semaine 4 : Migration Orchestrateur + Production

#### Jour 1-2 : Adapter orchestrateur pour PostgreSQL + Redis

**Modifications code** :
```python
# src/backend/main.py

# AVANT (SQLite)
from backend.core.database.manager import DatabaseManager
db = DatabaseManager("src/backend/data/db/emergence_v7.db")

# APRÈS (PostgreSQL)
from backend.core.database.manager_postgres import PostgreSQLManager
db = PostgreSQLManager(
    host=os.getenv("CLOUD_SQL_HOST"),
    unix_socket=os.getenv("CLOUD_SQL_UNIX_SOCKET"),
    database="emergence",
    user="emergence-app",
    password=os.getenv("DB_PASSWORD")
)

# Ajouter Redis
from backend.core.cache.redis_manager import RedisManager
redis = RedisManager(
    host=os.getenv("REDIS_HOST"),
    password=os.getenv("REDIS_PASSWORD")
)
```

**Modifier ChatService pour publier vers Pub/Sub** :
```python
# src/backend/features/chat/service.py

from google.cloud import pubsub_v1

class ChatService:
    def __init__(self, db, redis, pubsub_publisher):
        self.db = db
        self.redis = redis
        self.publisher = pubsub_publisher

    async def handle_message(self, session_id, user_message):
        # 1. Sauvegarder message user
        await self.db.execute(
            "INSERT INTO messages (session_id, role, content) VALUES ($1, $2, $3)",
            session_id, "user", user_message
        )

        # 2. Publier vers Pub/Sub (agent async)
        topic = f"projects/emergence-469005/topics/agent-anima-tasks"
        message_data = {
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
            "messages": [{"role": "user", "content": user_message}]
        }

        future = self.publisher.publish(
            topic,
            json.dumps(message_data).encode("utf-8")
        )
        future.result()  # Wait for publish

        # 3. Return pending status (client poll ou WebSocket callback)
        return {"status": "processing", "message_id": message_data["message_id"]}
```

#### Jour 3 : Deploy orchestrateur mis à jour

```bash
# 1. Build nouvelle image
docker build -t gcr.io/emergence-469005/emergence-app:v2.0.0 .
docker push gcr.io/emergence-469005/emergence-app:v2.0.0

# 2. Update Cloud Run service
gcloud run services update emergence-app \
  --image=gcr.io/emergence-469005/emergence-app:v2.0.0 \
  --region=europe-west1 \
  --add-cloudsql-instances=emergence-469005:europe-west1:emergence-postgres-prod \
  --set-env-vars="CLOUD_SQL_UNIX_SOCKET=/cloudsql/emergence-469005:europe-west1:emergence-postgres-prod" \
  --set-env-vars="REDIS_HOST=<REDIS_IP_FROM_TERRAFORM>"

# 3. Tester
curl https://emergence-app-xxx.run.app/api/health
```

#### Jour 4 : Tests production

**Checklist finale** :
- [ ] Orchestrateur connecté à Cloud SQL (pas SQLite)
- [ ] Workers reçoivent messages Pub/Sub
- [ ] Workers écrivent dans Cloud SQL
- [ ] Redis cache fonctionne (RAG, sessions)
- [ ] WebSocket notifications fonctionnent
- [ ] Métriques Cloud Monitoring actives
- [ ] Logs centralisés Cloud Logging
- [ ] Backups automatiques configurés

#### Jour 5 : Cutover production

```bash
# 1. Maintenance mode (optionnel)
# Afficher page "Migration en cours..." côté frontend

# 2. Switch DNS/Load Balancer vers nouvelle architecture
gcloud compute url-maps update emergence-lb \
  --default-service=emergence-app-new

# 3. Monitoring intensif (1h)
gcloud monitoring dashboards create --config-from-file=monitoring/prod-dashboard.yaml

# 4. Validation
# - Envoyer messages test
# - Vérifier coûts LLM trackés
# - Tester RAG avec documents
# - Vérifier débats multi-agents

# 5. Désactiver ancienne architecture (après 24h stabilité)
gcloud run services delete emergence-app-old --region=europe-west1
```

---

## 🔧 Configuration CI/CD (Cloud Build)

### Fichier cloudbuild.yaml

```yaml
# cloudbuild.yaml - CI/CD pour ÉMERGENCE V8

steps:
  # Step 1: Tests backend
  - name: 'python:3.11-slim'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -r requirements.txt
        pytest tests/ --cov=src/backend --cov-report=term

  # Step 2: Build frontend
  - name: 'node:20'
    entrypoint: 'npm'
    args: ['ci']

  - name: 'node:20'
    entrypoint: 'npm'
    args: ['run', 'build']

  # Step 3: Build Docker orchestrateur
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/emergence-app:$SHORT_SHA'
      - '-t'
      - 'gcr.io/$PROJECT_ID/emergence-app:latest'
      - '.'

  # Step 4: Push orchestrateur
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '--all-tags', 'gcr.io/$PROJECT_ID/emergence-app']

  # Step 5: Build workers
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'workers/Dockerfile.worker'
      - '-t'
      - 'gcr.io/$PROJECT_ID/anima-worker:$SHORT_SHA'
      - '.'

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/anima-worker:$SHORT_SHA']

  # Repeat for neo-worker, nexus-worker...

  # Step 6: Deploy orchestrateur
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'emergence-app'
      - '--image=gcr.io/$PROJECT_ID/emergence-app:$SHORT_SHA'
      - '--region=europe-west1'
      - '--platform=managed'

  # Step 7: Deploy workers
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'anima-worker'
      - '--image=gcr.io/$PROJECT_ID/anima-worker:$SHORT_SHA'
      - '--region=europe-west1'

options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY

timeout: '1200s'
```

### Trigger automatique

```bash
# Créer trigger Cloud Build sur push main
gcloud builds triggers create github \
  --repo-name=emergencev8 \
  --repo-owner=DrKz36 \
  --branch-pattern=^main$ \
  --build-config=cloudbuild.yaml \
  --project=emergence-469005
```

---

## 📊 Monitoring & Alertes

### Métriques clés à surveiller

**Cloud SQL** :
- CPU usage > 80%
- Connections > 80
- Disk usage > 80%
- Replication lag > 60s

**Memorystore Redis** :
- Memory usage > 90%
- Evicted keys > 100/min
- CPU usage > 80%

**Cloud Run** :
- Request latency p99 > 5s
- Error rate > 5%
- Cold start duration > 10s
- Instance count (autoscaling)

**Pub/Sub** :
- Unacked messages > 1000
- Oldest unacked message age > 5min
- Dead letter queue growth

### Alertes Slack/Email

```bash
# Créer notification channel
gcloud alpha monitoring channels create \
  --display-name="ÉMERGENCE Alerts" \
  --type=slack \
  --channel-labels=url=https://hooks.slack.com/...

# Créer alert policy
gcloud alpha monitoring policies create \
  --notification-channels=<CHANNEL_ID> \
  --display-name="Cloud SQL CPU High" \
  --condition-display-name="CPU > 80%" \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s
```

---

## 💰 Optimisation Coûts

### Estimations mensuelles (charge moyenne)

| Service | Config | Coût/mois (USD) |
|---------|--------|-----------------|
| Cloud SQL | db-custom-2-7680, 20GB SSD | ~$120 |
| Memorystore Redis | 1GB Standard HA | ~$50 |
| Cloud Run Orchestrator | 2 vCPU, 2GB RAM, 50K req/jour | ~$30 |
| Cloud Run Workers (x3) | 1 vCPU, 512MB, scale-to-zero | ~$20 |
| Pub/Sub | 1M messages/mois | ~$5 |
| **TOTAL** | | **~$225/mois** |

**Optimisations possibles** :
- Cloud SQL : Passer en `db-f1-micro` pour dev/staging (~$15/mois)
- Redis : Tier Basic pour non-prod (~$25/mois)
- Workers : Aggressif scale-to-zero (minScale: 0)
- Pub/Sub : Batch publishing pour réduire coûts

---

## 🔄 Rollback Plan

Si problèmes critiques après migration :

### Rollback rapide (< 5 min)

```bash
# 1. Revert Cloud Run vers ancienne image
gcloud run services update emergence-app \
  --image=gcr.io/emergence-469005/emergence-app:v1.0.0 \
  --region=europe-west1

# 2. Rediriger vers ancienne architecture (SQLite monolithe)
# (si encore déployée en parallèle)

# 3. Restaurer backup Cloud SQL si corruption données
gcloud sql backups restore <BACKUP_ID> \
  --backup-instance=emergence-postgres-prod \
  --backup-project=emergence-469005
```

### Rollback complet (si échec total)

1. Restaurer ancienne architecture SQLite monolithe
2. Re-migrer données manuellement PostgreSQL → SQLite
3. Post-mortem et corrections avant re-tentative

---

## ✅ Checklist Finale

Avant de déclarer migration réussie :

- [ ] **Infrastructure** : Cloud SQL, Redis, Pub/Sub opérationnels
- [ ] **Migration données** : Counts vérifiés, embeddings pgvector fonctionnels
- [ ] **Workers** : 3 workers déployés, Pub/Sub push configuré
- [ ] **Orchestrateur** : Connecté PostgreSQL + Redis, Pub/Sub publisher
- [ ] **Tests E2E** : Flow complet user → orchestrator → worker → DB
- [ ] **Monitoring** : Dashboards + alertes configurés
- [ ] **Backups** : Automatiques quotidiens, testés
- [ ] **Performance** : Latence p99 < 2s, throughput > 100 req/s
- [ ] **Coûts** : Sous budget ($300/mois max)
- [ ] **Documentation** : Runbooks, procédures incident

---

## 📞 Support

**Ressources** :
- Architecture docs : `docs/architecture/`
- Terraform code : `infra/terraform/`
- Workers code : `workers/`
- Scripts migration : `scripts/migrate_sqlite_to_postgres.py`

**Contacts** :
- Architecte : gonzalefernando@gmail.com
- GCP Console : https://console.cloud.google.com/home/dashboard?project=emergence-469005

**🤖 Migration guide généré avec CodeSmith-AI - Version 1.0.0**
