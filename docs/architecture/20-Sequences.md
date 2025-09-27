# ÉMERGENCE — Séquences (User Journeys)

## 0) Auth email (Allowlist -> Token -> Landing)
1. Front : `HomeModule` affiche le hero (fond noir + logo) et le formulaire email; validation locale du format.
2. **DEV** (`AUTH_DEV_MODE=1`) : `main.js` tente `POST /api/auth/dev/login` pour récupérer un JWT local (`email` = `AUTH_DEV_DEFAULT_EMAIL` ou premier admin allowlist) et booter l'app sans overlay.
3. Front : (flux standard) `POST /api/auth/login` avec `{ email }` et métadonnées (user-agent, locale); état `pending`.
4. Back : `AuthRateLimiter` vérifie le quota IP+email (5 essais / 5 min); `AuthService` contrôle l'allowlist (`LOCAL_ALLOWED_EMAILS`).
5. Back : génération JWT HS256 (`iss=emergence.local`, `aud=emergence-app`, `sub=sha256(email)`), enregistrement dans `auth_sessions` (`issued_at`, `expires_at=+7j`, `ip`, `role`, `otp_fields`).
6. Back : réponse `200` `{ token, expires_at, role, session_id }`; sinon `429` (rate) ou `401` (email refusé).
7. Front : stockage token (`localStorage` + cookie), mise a jour `StateManager.auth`, `StateManager.resetForSession(session_id)` remet l'etat a zero, `api-client` memorise le `session_id` pour l'entete `X-Session-Id`, puis `App` lance `WebSocketClient.connect()`.
8. Back : handshake WS accepte le token local (signature, expiration, revocation), verifie le `session_id` (path WS + entete) et attache `session.sub`.
9. Front : badge auth actif; `POST /api/auth/logout` purge le token, supprime `X-Session-Id` cote storage/localStorage et relance `HomeModule`.

## 1) Chat temps réel (Bootstrap -> WS -> Agents -> Persist)
1. Front : `HomeModule` + `storeAuthToken()` garantissent un JWT (storage/cookie) et `StateManager.getSessionId()` expose le `session_id` pour REST/WS. En DEV (`AUTH_DEV_MODE=1`), l'app peut appeler `/api/auth/dev/login` pour obtenir un token de test.
2. Front : `ensureCurrentThread()` -> `GET /api/threads?type=chat&limit=1` ; cree (`POST /api/threads`) si vide, hydrate `state.threads.map` via `GET /api/threads/{id}/messages?limit=50` ; `api-client` ajoute `X-Session-Id` sur chaque appel.
3. Front : ouverture WS `wss:///ws/{session_id}` (sub-proto `jwt` + token) et entete `X-Session-Id` ; ecoute `ws:session_established`.
4. Front : envoi {type:"chat.message", payload:{text, agent_id, use_rag, thread_id}} ; watchdog REST (`POST /api/threads/{id}/messages` + `X-Session-Id`) si `ws:chat_stream_start` ne survient pas en 1,5 s.
5. Back : `ChatService` normalise l'historique (roles en lower-case, fallback sur content/message), persiste le message, filtre threads/messages/documents par `session_id` et enrichit le prompt (memoire STM/LTM + RAG si active) avant d'appeler les modeles (fallback Google -> Anthropic -> OpenAI).
6. Back : stream `ws:chat_stream_start/chunk/end`, `ws:model_info`, `ws:model_fallback`, `ws:memory_banner`, `ws:rag_status`.
7. Front : integre chunks, affiche sources RAG, met a jour metriques; REST `GET /api/threads/{id}/messages` (avec `X-Session-Id`) pour pagination.

## 2) Mémoire (Analyse → Consolidation → Clear)
1. Front : utilisateur clique `Analyser` -> `POST /api/memory/tend-garden` (payload optionnel `thread_id`); `api-client` ajoute `X-Session-Id` pour cibler la session active.
2. Back : `MemoryGardener` agrege l'historique de la session (global ou thread), `MemoryAnalyzer` produit resume/faits/concepts via LLM, persiste en base avec `session_id` et vectorise (Chroma).
3. Back : notifie via `ws:analysis_status` + `ws:memory_banner` (STM/LTM injectees) en rappelant le `session_id`.
4. Front : badges memoire mis a jour; `GET /api/memory/tend-garden` (avec `X-Session-Id`) pour verifier l'etat courant.
5. Clear : `POST /api/memory/clear` (avec `X-Session-Id`) -> purge STM + items LTM filtres par session/agent, notifie WS.

## 3) Documents (Upload → Indexation → Utilisation RAG)
1. Front : drop/upload -> `POST /api/documents/upload` (FormData + `X-Session-Id`).
2. Back : `DocumentService` valide extension (`.pdf|.txt|.docx`), parse, chunk, vectorise, persiste metadonnees avec `session_id`.
3. Back : repond `201` + declenche rafraichissement (`GET /api/documents` filtre par `session_id`).
4. Front : `DocumentsModule` met a jour liste + quotas; `ChatModule` peut lier `document_ids` au thread (POST docs avec `X-Session-Id`).
5. RAG : lors du chat, `ChatService` interroge `VectorService` pour recuperer passages pertinents (filtre thread/doc + `session_id`), inclut sources dans `ws:chat_stream_end`.

- **Smoke QA** : `pwsh -File scripts/smoke/smoke-ws-rag.ps1 -SessionId <id> -MsgType chat.message -UserId "tester&dev_bypass=1"` valide le flux WS+RAG. Logs `#<-` archivés dans `docs/assets/memoire/smoke-ws-rag.log` (session `ragtest124`, 2025-09-27).

## 4) Débat multi-agents
1. Front : configure débat → envoie `{type:"debate:create"}` (topic, agents, rounds, `use_rag`).
2. Back : `DebateService` crée session interne, boucle sur les agents (isolation contextuelle), invoque `ChatService` pour chaque tour.
3. Back : publie `ws:debate_status_update` pour chaque round + `ws:debate_result` (synthèse, coûts).
4. Front : affiche tours, synthèse, permet export.

## 5) Dashboard & coûts
1. Front : `DashboardModule` → `GET /api/dashboard/costs/summary`.
2. Back : `DashboardService` agrège coûts, sessions, documents.
3. Front : rend cartes (jour/semaine/mois/total) + monitoring ; rafraîchissement manuel possible.

## 6) Admin auth (Allowlist & Sessions)
1. Admin : login via email (présent dans `LOCAL_AUTH_ADMIN_EMAILS`) -> payload `role="admin"`.
2. Front : `AuthAdminModule` consomme `GET /api/auth/admin/allowlist` et `GET /api/auth/admin/sessions?status=active`.
3. Back : `AuthService` vérifie le rôle admin, renvoie allowlist + sessions (expiration, ip, revoked_at).
4. Admin : ajoute une entrée `POST /api/auth/admin/allowlist` (`{ email, note? }`) ou supprime `DELETE /api/auth/admin/allowlist/{email}`; peut révoquer `POST /api/auth/admin/sessions/revoke` (`{ session_id }`).
5. Back : journalise l'action (`auth_audit_log`), met à jour tables, renvoie l'état; front rafraîchit et notifie.
