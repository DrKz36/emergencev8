## [2025-10-06 06:12] - Agent: Codex (Déploiement Cloud Run)

### Fichiers modifiés
- `docs/deployments/2025-10-06-agents-ui-refresh.md` (nouveau)
- `docs/deployments/README.md`
- `AGENT_SYNC.md`
- `docs/passation.md`

### Contexte
- Construction d'une nouvelle image Docker avec les derniers commits UI/personnalités et les ajustements CSS présents dans l'arbre local.
- Déploiement de la révision `emergence-app-00268-9s8` sur Cloud Run (image `deploy-20251006-060538`).
- Mise à jour de la documentation de déploiement + synchronisation AGENT_SYNC / passation.

### Actions réalisées
1. `npm run build` (vite 7.1.2) — succès malgré warning importmap.
2. `python -m pytest` — 77 tests OK / 7 erreurs (fixture `app` manquante dans `tests/backend/features/test_memory_concept_search.py`).
3. `ruff check` — 28 erreurs E402/F401/F841 (scripts legacy, containers, tests).
4. `mypy src` — 12 erreurs (benchmarks repo, concept_recall, chat.service, memory.router).
5. `pwsh -File tests/run_all.ps1` — smoke tests API/upload OK.
6. `docker build --platform linux/amd64 -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251006-060538 .`
7. `docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-20251006-060538`.
8. `gcloud run deploy emergence-app --image ...:deploy-20251006-060538 --region europe-west1 --project emergence-469005 --allow-unauthenticated --quiet`.
9. Vérifications `https://.../api/health` (200 OK) et `https://.../api/metrics` (200, metrics désactivées), `/health` renvoie 404 (comportement attendu).

### Tests
- ✅ `npm run build`
- ⚠️ `python -m pytest` (7 erreurs fixture `app` manquante)
- ⚠️ `ruff check` (28 erreurs E402/F401/F841)
- ⚠️ `mypy src` (12 erreurs)
- ✅ `pwsh -File tests/run_all.ps1`

### Prochaines actions recommandées
1. Corriger les suites `pytest`/`ruff`/`mypy` identifiées avant prochaine validation architecte.
2. QA front & WebSocket sur la révision Cloud Run `emergence-app-00268-9s8` (module documentation, personnalités ANIMA/NEO/NEXUS).
3. Surveiller les logs Cloud Run (`severity>=ERROR`) pendant la fenêtre post-déploiement.

### Blocages
- Aucun blocage bloquant, mais les échecs `pytest`/`ruff`/`mypy` restent à adresser.

---
## [2025-10-06 22:10] - Agent: Codex (Frontend)

### Fichiers modifiés
- `src/frontend/features/references/references.js`

### Contexte
- Reprise propre du module "A propos" après la suppression du tutoriel interactif.
- Ajout du guide statique en tête de liste et raccordement à l'eventBus pour les ouvertures externes (WelcomePopup, navigation).

### Actions réalisées
1. Réintégré la version HEAD de `references.js` puis ajouté `tutorial-guide` dans `DOCS` et le bouton d'accès direct.
2. Ajouté `handleExternalDocRequest`, la souscription `references:show-doc` (mount/unmount) et nettoyage du bouton interactif legacy.
3. Vérifié les styles de debug (`debug-pointer-fix.css`) et le `WelcomePopup` (import `EVENTS`, émission `references:show-doc`).
4. `npm run build` (succès, warning importmap existant).

### Tests
- ✅ `npm run build`

### Prochaines actions recommandées
1. Finaliser la refonte de la vue "A propos" (maquette, contenus restants à valider).
2. Relancer les suites backend (`pytest`, `ruff`, `mypy`) avant validation architecte.
3. Mettre à jour la documentation architecture si d'autres modules doc sont retouchés.

### Blocages
- `scripts/sync-workdir.ps1` échoue tant que les nombreuses modifications frontend existantes ne sont pas commit/stash (rebase impossible en dirty state).
## [2025-10-06 20:44] - Agent: Codex (Frontend)

### Fichiers modifiés
- src/frontend/core/app.js
- src/frontend/main.js

### Contexte
- Remise en fonction du menu mobile : les clics sur le burger ne déclenchaient plus l'ouverture faute de binding fiable.

### Actions réalisées
1. Refondu setupMobileNav() pour re-sélectionner les éléments, purger/reposer les listeners et exposer open/close/toggle + isMobileNavOpen après binding.
2. Ajouté une tentative de liaison depuis setupMobileShell() et un fallback sur le bouton lorsque l'attribut `data-mobile-nav-bound` n'est pas en place, en conservant la synchro classes/backdrop.
3. Maintenu les événements mergence:mobile-menu-state pour garder la coordination avec le backdrop/brain panel.

### Tests
- ✅ 
pm run build (warning importmap existant)

### Prochaines actions recommandées
1. QA responsive manuelle (≤760px) pour valider l'ouverture/fermeture via bouton, backdrop et touche Escape.
2. Réduire les overrides CSS historiques (`mobile-menu-fix.css`/`ui-hotfix`) une fois le comportement stabilisé.

### Blocages
- Aucun.
