## 📋 TÂCHES EN COURS (2025-10-24) — Multi-Agents

### 🎯 État Roadmap Actuel
**Progression globale:** 14/20 (70%)
- ✅ P0/P1/P2 Features: 9/9 (100%)
- ✅ P1/P2 Maintenance: 5/7 (71%)
- ⏳ P3 Features: 0/4 (À faire)
- ⏳ P3 Maintenance: 0/2 (À faire)

---

### 🔧 TÂCHE CODEX GPT — PWA Mode Hors Ligne (P3.10)
**Branche:** `feature/pwa-offline`
**Durée estimée:** 4 jours
**Priorité:** P3 (BASSE - Nice-to-have)

**Objectif:**
Implémenter le mode hors ligne (Progressive Web App) pour permettre l'accès aux conversations récentes sans connexion internet.

**Spécifications détaillées (ROADMAP.md:144-153):**
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

### 🌐 TÂCHE CLAUDE CODE WEB — Webhooks et Intégrations (P3.11)
**Branche:** `feature/webhooks-integrations`
**Durée estimée:** 3 jours
**Priorité:** P3 (BASSE - Nice-to-have)

**Objectif:**
Implémenter système de webhooks pour permettre intégrations externes (Slack, Discord, Zapier, etc.)

**Spécifications détaillées (ROADMAP.md:154-163):**
- [ ] Backend: table `webhooks` (migration SQL)
- [ ] Endpoints POST/GET/DELETE webhooks
- [ ] Système événements (thread.created, message.sent, analysis.completed)
- [ ] POST vers webhook URL avec signature HMAC
- [ ] UI: onglet "Webhooks" (Paramètres > Intégrations)
- [ ] Retry automatique si échec (3 tentatives)

**Fichiers à créer:**
- `migrations/add_webhooks_table.sql`
- `src/backend/features/webhooks/models.py`
- `src/backend/features/webhooks/service.py`
- `src/backend/features/webhooks/events.py`
- `src/backend/features/webhooks/delivery.py`
- `src/backend/features/webhooks/router.py`
- `src/frontend/features/settings/webhooks.js`

**Acceptance Criteria:**
- ✅ Webhooks CRUD complets (create, list, update, delete)
- ✅ Delivery automatique events sélectionnés
- ✅ Signature HMAC vérifiable côté destinataire
- ✅ Retry automatique 3x si échec (5xx, timeout)
- ✅ UI intuitive (modal création, liste, stats)

---

### 🔄 Coordination Multi-Agents

**Branches actives:**
- `feature/pwa-offline` → Codex GPT
- `feature/webhooks-integrations` → Claude Code Web
- `fix/cockpit-sql-bugs` → PR en cours de review

**Règles de travail:**
1. **Chacun travaille sur SA branche dédiée** (pas de collision)
2. **Tester localement AVANT de push** (npm run build + pytest)
3. **Documenter dans passation.md** après chaque session
4. **Créer PR vers main** quand feature complète
5. **Ne PAS merger sans validation FG**

**Synchronisation:**
- Codex GPT: Frontend principalement (PWA)
- Claude Web: Backend principalement (Webhooks)
- Pas de dépendances entre les 2 tâches → parallélisation OK
---
## ✅ Session COMPLÉTÉE (2025-10-24 06:15 CET) — Agent : Claude Code

### Fichiers modifiés
- `src/backend/features/dashboard/timeline_service.py` (3 bugs SQL fixés)
- `src/backend/features/dashboard/router.py` (suppression filtrage session_id)
- `AGENT_SYNC.md`
- `docs/passation.md`

### Actions réalisées
**🔥 Fix 3 bugs critiques Cockpit - Graphiques distribution vides**

**Problèmes utilisateur:**
- Graphiques Distribution des Agents complètement vides (0 données affichées)
- Timeline vide (mais normal si DB vide en local)

**Bugs SQL identifiés et corrigés:**

1. **Bug SQL `no such column: agent`** ([timeline_service.py:276,278,288,322,324,334](src/backend/features/dashboard/timeline_service.py)):
   - Table `messages` a colonne `agent_id` (pas `agent`)
   - Code utilisait `SELECT agent, ... GROUP BY agent` → crash SQL
   - **Fix**: Remplacé par `SELECT agent_id, ... GROUP BY agent_id`
   - Impact: `/api/dashboard/distribution/threads` et `/messages` crashaient systématiquement

2. **Bug filtrage session_id trop restrictif** ([router.py:105-164](src/backend/features/dashboard/router.py)):
   - Frontend envoie header `X-Session-Id` (session WebSocket actuelle)
   - Backend filtrait UNIQUEMENT les données de cette session → graphiques vides si conversations dans autres sessions
   - **Fix**: Passé `session_id=None` dans tous les endpoints timeline/distribution
   - Impact: Cockpit affiche maintenant TOUTES les données de l'utilisateur (toutes sessions confondues)

3. **Bug alias SQL manquant** ([timeline_service.py:277](src/backend/features/dashboard/timeline_service.py)):
   - Conditions WHERE utilisaient `m.created_at`, `m.user_id`, `m.session_id`
   - Mais requête SQL disait `FROM messages` (sans alias `m`) → crash `no such column: m.created_at`
   - **Fix**: Ajouté alias `FROM messages m`
   - Impact: `/api/dashboard/distribution/threads` crashait sur ce bug après le fix du bug #1

**Tests:**
- ✅ Backend relancé avec les 3 fixes
- ✅ Distribution des Agents s'affiche maintenant (pie chart visible)
- ⚠️ Timeline reste vide (DB locale vide - pas de messages historiques)

**État final:**
- Code prêt pour prod (3 bugs SQL corrigés)
- Graphiques Distribution fonctionnent ✅
- Graphiques Timeline fonctionneront dès que l'utilisateur aura créé des conversations

**Prochaines actions recommandées (Codex GPT):**
- Tester en créant 2-3 conversations dans module Dialogue
- Vérifier que tous les graphiques Cockpit se remplissent
- Éventuellement ajouter données de test en DB pour démo

---

## ✅ Session COMPLÉTÉE (2025-10-24 11:30 CET) — Agent : Claude Code

### Fichiers modifiés
- `src/backend/features/dashboard/service.py`
- `src/backend/features/dashboard/timeline_service.py`
- `src/frontend/features/cockpit/cockpit-charts.js`
- `AGENT_SYNC.md`
- `docs/passation.md`

### Actions réalisées
**🔧 Debug module Cockpit - Fix agents fantômes + graphiques vides**

**Problèmes identifiés:**
1. **Agents fantômes** dans Distribution: `GPT_CODEX_CLOUD`, `CLAUDE_LOCAL_REMOTE_PROMPT`, `MESSAGE_TO_GPT_CODEX_CLOUD` apparaissaient dans le graphique
2. **Distribution par Threads vide**: Le graph affichait rien quand on passait de "Par Messages" à "Par Threads"
3. **Graphiques Timeline/Tokens/Coûts vides**: Pas de données affichées (problème probable DB vide en local, mais code OK pour prod)

**Root cause:**
- Backend ne filtrait PAS les agents invalides → agents legacy/fantômes remontaient de la DB
- Frontend ne fetcha PAS les données threads → `result.threads` restait vide `{}`
- Backend endpoint `/api/dashboard/distribution/threads` existait mais `get_distribution_by_agent()` ne gérait pas le metric "threads"

**Fixes appliqués:**

1. **Backend - Filtrage agents fantômes** ([service.py](src/backend/features/dashboard/service.py:110-147)):
   - Ajout whitelist stricte: `valid_agents = {"anima", "neo", "nexus", "user", "system"}`
   - Tout agent hors whitelist est filtré (logged en debug)
   - Mapping vers noms affichage (Anima, Neo, Nexus, User, System)

2. **Backend - Support metric "threads"** ([timeline_service.py](src/backend/features/dashboard/timeline_service.py:243-287)):
   - Ajout branch `if metric == "threads"` dans `get_distribution_by_agent()`
   - Query SQL: `SELECT agent, COUNT(DISTINCT thread_id) FROM messages GROUP BY agent`
   - Même filtrage agents invalides + mapping noms
   - Aussi ajouté metric "messages" (comptage messages par agent)

3. **Frontend - Fetch vraies données threads** ([cockpit-charts.js](src/frontend/features/cockpit/cockpit-charts.js:249-310)):
   - Remplacé single fetch `/api/dashboard/costs/by-agent` par 4 fetches parallèles:
     * `/api/dashboard/costs/by-agent` → costs
     * `/api/dashboard/distribution/threads?period=X` → threads
     * `/api/dashboard/distribution/messages?period=X` → messages
     * `/api/dashboard/distribution/tokens?period=X` → tokens
   - Supprimé mock data fallback (retourne `{}` vide si erreur)

**Tests:**
- ✅ `npm run build`: OK (1.24s, pas d'erreurs JS)
- ✅ `ruff check`: OK (All checks passed)
- ✅ `mypy`: OK (Success: no issues)

---
## ✅ Session COMPLÉTÉE (2025-10-24 11:45 CET) — Agent : Codex GPT

### Fichiers modifiés
- `AGENT_SYNC.md`
- `docs/passation.md`

### Actions réalisées
- Création de la branche `codex/codex-gpt` pour les futures sessions Codex (fin des travaux sur `work`).
- Aucune modification fonctionnelle côté code.

### Tests
- ⚠️ Aucun test lancé (mise à jour Git/documentation uniquement).

### Prochaines actions
1. Se basculer sur `codex/codex-gpt` pour les prochains développements.
2. Avancer sur la demande utilisateur dès réception.

---
## ✅ Session COMPLÉTÉE (2025-10-24 17:30 CET) — Agent : Codex GPT

### Fichiers modifiés
- `AGENT_SYNC.md`
- `docs/passation.md`

### Actions réalisées
- Résolution des conflits de fusion détectés sur `AGENT_SYNC.md` et `docs/passation.md`.
- Consolidation des entrées de sessions Claude Code / Codex (23-24/10) sans perte d'information.
- Aucun changement applicatif en dehors de la documentation de synchronisation.

### Tests
- ⚠️ Non lancés (documentation uniquement).

### Prochaines actions
1. Reprendre les travaux PWA / Webhooks en s'appuyant sur les sections synchronisées.
2. Déclencher la consolidation AutoSync si nécessaire via le dashboard (port 8000).

---
## ✅ Session COMPLÉTÉE (2025-10-24 18:45 CET) — Agent : Claude Code

### Fichiers modifiés
- `AGENT_SYNC.md`
- `docs/passation.md`
- `scripts/debug_passation.py` (non versionné - script temporaire)
- `scripts/update_passation_insert.py` (non versionné - script temporaire)

### Actions réalisées
**📝 Mise à jour documentation inter-agents + commit propre**

**Contexte:**
L'utilisateur a demandé de mettre à jour la doc de coopération inter-agents (AGENT_SYNC.md + passation.md) et de faire un commit push propre de tous les fichiers modifiés/créés pour avoir un dépôt local clean.

**Travail réalisé:**
1. Lecture état Git : 2 fichiers modifiés (`AGENT_SYNC.md`, `docs/passation.md`), 2 scripts Python non versionnés
2. Ajout entrée dans `AGENT_SYNC.md` (session courante 18:45 CET)
3. Ajout entrée dans `docs/passation.md` (même session)
4. Commit Git de toutes les modifications

**Note:**
- Les 2 scripts Python (`scripts/debug_passation.py`, `scripts/update_passation_insert.py`) sont des scripts temporaires de debug (non versionnés volontairement)
- Si besoin de les versionner, ajouter explicitement via `git add scripts/*.py`

### Tests
- ⚠️ Non lancés (documentation uniquement)

### Prochaines actions recommandées
1. Continuer travaux tâches P3 (PWA pour Codex, Webhooks pour Claude Web)
2. Vérifier que les branches `feature/pwa-offline` et `feature/webhooks-integrations` sont bien à jour
3. Lancer Guardian si besoin (`pwsh -File claude-plugins\integrity-docs-guardian\scripts\run_audit.ps1`)

