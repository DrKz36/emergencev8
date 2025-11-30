# 📋 AGENT_SYNC — Claude Code

**Dernière mise à jour:** 2025-11-30 08:45 CET *(inclut note coordination Codex)*
**Mode:** Développement collaboratif multi-agents

---

## 📖 Guide de lecture

**AVANT de travailler, lis dans cet ordre:**
1. **`SYNC_STATUS.md`** ← Vue d'ensemble (qui a fait quoi récemment)
2. **Ce fichier** ← État détaillé de tes tâches (Claude Code)
3. **`AGENT_SYNC_CODEX.md`** ← État détaillé de Codex GPT
4. **`docs/passation_claude.md`** ← Ton journal (48h max)
5. **`docs/passation_codex.md`** ← Journal de Codex (pour contexte)
6. **`git status` + `git log --oneline -10`** ← État Git

---

## ✅ Session 2025-11-30 (suite) — Documentation Multi-Agents

### Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `SYNC_STATUS.md` | Réécrit - Vue d'ensemble propre (était corrompu) |
| `AGENT_SYNC_CODEX.md` | Ajout entrée "Plan appliqué par Claude" |
| `AGENT_SYNC_GEMINI.md` | Mis à jour timestamp + version |
| `docs/passation_gemini.md` | Créé - Journal Gemini |
| `docs/passation_claude.md` | Mise à jour session |

### Actions réalisées

1. **Réécrit `SYNC_STATUS.md`** (était une copie de AGENT_SYNC_GEMINI.md, trop gros)
   - Maintenant c'est une vraie vue d'ensemble concise (~100 lignes)
   - Tableau état des 3 agents
   - Activité récente 48h
   - Roadmap progress

2. **Mis à jour `AGENT_SYNC_CODEX.md`**
   - Ajout session "APPLIED" pour noter que Claude a appliqué le plan de Codex
   - Marqué les next steps comme complétés

3. **Créé `docs/passation_gemini.md`**
   - Journal de passation Gemini (n'existait pas)

---

## 🤝 Note coordination (ajout Codex — 2025-11-30 08:45 CET)

- Synchronisation doc/collab remise à jour côté Codex (`SYNC_STATUS.md`, `AGENT_SYNC_CODEX.md`, journal Codex) après les livraisons sécurité beta-3.3.39.
- Tests repassés: `npm run build`, `pytest tests/backend/features/test_auth_admin.py`, `ruff check` ciblé.
- Service AutoSync (`http://localhost:8000/api/sync/status`) toujours KO → relance conseillée avant prochaines modifs backend.

---

## ✅ Session 2025-11-30 — Audit Sécurité beta-3.3.39

### Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `src/backend/main.py` | CORS durci + chargement `.env` auto via dotenv |
| `src/backend/features/auth/service.py` | JWT fail fast (dev mode exception avec secret temporaire) |
| `src/backend/features/monitoring/router.py` | Auth admin JWT sur tous les endpoints sensibles |
| `src/backend/features/sync/auto_sync_service.py` | Fichiers surveillés mis à jour (nouvelle structure) |
| `CHANGELOG.md` | Nouvelle entrée beta-3.3.39 |
| `src/version.js` | Version bumped |
| `src/frontend/version.js` | Version bumped |
| `package.json` | Version bumped |

### Actions réalisées

1. **CORS durci** ([main.py:495-516](src/backend/main.py#L495-L516))
   - Remplacé `allow_origins=["*"]` par origines explicites
   - Configurable via `CORS_ALLOWED_ORIGINS` (env var)
   - Fallback dev-friendly (localhost + Cloud Run URL)

2. **Endpoints monitoring protégés** ([router.py:30-77](src/backend/features/monitoring/router.py#L30-L77))
   - Nouveau `verify_admin()` avec JWT + rôle admin obligatoire
   - `/api/monitoring/*` retourne 401/403 si non autorisé
   - `/api/monitoring/system/info` aussi protégé

3. **JWT fail fast** ([service.py:2419-2438](src/backend/features/auth/service.py#L2419-L2438))
   - Refuse de démarrer si `AUTH_JWT_SECRET` absent ou faible
   - Exception: `AUTH_DEV_MODE=1` génère un secret temporaire
   - Liste noire: "change-me", "changeme", "secret", "test"

4. **AutoSync fichiers mis à jour** ([auto_sync_service.py:127-140](src/backend/features/sync/auto_sync_service.py#L127-L140))
   - Nouvelle structure: `SYNC_STATUS.md`, `AGENT_SYNC_*.md`, `docs/passation_*.md`
   - Remplacé `AGENT_SYNC.md` (obsolète) par nouveaux fichiers

5. **Chargement .env automatique** ([main.py:10-17](src/backend/main.py#L10-L17))
   - `python-dotenv` charge le `.env` racine au démarrage
   - Permet `AUTH_DEV_MODE=1` en dev local

### Tests

- ✅ `ruff check` - All checks passed
- ✅ `/ready` - db up, vector ready
- ✅ `/api/monitoring/metrics` - 401 (auth requise)
- ✅ `/api/monitoring/system/info` - 401 (auth requise)

### Variables d'environnement ajoutées

| Variable | Valeur | Usage |
|----------|--------|-------|
| `CORS_ALLOWED_ORIGINS` | (optionnel) | Liste d'origines CORS séparées par virgule |
| `AUTH_DEV_MODE` | `1` | Active le mode dev (secret JWT temporaire) |

---

## 🔧 TÂCHES EN COURS

**Aucune** - Session terminée.

---

## 📝 Prochaines actions recommandées

1. **Commit et push** des changements (beta-3.3.39)
2. **Vérifier production** - S'assurer que `AUTH_JWT_SECRET` est bien défini
3. **Documenter** les nouvelles variables d'env dans le README déploiement

---

## 🚨 Points d'attention pour Codex

- **CORS**: Si tu modifies les origines, utilise `CORS_ALLOWED_ORIGINS` (ne pas hardcoder)
- **Monitoring**: Tous les endpoints `/api/monitoring/*` nécessitent maintenant un JWT admin
- **Dev local**: Assure-toi que `.env` racine a `AUTH_DEV_MODE=1`
