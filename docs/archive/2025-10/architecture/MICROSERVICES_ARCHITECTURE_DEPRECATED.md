# Emergence - Architecture Microservices Cloud Run

## Vue d'ensemble

L'application Emergence est en cours de migration vers une architecture microservices sur Google Cloud Run, permettant une meilleure scalabilité, isolation des responsabilités et résilience.

## Architecture actuelle (Phase P2.2, P2.3, P2.4)

```
┌──────────────────────────────────────────────────────────────┐
│                      Load Balancer                           │
│              (Google Cloud Load Balancing)                   │
└──────────────────────────────────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │              │
            ▼                  ▼                  ▼              ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Auth Service    │ │   Session    │ │  Chat/LLM    │ │  Main App    │
│  (Cloud Run)     │ │   Service    │ │   Service    │ │  (Cloud Run) │
│                  │ │  (Cloud Run) │ │  (Cloud Run) │ │              │
│  - Login/Logout  │ │  - WebSocket │ │  - LLM APIs  │ │  - Documents │
│  - JWT tokens    │ │  - Sessions  │ │  - Streaming │ │  - Dashboard │
│  - User mgmt     │ │  - Memory    │ │  - RAG/Cache │ │  - Benchmarks│
│  - Passwords     │ │  - Threads   │ │  - Debate    │ │              │
└──────────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
         │                  │                 │                 │
         └──────────────────┼─────────────────┼─────────────────┘
                            ▼                 ▼
                   ┌─────────────────┐  ┌──────────────┐
                   │   SQLite DB     │  │  ChromaDB    │
                   │  (Cloud Storage)│  │   (Memory)   │
                   └─────────────────┘  └──────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
              ┌──────────┐             ┌──────────┐             ┌──────────┐
              │  OpenAI  │             │ Anthropic│             │  Google  │
              │   API    │             │   API    │             │Gemini API│
              └──────────┘             └──────────┘             └──────────┘
```

## Services déployés

### 1. Service d'Authentification (`emergence-auth-service`)

**Responsabilités:**
- Authentification des utilisateurs (login/logout)
- Gestion des tokens JWT
- Gestion des utilisateurs et de l'allowlist
- Réinitialisation de mot de passe
- Gestion des sessions d'authentification

**Endpoints:**
- `POST /api/auth/login` - Connexion utilisateur
- `POST /api/auth/logout` - Déconnexion
- `POST /api/auth/dev/login` - Login dev (si AUTH_DEV_MODE=true)
- `GET /api/auth/session` - Informations sur la session courante
- `POST /api/auth/change-password` - Changer son mot de passe
- `POST /api/auth/request-password-reset` - Demander reset de mot de passe
- `POST /api/auth/reset-password` - Réinitialiser le mot de passe
- `GET /api/auth/admin/allowlist` - Liste des utilisateurs autorisés (admin)
- `POST /api/auth/admin/allowlist` - Ajouter/modifier un utilisateur (admin)
- `DELETE /api/auth/admin/allowlist/{email}` - Supprimer un utilisateur (admin)
- `GET /api/auth/admin/sessions` - Liste des sessions actives (admin)
- `POST /api/auth/admin/sessions/revoke` - Révoquer une session (admin)

**Configuration Cloud Run:**
- Min instances: 1
- Max instances: 10
- CPU: 2
- Memory: 1Gi
- Concurrency: 80
- Timeout: 300s

**Variables d'environnement:**
- `AUTH_JWT_SECRET` - Secret pour signer les JWT (Secret Manager)
- `AUTH_JWT_ISSUER` - Émetteur des tokens JWT
- `AUTH_JWT_AUDIENCE` - Audience des tokens JWT
- `AUTH_JWT_TTL_DAYS` - Durée de vie des tokens (7 jours par défaut)
- `AUTH_ADMIN_EMAILS` - Emails des administrateurs (Secret Manager)
- `SMTP_*` - Configuration SMTP pour les emails de reset

### 2. Service de Session (`emergence-session-service`)

**Responsabilités:**
- Gestion des sessions WebSocket
- Gestion des conversations chat
- Analyse mémoire des sessions
- Gestion des threads de conversation
- Timeout d'inactivité automatique

**Endpoints:**
- `WS /ws/{session_id}` - Connexion WebSocket pour le chat
- `GET /api/health` - Health check
- Endpoints de gestion des threads et de la mémoire

**Configuration Cloud Run:**
- Min instances: 2
- Max instances: 20
- CPU: 4
- Memory: 2Gi
- Concurrency: 100
- Timeout: 900s (15 min pour les sessions longues)

**Variables d'environnement:**
- `SESSION_INACTIVITY_TIMEOUT_MINUTES` - Timeout d'inactivité (30 min)
- `SESSION_CLEANUP_INTERVAL_SECONDS` - Intervalle de nettoyage (60s)
- `SESSION_WARNING_BEFORE_TIMEOUT_SECONDS` - Avertissement avant timeout (120s)
- `MEMORY_ENABLED` - Activer l'analyse mémoire
- `EMBED_MODEL_NAME` - Modèle d'embeddings (all-MiniLM-L6-v2)
- `PROMETHEUS_ENABLED` - Métriques Prometheus

### 3. Service Chat/LLM (`emergence-chat-service`) - 🆕 P2.4

**Responsabilités:**
- Interactions avec les LLM (OpenAI, Anthropic, Google)
- Streaming des réponses LLM via WebSocket
- Gestion du contexte RAG (Retrieval-Augmented Generation)
- Cache RAG (TTL 5 min)
- Memory features (gardener, concept recall, proactive hints)
- Débats multi-agents
- Tracking des coûts LLM

**Endpoints:**
- `WS /ws/{session_id}` - WebSocket chat avec LLM
- `POST /api/chat/message` - Envoi message (REST fallback)
- `GET /api/health` - Health check
- `GET /metrics` - Métriques Prometheus

**Configuration Cloud Run:**
- Min instances: 1 (warm start critique pour latence)
- Max instances: 15
- CPU: 4 (pour embeddings + LLM processing)
- Memory: 2Gi (ChromaDB en mémoire)
- Concurrency: 80
- Timeout: 600s (10 min pour longues générations LLM)

**Variables d'environnement:**
- `OPENAI_API_KEY` - Clé API OpenAI (Secret Manager) **[Obligatoire]**
- `ANTHROPIC_API_KEY` - Clé API Anthropic (Secret Manager) **[Obligatoire]**
- `GOOGLE_API_KEY` - Clé API Google Gemini (Secret Manager) [Optionnel]
- `EMERGENCE_TEMP_DEFAULT` - Température par défaut (0.4)
- `EMERGENCE_RAG_OFF_POLICY` - Politique RAG OFF (stateless)
- `EMERGENCE_ENABLE_AGENT_MEMORY` - Activer mémoire agents (true)
- `MAX_TOKENS_DEFAULT` - Max tokens par défaut (4096)
- `ENABLE_STREAMING` - Activer streaming LLM (true)
- `ENABLE_RAG_CACHE` - Cache RAG activé (true)
- `RAG_CACHE_TTL_SECONDS` - TTL cache RAG (300 = 5 min)
- `ENABLE_MEMORY_GARDENER` - Memory gardener (true)
- `ENABLE_CONCEPT_RECALL` - Concept recall tracker (true)
- `ENABLE_PROACTIVE_HINTS` - Proactive hints engine (true)

**Métriques Prometheus exposées:**
- `chat_messages_total` - Total messages traités
- `llm_api_calls_total{provider,model}` - Appels API LLM
- `llm_tokens_total{type,model}` - Tokens consommés (input/output)
- `llm_cost_total{provider,model}` - Coûts LLM (USD)
- `rag_cache_hits_total` - Cache hits RAG
- `rag_cache_misses_total` - Cache misses RAG
- `memory_proactive_hints_generated_total{type}` - Hints proactifs générés
- `memory_concept_recall_total` - Rappels de concepts

**Dépendances externes:**
- OpenAI API (GPT-4, GPT-4o-mini)
- Anthropic API (Claude 3.5 Haiku, Sonnet, Opus)
- Google Generative AI (Gemini 1.5 Flash)

**Coûts estimés:**
- **Infrastructure** : ~$40-60/mois (min instances) | ~$300-500/mois (max instances @ peak)
- **LLM API** : Variable selon usage (GPT-4 : ~$0.03/1K tokens, GPT-4o-mini : ~$0.00015/1K tokens)

### 4. Application Principale (`emergence-app`)

Contient tous les autres services qui ne sont pas encore migrés:
- Dashboard
- Documents
- Debate
- Benchmarks
- Memory
- Monitoring

## Déploiement

### Service d'Authentification

```bash
cd /path/to/emergenceV8
chmod +x infra/cloud-run/deploy-auth-service.sh
./infra/cloud-run/deploy-auth-service.sh
```

### Service de Session

```bash
cd /path/to/emergenceV8
chmod +x infra/cloud-run/deploy-session-service.sh
./infra/cloud-run/deploy-session-service.sh
```

### Service Chat/LLM (P2.4)

```bash
cd /path/to/emergenceV8
chmod +x infra/cloud-run/deploy-chat-service.sh
./infra/cloud-run/deploy-chat-service.sh
```

**Ou via Makefile (recommandé):**

```bash
cd infra/cloud-run
make deploy-chat    # Deploy chat service
make test-chat      # Test health endpoint
make logs-chat      # Tail logs
```

## Sécurité

### Secrets requis

Les secrets suivants doivent être configurés dans Google Secret Manager:

**Pour le service Auth:**
- `AUTH_JWT_SECRET` - Secret pour JWT (générer avec `openssl rand -hex 32`)
- `AUTH_ADMIN_EMAILS` - Liste des emails admin séparés par virgule
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` - Configuration email

**Pour tous les services:**
- `OPENAI_API_KEY` - Clé API OpenAI
- `ANTHROPIC_API_KEY` - Clé API Anthropic
- `GOOGLE_API_KEY` - Clé API Google

### Création des secrets

```bash
# JWT Secret
openssl rand -hex 32 | gcloud secrets create AUTH_JWT_SECRET \
  --data-file=- \
  --replication-policy="automatic" \
  --project=emergence-469005

# Admin Emails
echo "admin@example.com,user@example.com" | gcloud secrets create AUTH_ADMIN_EMAILS \
  --data-file=- \
  --replication-policy="automatic" \
  --project=emergence-469005
```

## Monitoring

### Métriques Prometheus

Le service de session expose des métriques Prometheus sur `/metrics`:

**Métriques de session:**
- `sessions_timeout_total` - Total de sessions fermées par timeout
- `sessions_warning_sent_total` - Total d'avertissements d'inactivité envoyés
- `sessions_active_current` - Nombre de sessions actives
- `session_inactivity_duration_seconds` - Histogramme de durée d'inactivité

### Logs

Les logs sont disponibles dans Cloud Logging:

```bash
# Logs du service auth
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-auth-service" \
  --project=emergence-469005 \
  --limit=50

# Logs du service session
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-session-service" \
  --project=emergence-469005 \
  --limit=50
```

## Tests

### Test du service Auth

```bash
# Health check
curl https://emergence-auth-service-XXXXXXXXXX-ew.a.run.app/api/health

# Login
curl -X POST https://emergence-auth-service-XXXXXXXXXX-ew.a.run.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

### Test du service Session

```bash
# Health check
curl https://emergence-session-service-XXXXXXXXXX-ew.a.run.app/api/health

# WebSocket test (avec websocat ou navigateur)
websocat wss://emergence-session-service-XXXXXXXXXX-ew.a.run.app/ws/test-session-id
```

## Prochaines étapes (Phases futures)

- ✅ **P2.4**: Migration du service Chat/LLM ← **COMPLÉTÉ**
- **P2.5**: Migration du service Documents (upload, PDF parsing)
- **P2.6**: Migration du service Memory/RAG (Vertex AI Vector Search)
- **P2.7**: Migration du service Dashboard (analytics, admin)
- **P2.8**: Mise en place d'un API Gateway unifié (Cloud Load Balancer + routing)
- **P2.9**: Migration vers Cloud SQL PostgreSQL (scalabilité BDD)

## Considérations importantes

### État partagé

Actuellement, tous les services partagent la même base de données SQLite montée depuis Cloud Storage. Pour une meilleure isolation:
- **Court terme**: Continuer avec SQLite partagé
- **Moyen terme**: Migrer vers Cloud SQL (PostgreSQL)
- **Long terme**: Bases de données séparées par service avec événements pour la synchronisation

### Communication inter-services

- Actuellement: Communication HTTP directe
- Recommandé: Utiliser Pub/Sub pour les événements asynchrones
- API Gateway pour router les requêtes externes

### Scaling

Les services sont configurés avec:
- **Auth**: min 1, max 10 instances (peu de trafic, latence critique)
- **Session**: min 2, max 20 instances (beaucoup de connexions WebSocket)
- **Chat/LLM**: min 1, max 15 instances (warm start critique, compute-intensive)
- **Main App**: Configuration existante maintenue

## Troubleshooting

### Service ne démarre pas

```bash
# Vérifier les logs
gcloud run services logs read emergence-auth-service --project=emergence-469005

# Vérifier la configuration
gcloud run services describe emergence-auth-service \
  --region=europe-west1 \
  --project=emergence-469005
```

### Problèmes de secrets

```bash
# Lister les secrets
gcloud secrets list --project=emergence-469005

# Vérifier les permissions
gcloud projects get-iam-policy emergence-469005 \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:486095406755-compute@developer.gserviceaccount.com"
```

### Rollback

```bash
# Lister les révisions
gcloud run revisions list --service=emergence-auth-service \
  --region=europe-west1 \
  --project=emergence-469005

# Rollback vers une révision précédente
gcloud run services update-traffic emergence-auth-service \
  --to-revisions=emergence-auth-service-00001-xyz=100 \
  --region=europe-west1 \
  --project=emergence-469005
```

## Contact & Support

Pour toute question sur l'architecture ou le déploiement, consulter:
- Documentation Cloud Run: https://cloud.google.com/run/docs
- Logs d'application: Cloud Logging
- Métriques: Cloud Monitoring
