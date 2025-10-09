# Déploiement 2025-10-08 — Cloud Run Révision 00275

**Révision Cloud Run** : `emergence-app-00275-2jb`  
**Image Docker** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-183707`  
**Digest** : `sha256:b82dcc592db5739edf8671c0a5e2759a13c5bf653620b4106e3a322afa41e536`  
**Service URL** : https://emergence-app-486095406755.europe-west1.run.app  
**Commits Git** : `67f2d5a`, `0ff5edd`, `dcffd45`, `11ac853`, `611f06e`  
**Date/Heure** : 2025-10-08 18:37 CEST (16:37 UTC)

---

## 📋 Résumé des changements livrés
- Rebuild complet de l'image de production avec le tag `deploy-20251008-183707` depuis l'état `main` (Phases 2 & 3).
- Déploiement Cloud Run `emergence-app-00275-2jb`, remplaçant la révision `00274-m4w`.
- Vérification manuelle des endpoints `/api/health` et `/api/metrics`.

---

## 🧪 Tests exécutés avant/après déploiement
- ⚠️ `pwsh -File scripts/sync-workdir.ps1` → échec attendu (`tests/run_all.ps1` nécessite les variables `EMERGENCE_SMOKE_EMAIL` / `EMERGENCE_SMOKE_PASSWORD`).
- ✅ `curl https://emergence-app-486095406755.europe-west1.run.app/api/health` → `200 {"status":"ok","message":"Emergence Backend is running."}`
- ✅ `curl https://emergence-app-486095406755.europe-west1.run.app/api/metrics` → `# Metrics disabled...` (comportement attendu tant que Prometheus n'est pas activé).
- ✅ `gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005` → confirme `00275-2jb` active à 100 % du trafic.

---

## 🚀 Processus exécuté

```powershell
$timestamp = "20251008-183707"
$image = "europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp"

# Build & push Docker
docker build --platform linux/amd64 `
  -t $image .

docker push $image

# Déploiement Cloud Run
gcloud run deploy emergence-app `
  --image $image `
  --platform managed `
  --region europe-west1 `
  --project emergence-469005 `
  --allow-unauthenticated
```

---

## ✅ Vérifications post-déploiement
- ✅ Nouvelle révision `emergence-app-00275-2jb` active (100 % trafic).
- ✅ Health check `/api/health` → 200.
- ✅ Endpoint `/api/metrics` atteint (metrics désactivées tant que la variable d'environnement reste à `false`).
- ⏳ Surveillance recommandée : logs Cloud Run `MemoryAnalyzer`, `Cache (HIT|SAVED)` et `debate` pour confirmer les gains Phase 2, collecte métriques Phase 3 dès activation Prometheus.

---

## 📝 Documentation & suivis
- [x] `AGENT_SYNC.md` (section déploiement + session Codex) mis à jour.
- [x] `docs/deployments/README.md` (tableau historique) mis à jour.
- [x] `docs/passation.md` (entrée session Codex) ajoutée.
- [ ] Rapport métriques Phase 2/3 à compléter après collecte production.

---

**Agent** : Codex  
**Environnement** : Production Cloud Run (europe-west1)
