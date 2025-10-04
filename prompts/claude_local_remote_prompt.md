# Briefing Claude (Local) — Configuration des remotes Git

## Problème constaté
- Sur le cloud, `git remote -v` ne renvoie aucune entrée : ni `origin`, ni `codex` ne sont configurés.
- Sans remote défini, impossible de `fetch`, `pull` ou `push`, ce qui empêche de synchroniser la branche locale avec GitHub.

## Solution proposée
1. **Recréer les remotes attendus**
   - `git remote add origin https://github.com/DrKz36/emergencev8.git`
   - `git remote add codex git@github.com:DrKz36/emergencev8.git`
2. **Vérifier l’accès réseau**
   - Tester `git fetch origin` ; si un 403 apparaît (proxy HTTP côté cloud), retenter avec le réseau interne ou via le contournement proxy documenté.
3. **Synchroniser la branche de travail**
   - `git checkout main && git pull --rebase origin main`
   - Puis revenir sur la branche en cours (`git checkout work` ou autre) et `git rebase origin/main` avant de poursuivre le dev.

## Points de vigilance
- Le proxy du cloud bloque parfois l’HTTPS : prévoir un retry ou basculer vers un environnement où `origin` est accessible.
- Confirmer que `.claude/settings.local.json` reste aligné avec les consignes (fichier listé comme modifié dans l’état actuel).

## Prochaine étape
Une fois les remotes rétablis, relancer `scripts/sync-workdir.ps1` (ou l’équivalent manuel) pour repartir sur un arbre propre avant les prochaines tâches.
