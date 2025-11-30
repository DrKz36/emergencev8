# Plan d'action audit sécurité / stabilité (2025-11-23)

## Contexte
Audit du 23/11 : secrets en clair dans le repo, CORS permissif avec cookies, endpoints monitoring/admin sans auth, secret JWT faible/fallback, AutoSync KO (:8000), changelog désordonné.

## Objectifs
- Sécuriser secrets et config (clé JWT, providers, Gmail client).
- Fermer la surface d’attaque API (CORS, auth monitoring/system info).
- Restaurer l’AutoSync et aligner la doc de sync.
- Remettre le changelog et la version story cohérents.

## Actions prioritaires (ordre proposé)
1) **Purge secrets / rotation clés**
   - Retirer du dépôt : `.env`, `gmail_client_secret.json`, `emergence.db`, autres artefacts sensibles.
   - Ignorer ces fichiers (`.gitignore`) et ajouter un template clean (`.env.example` si besoin).
   - Régénérer clés/API (OpenAI/Gemini/Anthropic/ElevenLabs/JWT/Gmail) et documenter l’emplacement sûr (Secret Manager / env local).
   - Ajouter check CI/pre-commit pour refuser `.env`/`*secret*.json`/`.db`.

2) **Durcir auth/CORS**
   - Dans `src/backend/main.py` : restreindre `allow_origins` à la liste des frontends attendus, désactiver `allow_credentials` si `*`, ou passer en origines explicites + credentials.
   - Dans `src/backend/features/monitoring/router.py` : remplacer `verify_admin` stub par dépendance JWT + rôle admin ; bloquer `/api/monitoring/*` et `/api/system/info`.
   - Dans `features/auth/service.py` : supprimer fallback `"change-me"`, rendre `AUTH_JWT_SECRET` obligatoire et fort ; fail fast au démarrage si absent/faible.

3) **AutoSync**
   - Redémarrer/diagnostiquer le service local (:8000) et corriger si crash (logs `scripts/run-backend.ps1` + `backend/features/sync/auto_sync_service.py`).
   - Vérifier la cohérence `SYNC_STATUS.md` vs `AGENT_SYNC_CODEX.md` une fois le service up ; déclencher consolidation si nécessaire.

4) **Changelog / doc**
   - Réordonner `CHANGELOG.md` (beta-3.3.38 au-dessus de 3.3.37/36) pour refléter l’ordre chronologique.
   - Si version ou patch notes doivent bouger, synchroniser `src/version.js`, `src/frontend/version.js`, `package.json`.

## Notes de livraison
- Tests à prévoir après correctifs : `npm run build`, `ruff check src/backend`, `pytest` ciblé (auth/monitoring) et smoke `tests/run_all.ps1` si sync/backend touchés.
- Documenter les rotations de clés hors repo (README ops) et tracer la mise à jour dans `AGENT_SYNC_CODEX.md` + passation.
