# Prompt Codex - Déploiement Production Phase 3 Cockpit

**Agent destinataire** : Codex (déploiement Cloud Run)
**Date** : 2025-10-09
**Objectif** : Déployer les features validées Phase 3 (Cockpit métriques enrichies) en production

---

## 📋 Contexte

### Features Validées ✅

**1. Cockpit Métriques Enrichies (Phase 3)**
- ✅ API endpoints fonctionnels : `/api/dashboard/costs/summary`, `/timeline/*`
- ✅ Métriques enrichies : messages (total/today/week/month), tokens (input/output/avg), costs
- ✅ Filtrage par session : header `X-Session-Id` + endpoint dédié
- ✅ Calculs validés : 100% cohérence API vs BDD
- ✅ Tests : 45/45 passants, mypy 0 erreur, ruff clean

**2. Timeline Service (nouveau)**
- Service `TimelineService` pour données temporelles
- Endpoints : `/timeline/activity`, `/timeline/costs`, `/timeline/tokens`
- Support périodes : 7d, 30d, 90d, 1y

**3. Database Migration**
- Migration `20251009_enrich_costs.sql` : colonnes `user_id`, `session_id` dans table `costs`
- Indexes optimisés pour filtrage rapide

### État Actuel Production
- **Révision active** : `emergence-app-metrics001`
- **Image** : `deploy-20251008-183707`
- **Features** : Prometheus Phase 3 actif (13 métriques)
- **URL** : https://emergence-app-47nct44nma-ew.a.run.app
- **Statut** : ✅ Stable, 100% traffic

---

## 🎯 Mission Codex

### Objectif Principal
Déployer une nouvelle révision Cloud Run contenant toutes les features Phase 3 validées.

### Actions Requises

#### 1. Pré-déploiement ✅ Validations
```bash
# 1.1 Vérifier statut git
git status
git log --oneline -5

# 1.2 Vérifier dernière révision prod
gcloud run revisions list \
  --service emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --limit 5

# 1.3 Confirmer image actuelle
gcloud run revisions describe emergence-app-metrics001 \
  --region europe-west1 \
  --project emergence-469005 \
  --format="value(spec.containers[0].image)"
```

#### 2. Build & Push Image
```bash
# 2.1 Générer timestamp
timestamp=$(date +%Y%m%d-%H%M%S)
echo "Building image: cockpit-phase3-$timestamp"

# 2.2 Build Docker (architecture Cloud Run)
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp \
  .

# 2.3 Push to Artifact Registry
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp

# 2.4 Sauvegarder tag pour rollback
echo "cockpit-phase3-$timestamp" > build_tag.txt
```

#### 3. Deploy Cloud Run
```bash
# 3.1 Deploy nouvelle révision
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --revision-suffix cockpit-phase3 \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi

# 3.2 Router 100% trafic vers nouvelle révision
gcloud run services update-traffic emergence-app \
  --region europe-west1 \
  --to-revisions emergence-app-cockpit-phase3=100
```

#### 4. Validation Post-Déploiement
```bash
# 4.1 Health check
curl -f https://emergence-app-47nct44nma-ew.a.run.app/api/health || echo "HEALTH CHECK FAILED"

# 4.2 Test cockpit metrics endpoint
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/dashboard/costs/summary | jq '.messages.total' || echo "METRICS ENDPOINT FAILED"

# 4.3 Test timeline endpoint
curl -s "https://emergence-app-47nct44nma-ew.a.run.app/api/dashboard/timeline/activity?period=7d" | jq 'length' || echo "TIMELINE ENDPOINT FAILED"

# 4.4 Vérifier Prometheus metrics
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep -c "concept_recall" || echo "PROMETHEUS METRICS FAILED"

# 4.5 Check logs récents
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app AND resource.labels.revision_name=emergence-app-cockpit-phase3" \
  --limit 20 \
  --format json \
  --project emergence-469005
```

#### 5. Documentation Post-Déploiement
```bash
# 5.1 Créer rapport déploiement
cat > docs/deployments/2025-10-09-deploy-cockpit-phase3.md << 'EOF'
# Déploiement Production - Cockpit Phase 3

**Date** : $(date +"%Y-%m-%d %H:%M CEST")
**Révision** : emergence-app-cockpit-phase3
**Image** : cockpit-phase3-$(cat build_tag.txt)

## Features Déployées
- Cockpit métriques enrichies (messages, tokens, costs avec moyennes)
- Timeline endpoints (activity, costs, tokens)
- Filtrage par session (X-Session-Id header)
- Database migration costs enrichie

## Validation
- Health check : ✅
- Metrics endpoint : ✅
- Timeline endpoints : ✅
- Prometheus metrics : ✅

## Commits Inclus
$(git log --oneline -10)
EOF

# 5.2 Mettre à jour docs/deployments/README.md
# Ajouter ligne dans tableau avec nouvelle révision

# 5.3 Mettre à jour AGENT_SYNC.md
# Ajouter section déploiement Phase 3
```

---

## 📊 Métriques de Succès

### Validation Technique
- [ ] Build Docker réussie (< 10 min)
- [ ] Push Artifact Registry OK
- [ ] Déploiement Cloud Run OK (révision active)
- [ ] Traffic routé 100% vers nouvelle révision

### Validation Fonctionnelle
- [ ] `/api/health` retourne 200 OK
- [ ] `/api/dashboard/costs/summary` retourne JSON avec métriques
- [ ] `/api/dashboard/timeline/activity` retourne array non vide
- [ ] `/api/metrics` contient métriques Prometheus (13+)

### Validation Performance
- [ ] Temps réponse `/api/dashboard/costs/summary` < 500ms
- [ ] Temps réponse `/api/health` < 100ms
- [ ] Aucune erreur dans logs (5 premières minutes)

---

## 🚨 Rollback Plan (si problème)

### Rollback Immédiat
```bash
# Router traffic vers révision précédente stable
gcloud run services update-traffic emergence-app \
  --region europe-west1 \
  --to-revisions emergence-app-metrics001=100
```

### Rollback Image
```bash
# Redéployer image précédente
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app@sha256:c1aa10d52884aab51516008511ad5b4c6b8d634c6406a9866aae2a939bcebc86 \
  --project emergence-469005 \
  --region europe-west1 \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5"
```

---

## 📝 Fichiers Importants

### Code Backend Modifié
- `src/backend/features/dashboard/timeline_service.py` (nouveau, 261 lignes)
- `src/backend/core/database/queries.py` (+175 lignes)
- `src/backend/features/dashboard/router.py` (+123 lignes endpoints timeline)
- `src/backend/core/database/migrations/20251009_enrich_costs.sql` (migration)

### Code Frontend Modifié
- `src/frontend/features/cockpit/cockpit-metrics.js` (intégration API métriques)

### Documentation
- `docs/passation.md` (entrée validation 2025-10-09)
- `docs/deployments/2025-10-09-activation-metrics-phase3.md` (validation complète)
- `NEXT_SESSION_PROMPT.md` (instructions pour prochaine session)
- `PROMPT_DEBUG_COCKPIT_METRICS.md` (détails validation)

### Config
- `env.yaml` (variables environnement, déjà en prod)
- `.dockerignore` (build optimisé)
- `Dockerfile` (multi-stage build)

---

## ⚠️ Notes Importantes

### Secrets
- **NE PAS** commiter secrets dans git
- Utiliser `--update-secrets` avec Secret Manager
- Vérifier `env.yaml` ne contient pas de clés API

### Base de Données
- Migration `20251009_enrich_costs.sql` **déjà appliquée** en local
- **IMPORTANT** : Vérifier migration appliquée en prod avant deploy
- Si migration manquante, l'appliquer via Cloud Run console ou SSH

### Tests
- Tests locaux : 45/45 passants ✅
- Qualité code : mypy 0 erreur, ruff clean ✅
- Validation API : 100% cohérence calculée ✅

### Monitoring
- Prometheus métriques déjà actives (13 métriques Phase 3)
- Dashboard Grafana disponible : `monitoring/grafana-dashboard-prometheus-phase3.json`
- Alertes configurables sur métriques coûts

---

## 🎯 Checklist Codex

Avant de commencer :
- [ ] Lire ce prompt en entier
- [ ] Vérifier accès gcloud (`gcloud config get-value project`)
- [ ] Vérifier Docker daemon actif (`docker ps`)
- [ ] Lire `docs/passation.md` entrée 2025-10-09
- [ ] Lire `AGENT_SYNC.md` pour contexte général

Pendant déploiement :
- [ ] Suivre les étapes 1-5 dans l'ordre
- [ ] Logger toutes commandes exécutées
- [ ] Capturer outputs pour rapport
- [ ] Surveiller logs Cloud Run pendant déploiement

Après déploiement :
- [ ] Créer rapport `docs/deployments/2025-10-09-deploy-cockpit-phase3.md`
- [ ] Mettre à jour `docs/deployments/README.md`
- [ ] Mettre à jour `AGENT_SYNC.md`
- [ ] Mettre à jour `docs/passation.md` avec entrée déploiement
- [ ] Commit tous changements : `git add -A && git commit -m "deploy: cockpit phase 3 production" && git push`

---

## 🚀 Commande Rapide (si tout OK)

```bash
# All-in-one deploy (à exécuter seulement si toutes validations pré-deploy OK)
timestamp=$(date +%Y%m%d-%H%M%S) && \
docker build --platform linux/amd64 -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp . && \
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp && \
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --revision-suffix cockpit-phase3 \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi && \
echo "cockpit-phase3-$timestamp" > build_tag.txt
```

---

**Bon déploiement, Codex ! 🚀**

**Rappel** : En cas de problème, rollback immédiat vers `emergence-app-metrics001` (révision stable actuelle).
