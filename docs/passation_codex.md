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

### Tests
- ✅ `npm run build`

### Travail de Claude Code pris en compte
- Aucun changement concurrent identifié sur la zone Settings/About ou sur la documentation de genèse.

### Prochaines actions recommandées
1. QA visuelle du module À propos (desktop + mobile) pour vérifier le rendu des hints et la lisibilité des nouvelles stats.
2. Mettre à jour les captures/screens si elles sont utilisées dans la communication produit.

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
