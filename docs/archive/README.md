# Archives — Documentation et Scripts Obsolètes

**Date de création** : 2025-10-18
**Auteur** : Claude Code (Sonnet 4.5)

---

## Objectif

Ce répertoire contient tous les fichiers obsolètes, temporaires ou redondants qui encombraient la racine du projet.

**Nettoyage effectué** : 2025-10-18
- **107 fichiers déplacés** de la racine vers les archives
- **9 fichiers temporaires supprimés**
- Racine nettoyée : 200+ fichiers → ~30 fichiers essentiels

---

## Structure

```
docs/archive/
├── 2025-10/                    ← Archives octobre 2025
│   ├── phase3/                 ← 8 fichiers PHASE3_*.md (RAG, Citations, Fixes)
│   ├── prompts/                ← 8 fichiers PROMPT_NEXT_SESSION_*.md
│   ├── deployment/             ← 8 anciens guides déploiement
│   ├── fixes/                  ← 10 correctifs ponctuels (PROD_FIX, SECURITY_FIX, etc.)
│   ├── handoffs/               ← 4 fichiers de passation inter-sessions
│   ├── html-tests/             ← 6 fichiers HTML de test/debug
│   ├── scripts-temp/           ← 40+ scripts Python/Bash/Batch temporaires
│   └── *.md                    ← 15 fichiers .md redondants/obsolètes
└── README.md                   ← Ce fichier
```

---

## Contenu par Catégorie

### Phase 3 (8 fichiers)
Documentation des fixes RAG et citations (octobre 2025) :
- `PHASE3_RAG_CHANGELOG.md`
- `PHASE3.1_CITATIONS_CHANGELOG.md`
- `PHASE3_CRITICAL_FIX.md`
- `PHASE3_FIX_V2.md`
- `PHASE3_FIX_V3_FINAL.md`
- `PHASE3_FIX_V4_CONTEXT_LIMIT.md`
- `PHASE3_RAG_FINAL_STATUS.md`
- `PHASE3_SUMMARY.md`

**État** : Obsolète - Phase 3 terminée et documentée dans CHANGELOG.md

---

### Prompts & Next Session (8 fichiers)
Prompts de planification pour sessions futures (obsolètes) :
- `PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md`
- `PROMPT_NEXT_SESSION_P1_FIXES.md`
- `PROMPT_NEXT_SESSION_CLEANUP.md`
- `NEXT_INSTANCE_PROMPT.md`
- `DEPLOY_P1_P0_PROMPT.md`
- `QUICK_START_NEXT_SESSION.md`
- `NEXT_SESSION_P2_4_TO_P2_9.md`
- `NEXT_SESSION_P1_AUDIT_CLEANUP.md`

**État** : Obsolète - Sessions terminées, planification intégrée dans ROADMAP_PROGRESS.md

---

### Handoffs (4 fichiers)
Passations inter-agents et cloud/local :
- `RESUME_SESSION_2025-10-15.md`
- `HANDOFF_AUDIT_20251010.txt`
- `HANDOFF_NEXT_SESSION.txt`
- `POUR_GPT_CODEX_CLOUD.md`

**État** : Obsolète - Remplacé par docs/passation.md et AGENT_SYNC.md

---

### Correctifs Ponctuels (10 fichiers)
Correctifs et fixes spécifiques (octobre 2025) :
- `PROD_FIX_2025-10-11.md`
- `SECURITY_FIX_2025-10-12.md`
- `CORRECTIONS_2025-10-10.md`
- `QUICKTEST_MEMORY_FIX.md`
- `DEPLOY_HOTFIX_DB_RECONNECT.md`
- `MOBILE_UI_FIXES.md`
- `MEMORY_AUDIT_FIXES.md`
- `WEBSOCKET_AUDIT_2025-10-11.md`
- `CLEANUP_PLAN_20251010.md`
- `AUTO_COMMIT_ACTIVATED.md`

**État** : Obsolète - Correctifs appliqués et documentés dans CHANGELOG.md

---

### Déploiement Obsolète (8 fichiers)
Anciens guides de déploiement (remplacés) :
- `DEPLOIEMENT.md`
- `DEPLOYMENT_QUICKSTART.md`
- `DEPLOYMENT_SUMMARY.md`
- `DEPLOYMENT_COMPLETE.md`
- `UPGRADE_NOTES.md`
- `CHANGELOG_UPGRADE.md`
- `PROD_MONITORING_SETUP_COMPLETE.md`
- `EMERGENCE_STATE_2025-10-11.md`

**État** : Obsolète - Remplacé par :
- `DEPLOYMENT_SUCCESS.md` (racine)
- `FIX_PRODUCTION_DEPLOYMENT.md` (racine)
- `CANARY_DEPLOYMENT.md` (racine)

---

### HTML de Test (6 fichiers)
Pages HTML temporaires pour tests/debug :
- `beta_invitations.html`
- `check_jwt_token.html`
- `onboarding.html`
- `request-password-reset.html`
- `reset-password.html`
- `sync-dashboard.html`

**État** : Obsolète - Tests intégrés dans l'interface principale (index.html)

---

### Scripts Temporaires (40+ fichiers)

**Scripts de test** (16 fichiers) :
- `test_anima_context.py`
- `test_archived_memory_fix.py`
- `test_beta_invitation.py`
- `test_beta_invitations.py`
- `test_beta_router.py`
- `test_costs_fix.py`
- `test_costs_simple.py`
- `test_email_sending.py`
- `test_email_simple.py`
- `test_email_smtp.py`
- `test_isolation.py`
- `test_session_timeout.py`
- `test_session_timeout_quick.py`
- `test_token.py`
- `test_token_final.py`
- `test_token_v2.py`

**Scripts utilitaires DB/Auth** (7 fichiers) :
- `add_password_must_reset_column.py`
- `check_db.py`
- `check_db_schema.py`
- `check_db_simple.py`
- `check_cockpit_data.py`
- `disable_password_reset_for_admin.py`
- `fix_admin_role.py`

**Scripts Beta/Email** (2 fichiers) :
- `fetch_allowlist_emails.py`
- `send_beta_invitations.py`

**Scripts Mémoire** (3 fichiers) :
- `consolidate_all_archives.py`
- `consolidate_archives_manual.py`
- `check_archived_threads.py`

**Scripts Test/QA** (3 fichiers) :
- `qa_metrics_validation.py`
- `inject_test_messages.py`
- `generate_phase3_report.py`

**Scripts Déploiement** (3 fichiers) :
- `deploy_auth_fixes.sh`
- `cleanup.sh`
- `revoke_all_sessions.sh`

**Scripts Batch** (3 fichiers) :
- `envoyer_invitations_beta.bat`
- `ouvrir_interface_invitations.bat`
- `run_memory_validation.bat`

**Scripts PowerShell** (2 fichiers) :
- `progressive-deploy.ps1`
- `test-canary.ps1`

**État** : Obsolète - Scripts ponctuels déjà exécutés ou remplacés par des tests automatisés

---

### Documentation Redondante (15 fichiers)
Fichiers .md obsolètes ou redondants :
- `CODex_GUIDE.md` (ancien, remplacé par CODEX_GPT_GUIDE.md)
- `AGENT_SYNC_ADDENDUM.md` (fusionné dans AGENT_SYNC.md)
- `FONCTIONNEMENT_AUTO_SYNC.md` (obsolète)
- `ORCHESTRATEUR_IMPLEMENTATION.md`
- `AUDIT_COMPLET_EMERGENCE_V8_20251010.md`
- `INTEGRATION.md`
- `INTEGRATION_TESTS.md`
- `IMPLEMENTATION_PHASES_3_4.md`
- `FINAL_SUMMARY.md`
- `TESTING.md`
- `TEST_README.md`
- `MICROSERVICES_MIGRATION_P2_RECAP.md`
- `START_HERE.md` (info dans README.md)
- `SETUP_COMPLETE.md`
- `RAPPORT_TEST_MEMOIRE_ARCHIVEE.md`

**État** : Obsolète - Info intégrée dans documentation principale

---

## Fichiers Conservés à la Racine (Essentiels)

**Documentation Principale** :
- `README.md` - Doc projet
- `CLAUDE.md` - **Prompt principal Claude Code**
- `AGENT_SYNC.md` - État sync inter-agents
- `AGENTS.md` - Consignes agents
- `CODEV_PROTOCOL.md` - Protocole multi-agents
- `CHANGELOG.md` - Historique versions
- `ROADMAP_OFFICIELLE.md` - Roadmap unique
- `ROADMAP_PROGRESS.md` - Suivi progression
- `MEMORY_REFACTORING_ROADMAP.md` - Roadmap mémoire (actif)

**Guides Opérationnels** :
- `DEPLOYMENT_SUCCESS.md` - État déploiement
- `FIX_PRODUCTION_DEPLOYMENT.md` - Guide résolution
- `CANARY_DEPLOYMENT.md` - Procédure canary
- `GUARDIAN_SETUP_COMPLETE.md` - Setup Guardians
- `GUIDE_INTERFACE_BETA.md` - Guide interface
- `CONTRIBUTING.md` - Guide contribution

**Guides Agents** :
- `CLAUDE_CODE_GUIDE.md` - Guide Claude Code
- `CODEX_GPT_GUIDE.md` - Guide Codex GPT

**Configuration & Build** :
- `package.json`, `requirements.txt`
- `Dockerfile`, `docker-compose.yaml`
- `stable-service.yaml`, `canary-service.yaml`
- `index.html` - Point d'entrée app

**Scripts Actifs** :
- `apply_migration_conversation_id.py` - Migration récente (2025-10-18)
- `check_db_status.py` - Vérification DB (2025-10-18)

---

## Fichiers Déplacés vers docs/ (Actifs)

**Documentation Beta** (`docs/beta/`) :
- `BETA_QUICK_START.md`
- `BETA_INVITATIONS_SUMMARY.md`
- `COMMENT_ENVOYER_INVITATIONS.md`
- `README_BETA_INVITATIONS.md`

**Documentation Auth** (`docs/auth/`) :
- `PASSWORD_RESET_IMPLEMENTATION.md`

**Documentation Onboarding** (`docs/onboarding/`) :
- `ONBOARDING_IMPLEMENTATION.md`

---

## Politique de Rétention

**Archivage** :
- Les fichiers archivés sont conservés pour référence historique
- Pas de suppression prévue (faible poids : ~5 MB total)

**Consultation** :
- Si besoin de consulter un ancien fix/script, chercher dans `docs/archive/2025-10/`
- Structure organisée par catégorie pour retrouver facilement

**Nettoyage futur** :
- Archiver les fichiers obsolètes dans `docs/archive/YYYY-MM/` par mois
- Garder au maximum 6 mois d'archives (supprimer au-delà si nécessaire)

---

## Historique des Nettoyages

### 2025-10-18 - Grand Nettoyage Racine
- **Auteur** : Claude Code (Sonnet 4.5)
- **Raison** : Racine encombrée (200+ fichiers)
- **Actions** :
  - 107 fichiers déplacés vers archives
  - 9 fichiers temporaires supprimés
  - Structure d'archivage créée (2025-10/)
  - Documentation organisée (beta/, auth/, onboarding/)
- **Résultat** : Racine nettoyée → 30 fichiers essentiels
- **Script** : `scripts/cleanup_root.py`
- **Plan** : `CLEANUP_PLAN_2025-10-18.md` (racine)

---

**Prochains nettoyages** : Prévoir archivage mensuel automatisé via script Guardian
