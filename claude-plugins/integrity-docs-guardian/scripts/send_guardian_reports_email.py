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
import argparse
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
ADMIN_EMAIL = "emergence.app.ch@gmail.com"  # Email admin principal (redirige vers gonzalefernando@gmail.com)
REPORTS_DIR = Path(__file__).parent / "reports"  # Les rapports sont dans scripts/reports/


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


def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_html_report(reports: Dict[str, Optional[Dict]]) -> str:
    """Génère un rapport HTML ENRICHI avec TOUS les détails (stack traces, patterns, code snippets, etc.)"""

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
        "OK": "#44ff44",
        "WARNING": "#ffaa00",
        "CRITICAL": "#ff4444"
    }.get(global_status, "#4a9eff")

    status_emoji = format_status_emoji(global_status)
    timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    # Header HTML avec styles enrichis
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guardian Report - ÉMERGENCE V8</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background-color: #0a0e27;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: #1a1f3a;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        h1 {{
            color: #ffffff;
            margin-top: 0;
            border-bottom: 3px solid {status_color};
            padding-bottom: 15px;
        }}
        h2 {{
            color: #4a9eff;
            border-bottom: 2px solid #2a3f5f;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 16px;
            background-color: {status_color};
            color: #ffffff;
            margin-bottom: 20px;
        }}
        .summary-box {{
            background-color: #252b4a;
            border-left: 4px solid {status_color};
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .summary-item {{
            background-color: #1a1f3a;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }}
        .summary-item .number {{
            font-size: 32px;
            font-weight: bold;
            color: {status_color};
        }}
        .summary-item .label {{
            font-size: 12px;
            color: #a0a0a0;
            text-transform: uppercase;
            margin-top: 5px;
        }}
        .report-section {{
            background-color: #252b4a;
            border-left: 4px solid #3b82f6;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .report-title {{
            color: #3b82f6;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 15px;
        }}
        .error-card {{
            background-color: #2a1f1f;
            border-left: 4px solid #ff4444;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .code-block {{
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            margin: 10px 0;
            color: #c9d1d9;
        }}
        .code-block pre {{
            margin: 0;
            white-space: pre-wrap;
        }}
        .endpoint-tag {{
            display: inline-block;
            background-color: #3a3f5a;
            color: #4a9eff;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            margin: 5px 5px 5px 0;
        }}
        .file-tag {{
            display: inline-block;
            background-color: #3a3f5a;
            color: #ffaa00;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            margin: 5px 5px 5px 0;
        }}
        .error-type-tag {{
            display: inline-block;
            background-color: #3a3f5a;
            color: #ff4444;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            margin: 5px 5px 5px 0;
        }}
        .pattern-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .pattern-box {{
            background-color: #252b4a;
            padding: 15px;
            border-radius: 6px;
        }}
        .pattern-box h4 {{
            margin-top: 0;
            color: #4a9eff;
            font-size: 14px;
        }}
        .pattern-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #2a3f5f;
        }}
        .pattern-item:last-child {{
            border-bottom: none;
        }}
        .badge-count {{
            background-color: #ff4444;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: bold;
        }}
        .recommendation {{
            background-color: #252b4a;
            border-left: 4px solid #4a9eff;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        .recommendation.high {{
            border-left-color: #ff4444;
        }}
        .recommendation.medium {{
            border-left-color: #ffaa00;
        }}
        .recommendation.low {{
            border-left-color: #44ff44;
        }}
        .timestamp {{
            color: #a0a0a0;
            font-size: 12px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #2a3f5f;
            text-align: center;
            color: #a0a0a0;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Guardian Report - ÉMERGENCE V8</h1>
        <div class="status-badge">{status_emoji} Statut Global: {global_status}</div>
        <p class="timestamp">Généré le {timestamp}</p>
"""

    # Ajouter chaque rapport avec détails enrichis
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
        html += f"""
        <div class="report-section">
            <div class="report-title">{report_title}</div>
            <div class="status-badge" style="background: {status_color}; font-size: 14px; padding: 6px 12px;">{format_status_emoji(status)} {status.upper()}</div>
"""

        # Summary avec grid
        if 'summary' in report_data:
            summary = report_data['summary']
            if isinstance(summary, dict):
                html += """
            <div class="summary-box">
                <h3 style="margin-top: 0;">📊 Summary</h3>
                <div class="summary-grid">
"""
                for key, value in summary.items():
                    if key != 'status':
                        display_key = key.replace('_', ' ').title()
                        html += f"""
                    <div class="summary-item">
                        <div class="number">{escape_html(str(value))}</div>
                        <div class="label">{escape_html(display_key)}</div>
                    </div>
"""
                html += """
                </div>
            </div>
"""

        # Error Patterns (NOUVEAU - enrichi)
        if 'error_patterns' in report_data:
            patterns = report_data['error_patterns']
            if isinstance(patterns, dict) and patterns:
                html += """
            <h3>🔍 Error Patterns Analysis</h3>
            <div class="pattern-grid">
"""
                if patterns.get('by_endpoint'):
                    html += """
                <div class="pattern-box">
                    <h4>🌐 By Endpoint</h4>
"""
                    for endpoint, count in list(patterns['by_endpoint'].items())[:5]:
                        html += f"""
                    <div class="pattern-item">
                        <span class="endpoint-tag">{escape_html(endpoint)}</span>
                        <span class="badge-count">{count}</span>
                    </div>
"""
                    html += """
                </div>
"""

                if patterns.get('by_error_type'):
                    html += """
                <div class="pattern-box">
                    <h4>⚠️ By Error Type</h4>
"""
                    for error_type, count in list(patterns['by_error_type'].items())[:5]:
                        html += f"""
                    <div class="pattern-item">
                        <span class="error-type-tag">{escape_html(error_type)}</span>
                        <span class="badge-count">{count}</span>
                    </div>
"""
                    html += """
                </div>
"""

                if patterns.get('by_file'):
                    html += """
                <div class="pattern-box">
                    <h4>📁 By File</h4>
"""
                    for file_path, count in list(patterns['by_file'].items())[:5]:
                        html += f"""
                    <div class="pattern-item">
                        <span class="file-tag">{escape_html(file_path)}</span>
                        <span class="badge-count">{count}</span>
                    </div>
"""
                    html += """
                </div>
"""
                html += """
            </div>
"""

        # Detailed Errors (NOUVEAU - enrichi avec stack traces)
        if 'errors_detailed' in report_data:
            errors = report_data['errors_detailed']
            if isinstance(errors, list) and len(errors) > 0:
                html += f"""
            <h3>❌ Detailed Errors (Top {len(errors)})</h3>
"""
                for error in errors[:10]:  # Max 10 erreurs détaillées
                    html += """
            <div class="error-card">
"""
                    if error.get('timestamp'):
                        html += f"""
                <p><strong>⏰ Time:</strong> <span class="timestamp">{escape_html(error['timestamp'])}</span></p>
"""
                    if error.get('severity'):
                        html += f"""
                <p><strong>🔴 Severity:</strong> {escape_html(error['severity'])}</p>
"""
                    if error.get('endpoint'):
                        method = error.get('http_method', '')
                        html += f"""
                <p><strong>🌐 Endpoint:</strong> <span class="endpoint-tag">{escape_html(method)} {escape_html(error['endpoint'])}</span></p>
"""
                    if error.get('error_type'):
                        html += f"""
                <p><strong>⚠️ Type:</strong> <span class="error-type-tag">{escape_html(error['error_type'])}</span></p>
"""
                    if error.get('file_path'):
                        line = error.get('line_number', '')
                        html += f"""
                <p><strong>📁 File:</strong> <span class="file-tag">{escape_html(error['file_path'])}:{line}</span></p>
"""
                    if error.get('message'):
                        html += f"""
                <p><strong>💬 Message:</strong></p>
                <div class="code-block"><pre>{escape_html(error['message'])}</pre></div>
"""
                    if error.get('stack_trace'):
                        html += f"""
                <p><strong>📚 Stack Trace:</strong></p>
                <div class="code-block"><pre>{escape_html(error['stack_trace'])}</pre></div>
"""
                    if error.get('request_id'):
                        html += f"""
                <p><strong>🔍 Request ID:</strong> <code>{escape_html(error['request_id'])}</code></p>
"""
                    html += """
            </div>
"""

        # Code Snippets (NOUVEAU - enrichi)
        if 'code_snippets' in report_data:
            snippets = report_data['code_snippets']
            if isinstance(snippets, list) and len(snippets) > 0:
                html += """
            <h3>💻 Suspect Code Snippets</h3>
"""
                for snippet in snippets[:5]:  # Max 5 snippets
                    error_count = snippet.get('error_count', 0)
                    html += f"""
            <div class="pattern-box">
                <h4>📁 {escape_html(snippet.get('file', ''))} <span style="color: #ff4444;">({error_count} errors)</span></h4>
                <p style="font-size: 12px; color: #a0a0a0;">Line {snippet.get('line', '')} (showing lines {snippet.get('start_line', '')}-{snippet.get('end_line', '')})</p>
                <div class="code-block"><pre>{escape_html(snippet.get('code_snippet', ''))}</pre></div>
            </div>
"""

        # Recent Commits (NOUVEAU - enrichi)
        if 'recent_commits' in report_data:
            commits = report_data['recent_commits']
            if isinstance(commits, list) and len(commits) > 0:
                html += """
            <h3>🔀 Recent Commits (Potential Culprits)</h3>
"""
                for commit in commits[:5]:  # Max 5 commits
                    html += f"""
            <div class="pattern-box" style="margin-bottom: 10px;">
                <span style="color: #4a9eff; font-family: monospace;">{escape_html(commit.get('hash', ''))}</span>
                by <span style="color: #ffaa00;">{escape_html(commit.get('author', ''))}</span>
                <span class="timestamp">({escape_html(commit.get('time', ''))})</span>
                <p style="margin: 5px 0 0 0;">{escape_html(commit.get('message', ''))}</p>
            </div>
"""

        # Recommendations (ENRICHI avec commandes, fichiers affectés, etc.)
        if 'recommendations' in report_data:
            recommendations = report_data['recommendations']
            if isinstance(recommendations, list) and len(recommendations) > 0:
                html += """
            <h3>💡 Recommendations</h3>
"""
                for rec in recommendations:
                    priority = rec.get('priority', 'MEDIUM')
                    priority_class = priority.lower()
                    action = rec.get('action', '')
                    details = rec.get('details', '')

                    html += f"""
            <div class="recommendation {priority_class}">
                <p><strong>🚨 [{escape_html(priority)}] {escape_html(action)}</strong></p>
                <p>{escape_html(details)}</p>
"""
                    if rec.get('command'):
                        html += f"""
                <p><strong>Command:</strong></p>
                <div class="code-block"><pre>{escape_html(rec['command'])}</pre></div>
"""
                    if rec.get('rollback_command'):
                        html += f"""
                <p><strong>Rollback Command:</strong></p>
                <div class="code-block"><pre>{escape_html(rec['rollback_command'])}</pre></div>
"""
                    if rec.get('suggested_fix'):
                        html += f"""
                <p><strong>Suggested Fix:</strong> {escape_html(rec['suggested_fix'])}</p>
"""
                    if rec.get('affected_endpoints'):
                        html += """
                <p><strong>Affected Endpoints:</strong></p>
"""
                        for endpoint in rec['affected_endpoints']:
                            html += f"""
                <span class="endpoint-tag">{escape_html(endpoint)}</span>
"""
                    if rec.get('affected_files'):
                        html += """
                <p><strong>Affected Files:</strong></p>
"""
                        for file_path in rec['affected_files']:
                            html += f"""
                <span class="file-tag">{escape_html(file_path)}</span>
"""
                    if rec.get('suggested_investigation'):
                        html += """
                <p><strong>Investigation Steps:</strong></p>
                <ul>
"""
                        for step in rec['suggested_investigation']:
                            html += f"""
                    <li>{escape_html(step)}</li>
"""
                        html += """
                </ul>
"""
                    html += """
            </div>
"""

        # Timestamp du rapport
        if 'timestamp' in report_data:
            html += f"""
            <p class="timestamp">Dernier scan: {escape_html(report_data['timestamp'])}</p>
"""

        html += """
        </div>
"""

    # Footer
    html += f"""
        <div class="footer">
            <p><strong>🤖 Guardian System 3.0.0 - Automated Production Monitoring</strong></p>
            <p>ÉMERGENCE V8 Production Monitoring | Généré {timestamp}</p>
            <p style="margin-top: 10px; font-size: 11px;">
                Rapport enrichi avec stack traces, patterns, code snippets et recommandations détaillées.<br>
                Pour toute question: emergence.app.ch@gmail.com
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
    # Parse arguments
    parser = argparse.ArgumentParser(description="Send Guardian reports via email")
    parser.add_argument(
        "--to",
        type=str,
        default=ADMIN_EMAIL,
        help=f"Email recipient (default: {ADMIN_EMAIL})"
    )
    args = parser.parse_args()

    # Override ADMIN_EMAIL si spécifié
    global ADMIN_EMAIL
    if args.to:
        ADMIN_EMAIL = args.to
        print(f"📧 Sending reports to: {ADMIN_EMAIL}")

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
