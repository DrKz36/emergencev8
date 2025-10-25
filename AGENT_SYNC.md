# 📋 AGENT_SYNC.md - État Synchronisation Multi-Agents

**Dernière mise à jour:** 2025-10-25 21:15 CET
**Mode:** Développement collaboratif multi-agents

---

## 🎯 État Roadmap Actuel

**Progression globale:** 15/20 (75%)
- ✅ P0/P1/P2 Features: 9/9 (100%)
- ✅ P1/P2 Maintenance: 5/7 (71%)
- ✅ P3 Features: 1/4 (25%) - Webhooks terminés ✅
- ⏳ P3 Maintenance: 0/2 (À faire)

**Features P3 restantes:**
- ⏳ P3.10: PWA Mode Hors Ligne (Codex GPT - 80% fait, reste tests)
- ⏳ P3.12: Benchmarking Performance
- ⏳ P3.13: Auto-scaling Agents

**Nouveaux scripts workflow (Claude Code Local):**
- ✅ P0: `scripts/run-all-tests.ps1` (tests complets backend+frontend)
- ✅ P1 Doc: `docs/CLAUDE_CODE_WORKFLOW.md` (guide actions rapides)
- ⏳ P1 Health: `scripts/check-prod-health.ps1` (en cours - 2-3h)

---

## 🔧 TÂCHES EN COURS

### 🛠️ Claude Code Local — Workflow Scripts (Nouvelle branche)

**Status:** ⏳ P0+P1 doc FAITS, P1 health EN COURS
**Branche:** `feature/claude-code-workflow-scripts`
**Commit:** `5b3c413` (P0+P1 doc livrés)
**Priorité:** P0/P1 (CRITIQUE/IMPORTANT)

**Objectif:**
Créer scripts PowerShell pour actions rapides Claude Code (tests, healthcheck prod, monitoring).

**Progress 2025-10-25 (Claude Code Local):**
- ✅ **P0 FAIT**: `scripts/run-all-tests.ps1`
  - Tests complets (pytest + ruff + mypy + npm build)
  - Parsing résultats intelligent
  - Rapport markdown auto-généré (`reports/all-tests-report.md`)
  - Exit codes clairs (0=OK, 1=FAIL)
  - Gestion virtualenv manquant
- ✅ **P1 Doc FAIT**: `docs/CLAUDE_CODE_WORKFLOW.md`
  - Guide actions rapides pour Claude Code
  - Setup env, commandes pré-commit, vérif prod
  - Scripts par scénario (dev feature, fix bug, audit)
  - Troubleshooting, checklist TL;DR
- ⏳ **P1 Health EN COURS**: `scripts/check-prod-health.ps1` (2-3h estimé)
  - Healthcheck prod avec JWT auth
  - Vérif endpoint `/ready`
  - Métriques Cloud Run (optionnel)
  - Logs récents (optionnel)
  - Rapport markdown

**Prochaines étapes (Claude Code Local):**
1. Implémenter `check-prod-health.ps1` (specs ci-dessous)
2. Tester script (3 cas: nominal, échec, pas JWT)
3. Mettre à jour AGENT_SYNC.md + docs/passation.md
4. Commit + push sur `feature/claude-code-workflow-scripts`
5. PR vers main (review par Claude Web)

**Specs P1 Health Script:**
```powershell
# 1. Lire JWT depuis .env (JWT_SECRET)
# 2. Healthcheck avec auth: GET /ready (Bearer token)
# 3. Vérifier réponse: {"ok":true,"db":"up","vector":"up"}
# 4. Métriques Cloud Run (optionnel): gcloud run services describe
# 5. Logs récents (optionnel): gcloud run logs read --limit=20
# 6. Rapport markdown: reports/prod-health-report.md
# 7. Exit codes: 0=OK, 1=FAIL
```

---

### 🚀 Codex GPT — PWA Mode Hors Ligne (P3.10)

**Status:** ⏳ 80% FAIT, reste tests manuels
**Branche:** `feature/pwa-offline` (pas encore créée - modifs locales)
**Priorité:** P3 (BASSE - Nice-to-have)

**Objectif:**
Implémenter le mode hors ligne (Progressive Web App) pour permettre l'accès aux conversations récentes sans connexion internet.

**Specs (ROADMAP.md:144-153):**
- [x] Créer un manifest PWA (config installable)
- [x] Service Worker cache-first strategy
- [x] Cacher conversations récentes (IndexedDB)
- [x] Indicateur "Mode hors ligne"
- [x] Sync automatique au retour en ligne
- [ ] Tests: offline → conversations dispo → online → sync

**Fichiers créés (2025-10-24 Codex GPT):**
- ✅ `manifest.webmanifest` - Config PWA installable
- ✅ `sw.js` - Service Worker cache-first
- ✅ `src/frontend/features/pwa/offline-storage.js` - IndexedDB (threads/messages + outbox)
- ✅ `src/frontend/features/pwa/sync-manager.js` - Sync auto online/offline
- ✅ `src/frontend/styles/pwa.css` - Badge offline UI
- ✅ Integration dans `main.js` - Registration SW + badge
- ✅ `npm run build` - Build OK

**Progress 2025-10-24 (Codex GPT):**
- ✅ Manifest + SW racine enregistrés depuis `main.js` (badge offline + cache shell)
- ✅ Offline storage IndexedDB (threads/messages + outbox WS)
- ✅ Build frontend OK
- ⏳ Reste à valider : tests offline/online manuels (30 min estimé)

**Prochaines étapes (Codex GPT):**
1. Tester PWA offline/online manuellement:
   - Désactiver réseau navigateur
   - Vérifier badge offline s'affiche
   - Vérifier conversations dispo
   - Réactiver réseau
   - Vérifier sync auto
2. Commit modifs sur branche `feature/pwa-offline`
3. Push branche
4. PR vers main (review par FG)

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
- `main` : Production stable (6 commits ahead origin/main - à pusher)
- `feature/claude-code-workflow-scripts` : Claude Code Local (workflow scripts P0+P1 doc ✅)
- `feature/pwa-offline` : Codex GPT (PWA - pas encore créée, modifs locales)

**Règles de travail:**
1. **Chacun travaille sur SA branche dédiée** (éviter collisions)
2. **Tester localement AVANT push** (npm run build + pytest)
3. **Documenter dans passation.md** après chaque session (max 48h)
4. **Créer PR vers main** quand feature complète
5. **Ne PAS merger sans validation FG**

**Synchronisation:**
- **Claude Code Local**: Workflow scripts PowerShell (tests, healthcheck, monitoring)
- **Codex GPT**: Frontend principalement (PWA offline)
- **Claude Code Web**: Backend, monitoring production, review PR, support
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

**Pour Claude Code Local (urgent - 2-3h):**
1. ⏳ Implémenter `scripts/check-prod-health.ps1` (specs ci-dessus section "Tâches en cours")
2. Tester script (3 cas: nominal, échec, pas JWT)
3. Mettre à jour AGENT_SYNC.md + docs/passation.md
4. Commit + push sur `feature/claude-code-workflow-scripts`
5. Créer PR vers main (review par Claude Web)

**Pour Codex GPT (urgent - 30 min):**
1. ⏳ Tester PWA offline/online manuellement (voir étapes ci-dessus section "Tâches en cours")
2. Commit modifs sur branche `feature/pwa-offline`
3. Push branche
4. Créer PR vers main (review par FG)

**Pour Claude Code Web (attente):**
1. ✅ Sync docs FAIT (AGENT_SYNC.md + passation.md)
2. ✅ Commit + push modifs PWA Codex + docs sync
3. ⏳ Attendre que Local et Codex finissent leurs tâches
4. Review des 2 branches avant merge
5. Monitoring production

**Pour les trois:**
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

**Dernière synchro agents:** 2025-10-25 21:15 CET (Claude Code Web)
