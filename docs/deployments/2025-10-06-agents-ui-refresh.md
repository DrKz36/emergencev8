# Déploiement 2025-10-06 - Agents & UI Refresh

**Révision Cloud Run** : `emergence-app-00268-9s8`
**Image Docker** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251006-060538`
**Service URL** : https://emergence-app-486095406755.europe-west1.run.app
**Commits Git** : `a6b1ee6`, `32e5382`, `67cbf32`, `00fe357`, `f6e50eb`, `61d8321`, `2a458df`
**Date/Heure** : 2025-10-06 06:07 CEST

---

## 📋 Résumé des Changements livrés
- Nouvelles personnalités ANIMA / NEO / NEXUS (commit `a6b1ee6`) alignées avec les scripts d'instructions récents.
- Optimisation navigation : sidebar & responsive mobile (commit `32e5382`) avec correctifs CSS.
- Module Documentation + refonte section Genèse (commits `00fe357`, `67cbf32`) pour le front landing.
- Hook d'instructions custom côté config (commit `f6e50eb`).
- Documentation synchronisée (commits `61d8321`, `2a458df`).
- Image construite depuis l'arbre de travail courant incluant les ajustements CSS (non encore commités).

---

## 🧪 Tests exécutés avant déploiement

### Frontend
- ✅ `npm run build` (vite 7.1.2) — succès avec warning importmap dans `index.html`.

### Backend
- ⚠️ `python -m pytest` — 77 tests OK / 7 erreurs (`tests/backend/features/test_memory_concept_search.py` : fixture `app` introuvable).
- ⚠️ `ruff check` — 28 erreurs E402/F401/F841 sur scripts legacy (`scripts/migrate_concept_metadata.py`, `src/backend/containers.py`, tests).
- ⚠️ `mypy src` — 12 erreurs de typage (`benchmarks`, `concept_recall`, `chat.service`, `memory.router`).
- ✅ `pwsh -File tests/run_all.ps1` — smoke tests API & upload OK (suppression doc ID=1 retourne 404 attendu).

> Les échecs `pytest`/`ruff`/`mypy` sont préexistants et devront être traités séparément avant la prochaine validation architecte.

---

## 🚀 Processus exécuté
```powershell
# Build
docker build --platform linux/amd64 `
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251006-060538 .

docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251006-060538

# Déploiement Cloud Run
gcloud run deploy emergence-app `
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251006-060538 `
  --platform managed --region europe-west1 --project emergence-469005 `
  --allow-unauthenticated --quiet
```

**Résultat** : Révision `emergence-app-00268-9s8` en production (100% trafic).

---

## ✅ Vérifications post-déploiement
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/health` → 200 `{ "status": "ok" }`.
- ⚠️ `https://emergence-app-486095406755.europe-west1.run.app/health` → 404 `{"detail":"Not Found"}` (endpoint non exposé côté app, conforme à l'existant).
- ✅ `https://emergence-app-486095406755.europe-west1.run.app/api/metrics` → 200 `# Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.`

Aucune vérification manuelle UI effectuée (QA à planifier).

---

## 📝 Documentation
- [x] Ce rapport (`docs/deployments/2025-10-06-agents-ui-refresh.md`).
- [ ] QA post-déploiement à compléter si anomalies détectées.

---

## 🎯 Prochaines actions
1. Corriger les erreurs `pytest` / `ruff` / `mypy` listées.
2. Exécuter une QA front/WS sur la révision `00268-9s8` (conversations, documentation, personnalités).
3. Surveiller les logs Cloud Run (`severity>=ERROR`) pendant la fenêtre post-déploiement.

---

**Agent** : Codex (local)
**Environnement** : Production Cloud Run (europe-west1)
