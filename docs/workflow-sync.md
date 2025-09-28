# Workflow de synchronisation cloud/local

## Objectif
- Garantir que les environnements locaux et cloud (Codex) consomment la mÃªme base de code.
- RÃ©duire le risque d'oublier un `fetch/rebase` ou de pousser un Ã©tat non testÃ©.

## Script `scripts/sync-workdir.ps1`
- Ã‰tapes enchaÃ®nÃ©es :
  1. VÃ©rifie que l'arbre de travail est propre (sauf `-AllowDirty`).
  2. `git fetch --all --prune` puis rebase sur `origin/<BaseBranch>` (dÃ©faut `main`).
  3. ExÃ©cute les commandes de test fournies (dÃ©faut : `pwsh -File tests/run_all.ps1`).
  4. Pousse la branche courante sur `origin` si tout est vert.
  5. Supprime les artefacts de test générés (ex : `test_upload.txt`) avant la vérification finale.
- ParamÃ¨tres utiles :
  - `-BaseBranch <nom>` : branche de rÃ©fÃ©rence, `main` par dÃ©faut.
  - `-SkipTests` : saute l'Ã©tape de test (Ã  Ã©viter hors dÃ©pannage).
  - `-NoPush` : ne pousse pas automatiquement.
  - `-AllowDirty` : tolÃ¨re un working tree non vide (journaliser la raison).
  - `-TestCommands @( <cmd1>, <cmd2> )` : tableau de commandes (chaque commande est un tableau `@(exe, args...)`). Un tableau simple (`@("pytest","-k","smoke")`) ou une chaÃ®ne (`"pytest -k smoke"`) sont Ã©galement acceptÃ©s pour exÃ©cuter une seule commande.

### Exemples d'utilisation
```powershell
# Routine standard (local ou cloud)
pwsh -File scripts/sync-workdir.ps1

# Rebase sur develop et pousser manuellement ensuite
pwsh -File scripts/sync-workdir.ps1 -BaseBranch develop -NoPush

# Ajouter pytest aprÃ¨s le smoke test
pwsh -File scripts/sync-workdir.ps1 -TestCommands @(
    @("pwsh","-NoProfile","-ExecutionPolicy","Bypass","-File","tests/run_all.ps1"),
    @("pytest","tests/backend")
)
```

## Initialisation du remote
- Utiliser les scripts bootstrap pour aligner `origin` sur https://github.com/DrKz36/emergencev8.git avant la premiere synchronisation.
- Windows/PowerShell : `pwsh -File scripts/bootstrap.ps1 -SkipStart` pour configurer le remote sans lancer npm.
- Linux/macOS : `./scripts/bootstrap.sh --skip-start` pour le meme scenario.
- Les options `--remote-name` / `--remote-url` ou `-StartScript` adaptent le script aux forks ou workflows specifiques.
- Si vous utilisez HTTPS avec un PAT GitHub, assurez-vous que le token dispose des permissions `repo` ET `workflow` (fine-grained : `Actions` / `Workflows` en lecture/Ã©criture), faute de quoi GitHub refuse les pushes modifiant `.github/workflows/*.yml`.

## Bonnes pratiques
- Lancer le script au dÃ©but et Ã  la fin de chaque session de travail.
- Verifier a chaque session que les remotes `origin` (HTTPS) et `codex` (SSH) pointent vers le meme depot (`git remote -v`) et corriger l'URL si besoin avant de lancer la synchronisation.
- Documenter tout usage de `-SkipTests`, `-NoPush` ou `-AllowDirty` dans le journal de session.
- Programmer un rappel (Task Scheduler / cron) pour Ã©viter les oublis.
- Coupler avec la CI afin de valider automatiquement chaque push (recommandÃ©).


## Maintenance hebdomadaire du vector store
- Utiliser `pwsh -File scripts/maintenance/run-vector-store-reset.ps1` pour exécuter le scénario auto-reset sans saisie manuelle. Le script délègue à `tests/test_vector_store_reset.ps1 -AutoBackend`, qui démarre/arrête uvicorn, attend `/api/health` puis réalise les uploads de contrôle.
- Les journaux sont archivés sous `docs/assets/memoire/vector-store-reset-YYYYMMDD.log`; conserver les quatre dernières exécutions pour la traçabilité et référencer le fichier correspondant dans `docs/passation.md`.
- Paramètres disponibles : `-BackendHost`, `-BackendPort`, `-BackendStartupTimeoutSec`, `-LogDirectory`, `-LogPrefix`, `-Quiet`.
- Exemple Task Scheduler (Windows) :
  ```powershell
  schtasks /Create /SC WEEKLY /D MON /TN "Emergence_VectorStore_Reset" `
    /TR "pwsh -NoProfile -ExecutionPolicy Bypass -File C\\dev\\emergenceV8\\scripts/maintenance/run-vector-store-reset.ps1" `
    /ST 03:00 /RL HIGHEST
  ````
- Sur Linux/macOS, planifier via cron : `0 4 * * Mon cd /opt/emergence && pwsh -File scripts/maintenance/run-vector-store-reset.ps1 >> docs/assets/memoire/vector-store-reset-cron.log 2>&1`.
