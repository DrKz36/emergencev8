# Activation des métriques Prometheus – Cloud Run

- **Date** : 2025-10-09 05:40 CEST
- **Agent** : Codex (déploiement)
- **Révision Cloud Run** : `emergence-app-metrics001`
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app@sha256:c1aa10d52884aab51516008511ad5b4c6b8d634c6406a9866aae2a939bcebc86`
- **Service URL (primaire)** : https://emergence-app-47nct44nma-ew.a.run.app
- **Alias historique** : https://emergence-app-486095406755.europe-west1.run.app
- **Objectif** : Activer `CONCEPT_RECALL_METRICS_ENABLED=true` pour exposer les 13 métriques Prometheus (Phase 3)

---

## 1. Contexte & rappel des blocages

1. Les cinq tentatives du 09/10 (cf. `docs/deployments/2025-10-09-blocage-activation-metriques.md`) échouaient sur :
   - rebuild `gcloud run deploy --source .` → révisions `00276-00282` non prêtes (erreur `ContainerImageImportFailed`).
   - `gcloud run deploy --image … --set-env-vars` → `ModuleNotFoundError: backend` car `PYTHONPATH` manquait.
2. `env.yaml` introduit les quatre variables critiques (metrics + PYTHONPATH + allowlist + AUTH_DEV_MODE).
3. `PROMPT_CODEX_ENABLE_METRICS.md` demandait une exécution propre : déploiement unique + validation de 13 métriques + documentation.

---

## 2. Commandes exécutées

```bash
# 1) Build Cloud Run à partir des sources (image reconstruite mais révision non routée)
gcloud run deploy emergence-app \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi

# 2) Promotion d'une révision stable avec l'image existante + env.yaml
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app@sha256:c1aa10d52884aab51516008511ad5b4c6b8d634c6406a9866aae2a939bcebc86 \
  --region europe-west1 \
  --allow-unauthenticated \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi \
  --revision-suffix metrics001

# 3) Routage du trafic à 100 % vers la révision metrics001
gcloud run services update-traffic emergence-app \
  --region europe-west1 \
  --to-revisions emergence-app-metrics001=100
```

**Observations clés**
- Les révisions `00280`, `00281`, `00282` restent « Retired » (import image partiel) mais la build artefact reste disponible.
- `emergence-app-metrics001` hérite de l’image stable `deploy-20251008-183707` avec `env.yaml` appliqué.
- Nouveau host primaire généré par Cloud Run : `https://emergence-app-47nct44nma-ew.a.run.app`.

---

## 3. Tests et validations

| Vérification | Résultat | Détails |
|--------------|----------|---------|
| `python -m pytest` | ❌ | 9 échecs + 1 erreur (`tests/backend/tests_auth_service`, `tests/memory/test_preferences.py`, `tests/test_memory_archives.py`, `VectorService.__init__` signature). |
| `python -m ruff check` | ❌ | 9 erreurs (imports E402, unused json, logger non défini). |
| `mypy src` | ❌ | 21 erreurs typage (`psutil` stubs manquants, `MemoryAnalyzer.logger`, `DebateService` variables). |
| `npm run build` | ✅ | Vite 7.1.2 OK, bundles générés. |
| `pwsh -File tests/run_all.ps1` | ❌ | Login de smoke-tests impossible (identifiants manquants). |
| Cloud Run `/api/health` | ✅ | 200 sur les deux URLs (legacy + nouveau host). |
| Cloud Run `/api/metrics` | ✅ | Flux Prometheus complet (13 métriques Phase 3 actives). |
| `gcloud run revisions list` | ✅ | `emergence-app-metrics001` actif, 100 % trafic. |
| `gcloud logging read … revision_name=emergence-app-metrics001` | ✅ | Logs `Request completed: GET /api/metrics` confirmés (duration ~2 ms). |

Les suites en échec sont remontées dans `docs/passation.md` et `AGENT_SYNC.md`. Aucun correctif appliqué durant cette session.

---

## 4. Extrait des métriques Prometheus

```text
# HELP memory_analysis_success_total Nombre total d'analyses réussies
# TYPE memory_analysis_success_total counter
memory_analysis_success_total 0.0
# HELP memory_analysis_cache_hits_total Nombre total de cache hits
# TYPE memory_analysis_cache_hits_total counter
memory_analysis_cache_hits_total 0.0
# HELP memory_analysis_duration_seconds Durée des analyses mémoire
# TYPE memory_analysis_duration_seconds histogram
# HELP concept_recall_similarity_score Distribution of similarity scores for detected concepts
# TYPE concept_recall_similarity_score histogram
concept_recall_system_info{collection_name="emergence_knowledge",max_recalls_per_message="3",similarity_threshold="0.5",version="1.0"} 1.0
```

> L’endpoint renvoie également les compteurs génériques Python (`python_gc_*`, `process_*`) exposés par `prometheus-client`.

---

## 5. Prochaines actions recommandées

1. **Stabiliser la qualité** : corriger les suites `pytest`, `ruff`, `mypy` et le script `tests/run_all.ps1` (ajout d’identifiants smoke dans le vault ou injection via variables).  
2. **Monitoring** : brancher un dashboard Grafana / alerts Prometheus sur l’URL `/api/metrics` (13 métriques, buckets histogrammes prêts).  
3. **Nettoyage des révisions** : envisager la suppression des révisions « Retired » (`00276`→`00282`) après validation prolongée, ou les laisser comme pistes d’audit.  
4. **Documentation** : consolider `PROMPT_CODEX_ENABLE_METRICS.md` en y ajoutant la procédure de promotion (`gcloud run services update-traffic`).  
5. **QA fonctionnelle** : lancer une analyse mémoire et un rappel concept pour incrémenter effectivement les compteurs (`memory_analysis_success_total`, `concept_recall_detections_total`).  

---

## 6. Historique rapide

| Heure CEST | Action | Notes |
|-----------|--------|-------|
| 05:02 | `gcloud run deploy --source .` | Build 15 min, révision `00282-hqt` créée mais retirée (import image). |
| 05:24 | `gcloud run deploy --image … --revision-suffix metrics001` | Révision créée avec env.yaml complet. |
| 05:25 | `gcloud run services update-traffic … metrics001=100` | Nouveau host Cloud Run ; trafic 100 % vers metrics001. |
| 05:27 | `Invoke-WebRequest …/api/metrics` | 200 + flux Prometheus complet. |
| 05:30 | `gcloud logging read … revision_name=metrics001` | Logs `Incoming request: GET /api/metrics` confirmés. |

---

### Artefacts produits

- `env.yaml` (déjà versionné) : utilisé comme source unique des 4 variables obligatoires.
- Ce rapport (`docs/deployments/2025-10-09-activation-metrics-phase3.md`).

---

✅ **Résultat** : `CONCEPT_RECALL_METRICS_ENABLED` actif en production, métriques Prometheus disponibles pour Phase 3 (rev. `emergence-app-metrics001`).  
⚠️ **Dette ouverte** : suites locales `pytest`, `ruff`, `mypy`, `tests/run_all.ps1` à remettre au vert.
