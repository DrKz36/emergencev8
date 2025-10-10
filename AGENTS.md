# Consignes Agent Emergence V8

## Vue d'ensemble
- S'assurer que chaque action reste coherente avec la documentation vivante du depot et les consignes de session.
- Travailler dans un environnement controle (Python 3.11 + Node.js >= 18) et reproductible.
- Synchroniser en continu la documentation et le code, en particulier pour l'architecture et la memoire/RAG.
- Boucler chaque session par des tests pertinents, un diff relu et une passation claire des prochaines actions.
- Conduire chaque tache ou serie de taches jusqu'a l'objectif defini sans solliciter de validation intermediaire de l'utilisateur, sauf blocage critique documente.

## Checklist express
### Lancement de session
- **🔄 NOUVEAU - SYNCHRONISATION AUTOMATIQUE ACTIVÉE** :
  - Le système AutoSyncService surveille automatiquement 8 fichiers critiques
  - Dashboard disponible : http://localhost:8000/sync-dashboard.html
  - Vérifier le statut de sync avant de commencer : `curl http://localhost:8000/api/sync/status`
- **OBLIGATOIRE** : Lire `AGENT_SYNC.md` (etat sync inter-agents) AVANT toute action de code.
  - ⚠️ Ce fichier est maintenant surveillé automatiquement - toute modification sera détectée
- Lire integralement ce fichier ainsi que tout `AGENTS.md` specifique au dossier courant.
- Consulter `docs/passation.md` (3 dernieres entrees minimum) pour contexte recent.
  - ⚠️ Ce fichier est maintenant surveillé automatiquement
- Consulter les references clefs : `docs/architecture/`, `docs/Roadmap Strategique.txt`, `docs/Memoire.md`.
  - ⚠️ Fichiers architecture surveillés automatiquement : 00-Overview.md, 30-Contracts.md, 10-Memoire.md
- Lancer `pwsh -File scripts/sync-workdir.ps1` (option par defaut) ou realiser l'equivalent manuel (`git fetch --all --prune`, rebase, tests rapides).
- Verifier que `git status` est propre et que l'environnement (virtualenv Python + Node.js) est pret.
- Verifier que Codex/Copilot est configure en auto-completion auto-apply (settings VS Code/Windsurf) pour eviter les demandes d'approbation.

### Pendant le developpement
- Avancer sans interruption sur l'objectif confie en bouclant l'ensemble des taches identifiees avant de solliciter l'utilisateur, sauf dependance bloquante explicitement consignee.
- Respecter la structure des dossiers et conventions etablies (`src/backend`, `src/frontend`, `docs`, ...).
- Creer les tests/configurations necessaires pour tout nouveau fichier; ne deposez pas de travail partiel.
- Tenir la documentation synchronisee des que des composants, responsabilites ou flux memoire/RAG evoluent.
- Signaler tout blocage ou dependance manquante pour faciliter la releve.

### Cloture de session
- Executer les tests/lint pertinents (`pytest`, `ruff`, `mypy`, `npm run build`, `pwsh -File tests/run_all.ps1` selon l'impact).
- Relire `git diff` pour traquer secrets, artefacts ou changements involontaires.
- **🔄 OBLIGATOIRE : Mettre à jour la documentation collaborative** :
  - `AGENT_SYNC.md` (section "Claude Code" avec timestamp et fichiers touchés)
    - ⚠️ Surveillé automatiquement - la modification sera détectée et consolidée
  - `docs/passation.md` (nouvelle entrée complète en haut du fichier)
    - ⚠️ Surveillé automatiquement - la modification sera détectée et consolidée
  - Voir `docs/SYNCHRONISATION_AUTOMATIQUE.md` pour le fonctionnement complet
- **🔄 NOUVEAU - Consolidation automatique** :
  - Option 1 : Laisser le système consolider automatiquement (seuil 5 changements ou 60 min)
  - Option 2 : Déclencher manuellement via dashboard : http://localhost:8000/sync-dashboard.html
  - Option 3 : Déclencher via API : `curl -X POST http://localhost:8000/api/sync/consolidate`
  - Les rapports de consolidation sont ajoutés automatiquement à `AGENT_SYNC.md`
- Finaliser par `git add -A`, un commit explicite et `git push` (sauf instruction contraire) apres rebase sur la branche de reference.
- Noter dans le compte-rendu les prochaines priorites et actions recommandees.

---

## 1. Documentation de reference
- Lire integralement ce fichier et tout `AGENTS.md` specifique dans un sous-dossier avant toute action.
- Consulter systematiquement les documents clefs dans `docs/` avant de modifier du code :
  - `docs/architecture/` pour l'architecture, les composants, les sequences et les contrats.
  - `docs/Roadmap Strategique.txt` pour l'etat des priorites.
  - `docs/Memoire.md` pour les interactions memoire/RAG.
- Appliquer immediatement toute nouvelle consigne decouverte pendant la session et l'articuler avec les decisions en cours.
- Verifier que les choix techniques et fonctionnels restent coherents avec ces sources et mettre a jour la documentation si necessaire.

## 2. Synchronisation documentation <-> code
- Repercuter dans `docs/` toute evolution impactant l'architecture, les responsabilites de services ou les flux memoire/RAG.
- Inclure dans les commits les mises a jour de documentation liees aux changements de code et en rappeler l'impact dans la PR.

## 3. Preparation de l'environnement
- Utiliser Python 3.11 dans un virtualenv.
- Windows PowerShell : `python -m venv .venv` puis `.\\.venv\\Scripts\\Activate.ps1`.
- macOS / Linux : `python3.11 -m venv .venv` puis `source .venv/bin/activate`.
- Installer ou mettre a jour les dependances avec `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`.
- Optionnel : capturer les versions effectives avec `pip freeze > requirements-dev.txt` ou maintenir un `requirements.lock`.
- Demarrer le backend local via `pwsh -File scripts/run-backend.ps1` (maintient uvicorn en avant-plan, evite le signal window close precedent et prepare l'ajout d'une supervision).
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
- Lancer `pwsh -File scripts/sync-workdir.ps1` (fetch/rebase/tests/push par defaut) au demarrage puis a la fin de chaque session locale ou cloud pour garder l'etat aligne.
- Utiliser les options `-SkipTests`, `-NoPush` ou `-AllowDirty` uniquement en cas de blocage identifie et consigner la raison dans le journal de session.
- Toujours considerer la branche distante comme source de verite; travailler sur une seule branche de fonctionnalite par sujet et pousser apres chaque session (`git push origin <branche>`).
- Verifier que `git status` reste propre avant de quitter un poste; le script echoue par defaut en cas de fichiers non commites (sauf usage explicite de `-AllowDirty`).
- Preferer `git worktree` ou des branches ephemeres plutot que des stashes pour des travaux longs afin de garder un etat reproductible.

### Alternative plus robuste
- Programmer `scripts/sync-workdir.ps1` (Task Scheduler/cron) sur les postes utilises frequemment pour rappeler les synchronisations.
- Coupler la CI (GitHub Actions) pour reconstruire et tester chaque push vers la branche de travail avant fusion.
- Activer `pre-commit` avec des hooks de formatage/lint afin d'eviter de pousser des artefacts temporaires.

---

## 13. Co-developpement multi-agents (Claude Code ? Codex)

### Principes fondamentaux
- **Egalite technique** : Claude Code et Codex sont des co-developpeurs de niveau ingenieur equivalent.
- **Modification croisee autorisee** : tout agent peut modifier n'importe quel fichier du depot.
- **Validation architecte** : l'architecte humain (FG) valide avant commit/push/deploy.
- **Communication asynchrone** : via Git (commits, branches) et documentation (passation).

### Lecture obligatoire avant toute session
1. `CODEV_PROTOCOL.md` : protocole complet de co-developpement.
2. `docs/passation.md` : derni?res 3 entr?es minimum (contexte, blocages, next actions).
3. `git status` et `git log --oneline -10` : etat actuel du depot.

### Passation de relais (handoff)
Chaque agent doit consigner systematiquement dans `docs/passation.md` :
- Date/heure (Europe/Zurich), agent (Claude Code | Codex).
- Fichiers modifies (liste exhaustive).
- Contexte et decisions prises.
- Actions recommandees pour le prochain agent.
- Blocages eventuels (dependances, tests echoues).

### Tests obligatoires avant validation
- [ ] Backend : `pytest` (ou sous-ensemble pertinent).
- [ ] Frontend : `npm run build`.
- [ ] Smoke tests : `pwsh -File tests/run_all.ps1`.
- [ ] Linters : `ruff check`, `mypy`.
- [ ] Documentation : mise a jour `docs/passation.md`, architecture si impactee.
- [ ] ARBO-LOCK : snapshot si creation/deplacement/suppression de fichiers.

### Zones de responsabilite suggerees (non bloquantes)
- **Claude Code** : Backend Python, architecture, tests, documentation technique.
- **Codex** : Frontend JavaScript, UI/UX, scripts PowerShell, documentation utilisateur.
- **Important** : ces zones sont indicatives. Tout agent peut intervenir partout.

### Ressources
- `CODEV_PROTOCOL.md` : protocole detaille.
- `docs/passation.md` : journal inter-agents.
- `docs/git-workflow.md` : workflow Git.
- `docs/workflow-sync.md` : synchronisation cloud/local.
