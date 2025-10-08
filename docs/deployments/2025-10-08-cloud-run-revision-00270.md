# Déploiement 2025-10-08 — Cloud Run Révision 00270

**Révision Cloud Run** : `emergence-app-00270-zs6`  
**Image Docker** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-082149`  
**Service URL** : https://emergence-app-486095406755.europe-west1.run.app  
**Commits Git** : `b45cfd8` (docs: mise à jour AGENT_SYNC.md - session fix navigation menu mobile)  
**Date/Heure** : 2025-10-08 08:22 CEST

---

## 📋 Résumé des Changements livrés
- Rafraîchissement de l'image Docker depuis `main` pour aligner Cloud Run sur le dernier état documenté (corrections navigation mobile déployées précédemment + synchronisation AGENT_SYNC).
- Aucun changement de configuration ou de secrets ; même surface fonctionnelle que la révision 00269.
- Objectif principal : générer une nouvelle révision Cloud Run confirmant le correctif menu mobile et garder la documentation de déploiement à jour.

---

## 🧪 Tests exécutés avant déploiement

### Frontend
- ✅ `npm run build` — succès (vite 7.1.2), bundle généré sans nouveaux avertissements.

### Backend
- ⚠️ `python -m pytest` — échec collecte (`ModuleNotFoundError: No module named 'backend'` + `ModuleNotFoundError: No module named 'pytest_asyncio'`). Problème existant sur la branche.
- ⚠️ `python -m ruff check` — 52 erreurs (imports hors tête de fichier, imports inutilisés, variables non utilisées). Dette connue.
- ⚠️ `python -m mypy src` — 27 erreurs (types `BenchmarksRepository`, `AuthService`, `MemoryGardener`, `ChatService`, etc.).
- ⚠️ `pwsh -File tests/run_all.ps1` — échec login smoke-tests (`Login failed for gonzalefernando@gmail.com`). Identifiants non fournis.

> Tous les échecs étaient déjà signalés lors des sessions précédentes ; aucun nouveau test n'a été ajouté dans cette passe.

---

## 🚀 Processus exécuté

```powershell
$timestamp = "20251008-082149"

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

**Résultat** : révision `emergence-app-00270-zs6` en production (100 % du trafic).

---

## ✅ Vérifications post-déploiement
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/health` → 200 `{"status":"ok","message":"Emergence Backend is running."}`
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/metrics` → 200 (payload Prometheus exposé).
- ✅ `gcloud run revisions list` — confirme `emergence-app-00270-zs6` active, 100 % trafic.
- ⏱️ QA UI manuelle non menée (à planifier si besoin).

---

## 📝 Documentation
- [x] Rapport de déploiement (`docs/deployments/2025-10-08-cloud-run-revision-00270.md`).
- [ ] QA complémentaire à prévoir si des anomalies front sont détectées.

---

## 🎯 Prochaines actions
1. Résoudre les erreurs `pytest` / `ruff` / `mypy` pour rétablir une suite CI saine.
2. Fournir des identifiants smoke-tests afin de réactiver `tests/run_all.ps1`.
3. Effectuer une QA mobile ciblée pour confirmer définitivement les correctifs du menu hamburger.

---

**Agent** : Codex  
**Environnement** : Production Cloud Run (europe-west1)
