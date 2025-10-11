# Historique des Déploiements Cloud Run

Ce dossier contient l'historique chronologique des déploiements de l'application Emergence sur Google Cloud Run.

## ⚠️ Changement d'Architecture - 2025-10-11

**Migration vers conteneur unique sans canary**

- **Avant** : Services multiples (`emergence-app`, `emergence-app-canary`, `emergence-app-clean`)
- **Maintenant** : Un seul service `emergence-app` (conteneur principal-source)
- **Impact** : Déploiement simplifié, pas de split de trafic, rollback via les 3 dernières révisions conservées
- **Nettoyage effectué** :
  - Services supprimés : `emergence-app-canary`, `emergence-app-clean`
  - Révisions nettoyées : 89 anciennes révisions supprimées
  - Révisions conservées : 3 dernières actives (00297-6pr, 00350-wic, 00348-rih)

## Structure des Documents

Chaque déploiement est documenté avec :
- **Révision Cloud Run** et tag image Docker
- **Commits Git** inclus dans le déploiement
- **Résumé des changements** (features, fixes, optimisations)
- **Tests de validation** effectués
- **Processus de déploiement** (commandes Docker/gcloud)
- **Métriques** et impact (si applicable)
- **Points de vérification** post-déploiement

## Déploiements Récents

| Date | Révision | Image Tag | Description | Statut |
|------|----------|-----------|-------------|--------|
| 2025-10-10 | `emergence-app-p1-p0-20251010-040147` | `p1-p0-20251010-040147` | Phase P1.2 + P0 (préférences persistées + consolidation threads archivés) ([rapport](2025-10-10-deploy-p1-p0.md)) | ✅ Active (100%) |
| 2025-10-09 | `emergence-app-p1memory` | `deploy-p1-20251009-094822` | Phase P1 mémoire (queue async, préférences, instrumentation) ([rapport](2025-10-09-deploy-p1-memory.md)) | ✅ Active (100%) |
| 2025-10-09 | `emergence-app-phase3b` | `cockpit-phase3-20251009-073931` | Fix timeline SQL + redeploy cockpit Phase 3 ([rapport](2025-10-09-deploy-cockpit-phase3.md)) | ✅ Active (100%) |
| 2025-10-09 | `emergence-app-metrics001` | `deploy-20251008-183707` | Activation `CONCEPT_RECALL_METRICS_ENABLED` + routage 100 % (Prometheus Phase 3) ([rapport](2025-10-09-activation-metrics-phase3.md)) | ✅ Active (100%) |
| 2025-10-08 | `emergence-app-00275-2jb` | `deploy-20251008-183707` | Rebuild image Phases 2 & 3 + redeploy Cloud Run (health + metrics OK) ([rapport](2025-10-08-cloud-run-revision-00275.md)) | ⏸️ Archived |
| 2025-10-08 | `emergence-app-00274-m4w` | `deploy-20251008-121131` | **Phase 2 Performance** en production (neo_analysis, cache mémoire, débats parallèles) ([rapport](2025-10-08-cloud-run-revision-00274.md)) | ⏸️ Archived |
| 2025-10-08 | `emergence-app-00270-zs6` | `deploy-20251008-082149` | Cloud Run refresh (menu mobile confirmé) | ⏸️ Archived |
| 2025-10-08 | `emergence-app-00269-5qs` | `deploy-20251008-064424` | Cloud Run refresh (harmonisation UI cockpit/hymne) | ⏸️ Archived |
| 2025-10-06 | `emergence-app-00268-9s8` | `deploy-20251006-060538` | Agents & UI refresh (personnalités, module documentation, responsive) | ⏸️ Archived |
| 2025-10-05 | `emergence-app-00266-jc4` | `deploy-20251005-123837` | Corrections audit (13 fixes, score 87.5→95/100) | ⏸️ Archived |
| 2025-10-04 | `emergence-app-00265-xxx` | `deploy-20251004-205347` | Ajout système métriques + Settings module | ⏸️ Archived |

## Convention de Nommage

### Images Docker
Format : `deploy-YYYYMMDD-HHMMSS`
Exemple : `deploy-20251005-123837`

### Révisions Cloud Run
Format auto-généré : `emergence-app-00XXX-XXXXX`
Exemple : `emergence-app-00266-jc4`

### Documents
Format : `YYYY-MM-DD-description-courte.md`
Exemple : `2025-10-05-audit-fixes-deployment.md`

## Architecture de Déploiement

**Stratégie actuelle** : Conteneur unique sans canary

- **Service unique** : `emergence-app` (conteneur principal-source)
- **Pas de canary** : Toute nouvelle révision est déployée avec 100% du trafic
- **Gestion des révisions** : Conservation automatique des 3 dernières révisions fonctionnelles
- **Rollback simple** : Basculer vers l'une des 3 révisions conservées en cas de problème

## Processus de Déploiement Standard

```bash
# 1. Validation locale
npm run build
pytest tests/backend/ -v

# 2. Commit + Push
git add -A
git commit -m "feat: description"
git push origin main

# 3. Build Docker
timestamp=$(date +%Y%m%d-%H%M%S)
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp .

# 4. Push Registry
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp

# 5. Deploy Cloud Run sur conteneur unique
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp \
  --platform managed \
  --region europe-west1 \
  --project emergence-469005 \
  --allow-unauthenticated

# 6. Vérifications
gcloud run services list --platform=managed  # Doit montrer uniquement emergence-app
gcloud run revisions list --service emergence-app --region europe-west1 --limit 3  # Max 3 révisions

# 7. Documenter
# Créer docs/deployments/YYYY-MM-DD-description.md
# Mettre à jour docs/passation.md
# Mettre à jour AGENT_SYNC.md
```

## Rollback Procédure

En cas de problème avec une nouvelle révision :

```bash
# Lister les révisions conservées (max 3)
gcloud run revisions list --service emergence-app \
  --region europe-west1 --project emergence-469005

# Rollback vers une révision précédente
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00XXX-yyy=100 \
  --region europe-west1 --project emergence-469005
```

> **Note** : Seules les 3 dernières révisions fonctionnelles sont disponibles pour le rollback. Planifiez vos déploiements en conséquence.

## Monitoring Post-Déploiement

### Logs Cloud Run
```bash
gcloud run services logs read emergence-app \
  --region europe-west1 --project emergence-469005 --limit 100
```

### Métriques
- **Prometheus** : https://emergence-app-486095406755.europe-west1.run.app/api/metrics
- **Health** : https://emergence-app-486095406755.europe-west1.run.app/health
- **Cloud Console** : https://console.cloud.google.com/run/detail/europe-west1/emergence-app

### Alertes à Surveiller
- Erreurs 5xx > 1% des requêtes
- Latence p95 > 2s
- Utilisation mémoire > 80%
- Cold start > 10s

## 📚 Documents Phase 2 & 3 (2025-10-08)

### Documentation Complète
- 📊 **[2025-10-08-phase2-perf.md](2025-10-08-phase2-perf.md)** - Phase 2 Optimisations Performance
- 📊 **[2025-10-08-phase2-logs-analysis.md](2025-10-08-phase2-logs-analysis.md)** - Analyse logs + fix OpenAI
- 📈 **[2025-10-08-phase3-monitoring.md](2025-10-08-phase3-monitoring.md)** - Phase 3 Métriques Prometheus
- 🎯 **[PHASES_RECAP.md](PHASES_RECAP.md)** - Récapitulatif Phases 2 & 3 + guide déploiement
- 🚀 **[../../CODEX_BUILD_DEPLOY_PROMPT.md](../../CODEX_BUILD_DEPLOY_PROMPT.md)** - Prompt Codex pour build/deploy

### Phase 2 : Optimisations Performance
1. **Agent neo_analysis** : GPT-4o-mini pour analyses mémoire (latence -43%, coût -40%)
2. **Cache in-memory** : Résumés sessions (TTL 1h, max 100 entrées)
3. **Débats parallèles** : Round 1 asyncio.gather (latence -40%)
4. **Fix OpenAI prompt** : Ajout mot "json" requis par API (nov 2024+)

### Phase 3 : Monitoring Prometheus
1. **13 métriques exposées** via `/api/metrics`
2. **5 types** : Success, Failure, Cache, Latency, Size
3. **Dashboards Grafana** suggérés (5 panels)
4. **Alertes** Prometheus configurables

### Commits Phase 2 & 3
- `611f06e` fix: prompt OpenAI neo_analysis - ajout mot 'json' requis par API
- `11ac853` feat(phase3): add Prometheus metrics for MemoryAnalyzer monitoring
- `dcffd45` docs: récapitulatif complet Phases 2 & 3 - guide déploiement
- `0ff5edd` docs: prompt complet pour Codex - build & deploy Phase 3

### Validation post-deploy
Chercher dans logs Cloud Run :
```bash
# Analyses mémoire avec neo_analysis (Phase 2)
gcloud logging read "jsonPayload.message=~'neo_analysis'" --limit 50

# Cache HIT/MISS (Phase 2)
gcloud logging read "jsonPayload.message=~'Cache (HIT|SAVED)'" --limit 50

# Métriques Prometheus (Phase 3)
curl https://[APP_URL]/api/metrics | grep memory_analysis
```

Métriques cibles :
- **Phase 2** : Latence analyses <4s, Cache hit >40%, neo_analysis 100% succès
- **Phase 3** : 13 métriques exposées, compteurs incrémentent, histogrammes OK

---

## Checklist Pré-Déploiement

- [ ] Tests backend passent (`pytest`)
- [ ] Tests frontend passent (`npm run build`)
- [ ] Documentation mise à jour (si changements d'API)
- [ ] Variables d'environnement vérifiées (.env.production)
- [ ] Secrets Cloud Run à jour (si nécessaire)
- [ ] Passation complétée ([docs/passation.md](../passation.md))
- [ ] AGENT_SYNC.md mis à jour
- [ ] Vérification : aucun autre service canary ou test actif

## Checklist Post-Déploiement

- [ ] Révision déployée avec succès (100% trafic)
- [ ] Vérification : un seul service `emergence-app` actif
- [ ] Vérification : maximum 3 révisions conservées
- [ ] Health check OK (`/health` returns 200)
- [ ] Logs sans erreurs critiques (5 premières minutes)
- [ ] Métriques Prometheus exposées (`/api/metrics`)
- [ ] Tests fumée endpoints critiques
- [ ] Document déploiement créé
- [ ] Passation mise à jour
- [ ] Notification équipe (si applicable)

---

**Projet** : Emergence V8
**Cloud Provider** : Google Cloud Platform
**Service** : Cloud Run (europe-west1)
**Registry** : Artifact Registry (europe-west1-docker.pkg.dev)
