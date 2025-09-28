# Workflow de synchronisation cloud/local

## Objectif
- Garantir que les environnements locaux et cloud (Codex) consomment la même base de code.
- Réduire le risque d'oublier un `fetch/rebase` ou de pousser un état non testé.

## Script `scripts/sync-workdir.ps1`
- Étapes enchaînées :
  1. Vérifie que l'arbre de travail est propre (sauf `-AllowDirty`).
  2. `git fetch --all --prune` puis rebase sur `origin/<BaseBranch>` (défaut `main`).
  3. Exécute les commandes de test fournies (défaut : `pwsh -File tests/run_all.ps1`).
  4. Pousse la branche courante sur `origin` si tout est vert.
  5. Supprime les artefacts de test g�n�r�s (ex : `test_upload.txt`) avant la v�rification finale.
- Paramètres utiles :
  - `-BaseBranch <nom>` : branche de référence, `main` par défaut.
  - `-SkipTests` : saute l'étape de test (à éviter hors dépannage).
  - `-NoPush` : ne pousse pas automatiquement.
  - `-AllowDirty` : tolère un working tree non vide (journaliser la raison).
  - `-TestCommands @( <cmd1>, <cmd2> )` : tableau de commandes (chaque commande est un tableau `@(exe, args...)`). Un tableau simple (`@("pytest","-k","smoke")`) ou une chaîne (`"pytest -k smoke"`) sont également acceptés pour exécuter une seule commande.

### Exemples d'utilisation
```powershell
# Routine standard (local ou cloud)
pwsh -File scripts/sync-workdir.ps1

# Rebase sur develop et pousser manuellement ensuite
pwsh -File scripts/sync-workdir.ps1 -BaseBranch develop -NoPush

# Ajouter pytest après le smoke test
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
- Si vous utilisez HTTPS avec un PAT GitHub, assurez-vous que le token dispose des permissions `repo` ET `workflow` (fine-grained : `Actions` / `Workflows` en lecture/écriture), faute de quoi GitHub refuse les pushes modifiant `.github/workflows/*.yml`.

## Bonnes pratiques
- Lancer le script au début et à la fin de chaque session de travail.
- Verifier a chaque session que les remotes `origin` (HTTPS) et `codex` (SSH) pointent vers le meme depot (`git remote -v`) et corriger l'URL si besoin avant de lancer la synchronisation.
- Documenter tout usage de `-SkipTests`, `-NoPush` ou `-AllowDirty` dans le journal de session.
- Programmer un rappel (Task Scheduler / cron) pour éviter les oublis.
- Coupler avec la CI afin de valider automatiquement chaque push (recommandé).


## Maintenance hebdomadaire du vector store
- Utiliser `pwsh -File scripts/maintenance/run-vector-store-reset.ps1` pour exécuter le scénario auto-reset sans saisie manuelle (démarrage backend, corruption contrôlée, relance et upload post-reset).
- Les journaux sont archivés sous `logs/vector-store/vector_store_reset_YYYYMMDD-HHmmss.log`; conserver les 4 dernières exécutions pour traçabilité.
- Exemple Task Scheduler (Windows) :
  ```powershell
  schtasks /Create /SC WEEKLY /D SUN /TN "Emergence_VectorStore_Reset" `
    /TR "pwsh -NoProfile -ExecutionPolicy Bypass -File C:\dev\emergenceV8\scripts/maintenance/run-vector-store-reset.ps1" `
    /ST 03:00 /RL HIGHEST
  ```
- Pour un backend dans un virtualenv, préciser `-BackendCommand @("pwsh","-NoProfile","-Command",". .\.venv\Scripts\Activate.ps1; uvicorn --app-dir src backend.main:app --host 127.0.0.1 --port 8000")` dans la tâche planifiée.
- Sur Linux/macOS, planifier via cron : `0 4 * * Mon cd /opt/emergence && pwsh -File scripts/maintenance/run-vector-store-reset.ps1 >> logs/vector-store/cron.log 2>&1`.

