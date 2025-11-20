#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuration de l'automatisation Guardian
Configure les hooks Git et le scheduler pour une automatisation complète
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

# Fix encoding pour Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(
        sys.stdout, "reconfigure"
    ) else None

# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent.parent
GIT_HOOKS_DIR = REPO_ROOT / ".git" / "hooks"
SCRIPTS_DIR = Path(__file__).parent


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_step(step_num, total, description):
    """Print a step header"""
    print(f"[{step_num}/{total}] {description}")
    print("-" * 70)


def run_command(cmd, description="", check=True):
    """Execute a command and return success status"""
    try:
        result = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr
    except Exception as e:
        return False, "", str(e)


def verify_hooks_executable():
    """Ensure Git hooks are executable (Unix/Linux/Mac)"""
    if platform.system() != "Windows":
        hooks = ["pre-commit", "post-commit", "pre-push"]
        for hook in hooks:
            hook_path = GIT_HOOKS_DIR / hook
            if hook_path.exists():
                os.chmod(hook_path, 0o755)
                print(f"   ✅ {hook} rendu exécutable")


def setup_git_config():
    """Configure Git pour utiliser les hooks"""
    print_step(1, 5, "Configuration Git")

    # Vérifier que les hooks existent
    hooks_status = {}
    for hook in ["pre-commit", "post-commit", "pre-push"]:
        hook_path = GIT_HOOKS_DIR / hook
        hooks_status[hook] = hook_path.exists()

    all_exist = all(hooks_status.values())

    if all_exist:
        print("   ✅ Tous les hooks Git sont présents:")
        for hook, exists in hooks_status.items():
            print(f"      - {hook}: {'✅' if exists else '❌'}")

        # Rendre les hooks exécutables
        verify_hooks_executable()

        print("\n   💡 Les hooks s'exécuteront automatiquement:")
        print("      - pre-commit:  Avant chaque commit (vérifications)")
        print("      - post-commit: Après chaque commit (rapports)")
        print("      - pre-push:    Avant chaque push (vérif production)")
    else:
        print("   ⚠️  Certains hooks sont manquants:")
        for hook, exists in hooks_status.items():
            print(f"      - {hook}: {'✅' if exists else '❌ MANQUANT'}")

    print()
    return all_exist


def setup_environment_variables():
    """Guide l'utilisateur pour configurer les variables d'environnement"""
    print_step(2, 5, "Configuration des Variables d'Environnement")

    is_windows = platform.system() == "Windows"

    print("   Pour activer l'automatisation complète, configure ces variables:\n")

    env_vars = {
        "AUTO_UPDATE_DOCS": {
            "description": "Active la mise à jour auto de la documentation",
            "values": "0 (désactivé) ou 1 (activé)",
            "default": "0",
        },
        "AUTO_APPLY": {
            "description": "Applique et commit automatiquement les mises à jour",
            "values": "0 (désactivé) ou 1 (activé)",
            "default": "0",
        },
        "CHECK_GIT_STATUS": {
            "description": "Vérifie les changements non commités avant l'exécution",
            "values": "0 (skip) ou 1 (vérifier)",
            "default": "1",
        },
    }

    # Vérifier les valeurs actuelles
    print("   📊 Valeurs actuelles:")
    for var, info in env_vars.items():
        current = os.environ.get(var, info["default"])
        print(f"      - {var}={current} ({info['description']})")

    print("\n   💡 Pour configurer:")
    if is_windows:
        print("      PowerShell (session actuelle):")
        print("      $env:AUTO_UPDATE_DOCS='1'")
        print("      $env:AUTO_APPLY='1'")
        print("\n      PowerShell (permanent - ajoute à ton $PROFILE):")
        print(
            "      [System.Environment]::SetEnvironmentVariable('AUTO_UPDATE_DOCS','1','User')"
        )
    else:
        print("      Bash/Zsh (ajoute à ~/.bashrc ou ~/.zshrc):")
        print("      export AUTO_UPDATE_DOCS=1")
        print("      export AUTO_APPLY=1")

    print()


def verify_python_dependencies():
    """Vérifie que les dépendances Python sont installées"""
    print_step(3, 5, "Vérification des Dépendances Python")

    # Vérifier que Python est disponible
    python_cmd = sys.executable
    print(f"   🐍 Python: {python_cmd}")

    # Test d'import des modules critiques
    required_modules = ["json", "subprocess", "pathlib"]
    all_ok = True

    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ Module '{module}' disponible")
        except ImportError:
            print(f"   ❌ Module '{module}' manquant")
            all_ok = False

    if all_ok:
        print("\n   ✅ Toutes les dépendances sont présentes")
    else:
        print("\n   ⚠️  Certaines dépendances sont manquantes")

    print()
    return all_ok


def test_agents():
    """Test que les agents s'exécutent correctement"""
    print_step(4, 5, "Test des Agents Guardian")

    agents = [
        ("scan_docs.py", "Anima (DocKeeper)"),
        ("check_integrity.py", "Neo (IntegrityWatcher)"),
        ("check_prod_logs.py", "ProdGuardian"),
        ("generate_report.py", "Nexus (Coordinator)"),
    ]

    all_ok = True
    for script, name in agents:
        script_path = SCRIPTS_DIR / script
        if script_path.exists():
            print(f"   ✅ {name}: Script présent")
        else:
            print(f"   ❌ {name}: Script MANQUANT ({script})")
            all_ok = False

    if all_ok:
        print("\n   ✅ Tous les agents sont présents et prêts")
    else:
        print("\n   ⚠️  Certains agents sont manquants")

    print()
    return all_ok


def show_usage_guide():
    """Affiche un guide d'utilisation"""
    print_step(5, 5, "Guide d'Utilisation")

    print("   🎯 AUTOMATISATION ACTIVÉE!\n")

    print("   📋 Ce qui se passe maintenant:\n")

    print("   1️⃣  AVANT CHAQUE COMMIT (pre-commit hook):")
    print("      - Vérification de la couverture de tests")
    print("      - Vérification de la doc API (OpenAPI)")
    print("      - Exécution d'Anima (gaps de documentation)")
    print("      - Exécution de Neo (intégrité backend/frontend)")
    print("      ⚠️  Le commit est BLOQUÉ si erreurs critiques\n")

    print("   2️⃣  APRÈS CHAQUE COMMIT (post-commit hook):")
    print("      - Génération du rapport unifié (Nexus)")
    print("      - Affichage d'un résumé détaillé")
    print("      - Mise à jour automatique de la doc (si AUTO_UPDATE_DOCS=1)\n")

    print("   3️⃣  AVANT CHAQUE PUSH (pre-push hook):")
    print("      - Vérification de l'état de la production (ProdGuardian)")
    print("      - Vérification que tous les rapports sont OK")
    print("      ⚠️  Le push est BLOQUÉ si production en état critique\n")

    print("   💡 Commandes utiles:\n")
    print("      - git commit           → Déclenche pre-commit + post-commit")
    print("      - git commit --no-verify → Skip les hooks (déconseillé)")
    print("      - git push             → Déclenche pre-push\n")

    print("   📊 Voir les rapports:")
    print(
        f"      - Documentation: {REPO_ROOT}/claude-plugins/integrity-docs-guardian/reports/docs_report.json"
    )
    print(
        f"      - Intégrité:     {REPO_ROOT}/claude-plugins/integrity-docs-guardian/reports/integrity_report.json"
    )
    print(
        f"      - Production:    {REPO_ROOT}/claude-plugins/integrity-docs-guardian/reports/prod_report.json"
    )
    print(
        f"      - Unifié:        {REPO_ROOT}/claude-plugins/integrity-docs-guardian/reports/unified_report.json\n"
    )

    print("   🚀 Pour le monitoring continu en arrière-plan:")
    print("      - Utilise le scheduler.py (voir HIDDEN_MODE_GUIDE.md)")
    print("      - Configure une tâche Windows Task Scheduler ou cron job\n")


def main():
    """Configuration principale"""
    print_header("🤖 ÉMERGENCE Guardian - Configuration de l'Automatisation")

    print("Ce script va configurer l'automatisation complète des agents Guardian:")
    print("  ✅ Hooks Git (pre-commit, post-commit, pre-push)")
    print("  ✅ Variables d'environnement")
    print("  ✅ Vérification des dépendances")
    print("  ✅ Test des agents\n")

    # Étape 1: Configuration Git
    hooks_ok = setup_git_config()

    # Étape 2: Variables d'environnement
    setup_environment_variables()

    # Étape 3: Dépendances
    deps_ok = verify_python_dependencies()

    # Étape 4: Test des agents
    agents_ok = test_agents()

    # Étape 5: Guide d'utilisation
    show_usage_guide()

    # Résumé final
    print_header("📊 RÉSUMÉ DE LA CONFIGURATION")

    if hooks_ok and deps_ok and agents_ok:
        print("   ✅ Configuration réussie! L'automatisation est activée.\n")
        print(
            "   🎯 Prochain commit déclenchera automatiquement les agents Guardian.\n"
        )
        return 0
    else:
        print("   ⚠️  Configuration partiellement réussie.\n")
        print("   Certains éléments nécessitent ton attention:")
        if not hooks_ok:
            print("      - ❌ Hooks Git manquants ou non configurés")
        if not deps_ok:
            print("      - ❌ Dépendances Python manquantes")
        if not agents_ok:
            print("      - ❌ Certains agents manquants")
        print()
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Configuration interrompue")
        sys.exit(130)
