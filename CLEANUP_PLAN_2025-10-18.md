# Plan de Nettoyage Racine — 2025-10-18

**Objectif** : Nettoyer le bordel dans le répertoire racine (200+ fichiers → ~30 essentiels)

---

## 📊 État Actuel

- **74 fichiers .md** dans la racine
- **17 scripts test_*.py** dans la racine
- **7 fichiers HTML** de test/debug
- **20+ scripts utilitaires** temporaires (check_*.py, fix_*.py, etc.)
- **Dossiers bizarres** : C:devemergenceV8.* (corrupted paths)

---

## 🗂️ Structure d'Archivage

```
docs/archive/
├── 2025-10/           ← Archives octobre 2025
│   ├── phase3/        ← Tous les fichiers PHASE3_*.md
│   ├── prompts/       ← Tous les PROMPT_*.md
│   ├── deployment/    ← Anciens guides déploiement
│   ├── fixes/         ← Correctifs ponctuels (PROD_FIX, SECURITY_FIX, etc.)
│   └── handoffs/      ← HANDOFF_*.txt, RESUME_*.md
├── scripts-temp/      ← Scripts temporaires à archiver
└── html-tests/        ← Fichiers HTML de test
```

---

## 🟢 FICHIERS À GARDER (Essentiels - ~30 fichiers)

### Documentation Principale
- ✅ `README.md` - Doc principale
- ✅ `CLAUDE.md` - Config Claude Code (PROMPT PRINCIPAL!)
- ✅ `AGENT_SYNC.md` - État sync inter-agents
- ✅ `AGENTS.md` - Consignes agents
- ✅ `CODEV_PROTOCOL.md` - Protocole multi-agents
- ✅ `CHANGELOG.md` - Historique versions
- ✅ `ROADMAP_OFFICIELLE.md` - Roadmap unique
- ✅ `ROADMAP_PROGRESS.md` - Suivi progression
- ✅ `MEMORY_REFACTORING_ROADMAP.md` - Roadmap mémoire (actif)

### Guides Opérationnels Actifs
- ✅ `DEPLOYMENT_SUCCESS.md` - État déploiement
- ✅ `FIX_PRODUCTION_DEPLOYMENT.md` - Guide résolution
- ✅ `CANARY_DEPLOYMENT.md` - Procédure canary
- ✅ `GUARDIAN_SETUP_COMPLETE.md` - Setup Guardians
- ✅ `GUIDE_INTERFACE_BETA.md` - Guide interface
- ✅ `CONTRIBUTING.md` - Guide contribution

### Guides Agents Actifs
- ✅ `CLAUDE_CODE_GUIDE.md` - Guide Claude Code
- ✅ `CODEX_GPT_GUIDE.md` - Guide Codex GPT

### Configuration & Build
- ✅ `package.json`, `package-lock.json`
- ✅ `requirements.txt`
- ✅ `Dockerfile`, `docker-compose.yaml`
- ✅ `stable-service.yaml`, `canary-service.yaml`
- ✅ `index.html` - Point d'entrée app

### Scripts Actifs
- ✅ `apply_migration_conversation_id.py` - Migration récente (2025-10-18)
- ✅ `check_db_status.py` - Vérification DB (2025-10-18)

---

## 🔴 FICHIERS À ARCHIVER (Obsolètes ou temporaires)

### Phase 3 (7 fichiers - tous obsolètes)
- 📦 `PHASE3_RAG_CHANGELOG.md` → `docs/archive/2025-10/phase3/`
- 📦 `PHASE3.1_CITATIONS_CHANGELOG.md` → `docs/archive/2025-10/phase3/`
- 📦 `PHASE3_CRITICAL_FIX.md` → `docs/archive/2025-10/phase3/`
- 📦 `PHASE3_FIX_V2.md` → `docs/archive/2025-10/phase3/`
- 📦 `PHASE3_FIX_V3_FINAL.md` → `docs/archive/2025-10/phase3/`
- 📦 `PHASE3_FIX_V4_CONTEXT_LIMIT.md` → `docs/archive/2025-10/phase3/`
- 📦 `PHASE3_RAG_FINAL_STATUS.md` → `docs/archive/2025-10/phase3/`
- 📦 `PHASE3_SUMMARY.md` → `docs/archive/2025-10/phase3/`

### Prompts & Next Session (12 fichiers)
- 📦 `PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md` → `docs/archive/2025-10/prompts/`
- 📦 `PROMPT_NEXT_SESSION_P1_FIXES.md` → `docs/archive/2025-10/prompts/`
- 📦 `PROMPT_NEXT_SESSION_CLEANUP.md` → `docs/archive/2025-10/prompts/`
- 📦 `NEXT_INSTANCE_PROMPT.md` → `docs/archive/2025-10/prompts/`
- 📦 `DEPLOY_P1_P0_PROMPT.md` → `docs/archive/2025-10/prompts/`
- 📦 `QUICK_START_NEXT_SESSION.md` → `docs/archive/2025-10/prompts/`
- 📦 `NEXT_SESSION_P2_4_TO_P2_9.md` → `docs/archive/2025-10/prompts/`
- 📦 `NEXT_SESSION_P1_AUDIT_CLEANUP.md` → `docs/archive/2025-10/prompts/`
- 📦 `RESUME_SESSION_2025-10-15.md` → `docs/archive/2025-10/handoffs/`
- 📦 `HANDOFF_AUDIT_20251010.txt` → `docs/archive/2025-10/handoffs/`
- 📦 `HANDOFF_NEXT_SESSION.txt` → `docs/archive/2025-10/handoffs/`
- 📦 `POUR_GPT_CODEX_CLOUD.md` → `docs/archive/2025-10/handoffs/`

### Correctifs Ponctuels (10 fichiers)
- 📦 `PROD_FIX_2025-10-11.md` → `docs/archive/2025-10/fixes/`
- 📦 `SECURITY_FIX_2025-10-12.md` → `docs/archive/2025-10/fixes/`
- 📦 `CORRECTIONS_2025-10-10.md` → `docs/archive/2025-10/fixes/`
- 📦 `QUICKTEST_MEMORY_FIX.md` → `docs/archive/2025-10/fixes/`
- 📦 `DEPLOY_HOTFIX_DB_RECONNECT.md` → `docs/archive/2025-10/fixes/`
- 📦 `MOBILE_UI_FIXES.md` → `docs/archive/2025-10/fixes/`
- 📦 `MEMORY_AUDIT_FIXES.md` → `docs/archive/2025-10/fixes/`
- 📦 `WEBSOCKET_AUDIT_2025-10-11.md` → `docs/archive/2025-10/fixes/`
- 📦 `CLEANUP_PLAN_20251010.md` → `docs/archive/2025-10/fixes/`
- 📦 `AUTO_COMMIT_ACTIVATED.md` → `docs/archive/2025-10/fixes/`

### Déploiement Obsolète (8 fichiers)
- 📦 `DEPLOIEMENT.md` → `docs/archive/2025-10/deployment/`
- 📦 `DEPLOYMENT_QUICKSTART.md` → `docs/archive/2025-10/deployment/`
- 📦 `DEPLOYMENT_SUMMARY.md` → `docs/archive/2025-10/deployment/`
- 📦 `DEPLOYMENT_COMPLETE.md` → `docs/archive/2025-10/deployment/`
- 📦 `UPGRADE_NOTES.md` → `docs/archive/2025-10/deployment/`
- 📦 `CHANGELOG_UPGRADE.md` → `docs/archive/2025-10/deployment/`
- 📦 `PROD_MONITORING_SETUP_COMPLETE.md` → `docs/archive/2025-10/deployment/`
- 📦 `EMERGENCE_STATE_2025-10-11.md` → `docs/archive/2025-10/deployment/`

### Documentation Redondante/Obsolète (15 fichiers)
- 📦 `CODex_GUIDE.md` (ancien, remplacé par CODEX_GPT_GUIDE.md)
- 📦 `AGENT_SYNC_ADDENDUM.md` (fusionné dans AGENT_SYNC.md)
- 📦 `FONCTIONNEMENT_AUTO_SYNC.md` (obsolète)
- 📦 `ORCHESTRATEUR_IMPLEMENTATION.md` → `docs/archive/2025-10/`
- 📦 `AUDIT_COMPLET_EMERGENCE_V8_20251010.md` → `docs/archive/2025-10/`
- 📦 `INTEGRATION.md` → `docs/archive/2025-10/`
- 📦 `INTEGRATION_TESTS.md` → `docs/archive/2025-10/`
- 📦 `IMPLEMENTATION_PHASES_3_4.md` → `docs/archive/2025-10/`
- 📦 `FINAL_SUMMARY.md` → `docs/archive/2025-10/`
- 📦 `TESTING.md` → `docs/archive/2025-10/`
- 📦 `TEST_README.md` → `docs/archive/2025-10/`
- 📦 `MICROSERVICES_MIGRATION_P2_RECAP.md` → `docs/archive/2025-10/`
- 📦 `START_HERE.md` (obsolète, info dans README.md)
- 📦 `SETUP_COMPLETE.md` (fichier créé aujourd'hui mais déjà obsolète)
- 📦 `RAPPORT_TEST_MEMOIRE_ARCHIVEE.md` → `docs/archive/2025-10/`

### Beta/Onboarding (6 fichiers - à déplacer vers docs/)
- 📦 `BETA_QUICK_START.md` → `docs/beta/`
- 📦 `BETA_INVITATIONS_SUMMARY.md` → `docs/beta/`
- 📦 `COMMENT_ENVOYER_INVITATIONS.md` → `docs/beta/`
- 📦 `README_BETA_INVITATIONS.md` → `docs/beta/`
- 📦 `PASSWORD_RESET_IMPLEMENTATION.md` → `docs/auth/`
- 📦 `ONBOARDING_IMPLEMENTATION.md` → `docs/onboarding/`

### Changelogs Redondants (1 fichier)
- 📦 `CHANGELOG_PASSWORD_RESET_2025-10-12.md` → `docs/archive/2025-10/`

---

## 🔴 FICHIERS HTML À ARCHIVER (6 fichiers)

- 📦 `beta_invitations.html` → `docs/archive/2025-10/html-tests/`
- 📦 `check_jwt_token.html` → `docs/archive/2025-10/html-tests/`
- 📦 `onboarding.html` → `docs/archive/2025-10/html-tests/`
- 📦 `request-password-reset.html` → `docs/archive/2025-10/html-tests/`
- 📦 `reset-password.html` → `docs/archive/2025-10/html-tests/`
- 📦 `sync-dashboard.html` → `docs/archive/2025-10/html-tests/`

**Note** : `index.html` reste à la racine (point d'entrée app)

---

## 🔴 SCRIPTS TEST À DÉPLACER/SUPPRIMER (17 fichiers)

### Tests Unitaires → Déplacer vers /tests/scripts/
- 📦 `test_phase1_validation.py` → Garder dans `/tests/validation/`
- 📦 `test_phase3_validation.py` → Garder dans `/tests/validation/`

### Tests Temporaires → Archiver (15 fichiers)
- 🗑️ `test_anima_context.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_archived_memory_fix.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_beta_invitation.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_beta_invitations.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_beta_router.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_costs_fix.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_costs_simple.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_email_sending.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_email_simple.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_email_smtp.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_isolation.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_session_timeout.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_session_timeout_quick.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_token.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_token_final.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `test_token_v2.py` → `docs/archive/2025-10/scripts-temp/`

---

## 🔴 SCRIPTS UTILITAIRES À ARCHIVER (20+ fichiers)

### Scripts DB/Auth Temporaires
- 🗑️ `add_password_must_reset_column.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `check_db.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `check_db_schema.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `check_db_simple.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `check_cockpit_data.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `disable_password_reset_for_admin.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `fix_admin_role.py` → `docs/archive/2025-10/scripts-temp/`

### Scripts Beta/Email Temporaires
- 🗑️ `fetch_allowlist_emails.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `send_beta_invitations.py` → `docs/archive/2025-10/scripts-temp/`

### Scripts Mémoire Temporaires
- 🗑️ `consolidate_all_archives.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `consolidate_archives_manual.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `check_archived_threads.py` → `docs/archive/2025-10/scripts-temp/`

### Scripts Test/QA Temporaires
- 🗑️ `qa_metrics_validation.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `inject_test_messages.py` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `generate_phase3_report.py` → `docs/archive/2025-10/scripts-temp/`

### Scripts Déploiement Temporaires
- 🗑️ `deploy_auth_fixes.sh` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `cleanup.sh` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `revoke_all_sessions.sh` → `docs/archive/2025-10/scripts-temp/`

---

## 🔴 FICHIERS BATCH À ARCHIVER (3 fichiers)

- 🗑️ `envoyer_invitations_beta.bat` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `ouvrir_interface_invitations.bat` → `docs/archive/2025-10/scripts-temp/`
- 🗑️ `run_memory_validation.bat` → `docs/archive/2025-10/scripts-temp/`

---

## 🔴 FICHIERS TEMPORAIRES À SUPPRIMER

### Données Temporaires
- 🗑️ `downloaded-logs-20251010-041801.json` (363 KB - logs téléchargés)
- 🗑️ `tmp-auth.db` (126 KB - DB temporaire)
- 🗑️ `concepts_report.json` (338 bytes)
- 🗑️ `qa-p1-baseline.json` (1.3 KB)
- 🗑️ `build_tag.txt`, `BUILDSTAMP.txt`
- 🗑️ `nul` (fichier vide bizarre)
- 🗑️ `beta_testers_emails.txt` (contenu sensible? à vérifier avant suppression)

### Fichiers Arborescence
- 🗑️ `arborescence_synchronisee_20251008.txt` (4 MB !)

### Fichiers Révisions
- 🗑️ `revisions_to_delete.txt`

---

## 🔴 DOSSIERS CORROMPUS À SUPPRIMER

- 🗑️ `C:devemergenceV8.synclogs/`
- 🗑️ `C:devemergenceV8.syncpatches/`
- 🗑️ `C:devemergenceV8.syncscripts/`
- 🗑️ `C:devemergenceV8.synctemplates/`

**Cause** : Chemins Windows mal échappés dans script sync

---

## 📝 FICHIERS À REVOIR (Cas spéciaux)

### PowerShell Scripts
- ⚠️ `scripts/deploy-canary.ps1` - À GARDER (déploiement actif)
- ⚠️ `scripts/run-backend.ps1` - À GARDER (dev local)
- ⚠️ `progressive-deploy.ps1` - À archiver (obsolète si deploy-canary actif)
- ⚠️ `test-canary.ps1` - À archiver (test ponctuel)

---

## ✅ RÉSULTAT ATTENDU

### Fichiers Racine (27 fichiers essentiels)
```
emergenceV8/
├── README.md
├── CLAUDE.md                    ← PROMPT PRINCIPAL CLAUDE CODE
├── AGENT_SYNC.md
├── AGENTS.md
├── CODEV_PROTOCOL.md
├── CHANGELOG.md
├── ROADMAP_OFFICIELLE.md
├── ROADMAP_PROGRESS.md
├── MEMORY_REFACTORING_ROADMAP.md
├── DEPLOYMENT_SUCCESS.md
├── FIX_PRODUCTION_DEPLOYMENT.md
├── CANARY_DEPLOYMENT.md
├── GUARDIAN_SETUP_COMPLETE.md
├── GUIDE_INTERFACE_BETA.md
├── CONTRIBUTING.md
├── CLAUDE_CODE_GUIDE.md
├── CODEX_GPT_GUIDE.md
├── package.json
├── package-lock.json
├── requirements.txt
├── Dockerfile
├── docker-compose.yaml
├── stable-service.yaml
├── canary-service.yaml
├── index.html
├── apply_migration_conversation_id.py
└── check_db_status.py
```

### Répertoires Propres
```
emergenceV8/
├── docs/
│   ├── archive/
│   │   └── 2025-10/        ← Tout l'ancien bordel
│   ├── beta/               ← Docs beta consolidées
│   ├── auth/               ← Docs auth
│   └── onboarding/         ← Docs onboarding
├── tests/
│   ├── validation/
│   │   ├── test_phase1_validation.py
│   │   └── test_phase3_validation.py
│   └── ...
└── scripts/
    └── (scripts actifs uniquement)
```

---

## 🚀 COMMANDES D'EXÉCUTION

### 1. Créer structure d'archivage
```bash
mkdir -p docs/archive/2025-10/{phase3,prompts,deployment,fixes,handoffs,html-tests,scripts-temp}
mkdir -p docs/{beta,auth,onboarding}
mkdir -p tests/validation
```

### 2. Déplacer fichiers (automatisé via script)
```bash
# Script Python pour déplacer tous les fichiers selon le plan
python scripts/cleanup_root.py --execute
```

### 3. Supprimer dossiers corrompus
```bash
rm -rf "C:devemergenceV8."*
```

### 4. Nettoyer fichiers temporaires
```bash
rm -f downloaded-logs-*.json tmp-auth.db *.json build_tag.txt BUILDSTAMP.txt nul revisions_to_delete.txt arborescence_*.txt
```

---

## ⚠️ VALIDATION AVANT EXÉCUTION

- [ ] Sauvegarder le dépôt complet (`git stash` + `git push`)
- [ ] Vérifier qu'aucun fichier essentiel n'est marqué pour suppression
- [ ] Confirmer que les fichiers `CLAUDE.md`, `AGENT_SYNC.md`, `AGENTS.md` restent à la racine
- [ ] Tester après nettoyage : `npm run build` + `pytest`

---

**Prêt à exécuter le nettoyage ?**
