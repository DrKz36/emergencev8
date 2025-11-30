#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier l'installation du système Guardian v3.0
"""

import sys
import os
from pathlib import Path
from typing import List

# Fix encoding pour Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent.parent
PLUGIN_DIR = REPO_ROOT / "claude-plugins" / "integrity-docs-guardian"
SCRIPTS_DIR = PLUGIN_DIR / "scripts"
REPORTS_DIR = REPO_ROOT / "reports"  # UNIFIED: All reports in repo root
CONFIG_DIR = PLUGIN_DIR / "config"


def check_file(file_path: Path, description: str) -> bool:
    """Vérifie qu'un fichier existe"""
    exists = file_path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {file_path.name}")
    return exists


def check_dir(dir_path: Path, description: str) -> bool:
    """Vérifie qu'un dossier existe"""
    exists = dir_path.exists() and dir_path.is_dir()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {dir_path.name}/")
    return exists


def main():
    """Test d'installation Guardian v3.0"""
    print("=" * 70)
    print("🛡️  TEST D'INSTALLATION - GUARDIAN v3.0")
    print("=" * 70)
    print()

    checks: List[bool] = []

    # 1. Scripts agents principaux (REQUIS)
    print("📁 Scripts agents (REQUIS):")
    checks.append(check_file(SCRIPTS_DIR / "scan_docs.py", "Anima (DocKeeper) v2.0"))
    checks.append(
        check_file(SCRIPTS_DIR / "check_integrity.py", "Neo (IntegrityWatcher) v2.0")
    )
    checks.append(check_file(SCRIPTS_DIR / "check_prod_logs.py", "ProdGuardian"))
    checks.append(check_file(SCRIPTS_DIR / "generate_report.py", "Nexus (Coordinator)"))
    checks.append(
        check_file(SCRIPTS_DIR / "master_orchestrator.py", "Master Orchestrator")
    )
    print()

    # 2. Scripts agents optionnels
    print("📁 Scripts agents (OPTIONNELS):")
    checks.append(check_file(SCRIPTS_DIR / "argus_analyzer.py", "Argus (DevLogs)"))
    checks.append(check_file(SCRIPTS_DIR / "analyze_ai_costs.py", "Theia (CostWatcher)"))
    checks.append(check_file(SCRIPTS_DIR / "auto_update_docs.py", "Auto-update docs"))
    print()

    # 3. Scripts utilitaires
    print("📁 Scripts utilitaires:")
    checks.append(
        check_file(
            SCRIPTS_DIR / "send_guardian_reports_email.py", "Email reports sender"
        )
    )
    checks.append(
        check_file(SCRIPTS_DIR / "generate_html_report.py", "HTML report generator")
    )
    print()

    # 4. Hooks Git
    print("📁 Hooks Git:")
    pre_commit_hook = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    post_commit_hook = REPO_ROOT / ".git" / "hooks" / "post-commit"
    pre_push_hook = REPO_ROOT / ".git" / "hooks" / "pre-push"
    checks.append(check_file(pre_commit_hook, "Hook pre-commit"))
    checks.append(check_file(post_commit_hook, "Hook post-commit"))
    checks.append(check_file(pre_push_hook, "Hook pre-push"))
    print()

    # 5. Configuration
    print("📁 Configuration:")
    checks.append(check_file(CONFIG_DIR / "guardian_config.json", "Config Guardian"))
    print()

    # 6. PowerShell scripts
    print("📁 Scripts PowerShell:")
    checks.append(check_file(SCRIPTS_DIR / "setup_guardian.ps1", "Setup Guardian"))
    checks.append(check_file(SCRIPTS_DIR / "run_audit.ps1", "Run Audit"))
    checks.append(
        check_file(
            SCRIPTS_DIR / "guardian_monitor_with_notifications.ps1",
            "Monitor with notifications",
        )
    )
    print()

    # 7. Documentation
    print("📁 Documentation:")
    checks.append(check_file(PLUGIN_DIR / "README.md", "README principal"))
    checks.append(check_file(PLUGIN_DIR / "QUICKSTART.md", "Guide de démarrage"))
    print()

    # 8. Dossiers
    print("📁 Dossiers:")
    checks.append(check_dir(SCRIPTS_DIR, "Scripts"))
    checks.append(check_dir(REPORTS_DIR, "Reports (repo root)"))
    checks.append(check_dir(CONFIG_DIR, "Config"))
    logs_dir = PLUGIN_DIR / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(exist_ok=True)
    checks.append(check_dir(logs_dir, "Logs"))
    print()

    # 9. Fichiers sync multi-agents (NOUVEAU)
    print("📁 Fichiers sync multi-agents:")
    checks.append(check_file(REPO_ROOT / "SYNC_STATUS.md", "Vue d'ensemble"))
    checks.append(check_file(REPO_ROOT / "AGENT_SYNC_CLAUDE.md", "Sync Claude"))
    checks.append(check_file(REPO_ROOT / "AGENT_SYNC_CODEX.md", "Sync Codex"))
    checks.append(check_file(REPO_ROOT / "AGENT_SYNC_GEMINI.md", "Sync Gemini"))
    print()

    # 10. Variables d'environnement (info seulement)
    print("📋 Variables d'environnement (configuration):")
    auto_update_docs = os.environ.get("AUTO_UPDATE_DOCS", "0")
    auto_apply = os.environ.get("AUTO_APPLY", "0")

    print(
        f"   AUTO_UPDATE_DOCS: {auto_update_docs} {'✅ (activé)' if auto_update_docs == '1' else '⚠️ (désactivé)'}"
    )
    print(
        f"   AUTO_APPLY: {auto_apply} {'✅ (activé)' if auto_apply == '1' else '⚠️ (désactivé - mode analyse)'}"
    )
    print()

    # Résumé
    print("=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    total_checks = len(checks)
    passed_checks = sum(checks)
    failed_checks = total_checks - passed_checks

    print(f"Total vérifications: {total_checks}")
    print(f"✅ Réussies: {passed_checks}")
    print(f"❌ Échouées: {failed_checks}")
    print(f"Taux de réussite: {(passed_checks / total_checks * 100):.1f}%")
    print()

    if failed_checks == 0:
        print("🎉 INSTALLATION COMPLÈTE ET FONCTIONNELLE !")
        print()
        print("💡 Prochaines étapes:")
        print("   1. Lancer un audit global:")
        print(
            "      pwsh -File claude-plugins/integrity-docs-guardian/scripts/run_audit.ps1"
        )
        print()
        print("   2. (Re)configurer les hooks Git:")
        print(
            "      pwsh -File claude-plugins/integrity-docs-guardian/scripts/setup_guardian.ps1"
        )
        print()
        print("   3. Consulter la documentation:")
        print("      claude-plugins/integrity-docs-guardian/README.md")
        return 0
    elif failed_checks <= 3:
        print("⚠️  Installation presque complète - quelques éléments optionnels manquent")
        return 0
    else:
        print("❌ Installation incomplète - vérifier les éléments manquants ci-dessus")
        return 1


if __name__ == "__main__":
    sys.exit(main())
