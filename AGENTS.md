# Consignes Agent Emergence V8

Ces instructions s'appliquent a tout le depot `emergencev8`.

## 1. Documentation de reference
- Lire integralement ce fichier et tout `AGENTS.md` specifique dans un sous-dossier avant toute action.
- Consulter systematiquement les documents clefs dans `docs/` avant de modifier du code :
  - `docs/architecture/` pour l'architecture, les composants, les sequences et les contrats.
  - `docs/Roadmap Strategique.txt` pour l'etat des priorites.
  - `docs/Memoire.md` pour les interactions memoire/RAG.
- Appliquer immediatement toute nouvelle consigne decouverte pendant la session.
- Verifier que les decisions prises restent coherentes avec ces sources.

## 2. Synchronisation documentation <-> code
- Toute evolution impactant architecture, responsabilites de services ou flux memoire/RAG doit etre repercutee dans `docs/`.
- Inclure dans les commits les mises a jour de documentation liees aux changements de code.

## 3. Preparation de l'environnement
- Utiliser Python 3.11 dans un virtualenv.
- Windows PowerShell : `python -m venv .venv` puis `.\\.venv\\Scripts\\Activate.ps1`.
- macOS / Linux : `python3.11 -m venv .venv` puis `source .venv/bin/activate`.
- Installer ou mettre a jour les dependances avec `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`.
- Optionnel : capturer les versions effectives avec `pip freeze > requirements-dev.txt` ou maintenir un `requirements.lock`.
- Utiliser Node.js >= 18 (`nvm use 18` recommande) et reinstaller via `npm ci` apres tout changement de `package-lock.json`.
- Executer `npm run build` pour verifier le frontend avant chaque push.

## 4. Avant de coder
- Verifier que `git status` est propre avant de commencer.
- Mettre a jour/configurer `.env.local` si les changements le necessitent (cles API, tokens, allow/deny lists).
- S'assurer que les migrations ou initialisations necessaires sont executees selon la documentation (`run-local.ps1`, docs d'architecture, etc.).
- Planifier les travaux dans la fenetre de contexte disponible; ne pas demarrer de taches trop longues pour une session.

## 5. Pendant la modification
- Respecter la structure des dossiers (`src/backend`, `src/frontend`, `docs`, ... ) et les conventions existantes.
- Creer les fichiers complementaires requis (config/tests) pour tout nouveau fichier ajoute.
- Ne livrer que des fichiers complets et conformes.

## 6. Actions immediates
- Apres chaque contribution, proposer des actions prioritaires pour la prochaine instance, alignees avec la roadmap.
- Signaler tout blocage ou dependance manquante pour faciliter la releve.

## 7. Verifications avant commit
- Backend : executer les linters/tests pertinents (`pytest`, `ruff`, `mypy`) selon la portee des changements.
- Frontend : executer `npm run build` (et autres scripts specifies localement) lorsque du code frontend est modifie.
- Relire `git diff` pour eliminer secrets, artefacts ou modifications accidentelles.

## 8. Procedure Git
- Utiliser des messages de commit explicites (ex. `<type>: <resume>`).
- Garder `git status` propre apres chaque commit.
- Identifier la branche de reference amont via `git remote show origin` (HEAD generalement `main`).
- Avant push : `git fetch --all --prune` puis `git rebase origin/<branche_de_reference>`.
- Resoudre les conflits en local, relancer les tests, puis utiliser `git push --force-with-lease` uniquement apres un rebase reussi.
- Nettoyer regulierement les branches fusionnees (localement et sur le remote).
- Finaliser chaque intervention par `git add -A`, un commit explicite et `git push` sauf instruction contraire.

## 9. Verifications supplementaires
- Lancer les scripts de tests disponibles (`pwsh -File tests/run_all.ps1`) pour valider les endpoints backend critiques lorsqu'ils sont touches.
- Pour le frontend, verifier que `npm run build` reussit et reste compatible avec la cible configuree par Vite.
- Si necessaire pour parite production, construire l'image Docker locale (`docker build -t emergence-local .`).

## 10. Preparation de la PR
- Preparer un resume des changements, tests executes et commandes utilisees.
- S'assurer que l'integration continue passe (si accessible) apres le push.

## 11. Workflow cloud -> local recommande
1. `git status`
2. `git remote show origin` pour confirmer la branche de base (souvent `main`).
3. `git fetch --all --prune`
4. `git checkout <branche_base>` puis `git pull --rebase origin <branche_base>`
5. `git checkout <branche_travail>` puis `git rebase origin/<branche_base>`
6. Reactiver le virtualenv Python et executer `python -m pip install -r requirements.txt` si les lockfiles ont evolue.
7. Executer `npm ci` puis `npm run build` si `package-lock.json` a change.
8. Lancer les tests/lint backend pertinents (`pytest`, `ruff`, `mypy`) et verifier que `npm run build` passe.
9. Developper et committer de maniere atomique avec un message explicite.
10. Rebaser juste avant le push si la branche a diverge.
11. `git push origin <branche>` et ouvrir la PR.
12. Apres merge, supprimer les branches obsolete (`git branch -d`, `git push origin --delete`).
## 12. Harmonisation cloud/local
- Lancer `pwsh -File scripts/sync-workdir.ps1` (fetch/rebase/tests/push par défaut) au démarrage puis à la fin de chaque session locale ou cloud pour garder l'état aligné.
- Utiliser les options `-SkipTests`, `-NoPush` ou `-AllowDirty` uniquement en cas de blocage identifié et consigner la raison dans le journal de session.
- Toujours considérer la branche distante comme source de vérité; travailler sur une seule branche de fonctionnalité par sujet et pousser après chaque session (`git push origin <branche>`).
- Vérifier que `git status` reste propre avant de quitter un poste; le script échoue par défaut en cas de fichiers non commités (sauf usage explicite de `-AllowDirty`).
- Préférer `git worktree` ou des branches éphémères plutôt que des stashes pour des travaux longs afin de garder un état reproductible.

### Alternative plus robuste
- Programmer `scripts/sync-workdir.ps1` (Task Scheduler/cron) sur les postes utilisés fréquemment pour rappeler les synchronisations.
- Coupler la CI (GitHub Actions) pour reconstruire et tester chaque push vers la branche de travail avant fusion.
- Activer `pre-commit` avec des hooks de formatage/lint afin d'éviter de pousser des artefacts temporaires.
