# Session suivante: Phases P2.4 à P2.9

## Contexte

✅ **Phases P2.2 et P2.3 complétées** lors de cette session:
- Service d'authentification créé et documenté
- Service de gestion des sessions créé et documenté
- Infrastructure de déploiement complète
- Documentation exhaustive (architecture, migration, tests)

## Ce qui reste à faire

### Phase P2.4: Service Chat/LLM (priorité haute)

**Objectif**: Extraire la logique de chat et d'appel aux LLM dans un service dédié.

**Tâches**:
1. Créer `infra/cloud-run/chat-service.yaml`
2. Créer `infra/cloud-run/chat-service.Dockerfile`
3. Créer `infra/cloud-run/chat-requirements.txt`
4. Créer `infra/cloud-run/deploy-chat-service.sh`
5. Identifier et copier les modules nécessaires:
   - `src/backend/features/chat/`
   - `src/backend/core/llm/` (si existe)
   - Provider configurations (OpenAI, Anthropic, Google)
6. Configuration Cloud Run:
   - Min instances: 1
   - Max instances: 15
   - CPU: 4 cores
   - Memory: 2-4Gi
   - Timeout: 600s (10 min pour les longues générations)
7. Variables d'environnement:
   - API keys pour les LLMs (Secret Manager)
   - Configuration des modèles
   - Rate limiting

**Considérations**:
- Support multi-provider (OpenAI, Anthropic, Google)
- Gestion des tokens et coûts
- Streaming des réponses
- Circuit breakers pour les API LLM

### Phase P2.5: Service Documents (priorité moyenne)

**Objectif**: Service dédié pour l'upload, processing et gestion des documents.

**Tâches**:
1. Créer les fichiers de configuration Cloud Run
2. Modules à migrer:
   - `src/backend/features/documents/`
   - PDF parsing (PyMuPDF)
   - DOCX parsing
   - Text extraction
3. Configuration:
   - Min instances: 0 (peut cold start)
   - Max instances: 10
   - CPU: 2-4 cores
   - Memory: 2Gi
   - Timeout: 600s
4. Intégration avec Cloud Storage pour le stockage persistant

**Considérations**:
- Upload de fichiers volumineux
- Processing asynchrone
- Extraction de métadonnées
- Chunking pour RAG

### Phase P2.6: Service Memory/RAG (priorité haute)

**Objectif**: Service vectoriel dédié pour la mémoire et RAG.

**Tâches**:
1. Créer les fichiers de configuration Cloud Run
2. Modules à migrer:
   - `src/backend/features/memory/`
   - ChromaDB/Qdrant client
   - Embeddings generation
   - Memory analyzer
3. Configuration:
   - Min instances: 1 (pour avoir les embeddings en cache)
   - Max instances: 10
   - CPU: 4 cores
   - Memory: 4Gi (pour ChromaDB en mémoire)
   - Timeout: 300s
4. Considérer l'utilisation de Vertex AI Vector Search ou Pinecone

**Considérations**:
- Persistance des vecteurs (ChromaDB local vs service géré)
- Warm-up des embeddings models
- Performance des requêtes de similarité
- Synchronisation entre instances

### Phase P2.7: Service Dashboard (priorité basse)

**Objectif**: Service pour les endpoints de dashboard et analytics.

**Tâches**:
1. Créer les fichiers de configuration
2. Migrer:
   - `src/backend/features/dashboard/`
   - `src/backend/features/benchmarks/` (optionnel)
3. Configuration légère (peu de compute nécessaire)

### Phase P2.8: API Gateway & Load Balancer (critique)

**Objectif**: Unifier l'accès aux microservices derrière une URL unique.

**Tâches**:
1. Configurer Google Cloud Load Balancer
2. Créer les règles de routing:
   ```
   /api/auth/*      → emergence-auth-service
   /ws/*            → emergence-session-service
   /api/chat/*      → emergence-chat-service
   /api/documents/* → emergence-documents-service
   /api/memory/*    → emergence-memory-service
   /api/dashboard/* → emergence-dashboard-service
   /*               → emergence-app (fallback)
   ```
3. Configurer SSL/TLS
4. Configurer Cloud CDN (optionnel)
5. Mettre en place Cloud Armor (WAF)

**Configuration Load Balancer**:
```bash
# 1. Créer le backend bucket pour static assets
gcloud compute backend-buckets create emergence-static \
  --gcs-bucket-name=emergence-static-assets

# 2. Créer les NEGs (Network Endpoint Groups) pour chaque service
gcloud compute network-endpoint-groups create emergence-auth-neg \
  --region=europe-west1 \
  --network-endpoint-type=serverless \
  --cloud-run-service=emergence-auth-service

# 3. Créer les backend services
gcloud compute backend-services create emergence-auth-backend \
  --global \
  --load-balancing-scheme=EXTERNAL_MANAGED

# 4. Créer l'URL map avec routing
gcloud compute url-maps create emergence-lb \
  --default-service=emergence-app-backend

# 5. Configurer SSL et frontend
gcloud compute ssl-certificates create emergence-ssl \
  --domains=emergence.app,api.emergence.app

# 6. Créer le frontend HTTPS
gcloud compute target-https-proxies create emergence-https-proxy \
  --url-map=emergence-lb \
  --ssl-certificates=emergence-ssl
```

### Phase P2.9: Migration base de données (optionnel mais recommandé)

**Objectif**: Migrer de SQLite vers Cloud SQL (PostgreSQL).

**Étapes**:
1. Provisionner Cloud SQL instance
2. Créer le schéma PostgreSQL
3. Écrire script de migration SQLite → PostgreSQL
4. Tester la migration sur un environnement de staging
5. Mettre à jour les services pour utiliser PostgreSQL
6. Planifier la migration en production (fenêtre de maintenance)

**Configuration Cloud SQL recommandée**:
```yaml
Instance:
  tier: db-g1-small (démarrage)
  region: europe-west1
  high_availability: true (pour prod)
  backup:
    enabled: true
    start_time: "03:00"
  maintenance_window:
    day: SUN
    hour: 4
```

## Structure de session suggérée

### Session 1: P2.4 (Service Chat/LLM) - 2h
```
1. Analyser les dépendances actuelles du chat
2. Créer les fichiers de configuration
3. Tester le build Docker localement
4. Déployer et tester
5. Mettre à jour la documentation
```

### Session 2: P2.5 et P2.6 (Documents + Memory) - 3h
```
1. Service Documents (1h30)
   - Configuration et Dockerfile
   - Migration des modules
   - Tests d'upload

2. Service Memory/RAG (1h30)
   - Configuration avec embeddings
   - Migration ChromaDB
   - Tests de recherche vectorielle
```

### Session 3: P2.8 (Load Balancer) - 2h
```
1. Configurer le Load Balancer
2. Créer les règles de routing
3. Tester l'accès unifié
4. Configurer SSL
5. Tests de bout en bout
```

### Session 4 (optionnelle): P2.9 (PostgreSQL) - 4h
```
1. Provisionner Cloud SQL
2. Créer le schéma
3. Script de migration
4. Tests
5. Migration en production (fenêtre planifiée)
```

## Checklist avant de commencer P2.4

- [ ] P2.2 et P2.3 déployés et fonctionnels en production
- [ ] Tests d'intégration passent à 100%
- [ ] Monitoring configuré pour auth et session services
- [ ] Feedback utilisateurs collecté sur les 2 premiers services
- [ ] Coûts Cloud Run validés et dans le budget

## Ressources nécessaires

### Pour P2.4 (Chat/LLM)
- [ ] API keys pour OpenAI, Anthropic, Google (déjà en Secret Manager)
- [ ] Quotas vérifiés pour les API LLM
- [ ] Budget défini pour les coûts d'inférence

### Pour P2.6 (Memory/RAG)
- [ ] Évaluer Vertex AI Vector Search vs ChromaDB
- [ ] Budget pour le stockage vectoriel

### Pour P2.8 (Load Balancer)
- [ ] Nom de domaine configuré (emergence.app)
- [ ] Certificat SSL (Let's Encrypt ou géré par Google)

### Pour P2.9 (PostgreSQL)
- [ ] Budget Cloud SQL (~$50-200/mois selon instance)
- [ ] Planifier fenêtre de maintenance
- [ ] Backup SQLite avant migration

## Commandes utiles pour démarrer P2.4

```bash
# Se baser sur les templates P2.2/P2.3
cd infra/cloud-run

# Copier et adapter les fichiers
cp auth-service.yaml chat-service.yaml
cp auth-service.Dockerfile chat-service.Dockerfile
cp deploy-auth-service.sh deploy-chat-service.sh

# Identifier les dépendances
cd ../../src/backend/features/chat
ls -la
grep -r "import" *.py | sort | uniq

# Tester le build
docker build -f infra/cloud-run/chat-service.Dockerfile -t chat-local .
```

## Priorités

1. **Urgent**: P2.4 (Chat) - Service le plus utilisé, critique
2. **Important**: P2.6 (Memory) - Nécessaire pour les fonctionnalités RAG
3. **Important**: P2.8 (Load Balancer) - Simplifie l'accès client
4. **Moyen**: P2.5 (Documents) - Peut attendre si peu utilisé
5. **Optionnel**: P2.7 (Dashboard) - Nice to have
6. **Long terme**: P2.9 (PostgreSQL) - Amélioration scalabilité

## Documentation à créer pendant P2.4-P2.9

Pour chaque nouveau service:
- [ ] Ajouter section dans MICROSERVICES_ARCHITECTURE.md
- [ ] Mettre à jour MIGRATION_GUIDE.md
- [ ] Ajouter tests dans test-services.sh
- [ ] Mettre à jour le Makefile
- [ ] Créer diagrammes d'architecture mis à jour

## Métriques de succès

**Pour chaque phase complétée**:
- [ ] Service déployé et accessible
- [ ] Health checks passent
- [ ] Tests d'intégration à 100%
- [ ] Latency < 500ms (p95)
- [ ] Error rate < 1%
- [ ] Documentation à jour
- [ ] Coûts dans le budget prévu

## Points d'attention

**Performance**:
- Surveiller le cold start des services
- Optimiser les images Docker (multi-stage builds)
- Configurer min-instances appropriés

**Coûts**:
- Surveiller les coûts quotidiens
- Ajuster les ressources si sur-dimensionné
- Utiliser des budgets et alertes

**Sécurité**:
- Tous les secrets via Secret Manager
- IAM minimal pour chaque service
- HTTPS uniquement
- Cloud Armor configuré

## Fichiers de référence

Tout le code et la documentation sont dans:
- `infra/cloud-run/` - Configurations et scripts
- `MICROSERVICES_MIGRATION_P2_RECAP.md` - Résumé P2.2/P2.3
- Commit: `edd9886` - Phase P2.2 & P2.3 complete

---

**Résumé**: Les phases P2.2 et P2.3 sont complètes. La prochaine session devrait se concentrer sur P2.4 (Chat/LLM), le service le plus critique. Les templates et patterns sont établis, la migration des services suivants sera plus rapide.

**Temps estimé restant**: 10-15 heures pour P2.4 à P2.8 (sur 3-4 sessions)
