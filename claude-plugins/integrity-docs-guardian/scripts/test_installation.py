#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier l'installation du système d'orchestration automatique
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
REPORTS_DIR = PLUGIN_DIR / "reports"
CLAUDE_COMMANDS = REPO_ROOT / ".claude" / "commands"


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
    """Test d'installation"""
    print("=" * 70)
    print("🔍 TEST D'INSTALLATION - ORCHESTRATION AUTOMATIQUE v2.0.0")
    print("=" * 70)
    print()

    checks: List[bool] = []

    # 1. Scripts principaux
    print("📁 Scripts principaux:")
    checks.append(
        check_file(SCRIPTS_DIR / "auto_orchestrator.py", "Orchestrateur automatique")
    )
    checks.append(
        check_file(SCRIPTS_DIR / "auto_update_docs.py", "Agent de mise à jour doc")
    )
    checks.append(check_file(SCRIPTS_DIR / "scheduler.py", "Planificateur"))
    print()

    # 2. Scripts agents existants
    print("📁 Scripts agents:")
    checks.append(check_file(SCRIPTS_DIR / "scan_docs.py", "Anima (DocKeeper)"))
    checks.append(
        check_file(SCRIPTS_DIR / "check_integrity.py", "Neo (IntegrityWatcher)")
    )
    checks.append(check_file(SCRIPTS_DIR / "check_prod_logs.py", "ProdGuardian"))
    checks.append(check_file(SCRIPTS_DIR / "generate_report.py", "Nexus (Coordinator)"))
    checks.append(check_file(SCRIPTS_DIR / "merge_reports.py", "Merge Reports"))
    print()

    # 3. Hooks Git
    print("📁 Hooks Git:")
    post_commit_hook = REPO_ROOT / ".git" / "hooks" / "post-commit"
    checks.append(check_file(post_commit_hook, "Hook post-commit"))
    print()

    # 4. Commandes slash
    print("📁 Commandes slash Claude:")
    checks.append(check_file(CLAUDE_COMMANDS / "auto_sync.md", "/auto_sync"))
    checks.append(check_file(CLAUDE_COMMANDS / "check_docs.md", "/check_docs"))
    checks.append(
        check_file(CLAUDE_COMMANDS / "check_integrity.md", "/check_integrity")
    )
    checks.append(check_file(CLAUDE_COMMANDS / "check_prod.md", "/check_prod"))
    checks.append(
        check_file(CLAUDE_COMMANDS / "guardian_report.md", "/guardian_report")
    )
    checks.append(check_file(CLAUDE_COMMANDS / "sync_all.md", "/sync_all"))
    print()

    # 5. Documentation
    print("📁 Documentation:")
    checks.append(check_file(PLUGIN_DIR / "README.md", "README principal"))
    checks.append(check_file(PLUGIN_DIR / "QUICKSTART_AUTO.md", "Guide de démarrage"))
    checks.append(check_file(PLUGIN_DIR / "AUTO_ORCHESTRATION.md", "Doc complète"))
    checks.append(
        check_file(PLUGIN_DIR / "SUMMARY_AUTO_SETUP.md", "Résumé installation")
    )
    print()

    # 6. Dossiers
    print("📁 Dossiers:")
    checks.append(check_dir(SCRIPTS_DIR, "Scripts"))
    checks.append(check_dir(REPORTS_DIR, "Rapports"))
    logs_dir = PLUGIN_DIR / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(exist_ok=True)
    checks.append(check_dir(logs_dir, "Logs (créé si nécessaire)"))
    print()

    # 7. Variables d'environnement (info seulement)
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
        print("   1. Tester l'orchestration:")
        print(
            "      python claude-plugins/integrity-docs-guardian/scripts/auto_orchestrator.py"
        )
        print()
        print("   2. Activer le hook post-commit (optionnel):")
        print("      export AUTO_UPDATE_DOCS=1")
        print()
        print("   3. Consulter la documentation:")
        print("      claude-plugins/integrity-docs-guardian/QUICKSTART_AUTO.md")
        return 0
    else:
        print("⚠️ Installation incomplète - vérifier les éléments manquants ci-dessus")
        return 1


if __name__ == "__main__":
    sys.exit(main())
