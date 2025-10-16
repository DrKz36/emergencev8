#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur Automatique - Exécute tous les agents et met à jour la documentation automatiquement
"""

import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Fix encoding pour Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration
REPO_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = Path(__file__).parent
REPORTS_DIR = REPO_ROOT / "claude-plugins" / "integrity-docs-guardian" / "reports"


def run_command(cmd: List[str], description: str) -> Tuple[bool, str, str]:
    """Exécute une commande et retourne (success, stdout, stderr)"""
    print(f"🔄 {description}...")
    try:
        # Force UTF-8 encoding pour Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Remplace les caractères invalides au lieu de crasher
            timeout=300,
            env=env
        )
        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout après 300 secondes"
    except Exception as e:
        return False, "", str(e)


def run_agent(script_name: str, agent_name: str) -> Dict[str, Any]:
    """Exécute un agent spécifique"""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        return {
            'agent': agent_name,
            'status': 'ERROR',
            'message': f'Script introuvable: {script_path}'
        }

    success, stdout, stderr = run_command(
        [sys.executable, str(script_path)],
        f"Exécution de {agent_name}"
    )

    return {
        'agent': agent_name,
        'status': 'OK' if success else 'ERROR',
        'message': stdout if success else stderr,
        'timestamp': datetime.now().isoformat()
    }


def main():
    """Orchestration automatique complète"""
    print("=" * 70)
    print("🤖 ORCHESTRATEUR AUTOMATIQUE - ÉMERGENCE")
    print("=" * 70)
    print(f"\nDémarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Résultats de l'orchestration
    orchestration_results = {
        'timestamp': datetime.now().isoformat(),
        'agents': [],
        'global_status': 'OK',
        'summary': {}
    }

    # 1. Exécuter tous les agents en parallèle (simulé séquentiellement pour simplifier)
    agents = [
        ('scan_docs.py', 'Anima (DocKeeper)'),
        ('check_integrity.py', 'Neo (IntegrityWatcher)'),
        ('check_prod_logs.py', 'ProdGuardian'),
    ]

    print("📋 PHASE 1: Exécution des agents de vérification")
    print("-" * 70)

    for script, name in agents:
        result = run_agent(script, name)
        orchestration_results['agents'].append(result)

        status_emoji = "✅" if result['status'] == 'OK' else "❌"
        print(f"{status_emoji} {name}: {result['status']}")

        if result['status'] != 'OK':
            orchestration_results['global_status'] = 'ERROR'
            print(f"   ⚠️ {result['message'][:200]}")

    print()

    # 2. Générer le rapport unifié (Nexus)
    print("📋 PHASE 2: Génération du rapport unifié (Nexus)")
    print("-" * 70)

    nexus_result = run_agent('generate_report.py', 'Nexus (Coordinator)')
    orchestration_results['agents'].append(nexus_result)

    status_emoji = "✅" if nexus_result['status'] == 'OK' else "❌"
    print(f"{status_emoji} Nexus (Coordinator): {nexus_result['status']}\n")

    # 3. Fusionner tous les rapports (Orchestrateur)
    print("📋 PHASE 3: Fusion des rapports")
    print("-" * 70)

    merge_result = run_agent('merge_reports.py', 'Merge Reports')
    orchestration_results['agents'].append(merge_result)

    status_emoji = "✅" if merge_result['status'] == 'OK' else "❌"
    print(f"{status_emoji} Merge Reports: {merge_result['status']}\n")

    # 4. Mise à jour automatique de la documentation
    print("📋 PHASE 4: Mise à jour automatique de la documentation")
    print("-" * 70)

    auto_update_result = run_agent('auto_update_docs.py', 'Auto Documentation Updater')
    orchestration_results['agents'].append(auto_update_result)

    status_emoji = "✅" if auto_update_result['status'] == 'OK' else "❌"
    print(f"{status_emoji} Documentation Updater: {auto_update_result['status']}\n")

    # 5. Calculer les statistiques
    total_agents = len(orchestration_results['agents'])
    successful_agents = len([a for a in orchestration_results['agents'] if a['status'] == 'OK'])
    failed_agents = total_agents - successful_agents

    orchestration_results['summary'] = {
        'total_agents': total_agents,
        'successful': successful_agents,
        'failed': failed_agents,
        'success_rate': f"{(successful_agents / total_agents * 100):.1f}%"
    }

    # 6. Sauvegarder le rapport d'orchestration
    orchestration_report_path = REPORTS_DIR / "orchestration_report.json"
    with open(orchestration_report_path, 'w', encoding='utf-8') as f:
        json.dump(orchestration_results, f, indent=2, ensure_ascii=False)

    # 7. Afficher le résumé final
    print("=" * 70)
    print("📊 RÉSUMÉ DE L'ORCHESTRATION")
    print("=" * 70)
    print(f"Total agents exécutés: {total_agents}")
    print(f"Succès: {successful_agents}")
    print(f"Échecs: {failed_agents}")
    print(f"Taux de succès: {orchestration_results['summary']['success_rate']}")
    print()

    if orchestration_results['global_status'] == 'OK':
        print("✅ Orchestration terminée avec succès")
        print(f"📄 Rapport complet: {orchestration_report_path}")
        return 0
    else:
        print("⚠️ Orchestration terminée avec des erreurs")
        print(f"📄 Rapport complet: {orchestration_report_path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
