# Déploiement 2025-10-08 — Cloud Run Révision 00274

**Révision Cloud Run** : `emergence-app-00274-m4w`  
**Image Docker** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-121131`  
**Digest** : `sha256:5b52fbbf9f5dd397cfd39b22c2e85a82a01d1682c3a0770fc54b22c8512d926f`  
**Service URL** : https://emergence-app-486095406755.europe-west1.run.app  
**Commits Git** : `2bdbde1`, `4f30be9`, `69f7f50`, `c7079f0`, `30d09e8`, `b5a0caa`  
**Date/Heure** : 2025-10-08 12:11 CEST (10:11 UTC)

---

## 📋 Résumé des changements livrés
- Mise en production de la **Phase 2 Performance** : agent `neo_analysis` (GPT-4o-mini), cache mémoire in-memory (TTL 1h, LRU 100 entrées) et parallélisation du round 1 des débats.
- Enrichissement mémoire temporelle (horodatages naturels injectés dans le RAG) livré par `MemoryContextBuilder`.
- Documentation Phase 2 (prompt + guide build/deploy) incluse dans l'image afin d'aligner le code et les playbooks de production.
- Aucun changement de configuration Cloud Run ; même paramètres environnement qu'en révision 00270.

---

## 🧪 Tests exécutés avant déploiement
- ⚠️ `pwsh -File scripts/sync-workdir.ps1` → échec sur `tests/run_all.ps1` (login smoke-tests impossible sans variables `EMERGENCE_SMOKE_EMAIL/EMERGENCE_SMOKE_PASSWORD`). Dette connue.
- ↪️ Pas d'autres suites relancées (build & déploiement uniquement ; code identique aux commits listés ci-dessus).

---

## 🚀 Processus exécuté

```powershell
$timestamp = "20251008-121131"

# Build & push Docker
docker build --platform linux/amd64 `
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp .

docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp

# Déploiement Cloud Run
gcloud run deploy emergence-app `
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp `
  --platform managed --region europe-west1 --project emergence-469005 `
  --allow-unauthenticated
```

**Résultat** : révision `emergence-app-00274-m4w` en production (100 % du trafic).

---

## ✅ Vérifications post-déploiement
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/health` → `200 {"status":"ok","message":"Emergence Backend is running."}`
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/metrics` → `200` (`Metrics disabled` message attendu).
- ✅ `gcloud run revisions list` → confirme `emergence-app-00274-m4w` active, 100 % trafic ; précédentes révisions archivées (`00270-00273`).
- 🔍 Logs Cloud Run à monitorer : `MemoryAnalyzer` (neo_analysis + cache HIT/SAVED) et latence débats (`debate:`) pour valider les gains Phase 2.

---

## 📝 Documentation & suivis
- [x] Rapport de déploiement (`docs/deployments/2025-10-08-cloud-run-revision-00274.md`).
- [x] AGENT_SYNC.md (section déploiement mise à jour).
- [x] Passation `docs/passation.md` (entrée session Codex).
- [ ] Collecte métriques réelles post-déploiement (cache hit rate, latence analyses, latence débats).

---

## 🎯 Prochaines actions
1. Surveiller les logs Cloud Run (`jsonPayload.message=~"MemoryAnalyzer"` et `"Cache (HIT|SAVED)"`) pour confirmer le comportement attendu.
2. Mesurer les latences réelles (analyse mémoire <2s, round 1 débats ~3s) et consigner dans un rapport Phase 2 résultats.
3. Fournir des identifiants smoke-tests dédiés pour rétablir `tests/run_all.ps1` dans le script de synchronisation.

---

**Agent** : Codex  
**Environnement** : Production Cloud Run (europe-west1)
