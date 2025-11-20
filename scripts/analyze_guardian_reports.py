#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Outils d'analyse des rapports Guardian.

Le script peut générer un résumé synthétique (utile pour répondre vite aux
utilisateurs) ou afficher une analyse détaillée de tous les signaux remontés
par les agents Guardian.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Fix encoding Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

DEFAULT_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def load_report(report_path: Path) -> Dict[str, Any]:
    """Charge un rapport Guardian en JSON."""

    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def analyze_prod_report(prod: Dict[str, Any]) -> None:
    """Affiche l'analyse détaillée du rapport production."""

    print("=" * 60)
    print(f"📊 PRODUCTION - {prod['service']}")
    print("=" * 60)
    print(f"Status: {prod['status']}")
    print(f"Logs analysés: {prod['logs_analyzed']} (dernière {prod['freshness']})")
    print(f"Timestamp: {prod['timestamp']}")
    print()

    # Résumé
    summary = prod["summary"]
    print(f"✅ Erreurs: {summary['errors']}")
    print(f"⚠️  Warnings: {summary['warnings']}")
    print(f"🚨 Critical signals: {summary['critical_signals']}")
    print(f"🐌 Latency issues: {summary['latency_issues']}")
    print()

    # Erreurs détaillées
    if prod["errors_detailed"]:
        print("❌ ERREURS DÉTECTÉES:")
        for err in prod["errors_detailed"]:
            print(f"   - {err['message']}")
            print(f"     Endpoint: {err.get('endpoint', 'N/A')}")
            print(
                f"     File: {err.get('file_path', 'N/A')}:{err.get('line_number', 'N/A')}"
            )
            if err.get("stack_trace"):
                print(f"     Stack: {err['stack_trace'][:200]}...")
        print()

    # Warnings détaillés
    if prod["warnings_detailed"]:
        print("⚠️  WARNINGS:")
        for warn in prod["warnings_detailed"]:
            print(f"   - {warn['message']}")
            print(f"     Endpoint: {warn.get('endpoint', 'N/A')}")
        print()

    # Patterns d'erreurs
    patterns = prod["error_patterns"]
    if patterns["most_common_error"]:
        print("🔍 PATTERNS D'ERREURS:")
        print(f"   Erreur la plus fréquente: {patterns['most_common_error']}")
        if patterns["by_endpoint"]:
            print("   Endpoints touchés:")
            for endpoint, count in list(patterns["by_endpoint"].items())[:5]:
                print(f"     - {endpoint}: {count} erreur(s)")
        print()

    # Recommandations
    if prod["recommendations"]:
        print("💡 ACTIONS RECOMMANDÉES:")
        for rec in prod["recommendations"]:
            print(f"   [{rec['priority']}] {rec['action']}")
            print(f"      → {rec['details']}")
        print()

    # Commits récents (contexte)
    if prod["recent_commits"]:
        print("📝 COMMITS RÉCENTS:")
        for commit in prod["recent_commits"][:3]:
            print(f"   - {commit['hash']}: {commit['message']} ({commit['time']})")
        print()


def analyze_unified_report(unified: Dict[str, Any]) -> None:
    """Affiche l'analyse détaillée du rapport unifié Nexus."""

    print("=" * 60)
    print("📋 VUE D'ENSEMBLE (Nexus)")
    print("=" * 60)

    # Executive summary
    exec_sum = unified["executive_summary"]
    status_icon = "✅" if exec_sum["status"] == "ok" else "🔴"
    print(f"{status_icon} {exec_sum['headline']}")
    print(
        f"Issues totales: {exec_sum['total_issues']} (Critical: {exec_sum['critical']}, Warnings: {exec_sum['warnings']})"
    )
    print()

    # Priority actions
    if unified["priority_actions"]:
        print("🔥 PRIORITY ACTIONS:")
        for action in unified["priority_actions"]:
            print(f"   [{action['priority']}] {action['description']}")
            print(f"      File: {action.get('file', 'N/A')}")
            print(f"      Fix: {action.get('recommendation', 'N/A')}")
        print()

    # Anima (Documentation)
    anima = unified["full_reports"]["anima"]
    print("📚 ANIMA (Documentation):")
    print(f"   Status: {anima['status']}")
    print(f"   Gaps trouvés: {anima['statistics']['gaps_found']}")
    print(f"   Updates proposées: {anima['statistics']['updates_proposed']}")

    if anima["documentation_gaps"]:
        print("   ⚠️  GAPS:")
        for gap in anima["documentation_gaps"][:5]:
            print(f"      - {gap.get('description', 'N/A')} ({gap.get('file', 'N/A')})")

    if anima["proposed_updates"]:
        print("   📝 UPDATES PROPOSÉES:")
        for update in anima["proposed_updates"][:5]:
            print(
                f"      - {update.get('action', 'N/A')} → {update.get('target_file', 'N/A')}"
            )
    print()

    # Neo (Intégrité)
    neo = unified["full_reports"]["neo"]
    print("🔍 NEO (Intégrité):")
    print(f"   Status: {neo['status']}")
    print(f"   Backend files changed: {neo['statistics']['backend_files_changed']}")
    print(f"   Frontend files changed: {neo['statistics']['frontend_files_changed']}")
    print(f"   Issues trouvées: {neo['statistics']['issues_found']}")

    if neo["issues"]:
        print("   ❌ ISSUES:")
        for issue in neo["issues"][:5]:
            print(
                f"      - [{issue.get('category', 'N/A')}] {issue.get('description', 'N/A')}"
            )
            print(f"        → {issue.get('recommendation', 'N/A')}")
    print()

    # Recommandations par horizon
    recs = unified["recommendations"]
    print("💡 RECOMMANDATIONS PAR HORIZON:")
    if recs["immediate"] and recs["immediate"][0] != "None - all checks passed":
        print(f"   🔥 Immediate: {', '.join(recs['immediate'])}")
    if recs["short_term"] and recs["short_term"][0] != "Continue monitoring":
        print(f"   📅 Short-term: {', '.join(recs['short_term'])}")
    if recs["long_term"] and recs["long_term"][0] != "Maintain current practices":
        print(f"   📋 Long-term: {', '.join(recs['long_term'])}")
    print()


def print_summary(prod: Dict[str, Any], unified: Dict[str, Any]) -> None:
    """Affiche un résumé concis des rapports Guardian."""

    print("📊 Production (prod_report.json)")
    print(f"- Status: {prod['status']}")
    print(f"- Erreurs: {prod['summary']['errors']}")
    print(f"- Warnings: {prod['summary']['warnings']}")
    print()
    exec_summary = unified["executive_summary"]
    print("📋 Vue d'ensemble (unified_report.json)")
    print(f"- Status: {exec_summary['status']}")
    print(f"- Issues: {exec_summary['total_issues']}")
    print()


def parse_args() -> argparse.Namespace:
    """Analyse les arguments CLI."""

    parser = argparse.ArgumentParser(
        description="Analyse les rapports Guardian générés localement."
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Affiche uniquement un résumé concis conforme aux instructions Guardian.",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help=(
            "Force l'analyse détaillée même si --summary est présent. Utile pour"
            " obtenir toutes les informations de debug."
        ),
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help="Chemin vers le dossier contenant prod_report.json et unified_report.json.",
    )
    return parser.parse_args()


def main():
    """Point d'entrée principal."""

    args = parse_args()
    reports_dir = args.reports_dir.expanduser()

    prod_path = reports_dir / "prod_report.json"
    unified_path = reports_dir / "unified_report.json"

    try:
        prod = load_report(prod_path)
        unified = load_report(unified_path)

        summary_requested = args.summary and not args.detailed
        if summary_requested:
            print_summary(prod, unified)
            return

        print("\n" + "=" * 60)
        print("📊 ANALYSE RAPPORTS GUARDIAN")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

        analyze_prod_report(prod)
        analyze_unified_report(unified)

        print("=" * 60)
        print("✅ ANALYSE TERMINÉE")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"❌ ERREUR: Fichier rapport non trouvé: {e}")
        print("   Assure-toi que les rapports Guardian ont été générés.")
        print(
            "   Lance: pwsh -File claude-plugins/integrity-docs-guardian/scripts/run_audit.ps1"
        )
    except json.JSONDecodeError as e:
        print(f"❌ ERREUR: Fichier rapport JSON invalide: {e}")
    except Exception as e:
        print(f"❌ ERREUR inattendue: {e}")


if __name__ == "__main__":
    main()
