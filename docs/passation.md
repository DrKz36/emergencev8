# Passation Courante

## Backend & QA
- Backend verifie via `pwsh -File scripts/run-backend.ps1` (logs OK, WS et bannieres auth observes).
- `tests/run_all.ps1` : dernier passage indique OK (voir session precedente, aucun echec signale).

## Points livrees
- Capture QA de la banniere auth documentee dans `docs/ui/auth-required-banner.md` avec asset `docs/assets/ui/auth-banner-console.svg`.
- Test unitaire ajoute pour verrouiller `ensureCurrentThread()` -> `EVENTS.AUTH_REQUIRED` et garantir le payload QA.

## Suivi
- Conserver l'habitude d'utiliser `scripts/run-backend.ps1` avant la QA UI.
- Controler la configuration des remotes via `git remote -v` en debut de session et aligner `origin`/`codex` si besoin.
- Rejouer `npm test -- src/frontend/core/__tests__/app.ensureCurrentThread.test.js` en cas de modification auth/front.

## Sidebar to Conversations Migration (2025-09-24)
- Pass 1 complete: plan captured in `docs/ui/conversations-module-refactor.md` (scope, dependencies, accessibility notes).
- Pass 2 done: backend delete endpoint + API client/service updates (pytest `tests/backend/features/test_threads_delete.py`).
- Pass 3 complete: conversations module live in main content (nav entry, inline delete confirm, node tests on `ThreadsPanel.handleDelete`).
- Pass 4 next: run build + targeted Jest suite, capture new Conversations screenshots, rerun sync script for final handoff.


## Session 2025-09-25 - Debate metrics QA
- Tests: python -m pytest tests/backend/features/test_debate_service.py (2 passes) ; npm run build (vite ok, warning persists on ANIMATIONS export).
- Manual QA: simulated debate run (DebateService.run) -> 10 ws events (started, status updates, turn updates, result, ended); cost total 0.053200 USD with tokens 340/172 and by agent neo 0.0123, nexus 0.0222, anima 0.0187.
- UI follow-up: header shows progress + cost block; css wraps cost spans under 560px; next run full UI QA once backend is online.


## Session 2025-09-24 - Auth revocation QA
- Reprise backend via `pwsh -File scripts/run-backend.ps1` puis exécution `tests/run_all.ps1` : statut OK, endpoints accessibles.
- Vérification manuelle WS : réutiliser un token révoqué renvoie `ws:auth_required` (reason=`session_revoked`) lorsque la session WebSocket correspond au `sid` d'auth.
- Observation actuelle : les connexions WS gardant un `sessionId` distinct du `sid` ne sont pas encore coupées lors d'un logout (à corriger côté core/chat).
- 2025-09-26 : Correction livrée. Le handshake WS s'appuie désormais sur le `sid` vérifié (`AuthService.verify_token`) et `SessionManager` maintient les alias côté backend. Le client JS extrait ce `sid` du token afin d'aligner REST/WS, ce qui permet à `handle_session_revocation()` de couper les connexions actives après logout.

## Session 2025-09-25 - PR ws alias handoff
- PR ouverte `fix: align websocket session alias handling` (branche `fix/debate-chat-ws-events-20250915-1808` -> main).
- Description PR : résumé + tests (voir tmp/pr_body.md).
- CI GitHub Actions : statut non récupéré (API GitHub inaccessible sans jeton dans cet environnement, vérifier manuellement dès disponibilité).

## Session 2025-09-25 - QA Accueil + Auth
- Backend local lancé via `pwsh -File scripts/run-backend.ps1 -ListenHost 127.0.0.1` (via Start-Process) ; migrations appliquées, `src/backend/data/db/emergence_v7.db` régénérée.
- Stockage remis à plat pour la QA : allowlist vérifiée puis enrichie via `/api/auth/admin/allowlist` (dev bypass) avec `gonzalefernando@gmail.com` afin de tester le formulaire.
- Formulaire email (API) : `POST /api/auth/login` retourne 200 + token pour l'email allowlist (session active dans `auth_sessions`).
- Bannière "Connexion requise" : `npm test -- src/frontend/core/__tests__/app.ensureCurrentThread.test.js` passe après avoir neutralisé l'init DOM dans `components/modals.js`; capture déposée (`docs/assets/ui/auth-banner-20250925.png`) pour la prochaine passe UI.

### Pistes suivantes UI/Auth
- [FAIT 2025-09-26] Bootstrap DOM Node (`src/frontend/core/__tests__/helpers/dom-shim.js`) + relance de `npm test -- src/frontend/core/__tests__/app.ensureCurrentThread.test.js`.
- [FAIT 2025-09-26] `node scripts/qa/home-qa.mjs` rejoué (captures + console QA rafraîchies, `missingCount: 2` confirmé).
- Suivi: prévoir une passe QA manuelle backend hors-ligne prolongée pour valider la remise en place continue de `body.home-active` et mettre à jour `docs/ui/auth-required-banner.md` si le comportement évolue.



## Session 2025-09-26 - QA Accueil (clearToken)
- Scenario rejoue via node tmp/qa-auth-clear-check.mjs apres connexion (PID backend 504 tue par le script).
- Resultat : clearToken() declenche sur auth:missing, tokens storage/cookie sont purges, body.home-active repasse a true et le landing reste affiche sans reload.
- Metrics QA : missingCount incremente a 1 (overlay QA enregistre source=auth:missing).
- Console : plus de warning persistants; seul [WebSocket] Aucun ID token - connexion WS annulee apparait une fois lors de la reconnexion.
- Suite : rejouer le scenario en CI et planifier un test backend off (>1 min) pour confirmer l'absence de regressions.

## Session 2025-09-26 - Accueil email allowlist
- Module `features/home/home-module.js` : landing auth plein écran, formulaire email, appels `POST /api/auth/login`, intégration metrics QA.
- Refonte `src/frontend/main.js` : bascule automatique vers le landing sans token, bootstrap App/WS après succès, purge des tokens au logout.
- QA : `scripts/qa/home-qa.mjs` attend désormais `body.home-active` et capture l’état landing + overlay QA.
- Correctif: `main.js` réintroduit `clearToken()` pour purger les tokens navigateur lors d’un logout ou backend HS (supprime le warning console).
## Session 2025-09-26 - Auth password mode planning
- Objectif: préparer la bascule vers une authentification email + mot de passe sans dépendance GIS (mode dev).
- Étape 1: activer `AUTH_DEV_MODE=1` via `.env.local` et documenter le flux dev-only.
- Étape 2: concevoir la migration `auth_allowlist` (`password_hash`, `password_updated_at`) + script de seed pour l’admin.
- Étape 3: adapter `AuthService.login` et `/api/auth/login` pour accepter `{ email, password }` (bcrypt/argon2) tout en conservant l’allowlist.
- Étape 4: mettre à jour la landing front (`home-module.js`) avec champ mot de passe + messages i18n et ajuster l’API client.
- Étape 5: étendre les tests (`tests/backend/features/test_auth_login.py`, QA landing) et synchroniser la doc (`docs/architecture/30-Contracts.md`, `docs/ui/home-landing.md`, `docs/Memoire.md`).
- Étape 6: élargir l’allowlist aux bêta-testeurs via scripts dédiés une fois la mécanique validée.
