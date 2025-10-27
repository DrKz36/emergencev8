# Journal de Passation — Codex GPT

**Archives >48h:** Voir `docs/archives/passation_archive_*.md`

**RÈGLE:** Ce fichier contient UNIQUEMENT les entrées des 48 dernières heures.
**Rotation:** Entrées >48h sont automatiquement archivées.

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
