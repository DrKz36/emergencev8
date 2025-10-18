#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guardian Reports Email Sender
Envoie automatiquement les rapports Guardian par email aux administrateurs
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Fix encoding pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Charger les variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    repo_root = Path(__file__).parent.parent.parent.parent
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Fichier .env chargé depuis {env_path}")
except ImportError:
    print("⚠️  python-dotenv non installé, tentative de lecture .env manuelle")
    # Fallback: lecture manuelle du .env
    repo_root = Path(__file__).parent.parent.parent.parent
    env_path = repo_root / ".env"
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Ajouter le chemin du backend pour importer EmailService
backend_path = Path(__file__).parent.parent.parent.parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService, build_email_config_from_env

# Configuration
ADMIN_EMAIL = "gonzalefernando@gmail.com"  # Email admin uniquement
REPORTS_DIR = Path(__file__).parent.parent / "reports"


def load_report(report_path: Path) -> Optional[Dict]:
    """Charge un rapport JSON s'il existe"""
    try:
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"⚠️ Erreur lors du chargement de {report_path.name}: {e}")
        return None


def format_status_emoji(status: str) -> str:
    """Retourne un emoji selon le statut"""
    status_lower = status.lower()
    if status_lower in ['ok', 'healthy', 'success']:
        return '✅'
    elif status_lower in ['warning', 'degraded']:
        return '⚠️'
    elif status_lower in ['error', 'critical', 'failed']:
        return '🚨'
    else:
        return '📊'


def format_report_summary(report_name: str, report_data: Optional[Dict]) -> str:
    """Formate un résumé d'un rapport pour l'email"""
    if not report_data:
        return f"  • {report_name}: Non disponible\n"

    status = report_data.get('status', 'unknown')
    emoji = format_status_emoji(status)

    summary = f"  • {report_name}: {emoji} {status.upper()}\n"

    # Ajouter des détails spécifiques selon le type de rapport
    if 'summary' in report_data:
        summary_data = report_data['summary']
        if isinstance(summary_data, dict):
            if 'errors' in summary_data:
                summary += f"    - Erreurs: {summary_data['errors']}\n"
            if 'warnings' in summary_data:
                summary += f"    - Warnings: {summary_data['warnings']}\n"
            if 'critical_signals' in summary_data:
                summary += f"    - Signaux critiques: {summary_data['critical_signals']}\n"
            if 'total_issues' in summary_data:
                summary += f"    - Problèmes totaux: {summary_data['total_issues']}\n"

    if 'documentation_gaps' in report_data:
        gaps = report_data['documentation_gaps']
        if isinstance(gaps, list):
            high_severity = sum(1 for gap in gaps if gap.get('severity') == 'high')
            if high_severity > 0:
                summary += f"    - Gaps documentation (high): {high_severity}\n"

    if 'integrity_issues' in report_data:
        issues = report_data['integrity_issues']
        if isinstance(issues, list) and len(issues) > 0:
            summary += f"    - Problèmes d'intégrité: {len(issues)}\n"

    return summary


def generate_html_report(reports: Dict[str, Optional[Dict]]) -> str:
    """Génère un rapport HTML stylisé des rapports Guardian"""

    # Déterminer le statut global
    global_status = "OK"
    for report_data in reports.values():
        if report_data:
            status = report_data.get('status', '').lower()
            if status in ['critical', 'error', 'failed']:
                global_status = "CRITICAL"
                break
            elif status in ['warning', 'degraded'] and global_status != "CRITICAL":
                global_status = "WARNING"

    status_color = {
        "OK": "#10b981",
        "WARNING": "#f59e0b",
        "CRITICAL": "#ef4444"
    }.get(global_status, "#6b7280")

    status_emoji = format_status_emoji(global_status)

    timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    # Construction du HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 40px;
            color: #e2e8f0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #3b82f6;
            margin: 0;
            font-size: 28px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            margin: 10px 0;
            background: {status_color};
            color: white;
        }}
        .report-section {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #3b82f6;
        }}
        .report-title {{
            color: #3b82f6;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .report-status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .status-ok {{
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }}
        .status-warning {{
            background: rgba(245, 158, 11, 0.2);
            color: #f59e0b;
        }}
        .status-critical {{
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }}
        .detail-item {{
            margin: 8px 0;
            padding-left: 20px;
            color: #cbd5e1;
        }}
        .timestamp {{
            color: #94a3b8;
            font-size: 14px;
            margin-top: 10px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 14px;
            color: #94a3b8;
            text-align: center;
        }}
        .recommendations {{
            background: rgba(59, 130, 246, 0.1);
            border-left: 4px solid #3b82f6;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
        }}
        .rec-item {{
            margin: 10px 0;
            padding: 10px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Rapport Guardian ÉMERGENCE V8</h1>
            <div class="status-badge">{status_emoji} Statut Global: {global_status}</div>
            <p class="timestamp">Généré le {timestamp}</p>
        </div>
"""

    # Ajouter chaque rapport
    report_names = {
        'global_report.json': 'Rapport Global (Master)',
        'prod_report.json': 'Production Guardian',
        'integrity_report.json': 'Intégrité (Neo)',
        'docs_report.json': 'Documentation (Anima)',
        'unified_report.json': 'Rapport Unifié (Nexus)',
        'orchestration_report.json': 'Orchestration'
    }

    for report_file, report_title in report_names.items():
        report_data = reports.get(report_file)
        if not report_data:
            continue

        status = report_data.get('status', 'unknown')
        status_class = 'status-ok'
        if status.lower() in ['warning', 'degraded']:
            status_class = 'status-warning'
        elif status.lower() in ['critical', 'error', 'failed']:
            status_class = 'status-critical'

        html += f"""
        <div class="report-section">
            <div class="report-title">{report_title}</div>
            <span class="report-status {status_class}">{format_status_emoji(status)} {status.upper()}</span>
"""

        # Ajouter les détails selon le type de rapport
        if 'summary' in report_data:
            summary = report_data['summary']
            if isinstance(summary, dict):
                html += "            <div style='margin-top: 10px;'>\n"
                for key, value in summary.items():
                    if key != 'status':
                        display_key = key.replace('_', ' ').title()
                        html += f"                <div class='detail-item'>• {display_key}: {value}</div>\n"
                html += "            </div>\n"

        # Recommendations
        if 'recommendations' in report_data:
            recommendations = report_data['recommendations']
            if isinstance(recommendations, list) and len(recommendations) > 0:
                html += "            <div class='recommendations' style='margin-top: 15px;'>\n"
                html += "                <strong>📋 Recommandations:</strong>\n"
                for rec in recommendations[:3]:  # Max 3 recommandations
                    if isinstance(rec, dict):
                        priority = rec.get('priority', 'MEDIUM')
                        action = rec.get('action', rec.get('recommendation', ''))
                        html += f"                <div class='rec-item'>\n"
                        html += f"                    <strong>[{priority}]</strong> {action}\n"
                        if 'details' in rec:
                            html += f"                    <div style='margin-top: 5px; font-size: 13px; color: #94a3b8;'>{rec['details']}</div>\n"
                        html += "                </div>\n"
                html += "            </div>\n"

        # Timestamp du rapport
        if 'timestamp' in report_data:
            html += f"            <div class='timestamp'>Dernier scan: {report_data['timestamp']}</div>\n"

        html += "        </div>\n"

    # Footer
    html += """
        <div class="footer">
            <p><strong>🤖 Guardian Autonomous Monitoring System</strong></p>
            <p>Ce rapport est envoyé automatiquement aux administrateurs uniquement.</p>
            <p style="margin-top: 15px; font-size: 12px;">
                ÉMERGENCE V8 - Guardian System<br>
                Pour toute question: gonzalefernando@gmail.com
            </p>
        </div>
    </div>
</body>
</html>
"""

    return html


def generate_text_report(reports: Dict[str, Optional[Dict]]) -> str:
    """Génère un rapport texte simple des rapports Guardian"""

    timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    text = f"""
🛡️ RAPPORT GUARDIAN ÉMERGENCE V8
{'='*60}

Généré le: {timestamp}

"""

    # Ajouter chaque rapport
    report_names = {
        'global_report.json': 'RAPPORT GLOBAL (MASTER)',
        'prod_report.json': 'PRODUCTION GUARDIAN',
        'integrity_report.json': 'INTÉGRITÉ (NEO)',
        'docs_report.json': 'DOCUMENTATION (ANIMA)',
        'unified_report.json': 'RAPPORT UNIFIÉ (NEXUS)',
        'orchestration_report.json': 'ORCHESTRATION'
    }

    for report_file, report_title in report_names.items():
        report_data = reports.get(report_file)
        if not report_data:
            continue

        text += f"\n{report_title}\n"
        text += "-" * len(report_title) + "\n"
        text += format_report_summary(report_file, report_data)

        # Recommendations
        if 'recommendations' in report_data:
            recommendations = report_data['recommendations']
            if isinstance(recommendations, list) and len(recommendations) > 0:
                text += "\n  📋 Recommandations:\n"
                for rec in recommendations[:3]:
                    if isinstance(rec, dict):
                        priority = rec.get('priority', 'MEDIUM')
                        action = rec.get('action', rec.get('recommendation', ''))
                        text += f"    [{priority}] {action}\n"

        text += "\n"

    text += """
{'='*60}

🤖 Guardian Autonomous Monitoring System
Ce rapport est envoyé automatiquement aux administrateurs uniquement.

ÉMERGENCE V8 - Guardian System
Pour toute question: gonzalefernando@gmail.com
"""

    return text


async def send_guardian_reports():
    """Charge tous les rapports Guardian et les envoie par email"""

    print("📧 Préparation de l'envoi des rapports Guardian...")

    # Charger tous les rapports disponibles
    report_files = [
        'global_report.json',
        'prod_report.json',
        'integrity_report.json',
        'docs_report.json',
        'unified_report.json',
        'orchestration_report.json'
    ]

    reports = {}
    for report_file in report_files:
        report_path = REPORTS_DIR / report_file
        report_data = load_report(report_path)
        if report_data:
            reports[report_file] = report_data
            print(f"  ✅ {report_file} chargé")
        else:
            print(f"  ⚠️ {report_file} non trouvé ou invalide")

    if not reports:
        print("❌ Aucun rapport disponible à envoyer")
        return False

    # Générer les versions HTML et texte
    html_body = generate_html_report(reports)
    text_body = generate_text_report(reports)

    # Initialiser le service email
    email_service = EmailService()

    if not email_service.is_enabled():
        print("❌ Service email non activé ou mal configuré")
        print("   Vérifiez les variables d'environnement:")
        print("   - EMAIL_ENABLED=1")
        print("   - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD")
        return False

    print(f"\n📤 Envoi du rapport à: {ADMIN_EMAIL}")

    # Envoyer l'email
    subject = f"🛡️ Rapport Guardian ÉMERGENCE - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    success = await email_service.send_custom_email(
        to_email=ADMIN_EMAIL,
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

    if success:
        print(f"✅ Rapport Guardian envoyé avec succès à {ADMIN_EMAIL}")
        return True
    else:
        print(f"❌ Échec de l'envoi du rapport")
        return False


async def main():
    """Point d'entrée principal"""
    try:
        success = await send_guardian_reports()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
