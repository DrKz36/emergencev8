#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'analyse des rapports Guardian pour Codex GPT
Utilise les rapports JSON locaux pour générer un résumé actionnable
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Fix encoding Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

REPORTS_DIR = Path(__file__).parent.parent / 'reports'


def analyze_prod_report():
    """Analyse le rapport production"""
    with open(REPORTS_DIR / 'prod_report.json', 'r', encoding='utf-8') as f:
        prod = json.load(f)

    print("=" * 60)
    print(f"📊 PRODUCTION - {prod['service']}")
    print("=" * 60)
    print(f"Status: {prod['status']}")
    print(f"Logs analysés: {prod['logs_analyzed']} (dernière {prod['freshness']})")
    print(f"Timestamp: {prod['timestamp']}")
    print()

    # Résumé
    summary = prod['summary']
    print(f"✅ Erreurs: {summary['errors']}")
    print(f"⚠️  Warnings: {summary['warnings']}")
    print(f"🚨 Critical signals: {summary['critical_signals']}")
    print(f"🐌 Latency issues: {summary['latency_issues']}")
    print()

    # Erreurs détaillées
    if prod['errors_detailed']:
        print("❌ ERREURS DÉTECTÉES:")
        for err in prod['errors_detailed']:
            print(f"   - {err['message']}")
            print(f"     Endpoint: {err.get('endpoint', 'N/A')}")
            print(f"     File: {err.get('file_path', 'N/A')}:{err.get('line_number', 'N/A')}")
            if err.get('stack_trace'):
                print(f"     Stack: {err['stack_trace'][:200]}...")
        print()

    # Warnings détaillés
    if prod['warnings_detailed']:
        print("⚠️  WARNINGS:")
        for warn in prod['warnings_detailed']:
            print(f"   - {warn['message']}")
            print(f"     Endpoint: {warn.get('endpoint', 'N/A')}")
        print()

    # Patterns d'erreurs
    patterns = prod['error_patterns']
    if patterns['most_common_error']:
        print("🔍 PATTERNS D'ERREURS:")
        print(f"   Erreur la plus fréquente: {patterns['most_common_error']}")
        if patterns['by_endpoint']:
            print("   Endpoints touchés:")
            for endpoint, count in list(patterns['by_endpoint'].items())[:5]:
                print(f"     - {endpoint}: {count} erreur(s)")
        print()

    # Recommandations
    if prod['recommendations']:
        print("💡 ACTIONS RECOMMANDÉES:")
        for rec in prod['recommendations']:
            print(f"   [{rec['priority']}] {rec['action']}")
            print(f"      → {rec['details']}")
        print()

    # Commits récents (contexte)
    if prod['recent_commits']:
        print("📝 COMMITS RÉCENTS:")
        for commit in prod['recent_commits'][:3]:
            print(f"   - {commit['hash']}: {commit['message']} ({commit['time']})")
        print()


def analyze_unified_report():
    """Analyse le rapport unifié Nexus"""
    with open(REPORTS_DIR / 'unified_report.json', 'r', encoding='utf-8') as f:
        unified = json.load(f)

    print("=" * 60)
    print("📋 VUE D'ENSEMBLE (Nexus)")
    print("=" * 60)

    # Executive summary
    exec_sum = unified['executive_summary']
    status_icon = "✅" if exec_sum['status'] == 'ok' else "🔴"
    print(f"{status_icon} {exec_sum['headline']}")
    print(f"Issues totales: {exec_sum['total_issues']} (Critical: {exec_sum['critical']}, Warnings: {exec_sum['warnings']})")
    print()

    # Priority actions
    if unified['priority_actions']:
        print("🔥 PRIORITY ACTIONS:")
        for action in unified['priority_actions']:
            print(f"   [{action['priority']}] {action['description']}")
            print(f"      File: {action.get('file', 'N/A')}")
            print(f"      Fix: {action.get('recommendation', 'N/A')}")
        print()

    # Anima (Documentation)
    anima = unified['full_reports']['anima']
    print("📚 ANIMA (Documentation):")
    print(f"   Status: {anima['status']}")
    print(f"   Gaps trouvés: {anima['statistics']['gaps_found']}")
    print(f"   Updates proposées: {anima['statistics']['updates_proposed']}")

    if anima['documentation_gaps']:
        print("   ⚠️  GAPS:")
        for gap in anima['documentation_gaps'][:5]:
            print(f"      - {gap.get('description', 'N/A')} ({gap.get('file', 'N/A')})")

    if anima['proposed_updates']:
        print("   📝 UPDATES PROPOSÉES:")
        for update in anima['proposed_updates'][:5]:
            print(f"      - {update.get('action', 'N/A')} → {update.get('target_file', 'N/A')}")
    print()

    # Neo (Intégrité)
    neo = unified['full_reports']['neo']
    print("🔍 NEO (Intégrité):")
    print(f"   Status: {neo['status']}")
    print(f"   Backend files changed: {neo['statistics']['backend_files_changed']}")
    print(f"   Frontend files changed: {neo['statistics']['frontend_files_changed']}")
    print(f"   Issues trouvées: {neo['statistics']['issues_found']}")

    if neo['issues']:
        print("   ❌ ISSUES:")
        for issue in neo['issues'][:5]:
            print(f"      - [{issue.get('category', 'N/A')}] {issue.get('description', 'N/A')}")
            print(f"        → {issue.get('recommendation', 'N/A')}")
    print()

    # Recommandations par horizon
    recs = unified['recommendations']
    print("💡 RECOMMANDATIONS PAR HORIZON:")
    if recs['immediate'] and recs['immediate'][0] != "None - all checks passed":
        print(f"   🔥 Immediate: {', '.join(recs['immediate'])}")
    if recs['short_term'] and recs['short_term'][0] != "Continue monitoring":
        print(f"   📅 Short-term: {', '.join(recs['short_term'])}")
    if recs['long_term'] and recs['long_term'][0] != "Maintain current practices":
        print(f"   📋 Long-term: {', '.join(recs['long_term'])}")
    print()


def main():
    """Point d'entrée principal"""
    print("\n" + "=" * 60)
    print("📊 ANALYSE RAPPORTS GUARDIAN")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    try:
        analyze_prod_report()
        analyze_unified_report()

        print("=" * 60)
        print("✅ ANALYSE TERMINÉE")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"❌ ERREUR: Fichier rapport non trouvé: {e}")
        print("   Assure-toi que les rapports Guardian ont été générés.")
        print("   Lance: pwsh -File claude-plugins/integrity-docs-guardian/scripts/run_audit.ps1")
    except json.JSONDecodeError as e:
        print(f"❌ ERREUR: Fichier rapport JSON invalide: {e}")
    except Exception as e:
        print(f"❌ ERREUR inattendue: {e}")


if __name__ == '__main__':
    main()
