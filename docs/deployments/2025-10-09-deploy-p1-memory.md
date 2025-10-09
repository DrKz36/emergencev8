# Déploiement Phase P1 Mémoire – Async queue & préférences

- **Date** : 2025-10-09 09:55 CEST
- **Agent** : Codex (CLI)
- **Révision Cloud Run** : `emergence-app-p1memory`
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-p1-20251009-094822`
- **Digest** : `sha256:883d85d093cab8ae2464d24c14d54e92b65d3c7da9c975bcb1d65b534ad585b5`
- **Service URL** : https://emergence-app-47nct44nma-ew.a.run.app
- **Alias** : https://emergence-app-486095406755.europe-west1.run.app
- **Objectif** : publier la phase P1 (MemoryTaskQueue + extraction préférences + instrumentation) sur Cloud Run et transférer 100 % du trafic.

---

## 1. Préparation locale & QA

| Type | Commande | Résultat |
|------|----------|----------|
| Frontend | `npm run build` | ✅ vite 7.1.2 |
| Backend | `.venv\Scripts\python.exe -m pytest` | ✅ 165 tests |
| Lint | `.venv\Scripts\ruff.exe check` | ✅ |
| Typage | `.venv\Scripts\python.exe -m mypy src` | ✅ |
| Note | `tests/run_all.ps1` | ⚠️ ignoré (login smoke prod requis) |

Correctif mineur `mypy`: `MemoryAnalyzer.analyze_session_async` accepte désormais `callback: Optional[Callable[..., Any]]`.

---

## 2. Build & push Docker

```powershell
# Tag mis à jour via build_tag.txt
$tag = "deploy-p1-20251009-094822"

docker build --platform linux/amd64 `
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:$tag .

docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:$tag

gcloud artifacts docker images list \
  europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app \
  --include-tags --filter="tags=$tag"
```

Résultat : image poussée (digest `sha256:bee6bd66e0a300b9…`) et visible dans Artifact Registry.

---

## 3. Déploiement & routage

```powershell
# Déploiement révision p1memory
gcloud run deploy emergence-app `
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:$tag `
  --project emergence-469005 `
  --region europe-west1 `
  --platform managed `
  --allow-unauthenticated `
  --revision-suffix p1memory `
  --timeout 300 --memory 2Gi --cpu 2 --max-instances 10 `
  --env-vars-file env.yaml

# Trafic à 100 % sur la nouvelle révision
gcloud run services update-traffic emergence-app `
  --region europe-west1 `
  --project emergence-469005 `
  --to-revisions emergence-app-p1memory=100
```

Logs GCP confirment `MemoryTaskQueue started with 2 workers` et `Ready=True` pour `emergence-app-p1memory`.

---

## 4. Post-déploiement & métriques

- `Invoke-RestMethod https://…/api/health` → `{"status":"ok"}` (≈210 ms)
- `GET /api/memory/tend-garden` (thread ciblé) : succès, `consolidated_sessions=1`
- `GET /api/metrics` : compteurs `memory_analysis_*` et `concept_recall_*` exposés
- `gcloud logging read --limit 5` : aucune erreur 5xx, traces de la file asynchrone

### Focus métriques préférences

- Les compteurs `memory_preferences_*` attendus ne figurent pas encore dans `/api/metrics`.
- Hypothèse : le module `preference_extractor` n’est pas importé côté runtime tant qu’aucun worker ne déclenche l’extracteur.
- Action suivie : lancer un scénario QA complet (`qa_metrics_validation.py`) pour vérifier l’activation et, si besoin, instrumenter `MemoryGardener` directement.

---

## 5. Actions recommandées

1. Exécuter `python qa_metrics_validation.py --base-url … --trigger-memory` avec credentials prod pour déclencher les métriques `memory_preferences_*`.
2. Surveiller les logs `backend.features.memory.task_queue` durant 24 h (erreurs worker).
3. Ajouter un test d’intégration Prometheus ciblant `memory_preferences_extracted_total` (backend ou QA script).
4. Documenter la procédure QA dans `docs/monitoring/prometheus-phase3-setup.md` (ajout P1).

---

## 6. Références

- `build_tag.txt` → `deploy-p1-20251009-094822`
- `gcloud run services describe emergence-app --region europe-west1`
- `gcloud logging read --project emergence-469005 --limit 20 "textPayload:MemoryTaskQueue"`
- `PROMPT_CODEX_DEPLOY_P1.md`

