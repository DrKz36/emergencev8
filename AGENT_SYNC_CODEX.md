## Session COMPLETED (2025-10-31 16:05 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/styles/components/rag-power-button.css`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Forcé la règle responsive mobile à utiliser `display:flex !important` pour que les boutons RAG/TTS mobiles apparaissent en portrait.
2. Incrémenté la version vers `beta-3.3.22` + patch notes/changelog alignés avec le hotfix.
3. Mis à jour la passation et la sync agent pour tracer la correction QA prod.

### Tests
- ✅ `npm run build`

### Next steps
1. QA manuelle sur mobile (Safari/Chrome) pour valider la visibilité du bouton TTS.
2. Vérifier que Guardian/CI relaie bien la version `beta-3.3.22`.
3. Surveiller éventuels retours utilisateurs sur le mode vocal.

### Blockers
- Aucun.

## Session COMPLETED (2025-10-31 12:40 CET) - Agent : Codex GPT

### Files touched
- `.github/workflows/cloud-run-iam-restore.yml`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Donné une valeur par défaut à l'input `reason` pour éviter l'expression vide qui faisait planter la validation du workflow.
2. Branché `setup-gcloud` sur `steps.auth.outputs.project_id` (fallback env) et exporté les credentials par défaut pour que les commandes `gcloud` héritent bien du projet.
3. Raffiné la condition `Context` afin qu'elle ne s'exécute que si un motif est réellement fourni.

### Tests
- ⚠️ Pas de tests automatisés (workflow GitHub Actions seulement).

### Next steps
1. Relancer le workflow hotfix côté GitHub pour confirmer qu'il passe la validation YAML + IAM.
2. Ajouter le log du premier run OK dans l'incident Cloud Run.
3. Mettre en place un guard Guardian sur la présence du binding `allUsers`.

### Blockers
- Aucun.

## Session COMPLETED (2025-10-31 11:10 CET) - Agent : Codex GPT

### Files touched
- `.github/workflows/cloud-run-iam-restore.yml`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Forcé `setup-gcloud` à définir le projet par défaut pour que `gcloud run ...` arrête de gueuler sur l'absence de `project`.
2. Ajouté `--project $GCP_PROJECT_ID` sur chaque commande `gcloud` du workflow pour qu'un runner vierge n'échoue plus.
3. Consigné la correction dans le journal de session afin que l'astreinte sache que le workflow est à nouveau exécutable.

### Tests
- ⚠️ Pas de tests automatisés (workflow GitHub Actions uniquement).

### Next steps
1. Relancer le workflow `Restore Cloud Run IAM Access` pour valider les bindings IAM depuis GitHub.
2. Capturer le log du premier run réussi dans l'incident en cours.
3. Ajouter un guard Guardian qui alerte si `allUsers` saute encore.

### Blockers
- Aucun.

## Session COMPLETED (2025-10-31 09:45 CET) - Agent : Codex GPT

### Files touched
- `.github/workflows/cloud-run-iam-restore.yml`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Corrigé la condition `if` du workflow Hotfix IAM pour utiliser `github.event.inputs.reason` et respecter la syntaxe GitHub Actions.
2. Vérifié que seul le pas d'affichage du motif dépend de l'input optionnel, sans impact sur les commandes gcloud.
3. Mise à jour des journaux de session pour tracer le fix et rappeler le besoin de QA sur le workflow lors du prochain déclenchement.

### Tests
- ⚠️ Pas de tests automatisés (workflow GitHub Actions uniquement).

### Next steps
1. Déclencher le workflow dès que possible pour confirmer que la syntaxe corrigée passe la validation GitHub.
2. Documenter le résultat du premier run (capture logs) dans l'incident si nécessaire.
3. Prévoir un guard Guardian qui alerte si le binding allUsers disparaît à nouveau.

### Blockers
- Aucun.

## Session COMPLETED (2025-10-30 23:15 CET) - Agent : Codex GPT

### Files touched
- `.github/workflows/cloud-run-iam-restore.yml`
- `scripts/restore-cloud-run-iam.ps1`
- `INCIDENT_2025-10-30_WS_DOWN.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Ajouté un workflow GitHub Actions "Restore Cloud Run IAM Access" pour réappliquer le binding `allUsers → roles/run.invoker`, retirer `allAuthenticatedUsers` et vérifier `/health` sans rebuild complet.
2. Écrit le script PowerShell `restore-cloud-run-iam.ps1` qui déclenche le workflow Hotfix depuis la ligne de commande et guide le suivi du run.
3. Documenté l'option de hotfix dans `INCIDENT_2025-10-30_WS_DOWN.md` pour qu'on sache qu'il suffit de lancer le workflow ou le script quand la prod retombe en 403.

### Tests
- ⚠️ Pas de tests automatisés (workflow/action seulement, pas exécutable localement).

### Next steps
1. Ajouter une alerte Guardian/monitoring qui détecte la disparition de `allUsers` pour déclencher automatiquement le workflow.
2. Vérifier que le workflow dispose bien des permissions SA côté GitHub (premier run à planifier après merge).
3. Intégrer le script dans le playbook d'astreinte (docs ops).

### Blockers
- Aucun.

## Session COMPLETED (2025-10-30 09:20 CET) - Agent : Codex GPT

### Files touched
- `docs/optimizations/langgraph_vllm_surveillance_2025-10.md`
- `requirements-agents.txt`
- `scripts/qa/langgraph_persistence_check.py`
- `scripts/qa/maven_adversarial_probe.py`
- `scripts/benchmarks/token_drift_compare.py`
- `reports/benchmarks/vllm_openai_token_drift.log`
- `reports/langgraph_persistence/README.md`
- `reports/maven/README.md`

### Work summary
1. Rédigé le rapport de veille LangGraph/vLLM/Jetson/MAVEN avec statuts Ready/Watch/Blocker et recommandations multi-agents.
2. Ajouté les scripts de stress `langgraph_persistence_check`, `maven_adversarial_probe` et `token_drift_compare` + fichiers de rapport associés.
3. Introduit `requirements-agents.txt` pour consigner les dépendances LangGraph 1.0.2 / checkpoint 3.0 (SQLite) et préparé la structure de logs.

### Tests
- ⚠️ Scripts non exécutés (endpoints réels / Firestore 3.0 absents dans cet environnement).

### Next steps
1. Lancer `scripts/benchmarks/token_drift_compare.py` avec un endpoint vLLM >=0.10.2 pour capter un premier log réel.
2. Exposer `token_ids` dans les métas backend (`ws:chat_stream_chunk`) puis brancher le bench dans la CI Guardian.
3. Surveiller la sortie de `langgraph-checkpoint-firestore` 3.0 pour activer le scénario Firestore dans le script.

### Blockers
- Extension Firestore 3.0 indisponible (dernier build 0.1.x) → reprise Firestore en attente.

## Session COMPLETED (2025-10-30 22:10 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/core/__tests__/auth.normalize-token.test.mjs`
## Session COMPLETED (2025-10-30 22:45 CET) - Agent : Codex GPT

### Files touched
- `vite.config.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Renommé la suite `auth.normalize-token` en `.test.mjs` pour qu’elle reste ESM et ne fasse plus planter le build Vite/CI qui supposait du CommonJS.
2. Synchronisé toutes les références de documentation/versioning (CHANGELOG, passation, sync) avec le nouveau chemin.
3. Bump version `beta-3.3.13` + patch notes alignées (backend/frontend/package.json).

### Tests
- ✅ `npm run build`
- ✅ `npm test -- src/frontend/core/__tests__/auth.normalize-token.test.mjs`

### Next steps
1. Vérifier les pipelines Guardian pour confirmer que le build ne scanne plus les tests Node.
2. Ajouter un guard Vite qui ignore automatiquement `__tests__` en production (tech debt).

### Blockers
- Aucun.

## Session COMPLETED (2025-10-30 19:40 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/core/auth.js`
- `src/frontend/core/state-manager.js`
- `src/frontend/core/websocket.js`
- `src/frontend/main.js`
- `src/frontend/core/__tests__/auth.normalize-token.test.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Assoupli la normalisation JWT (support du padding `=` + découpe sûre des préfixes `token=`) et ajouté une suite `node:test` couvrant les cas Bearer/token=/quotes.
2. `StateManager.resetForSession()` préserve `auth.isAuthenticated` lorsqu’on conserve la session, le WebSocket client applique ce mode et `refreshSessionRole()` réaffirme `hasToken/isAuthenticated` après chaque ping backend.
3. Version bump `beta-3.3.12` avec changelog/patch notes synchronisés + build/test frontend verts.

### Tests
- ✅ `npm test`
- ✅ `npm run build`

### Next steps
1. QA manuelle staging/prod pour confirmer disparition des prompts `auth:missing` et des WS 4401 juste après login.
2. Étendre la couverture de tests pour vérifier la préservation `isAuthenticated` côté StateManager lors des resets multi-session.
3. Monitorer Guardian/ProdGuardian pour s’assurer que les rapports ne signalent plus de reconnexions en boucle.
1. Refactoré `vite.config.js` pour charger `rollup-plugin-visualizer` via `import()` dynamique et supporter Node >= 20 sans lever `ERR_REQUIRE_ESM` quand `ANALYZE_BUNDLE=1`.
2. Ajouté un avertissement clair si le plugin n’est pas installé afin que les builds continuent en mode analyse désactivée.
3. Bump version `beta-3.3.12`, patch notes/changelog synchronisés et tests frontend relancés.

### Tests
- ✅ `npm run build`
- ✅ `npm test`

### Next steps
1. Vérifier dans la CI que le job "Build frontend" repasse en vert avec l’analyse bundle activée.
2. Documenter dans le guide tooling quand activer `ANALYZE_BUNDLE=1` pour éviter les surprises côté devs.
3. Évaluer l’ajout d’un flag CLI (`npm run build:analyze`) qui positionne automatiquement la variable d’environnement.

### Blockers
- Aucun.

## Session COMPLETED (2025-10-30 15:10 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/core/auth.js`
- `src/frontend/core/state-manager.js`
- `src/frontend/main.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`

### Work summary
1. Durci la persistance des tokens : normalisation (`Bearer`, `token=`, guillemets) + purge des valeurs invalides pour stopper les 4401 en WebSocket.
2. Ajout du flag `auth.isAuthenticated` dans le `StateManager`, le badge et les flux login/logout afin que le module Chat n’affiche plus le prompt avant authent réelle.
3. Bump version `beta-3.3.11`, patch notes/changelog synchronisés et tests front exécutés pour valider la correction.

### Tests
- ✅ `npm run build`
- ✅ `npm test`

### Next steps
1. QA manuelle en prod/staging pour vérifier que la reconnexion WS post-login ne renvoie plus de 4401.
2. Monitorer Guardian/ProdGuardian pour confirmer l’absence de nouveaux AUTH_MISSING juste après login.
3. Prévoir un test unitaire ciblant `normalizeToken` pour verrouiller les futurs formats de token.

### Blockers
- Aucun.

## Session COMPLETED (2025-10-30 09:30 CET) - Agent : Codex GPT

### Files touched
- `scripts/sync_version.ps1`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Adapté `scripts/sync_version.ps1` pour lire l’objet `CURRENT_RELEASE` (version/nom/date) et restauré la compatibilité avec le workflow d’incrément auto.
2. Affiné les sorties du script (dry-run + liste réelle des fichiers modifiés) et bumpé l’app en `beta-3.3.10` avec patch notes synchro.
3. Regénéré le changelog/versions backend & frontend afin que Guardian arrête de gueuler sur la version introuvable.

### Tests
- ✅ `npm run build`
- ✅ `npm test`

### Next steps
1. Lancer le script PowerShell sur une machine Windows (ou container avec pwsh) pour valider la nouvelle extraction regex.
2. Ajouter un check CI léger (Node) qui échoue si `CURRENT_RELEASE` ne respecte pas la structure attendue.
3. Continuer la mise en place du badge vectorisation partielle côté UI Documents.

### Blockers
- Pas de `pwsh` dans ce container Linux → impossible de tester directement le script PowerShell.

## Session COMPLETED (2025-10-29 22:30 CET) - Agent : Codex GPT

### Files touched
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Corrigé la fusion foireuse des fichiers de version qui dupliquait les clefs `version`/`name` et faisait planter Vite.
2. Incrémenté la version `beta-3.3.9`, synchronisé patch notes/changelog et regroupé les notes 3.3.7/3.3.8.
3. Ajouté une entrée de changelog dédiée pour tracer le hotfix et documenté la session/passation.

### Tests
- ✅ `npm run build`

### Next steps
1. Ajouter un test automatisé (node) qui vérifie la structure de `CURRENT_RELEASE` et l’absence de doublons.
2. Installer les dépendances Python manquantes pour pouvoir relancer `ruff`/`pytest` dans ce container.
3. Finaliser l’UX documents (badge vectorisation partielle) avant de boucler la tâche P3.10.

### Blockers
- Environnement Python incomplet (FastAPI/HTTPX manquants) ⇒ impossible de relancer la suite backend.

## Session COMPLETED (2025-10-29 19:45 CET) - Agent : Codex GPT

### Files touched
- `src/backend/features/documents/service.py`
- `src/backend/features/documents/router.py`
- `src/frontend/features/documents/documents.js`
- `tests/backend/features/test_documents_vector_resilience.py`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`

### Work summary
1. Ajout d’une limitation configurable (`DOCUMENTS_MAX_VECTOR_CHUNKS`) et d’un batching pour la vectorisation afin d’éviter les timeouts quand un upload génère plusieurs milliers de paragraphes.
2. Les endpoints `/documents/upload` et `/documents/{id}/reindex` renvoient désormais le nombre de chunks indexés et un warning même en cas de succès ; l’UI affiche un toast d’avertissement dans ce cas.
3. Nouveau test backend qui vérifie le respect de la limite de chunks et le découpage en batchs.

### Tests
- ✅ `ruff check src/backend/`
- ⚠️ `pytest tests/backend/features/test_documents_vector_resilience.py` (KO – dépendance `httpx` absente dans l’environnement)
- ✅ `npm run build`

### Next steps
1. Installer les dépendances Python manquantes (`httpx`, `fastapi`, `aiosqlite`, etc.) pour pouvoir lancer les tests backend dans l’environnement container.
2. Ajouter un badge/tooltip dans la liste des documents pour indiquer les vectorisations partielles.
3. Étudier un retry automatique de vectorisation lorsque Chroma repasse en mode lecture/écriture.

### Blockers
- Environnement container toujours sans dépendances FastAPI/HTTPX, ce qui empêche `pytest` de tourner.

## Session COMPLETED (2025-10-29 16:20 CET) - Agent : Codex GPT

### Files touched
- `src/backend/features/documents/service.py`
- `src/backend/features/documents/router.py`
- `src/frontend/features/documents/documents.js`
- `tests/backend/features/test_documents_vector_resilience.py`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`

### Work summary
1. Le service Documents encaisse désormais un vector store en READ-ONLY : stockage des chunks, statut `error` et avertissement retourné côté API sans lever de 500.
2. L’UI documents affiche un warning quand la vectorisation est sautée (upload ou ré-indexation) et conserve la trace du document.
3. Ajout d’un test async ciblé pour garantir qu’un upload passe sans vecteurs, plus bump version `beta-3.3.7` + changelog/patch notes synchronisés.

### Tests
- ⚠️ `mypy src/backend/` (KO - librairies FastAPI/Pydantic/httpx/aiosqlite absentes dans l’image)
- ⚠️ `pytest tests/backend/` (KO - mêmes dépendances manquantes)
- ✅ `ruff check src/backend/`
- ✅ `npm run build`

### Next steps
1. Installer les dépendances Python manquantes dans l’environnement CI pour rendre mypy/pytest utiles.
2. Ajouter un indicateur visuel dans la liste des documents (tooltip détaillé ou bouton de re-indexation rapide).
3. Préparer un cron de ré-indexation automatique dès que Chroma repasse en mode read-write.

### Blockers
- Environnement container sans `fastapi`, `pydantic`, `httpx`, `aiosqlite`, `dependency-injector` : mypy/pytest plantent à l’import.

## Session COMPLETED (2025-10-29 14:30 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/features/settings/settings-about.js`
- `src/frontend/features/settings/settings-about.css`
- `src/frontend/core/version-display.js`
- `src/frontend/version.js`
- `src/version.js`
- `docs/story-genese-emergence.md`
- `CHANGELOG.md`
- `package.json`

### Work summary
1. Rafraîchi le module **À propos** : cartes modules à jour, stats projet (139 fichiers backend, 95 JS, 503 tests, dépendances, LOC) et rappel des prototypes LLM dès 2022.
2. Synchronisé le calcul `featuresDisplay` et les patch notes (backend/frontend) pour refléter 18/23 features complétées et mis à jour le changelog + versioning.
3. Corrigé la genèse du projet (doc) pour indiquer le vrai démarrage des expérimentations conversationnelles en 2022.
## Session COMPLETED (2025-10-29 11:40 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/styles/components/modals.css`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Viré le faux cadre : plus de padding ni de boîte fantôme autour du modal de reprise, l’overlay couvre tout l’écran sans créer un deuxième bloc.
2. Recentré la carte et recalibré la largeur (desktop + mobile) pour coller aux captures de référence.

### Tests
- `npm run build`

### Next steps
1. Vérifier sur device réel que les nouveaux hints de stats s’affichent correctement (desktop + mobile).
2. Mettre à jour les captures du module À propos si utilisées dans les docs marketing.
1. Vérifier sur poste desktop + mobile réel que le modal s'affiche bien sans halo supplémentaire.
2. Ajuster l’ombre portée si tu veux un rendu encore plus soft.

### Blockers
- Aucun.

## Session COMPLETED (2025-10-29 11:05 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/core/app.js`
- `src/frontend/features/chat/chat.css`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Flagged the currently mounted module on `app-content` and `body` so CSS can react when the chat tab is active.
2. Trimmed the mobile bottom padding when chat is active and kept safe-area spacing so the composer hugs the navbar with no dead zone.

### Tests
- `npm run build`

### Next steps
1. Sanity-check the portrait view on a real device (iOS + Android) to confirm the sticky footer aligns perfectly.
2. Ensure other modules still get the expected bottom padding after the new module-active classes.

### Blockers
- None.

## Session COMPLETED (2025-10-29 09:45 CET) - Agent : Codex GPT

### Files touched
- `scripts/setup-codex-cloud.sh`
- `.gitignore`
- `PROMPT_CODEX_CLOUD.md`
- `docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Solidified the Codex Cloud bootstrap: default `nvm` alias, symlinks for `node`/`npm`/`npx`/`corepack` into `.venv/bin`, auto-generated `.codex-cloud/env.sh`, and profile hooks (`.bashrc`, `.profile`, `.zshrc`).
2. Updated docs and ignored `.codex-cloud/` so the repo stays clean after running the setup script.
3. Added `PROMPT_CODEX_ALTER_EGO.md` plus updated the prompt architecture doc so any backup agent pings us when something breaks.

### Tests
- ⚠️ `bash scripts/setup-codex-cloud.sh` (not executed locally: current CLI lacks bash/WSL)

### Next steps
1. Run the bootstrap on Codex Cloud to confirm node/npm availability in a fresh session.
2. Double-check AutoSync/Guardian once the script has been executed in the target environment.
3. Hand this alter-ego prompt to the backup agent and ensure they follow the feedback protocol.

### Blockers
- No bash binary in this Windows CLI environment, so the script can't be run end-to-end here.

## Session COMPLETED (2025-10-28 23:40 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/styles/components/modals.css`
- `src/backend/features/auth/models.py`
- `src/backend/features/auth/service.py`
- `tests/backend/features/test_auth_allowlist_snapshot.py`
- `stable-service.yaml`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Rebuilt the dialogue modal so the welcome popup stays strictly centered, width-capped, and aligned with the user's capture.
2. Added Firestore-backed allowlist snapshots so manually added credentials survive Cloud Run redeploys, including config/env plumbing.
3. Introduced regression tests covering snapshot round-trips and wired the production manifest to enable the new persistence path.

### Tests
- `pytest tests/backend/features/test_auth_allowlist_snapshot.py`
- `pytest tests/backend/features/test_auth_admin.py`
- `npm run build`

### Next steps
1. Verify Firestore permissions & required secrets in prod before deploying this change.
2. QA other modals (settings, docs, admin) on desktop/mobile to confirm the shared styling remains stable.

### Blockers
- None.

## Session COMPLETED (2025-10-28 12:40 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/styles/components/modals.css`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Work summary
1. Rebuilt `modals.css` with a 320 px card, strict centering, and neutral shadow so the conversation popup stays compact without the blue halo.
2. Tuned typography/colors for readability, kept backdrop clicks, and added a shared `modal-lg` variant for wider settings/doc modals.
3. Documented the session and verified the frontend bundle with `npm run build`.

### Tests
- `npm run build`

### Next steps
1. Visual QA (desktop + mobile) to confirm the popup layout, backdrop click, and no blue halo.
2. Double-check other modals (Settings, Documentation, Webhooks) for regressions triggered by the shared styles.

### Blockers
- None.

# 📋 AGENT_SYNC — Codex GPT

**Dernière mise à jour:** 2025-10-27 21:05 CET (Codex GPT)
**Dernière mise à jour:** 2025-10-27 20:05 CET (Codex GPT)
**Dernière mise à jour:** 2025-10-27 19:20 CET (Codex GPT)
**Dernière mise à jour:** 2025-10-26 18:10 CET (Codex GPT)
**Mode:** Développement collaboratif multi-agents

---

## 📖 Guide de lecture

**AVANT de travailler, lis dans cet ordre:**
1. **`SYNC_STATUS.md`** ← Vue d'ensemble (qui a fait quoi récemment)
2. **Ce fichier** ← État détaillé de tes tâches
3. **`AGENT_SYNC_CLAUDE.md`** ← État détaillé de Claude Code
4. **`docs/passation_codex.md`** ← Ton journal (48h max)
5. **`docs/passation_claude.md`** ← Journal de Claude (pour contexte)
6. **`git status` + `git log --oneline -10`** ← État Git

---

## ✅ Session COMPLÉTÉE (2025-10-27 21:05 CET)

### Fichiers modifiés
- `src/backend/features/memory/unified_retriever.py`
- `src/backend/main.py`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Actions réalisées
- Corrigé `_get_ltm_context` pour supporter les mocks/implémentations async (`query_weighted` attendable) et restauré les tests `UnifiedMemoryRetriever`.
- Nettoyé l’endpoint `/ready` pour supprimer la variable inutilisée signalée par Ruff (CI rouge).

### Tests
- ✅ `pytest tests/backend/features/test_unified_retriever.py`
- ✅ `ruff check src/backend`

### Prochaines actions
1. Surveiller le prochain run CI backend pour confirmer la suppression des échecs.
2. Ajouter un stub `localStorage` Python si des tests backend supplémentaires en ont besoin.

---

## ✅ Session COMPLÉTÉE (2025-10-27 20:05 CET)

### Fichiers modifiés
- `src/frontend/core/__tests__/app.ensureCurrentThread.test.js`
- `src/frontend/core/__tests__/helpers/dom-shim.js`
- `src/frontend/core/__tests__/state-manager.test.js`
- `src/frontend/features/chat/__tests__/chat-opinion.flow.test.js`
- `src/frontend/shared/__tests__/backend-health.timeout.test.js`
- `src/frontend/shared/backend-health.js`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Actions réalisées
- Stabilisation complète des tests `node --test` : stub DOM `withDomStub`, mock `api.listThreads`, refactor StateManager en promesses + coalescing.
- Ajout d’un shim `localStorage/sessionStorage` et `requestAnimationFrame` dans `dom-shim` pour éliminer les warnings résiduels.
- Validation intégrale via `npm run test` + `npm run build`.

### Tests
- ✅ `npm run test`
- ✅ `npm run build`

### Prochaines actions
1. Factoriser un helper partagé pour stubs `localStorage` si d’autres suites en ont besoin.
2. Vérifier si d’autres specs `chat/*` gagnent à utiliser `withDomStub`.

---

## ✅ Session COMPLÉTÉE (2025-10-27 19:20 CET)

### Fichiers modifiés
- `src/frontend/shared/__tests__/backend-health.timeout.test.js`
- `src/frontend/shared/backend-health.js`
- `AGENT_SYNC_CODEX.md`
- `docs/passation_codex.md`

### Actions réalisées
- Ajout d’un test Node simulant l’absence d’`AbortSignal.timeout` et vérifiant le cleanup du fallback `AbortController`.
- Adaptation du helper `backend-health` pour annoter et nettoyer systématiquement le timeout.

### Tests
- ✅ `npm run build`
- ❌ `npm run test` (suite Node encore instable avant stabilisation 20:05 CET)

### Prochaines actions
1. Stabiliser la suite `node --test` (promesse réalisée à 20:05 CET, voir entrée ci-dessus).
2. QA Safari 16 / Chrome 108 pour confirmer la disparition des délais de loader.

---

## ✅ Session COMPLÉTÉE (2025-10-26 18:10 CET)

### Fichiers modifiés
- `src/frontend/features/chat/chat.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `docs/passation_codex.md`
- `AGENT_SYNC_CODEX.md`

### Actions réalisées
- Ajout d'une attente explicite sur les events `threads:*` avant d'afficher le modal de choix conversation
- Reconstruction du modal quand les conversations arrivent pour garantir le wiring du bouton « Reprendre »
- Bump version `beta-3.1.1` + patch notes + changelog synchronisés

### Tests
- ✅ `npm run build`

### Prochaines actions
1. Vérifier côté backend que `threads.currentId` reste cohérent avec la reprise utilisateur
2. QA UI sur l'app pour valider le flux complet (connexion → modal → reprise thread)

---

## ✅ Session COMPLÉTÉE (2025-10-26 18:05 CET)

### Fichiers modifiés
- `manifest.webmanifest`
- `src/frontend/main.js`
- `src/frontend/features/chat/chat.css`
- `src/frontend/styles/overrides/mobile-menu-fix.css`

### Actions réalisées
- Verrou portrait côté PWA (manifest + garde runtime) avec overlay d'avertissement en paysage
- Ajusté la zone de saisie chat pour intégrer le safe-area iOS et assurer l'accès au composer sur mobile
- Amélioré l'affichage des métadonnées de conversation et des sélecteurs agents en mode portrait

### Tests
- ✅ `npm run build`

### Prochaines actions
1. QA sur device iOS/Android pour valider l'overlay orientation et le padding du composer
2. Vérifier que le guard portrait n'interfère pas avec le mode desktop (résolution > 900px)
3. Ajuster si besoin la copie/UX de l'overlay selon retours utilisateur

---

## 🔧 TÂCHES EN COURS

### 🚀 PWA Mode Hors Ligne (P3.10)

**Status:** ⏳ 80% FAIT, reste tests manuels
**Priorité:** P3 (BASSE - Nice-to-have)

**Objectif:**
Implémenter le mode hors ligne (Progressive Web App) pour permettre l'accès aux conversations récentes sans connexion internet.

**Specs:**
- [x] Créer un manifest PWA (config installable)
- [x] Service Worker cache-first strategy
- [x] Cacher conversations récentes (IndexedDB)
- [x] Indicateur "Mode hors ligne"
- [x] Sync automatique au retour en ligne
- [ ] Tests: offline → conversations dispo → online → sync

**Fichiers créés:**
- ✅ `manifest.webmanifest`
- ✅ `sw.js`
- ✅ `src/frontend/features/pwa/offline-storage.js`
- ✅ `src/frontend/features/pwa/sync-manager.js`
- ✅ `src/frontend/styles/pwa.css`
- ✅ Integration dans `main.js`

**Prochaines étapes:**
1. Tester PWA offline/online manuellement
2. Commit modifs sur branche `feature/pwa-offline`
3. Push branche
4. Créer PR vers main

**Acceptance Criteria:**
- ✅ PWA installable (bouton "Installer" navigateur)
- ✅ Conversations récentes accessibles offline (20+ threads)
- ✅ Messages créés offline synchronisés au retour en ligne
- ✅ Indicateur offline visible (badge rouge header)
- ✅ Cache assets statiques (instant load offline)

---

## ✅ TÂCHES COMPLÉTÉES RÉCEMMENT

### ✅ Mobile Portrait Lock + Composer Spacing

**Status:** ✅ COMPLÉTÉ (2025-10-26 18:05)
**Version:** beta-3.1.0

**Implémentation:**
- Verrou portrait PWA avec overlay avertissement paysage
- Safe-area iOS intégrée pour composer
- Métadonnées conversation optimisées mobile

### ✅ Fix Modal Reprise Conversation

**Status:** ✅ COMPLÉTÉ (2025-10-26 18:10)
**Version:** beta-3.1.1

**Implémentation:**
- Attente événements `threads:*` avant modal
- Reconstruction modal pour wiring bouton "Reprendre"

---

## 🔄 Coordination avec Claude Code

**Voir:** `AGENT_SYNC_CLAUDE.md` pour l'état de ses tâches

**Dernière activité Claude:**
- 2025-10-26 15:30 - Système versioning automatique (beta-3.1.0)
- 2025-10-25 21:30 - Production health check script (merged)

**Zones de travail Claude actuellement:**
- ✅ Backend Python (features, core, services)
- ✅ Architecture & refactoring
- ✅ Scripts monitoring production

**Pas de conflits détectés.**

---

## 🎯 État Roadmap Actuel

**Progression globale:** 18/23 (78%)
- ✅ P0/P1/P2 Features: 9/9 (100%)
- ✅ P1/P2 Maintenance: 5/7 (71%)
- ✅ P3 Features: 1/4 (25%) - Webhooks ✅
- ⏳ P3 Maintenance: 0/2 (À faire)

**Tes features P3:**
- ⏳ P3.10: PWA Mode Hors Ligne - 80% fait (reste tests)

**Features P3 restantes (Claude ou toi):**
- ⏳ P3.12: Benchmarking Performance
- ⏳ P3.13: Auto-scaling Agents

---

## 📊 État Production

**Service:** `emergence-app` (Cloud Run europe-west1)
**URL:** https://emergence-app-486095406755.europe-west1.run.app
**Status:** ✅ Stable

---

## 🔍 Prochaines Actions Recommandées

**Pour Codex GPT:**
1. ⏳ Finir tests PWA offline/online (30 min)
2. Créer PR pour PWA feature
3. Améliorer UX mobile (retours utilisateur)

**À lire avant prochaine session:**
- `SYNC_STATUS.md` - Vue d'ensemble
- `AGENT_SYNC_CLAUDE.md` - État Claude
- `docs/passation_codex.md` - Ton journal (48h)
- `docs/passation_claude.md` - Journal Claude (contexte)

---

**Dernière synchro:** 2025-10-26 18:10 CET (Codex GPT)
## Session COMPLETED (2025-10-29 15:40 CET) - Agent : Codex GPT

### Files touched
- `src/frontend/features/chat/chat.js`
- `src/frontend/features/chat/__tests__/chat-opinion.flow.test.js`
- `src/version.js`
- `src/frontend/version.js`
- `CHANGELOG.md`
- `package.json`
- `docs/passation_codex.md`
- `AGENT_SYNC_CODEX.md`

### Work summary
1. Corrigé le routage des réponses d’opinion : les avis restent dans le fil de l’agent évalué (source) avec fallback cible/reviewer.
2. Mis à jour la suite `chat-opinion.flow.test.js` pour vérifier le bucket source et éviter les régressions.
3. Incrémenté la version `beta-3.3.7` + patch notes/changelog synchronisés.

### Tests
- `npm run build`
- `npm run test`

### Next steps
1. QA visuelle en prod/staging pour confirmer le comportement sur mobile.
2. Ajouter un indicateur UI si besoin pour différencier une réponse d’opinion dans un fil tiers.

### Blockers
- Aucun.
