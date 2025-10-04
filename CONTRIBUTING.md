# Contributing - Emergence V8

Merci de contribuer a Emergence V8. Ce guide resume les attentes avant d'ouvrir une Pull Request.

## Prerequis
- Python 3.11 et Node.js 18 (voir README pour l'installation).
- Script `scripts/sync-workdir.ps1` fonctionnel (PowerShell 7 recommande).
- Acces au depot GitHub `DrKz36/emergencev8`.

## Cycle de developpement
1. Lancer `pwsh -File scripts/sync-workdir.ps1` pour rebaser et executer les tests de fumee.
2. Developper sur une branche derivee de `main` (`fix/`, `feat/`, `docs/`, etc.).
3. Ajouter la documentation et les tests correspondant aux changements.
4. Renseigner la passation (`docs/passation*.md`) lorsque des decisions impactent l'architecture ou le RAG.
5. Ouvrir une PR en remplissant le template fourni dans `.github/pull_request_template.md`.

## Tests et qualite
- Backend : `pytest`, `ruff`, `mypy` (ou `./scripts/run_backend_quality.ps1`).
- Frontend : `npm run build` et tests specifiques via `node --test`.
- Scripts : fournir des tests ou instructions de verification lorsque c'est pertinent.

## Workflow Git et squash merge
- Toutes les PR sont fusionnees via **squash merge**. Les commits individuels d'une branche ne se retrouvent plus dans `main` apres merge (voir `docs/git-workflow.md`).
- Apres merge :
  ```powershell
  git checkout main
  git pull origin main
  git branch -d <branche>
  git push origin --delete <branche>
  ```
- Relancer `scripts/sync-workdir.ps1` (ajouter `-AllowDirty` si des fichiers non suivis doivent rester).

## Communication
- Documenter les changements majeurs dans `docs/passation.md` ou un fichier dedie.
- Mentionner les dependances externes necessaires (API keys, services) dans la PR.
- Signaler tout blocage ou dette technique dans le canal prevu (issues, doc, passation).

## Ressources utiles
- `docs/git-workflow.md` : workflow Git detaille.
- `docs/workflow-sync.md` : synchronisation cloud/local et script de sync.
- `README.md` : installation et commandes principales.

Bon developpement !
