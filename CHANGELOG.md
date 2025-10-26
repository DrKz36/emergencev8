# 📦 CHANGELOG - EMERGENCE V8

> **Suivi de versions et évolutions du projet**
>
> Format de versioning : `beta-X.Y.Z` jusqu'à la release V1.0.0
> - **X (Major)** : Phases complètes (P0, P1, P2, P3) / Changements majeurs
> - **Y (Minor)** : Nouvelles fonctionnalités / Features individuelles
> - **Z (Patch)** : Corrections de bugs / Améliorations mineures
>
> Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
> et ce projet adhère au [Versioning Sémantique](https://semver.org/lang/fr/).

---

## [beta-3.1.3] - 2025-10-26

### ✨ Nouvelle Fonctionnalité

**Métrique nDCG@k Temporelle - Évaluation Ranking avec Fraîcheur**

Implémentation d'une métrique d'évaluation interne pour mesurer l'impact des boosts de fraîcheur et entropie dans le moteur de ranking ÉMERGENCE V8.

**Fonctionnalités:**

1. **Métrique nDCG@k temporelle (`ndcg_time_at_k`)**
   - Formule : `DCG^time@k = Σ (2^rel_i - 1) * exp(-λ * Δt_i) / log2(i+1)`
   - Pénalisation exponentielle selon la fraîcheur des documents
   - Paramètres configurables : `k`, `T_days`, `lambda`
   - Fichier : `src/backend/features/benchmarks/metrics/temporal_ndcg.py`

2. **Intégration dans BenchmarksService**
   - Méthode helper : `BenchmarksService.calculate_temporal_ndcg()`
   - Import de la métrique dans `features/benchmarks/service.py`
   - Exposition pour réutilisation dans d'autres services

3. **Endpoint API**
   - `POST /api/benchmarks/metrics/ndcg-temporal` - Calcul métrique à la demande
   - Pydantic models pour validation : `RankedItem`, `TemporalNDCGRequest`
   - Retour JSON avec score nDCG@k + métadonnées

4. **Tests complets**
   - 18 tests unitaires dans `tests/backend/features/test_benchmarks_metrics.py`
   - Couverture : cas edge, décroissance temporelle, trade-offs pertinence/fraîcheur
   - Validation paramètres (k, T_days, lambda)
   - Scénarios réalistes (recherche documents)

**Impact:**
- ✅ **Quantification boosts fraîcheur** - Mesure réelle impact ranking temporel
- ✅ **Métrique réutilisable** - Accessible via service pour benchmarks futurs
- ✅ **API externe** - Endpoint pour calcul à la demande
- ✅ **Type-safe** - Type hints complets + validation Pydantic

**Fichiers modifiés:**
- `src/backend/features/benchmarks/service.py` - Import + méthode helper
- `src/backend/features/benchmarks/router.py` - Endpoint POST + Pydantic models
- `src/backend/features/benchmarks/metrics/temporal_ndcg.py` - Métrique complète
- `tests/backend/features/test_benchmarks_metrics.py` - 18 tests

**Référence:** Prompt ÉMERGENCE révision 00298-g8j (Phase P2 complétée)
### 🔧 Corrections

- **Chat Mobile – Composer & Scroll**
  - Décale le footer du chat au-dessus de la barre de navigation portrait pour garder la zone de saisie accessible.
  - Ajoute un padding dynamique côté messages pour éviter les zones mortes sous la bottom nav sur iOS/Android.
  - **Fichiers :** [`chat.css`](src/frontend/features/chat/chat.css)

### 📦 Versioning & Patch Notes

- `src/version.js` & `src/frontend/version.js` — Version `beta-3.1.3`, patch notes mises à jour.
- `package.json` — Synchronisation version npm (`beta-3.1.3`).

---

## [beta-3.1.2] - 2025-10-26

### ✨ Amélioration Qualité

**Refactor Complet Documentation Inter-Agents**

**Problème résolu:** Conflits merge récurrents sur `AGENT_SYNC.md` et `docs/passation.md` (454KB !) lors de travail parallèle des agents.

**Solution implémentée - Structure fichiers séparés par agent:**

1. **Fichiers de synchronisation séparés:**
   - `AGENT_SYNC_CLAUDE.md` ← Claude Code écrit ici
   - `AGENT_SYNC_CODEX.md` ← Codex GPT écrit ici
   - `SYNC_STATUS.md` ← Vue d'ensemble centralisée (index)

2. **Journaux de passation séparés:**
   - `docs/passation_claude.md` ← Journal Claude (48h max, auto-archivé)
   - `docs/passation_codex.md` ← Journal Codex (48h max, auto-archivé)
   - `docs/archives/passation_archive_*.md` ← Archives >48h

3. **Rotation stricte 48h:**
   - Anciennes entrées archivées automatiquement
   - Fichiers toujours légers (<50KB)

**Résultat:**
- ✅ **Zéro conflit merge** sur docs de synchronisation (fichiers séparés)
- ✅ **Meilleure coordination** (chaque agent voit clairement ce que fait l'autre)
- ✅ **Lecture rapide** (SYNC_STATUS.md = 2 min vs 10 min avant)
- ✅ **Rotation auto** (passation.md archivé de 454KB → <20KB)

**Fichiers modifiés:**
- Créés: `SYNC_STATUS.md`, `AGENT_SYNC_CLAUDE.md`, `AGENT_SYNC_CODEX.md`
- Créés: `docs/passation_claude.md`, `docs/passation_codex.md`
- Archivé: `docs/passation.md` (454KB) → `docs/archives/passation_archive_2025-10-01_to_2025-10-26.md`
- Mis à jour: `CLAUDE.md`, `CODEV_PROTOCOL.md`, `CODEX_GPT_GUIDE.md` (nouvelle structure de lecture)

### 📦 Versioning & Patch Notes

- `src/version.js` & `src/frontend/version.js` — Version `beta-3.1.2`, patch notes ajoutées.
- `package.json` — Synchronisation version npm (`beta-3.1.2`).

---

## [beta-3.1.1] - 2025-10-26

### 🔧 Corrections

- **Module Dialogue - Modal de reprise**
  - Attente automatique du chargement des threads pour proposer l'option « Reprendre » quand des conversations existent.
  - Mise à jour dynamique du contenu du modal si les données arrivent après affichage.
  - **Fichiers :** [chat.js](src/frontend/features/chat/chat.js)

### 📦 Versioning & Patch Notes

- `src/version.js` & `src/frontend/version.js` — Version `beta-3.1.1`, entrée patch notes dédiée.
- `package.json` — Synchronisation version npm (`beta-3.1.1`).

## [beta-3.1.0] - 2025-10-26

### 🆕 Fonctionnalités Ajoutées

**1. Système de Webhooks Complet (P3.11)**
- Endpoints REST `/api/webhooks/*` (CRUD + deliveries + stats)
- Événements: thread.created, message.sent, analysis.completed, debate.completed, document.uploaded
- Delivery HTTP POST avec HMAC SHA256 pour sécurité
- Retry automatique 3x avec backoff (5s, 15s, 60s)
- UI complète: Settings > Webhooks (modal, liste, logs, stats)
- Tables BDD: `webhooks` + `webhook_deliveries` (migration 010)

**Fichiers:**
- Backend: [webhooks/router.py](src/backend/features/webhooks/router.py)
- Frontend: [settings-webhooks.js](src/frontend/features/settings/settings-webhooks.js)
- **PR:** #12

**2. Scripts de Monitoring Production**
- Script health check avec JWT auth: [check-prod-health.ps1](scripts/check-prod-health.ps1)
- Vérification endpoint `/ready` avec Bearer token (résout 403)
- Métriques Cloud Run via gcloud (optionnel)
- Logs récents (20 derniers, optionnel)
- Rapport markdown auto-généré dans `reports/prod-health-report.md`
- Détection OS automatique (python/python3)
- Documentation complète: [README_HEALTH_CHECK.md](scripts/README_HEALTH_CHECK.md)

**Fichiers:**
- [scripts/check-prod-health.ps1](scripts/check-prod-health.ps1)
- **PR:** #17

**3. Système de Patch Notes**
- Patch notes centralisées dans `src/version.js`
- Affichage automatique dans module "À propos" (Paramètres)
- Historique des 2 dernières versions visible
- Icônes par type de changement (feature, fix, quality, perf, phase)
- Mise en évidence de la version actuelle

**Fichiers:**
- [src/version.js](src/version.js) - Système centralisé
- [settings-main.js](src/frontend/features/settings/settings-main.js) - Affichage UI

### ✨ Qualité & Performance

**4. Mypy 100% Clean - Type Safety Complet**
- 471 erreurs mypy corrigées → **0 erreurs** restantes
- Type hints complets sur tout le backend Python
- Strict mode mypy activé
- Guide de style mypy intégré: [MYPY_STYLE_GUIDE.md](docs/MYPY_STYLE_GUIDE.md)

**Commits:**
- Batch final: `439f8f4` (471→0 erreurs)
- Documentation: `e9bd1e5`

**5. Bundle Optimization Frontend**
- Lazy loading: Chart.js, jsPDF, PapaParse
- Réduction taille bundle initial
- Amélioration temps de chargement page

**Fichiers:**
- [vite.config.js](vite.config.js) - Config optimisation
- **Commit:** `fa6c87c`

### 🔧 Corrections

**6. Cockpit - 3 Bugs SQL Critiques**
- Bug SQL `no such column: agent` → `agent_id`
- Filtrage session_id trop restrictif → `session_id=None`
- Agents fantômes dans Distribution → whitelist stricte
- Graphiques vides → fetch données + backend metrics

**Fichiers:**
- [cockpit/router.py](src/backend/features/cockpit/router.py)
- **PRs:** #11, #10, #7

**7. Module Documents - Layout Desktop/Mobile**
- Fix layout foireux desktop et mobile
- Résolution problèmes d'affichage et scroll

**Commit:** `a616ae9`

**8. Module Chat - 4 Bugs UI/UX Critiques**
- Modal démarrage corrigé
- Scroll automatique résolu
- Routing réponses agents fixé
- Duplication messages éliminée

**Commits:**
- `bd197d7`, `fdc59a4`, `a9289e2`

**9. Tests - 5 Flaky Tests Corrigés**
- ChromaDB Windows compatibility
- Mocks RAG améliorés
- Stabilité suite de tests

**Commit:** `598d456`

### 📝 Documentation

**10. Harmonisation Documentation Multi-Agents**
- AGENTS.md harmonisé avec CODEV_PROTOCOL.md et CLAUDE.md
- CODEX_SYSTEM_PROMPT.md unifié
- Suppression ARBO-LOCK (obsolète)
- Ajout directives versioning obligatoires

**Commits:**
- `9dfd2f1`, `16dbdc8`, `58e4ede`

**11. Guide Versioning Complet**
- [VERSIONING_GUIDE.md](docs/VERSIONING_GUIDE.md) mis à jour
- Règles d'incrémentation clarifiées
- Workflow de mise à jour documenté

### 🎯 Impact Global

- ✅ **78% features complétées** (18/23) - +4% vs beta-3.0.0
- ✅ **Phase P3 démarrée** (1/4 features done - P3.11 webhooks)
- ✅ **Qualité code maximale** (mypy 100% clean)
- ✅ **Monitoring production** automatisé
- ✅ **Intégrations externes** possibles via webhooks

---

## [beta-2.1.3] - 2025-10-17

### 📧 Guardian Email Reports - Notification Automatique

#### 🆕 Fonctionnalités Ajoutées

**1. Système d'envoi automatique des rapports Guardian par email**
- Email automatique après chaque orchestration Guardian
- Rapports HTML stylisés avec thème ÉMERGENCE (dégradés bleu/noir)
- Version text pour compatibilité
- Destinataire: Admin uniquement (`gonzalefernando@gmail.com`)

**Fichiers créés:**
- [send_guardian_reports_email.py](claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py) - Script d'envoi automatique
- [README_EMAIL_REPORTS.md](claude-plugins/integrity-docs-guardian/README_EMAIL_REPORTS.md) - Documentation complète (400+ lignes)

**2. Intégration dans les orchestrations Guardian**
- Auto-orchestrator exécute l'envoi en Phase 5
- Master-orchestrator exécute l'envoi en Step 9/9
- Gestion d'erreurs sans bloquer l'orchestration
- Chargement automatique du `.env` (dotenv)

**Fichiers modifiés:**
- [auto_orchestrator.py:145-153](claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py#L145-L153) - Intégration Phase 5
- [master_orchestrator.py:322-328](claude-plugins/integrity-docs-guardian/scripts/master_orchestrator.py#L322-L328) - Intégration Step 9

**3. Configuration SMTP complète**
- Variables d'environnement documentées dans `.env.example`
- Support Gmail, Outlook, Amazon SES
- TLS/SSL configurable
- Mot de passe d'application Gmail (sécurisé)

**Fichier modifié:**
- [.env.example:28-36](c:\dev\emergenceV8\.env.example#L28-L36) - Variables SMTP

**4. Contenu des rapports email**

Chaque email contient:
- Badge de statut global (✅ OK, ⚠️ WARNING, 🚨 CRITICAL)
- 6 rapports Guardian complets:
  - **Production Guardian** (prod_report.json) - Santé Cloud Run
  - **Intégrité Neo** (integrity_report.json) - Cohérence backend/frontend
  - **Documentation Anima** (docs_report.json) - Lacunes documentation
  - **Rapport Unifié Nexus** (unified_report.json) - Synthèse
  - **Rapport Global Master** (global_report.json) - Orchestration
  - **Orchestration** (orchestration_report.json) - Résumé exécution
- Statistiques détaillées par rapport (erreurs, warnings, problèmes)
- Top 3 recommandations prioritaires par rapport
- Timestamp de chaque scan
- Design HTML responsive et professionnel

#### ✅ Tests Effectués

- [x] Envoi manuel d'email - Succès
- [x] Orchestration automatique avec email - Succès
- [x] Intégration dans auto_orchestrator - Succès
- [x] Configuration SMTP Gmail validée - Succès
- [x] Réception email confirmée - Succès

#### 📝 Documentation Mise à Jour

**Nouvelle documentation:**
- [README_EMAIL_REPORTS.md](claude-plugins/integrity-docs-guardian/README_EMAIL_REPORTS.md) - Guide complet (400+ lignes)
  - Configuration SMTP détaillée (Gmail, Outlook, SES)
  - Guide d'utilisation (manuel et automatique)
  - Troubleshooting complet
  - Exemples d'automatisation (cron, Windows Task Scheduler)
  - Bonnes pratiques de sécurité

**Documentation mise à jour:**
- [GUARDIAN_SETUP_COMPLETE.md](GUARDIAN_SETUP_COMPLETE.md) - Ajout section "Envoi Automatique par Email"
- [MONITORING_GUIDE.md:502-542](docs/MONITORING_GUIDE.md#L502-L542) - Section Guardian Email Reports
- [.env.example](c:\dev\emergenceV8\.env.example) - Variables SMTP documentées

#### 🎯 Impact

- ✅ Rapports Guardian envoyés automatiquement à l'admin après chaque orchestration
- ✅ Monitoring proactif de la production sans intervention manuelle
- ✅ Email HTML professionnel avec design ÉMERGENCE
- ✅ Support multi-fournisseurs SMTP (Gmail, Outlook, SES)
- ✅ Documentation complète pour configuration et troubleshooting

#### 🚀 Utilisation

**Envoi automatique avec orchestration:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py
```

**Envoi manuel des derniers rapports:**
```bash
python claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py
```

**Configuration requise (dans `.env`):**
```env
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=admin@example.com
SMTP_PASSWORD=app-password
SMTP_FROM_EMAIL=admin@example.com
SMTP_FROM_NAME=ÉMERGENCE Guardian
SMTP_USE_TLS=1
```

---

## [beta-2.1.2] - 2025-10-17

### 🎉 Corrections Production et Synchronisation Système

#### 📊 Métriques
- **Fonctionnalités complètes** : 14/23 (61%)
- **Phase P1** : Complété (3/3)
- **Version package.json** : `beta-2.1.2`

#### 🔧 Corrections Critiques

**1. Synchronisation Versioning (beta-2.1.2)**
- Correction de la désynchronisation entre version production et code
- Mise à jour automatique dans tous les fichiers source
- Production affichera désormais la bonne version

**Fichiers modifiés** :
- [package.json:4](package.json#L4) - Version mise à jour
- [index.html:186](index.html#L186) - Version UI mise à jour
- [monitoring/router.py:38](src/backend/features/monitoring/router.py#L38) - Healthcheck
- [monitoring/router.py:384](src/backend/features/monitoring/router.py#L384) - System info

**2. Script de Synchronisation Automatique**
- Nouveau script PowerShell pour synchronisation version automatique
- Lit depuis `src/version.js` (source de vérité unique)
- Met à jour 4 fichiers automatiquement
- Mode DryRun pour validation sécurisée

**Fichier créé** :
- [scripts/sync_version.ps1](scripts/sync_version.ps1) - Script de synchronisation

**3. Correction Bug password_must_reset**
- Correction de la boucle infinie de demande de vérification email/reset password
- Membres ne seront plus demandés de réinitialiser leur mot de passe à chaque connexion
- Fix SQL CASE statement dans _upsert_allowlist

**Fichiers modifiés** :
- [auth/service.py:1205](src/backend/features/auth/service.py#L1205) - Fix SQL CASE
- [auth/service.py:998-1003](src/backend/features/auth/service.py#L998-L1003) - UPDATE explicite (change_own_password)
- [auth/service.py:951-956](src/backend/features/auth/service.py#L951-L956) - UPDATE explicite (set_allowlist_password)

**4. Correction Chargement Thread Mobile**
- Thread se charge maintenant automatiquement au retour sur le module chat (mobile)
- Le premier message est pris en compte immédiatement
- Thread activé à chaque affichage du module chat

**Fichier modifié** :
- [app.js:671](src/frontend/core/app.js#L671) - Condition de chargement étendue

**5. Vérification Accès Conversations Archivées**
- Confirmé : les agents ont accès aux conversations archivées via leur mémoire
- Paramètre `include_archived=True` par défaut dans l'API de recherche unifiée
- Recherche mémoire fonctionne sur threads actifs ET archivés

**Fichier vérifié** :
- [memory/router.py:704](src/backend/features/memory/router.py#L704) - Paramètre include_archived

#### ✅ Impact des Corrections

- ✅ Production affiche version correcte (beta-2.1.2 + 61% completion)
- ✅ Membres peuvent utiliser le système sans demandes répétitives de reset password
- ✅ Mobile : thread charge automatiquement au premier affichage du chat
- ✅ Agents ont accès complet à toutes les conversations (actives + archivées)
- ✅ Synchronisation version automatisée pour l'avenir

#### 📝 Documentation Mise à Jour

- [docs/VERSIONING_GUIDE.md](docs/VERSIONING_GUIDE.md) - Guide de versioning (à jour)
- [scripts/sync_version.ps1](scripts/sync_version.ps1) - Script avec documentation intégrée

#### 🔜 Prochaine Étape

**Déploiement Production**
- Build Docker avec version beta-2.1.2
- Déploiement canary sur Google Cloud Run
- Tests sur canary (version, password reset, thread loading)
- Déploiement progressif si tests OK

---

## [beta-1.1.0] - 2025-10-15

### 🎉 P0.1 - Archivage des Conversations (UI)

#### 📊 Métriques
- **Fonctionnalités complètes** : 9/23 (39%) ⬆️ +4%
- **Phase P0** : 33% complété (1/3)
- **Version package.json** : `beta-1.1.0`

#### ✅ Fonctionnalités Ajoutées

**1. Toggle Actifs/Archivés**
- Interface avec deux boutons visuels (Actifs / Archivés)
- État actif avec gradient bleu et indicateur visuel
- Compteurs en temps réel pour chaque vue
- Navigation fluide entre les deux modes

**Fichiers** :
- [threads.js:295-312](src/frontend/features/threads/threads.js#L295-L312) - Template HTML du toggle
- [threads.js:369-392](src/frontend/features/threads/threads.js#L369-L392) - Event listeners
- [threads.js:472-487](src/frontend/features/threads/threads.js#L472-L487) - État visuel du toggle

**2. Fonction de Désarchivage**
- Bouton "Désarchiver" dans le menu contextuel en mode archivé
- API `unarchiveThread()` pour restaurer les conversations
- Mise à jour automatique des compteurs après désarchivage
- Suppression du thread de la liste archivée après désarchivage

**Fichiers** :
- [threads-service.js:144-147](src/frontend/features/threads/threads-service.js#L144-L147) - Fonction API
- [threads.js:1034-1069](src/frontend/features/threads/threads.js#L1034-L1069) - Handler désarchivage
- [threads.js:706-709](src/frontend/features/threads/threads.js#L706-L709) - Event handler menu contextuel

**3. Menu Contextuel Adaptatif**
- Affiche "Archiver" ou "Désarchiver" selon le mode actuel
- Icônes SVG appropriées pour chaque action
- Logique conditionnelle basée sur `viewMode`

**Fichiers** :
- [threads.js:1200-1270](src/frontend/features/threads/threads.js#L1200-L1270) - Rendu du menu contextuel

**4. Compteurs Dynamiques**
- Méthode `updateThreadCounts()` pour récupérer les stats
- Badges avec nombre de threads actifs/archivés
- Mise à jour automatique après archivage/désarchivage
- Affichage dans les boutons du toggle

**Fichiers** :
- [threads.js:489-512](src/frontend/features/threads/threads.js#L489-L512) - Méthode de mise à jour
- [threads.js:500](src/frontend/features/threads/threads.js#L500) - Appel après reload
- [threads.js:1020](src/frontend/features/threads/threads.js#L1020) - Appel après archivage
- [threads.js:1048](src/frontend/features/threads/threads.js#L1048) - Appel après désarchivage

**5. Chargement Conditionnel**
- `reload()` charge les threads actifs ou archivés selon `viewMode`
- Utilise `fetchArchivedThreads()` en mode archivé
- Utilise `fetchThreads()` en mode actif

**Fichiers** :
- [threads.js:514-531](src/frontend/features/threads/threads.js#L514-L531) - Méthode reload avec condition

**6. Styling CSS Complet**
- Styles pour le toggle view avec états actif/inactif
- Badges de compteurs avec background gradient
- Transitions et animations fluides
- Responsive et accessible

**Fichiers** :
- [threads.css:116-177](src/frontend/features/threads/threads.css#L116-L177) - Styles complets

**7. Événement de désarchivage**
- Ajout de `THREADS_UNARCHIVED` dans les constantes
- Émission d'événement lors du désarchivage réussi
- Cohérence avec les autres événements threads

**Fichiers** :
- [constants.js:98](src/frontend/shared/constants.js#L98) - Constante événement

#### 🎯 Acceptance Criteria Remplis

- ✅ Clic droit sur thread → "Archiver" → disparaît de la liste active
- ✅ Onglet "Archives" affiche threads archivés
- ✅ Clic sur "Désarchiver" → thread revient dans actifs
- ✅ Badge compteur "X archivés" visible et mis à jour en temps réel

#### 📝 Documentation Mise à Jour

- [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) - Statut P0.1 complété
- [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) - Référence phase P0

#### ⏱️ Temps de Développement

- **Estimé** : 1 jour
- **Réel** : ~4 heures
- **Efficacité** : 200% (2x plus rapide que prévu)

#### 🔜 Prochaine Étape

**P0.2 - Graphe de Connaissances Interactif**
- Intégration du composant ConceptGraph
- Onglet "Graphe" dans le Centre Mémoire
- Filtres et interactions (zoom, pan, tooltips)

---

## [beta-1.0.0] - 2025-10-15

### 🎉 État Initial - Version Bêta de Référence

#### 📊 Métriques de Base
- **Fonctionnalités complètes** : 8/23 (35%)
- **Fonctionnalités partielles** : 3/23 (13%)
- **Fonctionnalités manquantes** : 12/23 (52%)
- **Version package.json** : `beta-1.0.0`

#### ✅ Fonctionnalités Principales Implémentées
- Système d'authentification et gestion utilisateurs
- Chat multi-agents (5 agents : Analyste, Généraliste, Créatif, Technique, Éthique)
- Centre Mémoire avec extraction de concepts
- Documentation interactive intégrée
- Interface administrateur (basique)
- Système de tutoriel guidé
- Métriques Prometheus (activées par défaut)
- Gestion des sessions avec notifications inactivité
- Système de versioning bêta établi

#### 📝 Documents de Référence
- [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) - Roadmap de développement (13 features prévues)
- [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) - Suivi de progression temps réel
- [docs/ROADMAP_README.md](docs/ROADMAP_README.md) - Guide d'utilisation roadmap

#### 🛠️ Stack Technique
- **Frontend** : Vite + Vanilla JS
- **Backend** : FastAPI + Python
- **Base de données** : SQLite
- **Métriques** : Prometheus + Grafana
- **Versioning** : Sémantique (SemVer) - Phase bêta

#### 🔮 Prochaines Versions Prévues
- `beta-1.1.0` : Archivage conversations (UI)
- `beta-1.2.0` : Graphe de connaissances interactif
- `beta-1.3.0` : Export conversations (CSV/PDF)
- `beta-2.0.0` : Phase P1 complète (UX Essentielle)
- `beta-3.0.0` : Phase P2 complète (Administration & Sécurité)
- `beta-4.0.0` : Phase P3 complète (Fonctionnalités Avancées)
- `v1.0.0` : Release Production Officielle (date TBD)

---

## [Non publié] - 2025-10-15

### 📝 Ajouté

#### Mémoire - Feedback Temps Réel Consolidation (V3.8)

**Fonctionnalité** : Barre de progression avec notifications WebSocket pour la consolidation mémoire

**Problème** : Manque total de feedback utilisateur pendant la consolidation (30s-5min d'attente sans retour visuel)

**Solutions implémentées** :

1. **Backend - Événements WebSocket `ws:memory_progress`** ([gardener.py:572-695](src/backend/features/memory/gardener.py#L572-L695))
   - Notification session par session pendant consolidation
   - Phases : `extracting_concepts`, `analyzing_preferences`, `vectorizing`, `completed`
   - Payload : `{current: 2, total: 5, phase: "...", status: "in_progress"}`
   - Message final avec résumé : `{consolidated_sessions: 5, new_items: 23}`

2. **Frontend - Barre de Progression Visuelle** ([memory.js:73-139](src/frontend/features/memory/memory.js#L73-L139))
   - Barre animée avec pourcentage (0-100%)
   - Labels traduits : "Extraction des concepts... (2/5 sessions)"
   - Message final : "✓ Consolidation terminée : 5 sessions, 23 nouveaux items"
   - Auto-masquage après 3 secondes
   - Styles glassmorphism ([memory.css](src/frontend/features/memory/memory.css))

3. **UX - Clarté des Actions** ([memory.js:109-475](src/frontend/features/memory/memory.js#L109-L475))
   - Bouton renommé : "Analyser" → **"Consolider mémoire"**
   - Tooltip explicatif : "Extrait concepts, préférences et faits structurés..."
   - État pendant exécution : "Consolidation..." (bouton désactivé)

4. **Documentation Enrichie**
   - Guide technique : [docs/backend/memory.md](docs/backend/memory.md) - Section 1.0 ajoutée
   - Tutoriel utilisateur : [TUTORIAL_SYSTEM.md](docs/TUTORIAL_SYSTEM.md) - Section 3 enrichie
   - Guide interactif : [tutorialGuides.js](src/frontend/components/tutorial/tutorialGuides.js) - Mémoire détaillée
   - Guide utilisateur beta : [GUIDE_UTILISATEUR_BETA.md](docs/GUIDE_UTILISATEUR_BETA.md) - **NOUVEAU**
   - Guide QA : [memory_progress_qa_guide.md](docs/qa/memory_progress_qa_guide.md) - **NOUVEAU**
   - Rapport d'implémentation : [ameliorations_memoire_15oct2025.md](reports/ameliorations_memoire_15oct2025.md)

**Impact** :
- ✅ Utilisateur voit progression en temps réel
- ✅ Comprend ce que fait la consolidation (tooltip + docs)
- ✅ Sait combien de temps ça prend (~30s-2min)
- ✅ Reçoit confirmation de succès (résumé final)
- ✅ Peut réessayer en cas d'erreur (bouton reste actif)

**Tests recommandés** :
- [ ] Créer 3 conversations (10 messages chacune)
- [ ] Cliquer "Consolider mémoire" dans Centre Mémoire
- [ ] Vérifier barre progression affiche "(1/3)", "(2/3)", "(3/3)"
- [ ] Vérifier message final : "✓ Consolidation terminée : 3 sessions, X items"
- [ ] Vérifier tooltip au survol bouton
- [ ] Tester responsive mobile (barre + tooltip)

**Référence complète** : [Guide QA - memory_progress_qa_guide.md](docs/qa/memory_progress_qa_guide.md) (10 scénarios de test)

---

### 🔧 Corrigé

#### Mémoire - Détection Questions Temporelles et Enrichissement Contexte

**Problème** : Anima ne pouvait pas répondre précisément aux questions temporelles ("Quel jour et à quelle heure avons-nous abordé ces sujets ?")

**Diagnostic** :
- ✅ Rappel des concepts récurrents fonctionnel avec timestamps
- ❌ Contexte temporel non enrichi pour questions explicites sur dates/heures
- ❌ Détection des questions temporelles absente

**Corrections apportées** :

1. **ChatService - Détection Questions Temporelles** ([service.py:1114-1128](src/backend/features/chat/service.py#L1114-L1128))
   - Ajout regex `_TEMPORAL_QUERY_RE` pour détecter les questions temporelles
   - Patterns : "quand", "quel jour", "quelle heure", "à quelle heure", "quelle date"
   - Support multilingue (FR/EN)

2. **ChatService - Enrichissement Contexte Historique** ([service.py:1130-1202](src/backend/features/chat/service.py#L1130-L1202))
   - Nouvelle fonction `_build_temporal_history_context()`
   - Récupération des 20 derniers messages du thread avec timestamps
   - Format : `**[15 oct à 3h08] Toi :** Aperçu du message...`
   - Injection dans le contexte RAG sous section "### Historique récent de cette conversation"

3. **ChatService - Intégration dans le flux RAG** ([service.py:1697-1709](src/backend/features/chat/service.py#L1697-L1709))
   - Détection automatique des questions temporelles
   - Enrichissement proactif du `recall_context` si détection positive
   - Fallback élégant si erreur

**Impact** :
- Anima peut maintenant répondre précisément avec dates et heures exactes
- Amélioration de la cohérence temporelle des réponses
- Meilleure exploitation de la mémoire à long terme

**Tests effectués** :
- [x] Tests unitaires créés (12 tests, 100% passés)
- [x] Détection questions temporelles FR/EN validée
- [x] Formatage dates en français validé ("15 oct à 3h08")
- [x] Workflow complet d'intégration testé
- [x] Backend démarre sans erreur
- [x] Code source vérifié et conforme

**Tests en production effectués** :
- [x] Question temporelle en production avec Anima ✅
- [x] Vérification logs `[TemporalQuery]` en conditions réelles ✅
- [x] Validation enrichissement avec 4 concepts consolidés ✅
- [ ] Test consolidation Memory Gardener avec authentification

**Résultat Test Production (2025-10-15 04:11)** :
- Question: "Quand avons-nous parlé de mon poème fondateur? (dates et heures précises)"
- Réponse Anima: "le 5 octobre à 14h32 et le 8 octobre à 09h15" ✅
- Log backend: `[TemporalHistory] Contexte enrichi: 20 messages + 4 concepts consolidés` ✅
- Performance: 4.84s total (recherche ChromaDB + LLM) ✅

**Documentation Tests** :
- [test_temporal_query.py](tests/backend/features/chat/test_temporal_query.py) - Suite de tests unitaires (12/12 passés)
- [test_results_temporal_memory_2025-10-15.md](reports/test_results_temporal_memory_2025-10-15.md) - Rapport tests unitaires
- [test_production_temporal_memory_2025-10-15.md](reports/test_production_temporal_memory_2025-10-15.md) - Rapport test production ✅

**Correction Post-Validation (Fix Bug 0 Concepts Consolidés)** :

4. **ChatService - Enrichissement avec Mémoire Consolidée** ([service.py:1159-1188](src/backend/features/chat/service.py#L1159-L1188))
   - Ajout recherche sémantique dans `emergence_knowledge` (ChromaDB)
   - Récupération des 5 concepts consolidés les plus pertinents
   - Extraction `timestamp`, `summary`, `type` depuis métadonnées
   - Format : `**[14 oct à 4h30] Mémoire (concept) :** Résumé...`

5. **ChatService - Fusion Chronologique** ([service.py:1190-1266](src/backend/features/chat/service.py#L1190-L1266))
   - Combinaison messages thread + concepts consolidés
   - Tri chronologique automatique (du plus ancien au plus récent)
   - Distinction visuelle thread vs. mémoire consolidée
   - Log: `[TemporalHistory] Contexte enrichi: X messages + Y concepts consolidés`

**Impact de la correction** :
- ✅ Questions temporelles fonctionnent aussi pour conversations archivées/consolidées
- ✅ Exemple: "Quand avons-nous parlé de mon poème fondateur?" → Dates précises même si archivé
- ✅ Vue chronologique complète (récent + ancien consolidé)

**Documentation Correction** :
- [fix_temporal_consolidated_memory_2025-10-15.md](reports/fix_temporal_consolidated_memory_2025-10-15.md) - Analyse et solution détaillée

---

#### Memory Gardener - Isolation User ID

**Problème** : Erreur lors de la consolidation mémoire : "user_id est obligatoire pour accéder aux threads"

**Correction** :

1. **MemoryGardener - Appel get_thread_any()** ([gardener.py:669-671](src/backend/features/memory/gardener.py#L669-L671))
   - Remplacement de `get_thread()` par `get_thread_any()`
   - Passage du paramètre `user_id` en kwarg
   - Fallback gracieux si user_id non disponible

**Impact** :
- Consolidation mémoire fonctionnelle
- Respect des règles d'isolation user_id
- Logs plus clairs en cas d'erreur

---

## [Non publié] - 2025-10-10

### 🔧 Corrigé

#### Cockpit - Tracking des Coûts LLM

**Problème** : Les coûts et tokens pour Gemini et Anthropic (Claude) étaient enregistrés à $0.00 avec 0 tokens, alors que les requêtes étaient bien effectuées.

**Diagnostic** :
- ✅ OpenAI : 101 entrées, $0.21, 213k tokens → Fonctionnel
- ❌ Gemini : 29 entrées, $0.00, 0 tokens → Défaillant
- ❌ Anthropic : 26 entrées, $0.00, 0 tokens → Défaillant

**Corrections apportées** :

1. **Gemini - Format count_tokens()** ([llm_stream.py:164-178](src/backend/features/chat/llm_stream.py#L164-L178))
   - Correction du format d'entrée (string concaténé au lieu de liste)
   - Ajout de logs détaillés avec `exc_info=True`
   - Même correction pour input et output tokens

2. **Anthropic - Logs détaillés** ([llm_stream.py:283-286](src/backend/features/chat/llm_stream.py#L283-L286))
   - Remplacement de `except Exception: pass` par des logs détaillés
   - Ajout de warnings si `usage` est absent
   - Stack trace complète des erreurs

3. **Tous les providers - Uniformisation des logs** ([llm_stream.py](src/backend/features/chat/llm_stream.py))
   - Logs détaillés pour OpenAI (lignes 139-144)
   - Logs détaillés pour Gemini (lignes 224-229)
   - Logs détaillés pour Anthropic (lignes 277-282)
   - Format uniforme : `[Provider] Cost calculated: $X.XXXXXX (model=XXX, input=XXX tokens, output=XXX tokens, pricing_input=$X.XXXXXXXX/token, pricing_output=$X.XXXXXXXX/token)`

**Impact** :
- Correction de la sous-estimation des coûts (~70% du volume réel)
- Meilleure traçabilité des coûts dans les logs
- Cockpit affiche désormais des valeurs réelles

**Documentation** :
- [COCKPIT_COSTS_FIX_FINAL.md](docs/cockpit/COCKPIT_COSTS_FIX_FINAL.md) - Guide complet des corrections
- [COCKPIT_ROADMAP_FIXED.md](docs/cockpit/COCKPIT_ROADMAP_FIXED.md) - Feuille de route complète
- [COCKPIT_GAP1_FIX_SUMMARY.md](docs/cockpit/COCKPIT_GAP1_FIX_SUMMARY.md) - Résumé Gap #1

**Tests requis** :
- [ ] Conversation avec Gemini (3 messages minimum)
- [ ] Conversation avec Claude (2 messages minimum)
- [ ] Vérification logs backend (`grep "Cost calculated"`)
- [ ] Vérification BDD (`python check_db_simple.py`)
- [ ] Vérification cockpit (Tokens > 0, Coûts > $0.00)

---

### 📝 Ajouté

#### Scripts de Diagnostic

1. **check_db_simple.py** - Analyse rapide de la base de données
   - Compte les messages, coûts, sessions, documents
   - Analyse les coûts par modèle
   - Détection automatique des problèmes (coûts à $0.00)
   - Affiche les 5 entrées de coûts les plus récentes

2. **check_cockpit_data.py** - Diagnostic complet du cockpit
   - Analyse par période (aujourd'hui, semaine, mois)
   - Détection spécifique des problèmes Gemini (Gap #1)
   - Calcul des tokens moyens par message
   - Résumé avec recommandations

**Usage** :
```bash
# Diagnostic rapide
python check_db_simple.py

# Diagnostic complet (nécessite UTF-8)
python check_cockpit_data.py
```

---

### 📚 Documentation

#### Cockpit - Guides Complets

1. **[COCKPIT_ROADMAP_FIXED.md](docs/cockpit/COCKPIT_ROADMAP_FIXED.md)**
   - État des lieux complet (85% fonctionnel)
   - 3 Gaps identifiés avec solutions détaillées
   - Plan d'action (Phase 0-3, 4h total)
   - Scripts de validation et tests E2E
   - Critères de succès mesurables

2. **[COCKPIT_GAP1_FIX_SUMMARY.md](docs/cockpit/COCKPIT_GAP1_FIX_SUMMARY.md)**
   - Résumé des corrections Gap #1 (logs améliorés)
   - Exemples de sortie de logs
   - Guide de validation étape par étape
   - Checklist de validation

3. **[COCKPIT_COSTS_FIX_FINAL.md](docs/cockpit/COCKPIT_COSTS_FIX_FINAL.md)**
   - Diagnostic complet du problème de coûts
   - Corrections détaillées (Gemini + Anthropic)
   - Guide de test et validation
   - Section debugging avec tests manuels
   - Tableau avant/après les corrections

4. **[COCKPIT_GAPS_AND_FIXES.md](docs/cockpit/COCKPIT_GAPS_AND_FIXES.md)** (existant)
   - Analyse initiale du cockpit
   - Backend infrastructure (85% opérationnel)
   - 3 Gaps critiques identifiés
   - Plan Sprint 0 Cockpit (1-2 jours)

---

## [1.0.0] - 2025-10-10 (Phase P1.2 + P0)

### 🚀 Déployé

**Révision** : `emergence-app-p1-p0-20251010-040147`
**Image Tag** : `p1-p0-20251010-040147`
**Statut** : ✅ Active (100%)

### Ajouté
- Préférences utilisateur persistées
- Consolidation threads archivés
- Queue async pour la mémoire

### Documentation
- [2025-10-10-deploy-p1-p0.md](docs/deployments/2025-10-10-deploy-p1-p0.md)

---

## [0.9.0] - 2025-10-09 (Phase P1 Mémoire)

### 🚀 Déployé

**Révision** : `emergence-app-p1memory`
**Image Tag** : `deploy-p1-20251009-094822`
**Statut** : ✅ Active (100%)

### Ajouté
- Queue async pour la mémoire
- Système de préférences utilisateur
- Instrumentation Prometheus pour mémoire

### Documentation
- [2025-10-09-deploy-p1-memory.md](docs/deployments/2025-10-09-deploy-p1-memory.md)

---

## [0.8.0] - 2025-10-09 (Cockpit Phase 3)

### 🚀 Déployé

**Révision** : `emergence-app-phase3b`
**Image Tag** : `cockpit-phase3-20251009-073931`
**Statut** : ✅ Active (100%)

### Corrigé
- Timeline SQL queries optimisées
- Cockpit Phase 3 redéployé

### Documentation
- [2025-10-09-deploy-cockpit-phase3.md](docs/deployments/2025-10-09-deploy-cockpit-phase3.md)

---

## [0.7.0] - 2025-10-09 (Prometheus Phase 3)

### 🚀 Déployé

**Révision** : `emergence-app-metrics001`
**Image Tag** : `deploy-20251008-183707`
**Statut** : ✅ Active (100%)

### Ajouté
- Activation `CONCEPT_RECALL_METRICS_ENABLED`
- Routage 100% Prometheus Phase 3
- Métriques Concept Recall

### Documentation
- [2025-10-09-activation-metrics-phase3.md](docs/deployments/2025-10-09-activation-metrics-phase3.md)

---

## [0.6.0] - 2025-10-08 (Phase 2 Performance)

### 🚀 Déployé

**Révision** : `emergence-app-00274-m4w`
**Image Tag** : `deploy-20251008-121131`
**Statut** : ⏸️ Archived

### Ajouté
- Neo analysis optimisé
- Cache mémoire amélioré
- Débats parallèles
- Health checks + métriques Prometheus

### Documentation
- [2025-10-08-cloud-run-revision-00274.md](docs/deployments/2025-10-08-cloud-run-revision-00274.md)

---

## [0.5.0] - 2025-10-08 (UI Fixes)

### 🚀 Déployé

**Révision** : `emergence-app-00270-zs6`
**Image Tag** : `deploy-20251008-082149`
**Statut** : ⏸️ Archived

### Corrigé
- Menu mobile confirmé
- Harmonisation UI cockpit/hymne

---

## [0.4.0] - 2025-10-06 (Agents & UI Refresh)

### 🚀 Déployé

**Révision** : `emergence-app-00268-9s8`
**Image Tag** : `deploy-20251006-060538`
**Statut** : ⏸️ Archived

### Ajouté
- Personnalités agents améliorées
- Module documentation
- Interface responsive

---

## [0.3.0] - 2025-10-05 (Audit Fixes)

### 🚀 Déployé

**Révision** : `emergence-app-00266-jc4`
**Image Tag** : `deploy-20251005-123837`
**Statut** : ⏸️ Archived

### Corrigé
- 13 corrections issues de l'audit
- Score qualité : 87.5 → 95/100

### Documentation
- [2025-10-05-audit-fixes-deployment.md](docs/deployments/)

---

## [0.2.0] - 2025-10-04 (Métriques & Settings)

### 🚀 Déployé

**Révision** : `emergence-app-00265-xxx`
**Image Tag** : `deploy-20251004-205347`
**Statut** : ⏸️ Archived

### Ajouté
- Système de métriques Prometheus
- Module Settings (préférences utilisateur)

---

## Légende

- 🚀 **Déployé** : Déployé en production (Cloud Run)
- 🔧 **Corrigé** : Corrections de bugs
- 📝 **Ajouté** : Nouvelles fonctionnalités
- 📚 **Documentation** : Mises à jour documentation
- ⚠️ **Déprécié** : Fonctionnalités dépréciées
- 🗑️ **Supprimé** : Fonctionnalités supprimées
- 🔒 **Sécurité** : Corrections de sécurité

---

## Versions à Venir

### [Prochainement] - Gap #2 : Métriques Prometheus Coûts

**Priorité** : P1
**Estimation** : 2-3 heures

**Objectifs** :
- Instrumenter `cost_tracker.py` avec métriques Prometheus
- Ajouter 7 métriques (Counter + Histogram + Gauge)
- Background task pour mise à jour des gauges (5 min)
- Configurer alertes Prometheus (budget dépassé)

**Référence** : [COCKPIT_ROADMAP_FIXED.md - Phase 2](docs/cockpit/COCKPIT_ROADMAP_FIXED.md#phase-2--métriques-prometheus-2-3-heures-)

---

### [Prochainement] - Gap #3 : Tests E2E Cockpit

**Priorité** : P2
**Estimation** : 30 minutes

**Objectifs** :
- Tests conversation complète (3 providers)
- Validation affichage cockpit
- Validation API `/api/dashboard/costs/summary`
- Tests seuils d'alerte (vert/jaune/rouge)

---

## Contributeurs

- Claude Code (Anthropic) - Assistant IA
- Équipe Emergence

---

**Dernière mise à jour** : 2025-10-10

