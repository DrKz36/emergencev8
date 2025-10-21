#!/usr/bin/env python3
"""
Guardian Email Report - Génère et envoie un rapport Guardian complet par email
Exécute tous les guardians, génère les rapports, et envoie par email
"""
import asyncio
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import json
import hashlib
import hmac
from typing import Any, Iterable, Optional, Sequence

# Charger .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Ajouter backend au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'backend'))

# Secret pour signer les tokens (doit matcher celui du backend)
GUARDIAN_SECRET = os.getenv("GUARDIAN_SECRET", "dev-secret-change-in-prod")


def normalize_status(raw_status: Any) -> str:
    if raw_status is None:
        return 'UNKNOWN'
    status_str = str(raw_status).strip()
    if not status_str:
        return 'UNKNOWN'
    upper = status_str.upper()
    if upper in {'OK', 'HEALTHY', 'SUCCESS'}:
        return 'OK'
    if upper in {'WARNING', 'WARN'}:
        return 'WARNING'
    if upper in {'NEEDS_UPDATE', 'STALE'}:
        return 'NEEDS_UPDATE'
    if upper in {'ERROR', 'FAILED', 'FAILURE'}:
        return 'ERROR'
    if upper in {'CRITICAL', 'SEVERE'}:
        return 'CRITICAL'
    return upper


def resolve_path(data: Any, path: Sequence[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def extract_status(report: Any, fallback_paths: Optional[Iterable[Sequence[str]]] = None) -> str:
    if not isinstance(report, dict):
        return 'UNKNOWN'

    candidates = [report.get('status')]
    if fallback_paths:
        for path in fallback_paths:
            candidates.append(resolve_path(report, path))

    for candidate in candidates:
        normalized = normalize_status(candidate)
        if normalized != 'UNKNOWN':
            return normalized

    return 'UNKNOWN'


def generate_fix_token(report_id: str) -> str:
    """Génère un token sécurisé pour autoriser l'auto-fix"""
    timestamp = str(int(datetime.now().timestamp()))
    data = f"{report_id}:{timestamp}"
    signature = hmac.new(
        GUARDIAN_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{data}:{signature}"

async def run_all_guardians():
    """Exécute tous les guardians pour générer des rapports frais"""
    print("Execution des Guardians...")

    scripts_dir = Path(__file__).parent.parent / 'claude-plugins' / 'integrity-docs-guardian' / 'scripts'

    guardians = [
        ('ProdGuardian', 'prod_guardian.py'),
        ('Anima', 'anima.py'),
        ('Neo', 'neo.py'),
        ('Nexus', 'nexus_coordinator.py')
    ]

    for name, script in guardians:
        script_path = scripts_dir / script
        if script_path.exists():
            print(f"  Lancement {name}...")
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(Path(__file__).parent.parent),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    print(f"    OK {name}")
                else:
                    print(f"    WARNING {name}: {result.stderr[:100]}")
            except Exception as e:
                print(f"    ERROR {name}: {e}")
        else:
            print(f"  SKIP {name} (script non trouvé)")

async def load_reports():
    """Charge tous les rapports Guardian"""
    reports_dir = Path(__file__).parent.parent / 'reports'

    reports = {}
    report_files = {
        'prod': 'prod_report.json',
        'docs': 'docs_report.json',
        'integrity': 'integrity_report.json',
        'unified': 'unified_report.json',
        'orchestration': 'orchestration_report.json',
        'global': 'global_report.json'
    }

    for key, filename in report_files.items():
        filepath = reports_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # S'assurer que c'est un dict, pas une string
                    if isinstance(data, dict):
                        reports[key] = data
                    else:
                        print(f"  WARNING: {filename} n'est pas un dict valide")
                        reports[key] = None
            except Exception as e:
                print(f"  WARNING: Impossible de charger {filename}: {e}")
                reports[key] = None
        else:
            reports[key] = None

    return reports

def format_status_badge(status):
    """Retourne un badge HTML pour le status"""
    colors = {
        'OK': '#10b981',
        'WARNING': '#f59e0b',
        'CRITICAL': '#ef4444',
        'ERROR': '#ef4444',
        'NEEDS_UPDATE': '#f59e0b',
        'UNKNOWN': '#6b7280'
    }

    emojis = {
        'OK': '✅',
        'WARNING': '⚠️',
        'CRITICAL': '🚨',
        'ERROR': '🚨',
        'NEEDS_UPDATE': '📊',
        'UNKNOWN': '❓'
    }

    color = colors.get(status, '#6b7280')
    emoji = emojis.get(status, '📊')

    return f'<span style="background:{color};color:white;padding:4px 12px;border-radius:12px;font-weight:600;font-size:14px;">{emoji} {status}</span>'

async def generate_html_email(reports):
    """Génère le HTML de l'email Guardian"""
    timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    # Extraire les infos principales avec safe access
    global_report = reports.get('global')
    prod_report = reports.get('prod')
    docs_report = reports.get('docs')
    integrity_report = reports.get('integrity')
    unified_report = reports.get('unified')

    global_status = extract_status(global_report, fallback_paths=[('executive_summary', 'status')])
    prod_status = extract_status(prod_report)
    docs_status = extract_status(docs_report)
    integrity_status = extract_status(integrity_report)
    unified_status = extract_status(unified_report, fallback_paths=[('executive_summary', 'status')])

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
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
            border-bottom: 2px solid rgba(255,255,255,0.1);
            padding-bottom: 20px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .timestamp {{
            color: #94a3b8;
            font-size: 14px;
        }}
        .section {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid #3b82f6;
        }}
        .section-title {{
            color: #3b82f6;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .metric {{
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .metric:last-child {{
            border-bottom: none;
        }}
        .metric-label {{
            color: #94a3b8;
            font-size: 14px;
        }}
        .metric-value {{
            color: #e2e8f0;
            font-weight: 600;
            font-size: 16px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
            color: #94a3b8;
            font-size: 14px;
        }}
        .recommendations {{
            background: rgba(251, 191, 36, 0.1);
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }}
        .recommendations-title {{
            color: #f59e0b;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        ul {{
            margin: 5px 0;
            padding-left: 20px;
        }}
        li {{
            margin: 5px 0;
            color: #cbd5e1;
        }}
        .action-button {{
            display: inline-block;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 15px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 16px;
            margin: 20px 0;
            transition: transform 0.2s;
        }}
        .action-button:hover {{
            transform: translateY(-2px);
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        }}
        .details-section {{
            background: rgba(239, 68, 68, 0.1);
            border-left: 4px solid #ef4444;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .details-title {{
            color: #ef4444;
            font-weight: 600;
            font-size: 18px;
            margin-bottom: 15px;
        }}
        .problem-item {{
            background: rgba(0, 0, 0, 0.2);
            padding: 12px;
            border-radius: 6px;
            margin: 10px 0;
        }}
        .problem-priority {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
        .priority-CRITICAL {{ background: #dc2626; color: white; }}
        .priority-HIGH {{ background: #f59e0b; color: white; }}
        .priority-MEDIUM {{ background: #3b82f6; color: white; }}
        .priority-LOW {{ background: #6b7280; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Guardian ÉMERGENCE V8</h1>
            <div class="timestamp">Rapport généré le {timestamp}</div>
            <div style="margin-top:15px;">
                {format_status_badge(global_status)}
            </div>
        </div>

        <!-- Production Guardian -->
        <div class="section">
            <div class="section-title">
                <span>☁️ Production Cloud Run</span>"""

    # Safe access pour prod status
    total_logs = 0
    error_count = 0
    warning_count = 0
    critical_count = 0

    if prod_report and isinstance(prod_report, dict):
        total_logs = prod_report.get('logs_analyzed', 0)
        summary = prod_report.get('summary')
        if summary and isinstance(summary, dict):
            error_count = summary.get('errors', 0)
            warning_count = summary.get('warnings', 0)
            critical_count = summary.get('critical_signals', 0)

    html += f"""
                {format_status_badge(prod_status)}
            </div>
            <div class="metric">
                <div class="metric-label">Logs analysés</div>
                <div class="metric-value">{total_logs}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Erreurs détectées</div>
                <div class="metric-value">{error_count}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Warnings</div>
                <div class="metric-value">{warning_count}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Problèmes critiques</div>
                <div class="metric-value">{critical_count}</div>
            </div>
"""

    # Recommandations Production avec safe access
    prod_recs = []
    if prod_report and isinstance(prod_report, dict):
        recs = prod_report.get('recommendations')
        if recs and isinstance(recs, list):
            prod_recs = recs

    if prod_recs:
        html += """
            <div class="recommendations">
                <div class="recommendations-title">📋 Recommandations</div>
                <ul>
"""
        for rec in prod_recs[:3]:  # Top 3
            if isinstance(rec, dict):
                priority = rec.get('priority', 'LOW')
                action = rec.get('action', 'N/A')
                html += f"                    <li>[{priority}] {action}</li>\n"
        html += """
                </ul>
            </div>
"""

    html += """
        </div>

        <!-- Documentation (Anima) -->
        <div class="section">
            <div class="section-title">
                <span>📚 Documentation (Anima)</span>
"""

    # Safe access avec vérification de type
    html += f"                {format_status_badge(docs_status)}\n"

    html += """
            </div>
            <div class="metric">
                <div class="metric-label">Gaps détectés</div>
"""

    # Safe access avec vérification de type
    gaps_count = 0
    if docs_report and isinstance(docs_report, dict):
        documentation_gaps = docs_report.get('documentation_gaps')
        if isinstance(documentation_gaps, list):
            gaps_count = len(documentation_gaps)

    html += f"                <div class='metric-value'>{gaps_count}</div>\n"

    html += """
            </div>
            <div class="metric">
                <div class="metric-label">Mises à jour proposées</div>
"""

    # Safe access avec vérification de type
    updates_count = 0
    if docs_report and isinstance(docs_report, dict):
        proposed_updates = docs_report.get('proposed_updates')
        if isinstance(proposed_updates, list):
            updates_count = len(proposed_updates)

    html += f"                <div class='metric-value'>{updates_count}</div>\n"

    html += """
            </div>
        </div>

        <!-- Intégrité (Neo) -->
        <div class="section">
            <div class="section-title">
                <span>🔐 Intégrité Système (Neo)</span>
"""

    # Safe access avec vérification de type
    html += f"                {format_status_badge(integrity_status)}\n"

    html += """
            </div>
            <div class="metric">
                <div class="metric-label">Problèmes critiques</div>
"""

    # Safe access avec vérification de type
    critical = 0
    if integrity_report and isinstance(integrity_report, dict):
        summary = integrity_report.get('summary')
        if summary and isinstance(summary, dict):
            critical = summary.get('critical_count', 0)

    html += f"                <div class='metric-value'>{critical}</div>\n"

    html += """
            </div>
            <div class="metric">
                <div class="metric-label">Warnings</div>
"""

    # Safe access avec vérification de type
    warnings = 0
    if integrity_report and isinstance(integrity_report, dict):
        summary = integrity_report.get('summary')
        if summary and isinstance(summary, dict):
            warnings = summary.get('warning_count', 0)

    html += f"                <div class='metric-value'>{warnings}</div>\n"

    html += """
            </div>
        </div>

        <!-- Rapport Unifié (Nexus) -->
        <div class="section">
            <div class="section-title">
                <span>🎯 Rapport Unifié (Nexus)</span>
"""

    # Safe access avec vérification de type
    html += f"                {format_status_badge(unified_status)}\n"

    html += """
            </div>
            <div class="metric">
                <div class="metric-label">Actions prioritaires</div>
"""

    # Safe access avec vérification de type
    priority_actions = 0
    if unified_report and isinstance(unified_report, dict):
        actions = unified_report.get('priority_actions')
        if actions and isinstance(actions, list):
            priority_actions = len(actions)

    html += f"                <div class='metric-value'>{priority_actions}</div>\n"

    html += """
            </div>
        </div>
"""

    # Collecter tous les problèmes et recommandations
    all_problems = []

    # Production
    if prod_report and isinstance(prod_report, dict):
        recs = prod_report.get('recommendations', [])
        if recs and isinstance(recs, list):
            for rec in recs:
                if isinstance(rec, dict):
                    all_problems.append({
                        'source': '☁️ Production',
                        'priority': rec.get('priority', 'MEDIUM'),
                        'action': rec.get('action', 'N/A'),
                        'file': rec.get('file', ''),
                        'details': rec.get('details', '')
                    })

    # Documentation (Anima)
    if docs_report and isinstance(docs_report, dict):
        recs = docs_report.get('recommendations', [])
        if recs and isinstance(recs, list):
            for rec in recs:
                if isinstance(rec, dict):
                    all_problems.append({
                        'source': '📚 Documentation',
                        'priority': rec.get('priority', 'MEDIUM'),
                        'action': rec.get('action', 'N/A'),
                        'file': rec.get('file', ''),
                        'details': rec.get('details', '')
                    })

    # Intégrité (Neo)
    if integrity_report and isinstance(integrity_report, dict):
        recs = integrity_report.get('recommendations', [])
        if recs and isinstance(recs, list):
            for rec in recs:
                if isinstance(rec, dict):
                    all_problems.append({
                        'source': '🔐 Intégrité',
                        'priority': rec.get('priority', 'MEDIUM'),
                        'action': rec.get('action', 'N/A'),
                        'file': rec.get('file', ''),
                        'details': rec.get('details', '')
                    })

    # Ajouter section détails si problèmes détectés
    if all_problems:
        html += """
        <div class="details-section">
            <div class="details-title">📋 Détails des corrections recommandées</div>
"""
        # Limiter à 10 problèmes max pour ne pas surcharger l'email
        for problem in all_problems[:10]:
            priority = problem['priority']
            source = problem['source']
            action = problem['action']
            file_info = problem.get('file', '')

            html += f"""
            <div class="problem-item">
                <span class="problem-priority priority-{priority}">{priority}</span>
                <strong>{source}</strong>
                <div style="margin-top:8px;">{action}</div>
"""
            if file_info:
                html += f"""
                <div style="margin-top:5px; color:#94a3b8; font-size:13px;">📄 {file_info}</div>
"""
            html += """
            </div>
"""

        if len(all_problems) > 10:
            html += f"""
            <div style="margin-top:15px; color:#94a3b8; font-size:14px;">
                ... et {len(all_problems) - 10} autres problèmes détectés
            </div>
"""

        html += """
        </div>
"""

    # Générer token pour auto-fix
    report_id = f"guardian-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    fix_token = generate_fix_token(report_id)

    # URL du backend (localhost pour dev, à adapter pour prod)
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    auto_fix_url = f"{backend_url}/api/guardian/auto-fix"

    # Ajouter bouton auto-fix si problèmes détectés
    if all_problems:
        html += f"""
        <div style="text-align:center; margin:30px 0;">
            <a href="{auto_fix_url}" class="action-button"
               style="color: white; text-decoration: none;"
               onclick="event.preventDefault(); applyFixes();">
                🔧 Appliquer les corrections automatiquement
            </a>
            <div style="margin-top:10px; color:#94a3b8; font-size:12px;">
                Token valide 24h
            </div>
        </div>

        <script>
        async function applyFixes() {{
            if (!confirm('Voulez-vous appliquer automatiquement les corrections Guardian ?\\n\\nCela peut modifier des fichiers dans le projet.')) {{
                return;
            }}

            try {{
                const response = await fetch('{auto_fix_url}', {{
                    method: 'POST',
                    headers: {{
                        'X-Guardian-Token': '{fix_token}',
                        'Content-Type': 'application/json'
                    }}
                }});

                const result = await response.json();

                if (response.ok) {{
                    alert('✅ Corrections appliquées avec succès!\\n\\n' +
                          'Corrections: ' + result.details.total_fixed + '\\n' +
                          'Ignorées: ' + result.details.total_skipped + '\\n' +
                          'Erreurs: ' + result.details.total_failed);
                }} else {{
                    alert('❌ Erreur: ' + result.detail);
                }}
            }} catch (error) {{
                alert('❌ Erreur réseau: ' + error.message);
            }}
        }}
        </script>
"""

    html += """
        <div class="footer">
            <p><strong>🤖 Guardian Autonomous Monitoring System</strong></p>
            <p>ÉMERGENCE V8 - Rapports automatiques toutes les 2h</p>
            <p style="margin-top:15px;">
                Contact: gonzalefernando@gmail.com
            </p>
        </div>
    </div>
</body>
</html>
"""

    return html

async def send_guardian_email(reports):
    """Envoie le rapport Guardian par email"""
    from features.auth.email_service import EmailService

    email_service = EmailService()

    if not email_service.is_enabled():
        print("ERROR: Service email non activé")
        return False

    # Générer HTML
    html_body = await generate_html_email(reports)

    # Texte brut simple avec safe access
    timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    # Safe extraction des statuts
    global_report = reports.get('global')
    prod_report = reports.get('prod')
    docs_report = reports.get('docs')
    integrity_report = reports.get('integrity')

    global_status = extract_status(global_report, fallback_paths=[('executive_summary', 'status')])
    prod_status = extract_status(prod_report)
    docs_status = extract_status(docs_report)
    integrity_status = extract_status(integrity_report)

    text_body = f"""
GUARDIAN ÉMERGENCE V8
Rapport généré le {timestamp}

Statut Global: {global_status}

Production: {prod_status}
Documentation: {docs_status}
Intégrité: {integrity_status}

Rapport complet disponible dans l'email HTML.

Guardian Autonomous Monitoring System
ÉMERGENCE V8
"""

    subject = f"🛡️ Guardian ÉMERGENCE - {global_status} - {datetime.now().strftime('%d/%m %H:%M')}"

    print("Envoi de l'email Guardian...")
    success = await email_service.send_custom_email(
        to_email="gonzalefernando@gmail.com",
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

    if success:
        print("Email Guardian envoyé avec succès!")
        return True
    else:
        print("Échec envoi email Guardian")
        return False

async def main():
    """Point d'entrée principal"""
    print("=" * 60)
    print("GUARDIAN EMAIL REPORT - GÉNÉRATION ET ENVOI")
    print("=" * 60)
    print()

    # 1. Exécuter tous les guardians
    await run_all_guardians()
    print()

    # 2. Charger les rapports
    print("Chargement des rapports...")
    reports = await load_reports()
    print(f"  {len([r for r in reports.values() if r])} rapports chargés")
    print()

    # 3. Envoyer par email
    success = await send_guardian_email(reports)

    print()
    print("=" * 60)
    if success:
        print("SUCCÈS - Email envoyé à gonzalefernando@gmail.com")
    else:
        print("ÉCHEC - Vérifier la configuration SMTP")
    print("=" * 60)

    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
