# 📝 Journal de Passation — Claude Code

> **Rotation automatique**: Garder uniquement les 48 dernières heures.
> Les entrées plus anciennes sont archivées dans `docs/archives/`.

---

## 2025-11-30 07:30 CET — Documentation Multi-Agents

### Contexte
Suite de la session audit - documentation des fichiers de sync inter-agents.

### Travail effectué

1. **Réécrit `SYNC_STATUS.md`**
   - Le fichier était corrompu (contenait une copie de AGENT_SYNC_GEMINI.md, ~60k tokens)
   - Nouveau format propre : vue d'ensemble concise (~100 lignes)
   - Tableau état des 3 agents avec timestamps
   - Activité récente 48h résumée
   - Roadmap progress

2. **Mis à jour `AGENT_SYNC_CODEX.md`**
   - Ajouté session "APPLIED" en haut pour tracer que Claude a appliqué le plan de Codex
   - Marqué les "Next steps" du plan comme complétés (✅ FAIT)

3. **Créé `docs/passation_gemini.md`**
   - Le fichier n'existait pas (AGENT_SYNC_GEMINI.md existait mais pas le journal)
   - Format standard de passation

### Fichiers modifiés

```
SYNC_STATUS.md (réécrit)
AGENT_SYNC_CODEX.md
AGENT_SYNC_GEMINI.md
docs/passation_gemini.md (créé)
docs/passation_claude.md (cette entrée)
AGENT_SYNC_CLAUDE.md
```

---

## 2025-11-30 07:15 CET — Audit Sécurité (beta-3.3.39)

### Contexte
Application du plan d'audit sécurité `plans/audit-fixes-2025-11-23.md`.

### Travail effectué

1. **CORS durci**
   - Problème: `allow_origins=["*"]` + `allow_credentials=True` = vulnérabilité
   - Fix: Origines explicites via `CORS_ALLOWED_ORIGINS` ou fallback dev
   - Fichier: `src/backend/main.py:495-516`

2. **Monitoring auth**
   - Problème: `verify_admin()` était un stub qui autorisait tout
   - Fix: Vraie auth JWT avec vérification rôle admin
   - Fichier: `src/backend/features/monitoring/router.py:30-77`

3. **JWT fail fast**
   - Problème: Fallback `"change-me"` permettait démarrage avec secret faible
   - Fix: Refuse de démarrer sauf en dev mode (génère secret temporaire)
   - Fichier: `src/backend/features/auth/service.py:2419-2438`

4. **AutoSync fichiers**
   - Problème: Surveillait `AGENT_SYNC.md` et `docs/passation.md` (obsolètes)
   - Fix: Nouvelle structure multi-fichiers
   - Fichier: `src/backend/features/sync/auto_sync_service.py:127-140`

5. **Chargement .env**
   - Problème: Variables d'env non chargées automatiquement en dev
   - Fix: `load_dotenv()` au démarrage de main.py
   - Fichier: `src/backend/main.py:10-17`

### Décisions prises

- **Dev mode exception**: Plutôt que bloquer complètement le dev local, on génère un secret temporaire quand `AUTH_DEV_MODE=1`
- **CORS fallback**: Liste hardcodée pour dev (localhost + Cloud Run URL) plutôt que wildcard

### Blocages rencontrés

- Le backend ne démarrait plus après le fix JWT → Résolu avec dev mode exception
- Variables d'env non chargées → Résolu avec python-dotenv

### Tests passés

- `ruff check` ✅
- `mypy` ✅
- `/ready` → ok
- `/api/monitoring/*` → 401 (attendu)

### Fichiers modifiés

```
src/backend/main.py
src/backend/features/auth/service.py
src/backend/features/monitoring/router.py
src/backend/features/sync/auto_sync_service.py
CHANGELOG.md
src/version.js
src/frontend/version.js
package.json
AGENT_SYNC_CLAUDE.md (créé)
docs/passation_claude.md (créé)
```

---

*Fin de session.*
