## Prompt Session Suivante - Emergence V8

### Contexte express
- ✅ QA cockpit centralisée : `qa_metrics_validation.py` orchestre métriques Prometheus + timelines + rapport JSON.
- ✅ Scripts de maintenance : `scripts/qa/run_cockpit_qa.ps1` (routine combinée) + `scripts/qa/purge_test_documents.py` (purge artefacts).
- ✅ TimelineService stabilisé (LEFT JOIN filtrés) et docs déploiement Phase3b complétées.
- ✅ Qualité vérifiée : `pytest`, `ruff check`, `mypy src`, `npm run build` passés ce matin.
- 🟡 À planifier : exécution programmée `run_cockpit_qa.ps1` (Task Scheduler/cron) + archivage régulier des rapports JSON (`docs/monitoring/snapshots/`).

### Derniers jalons Git
- `2546c25` docs: prompt P1 enrichissement mémoire - déportation async + préférences
- `67f2d5a` docs: index déploiements mis à jour avec Phases 2 & 3
- `cockpit-phase3-20251009-073931` image Cloud Run (révision `emergence-app-phase3b`)

### Artefacts clés
- `qa_metrics_validation.py` + `scripts/qa/*` (QA, purge, scheduler)
- `docs/monitoring/prometheus-phase3-setup.md` (section QA cockpit unifié)
- `docs/qa/cockpit-qa-playbook.md` (routine snapshot + planification)
- `docs/deployments/2025-10-09-deploy-cockpit-phase3.md` (rapport de redeploy timeline)

---

### Priorités recommandées (Claude Code)
1. **Routine QA distante**  
   Lancer `scripts/qa/run_cockpit_qa.ps1 -BaseUrl https://emergence-app-47nct44nma-ew.a.run.app -LoginEmail ... -LoginPassword ... -TriggerMemory -RunCleanup` avec les identifiants prod pour générer `qa-report.json` + smoke log, puis ranger ces artefacts dans `docs/monitoring/snapshots/`.

2. **Planification automatique**  
   - Créer une tâche planifiée Windows (ou cron) quotidienne 07:30 CEST qui exécute `run_cockpit_qa.ps1`.
   - Documenter le job (chemin, credentials, sortie) dans `docs/qa/cockpit-qa-playbook.md` + `AGENT_SYNC.md`.

3. **Nettoyage & packaging review FG**  
   - Préparer le bundle commit/push final (diff validé, `git tag` si requis, noter instructions FG).
   - Vérifier que `build_tag.txt` + `docs/deployments/README.md` sont alignés avec la révision Cloud Run servie (phase3b).

### État des tests
- `python -m pytest` (152 tests) ✅
- `ruff check` ✅
- `mypy src` ✅ (notes sur fonctions non typées seulement)
- `npm run build` ✅

### Commandes utiles
```bash
python qa_metrics_validation.py --base-url https://emergence-app-47nct44nma-ew.a.run.app \
  --login-email "$EMERGENCE_SMOKE_EMAIL" --login-password "$EMERGENCE_SMOKE_PASSWORD" \
  --trigger-memory --json-output docs/monitoring/snapshots/qa-report-$(date +%Y%m%d-%H%M).json

pwsh -File scripts/qa/run_cockpit_qa.ps1 -BaseUrl https://emergence-app-47nct44nma-ew.a.run.app `
  -LoginEmail $env:EMERGENCE_SMOKE_EMAIL -LoginPassword $env:EMERGENCE_SMOKE_PASSWORD `
  -TriggerMemory -RunCleanup
```

### Prompt de reprise (à copier pour Claude Code)
```
Salut Claude,

Contexte rapide : la QA cockpit est désormais unifiée (script python unique + routine PowerShell), les timelines SQL sont stabilisées et la doc monitoring/QA a été rafraîchie. Tous les tests (pytest, ruff, mypy, npm run build) passent en local.

Tâches focus :
1. Exécuter la routine QA distante (run_cockpit_qa.ps1) avec les credentials prod pour générer un rapport JSON + logs, puis archiver ces artefacts dans docs/monitoring/snapshots/.
2. Planifier l’exécution automatique quotidienne (Task Scheduler ou cron) de la routine QA et documenter la planification (playbook + AGENT_SYNC).
3. Préparer le bundle final pour FG : relire git diff, confirmer build_tag / docs/deployments cohérents, proposer le plan de commit/push/merge.

Le repo est propre (tests OK). Si une étape te bloque (ex: accès secrets), documente-le dans docs/passation.md et AGENT_SYNC.md avant de passer à la suite.
Bonne session !
```
