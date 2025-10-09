# Cockpit QA Playbook

## 1. Objectifs
- Centraliser les scripts QA cockpit (métriques Prometheus + timelines dashboard).
- Limiter l’accumulation des artefacts (`test_upload.txt`, documents temporaires).
- Préparer un rapport unique avant revue FG (snapshot + scripts).

## 2. Scripts clés

| Script | Rôle | Notes |
|--------|------|-------|
| `qa_metrics_validation.py` | Flux complet métriques + timeline + rapport JSON | Options `--skip-*`, `--json-output`, `--force-read-only-probe` |
| `scripts/qa/qa_timeline_scenario.py` | Compatibilité CLI timeline seule | Enrobe `qa_metrics_validation.py --skip-metrics` |
| `scripts/qa/purge_test_documents.py` | Purge des documents `test_upload*` | Support `--pattern`, `--dry-run`, fallback dev login |
| `scripts/qa/run_cockpit_qa.ps1` | Orchestration combinée (metrics → smoke → purge) | Paramètres `-SkipTimeline`, `-SkipMetrics`, `-RunCleanup` |
| `tests/run_all.ps1` | Smoke suite historique | Nettoie désormais automatiquement l’ID du document upload |

## 3. Commandes utiles

### 3.1 Rapport QA complet (console + JSON)

```bash
python qa_metrics_validation.py \
  --base-url https://emergence-app-47nct44nma-ew.a.run.app \
  --login-email "$EMERGENCE_SMOKE_EMAIL" \
  --login-password "$EMERGENCE_SMOKE_PASSWORD" \
  --trigger-memory \
  --json-output qa-report.json
```

### 3.2 Timeline seule (CLI historique)

```bash
python scripts/qa/qa_timeline_scenario.py --skip-metrics --use-rag
```

### 3.3 Purge ciblée des documents QA

```bash
python scripts/qa/purge_test_documents.py \
  --pattern test_upload \
  --dry-run
```

### 3.4 Routine programmable (PowerShell)

```powershell
pwsh -File scripts/qa/run_cockpit_qa.ps1 `
  -BaseUrl https://emergence-app-47nct44nma-ew.a.run.app `
  -LoginEmail $env:EMERGENCE_SMOKE_EMAIL `
  -LoginPassword $env:EMERGENCE_SMOKE_PASSWORD `
  -TriggerMemory `
  -RunCleanup
```

## 4. Planification (snapshot continu)

1. **Windows Task Scheduler**  
   - Action : `pwsh.exe -File C:\dev\emergenceV8\scripts\qa\run_cockpit_qa.ps1 -TriggerMemory -RunCleanup`  
   - Déclencheur : quotidien 07:30 CET (avant les QA manuelles).
2. **Linux/macOS cron**  
   - `0 6 * * * /usr/bin/pwsh -File /opt/emergence/scripts/qa/run_cockpit_qa.ps1 -TriggerMemory -RunCleanup`.
3. Exporter `qa-report.json` et log `tests/run_all.ps1` dans `docs/monitoring/snapshots/` pour la revue FG.

## 5. Snapshot "clean" pré-revue FG

1. Exécuter `scripts/qa/run_cockpit_qa.ps1 -TriggerMemory -RunCleanup`.
2. `python qa_metrics_validation.py --json-output docs/monitoring/snapshots/qa-report-$(Get-Date -Format yyyyMMdd-HHmm).json`.
3. `git status --short` (vérifier uniquement les fichiers attendus : timeline service, QA scripts, docs).
4. Documenter la session dans `docs/passation.md` + mise à jour `AGENT_SYNC.md`.

## 6. Checklist rapide
- [ ] `qa_metrics_validation.py` exécuté (console OK + JSON archivé)
- [ ] `tests/run_all.ps1` sans erreurs critiques
- [ ] `scripts/qa/purge_test_documents.py --dry-run` = 0 artefacts résiduels
- [ ] Snapshot docs (rapport JSON + log smoke) rangés dans `docs/monitoring/snapshots/`
- [ ] Diff relu avant revue FG (`git diff --stat`)
