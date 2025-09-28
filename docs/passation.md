## Session 2025-09-27 - Migration session isolation
- Migration `20250928_session_isolation.sql` rendue idempotente (suppression des `ALTER TABLE` + propagation vers `core/migrations`).
- Stockage local remis a zero (`src/backend/data/db/` + `src/backend/data/vector_store/`) puis backend relance via `pwsh -File scripts/run-backend.ps1`; toutes les migrations passent sans stacktrace.
- Nouvelle base SQLite regeneree; `migrations` contient bien l'entree `20250928_session_isolation.sql`.

# Passation Courante

## Backend & QA
- Backend verifie via `pwsh -File scripts/run-backend.ps1` (logs OK, WS et bannieres auth observes).
- Utiliser `python scripts/seed_admin.py --email <admin> --password <motdepasse>` pour initialiser ou mettre a jour le mot de passe admin en local.
- `tests/run_all.ps1` : dernier passage indique OK (voir session precedente, aucun echec signale).
- `scripts/smoke/smoke-ws-rag.ps1 -SessionId ragtest124 -MsgType chat.message -UserId "smoke_rag&dev_bypass=1"` : OK (27/09) — flux `ws:chat_stream_end` (OpenAI gpt-4o-mini) + upload document_id=57 sans 5xx. Logs `#<-` → `docs/assets/memoire/smoke-ws-rag.log`.
- `scripts/smoke/smoke-ws-rag.ps1 -SessionId ragtest-ws-send-20250927 -MsgType ws:chat_send -UserId "smoke_rag&dev_bypass=1"` : KO (27/09) — handshake accepté mais réponse `ws:error` (`Type inconnu: ws:chat_send`). Logs `#<-` → `docs/assets/memoire/smoke-ws-rag-ws-chat_send.log`.
- `scripts/smoke/smoke-ws-3msgs.ps1 -SessionId ragtest-3msgs-20250927 -MsgType chat.message -UserId "smoke_rag&dev_bypass=1"` : OK (27/09) — 3 messages consécutifs, `ws:chat_stream_start` x3 puis `ws:chat_stream_end`; aucun HTTP 5xx côté documents/uploads (`backend.err.log` inchangé). Logs `#<-` → `docs/assets/memoire/smoke-ws-3msgs.log`.
- Vérification UI nav rôle (2025-09-30) : scénario admin → logout → membre (`fernando36@bluewin.ch`). Après reconnexion, la sidebar doit exclure `Mémoire` et `Admin` et le bandeau afficher `Membre (fernando36@bluewin.ch)`. Capture à archiver : `docs/assets/passation/auth-role-reset.png`.
- Module Admin – Sessions (2025-09-30) : depuis l'onglet Admin, vérifier que le bloc Sessions liste les connexions actives (session_id, email, IP, dates). Rafraîchir via le bouton dédié et confirmer qu'un membre connecté apparait avec le statut Actif.
- `scripts/smoke/smoke-health.ps1 -BaseUrl https://emergence-app-486095406755.europe-west1.run.app` : OK (27/09 18:09 UTC) -> 200 `{ "status": "ok" }` sur revision `emergence-app-00256-jxh`.
- `scripts/smoke/smoke-memory-tend.ps1 -BaseUrl https://emergence-app-486095406755.europe-west1.run.app -UserId "smoke_rag&dev_bypass=1" -SessionId cloud-smoke-memory-20250927` : OK (27/09) -> `status=success`, `message="Aucune session a traiter."`.
- Test WSS Cloud Run (27/09) : envelope `chat.message` (session `cloud-wss-rag-20250927`, query `user_id=smoke_rag&dev_bypass=1`) -> `ws:rag_status` `searching` puis `found`, `ws:model_info` (`openai gpt-4o-mini`), flux complet jusqu'a `ws:chat_stream_end`. La tentative legacy `ws:chat_send` via `smoke-wss-cloudrun.ps1` retourne `ws:error` (`Type inconnu`), a realigner.
- Le tableau allowlist du module *Admin* expose desormais un bouton `Supprimer` par entree : confirmation navigateur, appel `DELETE /api/auth/admin/allowlist/{email}`, toast `Entree supprimee.` puis rechargement de la pagination active.

## Observabilite & logs (2025-09-27)
- `gcloud run services describe emergence-app --region europe-west1` : revision `emergence-app-00256-jxh` Ready (100 % traffic), tag `canary` pointe sur `emergence-app-00279-kub`.
- `gcloud logging read --freshness=1h --limit=200` filtre `service_name=emergence-app` : aucune entree `httpRequest.status >= 500`.
- Plus de 404 Gemini depuis le passage de `DEFAULT_GOOGLE_MODEL` sur `models/gemini-2.5-flash` (les anciens alias `models/gemini-1.5-flash*` sont maintenant mappés automatiquement). Surveiller `gcloud logging read --freshness=1h --limit=200` (aucune entree `google.api_core.exceptions.NotFound`) et controler les frames `ws:model_info` (`provider=google`, `model=models/gemini-2.5-flash`).

## Auth allowlist - mots de passe (2025-09-27)
- Module *Admin* cote frontend (navigation principale) reserve aux comptes `role=admin`. La liste est paginee, filtrable (`Actives`, `Revoquees`, `Toutes`) et propose une recherche email/note + resumes (`total`, `page`). Les toasts front confirment les sauvegardes et la copie du mot de passe genere.
- `GET /api/auth/admin/allowlist` expose maintenant `status=active|revoked|all`, `search`, `page`, `page_size` et renvoie `{ items, total, page, page_size, has_more, status, query }`. Le flag historique `include_revoked=true` reste accepte pour la compatibilite.
- `POST /api/auth/admin/allowlist` continue d'accepter `{ email, role?, note?, password?, generate_password? }` et retourne `{ entry, clear_password?, generated }`. Lorsque `generate_password=true`, l'audit ajoute `allowlist:password_generated` (longueur consigne dans `metadata.password_length`).
- Toujours initialiser/rafraichir les admins via `scripts/seed_admin.py` avant de communiquer le formulaire aux testeurs; la commande est idempotente et journalisee (`allowlist:password_set`).

### Quickstart QA - flux admin → generation → communication
1. `pwsh -File scripts/run-backend.ps1` puis `python scripts/seed_admin.py --email <admin> --password <secret>` pour garantir un acces admin valide.
2. Connexion UI avec le compte admin, onglet *Admin*. Verifier le resume (`total`, filtre `Actives`) et que la recherche vide affiche la pagination (`Page 1 sur 1`).
3. Ajouter un testeur `qa+<date>@example.com` avec une note, valider le toast `Entree mise a jour.` puis filtrer `Revoquees` = 0, `Actives` >= 1.
4. Utiliser `Generer un mot de passe` sur la ligne nouvellement creee : le panneau affiche le secret, le bouton *Copier* remonte le toast `Copie dans le presse-papiers.` et `password_updated_at` est renseigne. Capturer l'ecran (`docs/assets/admin/qa-password-generated.png`).
5. Se connecter avec le compte testeur et le mot de passe genere : `POST /api/auth/login` doit reussir, `auth_sessions` contient la session active. Relancer `pytest tests/backend/features/test_auth_admin.py` pour valider les audits (`allowlist:password_generated`).
6. Basculer sur `Toutes`, utiliser la recherche (email/note) pour reduire la liste et verifier la mise a jour du resume. Si une entree est supprimee via `DELETE /api/auth/admin/allowlist/{email}`, passer en filtre `Revoquees` pour controler le badge et l'horodatage.
   - Optionnel : `npm run test -- src/frontend/features/admin/__tests__/auth-admin-module.test.js` pour valider les gardes UI de recherche/pagination.

## Plan de deploiement - allowlist mots de passe
1. Deployer la version backend (FastAPI) et verifier au demarrage que les logs confirment la presence des colonnes `auth_allowlist.password_hash` / `password_updated_at` (DDL auto via `create_tables`).
2. Pour chaque environnement, executer `python scripts/seed_admin.py --email <admin> --password <motdepasse>` afin d'initialiser les comptes admin existants (idempotent, journalise).
3. Depuis le module *Admin*, generer ou saisir les nouveaux mots de passe pour les testeurs (`Generate password`) et consigner `password_updated_at`.
4. Communiquer les identifiants mis a jour via un canal securise, demander aux testeurs de se deconnecter/reconnecter pour invalider les anciens tokens.
5. QA post-deploiement : tester `POST /api/auth/login`, verifier l'apparition de l'entree dans la liste (colonne `password_updated_at`) et rejouer `tests/backend/features/test_auth_admin.py`.

## Points livrees
## Points livrees
- Capture QA de la banniere auth documentee dans `docs/ui/auth-required-banner.md` avec asset `docs/assets/ui/auth-banner-console.svg`.
- Test unitaire ajoute pour verrouiller `ensureCurrentThread()` -> `EVENTS.AUTH_REQUIRED` et garantir le payload QA.

## Suivi
- Le module « Mémoire » est désormais réservé aux admins et intègre la liste des conversations pour faciliter la revue des threads.
- Nouvel accès rapide « Mémoire » dans chaque agent du module Chat : tester qu’il lance bien memory:tend sur le thread actif.
- Mettre a jour `scripts/smoke/smoke-wss-cloudrun.ps1` pour envoyer `chat.message` (RAG) et consigner les evenements attendus.
- Confirmer que la configuration Gemini reference `models/gemini-2.5-flash` (les alias historiques `gemini-1.5-flash*` restent acceptes) afin d'eviter les 404 dans `MemoryAnalyzer`.
- Planifier le prochain chantier canary (WS/RAG) en s'appuyant sur la revision `emergence-app-00256-jxh` et la route taggee `canary`.
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

### QA - Roles & navigation
1. Se connecter avec un compte admin : confirmer la presence des modules `Memoire` et `Admin` dans la navigation, puis ouvrir un chat pour generer un evenement `ws:model_info` (noter `provider`/`model`).
2. Se deconnecter via le bouton header : verifier dans `localStorage` (cle `emergenceState-V14`) que `auth.role` repasse a `member`, que `session.id` et `websocket.sessionId` sont `null`, et que l'UI affiche a nouveau l'ecran d'accueil.
3. Se reconnecter avec un compte membre : controler que seuls les modules de base (`Dialogue`, `Documents`, `Debats`, `A propos`, `Cockpit`) restent visibles et que l'onglet actif revient sur `Dialogue`.
4. Depuis DevTools > Application > Storage, relire `emergenceState-V14` pour confirmer que `auth.role` et `chat.authRequired` sont respectivement `member` et `false`, sans residus de navigation admin.
5. Capturer la barre de navigation (etat membre) et un extrait Console montrant `ws:model_info` avec `models/gemini-2.5-flash` pour alimenter la checklist QA.


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
- État : authentification email + mot de passe (JWT local) déployée, sans dépendance GIS.
- Étape 1: activer `AUTH_DEV_MODE=1` (et optionnellement `AUTH_DEV_DEFAULT_EMAIL`) via `.env.local`, puis valider le flux d'auto-login (plus d'overlay Home).
- Étape 2: concevoir la migration `auth_allowlist` (`password_hash`, `password_updated_at`) + script de seed pour l’admin.
- Étape 3: adapter `AuthService.login` et `/api/auth/login` pour accepter `{ email, password }` (bcrypt/argon2) tout en conservant l’allowlist.
- Étape 4: mettre à jour la landing front (`home-module.js`) avec champ mot de passe + messages i18n et ajuster l’API client.
- Étape 5: étendre les tests (`tests/backend/features/test_auth_login.py`, QA landing) et synchroniser la doc (`docs/architecture/30-Contracts.md`, `docs/ui/home-landing.md`, `docs/Memoire.md`).
- Étape 6: élargir l’allowlist aux bêta-testeurs via scripts dédiés une fois la mécanique validée.


