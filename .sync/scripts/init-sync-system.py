#!/usr/bin/env python3
"""
Script d'initialisation du système de synchronisation multi-agent
Configure l'environnement et vérifie les prérequis
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class Colors:
    """Codes couleur ANSI"""

    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    RED = "\033[0;31m"
    NC = "\033[0m"


def log_info(msg: str) -> None:
    """Affiche un message d'information"""
    try:
        print(f"{Colors.BLUE}[i] {msg}{Colors.NC}")
    except UnicodeEncodeError:
        print(f"[i] {msg}")


def log_success(msg: str) -> None:
    """Affiche un message de succès"""
    try:
        print(f"{Colors.GREEN}[OK] {msg}{Colors.NC}")
    except UnicodeEncodeError:
        print(f"[OK] {msg}")


def log_warning(msg: str) -> None:
    """Affiche un avertissement"""
    try:
        print(f"{Colors.YELLOW}[!] {msg}{Colors.NC}")
    except UnicodeEncodeError:
        print(f"[!] {msg}")


def log_error(msg: str) -> None:
    """Affiche une erreur"""
    try:
        print(f"{Colors.RED}[ERROR] {msg}{Colors.NC}")
    except UnicodeEncodeError:
        print(f"[ERROR] {msg}")


def check_command_exists(command: str) -> bool:
    """Vérifie si une commande existe"""
    try:
        subprocess.run(
            [command, "--version"],
            capture_output=True,
            check=False,
        )
        return True
    except FileNotFoundError:
        return False


def check_git_config() -> Tuple[bool, List[str]]:
    """Vérifie la configuration Git"""
    issues = []

    try:
        # Vérifier user.name
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=False,
        )
        if not result.stdout.strip():
            issues.append("Git user.name non configuré")

        # Vérifier user.email
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
        )
        if not result.stdout.strip():
            issues.append("Git user.email non configuré")

        return len(issues) == 0, issues
    except Exception as e:
        return False, [str(e)]


def check_git_remotes() -> Tuple[bool, List[str]]:
    """Vérifie les remotes Git"""
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            check=False,
        )

        if not result.stdout.strip():
            return False, ["Aucun remote Git configuré"]

        remotes = result.stdout.strip().split("\n")
        return True, remotes
    except Exception as e:
        return False, [str(e)]


def create_git_aliases() -> bool:
    """Crée des alias Git utiles pour la synchronisation"""
    aliases = {
        "sync-export": "!f() { git format-patch origin/main --stdout > .sync/patches/sync_$(date +%Y%m%d_%H%M%S).patch; }; f",
        "sync-status": "!f() { git status --short > .sync/patches/files_$(date +%Y%m%d_%H%M%S).txt; git log origin/main..HEAD --oneline > .sync/patches/commits_$(date +%Y%m%d_%H%M%S).txt; }; f",
    }

    try:
        for alias, command in aliases.items():
            subprocess.run(
                ["git", "config", "--global", f"alias.{alias}", command],
                capture_output=True,
                check=True,
            )
        return True
    except Exception:
        return False


def init_sync_tracker() -> bool:
    """Initialise le système de traçabilité"""
    try:
        import sqlite3

        # Créer la DB manuellement
        sync_dir = Path(".sync")
        db_path = sync_dir / "sync_history.db"

        if db_path.exists():
            return True

        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    sync_type TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    patch_name TEXT NOT NULL,
                    branch_source TEXT,
                    branch_target TEXT,
                    commits_count INTEGER DEFAULT 0,
                    files_modified INTEGER DEFAULT 0,
                    patch_size_bytes INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
        return True
    except Exception as e:
        log_error(f"Erreur lors de l'initialisation du tracker: {e}")
        return False


def check_python_packages() -> Tuple[bool, List[str]]:
    """Vérifie les packages Python optionnels"""
    optional_packages = ["pytest", "ruff", "mypy"]
    missing = []

    for package in optional_packages:
        try:
            subprocess.run(
                [package, "--version"],
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            missing.append(package)

    return len(missing) == 0, missing


def main():
    """Point d'entrée principal"""
    print("\n" + "=" * 60)
    try:
        print("Initialisation Systeme de Synchronisation Multi-Agent")
    except UnicodeEncodeError:
        print("Initialisation Systeme de Synchronisation Multi-Agent")
    print("=" * 60 + "\n")

    all_good = True

    # 1. Vérifier qu'on est dans un dépôt Git
    log_info("[1/9] Vérification dépôt Git...")
    if not Path(".git").exists():
        log_error("Pas dans un dépôt Git")
        log_info("Exécutez ce script depuis la racine du projet EmergenceV8")
        return 1
    log_success("Dépôt Git détecté")

    # 2. Vérifier la structure .sync
    log_info("[2/9] Vérification structure .sync...")
    sync_dir = Path(".sync")
    required_dirs = [
        sync_dir / "patches",
        sync_dir / "logs",
        sync_dir / "scripts",
        sync_dir / "templates",
    ]

    for dir_path in required_dirs:
        if not dir_path.exists():
            log_warning(f"Création du dossier: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)

    log_success("Structure .sync OK")

    # 3. Vérifier Git
    log_info("[3/9] Vérification commande Git...")
    if not check_command_exists("git"):
        log_error("Git n'est pas installé")
        all_good = False
    else:
        log_success("Git installé")

    # 4. Vérifier configuration Git
    log_info("[4/9] Vérification configuration Git...")
    git_ok, issues = check_git_config()
    if not git_ok:
        for issue in issues:
            log_warning(issue)
        log_info("Configurez Git avec:")
        log_info('  git config --global user.name "Votre Nom"')
        log_info('  git config --global user.email "votre@email.com"')
        all_good = False
    else:
        log_success("Configuration Git OK")

    # 5. Vérifier remotes Git
    log_info("[5/9] Vérification remotes Git...")
    remotes_ok, remotes = check_git_remotes()
    if not remotes_ok:
        log_warning("Aucun remote Git configuré")
        log_info("Pour GPT Codex Cloud, c'est normal (pas d'accès réseau)")
        log_info("Pour agent local, configurez un remote avec:")
        log_info("  git remote add origin <url>")
    else:
        log_success("Remotes Git configurés:")
        for remote in remotes[:4]:  # Afficher max 4 lignes
            print(f"  {remote}")

    # 6. Créer alias Git (optionnel)
    log_info("[6/9] Création alias Git (optionnel)...")
    if create_git_aliases():
        log_success("Alias Git créés")
        log_info("  - git sync-export : Exporter patch rapide")
        log_info("  - git sync-status : Lister fichiers/commits")
    else:
        log_warning("Alias Git non créés (optionnel)")

    # 7. Initialiser système de traçabilité
    log_info("[7/9] Initialisation système de traçabilité...")
    if init_sync_tracker():
        log_success("Système de traçabilité initialisé")
        log_info("  Base de données: .sync/sync_history.db")
    else:
        log_warning("Erreur initialisation traçabilité")
        all_good = False

    # 8. Vérifier Python
    log_info("[8/9] Vérification Python...")
    if not check_command_exists("python") and not check_command_exists("python3"):
        log_error("Python n'est pas installé")
        all_good = False
    else:
        python_cmd = "python" if check_command_exists("python") else "python3"
        result = subprocess.run(
            [python_cmd, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        version = result.stdout.strip()
        log_success(f"Python installé: {version}")

        # Vérifier packages optionnels
        packages_ok, missing = check_python_packages()
        if not packages_ok:
            log_warning(f"Packages Python manquants: {', '.join(missing)}")
            log_info("Ces packages sont optionnels mais recommandés:")
            log_info("  pip install pytest ruff mypy")

    # 9. Vérifier Node.js (optionnel)
    log_info("[9/9] Vérification Node.js (optionnel)...")
    if not check_command_exists("node"):
        log_warning("Node.js non installé (optionnel pour backend Python)")
    else:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        version = result.stdout.strip()
        log_success(f"Node.js installé: {version}")

    # Résumé
    print("\n" + "=" * 60)
    if all_good:
        log_success("Systeme de synchronisation initialise avec succes!")
    else:
        log_warning("Systeme initialise avec quelques avertissements")

    print("\nProchaines etapes:\n")
    print("1. Lire le guide: .sync/README.md")
    print("2. Pour GPT Codex Cloud:")
    print("   python .sync/scripts/cloud-export.py")
    print("3. Pour Agent Local (Claude Code):")
    print("   python .sync/scripts/local-import.py <patch_name>")
    print("4. Consulter l'historique:")
    print("   python .sync/scripts/sync-tracker.py list")
    print("\n" + "=" * 60 + "\n")

    return 0 if all_good else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] Initialisation interrompue")
        sys.exit(130)
    except Exception as e:
        log_error(f"Erreur: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
