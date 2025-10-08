# Déploiement 2025-10-08 - Cloud Run Refresh

**Révision Cloud Run** : `emergence-app-00269-5qs`  
**Image Docker** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-064424`  
**Service URL** : https://emergence-app-486095406755.europe-west1.run.app  
**Commits Git** : `da5b625` (feat: harmonisation UI cockpit et hymne avec design system)  
**Date/Heure** : 2025-10-08 06:46 CEST

---

## 📋 Résumé des Changements livrés
- Mise en production des derniers correctifs UI (harmonisation cockpit et hymne) déjà présents sur `main`.
- Rafraîchissement de l'image pour aligner Cloud Run avec l'état actuel du dépôt (CSS margin fixes, monitoring stack).
- Aucun changement de configuration supplémentaire : variables d'environnement et secrets conservés tels quels.

---

## 🧪 Tests exécutés avant déploiement

### Frontend
- ✅ `npm run build` — succès (vite 7.1.2), aucun avertissement supplémentaire.

### Backend
- ⚠️ `python -m pytest` — échec pendant la collecte (`ImportError: cannot import name 'User' from backend.features.auth.models`). Problème préexistant sur la branche.
- ⚠️ `pwsh -File tests/run_all.ps1` — échec car identifiants smoke-tests non fournis (`Login failed for gonzalefernando@gmail.com`). Aucune régression liée au build.

> Les erreurs `pytest` et `tests/run_all.ps1` sont connues et documentées dans les sessions précédentes. Aucun test supplémentaire n'a été exécuté côté linters (`ruff`, `mypy`) pendant cette fenêtre.

---

## 🚀 Processus exécuté

```powershell
# Build
docker build --platform linux/amd64 `
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-064424 .

docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-064424

# Déploiement Cloud Run
gcloud run deploy emergence-app `
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251008-064424 `
  --platform managed --region europe-west1 --project emergence-469005 `
  --allow-unauthenticated
```

**Résultat** : révision `emergence-app-00269-5qs` en production (100 % du trafic).

---

## ✅ Vérifications post-déploiement
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/health` → 200 `{"status":"ok","message":"Emergence Backend is running."}`
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/metrics` → 200 `# Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.`
- ⚠️ Endpoint `/health` non exposé (comportement déjà connu, non bloquant).

Aucune QA UI manuelle effectuée dans cette passe.

---

## 📝 Documentation
- [x] Rapport de déploiement (`docs/deployments/2025-10-08-cloud-run-refresh.md`).
- [ ] QA post-déploiement à programmer si anomalies détectées.

---

## 🎯 Prochaines actions
1. Traiter les échecs `pytest` (import `User`) et rétablir l'exécution complète de `tests/run_all.ps1`.
2. Lancer une QA visuelle rapide (cockpit, hymne) pour confirmer l'alignement avec la branche `main`.
3. Mettre à jour les dashboards de monitoring si de nouvelles métriques sont disponibles.

---

**Agent** : Codex  
**Environnement** : Production Cloud Run (europe-west1)

