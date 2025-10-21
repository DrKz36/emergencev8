#!/usr/bin/env python3
"""
Analyse complète de la structure Guardian - Audit des rapports et workflows
"""
import os
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

REPO_ROOT = Path(__file__).parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
GUARDIAN_REPORTS_DIR = REPO_ROOT / "claude-plugins" / "integrity-docs-guardian" / "reports"

def analyze_reports():
    """Analyse tous les rapports Guardian"""
    print("=" * 80)
    print("ANALYSE STRUCTURE GUARDIAN - AUDIT COMPLET")
    print("=" * 80)
    print()

    # Analyser reports/
    print("📊 RAPPORTS DANS reports/:")
    print("-" * 80)
    reports = {}
    for report in sorted(REPORTS_DIR.glob("*.json")):
        size = report.stat().st_size
        try:
            with open(report, 'r', encoding='utf-8') as f:
                data = json.load(f)
                timestamp = data.get('timestamp', 'N/A')
                status = data.get('status') or data.get('executive_summary', {}).get('status', 'N/A')
        except:
            timestamp = 'N/A'
            status = 'N/A'

        reports[report.name] = {
            'size': size,
            'timestamp': timestamp,
            'status': status,
            'location': 'reports/'
        }
        print(f"{report.name:50} {size:>10} bytes   Status: {str(status):10}   TS: {str(timestamp)[:19]}")

    print()
    print("📊 RAPPORTS DANS claude-plugins/.../reports/:")
    print("-" * 80)
    guardian_reports = {}
    for report in sorted(GUARDIAN_REPORTS_DIR.glob("*.json")):
        size = report.stat().st_size
        try:
            with open(report, 'r', encoding='utf-8') as f:
                data = json.load(f)
                timestamp = data.get('timestamp', 'N/A')
                status = data.get('status') or data.get('executive_summary', {}).get('status', 'N/A')
        except:
            timestamp = 'N/A'
            status = 'N/A'

        guardian_reports[report.name] = {
            'size': size,
            'timestamp': timestamp,
            'status': status,
            'location': 'guardian/'
        }
        print(f"{report.name:50} {size:>10} bytes   Status: {str(status):10}   TS: {str(timestamp)[:19]}")

    print()
    print("🔍 ANALYSE DES DOUBLONS:")
    print("-" * 80)
    common_files = set(reports.keys()) & set(guardian_reports.keys())
    print(f"Fichiers présents dans LES DEUX emplacements: {len(common_files)}")
    for filename in sorted(common_files):
        r1 = reports[filename]
        r2 = guardian_reports[filename]
        diff = abs(r1['size'] - r2['size'])
        status_icon = "✅ SYNC" if diff < 100 else "⚠️ DIFF"
        print(f"  {status_icon} {filename:45} Diff: {diff:>6} bytes")

    print()
    print("📁 FICHIERS UNIQUES:")
    print("-" * 80)
    only_reports = set(reports.keys()) - set(guardian_reports.keys())
    only_guardian = set(guardian_reports.keys()) - set(reports.keys())

    if only_reports:
        print("Seulement dans reports/:")
        for f in sorted(only_reports):
            print(f"  - {f}")

    if only_guardian:
        print("Seulement dans guardian/:")
        for f in sorted(only_guardian):
            print(f"  - {f}")

    print()
    print("📊 STATISTIQUES:")
    print("-" * 80)
    print(f"Total rapports reports/: {len(reports)}")
    print(f"Total rapports guardian/: {len(guardian_reports)}")
    print(f"Doublons: {len(common_files)}")
    print(f"Uniques reports/: {len(only_reports)}")
    print(f"Uniques guardian/: {len(only_guardian)}")

    print()
    print("🔍 CATÉGORISATION DES RAPPORTS:")
    print("-" * 80)

    categories = {
        'core': [],  # Rapports core Guardian (prod, docs, integrity, unified)
        'archived': [],  # Rapports historiques/archivés
        'test': [],  # Rapports de test
        'audit': [],  # Rapports d'audit (cost, etc.)
        'deprecated': []  # Rapports obsolètes
    }

    all_reports = set(reports.keys()) | set(guardian_reports.keys())

    for filename in all_reports:
        if filename in ['prod_report.json', 'docs_report.json', 'integrity_report.json', 'unified_report.json', 'global_report.json']:
            categories['core'].append(filename)
        elif 'test' in filename.lower():
            categories['test'].append(filename)
        elif filename.startswith('consolidated_report') or filename.startswith('orchestration_report'):
            categories['archived'].append(filename)
        elif 'cost' in filename or 'audit' in filename:
            categories['audit'].append(filename)
        elif 'cleanup' in filename or 'memory_phase3' in filename or 'verification' in filename:
            categories['deprecated'].append(filename)
        else:
            categories['deprecated'].append(filename)

    for cat, files in categories.items():
        if files:
            print(f"\n{cat.upper()}:")
            for f in sorted(files):
                print(f"  - {f}")

    print()
    print("💡 RECOMMANDATIONS:")
    print("-" * 80)

    # Recommandations
    if len(common_files) > 5:
        print(f"⚠️ {len(common_files)} fichiers dupliqués entre les 2 emplacements")
        print("   → Unifier l'emplacement des rapports (garder reports/ uniquement)")

    if categories['deprecated']:
        print(f"\n⚠️ {len(categories['deprecated'])} rapports potentiellement obsolètes/à archiver:")
        for f in categories['deprecated'][:5]:
            print(f"   - {f}")

    if categories['archived']:
        print(f"\n📦 {len(categories['archived'])} rapports historiques à archiver:")
        for f in categories['archived']:
            print(f"   - {f}")

    print()
    print("=" * 80)

    return {
        'reports': reports,
        'guardian_reports': guardian_reports,
        'common_files': common_files,
        'categories': categories
    }

if __name__ == "__main__":
    analyze_reports()
