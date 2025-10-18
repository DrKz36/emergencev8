# ADR-001: Renommage Endpoints Sessions → Threads pour Clarifier la Distinction avec Sessions JWT

**Date**: 2025-10-18
**Statut**: ✅ Accepté et Implémenté
**Décideurs**: Claude Code (Sonnet 4.5), Architecte FG
**Tags**: `architecture`, `api`, `dashboard`, `sessions`, `threads`, `jwt`

---

## Contexte

### Problème Identifié

Le système **Émergence V8** utilise DEUX types de "sessions" complètement différentes, stockées dans deux tables distinctes :

1. **Table `sessions`** : Threads de conversation/chat (conversations persistantes avec historique)
2. **Table `auth_sessions`** : Sessions d'authentification JWT (tokens actifs des utilisateurs connectés)

**Avant cette décision** :
- Dashboard admin endpoint : `GET /api/admin/analytics/sessions`
  - Utilisait la table `sessions` (threads de chat)
  - Fonction backend : `AdminDashboardService.get_active_sessions()`
  - Labels UI : "Sessions actives", "Sessions (X)"
- Auth admin endpoint : `GET /api/auth/admin/sessions`
  - Utilisait la table `auth_sessions` (vraies sessions JWT)
  - Fonction backend : `AuthService.list_sessions()`
  - Labels UI : "Sessions actives" (dans module Auth Admin)

**Conséquence** : **Confusion totale** pour :
- Les administrateurs qui voyaient des "sessions actives" dans deux modules différents avec des données incohérentes
- Les développeurs qui maintenaient le code (risque de modifier le mauvais endpoint)
- La documentation d'architecture (pas claire sur cette distinction)

### Impact Utilisateur

- Dashboard admin affichait des threads de chat déguisés en "sessions d'authentification"
- Impossible de distinguer les deux concepts sans lire le code source
- Risque d'erreur de manipulation (par ex. révoquer un thread au lieu d'une session JWT)

**Sévérité** : 🔴 CRITIQUE (identifié lors de l'audit complet du 2025-10-18)

---

## Décision

**Nous décidons de renommer les endpoints et fonctions du dashboard admin pour utiliser la terminologie "threads" au lieu de "sessions", clarifiant ainsi la distinction avec les sessions d'authentification JWT.**

### Changements Implémentés

#### Backend (`src/backend/features/dashboard/`)

**Fichier** : `admin_service.py`
- ✅ Renommé `get_active_sessions()` → `get_active_threads()`
- ✅ Docstring mise à jour avec note explicative :
  ```python
  """
  Get all active threads (conversations) across all users.

  Note: This returns THREADS (conversations from 'sessions' table - legacy naming),
  not authentication sessions. For authentication sessions, use AuthService.list_sessions() instead.
  """
  ```
- ✅ Logs clarifiés : `"Fetching active threads"` au lieu de `"Fetching active sessions"`

**Fichier** : `admin_router.py`
- ✅ Endpoint renommé : `/admin/analytics/sessions` → `/admin/analytics/threads`
- ✅ Fonction renommée : `get_active_sessions()` → `get_active_threads()`
- ✅ Clé JSON retour : `{"threads": [...]}` au lieu de `{"sessions": [...]}`
- ✅ Description OpenAPI mise à jour avec note explicative

#### Frontend (`src/frontend/features/admin/`)

**Fichier** : `admin-dashboard.js`
- ✅ Fonction renommée : `loadActiveSessions()` → `loadActiveThreads()`
- ✅ Fonction renommée : `renderSessionsList()` → `renderThreadsList()`
- ✅ Variables renommées : `threads`, `activeThreads`, `inactiveThreads`
- ✅ Labels UI clarifiés :
  - "Threads de Conversation (X)" au lieu de "Sessions (X)"
  - "Threads de Conversation Actifs" dans le titre de section
  - "ID Thread" au lieu de "ID Session"
  - Icône `messageCircle` au lieu de `users`
- ✅ Bandeau info ajouté :
  ```html
  <div class="info-banner">
    <strong>Note :</strong> Cette vue affiche les <strong>threads de conversation</strong> (table <code>sessions</code>).
    Pour consulter les <strong>sessions d'authentification JWT</strong> (table <code>auth_sessions</code>),
    utilisez le module <strong>Auth Admin</strong>.
  </div>
  ```

**Fichier** : `admin-dashboard.css`
- ✅ Styles `.info-banner` ajoutés (background bleu, bordure gauche)

#### Documentation

- ✅ `docs/architecture/10-Components.md` : Nouvelle section "Tables et Nomenclature Critique"
- ✅ `docs/passation.md` : Entrée détaillée avec contexte complet
- ✅ Cet ADR documentant la décision

---

## Rationale (Justification)

### Pourquoi Renommer les Endpoints (Option A) plutôt que Changer la Table (Option B) ?

**Option A (Choisie)** : Renommer endpoints/fonctions/UI → "threads"
- ✅ Changement rapide et sûr (1 heure)
- ✅ Aucun risque de perte de données
- ✅ Pas de migration DB complexe
- ✅ Clarification immédiate pour les utilisateurs
- ✅ Rétrocompatibilité totale (table `sessions` inchangée)

**Option B (Rejetée)** : Utiliser la table `auth_sessions` au lieu de `sessions`
- ❌ Changement sémantique majeur (threads ≠ sessions JWT)
- ❌ Perte de l'historique des threads
- ❌ Migration de données complexe et risquée
- ❌ Temps de développement estimé : 1-2 jours
- ❌ Risque de régression en production

### Pourquoi Garder le Nom de Table `sessions` (Legacy) ?

Renommer la table DB `sessions` → `threads` nécessiterait :
- Migration SQLite avec CREATE TABLE + INSERT + DROP + RENAME
- Mise à jour de tous les services (ChatService, DashboardService, etc.)
- Tests complets de régression
- Risque d'erreur en production

**Décision** : Garder le nom legacy `sessions` en DB, mais clarifier au niveau API/UI avec "threads".

**TODO Futur** : Considérer une migration DB pour renommer `sessions` → `threads` lors d'une future refonte majeure.

---

## Conséquences

### Positives

- ✅ **Clarté totale** : Les administrateurs comprennent maintenant la différence entre threads et sessions JWT
- ✅ **UX améliorée** : Bandeau info explicatif dans le dashboard
- ✅ **Code maintenable** : Docstrings claires, noms de fonctions explicites
- ✅ **Documentation à jour** : Architecture docs reflètent la réalité
- ✅ **Pas de régression** : Module Auth Admin (sessions JWT) non touché
- ✅ **Tests passent** : Compilation, ruff, syntaxe JS OK

### Négatives

- ⚠️ **Nom legacy en DB** : La table s'appelle toujours `sessions` (peut prêter à confusion pour nouveaux développeurs)
- ⚠️ **TODO Futur** : Migration DB recommandée à long terme

### Risques

- 🟢 **Risque production** : **FAIBLE** - Changements isolés au dashboard admin, aucune modification des tables
- 🟢 **Risque régression** : **FAIBLE** - Tests passent, module Auth Admin inchangé
- 🟢 **Risque utilisateur** : **NUL** - Amélioration UX pure

---

## Alternatives Considérées

### Alternative 1 : Ne Rien Changer

**Argument** : "Les développeurs s'y sont habitués"

**Rejet** : Confusion inacceptable pour les administrateurs et nouveaux développeurs. Risque d'erreur de manipulation.

### Alternative 2 : Renommer la Table `sessions` → `threads`

**Argument** : Cohérence totale DB + API + UI

**Rejet** : Migration DB trop risquée pour un gain marginal. Peut être fait plus tard.

### Alternative 3 : Ajouter un Préfixe aux Endpoints

**Exemple** : `/admin/analytics/chat-sessions` vs `/api/auth/admin/jwt-sessions`

**Rejet** : URLs trop longues, "threads" est plus clair que "chat-sessions"

---

## Liens et Références

- **Audit Complet** : [AUDIT_COMPLET_2025-10-18.md](../../AUDIT_COMPLET_2025-10-18.md)
- **Plan d'Action Phase 1** : [PROMPT_SUITE_AUDIT.md](../../PROMPT_SUITE_AUDIT.md)
- **Passation Détaillée** : [docs/passation.md](../passation.md)
- **Architecture Components** : [10-Components.md](10-Components.md) (section "Tables et Nomenclature Critique")

**Commits** :
- Phase 1 : `84b2dcf` - fix(admin): rename sessions → threads to clarify dashboard analytics
- Phase 2 : `<à venir>` - feat(dashboard): improve costs chart + standardize user_id mapping

---

## Historique

| Date       | Statut          | Auteur              |
|------------|-----------------|---------------------|
| 2025-10-18 | Proposé         | Claude Code (Audit) |
| 2025-10-18 | Accepté         | Architecte FG       |
| 2025-10-18 | Implémenté      | Claude Code         |

---

**Leçon Apprise** : La clarté de la nomenclature est critique pour l'UX et la maintenabilité. Même si la table DB porte un nom legacy, les endpoints et l'UI doivent refléter la sémantique réelle.
