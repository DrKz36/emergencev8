#!/usr/bin/env python3
"""
Planificateur d'exécution automatique des agents
Peut être exécuté via cron/Task Scheduler pour des vérifications périodiques
"""

import time
import subprocess
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = Path(__file__).parent
LOG_FILE = SCRIPTS_DIR.parent / "logs" / "scheduler.log"

# Créer le dossier logs s'il n'existe pas
LOG_FILE.parent.mkdir(exist_ok=True)


def log_message(message: str):
    """Log un message dans le fichier et stdout"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')


def run_orchestrator() -> Dict[str, Any]:
    """Exécute l'orchestrateur automatique"""
    log_message("🚀 Démarrage de l'orchestration automatique...")

    try:
        # Force UTF-8 encoding pour Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "auto_orchestrator.py")],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Remplace les caractères invalides au lieu de crasher
            timeout=600,  # 10 minutes max
            env=env
        )

        success = result.returncode == 0

        if success:
            log_message("✅ Orchestration terminée avec succès")
        else:
            log_message(f"⚠️ Orchestration terminée avec des erreurs")
            log_message(f"   Stderr: {result.stderr[:500]}")

        return {
            'success': success,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'timestamp': datetime.now().isoformat()
        }

    except subprocess.TimeoutExpired:
        log_message("❌ Timeout après 10 minutes")
        return {
            'success': False,
            'error': 'Timeout',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        log_message(f"❌ Erreur: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def check_git_status() -> bool:
    """Vérifie s'il y a des changements non commités

    Note: En mode HIDDEN (CHECK_GIT_STATUS=0), on skip cette vérification
    pour permettre l'exécution même avec des changements non commités.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        # S'il y a des changements, ne pas exécuter (sauf si CHECK_GIT_STATUS=0)
        has_changes = bool(result.stdout.strip())
        if has_changes:
            log_message("ℹ️  Changements non commités détectés")
            log_message("   Exécution en mode monitoring (pas de commit automatique)")
        return not has_changes
    except Exception as e:
        log_message(f"⚠️ Impossible de vérifier le statut git: {e}")
        return True  # Continuer quand même


def main():
    """Fonction principale du planificateur"""
    log_message("=" * 70)
    log_message("🕐 PLANIFICATEUR D'ORCHESTRATION AUTOMATIQUE")
    log_message("=" * 70)

    # Configuration depuis les variables d'environnement
    interval_minutes = int(os.environ.get('AGENT_CHECK_INTERVAL', '60'))
    run_once = os.environ.get('RUN_ONCE', '0') == '1'
    check_git = os.environ.get('CHECK_GIT_STATUS', '1') == '1'

    log_message(f"Configuration:")
    log_message(f"  - Intervalle: {interval_minutes} minutes")
    log_message(f"  - Mode: {'Une seule fois' if run_once else 'Continu'}")
    log_message(f"  - Vérification Git: {check_git}")
    log_message("")

    iteration = 0

    while True:
        iteration += 1
        log_message(f"📊 Itération #{iteration}")

        # Vérifier le statut git si activé
        if check_git and not check_git_status():
            if run_once:
                log_message("Mode RUN_ONCE: sortie après vérification")
                break
            else:
                log_message(f"⏰ Prochaine vérification dans {interval_minutes} minutes")
                time.sleep(interval_minutes * 60)
                continue

        # Exécuter l'orchestration
        result = run_orchestrator()

        # Si mode RUN_ONCE, sortir après une exécution
        if run_once:
            log_message("Mode RUN_ONCE: sortie après orchestration")
            return 0 if result['success'] else 1

        # Mode continu: attendre avant la prochaine itération
        log_message(f"⏰ Prochaine exécution dans {interval_minutes} minutes")
        log_message("")

        try:
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            log_message("⏹️ Arrêt du planificateur (Ctrl+C)")
            break

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n⏹️ Planificateur interrompu")
        sys.exit(0)
