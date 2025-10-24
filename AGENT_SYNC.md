# 📋 AGENT_SYNC.md - État Synchronisation Multi-Agents

**Dernière mise à jour:** 2025-10-24 19:30 CET
**Mode:** Développement collaboratif multi-agents

### 🛠️ NOUVELLE TÂCHE - Workflow Scripts Claude Code (2025-10-24 14:30)
**Agent:** Claude Code Local (à implémenter)
**Priorité:** P1 (IMPORTANT - améliore workflow dev)
**Prompt:** `docs/PROMPT_CLAUDE_LOCAL_SETUP.md`

**Objectif:**
Créer scripts manquants pour workflow optimal Claude Code Cloud (alter ego qui tourne en environnement éphémère sans deps).

**Tâches:**
1. **P0:** `scripts/run-all-tests.ps1` - Script test complet rapide (pytest + ruff + mypy + npm)
2. **P1:** `scripts/check-prod-health.ps1` - Vérif santé prod avec JWT (résout 403)
3. **P1:** `docs/CLAUDE_CODE_WORKFLOW.md` - Doc workflow pour Claude Code
4. **P2:** `scripts/pre-commit-check.ps1` - Validation avant commit
5. **P3:** Améliorer `scripts/check-github-workflows.ps1` - Dashboard CI/CD

**Pourquoi:**
- Claude Code Cloud tourne en env éphémère (pas de deps installées)
- Impossible de lancer tests localement → besoin scripts pour valider code
- Production répond 403 → besoin script avec JWT pour healthchecks
- Pas de doc workflow spécifique AI → deviner comment utiliser scripts existants

### 🔍 AUDIT POST-MERGE (2025-10-24 13:40 CET)
**Agent:** Claude Code
**Rapport:** `docs/audits/AUDIT_POST_MERGE_20251024.md`

**Verdict:** ⚠️ **ATTENTION - Environnement tests à configurer**

**Résultats:**
- ✅ Code quality: Ruff check OK
- ✅ Sécurité: Pas de secrets hardcodés
- ✅ Architecture: Docs à jour, structure cohérente
- ⚠️ Tests backend: KO (deps manquantes: httpx, pydantic, fastapi)
- ⚠️ Build frontend: KO (node_modules manquants)
- ⚠️ Production: Endpoints répondent 403 (à vérifier si normal)

**PRs auditées:**
- #12: Webhooks ✅ (code propre, HMAC, retry 3x)
- #11, #10, #7: Fix cockpit SQL ✅ (3 bugs corrigés)
- #8: Sync commits ✅

**Tests skippés analysés (6 → 5 après fix):**
- ✅ test_guardian_email_e2e.py: Skip normal (reports/ dans .gitignore)
- ✅ test_cost_telemetry.py (3x): Skip normal (Prometheus optionnel)
- ✅ test_hybrid_retriever.py: Placeholder E2E (TODO)
- ✅ test_unified_retriever.py: **FIXÉ** (Mock → AsyncMock)

**Actions requises:**
1. Configurer environnement tests (venv + npm install)
2. Lancer pytest + build pour valider merges
3. Vérifier prod Cloud Run (403 sur /ready anormal?)

---

## 🎯 État Roadmap Actuel

**Progression globale:** 15/20 (75%)
- ✅ P0/P1/P2 Features: 9/9 (100%)
- ✅ P1/P2 Maintenance: 5/7 (71%)
- ✅ P3 Features: 1/4 (25%) - Webhooks terminés ✅
- ⏳ P3 Maintenance: 0/2 (À faire)

**Features P3 restantes:**
- ⏳ P3.10: PWA Mode Hors Ligne (Codex GPT - en cours)
- ⏳ P3.12: Benchmarking Performance
- ⏳ P3.13: Auto-scaling Agents

---

## 🔧 TÂCHES EN COURS

### 🚀 Codex GPT — PWA Mode Hors Ligne (P3.10)

**Status:** ⏳ EN COURS
**Branche:** `feature/pwa-offline`
**Durée estimée:** 4 jours
**Priorité:** P3 (BASSE - Nice-to-have)

**Objectif:**
Implémenter le mode hors ligne (Progressive Web App) pour permettre l'accès aux conversations récentes sans connexion internet.

**Specs (ROADMAP.md:144-153):**
- [ ] Créer `manifest.json` (PWA config)
- [ ] Service Worker cache-first strategy
- [ ] Cacher conversations récentes (IndexedDB)
- [ ] Indicateur "Mode hors ligne"
- [ ] Sync automatique au retour en ligne
- [ ] Tests: offline → conversations dispo → online → sync

**Fichiers à créer:**
- `public/manifest.json`
- `src/frontend/sw.js` (Service Worker)
- `src/frontend/features/pwa/offline-storage.js`
- `src/frontend/features/pwa/sync-manager.js`
- `src/frontend/styles/pwa.css`

**Acceptance Criteria:**
- ✅ PWA installable (bouton "Installer" navigateur)
- ✅ Conversations récentes accessibles offline (20+ threads)
- ✅ Messages créés offline synchronisés au retour en ligne
- ✅ Indicateur offline visible (badge rouge header)
- ✅ Cache assets statiques (instant load offline)

---

## ✅ TÂCHES COMPLÉTÉES RÉCEMMENT

### ✅ Claude Code Web — Webhooks et Intégrations (P3.11)

**Status:** ✅ COMPLÉTÉ (2025-10-24)
**Branche:** `claude/implement-webhooks-011CURfewj5NWZskkCoQcHi8` → Merged to main
**PR:** #12

**Implémentation:**
- ✅ Backend: tables `webhooks` + `webhook_deliveries` (migration 010)
- ✅ Endpoints REST `/api/webhooks/*` (CRUD + deliveries + stats)
- ✅ Événements: thread.created, message.sent, analysis.completed, debate.completed, document.uploaded
- ✅ Delivery HTTP POST avec HMAC SHA256
- ✅ Retry automatique 3x (5s, 15s, 60s)
- ✅ UI: Settings > Webhooks (modal, liste, logs, stats)

**Tests:** ✅ Ruff OK, ✅ Build OK, ✅ Mypy OK

### ✅ Claude Code — Fix Cockpit SQL Bugs (P2)

**Status:** ✅ COMPLÉTÉ (2025-10-24)
**PRs:** #11, #10, #7

**Bugs fixés:**
- ✅ Bug SQL `no such column: agent` → `agent_id`
- ✅ Filtrage session_id trop restrictif → `session_id=None`
- ✅ Agents fantômes dans Distribution → whitelist stricte
- ✅ Graphiques vides → fetch données + backend metrics

---

## 🔄 Coordination Multi-Agents

**Branches actives:**
- `main` : Production stable
- `feature/pwa-offline` : Codex GPT (PWA en cours)

**Règles de travail:**
1. **Chacun travaille sur SA branche dédiée** (éviter collisions)
2. **Tester localement AVANT push** (npm run build + pytest)
3. **Documenter dans passation.md** après chaque session (max 48h)
4. **Créer PR vers main** quand feature complète
5. **Ne PAS merger sans validation FG**

**Synchronisation:**
- Codex GPT: Frontend principalement (PWA)
- Claude Code: Backend, monitoring, maintenance, support
- Pas de dépendances entre tâches actuelles → parallélisation OK

---

## 📊 État Production

**Service:** `emergence-app` (Cloud Run europe-west1)
**URL:** https://emergence-app-486095406755.europe-west1.run.app
**Status:** ✅ Stable (dernière vérif: 2025-10-24 19:00)

**Derniers déploiements:**
- 2025-10-24: Webhooks + Cockpit fixes
- 2025-10-23: Guardian v3.0.0 + UI fixes

**Monitoring:**
- ✅ Guardian système actif (pre-commit hooks)
- ✅ ProdGuardian vérifie prod avant push
- ✅ Tests: 471 passed, 13 failed (ChromaDB env local), 6 errors

---

## 🔍 Prochaines Actions Recommandées

**Pour Codex GPT:**
1. Continuer implémentation PWA (feature/pwa-offline)
2. Tests offline/online scenarios
3. PR vers main quand complet

**Pour Claude Code:**
1. Monitoring production
2. Support technique utilisateur
3. Maintenance code (fix bugs, optimisations)

**Pour les deux:**
- Lire [docs/passation.md](docs/passation.md) avant chaque session (état sync 48h)
- Mettre à jour ce fichier après modifications importantes
- Archiver passation.md si >48h (voir règle ci-dessous)

---

## 📚 Documentation Collaboration

**Fichiers clés:**
- `AGENT_SYNC.md` : Ce fichier - état temps réel des tâches
- `docs/passation.md` : Journal sessions dernières 48h
- `docs/archives/passation_archive_*.md` : Archives anciennes sessions
- `CODEV_PROTOCOL.md` : Protocole collaboration détaillé
- `CLAUDE.md` : Configuration Claude Code
- `CODEX_GPT_GUIDE.md` : Guide Codex GPT

**Règle archivage (NEW - 2025-10-24):**
- `docs/passation.md` : Garder UNIQUEMENT dernières 48h
- Sessions >48h : Archiver dans `docs/archives/passation_archive_YYYY-MM-DD_to_YYYY-MM-DD.md`
- Format synthétique : 1 entrée par session (5-10 lignes max)
- Liens vers archives dans header passation.md

---

**Dernière synchro agents:** 2025-10-24 19:30 CET (Claude Code)
