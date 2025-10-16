# Agent Sync — État de synchronisation inter-agents

**Objectif** : Éviter que Claude Code, Codex (local) et Codex (cloud) se marchent sur les pieds.

**Dernière mise à jour** : 2025-10-16 12:50 (Orchestrateur: audit complet système multi-agents)

**🔄 SYNCHRONISATION AUTOMATIQUE ACTIVÉE** : Ce fichier est maintenant surveillé et mis à jour automatiquement par le système AutoSyncService

---

## 🔥 Lecture OBLIGATOIRE avant toute session de code

**Ordre de lecture pour tous les agents :**
1. Ce fichier (`AGENT_SYNC.md`) — état actuel du dépôt
2. [`AGENTS.md`](AGENTS.md) — consignes générales
3. [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md) — protocole multi-agents
4. [`docs/passation.md`](docs/passation.md) — 3 dernières entrées minimum
5. `git status` + `git log --oneline -10` — état Git

---

## 📍 État actuel du dépôt (2025-10-16)

### Branche active
- **Branche courante** : `main`
- **Derniers commits** (5 plus récents) :
  - `46ec599` feat(auth): bootstrap allowlist seeding
  - `fe9fa85` test(backend): Add Phase 1 validation tests and update documentation
  - `eb0afb1` docs(agents): Add Codex GPT guide and update inter-agent cooperation docs
  - `102e01e` fix(backend): Phase 1 - Critical backend fixes for empty charts and admin dashboard
  - `dc1781f` docs(debug): Add comprehensive debug plan for Cockpit, Memory, Admin, and About modules

### Working tree
- **Statut** : ⚠️ Modifications en cours (auto-activation conversations + cleanup divers)
- **Fichiers modifiés** : 8 fichiers
- **Fichiers à commiter** : Tous les changements en attente (auto-activation + scripts auto-sync)

### Remotes configurés
- `origin` → HTTPS : `https://github.com/DrKz36/emergencev8.git`
- `codex` → SSH : `git@github.com:DrKz36/emergencev8.git`

---

## 🚀 Déploiement Cloud Run - État Actuel (2025-10-16)

### ✅ PRODUCTION STABLE ET OPÉRATIONNELLE

**Statut** : ✅ **Révision 00458-fiy en production (100% trafic) - Anti-DB-Lock Fix**

#### Infrastructure
- **Projet GCP** : `emergence-469005`
- **Région** : `europe-west1`
- **Service** : `emergence-app` (conteneur unique, pas de canary)
- **Registry** : `europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app`

#### URLs de Production
| Service | URL | Statut |
|---------|-----|--------|
| **Application principale** | https://emergence-app.ch | ✅ Opérationnel |
| **URL directe Cloud Run** | https://emergence-app-47nct44nma-ew.a.run.app | ✅ Opérationnel |
| **Health Check** | https://emergence-app.ch/api/health | ✅ 200 OK |

#### Révision Active (2025-10-16 17:10)
- **Révision** : `emergence-app-00458-fiy` (tag `anti-db-lock`, alias `stable`)
- **Image** : `europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:anti-db-lock-20251016-170500`
  (`sha256:28d7752ed434d2fa4c5d5574a9cdcedf3dff6f948b5c717729053977963e0550`)
- **Trafic** : 100% (canary 10% → 100% - tests validés)
- **Version** : beta-2.1.2 (Anti-DB-Lock Fix - Correctif critique auth)
- **CPU** : 2 cores
- **Mémoire** : 4 Gi
- **Min instances** : 1
- **Max instances** : 10
- **Timeout** : 300s

#### Déploiements Récents (Session 2025-10-16)

**🆕 Déploiement Anti-DB-Lock (2025-10-16 17:10)** :
- **Révision** : emergence-app-00458-fiy
- **Tag** : anti-db-lock-20251016-170500
- **Build** : Docker local → GCR → Cloud Run
- **Tests** : ✅ Health check OK, ✅ Aucune erreur "database is locked", ✅ Logs propres
- **Déploiement** : Canary 10% → 100% (validation progressive)
- **Contenu** : Correctif définitif erreurs 500 "database is locked" sur auth

**Déploiement beta-2.1.1 (2025-10-16 12:38)** :
- **Révision** : emergence-app-00455-cew
- **Tag** : 20251016-123422
- **Build** : Docker local → GCR → Cloud Run
- **Tests** : ✅ Health check OK, ✅ Fichiers statiques OK, ✅ Logs propres
- **Déploiement** : Canary 10% → 100% (validation rapide)
- **Contenu** : Audit agents + versioning unifié + Phase 1 & 3 debug

#### Problèmes Résolus (Session 2025-10-16)

**🆕 6. ✅ Erreurs 500 "database is locked" sur /api/auth/login (CRITIQUE)**
- **Problème** : Timeout 25.7s + erreur 500 après 3-5 connexions/déconnexions rapides
- **Cause** : Contention SQLite sur écritures concurrentes (auth_sessions + audit_log)
- **Correctif 4 niveaux** :
  1. **SQLite optimisé** : busy_timeout 60s, cache 128MB, WAL autocheckpoint 500 pages
  2. **Write mutex global** : Nouvelle méthode `execute_critical_write()` avec `asyncio.Lock()`
  3. **Audit asynchrone** : Écriture logs non-bloquante (réduit latence ~50-100ms)
  4. **Auth sessions sérialisées** : INSERT auth_sessions via mutex pour éliminer race conditions
- **Fichiers modifiés** :
  - [src/backend/core/database/manager.py](src/backend/core/database/manager.py) (V23.3-locked)
  - [src/backend/features/auth/service.py:544-573,1216-1265](src/backend/features/auth/service.py)
- **Tests** : ✅ 0 erreurs "database is locked" post-déploiement (10+ min surveillance)
- **Impact** : Connexions concurrentes multiples maintenant supportées sans blocage

#### Problèmes Résolus (Sessions précédentes 2025-10-16)

**1. ✅ Configuration Email SMTP**
- Variables SMTP ajoutées dans `stable-service.yaml`
- Secret SMTP_PASSWORD configuré via Google Secret Manager
- Test réussi : Email de réinitialisation envoyé avec succès

**2. ✅ Variables d'Environnement Manquantes**
- Toutes les API keys configurées (OPENAI, GEMINI, ANTHROPIC, ELEVENLABS)
- Configuration OAuth complète (CLIENT_ID, CLIENT_SECRET)
- Configuration des agents IA (ANIMA, NEO, NEXUS)

**3. ✅ Erreurs 500 sur les Fichiers Statiques**
- Liveness probe corrigé : `/health/liveness` → `/api/health`
- Tous les fichiers statiques retournent maintenant 200 OK

**4. ✅ Module Papaparse Manquant**
- Import map étendu dans `index.html` :
  - papaparse@5.4.1
  - jspdf@2.5.2
  - jspdf-autotable@3.8.3
- Module chat se charge maintenant sans erreurs

**5. ✅ Seed allowlist automatisé + nouvelle révision**
- Script `scripts/generate_allowlist_seed.py` ajouté pour exporter/publier le JSON allowlist.
- `AuthService.bootstrap` consomme `AUTH_ALLOWLIST_SEED` / `_PATH` pour reconstruire l'allowlist à chaque boot.
- Déploiement `20251016-110758` achevé (canary progressif validé, 100% trafic).

#### Configuration Complète

**Variables d'environnement configurées (93 variables)** :
- **Système** : GOOGLE_CLOUD_PROJECT, AUTH_DEV_MODE=0, SESSION_INACTIVITY_TIMEOUT_MINUTES=30
- **Email/SMTP** : EMAIL_ENABLED=1, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (secret)
- **API Keys** : OPENAI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, ELEVENLABS_API_KEY (tous via Secret Manager)
- **OAuth** : GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET (secrets)
- **AI Agents** : ANIMA (openai/gpt-4o-mini), NEO (google/gemini-1.5-flash), NEXUS (anthropic/claude-3-haiku)
- **Telemetry** : ANONYMIZED_TELEMETRY=False, CHROMA_DISABLE_TELEMETRY=1
- **Cache** : RAG_CACHE_ENABLED=true, RAG_CACHE_TTL_SECONDS=300

**Secrets configurés dans Secret Manager** :
- ✅ SMTP_PASSWORD (version 3)
- ✅ OPENAI_API_KEY
- ✅ GEMINI_API_KEY
- ✅ ANTHROPIC_API_KEY
- ✅ GOOGLE_OAUTH_CLIENT_ID
- ✅ GOOGLE_OAUTH_CLIENT_SECRET

#### Procédure de Déploiement

**🆕 PROCÉDURE RECOMMANDÉE : Déploiement Canary (2025-10-16)**

Pour éviter les rollbacks hasardeux, utiliser le **déploiement progressif canary** :

```bash
# Script automatisé (recommandé)
pwsh -File scripts/deploy-canary.ps1

# Ou manuel avec phases progressives (voir CANARY_DEPLOYMENT.md)
```

**Étapes du déploiement canary** :
1. Build + Push image Docker (avec tag timestamp)
2. Déploiement avec `--no-traffic` (0% initial)
3. Tests de validation sur URL canary
4. Routage progressif : 10% → 25% → 50% → 100%
5. Surveillance continue à chaque phase

**Documentation complète** : [CANARY_DEPLOYMENT.md](CANARY_DEPLOYMENT.md)

**Ancienne méthode (déconseillée)** :
```bash
# Build et push
docker build -t europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest .
docker push europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest

# Déploiement direct (risqué - préférer canary)
gcloud run services replace stable-service.yaml \
  --region=europe-west1 \
  --project=emergence-469005
```

**Vérification** :
```bash
# 1. Health check
curl https://emergence-app.ch/api/health

# 2. Fichiers statiques
curl -I https://emergence-app.ch/src/frontend/main.js

# 3. Logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app" \
  --project=emergence-469005 --limit=10 --freshness=5m
```

#### Monitoring et Logs

**Commandes utiles** :
```bash
# Logs en temps réel
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app" \
  --project=emergence-469005

# Métriques du service
gcloud run services describe emergence-app \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.conditions)"

# État des révisions
gcloud run revisions list \
  --service=emergence-app \
  --region=europe-west1 \
  --project=emergence-469005
```

#### Documentation
- 🆕 [CANARY_DEPLOYMENT.md](CANARY_DEPLOYMENT.md) - **Procédure officielle de déploiement canary** (2025-10-16)
- 🔧 [scripts/deploy-canary.ps1](scripts/deploy-canary.ps1) - Script automatisé de déploiement canary
- ✅ [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - Rapport complet de déploiement
- ✅ [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md) - Guide de résolution
- ✅ [stable-service.yaml](stable-service.yaml) - Configuration Cloud Run

---

## 📊 Roadmap & Progression (2025-10-16)

### ✅ PHASE P0 - QUICK WINS - **COMPLÉTÉE** (3/3)
- ✅ P0.1 - Archivage des Conversations (UI) - Complété 2025-10-15
- ✅ P0.2 - Graphe de Connaissances Interactif - Complété 2025-10-15
- ✅ P0.3 - Export Conversations (CSV/PDF) - Complété 2025-10-15

### ✅ PHASE P1 - UX ESSENTIELLE - **COMPLÉTÉE** (3/3)
- ✅ P1.1 - Hints Proactifs (UI) - Complété 2025-10-16
- ✅ P1.2 - Thème Clair/Sombre - Complété 2025-10-16
- ✅ P1.3 - Gestion Avancée des Concepts - Complété 2025-10-16

### 📊 Métriques Globales
```
Progression Totale : [████████░░] 14/23 (61%)

✅ Complètes    : 14/23 (61%)
🟡 En cours     : 0/23 (0%)
⏳ À faire      : 9/23 (39%)
```

### 🎯 PROCHAINE PHASE : P2 - ADMINISTRATION & SÉCURITÉ
**Statut** : ⏳ À démarrer
**Estimation** : 4-6 jours
**Fonctionnalités** :
- P2.1 - Dashboard Administrateur Avancé
- P2.2 - Gestion Multi-Sessions
- P2.3 - Authentification 2FA (TOTP)

### Documentation Roadmap
- 📋 [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) - Document unique et officiel
- 📊 [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) - Suivi quotidien de progression
- 📜 [CHANGELOG.md](CHANGELOG.md) - Historique des versions

---

## 🔧 Système de Versioning

**Version actuelle** : `beta-2.1.1` (Phase P1 + Debug & Audit)

**Format** : `beta-X.Y.Z`
- **X (Major)** : Phases complètes (P0→1, P1→2, P2→3, P3→4)
- **Y (Minor)** : Nouvelles fonctionnalités individuelles
- **Z (Patch)** : Corrections de bugs / Améliorations mineures

**Roadmap des Versions** :
- ✅ `beta-1.0.0` : État initial du projet (2025-10-15)
- ✅ `beta-1.1.0` : P0.1 - Archivage conversations (2025-10-15)
- ✅ `beta-1.2.0` : P0.2 - Graphe de connaissances (2025-10-15)
- ✅ `beta-1.3.0` : P0.3 - Export CSV/PDF (2025-10-15)
- ✅ `beta-2.0.0` : Phase P1 complète (2025-10-16)
- ✅ `beta-2.1.0` : Phase 1 & 3 Debug (Backend + UI/UX)
- ✅ `beta-2.1.1` : Audit système agents + versioning unifié (2025-10-16)
- 🔜 `beta-3.0.0` : Phase P2 complète (TBD)
- ⏳ `beta-4.0.0` : Phase P3 complète (TBD)
- 🎯 `v1.0.0` : Release Production Officielle (TBD)

---

## 🔍 Audit Système Multi-Agents (2025-10-16 12:45)

### ✅ Résultat Global: OK (avec améliorations mineures recommandées)

**Statut agents** : 3/5 actifs, 6/6 scripts opérationnels, 6/6 commandes slash disponibles

**Agents actifs (rapport < 24h)** :
- ✅ **Anima (DocKeeper)** : Dernier rapport 2025-10-16T12:07 (< 1h) - 0 gap documentaire
- ✅ **Neo (IntegrityWatcher)** : Dernier rapport 2025-10-16T12:07 (< 1h) - 0 issue détectée, 15 endpoints validés
- ✅ **Nexus (Coordinator)** : Dernier rapport 2025-10-16T12:07 (< 1h) - "All checks passed"

**Agents semi-actifs** :
- 🟡 **Orchestrateur** : Dernier rapport 2025-10-15T17:27 (19h) - 5 agents exécutés, 0 erreur

**Agents inactifs** :
- ⚠️ **ProdGuardian** : Dernier rapport 2025-10-10T09:17 (6 jours - OBSOLÈTE) - Nécessite réexécution

**Incohérences détectées** :
1. [MOYENNE] ProdGuardian rapport obsolète (6 jours) - Perte de visibilité sur production
2. [BASSE] Orchestrateur statuts "UNKNOWN" dans rapport global
3. [BASSE] Warnings vides dans prod_report.json

**Actions prioritaires** :
1. 🔴 **HAUTE** : Exécuter `/check_prod` pour surveillance Cloud Run
2. 🟡 **MOYENNE** : Automatiser exécution quotidienne via GitHub Actions
3. 🟢 **BASSE** : Améliorer qualité rapports (filtrer warnings vides, statuts déterministes)

**Rapport complet d'audit** : Généré 2025-10-16 12:45 par Orchestrateur (Claude Code Sonnet 4.5)

---

## 🚧 Zones de Travail en Cours

### ✅ Session 2025-10-16 (Soir) - Auto-activation Conversations Module Dialogue (TERMINÉE)

**Statut** : ✅ **FONCTIONNALITÉ IMPLÉMENTÉE ET DOCUMENTÉE**
**Agent** : Claude Code (Sonnet 4.5)
**Durée** : 1 heure

**Problème résolu** :
- Utilisateurs arrivaient sur module Dialogue sans conversation active
- Agents ne répondaient pas → nécessitait reload ou activation manuelle

**Solution implémentée** :
- ✅ Nouvelle méthode `_ensureActiveConversation()` dans ChatModule
- ✅ Stratégie 1 : Récupère dernière conversation depuis `threads.order`
- ✅ Stratégie 2 : Crée nouvelle conversation si aucune n'existe
- ✅ Activation complète : Hydratation + State + Events + WebSocket

**Fichiers modifiés** :
- Frontend (1) : `src/frontend/features/chat/chat.js` (lignes 267-359)
- Documentation (2) : `docs/passation.md`, `AGENT_SYNC.md`

**Résultat** :
- ✅ Conversation active automatiquement au chargement module Dialogue
- ✅ Agents répondent immédiatement sans action utilisateur
- ✅ Fallback robuste (gère erreurs API et listes vides)

---

### ✅ Session 2025-10-16 (Après-midi) - Debug Phases 1 & 3 (TERMINÉE)

**Statut** : ✅ **PHASES 1 & 3 COMPLÉTÉES ET VALIDÉES**
**Agent** : Claude Code (Sonnet 4.5)
**Durée** : Phase 3 (1 jour) + Phase 1 (déjà complétée)

**Objectifs** :
- Phase 1 : Corriger problèmes backend critiques (graphiques vides, admin dashboard)
- Phase 3 : Standardiser système de boutons et améliorer UX

**Résultats** :
- ✅ **16/16 tests automatisés passés** (5 backend + 11 frontend)
- ✅ **9 fichiers modifiés** (2 backend, 6 frontend, 1 nouveau)
- ✅ **Build réussi** : 3.82s, aucune erreur

**Phase 1 - Backend Fixes (déjà complétée)** :
- ✅ Timeline endpoints : Ajout `COALESCE(timestamp, created_at, 'now')` partout
- ✅ Admin users breakdown : `INNER JOIN` → `LEFT JOIN`
- ✅ Admin date metrics : Gestion NULL timestamps + fallback 7 jours
- ✅ Endpoint `/api/admin/costs/detailed` : Nouveau endpoint créé
- **Tests** : 5/5 passés (`test_phase1_validation.py`)

**Phase 3 - UI/UX Improvements (nouvelle)** :
- ✅ **Design System Unifié** : `button-system.css` créé (374 lignes)
  - 6 variantes (.btn--primary, --secondary, --metal, --ghost, --danger, --success)
  - 3 tailles (.btn--sm, --md, --lg)
  - 3+ états (active, disabled, loading)
  - 28 variables CSS utilisées
- ✅ **Migration Memory** : Boutons "Historique" et "Graphe" vers `.btn .btn--secondary`
- ✅ **Migration Graph** : Boutons "Vue" et "Recharger" vers `.btn .btn--ghost`
- ✅ **Sticky Header** : Module "À propos" avec `position: sticky` + glassmorphism
- **Tests** : 11/11 passés (`test_phase3_validation.py`)

**Fichiers impactés** :
- Backend (2) : `timeline_service.py`, `admin_service.py`
- Frontend (6) : `button-system.css` (new), `main-styles.css`, `memory.css`, `memory-center.js`, `concept-graph.css`, `concept-graph.js`
- Tests (2) : `test_phase1_validation.py` (existant), `test_phase3_validation.py` (new)
- Documentation (1) : `docs/PHASE_1_3_COMPLETION_REPORT.md` (new, 600+ lignes)

**Documentation** :
- 📋 [docs/PHASE_1_3_COMPLETION_REPORT.md](docs/PHASE_1_3_COMPLETION_REPORT.md) - **Rapport complet de complétion**
- 📋 [docs/DEBUG_PHASE1_STATUS.md](docs/DEBUG_PHASE1_STATUS.md) - État Phase 1
- 📋 [PLAN_DEBUG_COMPLET.md](PLAN_DEBUG_COMPLET.md) - Plan global (référence)
- 🧪 [test_phase1_validation.py](test_phase1_validation.py) - Tests backend automatisés
- 🧪 [test_phase3_validation.py](test_phase3_validation.py) - Tests frontend automatisés

**Prochaines étapes** :
1. ⏳ Commit Phase 1 + 3 ensemble
2. ⏳ Phase 2 (Frontend fixes) - Filtrage agents dev, couleurs NEO/NEXUS
3. ⏳ Phase 4 (Documentation & Tests E2E)

---

## 🧑‍💻 Codex - Journal 2025-10-16

- **Horodatage** : 20:45 CET
- **Objectif** : Audit UI mobile portrait + verrouillage paysage (authentification).
- **Fichiers impactés** : `index.html`, `src/frontend/styles/core/_layout.css`, `src/frontend/styles/core/_responsive.css`, `src/frontend/features/home/home.css`.
- **Tests** : `npm run build`
- **Notes** : Overlay d'orientation ajouté + variables responsive centralisées (`--responsive-*`) à généraliser sur les prochains modules.

### ⚠️ WIP - Système d'Emails Membres (2025-10-16 11:45)

**Statut** : ✅ En développement (prêt pour commit)
**Agent** : NEO (IntegrityWatcher via Claude Code)

**Fichiers modifiés (9 fichiers)** :
- **Backend (6)** :
  - `email_service.py` - Ajout méthodes `send_auth_issue_notification_email()`, `send_custom_email()`
  - `admin_router.py` - Refonte endpoint `/admin/emails/send` (multi-types)
  - `admin_service.py`, `timeline_service.py`, `memory/router.py`, `monitoring/router.py`
- **Frontend (3)** :
  - `beta-invitations-module.js` - Refonte UI avec sélecteur de type d'email
  - `admin.js` - Onglet renommé "Envoi de mails"
  - `admin-dashboard.css` - Styles pour `.auth-admin__select`
- **Documentation** : `docs/MEMBER_EMAILS_SYSTEM.md` (nouveau), `AGENT_SYNC.md` (mis à jour)

**Changements API** :
- ⚠️ **Breaking change mitigé** : Endpoint `/admin/beta-invitations/send` renommé → `/admin/emails/send`
- ✅ **Rétrocompatibilité** : Endpoint deprecated ajouté avec redirection automatique
- ✅ **Type par défaut** : `beta_invitation` maintenu pour compatibilité
- ✅ **Nouvelles features** :
  - Template `auth_issue` : Notification problème d'authentification
  - Template `custom` : Emails personnalisés (requiert `subject`, `html_body`, `text_body`)

**Validation NEO** :
- ✅ Cohérence backend/frontend vérifiée
- ✅ Frontend appelle le nouveau endpoint `/admin/emails/send`
- ✅ Endpoint deprecated implémenté pour rétrocompatibilité
- ✅ Paramètres validés côté backend (type, custom fields)
- ⚠️ Tests E2E recommandés avant déploiement

**Recommandations avant commit** :
1. ✅ Tests manuels UI : sélecteur type email + envoi
2. ✅ Test endpoint deprecated (ancienne URL → redirection)
3. 🟡 Tests E2E automatisés (optionnel, recommandé)
4. 📝 Mise à jour `openapi.json` si généré automatiquement

**Documentation** :
- ✅ [docs/MEMBER_EMAILS_SYSTEM.md](docs/MEMBER_EMAILS_SYSTEM.md) - Guide complet système emails
- ✅ [AGENT_SYNC.md](AGENT_SYNC.md) - Section "Fonctionnalités Administration" mise à jour


### ✅ Session 2025-10-16 - Production Deployment (TERMINÉE)
- **Statut** : ✅ **PRODUCTION STABLE**
- **Priorité** : 🔴 **CRITIQUE** → ✅ **RÉSOLU**
- **Travaux effectués** :
  - Configuration complète SMTP pour emails
  - Ajout de toutes les API keys et secrets
  - Correction du liveness probe
  - Ajout de l'import map pour modules ESM
  - Déploiement révision `emergence-app-00364`
- **Résultat** : Application 100% fonctionnelle en production
- **Documentation** : [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md)

### ✅ Session 2025-10-15 - Phase P1 (TERMINÉE)
- **Statut** : ✅ **PHASE P1 COMPLÉTÉE** (3/3 fonctionnalités)
- **Fonctionnalités livrées** :
  - P1.1 - Hints Proactifs UI (~3 heures)
  - P1.2 - Thème Clair/Sombre (~2 heures)
  - P1.3 - Gestion Avancée Concepts (~4 heures)
- **Progression totale** : 61% (14/23 fonctionnalités)
- **Documentation** : [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md)

### ✅ Session 2025-10-15 - Phase P0 (TERMINÉE)
- **Statut** : ✅ **PHASE P0 COMPLÉTÉE** (3/3 fonctionnalités)
- **Fonctionnalités livrées** :
  - P0.1 - Archivage Conversations (~4 heures)
  - P0.2 - Graphe de Connaissances (~3 heures)
  - P0.3 - Export CSV/PDF (~4 heures)
- **Temps total** : ~11 heures (estimation : 3-5 jours)
- **Efficacité** : 3-4x plus rapide que prévu

---

## 📚 Documentation Essentielle

### Documents de Référence
- 📋 [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) - Roadmap unique et officielle (13 features)
- 📊 [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) - Suivi quotidien (61% complété)
- 🚀 [NEXT_SESSION_P2_4_TO_P2_9.md](NEXT_SESSION_P2_4_TO_P2_9.md) - Planification phases P2.4 à P2.9 (microservices migration)
- 📜 [CHANGELOG.md](CHANGELOG.md) - Historique détaillé des versions
- 📖 [README.md](README.md) - Documentation principale du projet

### Documentation Technique
- 🏗️ [docs/architecture/](docs/architecture/) - Architecture système
- 🔧 [docs/backend/](docs/backend/) - Documentation backend
- 🎨 [docs/frontend/](docs/frontend/) - Documentation frontend
- 📦 [docs/deployments/](docs/deployments/) - Guides de déploiement

### Conventions de Développement (Nouveau - 2025-10-16)
- 🆕 [docs/AGENTS_COORDINATION.md](docs/AGENTS_COORDINATION.md) - **Conventions obligatoires inter-agents**
  - Gestion NULL timestamps (pattern COALESCE)
  - Jointures flexibles (LEFT JOIN préféré)
  - Logging standardisé avec préfixes
  - Gestion d'erreurs robuste avec fallbacks
- 🆕 [docs/INTER_AGENT_SYNC.md](docs/INTER_AGENT_SYNC.md) - **Points de synchronisation et checklists**
  - Checklist pré/post modification
  - État du codebase (conformité conventions)
  - Communication entre sessions Claude Code / Codex GPT

### Tests et Validation
- 🆕 [docs/tests/PHASE1_VALIDATION_CHECKLIST.md](docs/tests/PHASE1_VALIDATION_CHECKLIST.md) - **Tests Phase 1 Backend Fixes**
  - 12 tests fonctionnels (API + Frontend)
  - Commandes curl pour validation manuelle
  - Critères de validation pour charts Cockpit et Admin

### Guides Opérationnels
- 🚀 [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) - État déploiement production
- 🔧 [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md) - Guide résolution problèmes
- 📝 [docs/passation.md](docs/passation.md) - Journal de passation (3 dernières entrées minimum)
- 🤖 [AGENTS.md](AGENTS.md) - Consignes pour agents IA
- 🔄 [CODEV_PROTOCOL.md](CODEV_PROTOCOL.md) - Protocole multi-agents

### Documentation Utilisateur
- 📚 [docs/TUTORIAL_SYSTEM.md](docs/TUTORIAL_SYSTEM.md) - Système de tutoriel
- 🎯 [GUIDE_INTERFACE_BETA.md](GUIDE_INTERFACE_BETA.md) - Guide interface bêta
- ❓ [docs/FAQ.md](docs/FAQ.md) - Questions fréquentes

### Fonctionnalités Administration
- 📧 [docs/MEMBER_EMAILS_SYSTEM.md](docs/MEMBER_EMAILS_SYSTEM.md) - **Système d'envoi d'emails aux membres**
  - Templates : invitation beta, notification auth, emails personnalisés
  - Interface admin : sélecteur de type d'email, gestion destinataires
  - API : `/api/admin/emails/send` (remplace `/api/admin/beta-invitations/send`)
  - Configuration SMTP requise (voir variables d'env dans doc)

### 🤖 Sub-Agents Claude Code - Système de Surveillance et Coordination

**IMPORTANT** : Les sub-agents Claude Code sont configurés pour **automatiquement suggérer la mise à jour de ce fichier (AGENT_SYNC.md)** quand ils détectent des changements structurels importants.

#### Sub-Agents Disponibles (Slash Commands)

**Anima - Gardien de Documentation** (`/check_docs`)
- **Rôle** : Vérifie la cohérence entre code et documentation
- **Responsabilité** : Suggère mise à jour AGENT_SYNC.md si nouvelle doc d'architecture, processus, ou guides ajoutés
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/scan_docs.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/docs_report.json`

**Neo - Gardien d'Intégrité** (`/check_integrity`)
- **Rôle** : Détecte incohérences backend/frontend et régressions
- **Responsabilité** : Suggère mise à jour AGENT_SYNC.md si breaking changes, nouveaux endpoints, ou changements d'architecture critiques
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/check_integrity.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/integrity_report.json`

**Nexus - Coordinateur** (`/guardian_report`)
- **Rôle** : Synthétise les rapports d'Anima et Neo
- **Responsabilité** : Propose mise à jour consolidée de AGENT_SYNC.md basée sur les changements systémiques détectés
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/generate_report.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/unified_report.json`

**ProdGuardian - Surveillance Production** (`/check_prod`)
- **Rôle** : Analyse logs Cloud Run et détecte anomalies en production
- **Responsabilité** : Suggère mise à jour AGENT_SYNC.md si problèmes récurrents ou changements de config nécessaires
- **Script** : `claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py`
- **Rapport** : `claude-plugins/integrity-docs-guardian/reports/prod_report.json`

#### Mécanisme de Synchronisation Automatique

Les sub-agents suivent ces règles :
1. ✅ **Détection** : Analyse des changements via leurs scripts respectifs
2. ✅ **Évaluation** : Détermination si changements impactent coordination multi-agents
3. ✅ **Suggestion** : Proposition de mise à jour de AGENT_SYNC.md avec contenu pré-rédigé
4. ⏸️ **Validation humaine** : Demande confirmation avant toute modification

**Formats de suggestion** : Chaque sub-agent utilise un format spécifique (📝, 🔧, 🎯, 🚨) pour identifier la source et le type de changement.

**Avantage pour Codex GPT** : Quand vous donnez une tâche à Codex GPT, il aura accès à une documentation AGENT_SYNC.md maintenue à jour par les sub-agents Claude Code, évitant malentendus et erreurs.

---

## ⚙️ Configuration Développement

### Environnement Local

**Prérequis** :
- Python 3.11+
- Node.js 18+
- Docker (pour tests et déploiement)

**Installation** :
```bash
# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
npm install

# Variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API
```

**Lancement** :
```bash
# Backend (dev)
uvicorn src.backend.main:app --reload --port 8000

# Frontend (dev)
npm run dev

# Build frontend
npm run build
```

**Tests** :
```bash
# Tests backend
pytest tests/backend/

# Tests frontend
npm run test

# Linting
ruff check src/backend/
mypy src/backend/
```

### Variables d'Environnement Essentielles

**Minimum requis pour développement local** :
```bash
# API Keys (au moins une)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...

# OAuth (optionnel en dev)
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...

# Email (optionnel)
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
```

---

## ✅ Synchronisation Cloud ↔ Local ↔ GitHub

### Statut
- ✅ **Machine locale** : Remotes `origin` et `codex` configurés et opérationnels
- ⚠️ **Environnement cloud GPT Codex** : Aucun remote (attendu et normal)
- ✅ **Solution** : Workflow de synchronisation via patches Git documenté

### Documentation
- 📚 [docs/CLOUD_LOCAL_SYNC_WORKFLOW.md](docs/CLOUD_LOCAL_SYNC_WORKFLOW.md) - Guide complet (3 méthodes)
- 📚 [docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md](docs/GPT_CODEX_CLOUD_INSTRUCTIONS.md) - Instructions agent cloud
- 📚 [prompts/local_agent_github_sync.md](prompts/local_agent_github_sync.md) - Résumé workflow

### Workflow Recommandé
1. **Agent cloud** : Génère patch avec modifications
2. **Agent local** : Applique patch et push vers GitHub
3. **Validation** : Tests + review avant merge

---

## 🔒 Sécurité & Bonnes Pratiques

### Secrets
- ❌ **JAMAIS** commiter de secrets dans Git
- ✅ Utiliser `.env` local (ignoré par Git)
- ✅ Utiliser Google Secret Manager en production
- ✅ Référencer les secrets via `secretKeyRef` dans YAML

### Déploiement
- ✅ Toujours tester localement avant déploiement
- ✅ Utiliser des digests SHA256 pour les images Docker
- ✅ Vérifier les health checks après déploiement
- ✅ Monitorer les logs pendant 1h post-déploiement

### Code Quality
- ✅ Linter : `ruff check src/backend/`
- ✅ Type checking : `mypy src/backend/`
- ✅ Tests : `pytest tests/backend/`
- ✅ Coverage : Maintenir >80%

---

## 🎯 Prochaines Actions

### Immédiat (Cette semaine)
1. 🔴 Publier/mettre à jour le secret GCP `AUTH_ALLOWLIST_SEED` (JSON allowlist + mots de passe temporaires)
2. 🟠 Surveiller les logs Cloud Run (`emergence-app-00447-faf`) pendant ≥60 min — alerte si pics 401/5xx
3. 🔜 Démarrer Phase P2 (Dashboard Admin Avancé)
4. 🔜 Tests d'intégration P1 en production

### Court Terme (1-2 semaines)
1. Phase P2 complète (Administration & Sécurité)
2. Tests E2E complets
3. Documentation utilisateur mise à jour
4. Monitoring et métriques Phase P2

### Moyen Terme (3-4 semaines)
1. Phase P3 (Fonctionnalités Avancées)
2. PWA (Mode hors ligne)
3. API Publique Développeurs
4. Webhooks et Intégrations

---

## 📞 Support & Contact

**Documentation Technique** :
- Guide de déploiement : [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md)
- Configuration YAML : [stable-service.yaml](stable-service.yaml)
- Roadmap officielle : [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md)

**Logs et Monitoring** :
- Cloud Logging : https://console.cloud.google.com/logs
- Cloud Run Console : https://console.cloud.google.com/run
- Projet GCP : emergence-469005

**En cas de problème** :
1. Vérifier les logs Cloud Run
2. Consulter [FIX_PRODUCTION_DEPLOYMENT.md](FIX_PRODUCTION_DEPLOYMENT.md)
3. Vérifier l'état des secrets dans Secret Manager
4. Rollback si nécessaire (voir procédure dans documentation)

---

## 📋 Checklist Avant Nouvelle Session

**À vérifier TOUJOURS avant de commencer** :

- [ ] Lire ce fichier (`AGENT_SYNC.md`)
- [ ] Lire [`AGENTS.md`](AGENTS.md)
- [ ] Lire [`CODEV_PROTOCOL.md`](CODEV_PROTOCOL.md)
- [ ] Lire les 3 dernières entrées de [`docs/passation.md`](docs/passation.md)
- [ ] Exécuter `git status`
- [ ] Exécuter `git log --oneline -10`
- [ ] Vérifier la [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md)
- [ ] Consulter [DEPLOYMENT_SUCCESS.md](DEPLOYMENT_SUCCESS.md) pour état production

**Avant de coder** :
- [ ] Créer une branche feature si nécessaire
- [ ] Mettre à jour les dépendances si ancien checkout
- [ ] Lancer les tests pour vérifier l'état de base
- [ ] Vérifier que le build frontend fonctionne

**Avant de commiter** :
- [ ] Lancer les tests : `pytest tests/backend/`
- [ ] Lancer le linter : `ruff check src/backend/`
- [ ] Vérifier le type checking : `mypy src/backend/`
- [ ] Build frontend : `npm run build`
- [ ] Mettre à jour [AGENT_SYNC.md](AGENT_SYNC.md)
- [ ] Mettre à jour [docs/passation.md](docs/passation.md)

---

**Dernière mise à jour** : 2025-10-16 13:40 par Claude Code (Sonnet 4.5)
**Version** : beta-2.1.1 (Phase P1 + Debug & Audit + Versioning unifié)
**Statut Production** : ✅ STABLE ET OPÉRATIONNEL - Révision 00455-cew (100% trafic)
**Progression Roadmap** : 61% (14/23 fonctionnalités)
**Dernière modification** : Déploiement canary beta-2.1.1 validé et basculé à 100%


---

## 🤖 Synchronisation automatique
### Consolidation - 2025-10-16T12:43:40.926663

**Type de déclenchement** : `threshold`
**Conditions** : {
  "pending_changes": 6,
  "threshold": 5
}
**Changements consolidés** : 6 événements sur 2 fichiers

**Fichiers modifiés** :
- **AGENT_SYNC.md** : 5 événement(s)
  - `modified` à 2025-10-16T12:29:41.398492 (agent: unknown)
  - `modified` à 2025-10-16T12:32:41.529434 (agent: unknown)
  - `modified` à 2025-10-16T12:33:11.529712 (agent: unknown)
  - `modified` à 2025-10-16T12:42:41.630139 (agent: unknown)
  - `modified` à 2025-10-16T12:43:11.651997 (agent: unknown)
- **docs/passation.md** : 1 événement(s)
  - `modified` à 2025-10-16T12:29:41.437724 (agent: unknown)

---

### Consolidation - 2025-10-16T12:29:40.845209

**Type de déclenchement** : `threshold`
**Conditions** : {
  "pending_changes": 5,
  "threshold": 5
}
**Changements consolidés** : 5 événements sur 2 fichiers

**Fichiers modifiés** :
- **AGENT_SYNC.md** : 4 événement(s)
  - `modified` à 2025-10-16T11:57:40.984670 (agent: unknown)
  - `modified` à 2025-10-16T12:19:11.234778 (agent: unknown)
  - `modified` à 2025-10-16T12:28:11.333615 (agent: unknown)
  - `modified` à 2025-10-16T12:28:41.358454 (agent: unknown)
- **docs/passation.md** : 1 événement(s)
  - `modified` à 2025-10-16T12:20:11.256692 (agent: unknown)

---

### Consolidation - 2025-10-16T11:57:40.616375

**Type de déclenchement** : `threshold`
**Conditions** : {
  "pending_changes": 5,
  "threshold": 5
}
**Changements consolidés** : 5 événements sur 2 fichiers

**Fichiers modifiés** :
- **AGENT_SYNC.md** : 4 événement(s)
  - `modified` à 2025-10-16T11:41:40.573899 (agent: unknown)
  - `modified` à 2025-10-16T11:42:10.589720 (agent: unknown)
  - `modified` à 2025-10-16T11:46:40.690651 (agent: unknown)
  - `modified` à 2025-10-16T11:47:10.714805 (agent: unknown)
- **docs/passation.md** : 1 événement(s)
  - `modified` à 2025-10-16T11:57:10.974770 (agent: unknown)

---


