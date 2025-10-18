#!/usr/bin/env python3
"""
Script de nettoyage du répertoire racine - 2025-10-18
Déplace les fichiers obsolètes vers docs/archive/2025-10/
"""

import os
import shutil
from pathlib import Path

# Répertoire racine du projet
ROOT = Path(__file__).parent.parent

# Dictionnaire: fichier source → destination relative à ROOT
MOVES = {
    # Phase 3 (8 fichiers)
    "PHASE3_RAG_CHANGELOG.md": "docs/archive/2025-10/phase3/",
    "PHASE3.1_CITATIONS_CHANGELOG.md": "docs/archive/2025-10/phase3/",
    "PHASE3_CRITICAL_FIX.md": "docs/archive/2025-10/phase3/",
    "PHASE3_FIX_V2.md": "docs/archive/2025-10/phase3/",
    "PHASE3_FIX_V3_FINAL.md": "docs/archive/2025-10/phase3/",
    "PHASE3_FIX_V4_CONTEXT_LIMIT.md": "docs/archive/2025-10/phase3/",
    "PHASE3_RAG_FINAL_STATUS.md": "docs/archive/2025-10/phase3/",
    "PHASE3_SUMMARY.md": "docs/archive/2025-10/phase3/",

    # Prompts & Next Session (12 fichiers)
    "PROMPT_NEXT_SESSION_AUDIT_FIXES_P0.md": "docs/archive/2025-10/prompts/",
    "PROMPT_NEXT_SESSION_P1_FIXES.md": "docs/archive/2025-10/prompts/",
    "PROMPT_NEXT_SESSION_CLEANUP.md": "docs/archive/2025-10/prompts/",
    "NEXT_INSTANCE_PROMPT.md": "docs/archive/2025-10/prompts/",
    "DEPLOY_P1_P0_PROMPT.md": "docs/archive/2025-10/prompts/",
    "QUICK_START_NEXT_SESSION.md": "docs/archive/2025-10/prompts/",
    "NEXT_SESSION_P2_4_TO_P2_9.md": "docs/archive/2025-10/prompts/",
    "NEXT_SESSION_P1_AUDIT_CLEANUP.md": "docs/archive/2025-10/prompts/",
    "RESUME_SESSION_2025-10-15.md": "docs/archive/2025-10/handoffs/",
    "HANDOFF_AUDIT_20251010.txt": "docs/archive/2025-10/handoffs/",
    "HANDOFF_NEXT_SESSION.txt": "docs/archive/2025-10/handoffs/",
    "POUR_GPT_CODEX_CLOUD.md": "docs/archive/2025-10/handoffs/",

    # Correctifs Ponctuels (10 fichiers)
    "PROD_FIX_2025-10-11.md": "docs/archive/2025-10/fixes/",
    "SECURITY_FIX_2025-10-12.md": "docs/archive/2025-10/fixes/",
    "CORRECTIONS_2025-10-10.md": "docs/archive/2025-10/fixes/",
    "QUICKTEST_MEMORY_FIX.md": "docs/archive/2025-10/fixes/",
    "DEPLOY_HOTFIX_DB_RECONNECT.md": "docs/archive/2025-10/fixes/",
    "MOBILE_UI_FIXES.md": "docs/archive/2025-10/fixes/",
    "MEMORY_AUDIT_FIXES.md": "docs/archive/2025-10/fixes/",
    "WEBSOCKET_AUDIT_2025-10-11.md": "docs/archive/2025-10/fixes/",
    "CLEANUP_PLAN_20251010.md": "docs/archive/2025-10/fixes/",
    "AUTO_COMMIT_ACTIVATED.md": "docs/archive/2025-10/fixes/",

    # Déploiement Obsolète (8 fichiers)
    "DEPLOIEMENT.md": "docs/archive/2025-10/deployment/",
    "DEPLOYMENT_QUICKSTART.md": "docs/archive/2025-10/deployment/",
    "DEPLOYMENT_SUMMARY.md": "docs/archive/2025-10/deployment/",
    "DEPLOYMENT_COMPLETE.md": "docs/archive/2025-10/deployment/",
    "UPGRADE_NOTES.md": "docs/archive/2025-10/deployment/",
    "CHANGELOG_UPGRADE.md": "docs/archive/2025-10/deployment/",
    "PROD_MONITORING_SETUP_COMPLETE.md": "docs/archive/2025-10/deployment/",
    "EMERGENCE_STATE_2025-10-11.md": "docs/archive/2025-10/deployment/",

    # Documentation Redondante/Obsolète (15 fichiers)
    "CODex_GUIDE.md": "docs/archive/2025-10/",
    "AGENT_SYNC_ADDENDUM.md": "docs/archive/2025-10/",
    "FONCTIONNEMENT_AUTO_SYNC.md": "docs/archive/2025-10/",
    "ORCHESTRATEUR_IMPLEMENTATION.md": "docs/archive/2025-10/",
    "AUDIT_COMPLET_EMERGENCE_V8_20251010.md": "docs/archive/2025-10/",
    "INTEGRATION.md": "docs/archive/2025-10/",
    "INTEGRATION_TESTS.md": "docs/archive/2025-10/",
    "IMPLEMENTATION_PHASES_3_4.md": "docs/archive/2025-10/",
    "FINAL_SUMMARY.md": "docs/archive/2025-10/",
    "TESTING.md": "docs/archive/2025-10/",
    "TEST_README.md": "docs/archive/2025-10/",
    "MICROSERVICES_MIGRATION_P2_RECAP.md": "docs/archive/2025-10/",
    "START_HERE.md": "docs/archive/2025-10/",
    "SETUP_COMPLETE.md": "docs/archive/2025-10/",
    "RAPPORT_TEST_MEMOIRE_ARCHIVEE.md": "docs/archive/2025-10/",

    # Beta/Onboarding (6 fichiers)
    "BETA_QUICK_START.md": "docs/beta/",
    "BETA_INVITATIONS_SUMMARY.md": "docs/beta/",
    "COMMENT_ENVOYER_INVITATIONS.md": "docs/beta/",
    "README_BETA_INVITATIONS.md": "docs/beta/",
    "PASSWORD_RESET_IMPLEMENTATION.md": "docs/auth/",
    "ONBOARDING_IMPLEMENTATION.md": "docs/onboarding/",

    # Changelogs Redondants
    "CHANGELOG_PASSWORD_RESET_2025-10-12.md": "docs/archive/2025-10/",

    # HTML (6 fichiers)
    "beta_invitations.html": "docs/archive/2025-10/html-tests/",
    "check_jwt_token.html": "docs/archive/2025-10/html-tests/",
    "onboarding.html": "docs/archive/2025-10/html-tests/",
    "request-password-reset.html": "docs/archive/2025-10/html-tests/",
    "reset-password.html": "docs/archive/2025-10/html-tests/",
    "sync-dashboard.html": "docs/archive/2025-10/html-tests/",

    # Scripts test temporaires (15 fichiers)
    "test_anima_context.py": "docs/archive/2025-10/scripts-temp/",
    "test_archived_memory_fix.py": "docs/archive/2025-10/scripts-temp/",
    "test_beta_invitation.py": "docs/archive/2025-10/scripts-temp/",
    "test_beta_invitations.py": "docs/archive/2025-10/scripts-temp/",
    "test_beta_router.py": "docs/archive/2025-10/scripts-temp/",
    "test_costs_fix.py": "docs/archive/2025-10/scripts-temp/",
    "test_costs_simple.py": "docs/archive/2025-10/scripts-temp/",
    "test_email_sending.py": "docs/archive/2025-10/scripts-temp/",
    "test_email_simple.py": "docs/archive/2025-10/scripts-temp/",
    "test_email_smtp.py": "docs/archive/2025-10/scripts-temp/",
    "test_isolation.py": "docs/archive/2025-10/scripts-temp/",
    "test_session_timeout.py": "docs/archive/2025-10/scripts-temp/",
    "test_session_timeout_quick.py": "docs/archive/2025-10/scripts-temp/",
    "test_token.py": "docs/archive/2025-10/scripts-temp/",
    "test_token_final.py": "docs/archive/2025-10/scripts-temp/",
    "test_token_v2.py": "docs/archive/2025-10/scripts-temp/",

    # Scripts utilitaires temporaires (20+ fichiers)
    "add_password_must_reset_column.py": "docs/archive/2025-10/scripts-temp/",
    "check_db.py": "docs/archive/2025-10/scripts-temp/",
    "check_db_schema.py": "docs/archive/2025-10/scripts-temp/",
    "check_db_simple.py": "docs/archive/2025-10/scripts-temp/",
    "check_cockpit_data.py": "docs/archive/2025-10/scripts-temp/",
    "disable_password_reset_for_admin.py": "docs/archive/2025-10/scripts-temp/",
    "fix_admin_role.py": "docs/archive/2025-10/scripts-temp/",
    "fetch_allowlist_emails.py": "docs/archive/2025-10/scripts-temp/",
    "send_beta_invitations.py": "docs/archive/2025-10/scripts-temp/",
    "consolidate_all_archives.py": "docs/archive/2025-10/scripts-temp/",
    "consolidate_archives_manual.py": "docs/archive/2025-10/scripts-temp/",
    "check_archived_threads.py": "docs/archive/2025-10/scripts-temp/",
    "qa_metrics_validation.py": "docs/archive/2025-10/scripts-temp/",
    "inject_test_messages.py": "docs/archive/2025-10/scripts-temp/",
    "generate_phase3_report.py": "docs/archive/2025-10/scripts-temp/",
    "deploy_auth_fixes.sh": "docs/archive/2025-10/scripts-temp/",
    "cleanup.sh": "docs/archive/2025-10/scripts-temp/",
    "revoke_all_sessions.sh": "docs/archive/2025-10/scripts-temp/",

    # Fichiers batch (3 fichiers)
    "envoyer_invitations_beta.bat": "docs/archive/2025-10/scripts-temp/",
    "ouvrir_interface_invitations.bat": "docs/archive/2025-10/scripts-temp/",
    "run_memory_validation.bat": "docs/archive/2025-10/scripts-temp/",

    # PowerShell à archiver
    "progressive-deploy.ps1": "docs/archive/2025-10/scripts-temp/",
    "test-canary.ps1": "docs/archive/2025-10/scripts-temp/",

    # Tests de validation à déplacer vers /tests/validation
    "test_phase1_validation.py": "tests/validation/",
    "test_phase3_validation.py": "tests/validation/",
}

# Fichiers à supprimer (temporaires)
DELETE = [
    "downloaded-logs-20251010-041801.json",
    "tmp-auth.db",
    "concepts_report.json",
    "qa-p1-baseline.json",
    "build_tag.txt",
    "BUILDSTAMP.txt",
    "nul",
    "beta_testers_emails.txt",
    "arborescence_synchronisee_20251008.txt",
    "revisions_to_delete.txt",
]

def move_files():
    """Déplace les fichiers selon le mapping MOVES"""
    moved = 0
    errors = []

    for src, dest_dir in MOVES.items():
        src_path = ROOT / src
        dest_path = ROOT / dest_dir / src

        if not src_path.exists():
            print(f"[SKIP] {src} (n'existe pas)")
            continue

        try:
            # Créer le répertoire de destination si nécessaire
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Déplacer le fichier
            shutil.move(str(src_path), str(dest_path))
            print(f"[OK] Deplace: {src} -> {dest_dir}")
            moved += 1
        except Exception as e:
            error_msg = f"[ERREUR] {src} -> {dest_dir}: {e}"
            print(error_msg)
            errors.append(error_msg)

    return moved, errors

def delete_files():
    """Supprime les fichiers temporaires"""
    deleted = 0
    errors = []

    for filename in DELETE:
        filepath = ROOT / filename

        if not filepath.exists():
            print(f"[SKIP] {filename} (n'existe pas)")
            continue

        try:
            filepath.unlink()
            print(f"[DELETE] Supprime: {filename}")
            deleted += 1
        except Exception as e:
            error_msg = f"[ERREUR] suppression {filename}: {e}"
            print(error_msg)
            errors.append(error_msg)

    return deleted, errors

def main():
    print("=" * 80)
    print("NETTOYAGE DU REPERTOIRE RACINE - 2025-10-18")
    print("=" * 80)
    print()

    # Déplacer les fichiers
    print("DEPLACEMENT DES FICHIERS...")
    print()
    moved, move_errors = move_files()
    print()
    print(f"[OK] {moved} fichiers deplaces")
    if move_errors:
        print(f"[ERREUR] {len(move_errors)} erreurs de deplacement")
    print()

    # Supprimer les fichiers temporaires
    print("SUPPRESSION DES FICHIERS TEMPORAIRES...")
    print()
    deleted, delete_errors = delete_files()
    print()
    print(f"[OK] {deleted} fichiers supprimes")
    if delete_errors:
        print(f"[ERREUR] {len(delete_errors)} erreurs de suppression")
    print()

    # Résumé final
    print("=" * 80)
    print("RESUME FINAL")
    print("=" * 80)
    print(f"[OK] Fichiers deplaces: {moved}")
    print(f"[OK] Fichiers supprimes: {deleted}")
    print(f"[ERREUR] Erreurs totales: {len(move_errors) + len(delete_errors)}")
    print()

    if move_errors or delete_errors:
        print("ERREURS DETAILLEES:")
        for error in move_errors + delete_errors:
            print(f"  {error}")
        print()

    print("[OK] Nettoyage termine!")
    print()

if __name__ == "__main__":
    main()
