#!/usr/bin/env python3
"""
Guardian Dashboard Generator - Génère un rapport HTML des Guardians

Lit les rapports JSON des guardians et génère un dashboard HTML visuel
accessible via docs/guardian-status.html

Usage:
    python scripts/generate_guardian_dashboard.py
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def load_json_report(path: Path) -> Dict[str, Any] | None:
    """Charge un rapport JSON, retourne None si erreur."""
    try:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Erreur lecture {path}: {e}")
        return None


def format_timestamp(ts_str: str) -> str:
    """Formate un timestamp ISO en format lisible."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts_str


def get_status_badge(status: str) -> str:
    """Retourne un badge HTML coloré selon le status."""
    status_lower = status.lower()
    if status_lower == "ok":
        return '<span class="badge badge-success">✅ OK</span>'
    elif status_lower == "warning":
        return '<span class="badge badge-warning">⚠️ WARNING</span>'
    elif status_lower == "error" or status_lower == "critical":
        return '<span class="badge badge-error">❌ ERROR</span>'
    else:
        return f'<span class="badge badge-info">{status}</span>'


def get_severity_badge(severity: str) -> str:
    """Badge pour sévérité (critical, warning, info)."""
    if severity == "critical":
        return '<span class="badge badge-error">🔴 CRITICAL</span>'
    elif severity == "warning":
        return '<span class="badge badge-warning">🟠 WARNING</span>'
    elif severity == "info":
        return '<span class="badge badge-info">🔵 INFO</span>'
    else:
        return f'<span class="badge">{severity}</span>'


def render_unified_report(report: Dict[str, Any] | None) -> str:
    """Render le rapport unifié (Nexus)."""
    if not report:
        return '<div class="card error"><p>❌ Rapport unifié introuvable</p></div>'

    metadata = report.get("metadata", {})
    summary = report.get("executive_summary", {})
    agent_status = report.get("agent_status", {})
    recommendations = report.get("recommendations", {})

    # Status global
    global_status = summary.get("status", "unknown")
    status_badge = get_status_badge(global_status)

    # Issues breakdown
    total_issues = summary.get("total_issues", 0)
    critical = summary.get("critical", 0)
    warnings = summary.get("warnings", 0)
    info = summary.get("info", 0)

    html = f"""
    <div class="card">
        <h2>📊 Rapport Unifié (Nexus)</h2>
        <div class="meta">
            <p><strong>Timestamp:</strong> {format_timestamp(metadata.get("timestamp", "N/A"))}</p>
            <p><strong>Commit:</strong> <code>{metadata.get("commit_hash", "N/A")[:8]}</code></p>
            <p><strong>Status:</strong> {status_badge}</p>
        </div>

        <h3>Résumé Exécutif</h3>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">Total Issues</div>
                <div class="summary-value {"error" if total_issues > 0 else "success"}">{total_issues}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Critical</div>
                <div class="summary-value {"error" if critical > 0 else "success"}">{critical}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Warnings</div>
                <div class="summary-value {"warning" if warnings > 0 else "success"}">{warnings}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Info</div>
                <div class="summary-value info">{info}</div>
            </div>
        </div>

        <h3>Status Agents</h3>
        <table class="status-table">
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Issues</th>
                    <th>Résumé</th>
                </tr>
            </thead>
            <tbody>
    """

    for agent_name, agent_data in agent_status.items():
        agent_status_val = agent_data.get("status", "unknown")
        issues_count = agent_data.get("issues_found", 0)
        summary_text = agent_data.get("summary", "N/A")

        html += f"""
                <tr>
                    <td><strong>{agent_name.upper()}</strong></td>
                    <td>{get_status_badge(agent_status_val)}</td>
                    <td>{issues_count}</td>
                    <td>{summary_text}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    """

    # Recommendations
    if recommendations:
        html += "<h3>Recommandations</h3>"
        for priority, actions in recommendations.items():
            if actions:
                html += f"<h4>{priority.capitalize()}</h4><ul>"
                for action in actions:
                    html += f"<li>{action}</li>"
                html += "</ul>"

    html += "</div>"
    return html


def render_prod_report(report: Dict[str, Any] | None) -> str:
    """Render le rapport production."""
    if not report:
        return '<div class="card error"><p>❌ Rapport production introuvable</p></div>'

    status = report.get("status", "UNKNOWN")
    summary = report.get("summary", {})
    timestamp = format_timestamp(report.get("timestamp", "N/A"))
    logs_analyzed = report.get("logs_analyzed", 0)

    errors = summary.get("errors", 0)
    warnings = summary.get("warnings", 0)
    critical_signals = summary.get("critical_signals", 0)
    latency_issues = summary.get("latency_issues", 0)

    status_badge = get_status_badge(status)

    html = f"""
    <div class="card">
        <h2>☁️ Production Cloud Run</h2>
        <div class="meta">
            <p><strong>Timestamp:</strong> {timestamp}</p>
            <p><strong>Service:</strong> {report.get("service", "N/A")}</p>
            <p><strong>Région:</strong> {report.get("region", "N/A")}</p>
            <p><strong>Logs analysés:</strong> {logs_analyzed}</p>
            <p><strong>Status:</strong> {status_badge}</p>
        </div>

        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">Errors</div>
                <div class="summary-value {"error" if errors > 0 else "success"}">{errors}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Warnings</div>
                <div class="summary-value {"warning" if warnings > 0 else "success"}">{warnings}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Critical Signals</div>
                <div class="summary-value {"error" if critical_signals > 0 else "success"}">{critical_signals}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Latency Issues</div>
                <div class="summary-value {"warning" if latency_issues > 0 else "success"}">{latency_issues}</div>
            </div>
        </div>
    """

    # Afficher les erreurs si présentes
    if report.get("errors"):
        html += '<h3>❌ Erreurs</h3><ul class="issues-list">'
        for error in report["errors"]:
            html += f'<li class="error">{error}</li>'
        html += "</ul>"

    # Afficher les warnings si présents
    if report.get("warnings"):
        html += '<h3>⚠️ Warnings</h3><ul class="issues-list">'
        for warning in report["warnings"]:
            html += f'<li class="warning">{warning}</li>'
        html += "</ul>"

    # Recommandations
    if report.get("recommendations"):
        html += "<h3>Recommandations</h3><ul>"
        for rec in report["recommendations"]:
            priority = rec.get("priority", "UNKNOWN")
            action = rec.get("action", "N/A")
            details = rec.get("details", "")

            html += f"<li><strong>[{priority}]</strong> {action}"
            if details:
                html += f" - <em>{details}</em>"
            html += "</li>"
        html += "</ul>"

    html += "</div>"
    return html


def render_integrity_report(report: Dict[str, Any] | None) -> str:
    """Render le rapport d'intégrité (Neo)."""
    if not report:
        return '<div class="card error"><p>❌ Rapport intégrité introuvable</p></div>'

    status = report.get("status", "unknown")
    timestamp = format_timestamp(report.get("timestamp", "N/A"))
    stats = report.get("statistics", {})
    backend_changes = report.get("backend_changes", {})
    frontend_changes = report.get("frontend_changes", {})
    issues = report.get("issues", [])

    status_badge = get_status_badge(status)

    html = f"""
    <div class="card">
        <h2>🛡️ Intégrité Backend/Frontend (Neo)</h2>
        <div class="meta">
            <p><strong>Timestamp:</strong> {timestamp}</p>
            <p><strong>Status:</strong> {status_badge}</p>
        </div>

        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">Backend Files</div>
                <div class="summary-value">{stats.get("backend_files_changed", 0)}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Frontend Files</div>
                <div class="summary-value">{stats.get("frontend_files_changed", 0)}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Issues</div>
                <div class="summary-value {"error" if stats.get("issues_found", 0) > 0 else "success"}">{stats.get("issues_found", 0)}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">Critical</div>
                <div class="summary-value {"error" if stats.get("critical", 0) > 0 else "success"}">{stats.get("critical", 0)}</div>
            </div>
        </div>
    """

    # Backend changes
    if backend_changes.get("files"):
        html += "<h3>Backend Changes</h3><ul>"
        for file in backend_changes["files"]:
            html += f"<li><code>{file}</code></li>"
        html += "</ul>"

    # Frontend changes
    if frontend_changes.get("files"):
        html += "<h3>Frontend Changes</h3><ul>"
        for file in frontend_changes["files"]:
            html += f"<li><code>{file}</code></li>"
        html += "</ul>"

    # Issues
    if issues:
        html += '<h3>Issues Détectées</h3><ul class="issues-list">'
        for issue in issues:
            severity = issue.get("severity", "info")
            message = issue.get("message", "N/A")
            file_path = issue.get("file", "")

            badge = get_severity_badge(severity)
            html += f'<li class="{severity}">{badge} {message}'
            if file_path:
                html += f" <code>{file_path}</code>"
            html += "</li>"
        html += "</ul>"

    html += "</div>"
    return html


def generate_dashboard() -> str:
    """Génère le dashboard HTML complet."""
    project_root = Path(__file__).parent.parent

    # Chemins des rapports
    unified_report_path = (
        project_root
        / "claude-plugins"
        / "integrity-docs-guardian"
        / "reports"
        / "unified_report.json"
    )
    prod_report_path = project_root / "reports" / "prod_report.json"
    integrity_report_path = (
        project_root
        / "claude-plugins"
        / "integrity-docs-guardian"
        / "reports"
        / "integrity_report.json"
    )

    # Charger les rapports
    unified_report = load_json_report(unified_report_path)
    prod_report = load_json_report(prod_report_path)
    integrity_report = load_json_report(integrity_report_path)

    # Générer le HTML
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guardian Dashboard - Emergence V8</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        }}

        h1 {{
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}

        .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .generated-at {{
            margin-top: 10px;
            font-size: 0.9em;
            opacity: 0.7;
        }}

        .card {{
            background: rgba(255, 255, 255, 0.95);
            color: #333;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }}

        .card.error {{
            background: rgba(239, 68, 68, 0.95);
            color: #fff;
        }}

        h2 {{
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}

        h3 {{
            font-size: 1.3em;
            margin-top: 25px;
            margin-bottom: 15px;
            color: #764ba2;
        }}

        h4 {{
            font-size: 1.1em;
            margin-top: 15px;
            margin-bottom: 10px;
            color: #555;
        }}

        .meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(102, 126, 234, 0.1);
            border-radius: 8px;
        }}

        .meta p {{
            margin: 5px 0;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .summary-item {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }}

        .summary-label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .summary-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}

        .summary-value.success {{
            color: #10b981;
        }}

        .summary-value.warning {{
            color: #f59e0b;
        }}

        .summary-value.error {{
            color: #ef4444;
        }}

        .summary-value.info {{
            color: #3b82f6;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge-success {{
            background: #10b981;
            color: #fff;
        }}

        .badge-warning {{
            background: #f59e0b;
            color: #fff;
        }}

        .badge-error {{
            background: #ef4444;
            color: #fff;
        }}

        .badge-info {{
            background: #3b82f6;
            color: #fff;
        }}

        .status-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: #fff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}

        .status-table thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }}

        .status-table th,
        .status-table td {{
            padding: 15px;
            text-align: left;
        }}

        .status-table tbody tr:nth-child(even) {{
            background: #f9fafb;
        }}

        .status-table tbody tr:hover {{
            background: #f3f4f6;
        }}

        code {{
            background: rgba(102, 126, 234, 0.1);
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #667eea;
        }}

        ul {{
            margin: 15px 0;
            padding-left: 30px;
        }}

        ul li {{
            margin: 8px 0;
            line-height: 1.6;
        }}

        .issues-list {{
            list-style: none;
            padding: 0;
        }}

        .issues-list li {{
            padding: 10px 15px;
            margin: 8px 0;
            border-left: 4px solid #3b82f6;
            background: #f9fafb;
            border-radius: 4px;
        }}

        .issues-list li.error {{
            border-left-color: #ef4444;
            background: #fef2f2;
        }}

        .issues-list li.warning {{
            border-left-color: #f59e0b;
            background: #fffbeb;
        }}

        .issues-list li.critical {{
            border-left-color: #dc2626;
            background: #fee2e2;
            font-weight: bold;
        }}

        footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid rgba(255, 255, 255, 0.2);
            opacity: 0.8;
        }}

        @media (max-width: 768px) {{
            h1 {{
                font-size: 2em;
            }}

            .summary-grid {{
                grid-template-columns: 1fr;
            }}

            .meta {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Guardian Dashboard</h1>
            <p class="subtitle">Système de Surveillance Automatisé - Emergence V8</p>
            <p class="generated-at">Généré le {now}</p>
        </header>

        <main>
            {render_unified_report(unified_report)}
            {render_prod_report(prod_report)}
            {render_integrity_report(integrity_report)}
        </main>

        <footer>
            <p>🛡️ Guardians: Anima (Docs) | Neo (Integrity) | Nexus (Coordinator) | ProdGuardian (Cloud Run)</p>
            <p>Rapports auto-générés par hooks Git (pre-commit, post-commit, pre-push)</p>
        </footer>
    </div>
</body>
</html>
"""

    return html


def main():
    """Point d'entrée principal."""
    import sys
    import io

    # Fix Windows encoding bullshit
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("🤖 Guardian Dashboard Generator")
    print("=" * 60)

    # Générer le dashboard
    print("📊 Génération du dashboard HTML...")
    html = generate_dashboard()

    # Écrire le fichier
    project_root = Path(__file__).parent.parent
    output_path = project_root / "docs" / "guardian-status.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Dashboard généré : {output_path}")
    print(f"📂 Taille : {len(html)} caractères")
    print()
    print("🌐 Ouvrir le fichier dans un navigateur pour visualiser")
    print(f"   file://{output_path.absolute()}")


if __name__ == "__main__":
    main()
