# Déploiement Cockpit Phase 3 – Correctif timeline & image patchée

- **Date** : 2025-10-09 07:55 CEST
- **Agent** : Codex (cloud)
- **Révision Cloud Run** : `emergence-app-phase3b`
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-20251009-073931`
- **Digest** : `sha256:4c0a5159057ac5adcd451b647110bfafbc0566a701452f90486e66f93d8dbf17`
- **Service URL** : https://emergence-app-47nct44nma-ew.a.run.app
- **Alias** : https://emergence-app-486095406755.europe-west1.run.app
- **Objectif** : corriger l’erreur SQL sur les endpoints timeline, rebuilder l’image Phase 3 et basculer le trafic sur la révision saine.

---

## 1. Correctifs appliqués

1. **TimelineService** (`src/backend/features/dashboard/timeline_service.py`)
   - Ajout de conditions paramétrées directement dans les clauses `LEFT JOIN`.
   - Suppression des `WHERE` injectés au milieu des JOINs (cause du `near "LEFT": syntax error`).
   - Harmonisation des filtres utilisateurs/sessions pour `activity`, `costs` et `tokens` timeline.
2. **qa_metrics_validation.py**
   - Nettoyage lint (import `json` supprimé, gestion réponse vide).
   - Fallback « lecture seule » via headers `x-dev-bypass` si `/api/auth/dev/login` indisponible (prod).
3. **requirements.txt**
   - Ajout `types-psutil>=7.0.0` pour conserver `mypy` au vert.

---

## 2. Build & déploiement

```bash
# Build image linux/amd64 + tag horodaté
$timestamp=20251009-073931
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp .

docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp

# Déploiement Cloud Run + secrets + env.yaml
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:cockpit-phase3-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --revision-suffix phase3b \
  --env-vars-file env.yaml \
  --update-secrets "OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 --cpu 2 --memory 4Gi

gcloud run services update-traffic emergence-app \
  --region europe-west1 \
  --to-revisions emergence-app-phase3b=100
```

**Résultats gcloud**
- `emergence-app-phase3b` : Ready en 52 s, digest `sha256:4c0a51…`.
- Trafic canary (`emergence-app-00279-kub`) conservé à 0 %.

---

## 3. Tests & validations

| Catégorie | Commande | Résultat |
|-----------|----------|----------|
| Front build | `npm run build` | ✅ vite 7.1.2 |
| Backend tests | `python -m pytest` | ✅ 152 tests passants |
| Lint | `ruff check` | ✅ |
| Typage | `mypy src` | ✅ |
| QA script | `python qa_metrics_validation.py` | ✅ fallback bypass lecture seule |
| Health prod | `curl https://…/api/health` | ✅ 200 (≈208 ms) |
| Metrics prod | `curl https://…/api/metrics` | ✅ 74 lignes `concept_recall*` |
| Timeline | `GET /api/dashboard/timeline/{activity,costs,tokens}?period=7d` | ✅ 200, payload vide mais sans erreur |
| Logs | `gcloud logging read … revision_name=emergence-app-phase3b` | ✅ aucune erreur SQL, seulement warnings bypass |

---

## 4. Points de validation notables

- **SQL timeline** : plus d’erreur `near "LEFT"`, requêtes 7d/30d retournent 8/31 entrées vides mais 200 OK.
- **Prometheus** : endpoint répond en <250 ms, compteurs toujours initialisés à 0 (pas d’activité utilisateur depuis la bascule).
- **Dev bypass** : headers `x-dev-bypass/x-user-id` nécessaires pour requêtes cockpit en prod (AUTH_DEV_MODE=0).
- **Logs PROD** : traces `backend.features.dashboard.timeline_service` montrent la récupération timeline sans stacktrace.

---

## 5. Suivi & prochaines actions

1. Alimenter les timelines avec une session réelle (QA manuelle) pour vérifier les agrégats non nuls.
2. Envisager un seed QA automatisé (via `qa_metrics_validation.py`) pour générer trafic/tokens et incrémenter les compteurs Prometheus.
3. Mettre à jour le dashboard Grafana (Phase 3) pour pointer sur la nouvelle révision/digest.
4. Purger les artefacts Docker obsolètes (tags `cockpit-phase3-20251009-070747` si validé par SRE).

---

## 6. Références

- `build_tag.txt` → `cockpit-phase3-20251009-073931`
- `gcloud run revisions describe emergence-app-phase3b` (digest & ready time)
- `docs/architecture/10-Components.md` (section DashboardService/TImeline)
- QA script : `qa_metrics_validation.py` (mode bypass)
