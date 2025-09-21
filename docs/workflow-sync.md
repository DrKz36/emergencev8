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
- Paramètres utiles :
  - `-BaseBranch <nom>` : branche de référence, `main` par défaut.
  - `-SkipTests` : saute l'étape de test (à éviter hors dépannage).
  - `-NoPush` : ne pousse pas automatiquement.
  - `-AllowDirty` : tolère un working tree non vide (journaliser la raison).
  - `-TestCommands @( <cmd1>, <cmd2> )` : tableau de commandes (chaque commande est un tableau `@(exe, args...)`).

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

## Bonnes pratiques
- Lancer le script au début et à la fin de chaque session de travail.
- Documenter tout usage de `-SkipTests`, `-NoPush` ou `-AllowDirty` dans le journal de session.
- Programmer un rappel (Task Scheduler / cron) pour éviter les oublis.
- Coupler avec la CI afin de valider automatiquement chaque push (recommandé).
