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


