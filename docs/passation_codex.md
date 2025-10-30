## [2025-10-30 22:10 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.12
- **Nouvelle:** beta-3.3.13 (PATCH - Auth token test bundler compatibility)

### Fichiers modifiés
- `src/frontend/core/__tests__/auth.normalize-token.test.mjs`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Les jobs CI plantaient sur `npm run build` car Vite traitait `auth.normalize-token.test.js` comme module CommonJS, ce qui cassait l’analyse ESM (`import` rejeté). Il fallait renommer la suite pour la forcer en ESM pur et réaligner le versioning.

### Travail réalisé
- Renommage du test en `.test.mjs` et validation `node --test` spécifique pour prouver que la suite reste OK.
- Mise à jour des docs (changelog, sync, passation) et bump version `beta-3.3.13` + patch notes côté backend/frontend.
- Exécution `npm run build` pour confirmer que Vite n’avale plus le test en mode CommonJS.

### Tests
- ✅ `npm run build`
- ✅ `npm test -- src/frontend/core/__tests__/auth.normalize-token.test.mjs`

### Travail de Claude Code pris en compte
- RAS (pas d’interaction directe backend, juste respect du workflow versioning).

### Prochaines actions recommandées
1. Ajouter un exclude explicite des répertoires `__tests__` dans la config Vite pour éviter de refaire ce rename la prochaine fois.
2. Étendre la suite Node pour couvrir la persistance cookie/localStorage avec expire dates.

### Blocages
- Aucun.

## [2025-10-30 19:40 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.11
- **Nouvelle:** beta-3.3.12 (PATCH - Auth session continuity)

### Fichiers modifiés
- `src/frontend/core/auth.js`
- `src/frontend/core/state-manager.js`
- `src/frontend/core/websocket.js`
- `src/frontend/main.js`
- `src/frontend/core/__tests__/auth.normalize-token.test.js`
## [2025-10-30 22:45 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.11
- **Nouvelle:** beta-3.3.12 (PATCH - Bundle analyzer ESM compatibility)

### Fichiers modifiés
- `vite.config.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Les resets de session forçaient `auth.isAuthenticated` à faux dès que le WebSocket rafraîchissait l’ID session, ce qui relançait les modales d’auth et coupait la connexion WS. Les tokens `token=...` avec padding `=` étaient aussi jetés par la nouvelle normalisation.

### Travail réalisé
- Refactor `normalizeToken` pour supporter le padding `=` et découper correctement les préfixes `token=`, avec une suite `node:test` qui couvre Bearer/token=/quotes et la purge des entrées invalides.
- Ajout d’un mode `preserveAuth.isAuthenticated` dans `resetForSession()`, activation côté WebSocket et réaffirmation `auth.hasToken`/`auth.isAuthenticated` dans `refreshSessionRole()` pour garder l’état connecté.
- Synchronisation version `beta-3.3.12` (CHANGELOG, patch notes, versions frontend/backend, package.json) + build/test front OK.

### Tests
- ✅ `npm test`
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Respect du workflow versioning+patch notes instauré par Claude, aucun changement backend requis.

### Prochaines actions recommandées
1. QA staging/prod pour confirmer la disparition des `auth:missing` et des 4401 post-login.
2. Ajouter un test d’intégration StateManager/WebSocket pour valider la conservation d’`auth.isAuthenticated` lors d’un nouveau `sessionId`.
3. Surveiller Guardian/ProdGuardian pour repérer d’éventuelles boucles de reconnexion résiduelles.
Le job CI "Build frontend" cassait dès que `ANALYZE_BUNDLE=1` activait `rollup-plugin-visualizer`. Node >= 20 refuse `require()` sur un module ESM → `ERR_REQUIRE_ESM` et pipeline rouge.

### Travail réalisé
- Refactor `vite.config.js` en config asynchrone pour charger le plugin via `import()` dynamique uniquement lorsque l’analyse est demandée.
- Ajout d’un warning explicite si le plugin n’est pas présent ou incompatible afin de laisser le build poursuivre sans crash.
- Synchronisation version `beta-3.3.12`, patch notes et changelog alignés.

### Tests
- ✅ `npm run build`
- ✅ `npm test`

### Travail de Claude Code pris en compte
- Respect du workflow versioning + patch notes instauré, aucun conflit backend.

### Prochaines actions recommandées
1. Vérifier sur la CI (ou Guardian) que le build passe désormais avec `ANALYZE_BUNDLE=1`.
2. Documenter un script `npm run build:analyze` qui exporte `ANALYZE_BUNDLE=1` avant le build.
3. Prévoir un check lint pour prévenir l’utilisation de `require()` dans les modules ESM.

### Blocages
- Aucun.

---

## [2025-10-30 15:10 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.10
- **Nouvelle:** beta-3.3.11 (PATCH - Auth handshake stabilization)

### Fichiers modifiés
- `src/frontend/core/auth.js`
- `src/frontend/core/state-manager.js`
- `src/frontend/main.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`

### Contexte
Déconnexion immédiate après login : le client stockait parfois des tokens corrompus (`Bearer ...`, `token=...`, guillemets) et relançait la WebSocket avec une chaîne invalide → 4401, `auth:missing`, retour à l’écran d’accueil.

### Travail réalisé
- Ajout d’une normalisation stricte des tokens (regex JWT) + purge des valeurs invalides dans `sessionStorage`/`localStorage` + fallback cookie, ce qui évite de propager des `id_token` foireux.
- Ajout du flag `auth.isAuthenticated` dans le `StateManager`, le badge et le flux login/logout pour bloquer les prompts/modals tant que l’auth n’est pas réellement finalisée.
- Synchronisation version `beta-3.3.11`, patch notes + changelog à jour, build/tests front relancés.

### Tests
- ✅ `npm run build`
- ✅ `npm test`

### Travail de Claude Code pris en compte
- Respect du workflow versioning + patch notes instauré par Claude, aucun changement backend requis.

### Prochaines actions recommandées
1. QA manuelle sur staging/prod pour confirmer qu’aucun `auth:missing` ne surgit juste après login.
2. Ajouter un test Node ciblant `normalizeToken` pour verrouiller les formats futurs.
3. Observer Guardian/ProdGuardian pour confirmer la disparition des 4401 post-login.

### Blocages
- Aucun.

---

## [2025-10-30 09:30 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.9
- **Nouvelle:** beta-3.3.10 (PATCH - Sync script compatibility fix)

### Fichiers modifiés
- `scripts/sync_version.ps1`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Le script PowerShell `scripts/sync_version.ps1` était incapable d’extraire la version depuis `src/version.js` depuis que `VERSION` pointe vers `CURRENT_RELEASE.version`. Guardian bloque toujours la synchro tant que le script pète → il fallait lui apprendre à lire l’objet centralisé.

### Travail réalisé
- Mis à jour l’extraction regex pour cibler `CURRENT_RELEASE` (version/nom/date) avec fallback sur l’ancien format littéral.
- Nettoyé la sortie du script : liste réelle des fichiers touchés, dry-run plus clair, bump version `beta-3.3.10` + patch notes synchronisées.
- Rafraîchi changelog + fichiers de version backend/frontend + package.json pour refléter la nouvelle release tooling.

### Tests
- ✅ `npm run build`
- ✅ `npm test`

### Travail de Claude Code pris en compte
- Maintien du workflow de versioning obligatoire posé par Claude (un seul `CURRENT_RELEASE` partagé backend/frontend).

### Prochaines actions recommandées
1. Exécuter `scripts/sync_version.ps1` sur un environnement avec PowerShell pour valider la nouvelle extraction regex.
2. Ajouter un test Node qui échoue si `CURRENT_RELEASE` perd une des clefs attendues.
3. Finaliser le badge UI d’alerte vectorisation partielle (documents) pour clore la tâche P3.10.

### Blocages
- Absence de `pwsh` dans ce container → impossible de lancer le script PowerShell directement.

---

## [2025-10-29 22:30 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.8
- **Nouvelle:** beta-3.3.9 (PATCH - Version manifest merge fix)

### Fichiers modifiés
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Merge double (branches `codex/corrige-la-reponse-d-anima` + `codex/fix-document-upload-issue-in-production`) a foutu le bordel dans `CURRENT_RELEASE` : deux clefs `version`/`name` l’une à la suite de l’autre ⇒ Vite crashe (`Expected ',' got 'version'`).

### Travail réalisé
- Nettoyé les fichiers de version frontend/backend pour ne garder qu’un objet courant + patch notes valides.
- Aligné `package.json` et le changelog avec la nouvelle version `beta-3.3.9` en combinant les notes 3.3.7/3.3.8.
- Ajouté une entrée de changelog dédiée pour tracer le hotfix et éviter que ça se reproduise sans test.

### Tests
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Respect du process de versioning obligatoire (fichiers version + changelog + patch notes synchronisés) qu’il a posé.

### Prochaines actions recommandées
1. Brancher un check lint/simple test qui valide que `CURRENT_RELEASE` ne contient pas de clefs dupliquées (ex: test node).
2. Relancer `ruff`/`pytest` dès que les deps backend seront installées dans le container pour sécuriser la branche.
3. Préparer le badge UI pour signaler les vectorisations partielles (restant de la tâche documents).

### Blocages
- Toujours pas de deps backend (`fastapi`, `httpx`, etc.) → impossible de relancer la suite Python.

---

## [2025-10-29 19:45 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.7
- **Nouvelle:** beta-3.3.8 (PATCH - Document chunk throttling & warnings)

### Fichiers modifiés
- `src/backend/features/documents/service.py`
- `src/backend/features/documents/router.py`
- `src/frontend/features/documents/documents.js`
- `tests/backend/features/test_documents_vector_resilience.py`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`

### Contexte
Upload d’un document très long a saturé la vectorisation (trop de paragraphes → requête géante vers Chroma) et planté l’API. Il fallait limiter le nombre de chunks vectorisés, batcher les appels et avertir l’utilisateur sans 500.

### Travail réalisé
- Ajout d’une limite configurable de chunks (`DOCUMENTS_MAX_VECTOR_CHUNKS`) et vectorisation par lots côté backend, avec warning quand on dépasse la fenêtre indexée.
- Ré-indexation alignée sur le même mécanisme (purge + batching) et retour API enrichi (`indexed_chunks`, `total_chunks`, warning conservé).
- UI Documents : toast warning déclenché même quand l’upload/ré-indexation reste « succès » mais partielle.
- Nouveau test backend pour valider la limite de chunks et le batching.

### Tests
- ✅ `ruff check src/backend/`
- ⚠️ `pytest tests/backend/features/test_documents_vector_resilience.py` (KO – dépendance `httpx` manquante)
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Poursuite de la résilience entamée sur le mode READ-ONLY : on garde son statut `error` + warnings et on ajoute la limitation/batching.

### Prochaines actions recommandées
1. Installer les dépendances Python requises (`httpx`, `fastapi`, `aiosqlite`, etc.) pour exécuter `pytest` dans ce container.
2. Ajouter un badge/tooltip sur la liste des documents pour signaler visuellement les vectorisations partielles.
3. Implémenter un retry automatique de vectorisation lorsque le vector store redevient accessible.

### Blocages
- Pas de stack Python complète dans le container (`httpx` manquant), ce qui bloque l’exécution de la suite `pytest`.

## [2025-10-29 16:20 CET] - Agent: Codex GPT

### Fichiers modifiés
- `src/backend/features/documents/service.py`
- `src/backend/features/documents/router.py`
- `src/frontend/features/documents/documents.js`
- `tests/backend/features/test_documents_vector_resilience.py`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`

### Contexte
Upload d’un document long a explosé côté prod parce que Chroma était en mode READ-ONLY : on se prenait un 500 et la liste des documents ne chargeait plus. Objectif : garder l’upload, avertir l’utilisateur et éviter de planter quand l’index vectoriel est HS.

### Travail réalisé
- DocumentService tolère maintenant l’indispo du vector store : stockage du fichier + chunks, statut `error` avec message et réponse HTTP qui remonte l’avertissement.
- Router + UI récupèrent `vectorized`/`warning` pour afficher un toast warning au lieu d’un faux succès et conserver la fiche dans la liste.
- Ajout d’un test async qui vérifie que l’upload passe en mode READ-ONLY sans planter.
- Version bump `beta-3.3.7`, changelog + patch notes synchronisés.

### Tests
- ⚠️ `mypy src/backend/` (KO – dépendances type `fastapi`, `pydantic`, `httpx`, `aiosqlite` absentes)
- ⚠️ `pytest tests/backend/` (KO – imports `fastapi`, `httpx`, `aiosqlite` manquants)
- ✅ `ruff check src/backend/`
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Néant spécifique ; aucun conflit avec ses derniers commits backend.

### Prochaines actions recommandées
1. Installer les deps `fastapi`, `pydantic`, `aiosqlite`, `httpx`, `dependency-injector` dans l’environnement de CI pour faire passer mypy/pytest.
2. Ajouter un message UI sur la carte document (tooltip) pour expliquer la marche à suivre en cas de statut `error`.
3. Prévoir une tâche de ré-indexation automatique quand Chroma redevient accessible.

### Blocages
Environnement container sans libs Python (fastapi/pydantic/httpx/aiosqlite) → mypy et pytest échouent dès l’import.

## [2025-10-29 14:30 CET] - Agent: Codex GPT

### Fichiers modifiés
- `src/frontend/features/settings/settings-about.js`
- `src/frontend/features/settings/settings-about.css`
- `src/frontend/core/version-display.js`
- `src/frontend/version.js`
- `src/version.js`
- `docs/story-genese-emergence.md`
- `CHANGELOG.md`
- `package.json`

### Contexte
Les infos techniques du module **À propos** (stats, progression, dépendances) étaient figées sur l’état d’octobre 2025 et la genèse mentionnait à tort un premier contact LLM en 2024. Il fallait réaligner l’UI et la doc avec la réalité (premiers prototypes en 2022) tout en respectant le workflow versioning obligatoire.

### Travail réalisé
- Rafraîchi la grille des modules/services + stats du module À propos avec les compteurs actuels (fichiers, tests, dépendances, LOC, rappel 2022).
- Synchronisé `featuresDisplay` avec la progression réelle (18/23 • 78%), mis à jour patch notes/Full changelog backend & frontend et incrémenté la version `beta-3.3.6`.
- Corrigé `docs/story-genese-emergence.md` pour intégrer la phase 2022-2023 (GPT-3, ChatGPT beta) et consigner la timeline exacte.
## [2025-10-29 11:40 CET] - Agent: Codex GPT

### Fichiers modifiés
- `src/frontend/styles/components/modals.css`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Le modal « Bienvenue dans le module Dialogue » affichait un halo rectangulaire plus large que la carte elle-même, parce que le container héritait d’un padding + d’un backdrop partiel. Sur desktop c’était particulièrement visible (carte décalée, overlay pas rond), et en portrait mobile ça faisait un double encadrement.

### Travail réalisé
- Suppression du padding sur `#conversation-choice-modal` et renforcement du blur plein écran pour avoir un seul overlay uniforme.
- Revue des largeurs : `modal-content` reste clampé à 420 px mais je force désormais `calc(100% - 64px)` (desktop) / `calc(100% - 32px)` (mobile) pour garder des marges régulières sans ressusciter le faux cadre.
- Ajustement de la build mobile (`margin: 0 16px`) afin que la carte respire sans coller aux bords.

### Tests
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Aucun changement concurrent identifié sur la zone Settings/About ou sur la documentation de genèse.

### Prochaines actions recommandées
1. QA visuelle du module À propos (desktop + mobile) pour vérifier le rendu des hints et la lisibilité des nouvelles stats.
2. Mettre à jour les captures/screens si elles sont utilisées dans la communication produit.
- Aucun impact sur ses fichiers ; CSS localisé dans `components/modals.css`.

### Prochaines actions recommandées
1. QA visuelle sur desktop + téléphone pour confirmer qu'il ne reste plus d'encadré fantôme.
2. Affiner le blur ou la teinte de l'overlay si tu veux un rendu encore plus discret.

### Blocages
- Aucun.

## [2025-10-29 11:05 CET] - Agent: Codex GPT

### Fichiers modifiés
- `src/frontend/core/app.js`
- `src/frontend/features/chat/chat.css`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
En mode portrait mobile, le footer du chat restait suspendu au-dessus de la navbar bleue. Le padding global appliqué à `.app-content` pour la navigation mobile ajoutait un gap inutile, et le module n'avait aucun indicateur permettant au CSS de savoir quel onglet était actif.

### Travail réalisé
- Injection d’un marquage `is-module-<id>` sur `app-content` + `module-active-<id>` / `data-active-module` sur `<body>` afin d’exposer le module courant aux feuilles de style.
- Override ciblé côté `chat.css` pour réduire le `padding-bottom` aux seuls `safe-area` lorsque le chat est actif en portrait, tout en conservant les compensations `env()` pour le footer fixe.
- Vérifications rapides du layout afin de s’assurer que les autres breakpoints restent inchangés.

### Tests
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Aucun changement récent côté Claude sur `app.js` ou le CSS mobile ; pas de conflit détecté.

### Prochaines actions recommandées
1. Valider sur devices physiques (iPhone + Pixel) que le footer colle bien à la navbar, safe area comprise.
2. Guetter d’éventuelles régressions sur les autres modules qui s’appuyaient sur l’ancien padding global.

### Blocages
- Aucun.

## [2025-10-29 09:45 CET] - Agent: Codex GPT

### Fichiers modifiés
- `scripts/setup-codex-cloud.sh`
- `.gitignore`
- `PROMPT_CODEX_CLOUD.md`
- `docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Le bootstrap Codex Cloud devait être rendu autonome : après exécution, l'agent cloud n'avait toujours pas `node`/`npm` dans le PATH et la doc ne précisait pas comment récupérer un shell prêt à l'emploi.

### Travail réalisé
- Ajout d'une configuration complète côté script : alias `nvm default`, relocalisation des binaires (`node`, `npm`, `npx`, `corepack`) vers `.venv/bin`, génération de `.codex-cloud/env.sh` et hook automatique (`.bashrc`, `.profile`, `.zshrc`).
- Ajout d'un message final pour rappeler `source .venv/bin/activate` et création d'une entrée `.gitignore` pour ignorer `.codex-cloud/`.
- Mise à jour des prompts Cloud afin d'indiquer la présence du nouvel helper et la marche à suivre pour recharger l'environnement.
- Création de `PROMPT_CODEX_ALTER_EGO.md` + référence dans `docs/PROMPTS_AGENTS_ARCHITECTURE.md` pour qu'un backup Codex fasse un retour immédiat en cas de blocage.

### Tests
- ⚠️ `bash scripts/setup-codex-cloud.sh` (non exécuté ici : environnement CLI sans bash/WSL disponible)

### Travail de Claude Code pris en compte
- Aucun changement récent côté Claude sur ces fichiers ; simple durcissement du script introduit précédemment.

### Prochaines actions recommandées
1. Lancer `bash scripts/setup-codex-cloud.sh` dans Codex Cloud pour valider les symlinks et le sourcing automatique.
2. Vérifier que Guardian/AutoSync ne signalent plus de fichiers non suivis après exécution (merci à l'entrée `.gitignore`).
3. Partager le nouveau prompt alter ego au backup et checker qu'il documente bien les blocages via `@Codex GPT -> feedback needed`.

### Blocages
- Impossible d'exécuter le script dans ce CLI Windows (absence de bash) : validation à réaliser côté environnement Linux.

## [2025-10-28 23:40 CET] - Agent: Codex GPT

### Fichiers modifiés
- `src/frontend/styles/components/modals.css`
- `src/backend/features/auth/models.py`
- `src/backend/features/auth/service.py`
- `tests/backend/features/test_auth_allowlist_snapshot.py`
- `stable-service.yaml`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
- Le popup de bienvenue du module Dialogue restait décentré malgré les précédents correctifs.
- Chaque redéploiement Cloud Run remettait l'allowlist à zéro (seul l'admin seed restait), bloquant l'onboarding des comptes ajoutés en production.

### Travail réalisé
- Refondu `modals.css` pour garantir centrage strict, largeur limitée et style aligné sur la capture fournie.
- Ajouté un snapshot Firestore dans `AuthService` + configuration `stable-service.yaml` afin de restaurer l'allowlist à chaque bootstrap.
- Écrit le test `test_auth_allowlist_snapshot.py` (stub Firestore) et relancé `test_auth_admin.py` + `npm run build` pour valider les flux critiques.

### Tests
- `pytest tests/backend/features/test_auth_allowlist_snapshot.py`
- `pytest tests/backend/features/test_auth_admin.py`
- `npm run build`

### Travail de Claude Code pris en compte
- Aucun changement de Claude impactant ces zones pendant la session (backend/front isolés).

### Prochaines actions recommandées
1. Vérifier que la révision Cloud Run dispose des permissions Firestore + secrets requis avant déploiement.
2. QA manuelle des autres modales (Settings/Admin/Docs) sur desktop et mobile pour détecter d'éventuelles régressions visuelles.

### Blocages
- `curl http://localhost:8000/api/sync/status` → `Recv failure: Connection was aborted` (dashboard AutoSync indisponible durant la session).

## [2025-10-28 12:40 CET] - Agent: Codex GPT

### Fichiers modifiés
- `src/frontend/styles/components/modals.css`

### Contexte
Recentrer le popup de reprise de conversation et supprimer le halo sombre pour coller au design attendu.

### Travail réalisé
- Recréation complète de `modals.css` avec carte 320 px, centrage stricte top/left et animation douce sans halo bleu.
- Renforcement de la lisibilité (couleurs primaires, suppression du glow) tout en conservant le clic backdrop et les transitions.
- Ajout d'une variante `modal-lg` partagée pour les écrans plus larges (settings, documentation) afin d'éviter les régressions visuelles.

### Tests
- ✓ `npm run build`

### Travail de Claude Code pris en compte
- Aucun changement backend récent, intervention purement front/UI.

### Prochaines actions recommandées
1. QA manuelle (desktop + mobile) pour valider le centrage, le rendu sans fond bleu et la fermeture par clic backdrop.
2. Vérifier que les autres modales (Settings, Webhooks, Documentation) conservent leur apparence attendue avec la nouvelle feuille.

### Blocages
- Aucun.

## [2025-10-28 08:22 CET] - Agent: Codex GPT

### Fichiers modifiés
- `src/frontend/features/chat/chat.js`
- `src/frontend/main.js`
- `src/frontend/features/settings/settings-about.js` (auto-sync à confirmer)
- `src/frontend/features/settings/settings-about.css` (auto-sync à confirmer)
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Forcer le retour systématique sur le module Dialogue après connexion et garantir l'affichage du popup de reprise/conversation nouvelle, même lorsque ThreadsPanel hydrate en arrière-plan.

### Travail réalisé
- Nouveau flag `_awaitingConversationChoice` + cache `_pendingThreadDetail` pour ignorer `THREADS_SELECTED` tant que l'utilisateur n'a pas choisi tout en conservant la data.
- Reset explicite de l'état (`chat.threadId`, `threads.currentId`) à chaque login, logs détaillés et émission `THREADS_REFRESH_REQUEST` pour tenir les compteurs à jour.
- `_resumeLastConversation` réutilise désormais les données en cache si ThreadsPanel hydrate pendant l'attente ; `_createNewConversation` nettoie les pending states.
- Ajustements UI : overlay modal transparent + bouton `Reprendre` en `btn-secondary` pour un popup centré plus propre.
### Tests
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Aucun changement backend, simple conformité aux consignes existantes.

### Prochaines actions recommandées
1. QA manuelle (desktop + mobile) du flux de connexion pour valider l'apparition du popup + blocage des hydrations auto.
2. Décider du sort des modifications auto sur `settings-about`.
3. Évaluer un test automatisé (Playwright) couvrant la reprise de conversation.

### Blocages
Aucun, seulement un point de vigilance sur les fichiers `settings-about` modifiés automatiquement.


### Fichiers modifiés
- `src/frontend/features/chat/chat.js`
- `src/frontend/main.js`
- `src/frontend/features/settings/settings-about.js` (mise à jour auto à confirmer)
- `src/frontend/features/settings/settings-about.css` (mise à jour auto à confirmer)
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Forcer le retour systématique sur le module Dialogue après connexion et garantir l'affichage du popup de reprise/conversation nouvelle, même lorsque les threads sont déjà cachés en cache.

### Travail réalisé
- Ajout d'un appel explicite à `App.showModule('chat')` côté `ensureApp()` pour overrider le module précédent lors d'une nouvelle session.
- Refactor `ChatModule` : nouveau scheduler `_scheduleConversationPromptCheck`, reset des flags `_initialModalChecked` / `_shouldForceModal`, et écoute de `auth:login:success` + `ui:auth:restored` pour relancer la vérification conversation.
- Nettoyage des promesses de bootstrap + teardown du modal pour réinitialiser l'état à chaque connexion.
- Observation des modifications auto-générées dans `settings-about` (laisser visible pour revue).

### Tests
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Aucun changement récent impactant le front, simple respect du protocole suivant les docs existantes.

### Prochaines actions recommandées
1. QA manuelle (desktop + mobile) du flux de connexion pour valider navigation + popup.
2. Décider du sort des changements auto sur `settings-about` (les revert si non souhaités).
3. Évaluer un test automatisé (Playwright) couvrant la reprise de conversation.

### Blocages
Aucun, seulement un point de vigilance sur les fichiers `settings-about` modifiés automatiquement.

# Journal de Passation — Codex GPT

**Archives >48h:** Voir `docs/archives/passation_archive_*.md`

**RÈGLE:** Ce fichier contient UNIQUEMENT les entrées des 48 dernières heures.
**Rotation:** Entrées >48h sont automatiquement archivées.

---

## ✅ [2025-10-27 21:05] — Agent: Codex GPT

### Version
- **Ancienne:** beta-3.2.1
- **Nouvelle:** beta-3.2.1 (inchangée)

### Fichiers modifiés
- `src/backend/features/memory/unified_retriever.py`
- `src/backend/main.py`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
- La CI backend pétait encore : `_get_ltm_context` renvoyait des concepts vides (mock AsyncMock non awaité) et Ruff signalait `vector_ready` jamais utilisé dans `/ready`.

### Travail réalisé
1. Détecté les résultats awaitables dans `_get_ltm_context` via `inspect.isawaitable` et attendu `query_weighted` pour corriger les tests `UnifiedMemoryRetriever`.
2. Supprimé la variable `vector_ready` inutilisée dans l’endpoint `/ready` (Ruff F841).

### Tests
- ✅ `pytest tests/backend/features/test_unified_retriever.py`
- ✅ `ruff check src/backend`

### Travail de Claude Code pris en compte
- Aucun impact direct sur ses livraisons ; corrections ciblées CI backend.

### Prochaines actions recommandées
1. Valider le prochain run GitHub Actions Backend Tests (Python 3.11).
2. Étendre le pattern `isawaitable` aux autres appels vectoriels si on ajoute des mocks async.

### Blocages
- Aucun.

---

## ✅ [2025-10-27 20:05] — Agent: Codex GPT

### Version
- **Ancienne:** beta-3.2.1
- **Nouvelle:** beta-3.2.1 (inchangée)

### Fichiers modifiés
- `src/frontend/core/__tests__/app.ensureCurrentThread.test.js`
- `src/frontend/core/__tests__/helpers/dom-shim.js`
- `src/frontend/core/__tests__/state-manager.test.js`
- `src/frontend/features/chat/__tests__/chat-opinion.flow.test.js`
- `src/frontend/shared/__tests__/backend-health.timeout.test.js`
- `src/frontend/shared/backend-health.js`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
- Stabilisation de la suite `node --test` après l’ajout du fallback `AbortController` : DOM manquant, mocks incomplets et tests StateManager basés sur `done()` plantaient régulièrement.

### Travail réalisé
1. Ajout du helper `withDomStub()` dans le test opinion pour simuler `document`/`requestAnimationFrame` et alignement des assertions sur le bucket reviewer.
2. Refactor des tests StateManager sur promesses (plus de `done()` double) + coalescing explicite pour `get()`.
3. Stub `api.listThreads` dans `ensureCurrentThread` + extension du `dom-shim` pour exposer `localStorage/sessionStorage` et `requestAnimationFrame`, puis validation `npm run test` + `npm run build`.

### Tests
- ✅ `npm run test`
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Respect des conventions récentes (bucket reviewer, comportement `get`) sans toucher au backend.

### Prochaines actions recommandées
1. Factoriser un stub `localStorage` partagé si d’autres suites en ont besoin.
2. QA Safari 16 / Chrome 108 pour confirmer la disparition des délais du loader.

### Blocages
- Aucun. Warnings `localStorage` disparus grâce au shim.

---

## ✅ [2025-10-27 19:20] — Agent: Codex GPT

### Version
- **Ancienne:** beta-3.2.1
- **Nouvelle:** beta-3.2.1 (inchangée)

### Fichiers modifiés
- `src/frontend/shared/__tests__/backend-health.timeout.test.js`
- `src/frontend/shared/backend-health.js`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
- Les navigateurs dépourvus d’`AbortSignal.timeout` (Safari < 17, Chromium/Firefox anciens) faisaient planter le health-check `/ready`, bloquant le bootstrap.

### Travail réalisé
1. Création d’un test `node:test` qui retire `AbortSignal.timeout`, stub `setTimeout`/`fetch` et vérifie le cleanup du fallback `AbortController`.
2. Ajustement du helper `backend-health` pour annoter et nettoyer systématiquement le timeout.

### Tests
- ✅ `npm run build`
- ❌ `npm run test` (suite Node encore instable avant le fix 20:05 CET)

### Travail de Claude Code pris en compte
- Aucun impact backend détecté ; modification purement front/test.

### Prochaines actions recommandées
1. Stabiliser `node --test` (réalisé à 20:05 CET — voir entrée ci-dessus).
2. QA manuelle Safari 16 / Chrome 108 pour confirmer la réduction du délai loader.

### Blocages
- Tests Node échouent encore (DOM/mocks manquants) — résolus dans l’entrée suivante.

---

## [2025-10-26 18:10] — Agent: Codex GPT

### Version
- **Ancienne:** beta-3.1.0
- **Nouvelle:** beta-3.1.1 (PATCH - fix modal reprise conversation)

### Fichiers modifiés
- `src/frontend/features/chat/chat.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `docs/passation_codex.md`
- `AGENT_SYNC_CODEX.md`

### Contexte
Fix bug modal reprise conversation qui ne fonctionnait pas après connexion.
Ajout attente explicite sur événements `threads:*` avant affichage modal.
Reconstruction du modal quand conversations arrivent pour garantir wiring bouton "Reprendre".

### Tests
- ✅ `npm run build`

### Versioning
- ✅ Version incrémentée (PATCH car bugfix)
- ✅ CHANGELOG.md mis à jour
- ✅ Patch notes ajoutées

### Prochaines actions recommandées
1. Vérifier côté backend que `threads.currentId` reste cohérent avec reprise utilisateur
2. QA UI sur l'app pour valider flux complet (connexion → modal → reprise thread)
3. Finir tests PWA offline/online (P3.10 - reste 20%)

### Blocages
Aucun.

---

## [2025-10-26 18:05] — Agent: Codex GPT

### Version
- **Ancienne:** beta-3.0.0
- **Nouvelle:** beta-3.1.0 (MINOR - lock portrait mobile + composer spacing)

### Fichiers modifiés
- `manifest.webmanifest`
- `src/frontend/main.js`
- `src/frontend/features/chat/chat.css`
- `src/frontend/styles/overrides/mobile-menu-fix.css`

### Contexte
Verrouillage orientation portrait pour PWA mobile avec overlay avertissement en mode paysage.
Ajustement zone de saisie chat pour intégrer safe-area iOS et assurer accès au composer sur mobile.
Amélioration affichage métadonnées conversation et sélecteurs agents en mode portrait.

### Tests
- ✅ `npm run build`

### Versioning
- ✅ Version incrémentée (MINOR car nouvelle feature UX)
- ✅ CHANGELOG.md mis à jour
- ✅ Patch notes ajoutées

### Prochaines actions recommandées
1. QA sur device iOS/Android pour valider overlay orientation et padding composer
2. Vérifier que guard portrait n'interfère pas avec mode desktop (résolution > 900px)
3. Ajuster UX de l'overlay selon retours utilisateur

### Blocages
Aucun.

---

**Note:** Pour historique complet, voir `docs/archives/passation_archive_2025-10-01_to_2025-10-26.md`
## [2025-10-29 15:40 CET] - Agent: Codex GPT

### Version
- **Ancienne:** beta-3.3.6
- **Nouvelle:** beta-3.3.7 (PATCH - Cross-agent opinion routing fix)

### Fichiers modifiés
- `src/frontend/features/chat/chat.js`
- `src/frontend/features/chat/__tests__/chat-opinion.flow.test.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Contexte
Les avis demandés à un agent (boutons d’opinion) réapparaissaient dans le chat du reviewer (ex. Anima) au lieu de rester dans le fil de l’agent évalué (ex. Nexus), ce qui casse la lecture croisée en prod.

### Travail réalisé
- Inversé le routage côté `chat.js` pour prioriser l’agent source dans `_determineBucketForMessage`, avec fallback sur l’agent cible puis le reviewer.
- Aligné la suite `chat-opinion.flow.test.js` sur le nouveau bucket attendu (thread de l’agent évalué).
- Incrémenté la version `beta-3.3.7`, synchronisé patch notes frontend/backend + changelog.
- Journal & sync docs mis à jour avec la session.

### Tests
- ✅ `npm run build`
- ✅ `npm run test`

### Travail de Claude Code pris en compte
- Aucun conflit : le backend expose déjà `source_agent_id`, rien à changer côté Claude.

### Prochaines actions recommandées
1. QA rapide en prod/staging : demander un avis Anima sur un message Nexus et vérifier que la réponse reste dans le fil Nexus.
2. Vérifier si l’UI doit afficher un badge spécifique pour différencier les avis dans le thread source.

### Blocages
- Aucun.

