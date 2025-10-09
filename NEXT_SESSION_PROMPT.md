# Prompt Session Suivante - Emergence V8

## Contexte

**Session précédente terminée** : ✅ Validation Cockpit Métriques Phase 3 - SUCCÈS COMPLET

**État actuel** :
- ✅ **Cockpit Validé 100%** : API endpoints fonctionnels, métriques enrichies, filtrage session OK
- ✅ **Calculs validés** : 100% cohérence API vs BDD (messages: 170, tokens: 404438, costs: 0.08543845)
- ✅ **Tests locaux** : 45/45 passants (pytest)
- ✅ **Qualité code** : mypy 0 erreur, ruff clean
- ✅ **Production stable** : Métriques Prometheus actives (`emergence-app-metrics001`)
- ⚠️ **Prêt pour deploy** : Nouvelle image ou utiliser metrics001 existante

**Derniers commits** :
```
c951a09 docs: prompt debug cockpit - validation métriques Phase 3
abf1b26 docs: validation complète Phase 3 Prometheus en production
1cbdac9 feat: frontend cockpit - intégration métriques enrichies + docs session
```

**Fichiers importants** :
- `docs/monitoring/prometheus-phase3-setup.md` - Setup complet monitoring
- `monitoring/grafana-dashboard-prometheus-phase3.json` - Dashboard 7 panels
- `docs/deployments/2025-10-09-activation-metrics-phase3.md` - Déploiement Phase 3

---

## 🚀 Tâche Prioritaire : Déploiement Production

### Option 1 : Build nouvelle image (recommandé pour phase 3)
```bash
# 1. Build image avec tag timestampé
timestamp=$(date +%Y%m%d-%H%M%S)
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:metrics-phase3-$timestamp \
  .

# 2. Push to registry
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:metrics-phase3-$timestamp

# 3. Deploy Cloud Run
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:metrics-phase3-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --revision-suffix metrics-phase3 \
  --env-vars-file env.yaml \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,GOOGLE_API_KEY=GOOGLE_API_KEY:5,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:5" \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi

# 4. Route 100% traffic
gcloud run services update-traffic emergence-app \
  --region europe-west1 \
  --to-revisions emergence-app-metrics-phase3=100
```

### Option 2 : Utiliser image existante (plus rapide)
L'image actuelle `metrics001` contient déjà tous les changements Phase 3. Peut être réutilisée directement.

### Validation Post-Deploy
```bash
# 1. Test health
curl https://emergence-app-47nct44nma-ew.a.run.app/api/health

# 2. Test cockpit metrics
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/dashboard/costs/summary | jq

# 3. Test timeline endpoints
curl -s "https://emergence-app-47nct44nma-ew.a.run.app/api/dashboard/timeline/activity?period=30d" | jq

# 4. Vérifier métriques Prometheus
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep -E "memory_analysis|concept_recall" | head -10

# 5. Check logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app" \
  --limit 20 \
  --format json \
  --project emergence-469005
```

## 📝 Documentation & Suivi

### Créer rapport déploiement
```bash
# Créer docs/deployments/2025-10-09-deploy-cockpit-phase3.md
# Inclure:
# - Timestamp déploiement
# - Révision Cloud Run
# - Tests validation post-deploy
# - Métriques observées
```

### Mettre à jour AGENT_SYNC.md
Ajouter section "Session 2025-10-09 - Validation Cockpit + Deploy Phase 3"

---

## Commandes Rapides

```bash
# Vérifier tests
python -m pytest tests/test_memory_archives.py -v --tb=short

# Vérifier qualité
python -m ruff check
mypy src

# Statut git
git status --short
git log --oneline -5

# Métriques prod
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep -E "memory_analysis|concept_recall" | head -10
```

---

## Notes Importantes

- **NE PAS** toucher au code déployé en prod (révision `emergence-app-metrics001` stable)
- **FOCUS** sur stabilisation locale (tests + qualité) avant prochaine feature
- **Si stuck** sur tests API : documenter problème et passer à Ruff/Mypy
- **Objectif session** : atteindre 154/154 tests passants OU documenter blocages clairement

---

## Prompt à Copier-Coller

```markdown
Bonjour Claude,

Je reprends le développement d'Emergence V8 après une session de debug cockpit + monitoring Prometheus.

**État actuel** :
- ✅ Métriques Prometheus Phase 3 en prod (13 métriques actives)
- ✅ Tests: 149/154 passent (5 échecs tests API intégration)
- ✅ Dashboard Grafana + doc monitoring créés
- ⚠️ Ruff: 5 erreurs E402, Mypy: 21 erreurs

**Tâches prioritaires (3 max)** :

1. **Corriger 5 tests API restants** (`tests/test_memory_archives.py`)
   - Échecs: unified_search, 3x API endpoints (401), concept_recall_timestamps
   - Problèmes: DB connection, auth fixtures, VectorService init

2. **Finaliser qualité code**
   - Ruff: fixer 5 erreurs E402 dans scripts/tests
   - Mypy: installer types-psutil + fix typages (optionnel)

3. **Documenter dans AGENT_SYNC.md**
   - Ajouter session 2025-10-09 (corrections + monitoring)
   - Mettre à jour "Prochaines étapes"

**Fichiers clés** :
- `tests/test_memory_archives.py` (5 échecs à fixer)
- `AGENT_SYNC.md` (documentation session)
- `scripts/migrate_concept_metadata.py` + `tests/test_benchmarks.py` (E402)

Commence par analyser les 5 échecs de tests API et propose des corrections. Si bloqué, passe à Ruff puis doc.

Objectif : atteindre 154/154 tests OU documenter blocages clairement.
```
