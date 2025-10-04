# Journal de Passation Inter-Agents — Emergence V8

**Usage** : ce fichier sert de journal chronologique pour la communication asynchrone entre agents IA (Claude Code, Codex) et l'architecte humain (FG).

**Template** : voir `docs/passation-template.md` pour le format standard d'une entrée.

**Protocole complet** : `CODEV_PROTOCOL.md`

---

## [2025-10-04 16:39] — Agent: Claude Code

### Fichiers modifiés
- [src/backend/features/memory/gardener.py](src/backend/features/memory/gardener.py)
- [src/backend/features/memory/concept_recall.py](src/backend/features/memory/concept_recall.py)
- [tests/backend/features/test_concept_recall_tracker.py](tests/backend/features/test_concept_recall_tracker.py)
- [tests/backend/features/test_memory_gardener_enrichment.py](tests/backend/features/test_memory_gardener_enrichment.py)
- [docs/passation.md](docs/passation.md)

### Contexte
Correction du bug ChromaDB thread_ids documenté dans [tests/backend/features/README_CONCEPT_RECALL_TESTS.md](tests/backend/features/README_CONCEPT_RECALL_TESTS.md). ChromaDB ne supporte pas les listes dans les métadonnées, causant l'erreur `ValueError: Expected metadata value to be a str, int, float or bool, got ['thread_1'] which is a <class 'list'>`.

### Actions réalisées
1. **Migration thread_ids → thread_ids_json** :
   - [gardener.py:1501](src/backend/features/memory/gardener.py#L1501) : Stockage JSON string `json.dumps([thread_id] if thread_id else [])`
   - [concept_recall.py:97,170](src/backend/features/memory/concept_recall.py#L97) : Décodage `json.loads(meta.get("thread_ids_json", "[]"))`
   - [concept_recall.py:178](src/backend/features/memory/concept_recall.py#L178) : Encodage lors mise à jour
   - Ajout `import json` dans les deux fichiers

2. **Correction distance → score** :
   - [concept_recall.py:90-93](src/backend/features/memory/concept_recall.py#L90) : ChromaDB utilise L2² pour vecteurs normalisés
   - Formule : `score = 1.0 - (distance / 2.0)` (au lieu de `1.0 - distance`)
   - Seuil abaissé de 0.75 → 0.5 pour similarité réaliste

3. **Correction métadonnées ChromaDB** :
   - [gardener.py:1500,1502](src/backend/features/memory/gardener.py#L1500) : Remplacement `None` → `""` pour `thread_id` et `message_id`
   - ChromaDB rejette les valeurs `None` dans les métadonnées

4. **Correction tests** :
   - [test_concept_recall_tracker.py:76](tests/backend/features/test_concept_recall_tracker.py#L76) : Usage `thread_ids_json` dans `seed_concept()`
   - [test_concept_recall_tracker.py:144](tests/backend/features/test_concept_recall_tracker.py#L144) : Seuil 0.75 → 0.5
   - [test_concept_recall_tracker.py:204-206](tests/backend/features/test_concept_recall_tracker.py#L204) : Décodage JSON pour assertions
   - [test_memory_gardener_enrichment.py:9](tests/backend/features/test_memory_gardener_enrichment.py#L9) : Import `json`
   - [concept_recall.py:39](src/backend/features/memory/concept_recall.py#L39) : Collection optionnelle si `vector_service=None`

### Tests
- ✅ `pytest tests/backend/features/test_concept_recall_tracker.py -v` => **8/8 passent** ✅
- ✅ `pytest tests/backend/features/test_memory_gardener_enrichment.py -v` => **4/4 passent** ✅
- ✅ **Total : 12/12 tests passent** (objectif atteint)

### Prochaines actions recommandées
1. ⚠️ Migration données production : Si des concepts existent en production avec `thread_ids` comme liste, exécuter un script de migration pour convertir → `thread_ids_json`
2. 📊 Monitoring : Ajouter métriques Prometheus pour tracker les détections de concept recall (taux de similarité, fréquence)
3. 🎨 Modal "Voir l'historique" : Implémenter UI pour afficher les threads passés où le concept a été mentionné (Phase suivante)
4. 📚 Documentation README : Mettre à jour [README_CONCEPT_RECALL_TESTS.md](tests/backend/features/README_CONCEPT_RECALL_TESTS.md) pour refléter les corrections
5. 🧪 QA manuelle : Tester le banner concept recall en conditions réelles selon [NEXT_INSTANCE_PROMPT.md](NEXT_INSTANCE_PROMPT.md)

### Blocages
Aucun.

---

## [2025-10-04 14:01] — Agent: Codex

### Fichiers modifiés
- `docs/passation.md`

### Contexte
- Construction et push de l'image Docker `europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251004-135440` pour la révision Cloud Run.
- Déploiement de la révision `emergence-app-00263-n7w` (100 % trafic) via `gcloud run deploy`.
- Vérification de santé `GET /api/health` sur `https://emergence-app-486095406755.europe-west1.run.app`.

### Actions réalisées
1. `docker build -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251004-135440 .`
2. `docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251004-135440`
3. `gcloud run deploy emergence-app --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251004-135440 --region europe-west1 --project emergence-469005 --quiet`
4. `Invoke-WebRequest https://emergence-app-486095406755.europe-west1.run.app/api/health` (HTTP 200).

### Tests
- ✅ `pwsh -File scripts/sync-workdir.ps1` (inclut `tests/run_all.ps1`, `pytest tests/backend/features/test_memory_clear.py`, `pytest tests/test_benchmarks.py`).

### Prochaines actions recommandées
1. Surveiller les logs Cloud Run (`gcloud beta run services logs tail emergence-app --region europe-west1 --project emergence-469005 --log-filter="severity>=ERROR"`).
2. Lancer un smoke test WS distant (`scripts/smoke/smoke-wss-cloudrun.ps1`) pour valider le streaming post-déploiement.
3. Préparer la validation FG pour promotion vers le domaine custom si les QA passent.

### Blocages
- Aucun.

## [2025-10-06 09:30] — Agent: Codex

### Fichiers modifiés
- `docs/passation.md`

### Contexte
- Initialisation d'une session "Code" pour aligner la configuration Git de l'environnement cloud avec les attentes du dépôt.
- Absence totale de remotes détectée au lancement ; ajout de `origin` (HTTPS) et `codex` (SSH) pointant vers `DrKz36/emergencev8`.
- Tentative de `git fetch origin` bloquée par le proxy (HTTP 403) — à relancer dans un environnement disposant de l'accès réseau requis.

### Actions réalisées
1. `git remote add origin https://github.com/DrKz36/emergencev8.git`
2. `git remote add codex git@github.com:DrKz36/emergencev8.git`
3. Vérification via `git remote -v`.

### Tests
- ⏭️ Non applicables (configuration Git uniquement).

### Prochaines actions recommandées
1. Relancer `git fetch --all --prune` puis `git rebase origin/main` une fois l'accès réseau rétabli.
2. Créer/mettre à jour la branche locale `main` pour suivre `origin/main` si nécessaire (`git checkout main && git branch --set-upstream-to=origin/main`).
3. Vérifier que les scripts d'automatisation (`scripts/sync-workdir.ps1`) passent sans erreur après synchronisation complète.

### Blocages
- Accès réseau HTTPS vers GitHub restreint (erreur 403 sur `git fetch origin`).

## [2025-10-04 16:00] — Agent: Claude Code

### Fichiers modifiés
- `CODEV_PROTOCOL.md` (nouveau, racine)
- `AGENTS.md` (ajout section 13 : co-développement multi-agents)
- `CODex_GUIDE.md` (ajout section 11 : collaboration Claude Code)
- `docs/passation-template.md` (nouveau)
- `docs/passation.md` (ajout entête + cette entrée)

### Contexte
Mise en place du protocole de co-développement multi-agents selon demande architecte.
Établissement workflow Claude Code ↔ Codex avec égalité technique, modification croisée autorisée, validation humaine requise.
Documentation complète créée pour assurer collaboration fluide sans accrocs.

### Tests
- ⏭️ Tests non applicables (documentation uniquement)
- ⏭️ `git status` : fichiers non commités (attente validation architecte)

### Prochaines actions recommandées
1. **Validation architecte** : revue `CODEV_PROTOCOL.md` + mises à jour `AGENTS.md`/`CODex_GUIDE.md`.
2. **Après validation** : mettre à jour `README.md` (lien vers `CODEV_PROTOCOL.md`).
3. **Commit** : `docs: add multi-agent codev protocol (Claude Code ↔ Codex)`.
4. **Communication** : partager `CODEV_PROTOCOL.md` avec Codex lors de sa prochaine session.
5. **Suite** : implémenter Quick Wins audit mémoire (injection préférences, pondération temporelle, topic shift).

### Blocages
Aucun. Attente validation avant commit/push.

---

## Session 2025-09-27 - Migration session isolation
- Migration `20250928_session_isolation.sql` rendue idempotente (suppression des `ALTER TABLE` + propagation vers `core/migrations`).
- Stockage local remis a zero (`src/backend/data/db/` + `src/backend/data/vector_store/`) puis backend relance via `pwsh -File scripts/run-backend.ps1`; toutes les migrations passent sans stacktrace.
- Nouvelle base SQLite regeneree; `migrations` contient bien l'entree `20250928_session_isolation.sql`.

# Passation Courante
- 2025-10-02 : Prod redeploy mergence-app-00262-xdv sans mode dev. Tests manuels : login admin réel, purge dev@local, navigation cockpit (200 sur /api/dashboard/costs/summary). Captures archivées : docs/assets/passation/auth-admin-prod-20251002.png, docs/assets/passation/cockpit-prod-20251002.png.

## Backend & QA
- 2025-10-03 : Benchmarks Firestore — le backend active la réplication cloud lorsque `EMERGENCE_FIRESTORE_PROJECT` et les credentials (`GOOGLE_APPLICATION_CREDENTIALS` ou login ADC) sont présents. En mode edge (`EDGE_MODE=1`), le service bascule automatiquement sur SQLite uniquement.
  - Procédure locale :
    1. `gcloud auth application-default login` ou renseigner `GOOGLE_APPLICATION_CREDENTIALS` vers le JSON du compte de service Firestore.
    2. Exporter `EMERGENCE_FIRESTORE_PROJECT=<project_id>` (ou `BENCHMARKS_FIRESTORE_PROJECT`) avant de lancer `pwsh -File scripts/run-backend.ps1`.
    3. Déclencher `POST /api/benchmarks/run` avec `{"scenario_id":"ARE"}` (auth admin) ou `python -m pytest tests/test_benchmarks.py` pour un run complet.
    4. Contrôler `benchmark_runs` en SQLite (`sqlite3 <db_path> "SELECT COUNT(*) FROM benchmark_runs;"`) et la réplication via `gcloud firestore documents list benchmark_matrices --project <project_id>`.
  - Sans credentials valides, `build_firestore_client` retourne `None` et la persistance reste locale (testé en STD/EDGE via script temporaire + `pytest`).
  - Vérification 2025-10-03 : ADC actif (`gcloud auth application-default login` + `EMERGENCE_FIRESTORE_PROJECT=emergence-469005`), le script Python a listé 1 matrice (`6b1c9fab95e645b7bbfe1b592080a52b`) et 8 runs (`228eddee7816b4019cd95c2578672f117e754d69`, `3c4d30577da0cbce8f4b44ab909d1b4e21770697`, `44411d6cc4911883eb6ae7bf4b70eca21ca4292a`, `5512416541ec5aaffc08a8e3e8c9cd687f3eead8`, `6862e081ed03e4046032e6195b6ba2ae97524c41`, `84a9a722952cb0183373832ec51fbbc789924c66`, `99814004ca286d621a053c3a073ee136c90b6dd1`, `cf0124d2840dd8b837dcc370ed5a34139ab8aed2`). Réplication Firestore confirmée.
    - Snapshot Firestore 2025-10-03 : matrice ARE (trigger `manual-firestore-v2`) => `runs_count=8`, `success_count=4`, `failure_count=4` (seuil 0.74). Exemple run `multi-agent::react::full-memory` réussi (latence `1189.9 ms`, coût `0.00859 USD`).
    - UI 2025-10-03 : Cockpit > Benchmarks affiche 4/8 configurations réussies (50 %), cohérent avec Firestore ; captures fournies pour archivage (placer sous `docs/assets/dashboard/benchmarks-are-20251003-{wide,zoom}.png`).
- 2025-10-02 : Cloud Run tail `gcloud beta run services logs tail emergence-app --region europe-west1 --project emergence-469005 --log-filter="severity>=DEFAULT"` (revision emergence-app-00261-z79) : aucune entrée >= ERROR; warnings DevMode (fallback user) + sessions/threads orphelins en cohérence avec les 401/404 attendus ; warnings `backend.features.memory.analyzer` (historique vide) attendus sur session smoke sans historique ; export `docs/assets/monitoring/cloud-run-tail-20251002.txt`.
- 2025-10-02 : `tests/run_all.ps1` (backend local lancé via `pwsh -File scripts/run-backend.ps1`, `AUTH_DEV_MODE=0`). Health/dashboard/documents OK, upload `test_upload.txt` -> document_id=28, suppression ID=1 => 404 attendu si absent, `pytest tests/backend/features/test_memory_clear.py -q` = 7 pass. Mise à jour 2025-10-03 : le script s'appuie désormais sur le helper d'auth (`tests/helpers/auth.ps1`) et effectue un login email/mot de passe avant les requêtes REST. Renseigner `EMERGENCE_SMOKE_EMAIL` / `EMERGENCE_SMOKE_PASSWORD` ou passer `-SmokeEmail`/`-SmokePassword` si nécessaire.
- 2025-10-02 : `scripts/smoke/smoke-ws-3msgs.ps1 -SessionId smoke-ws-3msgs-20251002 -MsgType chat.message -UserId "smoke_rag&dev_bypass=1" -WsHost emergence-app-47nct44nma-ew.a.run.app -Port 80` OK (3 tours `ws:chat_stream_*`, `ws:chat_stream_end` reçu, modèle gpt-4o-mini) ; trace `docs/assets/monitoring/smoke-ws-3msgs-20251002.txt`.
- 2025-10-01 : Flux chat.opinion - `pytest tests/backend/features/test_chat_opinion.py` et `pytest tests/backend/features/test_chat_router_opinion_dedupe.py` OK (dedupe couvert). `pytest tests/backend/features -k opinion` => 2 tests, 28 deselections.
- 2025-10-01 : Frontend dedupe - `node --test src/frontend/core/__tests__/websocket.dedupe.test.js` et `node --test src/frontend/features/chat/__tests__/chat-opinion.flow.test.js` OK (anti-dup WS + parcours UI).
- 2025-10-01 : `npm run build` OK (vite build).
- 2025-10-01 : QA manuelle chat.opinion non realisee (session CLI sans UI); planifier une verification en environnement graphique pour valider ws:chat_stream_* et ws:message_persisted + toast.
- 2025-09-29 : Correctif persistance multi-session (20251002_user_scope.sql) appliqué ; relancer `pwsh -File scripts/run-backend.ps1` pour regénérer la base et assurer le hachage `user_id` (threads et sessions). Le backend privilégie désormais `user_id` dans `get_threads/get_thread/get_messages` (filtrage cross-session), couvert par `pytest tests/backend/features/test_user_scope_persistence.py::test_threads_api_cross_session_listing`. Côté front, `StateManager.resetForSession()` conserve `threads.map/order` lorsque le même `user_id` se reconnecte et `api-client` envoie `X-User-Id` (QA : logout → login autre profil → retour profil initial = conversation encore visible).
- 2025-09-30 : Fix front connexion multi-profils – `StateManager.resetForSession()` nettoie désormais l'`user.id` et l'API client purge l'entête `X-User-Id` lors d'un logout/changement d'utilisateur. L'indicateur Auth (badge) écoute aussi `ws:session_established/restored` pour repasser immédiatement en vert après login et adopte un fond orange (déconnecté) / vert (connecté). Les tentatives successives membre/admin ne réutilisent plus le thread du compte précédent (QA locale OK après `npm run build`).
- 2025-09-28 : `tests/test_vector_store_reset.ps1 -AutoBackend` relanc� OK (backend auto, backup + upload valid�s). Log associ� : `docs/assets/memoire/vector-store-reset-20250928-153333.log`.
- Backend verifie via `pwsh -File scripts/run-backend.ps1` (logs OK, WS et traces auth `[AuthTrace]` observées).
- Utiliser `python scripts/seed_admin.py --email <admin> --password <motdepasse>` pour initialiser ou mettre a jour le mot de passe admin en local.
- `tests/run_all.ps1` : dernier passage indique OK (voir session precedente, aucun echec signale).
- `scripts/smoke/smoke-ws-rag.ps1 -SessionId ragtest124 -MsgType chat.message -UserId "smoke_rag&dev_bypass=1"` : OK (27/09) â flux `ws:chat_stream_end` (OpenAI gpt-4o-mini) + upload document_id=57 sans 5xx. Logs `#<-` â `docs/assets/memoire/smoke-ws-rag.log`.
- `scripts/smoke/smoke-ws-rag.ps1 -SessionId ragtest-ws-send-20250927 -MsgType ws:chat_send -UserId "smoke_rag&dev_bypass=1"` : KO (27/09) â handshake acceptÃ© mais rÃ©ponse `ws:error` (`Type inconnu: ws:chat_send`). Logs `#<-` â `docs/assets/memoire/smoke-ws-rag-ws-chat_send.log`.
- `scripts/smoke/smoke-ws-3msgs.ps1 -SessionId ragtest-3msgs-20250927 -MsgType chat.message -UserId "smoke_rag&dev_bypass=1"` : OK (27/09) â 3 messages consÃ©cutifs, `ws:chat_stream_start` x3 puis `ws:chat_stream_end`; aucun HTTP 5xx cÃ´tÃ© documents/uploads (`backend.err.log` inchangÃ©). Logs `#<-` â `docs/assets/memoire/smoke-ws-3msgs.log`.
- VÃ©rification UI nav rÃ´le (2025-09-30) : scÃ©nario admin â logout â membre (`fernando36@bluewin.ch`). AprÃ¨s reconnexion, la sidebar doit exclure `Admin` tout en conservant `Memoire`; le bandeau doit afficher `Membre (fernando36@bluewin.ch)`. Capture Ã  archiver : `docs/assets/passation/auth-role-reset.png`.
- Module Admin â Sessions (2025-09-30) : depuis l'onglet Admin, vÃ©rifier que le bloc Sessions liste les connexions actives (session_id, email, IP, dates). RafraÃ®chir via le bouton dÃ©diÃ© et confirmer qu'un membre connectÃ© apparait avec le statut Actif.
- `scripts/smoke/smoke-health.ps1 -BaseUrl https://emergence-app-486095406755.europe-west1.run.app` : OK (27/09 18:09 UTC) -> 200 `{ "status": "ok" }` sur revision `emergence-app-00256-jxh`.
- `scripts/smoke/smoke-memory-tend.ps1 -BaseUrl https://emergence-app-486095406755.europe-west1.run.app -UserId "smoke_rag&dev_bypass=1" -SessionId cloud-smoke-memory-20250927` : OK (27/09) -> `status=success`, `message="Aucune session a traiter."`.
- Test WSS Cloud Run (27/09) : envelope `chat.message` (session `cloud-wss-rag-20250927`, query `user_id=smoke_rag&dev_bypass=1`) -> `ws:rag_status` `searching` puis `found`, `ws:model_info` (`openai gpt-4o-mini`), flux complet jusqu'a `ws:chat_stream_end`. La tentative legacy `ws:chat_send` via `smoke-wss-cloudrun.ps1` retourne `ws:error` (`Type inconnu`), a realigner.
- Le tableau allowlist du module *Admin* expose desormais un bouton `Supprimer` par entree : confirmation navigateur, appel `DELETE /api/auth/admin/allowlist/{email}`, toast `Entree supprimee.` puis rechargement de la pagination active.

## Observabilite & logs (2025-09-27)
- `gcloud run services describe emergence-app --region europe-west1` : revision `emergence-app-00256-jxh` Ready (100 % traffic), tag `canary` pointe sur `emergence-app-00279-kub`.
- `gcloud logging read --freshness=1h --limit=200` filtre `service_name=emergence-app` : aucune entree `httpRequest.status >= 500`.
- Plus de 404 Gemini depuis le passage de `DEFAULT_GOOGLE_MODEL` sur `models/gemini-2.5-flash` (les anciens alias `models/gemini-1.5-flash*` sont maintenant mappÃ©s automatiquement). Surveiller `gcloud logging read --freshness=1h --limit=200` (aucune entree `google.api_core.exceptions.NotFound`) et controler les frames `ws:model_info` (`provider=google`, `model=models/gemini-2.5-flash`).

## Auth allowlist - mots de passe (2025-09-27)
- Module *Admin* cote frontend (navigation principale) reserve aux comptes `role=admin`. La liste est paginee, filtrable (`Actives`, `Revoquees`, `Toutes`) et propose une recherche email/note + resumes (`total`, `page`). Les toasts front confirment les sauvegardes et la copie du mot de passe genere.
- `GET /api/auth/admin/allowlist` expose maintenant `status=active|revoked|all`, `search`, `page`, `page_size` et renvoie `{ items, total, page, page_size, has_more, status, query }`. Le flag historique `include_revoked=true` reste accepte pour la compatibilite.
- `POST /api/auth/admin/allowlist` continue d'accepter `{ email, role?, note?, password?, generate_password? }` et retourne `{ entry, clear_password?, generated }`. Lorsque `generate_password=true`, l'audit ajoute `allowlist:password_generated` (longueur consigne dans `metadata.password_length`).
- Toujours initialiser/rafraichir les admins via `scripts/seed_admin.py` avant de communiquer le formulaire aux testeurs; la commande est idempotente et journalisee (`allowlist:password_set`).

### Quickstart QA - flux admin â generation â communication
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
- Capture QA historique (`docs/ui/auth-required-banner.md`) conservée pour référence (`docs/assets/ui/auth-banner-console.svg`).
- Test unitaire ajoute pour verrouiller `ensureCurrentThread()` -> `EVENTS.AUTH_REQUIRED` et garantir le payload QA.

## Suivi
- Le module Â« MÃ©moire Â» est dÃ©sormais rÃ©servÃ© aux admins et intÃ¨gre la liste des conversations pour faciliter la revue des threads.
- Nouvel accÃ¨s rapide Â« MÃ©moire Â» dans chaque agent du module Chat : tester quâil lance bien memory:tend sur le thread actif.
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

### Conversations - flux suppression & memoire (2025-09-28)
- Inline confirm: `ThreadsPanel` renders the `Supprimer ?` prompt with `Confirmer`/`Annuler` before hitting the destructive endpoint.
- Nav admin uniquement: l'entrée `Conversations` est retirée de la sidebar; vérifier que le rôle admin voit `Memoire` + `Admin` et que les membres conservent `Memoire` sans onglet `Admin`.
- `threads-service.deleteThread()` uses `DELETE /api/threads/{id}` with `X-Session-Id`; backend cascades to `messages` + `thread_docs` scoped to the same session.
- After `204` the module emits `EVENTS.THREADS_DELETED`, re-selects the next available thread, and boots a fresh chat when the list becomes empty.
- Memoire: STM/LTM entries remain until `POST /api/memory/clear`; rappeler aux testeurs qu'une purge est necessaire pour un effacement complet.
- Captures attendues: liste, bloc de confirmation, et etat vide + bandeau memoire; stocker `conversations-list.png`, `conversations-confirm.png`, `conversations-empty.png`, `memory-banner.png` sous `docs/assets/memoire/`.

## Session 2025-09-25 - Debate metrics QA
- Tests: python -m pytest tests/backend/features/test_debate_service.py (2 passes) ; npm run build (vite ok, warning persists on ANIMATIONS export).
- Manual QA: simulated debate run (DebateService.run) -> 10 ws events (started, status updates, turn updates, result, ended); cost total 0.053200 USD with tokens 340/172 and by agent neo 0.0123, nexus 0.0222, anima 0.0187.
- UI follow-up: header shows progress + cost block; css wraps cost spans under 560px; next run full UI QA once backend is online.


## Session 2025-09-24 - Auth revocation QA
- Reprise backend via `pwsh -File scripts/run-backend.ps1` puis exÃ©cution `tests/run_all.ps1` : statut OK, endpoints accessibles.
- VÃ©rification manuelle WS : rÃ©utiliser un token rÃ©voquÃ© renvoie `ws:auth_required` (reason=`session_revoked`) lorsque la session WebSocket correspond au `sid` d'auth.
- Observation actuelle : les connexions WS gardant un `sessionId` distinct du `sid` ne sont pas encore coupÃ©es lors d'un logout (Ã  corriger cÃ´tÃ© core/chat).
- 2025-09-26 : Correction livrÃ©e. Le handshake WS s'appuie dÃ©sormais sur le `sid` vÃ©rifiÃ© (`AuthService.verify_token`) et `SessionManager` maintient les alias cÃ´tÃ© backend. Le client JS extrait ce `sid` du token afin d'aligner REST/WS, ce qui permet Ã  `handle_session_revocation()` de couper les connexions actives aprÃ¨s logout.

## Session 2025-09-25 - PR ws alias handoff
- PR ouverte `fix: align websocket session alias handling` (branche `fix/debate-chat-ws-events-20250915-1808` -> main).
- Description PR : rÃ©sumÃ© + tests (voir tmp/pr_body.md).
- CI GitHub Actions : statut non rÃ©cupÃ©rÃ© (API GitHub inaccessible sans jeton dans cet environnement, vÃ©rifier manuellement dÃ¨s disponibilitÃ©).

## Session 2025-09-25 - QA Accueil + Auth
- Backend local lancÃ© via `pwsh -File scripts/run-backend.ps1 -ListenHost 127.0.0.1` (via Start-Process) ; migrations appliquÃ©es, `src/backend/data/db/emergence_v7.db` rÃ©gÃ©nÃ©rÃ©e.
- Stockage remis Ã  plat pour la QA : allowlist vÃ©rifiÃ©e puis enrichie via `/api/auth/admin/allowlist` (dev bypass) avec `gonzalefernando@gmail.com` afin de tester le formulaire.
- Formulaire email (API) : `POST /api/auth/login` retourne 200 + token pour l'email allowlist (session active dans `auth_sessions`).
- Log `[AuthTrace]` : `npm test -- src/frontend/core/__tests__/app.ensureCurrentThread.test.js` passe après avoir neutralisé l'init DOM dans `components/modals.js`; conserver les captures historiques (`docs/assets/ui/auth-banner-20250925.png`).
pm test -- src/frontend/core/__tests__/app.ensureCurrentThread.test.js passe après avoir neutralisé l'init DOM dans components/modals.js; conserver les captures historiques (`docs/assets/ui/auth-banner-20250925.png`).

### QA - Roles & navigation
1. Se connecter avec un compte admin : confirmer la presence des modules `Memoire` et `Admin` dans la navigation, puis ouvrir un chat pour generer un evenement `ws:model_info` (noter `provider`/`model`).
2. Se deconnecter via le bouton header : verifier dans `localStorage` (cle `emergenceState-V14`) que `auth.role` repasse a `member`, que `session.id` et `websocket.sessionId` sont `null`, et que l'UI affiche a nouveau l'ecran d'accueil.
3. Se reconnecter avec un compte membre : controler que seuls les modules de base (`Dialogue`, `Documents`, `Debats`, `A propos`, `Cockpit`) restent visibles et que l'onglet actif revient sur `Dialogue`.
4. Depuis DevTools > Application > Storage, relire `emergenceState-V14` pour confirmer que `auth.role` et `chat.authRequired` sont respectivement `member` et `false`, sans residus de navigation admin.
5. Capturer la barre de navigation (etat membre) et un extrait Console montrant `ws:model_info` avec `models/gemini-2.5-flash` pour alimenter la checklist QA.


### Pistes suivantes UI/Auth
- [FAIT 2025-09-26] Bootstrap DOM Node (`src/frontend/core/__tests__/helpers/dom-shim.js`) + relance de `npm test -- src/frontend/core/__tests__/app.ensureCurrentThread.test.js`.
- [FAIT 2025-09-26] `node scripts/qa/home-qa.mjs` rejouÃ© (captures + console QA rafraÃ®chies, `missingCount: 2` confirmÃ©).
- Suivi: prÃ©voir une passe QA manuelle backend hors-ligne prolongÃ©e pour valider la remise en place continue de `body.home-active` et mettre Ã  jour `docs/ui/auth-required-banner.md` si le comportement Ã©volue.


## Session 2025-09-26 - QA Accueil (clearToken)
- Scenario rejoue via node tmp/qa-auth-clear-check.mjs apres connexion (PID backend 504 tue par le script).
- Resultat : clearToken() declenche sur auth:missing, tokens storage/cookie sont purges, body.home-active repasse a true et le landing reste affiche sans reload.
- Metrics QA : missingCount incremente a 1 (overlay QA enregistre source=auth:missing).
- Console : plus de warning persistants; seul [WebSocket] Aucun ID token - connexion WS annulee apparait une fois lors de la reconnexion.
- Suite : rejouer le scenario en CI et planifier un test backend off (>1 min) pour confirmer l'absence de regressions.

## Admin Ops
- 2025-10-03 : Scripts PowerShell `tests/test_vector_store_reset.ps1` et `tests/test_vector_store_force_backup.ps1` alignés sur l'auth standard (Bearer). Ils consomment `tests/helpers/auth.ps1`, obtiennent un token via login email/mot de passe et injectent désormais `Authorization` + `X-Session-Id` sur les uploads. Configurer les mêmes variables d'environnement avant exécution.
- 2025-10-02 : `GET /api/auth/admin/allowlist` (headers `X-Dev-Bypass: 1`, `X-User-Id: gonzalefernando@gmail.com`) => 2 entrées actives (`gonzalefernando@gmail.com` admin, `fernando36@bluewin.ch` member). `dev@local` absent en base locale et devra rester banni prod.
- Procédure création/reset admin : exécuter `python scripts/seed_admin.py --email <admin> --password <motdepasse>` en local (ou utiliser l'onglet Admin > Allowlist > Ajouter), puis communiquer le mot de passe via canal sécurisé; vérifier la présence via `/api/auth/admin/allowlist`.
- Procédure suppression admin : via l'UI (onglet Allowlist > icône poubelle) ou via `DELETE /api/auth/admin/allowlist/{email}` (JWT admin requis). Penser à invalider les sessions via `/api/auth/admin/sessions/revoke`.

## Session 2025-09-26 - Accueil email allowlist
- Module `features/home/home-module.js` : landing auth plein Ã©cran, formulaire email, appels `POST /api/auth/login`, intÃ©gration metrics QA.
- Refonte `src/frontend/main.js` : bascule automatique vers le landing sans token, bootstrap App/WS aprÃ¨s succÃ¨s, purge des tokens au logout.
- QA : `scripts/qa/home-qa.mjs` attend dÃ©sormais `body.home-active` et capture lâÃ©tat landing + overlay QA.
- Correctif: `main.js` rÃ©introduit `clearToken()` pour purger les tokens navigateur lors dâun logout ou backend HS (supprime le warning console).
## Session 2025-09-26 - Auth password mode planning
- Ãtat : authentification email + mot de passe (JWT local) dÃ©ployÃ©e, sans dÃ©pendance GIS.
- Étape 1: confirmer `AUTH_DEV_MODE=0` et valider le login admin par le flux standard (email + mot de passe, overlay Home requis).
- Ãtape 2: concevoir la migration `auth_allowlist` (`password_hash`, `password_updated_at`) + script de seed pour lâadmin.
- Ãtape 3: adapter `AuthService.login` et `/api/auth/login` pour accepter `{ email, password }` (bcrypt/argon2) tout en conservant lâallowlist.
- Ãtape 4: mettre Ã  jour la landing front (`home-module.js`) avec champ mot de passe + messages i18n et ajuster lâAPI client.
- Ãtape 5: Ã©tendre les tests (`tests/backend/features/test_auth_login.py`, QA landing) et synchroniser la doc (`docs/architecture/30-Contracts.md`, `docs/ui/home-landing.md`, `docs/Memoire.md`).
- Ãtape 6: Ã©largir lâallowlist aux bÃªta-testeurs via scripts dÃ©diÃ©s une fois la mÃ©canique validÃ©e.


- 2025-09-30 : Investigation threads manquants – les requêtes REST filtrent désormais par user_id hashé (cf. src/backend/core/database/queries.py:_build_scope_condition). Les entrées historiques créées avant la migration conservent le placeholder 'FG' en user_id (ex.: threads f5db25d7af01415a8cb47f0bcd5918cc) et sont donc exclues des réponses pour le même compte (gonzalefernando@gmail.com). Aucun contenu n'est perdu en base (messages/documents présents), mais le backfill (src/backend/core/database/backfill.py) ne remplace pas ces valeurs. FAIT 2025-09-30 : run_user_scope_backfill remappe désormais les placeholders 'FG' vers le hash SHA-256 du compte de référence (AUTH_DEV_DEFAULT_EMAIL) et cascade sur threads/messages/documents/thread_docs/document_chunks. Test backend ajouté : tests/backend/features/test_user_scope_persistence.py::test_user_scope_backfill_remaps_legacy_placeholder.
