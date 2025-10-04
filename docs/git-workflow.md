# Git Workflow - Emergence V8

Ce document decrit le flux Git recommande pour contribuer au depot `emergenceV8` et eviter les pieges lies au squash merge.

## 1. Branches et preparation
- `main` est la branche de reference. Elle doit toujours rester deployable.
- Cree une branche de fonctionnalite depuis `main` :
  ```powershell
  git checkout main
  git pull origin main
  git checkout -b fix/ma-tache
  ```
- Nomme les branches avec un prefixe explicite (`fix/`, `feat/`, `docs/`, `chore/`).
- Lance `pwsh -File scripts/sync-workdir.ps1` au debut de la session pour rebaser et executer les tests de fumee.

## 2. Commits atomiques
- Commits petits et decrivant une intention unique (ex: `fix: handle ws opinion dedupe`).
- Inclure les mises a jour de documentation et de tests dans la meme PR.
- Eviter les commits "WIP"; rebase interactif avant la PR pour nettoyer l'historique local.

## 3. Pull Request
1. Rebase sur `origin/main` avant d'ouvrir la PR :
   ```powershell
   git checkout main
   git pull --rebase origin main
   git checkout <branche>
   git rebase origin/main
   ```
2. Verifier les tests (`pytest`, `npm run build`, etc.).
3. Ouvrir la PR avec le template `.github/pull_request_template.md`.
4. Joindre les resultats de test et les mises a jour de documentation.

## 4. Merge: pourquoi le squash
Le projet applique **squash merge** sur GitHub pour garder un historique lineaire et lisible.

- Avantage: un seul commit propre sur `main` par PR.
- Consequence: les SHA individuels de la branche sont perdus (ils deviennent un seul commit `main`).
- Impact: apres merge, `git log main` ne montrera plus vos commits originaux, mais les fichiers modifies sont toujours presents.

### Exemple
```
Branche feature:
* abc123 docs: update sync notes
* def456 tests: add integration check

Apres squash merge dans main:
* xyz789 docs: update sync notes (#42)
```

## 5. Procedure post-merge
1. Confirmer que la PR est `Merged` sur GitHub.
2. Mettre a jour `main` localement :
   ```powershell
   git checkout main
   git pull origin main
   ```
3. Verifier que les fichiers modifies sont bien presents.
4. Nettoyer les branches terminees :
   ```powershell
   git branch -d <branche>
   git push origin --delete <branche>
   ```
5. Relancer `scripts/sync-workdir.ps1` pour repartir sur des bases propres.
6. Mettre a jour le journal de session/passation avec les actions realisees.

## 6. Checklist post-merge
- [ ] PR en statut `Merged`.
- [ ] `main` local a jour (`git pull origin main`).
- [ ] Branche locale supprimee (`git branch -d`).
- [ ] Branche distante supprimee (`git push origin --delete`).
- [ ] Scripts de sync relances si necessaire.
- [ ] Compte-rendu de session mis a jour.

## 7. Utiliser `scripts/sync-workdir.ps1`
Le script orchestre `git fetch`, `rebase`, tests et push.

- `-AllowDirty` autorise les fichiers non suivis (journaliser la raison).
- `-NoPush` permet de controler manuellement le push.
- `-BaseBranch` change la branche de reference (par defaut `main`).
- Apres merge, lancer le script pour confirmer qu'aucun diff inattendu ne subsiste.

## 8. Resolution des problemes courants
### Mes commits ont disparu de `main`
C'est normal avec le squash merge. Chercher le commit de merge GitHub (`git log --grep "#<numero>"`) ou verifier les fichiers modifies (`git show HEAD --name-only`).

### Ma branche locale contient encore des commits apres le merge
Supprime-la et recree une branche depuis `main`.
```powershell
git checkout main
git pull origin main
git branch -D <branche>
```

### Je dois garder des fichiers non suivis (notes locales)
Utiliser `git status --ignored` pour les lister puis lancer `scripts/sync-workdir.ps1 -AllowDirty`. Documenter cette situation dans la passation.

## 9. Ressources
- `docs/workflow-sync.md` : synchronisation cloud/local.
- `README.md` : installation et commandes de base.
- `.github/pull_request_template.md` : checklist PR.
- `CONTRIBUTING.md` : bonnes pratiques et exigences de contribution.
