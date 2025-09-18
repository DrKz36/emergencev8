# Consignes pour les contributions agent

Ces instructions s'appliquent à tout le dépôt `emergencev8`.

## 1. Lecture des consignes
- Lire intégralement ce fichier (et tout `AGENTS.md` plus spécifique dans un sous-dossier) avant de modifier un fichier.
- Appliquer immédiatement toute nouvelle consigne découverte pendant la session.

## 2. Préparation de l'environnement
- Utiliser **Python 3.11** dans un virtualenv (`python -m venv .venv && source .venv/bin/activate`).
- Installer/mettre à jour les dépendances avec `python -m pip install --upgrade pip && pip install -r requirements.txt`.
- Utiliser **Node.js ≥ 18** (`nvm use 18` conseillé) et installer les dépendances web via `npm ci`.

## 3. Avant de coder
- Vérifier que `git status` est propre avant de commencer.
- Mettre à jour/configurer `.env.local` si les changements le nécessitent (clés API, tokens, allow/deny lists).
- S'assurer que les migrations ou initialisations nécessaires sont effectuées selon la documentation (scripts `run-local.ps1`, docs d'architecture, etc.).

## 4. Pendant la modification
- Respecter la structure des dossiers (`src/backend`, `src/frontend`, `docs`, ... ) et les conventions existantes.
- Créer les fichiers complémentaires (config/tests) requis par tout nouveau fichier ajouté.

## 5. Vérifications avant commit
- Backend : exécuter les linters/tests pertinents (par ex. `pytest`, `ruff`, `mypy`) lorsqu'ils sont requis par la portée des changements.
- Frontend : exécuter `npm run build` (et autres scripts spécifiés localement) lorsque du code frontend est modifié.
- Relire `git diff` pour éliminer secrets, artefacts ou modifications accidentelles.

## 6. Procédure Git
- Utiliser des messages de commit explicites (ex. `<type>: <résumé>` si applicable).
- Garder `git status` propre après chaque commit.
- Avant push : `git fetch && git rebase origin/main`, résoudre les conflits et relancer les tests si nécessaire.
- Pousser ensuite sur la branche (`git push origin <branche>`).

## 7. Vérifications supplémentaires
- Lancer les scripts de tests disponibles (`pwsh -File tests/run_all.ps1`) pour valider les endpoints backend critiques lorsque des modifications les touchent.
- Pour le frontend, vérifier que `npm run build` réussit et reste compatible avec la cible configurée par Vite.
- Si besoin de vérifier la parité avec l'environnement de production, construire l'image Docker locale (`docker build -t emergence-local .`).

## 8. Préparation de la PR
- Préparer un résumé des changements, des tests exécutés et des commandes utilisées.
- S'assurer que l'intégration continue passe (si accessible) après le push.

---

En appliquant systématiquement ces consignes, l'agent dispose d'une procédure standard pour éviter les problèmes de compatibilité et maintenir un workflow fluide.
