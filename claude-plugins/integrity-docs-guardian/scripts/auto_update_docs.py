#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent de mise à jour automatique de la documentation
Lit les rapports générés par les agents et met à jour automatiquement la documentation pertinente
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Fix encoding pour Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration des chemins
REPO_ROOT = Path(__file__).parent.parent.parent.parent
REPORTS_DIR = REPO_ROOT / "claude-plugins" / "integrity-docs-guardian" / "reports"
DOCS_DIR = REPO_ROOT / "docs"
AGENT_SYNC_FILE = REPO_ROOT / "AGENT_SYNC.md"


def load_report(report_name: str) -> Dict[str, Any]:
    """Charge un rapport JSON"""
    report_path = REPORTS_DIR / report_name
    if not report_path.exists():
        return {}

    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur lors de la lecture de {report_name}: {e}")
        return {}


def update_agent_sync_production(prod_report: Dict[str, Any]) -> List[str]:
    """Met à jour AGENT_SYNC.md avec les informations de production"""
    updates = []

    if not prod_report:
        return updates

    status = prod_report.get('status', 'UNKNOWN')
    timestamp = prod_report.get('timestamp', '')

    if status in ['DEGRADED', 'CRITICAL']:
        # Préparer une mise à jour pour AGENT_SYNC.md
        summary = prod_report.get('summary', {})
        errors = summary.get('errors', 0)
        warnings = summary.get('warnings', 0)

        update_text = f"""
## Production Status Update - {timestamp}

**Status:** {status}
- Errors: {errors}
- Warnings: {warnings}

**Recommendations:**
"""
        for rec in prod_report.get('recommendations', []):
            update_text += f"- [{rec.get('priority', 'UNKNOWN')}] {rec.get('action', 'N/A')}\n"

        updates.append({
            'file': str(AGENT_SYNC_FILE),
            'section': '🚀 Déploiement Cloud Run',
            'content': update_text,
            'priority': 'HIGH' if status == 'CRITICAL' else 'MEDIUM'
        })

    return updates


def update_documentation_from_docs_report(docs_report: Dict[str, Any]) -> List[str]:
    """Met à jour la documentation basée sur le rapport de documentation"""
    updates = []

    if not docs_report:
        return updates

    status = docs_report.get('status', 'ok')

    if status == 'needs_update':
        gaps = docs_report.get('gaps', [])

        for gap in gaps:
            severity = gap.get('severity', 'low')
            if severity in ['high', 'critical']:
                file_path = gap.get('file', '')
                affected_docs = gap.get('affected_docs', [])
                recommendation = gap.get('recommendation', '')

                for doc in affected_docs:
                    updates.append({
                        'file': doc,
                        'section': 'Auto-generated update',
                        'content': f"## Update from {file_path}\n\n{recommendation}",
                        'priority': 'HIGH' if severity == 'critical' else 'MEDIUM'
                    })

    return updates


def update_agent_sync_from_integrity(integrity_report: Dict[str, Any]) -> List[str]:
    """Met à jour AGENT_SYNC.md avec les problèmes d'intégrité critiques"""
    updates = []

    if not integrity_report:
        return updates

    status = integrity_report.get('status', 'ok')

    if status in ['warning', 'critical']:
        issues = integrity_report.get('issues', [])
        critical_issues = [i for i in issues if i.get('severity') == 'critical']

        if critical_issues:
            update_text = f"""
## Integrity Issues Detected - {datetime.now().isoformat()}

**Critical Issues Found:**
"""
            for issue in critical_issues:
                issue_type = issue.get('type', 'unknown')
                description = issue.get('description', 'N/A')
                update_text += f"- **{issue_type}:** {description}\n"

            updates.append({
                'file': str(AGENT_SYNC_FILE),
                'section': '🔧 Architecture Technique',
                'content': update_text,
                'priority': 'CRITICAL'
            })

    return updates


def generate_update_report(all_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Génère un rapport de mise à jour"""
    return {
        'timestamp': datetime.now().isoformat(),
        'updates_found': len(all_updates),
        'updates': all_updates,
        'priority_breakdown': {
            'CRITICAL': len([u for u in all_updates if u.get('priority') == 'CRITICAL']),
            'HIGH': len([u for u in all_updates if u.get('priority') == 'HIGH']),
            'MEDIUM': len([u for u in all_updates if u.get('priority') == 'MEDIUM']),
            'LOW': len([u for u in all_updates if u.get('priority') == 'LOW'])
        }
    }


def apply_updates_with_confirmation(updates: List[Dict[str, Any]], auto_apply: bool = False):
    """Applique les mises à jour avec confirmation (ou automatiquement si auto_apply=True)"""
    if not updates:
        print("✅ Aucune mise à jour de documentation nécessaire")
        return

    print(f"\n📝 {len(updates)} mise(s) à jour de documentation détectée(s):\n")

    for idx, update in enumerate(updates, 1):
        print(f"{idx}. [{update.get('priority', 'UNKNOWN')}] {update['file']}")
        print(f"   Section: {update.get('section', 'N/A')}")
        print(f"   Preview: {update.get('content', '')[:100]}...")
        print()

    if not auto_apply:
        print("\n⚠️ Mode manuel activé. Les mises à jour ne seront PAS appliquées automatiquement.")
        print("Pour appliquer automatiquement, utilisez: AUTO_APPLY=1")
        return

    print("🔄 Application automatique des mises à jour...")

    for update in updates:
        file_path = Path(update['file'])
        if not file_path.exists():
            print(f"⚠️ Fichier introuvable: {file_path}")
            continue

        # Pour simplifier, on ajoute les mises à jour à la fin du fichier
        # Une version plus sophistiquée rechercherait la section appropriée
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n\n<!-- Auto-update {datetime.now().isoformat()} -->\n")
                f.write(update.get('content', ''))
            print(f"✅ Mis à jour: {file_path}")
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour de {file_path}: {e}")


def main():
    """Fonction principale"""
    print("🤖 Agent de Mise à Jour Automatique de Documentation")
    print("=" * 60)
    print()

    # Charger tous les rapports
    print("📊 Chargement des rapports...")
    prod_report = load_report("prod_report.json")
    docs_report = load_report("docs_report.json")
    integrity_report = load_report("integrity_report.json")
    unified_report = load_report("unified_report.json")

    # Collecter toutes les mises à jour nécessaires
    all_updates = []

    print("🔍 Analyse des rapports de production...")
    all_updates.extend(update_agent_sync_production(prod_report))

    print("🔍 Analyse des rapports de documentation...")
    all_updates.extend(update_documentation_from_docs_report(docs_report))

    print("🔍 Analyse des rapports d'intégrité...")
    all_updates.extend(update_agent_sync_from_integrity(integrity_report))

    # Générer le rapport de mise à jour
    update_report = generate_update_report(all_updates)

    # Sauvegarder le rapport
    report_path = REPORTS_DIR / "auto_update_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(update_report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Rapport de mise à jour sauvegardé: {report_path}")

    # Vérifier si le mode auto-apply est activé
    auto_apply = os.environ.get('AUTO_APPLY', '0') == '1'

    # Appliquer les mises à jour
    apply_updates_with_confirmation(all_updates, auto_apply=auto_apply)

    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print(f"Total updates: {len(all_updates)}")
    for priority, count in update_report['priority_breakdown'].items():
        if count > 0:
            print(f"  {priority}: {count}")

    if auto_apply:
        print("\n✅ Documentation mise à jour automatiquement")
    else:
        print("\n⚠️ Mode manuel - aucune modification appliquée")
        print("Pour appliquer automatiquement: AUTO_APPLY=1 python auto_update_docs.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
