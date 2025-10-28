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
