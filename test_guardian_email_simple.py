#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script simple pour envoyer un email Guardian avec rapport enrichi
Sans imports du router qui causent des problèmes
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Charger les variables d'environnement
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ajouter le backend au path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService


def load_report(report_name: str):
    """Load a Guardian report JSON file"""
    reports_dir = Path(__file__).parent / "reports"
    report_path = reports_dir / report_name

    if not report_path.exists():
        print(f"⚠️  Report file not found: {report_path}")
        return None

    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded report: {report_name}")
        return data
    except Exception as e:
        print(f"❌ Error loading {report_name}: {e}")
        return None


async def main():
    """Test sending Guardian email with enriched prod_report.json"""

    print("=" * 70)
    print("TEST GUARDIAN EMAIL - Rapport Enrichi")
    print("=" * 70)
    print()

    # Load all reports
    reports = {}
    report_files = [
        'prod_report.json',  # Enriched test report
        'global_report.json',
        'integrity_report.json',
        'docs_report.json',
        'unified_report.json',
        'orchestration_report.json',
        'usage_report.json',
    ]

    for report_file in report_files:
        report_data = load_report(report_file)
        if report_data:
            # Keep .json suffix (EmailService expects 'prod_report.json' not 'prod_report')
            reports[report_file] = report_data
            if report_file == 'usage_report.json':
                reports['usage_stats'] = report_data  # For template

    if not reports.get('prod_report.json'):
        print("❌ prod_report.json is required for testing")
        print(f"   Available reports: {list(reports.keys())}")
        return False

    print()
    print(f"📊 Loaded {len([r for r in reports.values() if r])} reports")
    print()

    # Initialize email service
    email_service = EmailService()

    if not email_service.is_enabled():
        print("❌ Email service not enabled")
        print("   Set EMAIL_ENABLED=1 in .env")
        return False

    # Send email
    to_email = "emergence.app.ch@gmail.com"
    print(f"📧 Sending Guardian report to: {to_email}")
    print()

    # Prepare context for template
    # Determine global status
    global_status = "OK"
    if reports.get('prod_report'):
        prod_status = reports['prod_report'].get('status', '').upper()
        if prod_status in ['CRITICAL', 'ERROR']:
            global_status = "CRITICAL"
        elif prod_status in ['WARNING', 'DEGRADED']:
            global_status = "WARNING"

    # Build summary
    summary = {
        'critical_count': 0,
        'warning_count': 0,
        'active_users': 0
    }

    if reports.get('prod_report', {}).get('summary'):
        prod_summary = reports['prod_report']['summary']
        summary['critical_count'] = prod_summary.get('critical_signals', 0)
        summary['warning_count'] = prod_summary.get('warnings', 0)

    if reports.get('usage_stats', {}).get('summary'):
        usage_summary = reports['usage_stats']['summary']
        summary['active_users'] = usage_summary.get('active_users_count', 0)

    success = await email_service.send_guardian_report(
        to_email=to_email,
        reports=reports,
        base_url="https://emergence-app-486095406755.europe-west1.run.app"
    )

    print()
    print("=" * 70)
    if success:
        print("✅ Email envoyé avec succès!")
        print()
        print("📊 Le rapport devrait contenir:")
        print("   - ❌ Erreurs détaillées avec stack traces (3 exemples)")
        print("   - 🔍 Analyse de patterns (endpoint/fichier/type)")
        print("   - 💻 Code snippets suspects (2 fichiers)")
        print("   - 🔀 Commits récents (3 commits)")
        print()
        print("👀 Vérifie ta boîte mail: emergence.app.ch@gmail.com")
        print()
        print("📧 Si l'email n'apparaît pas, check:")
        print("   - Dossier Spam/Junk")
        print("   - Que SMTP_USER et SMTP_PASSWORD sont corrects dans .env")
    else:
        print("❌ Échec de l'envoi de l'email")
        print()
        print("⚠️  Vérifie que les variables d'environnement sont configurées:")
        print("   - EMAIL_ENABLED=1")
        print("   - SMTP_HOST=smtp.gmail.com")
        print("   - SMTP_PORT=587")
        print("   - SMTP_USER=ton-email@gmail.com")
        print("   - SMTP_PASSWORD=ton-app-password")
    print("=" * 70)

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
