# Chat/LLM Service - Cloud Run Deployment (P2.4)

## Vue d'ensemble

Service dédié pour gérer les conversations LLM, intégrant :
- **LLM Providers** : OpenAI (GPT-4, GPT-4o-mini), Anthropic (Claude 3.5), Google (Gemini)
- **Memory/RAG** : ChromaDB, embeddings, concept recall, proactive hints
- **Streaming** : Réponses LLM en temps réel via WebSocket
- **Débat Multi-Agents** : Support débats entre agents

## Architecture

```
┌────────────────────────────────────────┐
│      Chat/LLM Service                  │
│  (Cloud Run - europe-west1)            │
└────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐  ┌────────┐  ┌────────┐
│OpenAI  │  │Anthropic│ │ Google │
│API     │  │ API    │  │ API    │
└────────┘  └────────┘  └────────┘
                 │
                 ▼
         ┌─────────────┐
         │  ChromaDB   │
         │  (Memory)   │
         └─────────────┘
```

## Modules Backend Requis

### Core Modules
- `backend/core/session_manager.py` - Gestion sessions WebSocket
- `backend/core/cost_tracker.py` - Tracking coûts LLM
- `backend/core/websocket.py` - WebSocket connection manager
- `backend/core/database/` - SQLite database access
- `backend/core/config.py` - Configuration globale
- `backend/core/middleware.py` - Monitoring, rate limiting

### Chat Feature
- `backend/features/chat/service.py` - **ChatService** principal
- `backend/features/chat/llm_stream.py` - Streaming LLM responses
- `backend/features/chat/memory_ctx.py` - Context mémoire LTM
- `backend/features/chat/rag_cache.py` - Cache RAG (TTL 5 min)
- `backend/features/chat/rag_metrics.py` - Métriques RAG
- `backend/features/chat/pricing.py` - Prix modèles LLM
- `backend/features/chat/post_session.py` - Post-processing sessions
- `backend/features/chat/router.py` - WebSocket router (`/ws/{session_id}`)

### Memory Feature
- `backend/features/memory/vector_service.py` - VectorService (ChromaDB)
- `backend/features/memory/gardener.py` - MemoryGardener (vitality)
- `backend/features/memory/concept_recall.py` - ConceptRecallTracker
- `backend/features/memory/proactive_hints.py` - ProactiveHintEngine

### Debate Feature (optionnel mais utilisé)
- `backend/features/debate/service.py` - DebateService
- `backend/features/debate/router.py` - Endpoints débats

### Shared Modules
- `backend/shared/models.py` - ChatMessage, Role, AgentMessage
- `backend/shared/config.py` - Settings, DEFAULT_AGENT_CONFIGS
- `backend/shared/dependencies.py` - DI helpers

## Configuration

### Variables d'environnement requises

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `OPENAI_API_KEY` | Clé API OpenAI | **Obligatoire** (Secret Manager) |
| `ANTHROPIC_API_KEY` | Clé API Anthropic | **Obligatoire** (Secret Manager) |
| `GOOGLE_API_KEY` | Clé API Google Gemini | Optionnel (Secret Manager) |
| `EMERGENCE_TEMP_DEFAULT` | Température par défaut | `0.4` |
| `EMERGENCE_RAG_OFF_POLICY` | Politique RAG OFF | `stateless` |
| `EMERGENCE_ENABLE_AGENT_MEMORY` | Activer mémoire agents | `true` |
| `ENABLE_STREAMING` | Activer streaming LLM | `true` |
| `MAX_TOKENS_DEFAULT` | Max tokens par défaut | `4096` |
| `ENABLE_RAG_CACHE` | Cache RAG activé | `true` |
| `RAG_CACHE_TTL_SECONDS` | TTL cache RAG | `300` (5 min) |

### Secrets Google Cloud (Secret Manager)

```bash
# Créer les secrets obligatoires
echo "sk-..." | gcloud secrets create OPENAI_API_KEY --data-file=-
echo "sk-ant-..." | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo "AIza..." | gcloud secrets create GOOGLE_API_KEY --data-file=-

# Donner accès au service account
SERVICE_ACCOUNT="486095406755-compute@developer.gserviceaccount.com"
for SECRET in OPENAI_API_KEY ANTHROPIC_API_KEY GOOGLE_API_KEY; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

## Déploiement

### 1. Build et déploiement complet

```bash
cd infra/cloud-run
./deploy-chat-service.sh
```

### 2. Build uniquement (test local)

```bash
./deploy-chat-service.sh --build-only
```

### 3. Déploiement sans rebuild

```bash
./deploy-chat-service.sh --deploy-only
```

### 4. Via Makefile (recommandé)

```bash
cd infra/cloud-run
make deploy-chat    # Build + Deploy
make test-chat      # Tests d'intégration
make logs-chat      # Logs en temps réel
```

## Endpoints exposés

### Health Check
```
GET /api/health
```

### Chat WebSocket
```
WS /ws/{session_id}
```

Payload WebSocket :
```json
{
  "type": "chat",
  "data": {
    "message": "Hello, world!",
    "agent_id": "AnimA",
    "model": "gpt-4o-mini",
    "temperature": 0.4
  }
}
```

### Métriques Prometheus
```
GET /metrics
```

Métriques exposées :
- `chat_messages_total` - Total messages traités
- `llm_api_calls_total` - Appels API LLM (par provider)
- `llm_tokens_total` - Tokens consommés (input/output)
- `llm_cost_total` - Coûts LLM (USD)
- `rag_cache_hits_total` - Cache hits RAG
- `memory_proactive_hints_generated_total` - Hints proactifs générés

## Configuration Cloud Run

### Ressources
- **CPU** : 4 cores (pour embeddings + LLM)
- **Memory** : 2Gi (ChromaDB en mémoire)
- **Timeout** : 600s (10 min pour longues générations)
- **Concurrency** : 80 requêtes simultanées

### Auto-scaling
- **Min instances** : 1 (toujours chaud pour latence)
- **Max instances** : 15 (pic de charge)

### Coûts estimés
- **Min** : ~$40-60/mois (1 instance active)
- **Max** : ~$300-500/mois (15 instances @ peak)
- **+ Coûts LLM API** : Variable selon usage (GPT-4 vs GPT-4o-mini)

## Tests

### Test complet (automatisé)
```bash
./test-services.sh chat
```

### Tests manuels

**1. Health check**
```bash
SERVICE_URL=$(gcloud run services describe emergence-chat-service \
  --region=europe-west1 --project=emergence-469005 \
  --format="value(status.url)")

curl "$SERVICE_URL/api/health"
# Expected: {"status":"ok","message":"Emergence Backend is running."}
```

**2. WebSocket chat (via wscat)**
```bash
npm install -g wscat
wscat -c "wss://YOUR-SERVICE-URL/ws/test-session-123"

# Send message:
{"type":"chat","data":{"message":"Hello from test","agent_id":"AnimA"}}
```

**3. Métriques Prometheus**
```bash
curl "$SERVICE_URL/metrics" | grep chat_messages_total
```

## Troubleshooting

### Problème : Service ne démarre pas

**Solution** : Vérifier logs
```bash
gcloud run services logs tail emergence-chat-service \
  --project=emergence-469005 \
  --region=europe-west1 \
  --limit=100
```

### Problème : Timeout LLM

**Solution** : Augmenter timeout Cloud Run
```yaml
# chat-service.yaml
spec:
  template:
    spec:
      timeoutSeconds: 900  # 15 min au lieu de 10 min
```

### Problème : Out of Memory (OOM)

**Solution** : Augmenter mémoire
```yaml
resources:
  limits:
    memory: 4Gi  # Au lieu de 2Gi
```

### Problème : Coûts LLM élevés

**Solutions** :
1. Vérifier métriques : `curl $SERVICE_URL/metrics | grep llm_cost_total`
2. Utiliser GPT-4o-mini au lieu de GPT-4
3. Réduire `MAX_TOKENS_DEFAULT`
4. Activer `ENABLE_RAG_CACHE=true`

## Monitoring

### Cloud Monitoring Dashboards

Créer dashboard avec métriques :
- **Request latency** (p50, p95, p99)
- **Request count**
- **Error rate**
- **Instance count**
- **Memory usage**
- **CPU usage**

### Alertes recommandées

```bash
# Alerte si error rate > 5%
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="Chat Service - High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05
```

## Rollback

En cas de problème après déploiement :

```bash
# Via Makefile
make rollback-chat

# Ou manuellement
gcloud run services update-traffic emergence-chat-service \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=europe-west1 \
  --project=emergence-469005
```

## Prochaines étapes (après P2.4)

- **P2.5** : Service Documents (upload, PDF parsing)
- **P2.6** : Service Memory/RAG dédié (Vertex AI Vector Search)
- **P2.8** : Load Balancer unifié (routing `/api/chat/*`)

## Références

- [MICROSERVICES_ARCHITECTURE.md](./MICROSERVICES_ARCHITECTURE.md)
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [OpenAI API](https://platform.openai.com/docs)
- [Anthropic API](https://docs.anthropic.com)
- [Google Gemini API](https://ai.google.dev)

---

**Date création** : 2025-10-17
**Phase** : P2.4 - Chat/LLM Service
**Statut** : ✅ Configuration ready, déploiement pending
