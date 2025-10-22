#!/usr/bin/env python3
"""
Generate Codex GPT Summary - Enrichit les rapports Guardian pour exploitation par Codex GPT

Lit tous les rapports JSON Guardian et génère un résumé markdown exploitable
avec contexte actionnable, insights, et recommandations narratives.
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Paths
REPO_ROOT = Path(__file__).parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
FALLBACK_REPORT_DIRS = [
    REPO_ROOT / "claude-plugins" / "reports",
    REPO_ROOT / "claude-plugins" / "integrity-docs-guardian" / "reports",
    REPO_ROOT / "claude-plugins" / "integrity-docs-guardian" / "scripts" / "reports",
]
OUTPUT_FILE = REPORTS_DIR / "codex_summary.md"

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_json_report(filename: str) -> Optional[Dict]:
    """Charge un rapport JSON avec gestion d'erreurs."""
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        for fallback_dir in FALLBACK_REPORT_DIRS:
            fallback_path = fallback_dir / filename
            if fallback_path.exists():
                try:
                    with open(fallback_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as exc:  # pragma: no cover - fallback errors logged
                    print(f"⚠️  Erreur lecture {fallback_path}: {exc}", file=sys.stderr)
                    return None

                try:
                    shutil.copyfile(fallback_path, filepath)
                except Exception as exc:  # pragma: no cover - copie best effort
                    print(
                        f"⚠️  Impossible de synchroniser {filename} depuis {fallback_path}: {exc}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"ℹ️  Rapport {filename} synchronisé depuis {fallback_path}",
                        file=sys.stderr,
                    )
                return data

        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Erreur lecture {filename}: {e}", file=sys.stderr)
        return None


def extract_prod_insights(prod_report: Dict) -> Dict[str, Any]:
    """Extrait insights actionnables du rapport production."""
    if not prod_report:
        return {
            "status": "UNKNOWN",
            "logs_analyzed": 0,
            "errors_count": 0,
            "warnings_count": 0,
            "critical_signals": 0,
            "insights": [],
            "recommendations": [],
            "recent_commits": []
        }

    insights = []
    status = prod_report.get("status", "UNKNOWN")
    summary = prod_report.get("summary", {})

    # Errors avec contexte
    errors_detailed = prod_report.get("errors_detailed", [])
    if errors_detailed:
        insights.append({
            "type": "error",
            "title": f"🔴 {len(errors_detailed)} erreur(s) détectée(s) en production",
            "details": []
        })

        for err in errors_detailed[:5]:  # Top 5
            error_type = err.get("error_type", "Unknown")
            endpoint = err.get("endpoint", "N/A")
            file_path = err.get("file_path", "N/A")
            line = err.get("line_number", "N/A")
            message = err.get("message", "")[:200]

            insights[-1]["details"].append({
                "error_type": error_type,
                "endpoint": endpoint,
                "file": file_path,
                "line": line,
                "message": message
            })

    # Patterns d'erreurs
    error_patterns = prod_report.get("error_patterns", {})
    if error_patterns:
        by_endpoint = error_patterns.get("by_endpoint", {})
        by_file = error_patterns.get("by_file", {})
        by_error_type = error_patterns.get("by_error_type", {})

        if by_endpoint:
            top_endpoint = list(by_endpoint.items())[0]
            insights.append({
                "type": "pattern",
                "title": f"📊 Endpoint le plus affecté: {top_endpoint[0]}",
                "details": [{"count": top_endpoint[1], "endpoint": top_endpoint[0]}]
            })

        if by_file:
            top_file = list(by_file.items())[0]
            insights.append({
                "type": "pattern",
                "title": f"📁 Fichier le plus affecté: {top_file[0]}",
                "details": [{"count": top_file[1], "file": top_file[0]}]
            })

        if by_error_type:
            top_error = list(by_error_type.items())[0]
            insights.append({
                "type": "pattern",
                "title": f"⚠️ Type d'erreur récurrent: {top_error[0]}",
                "details": [{"count": top_error[1], "error_type": top_error[0]}]
            })

    # Code snippets
    code_snippets = prod_report.get("code_snippets", [])
    if code_snippets:
        insights.append({
            "type": "code",
            "title": f"💻 {len(code_snippets)} fichier(s) avec erreurs + snippets de code",
            "details": code_snippets
        })

    # Recommandations
    recommendations = prod_report.get("recommendations", [])
    actionable_recs = [rec for rec in recommendations if rec.get("priority") in ["HIGH", "CRITICAL"]]

    return {
        "status": status,
        "logs_analyzed": prod_report.get("logs_analyzed", 0),
        "errors_count": summary.get("errors", 0),
        "warnings_count": summary.get("warnings", 0),
        "critical_signals": summary.get("critical_signals", 0),
        "insights": insights,
        "recommendations": actionable_recs,
        "recent_commits": prod_report.get("recent_commits", [])
    }


def extract_docs_insights(docs_report: Dict) -> Dict[str, Any]:
    """Extrait insights du rapport documentation (Anima)."""
    if not docs_report:
        return {
            "status": "UNKNOWN",
            "gaps_count": 0,
            "updates_count": 0,
            "backend_files_changed": 0,
            "frontend_files_changed": 0,
            "insights": []
        }

    insights = []
    status = docs_report.get("status", "UNKNOWN")

    # Documentation gaps
    gaps = docs_report.get("documentation_gaps", [])
    if gaps:
        high_severity = [g for g in gaps if g.get("severity") == "high"]
        medium_severity = [g for g in gaps if g.get("severity") == "medium"]

        if high_severity:
            insights.append({
                "type": "gap_high",
                "title": f"🔴 {len(high_severity)} gap(s) documentation HAUTE priorité",
                "details": high_severity[:5]
            })

        if medium_severity:
            insights.append({
                "type": "gap_medium",
                "title": f"🟡 {len(medium_severity)} gap(s) documentation MOYENNE priorité",
                "details": medium_severity[:5]
            })

    # Proposed updates
    updates = docs_report.get("proposed_updates", [])
    if updates:
        insights.append({
            "type": "updates",
            "title": f"📝 {len(updates)} mise(s) à jour de documentation proposée(s)",
            "details": updates
        })

    # Changes detected
    changes = docs_report.get("changes_detected", {})
    backend_files = changes.get("backend", [])
    frontend_files = changes.get("frontend", [])

    return {
        "status": status,
        "gaps_count": len(gaps),
        "updates_count": len(updates),
        "backend_files_changed": len(backend_files),
        "frontend_files_changed": len(frontend_files),
        "insights": insights
    }


def extract_integrity_insights(integrity_report: Dict) -> Dict[str, Any]:
    """Extrait insights du rapport intégrité (Neo)."""
    if not integrity_report:
        return {
            "status": "UNKNOWN",
            "issues_count": 0,
            "critical_count": 0,
            "insights": []
        }

    insights = []
    status = integrity_report.get("status", "UNKNOWN")

    # Issues détectés
    issues = integrity_report.get("issues", [])
    if issues:
        critical = [i for i in issues if i.get("severity") == "critical"]
        warnings = [i for i in issues if i.get("severity") == "warning"]

        if critical:
            insights.append({
                "type": "critical",
                "title": f"🔴 {len(critical)} problème(s) intégrité CRITIQUE",
                "details": critical
            })

        if warnings:
            insights.append({
                "type": "warning",
                "title": f"⚠️ {len(warnings)} warning(s) intégrité",
                "details": warnings[:5]
            })

    # Backend/Frontend changes
    backend_changes = integrity_report.get("backend_changes", {})
    frontend_changes = integrity_report.get("frontend_changes", {})

    endpoints_modified = backend_changes.get("endpoints_modified", [])
    if endpoints_modified:
        insights.append({
            "type": "backend",
            "title": f"🔧 {len(endpoints_modified)} endpoint(s) modifié(s)",
            "details": endpoints_modified
        })

    api_calls_modified = frontend_changes.get("api_calls_modified", [])
    if api_calls_modified:
        insights.append({
            "type": "frontend",
            "title": f"🌐 {len(api_calls_modified)} appel(s) API modifié(s)",
            "details": api_calls_modified
        })

    return {
        "status": status,
        "issues_count": len(issues),
        "critical_count": len([i for i in issues if i.get("severity") == "critical"]),
        "insights": insights
    }


def extract_unified_insights(unified_report: Dict) -> Dict[str, Any]:
    """Extrait insights du rapport unifié (Nexus)."""
    if not unified_report:
        return {
            "status": "UNKNOWN",
            "total_issues": 0,
            "critical": 0,
            "warnings": 0,
            "insights": [],
            "statistics": {}
        }

    exec_summary = unified_report.get("executive_summary", {})
    status = exec_summary.get("status", "UNKNOWN")

    insights = []

    # Priority actions
    priority_actions = unified_report.get("priority_actions", [])
    if priority_actions:
        insights.append({
            "type": "actions",
            "title": f"⚡ {len(priority_actions)} action(s) prioritaire(s)",
            "details": priority_actions
        })

    # Statistics
    stats = unified_report.get("statistics", {})

    return {
        "status": status,
        "total_issues": exec_summary.get("total_issues", 0),
        "critical": exec_summary.get("critical", 0),
        "warnings": exec_summary.get("warnings", 0),
        "insights": insights,
        "statistics": stats
    }


def generate_markdown_summary(
    prod_insights: Dict,
    docs_insights: Dict,
    integrity_insights: Dict,
    unified_insights: Dict
) -> str:
    """Génère le résumé markdown exploitable pour Codex GPT."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = f"""# 🛡️ Guardian - Résumé pour Codex GPT

**Généré le:** {timestamp}
**Source:** Rapports automatiques Guardian (ProdGuardian, Anima, Neo, Nexus)

---

## 📊 Vue d'ensemble

| Guardian | Status | Métriques clés |
|----------|--------|----------------|
| **Production** | `{prod_insights['status']}` | {prod_insights['errors_count']} erreurs, {prod_insights['warnings_count']} warnings, {prod_insights['logs_analyzed']} logs analysés |
| **Documentation** | `{docs_insights['status']}` | {docs_insights['gaps_count']} gaps, {docs_insights['updates_count']} mises à jour proposées |
| **Intégrité** | `{integrity_insights['status']}` | {integrity_insights['issues_count']} issues ({integrity_insights['critical_count']} critiques) |
| **Rapport Unifié** | `{unified_insights['status']}` | {unified_insights['total_issues']} issues totales |

---

## 🔴 Production (ProdGuardian)

"""

    # Insights production
    if prod_insights['insights']:
        for insight in prod_insights['insights']:
            md += f"### {insight['title']}\n\n"

            if insight['type'] == 'error':
                for detail in insight['details']:
                    md += f"**{detail['error_type']}**\n"
                    md += f"- Endpoint: `{detail['endpoint']}`\n"
                    md += f"- Fichier: `{detail['file']}:{detail['line']}`\n"
                    md += f"- Message: {detail['message']}\n\n"

            elif insight['type'] == 'pattern':
                for detail in insight['details']:
                    if 'endpoint' in detail:
                        md += f"- Endpoint: `{detail['endpoint']}` ({detail['count']} erreurs)\n"
                    elif 'file' in detail:
                        md += f"- Fichier: `{detail['file']}` ({detail['count']} erreurs)\n"
                    elif 'error_type' in detail:
                        md += f"- Type: `{detail['error_type']}` ({detail['count']} occurrences)\n"
                md += "\n"

            elif insight['type'] == 'code':
                for snippet in insight['details']:
                    md += f"**Fichier:** `{snippet['file']}`  \n"
                    md += f"**Ligne:** {snippet['line']}  \n"
                    md += f"**Erreurs:** {snippet.get('error_count', 1)}  \n"
                    md += f"```python\n{snippet['code_snippet']}\n```\n\n"

    # Recommandations production
    if prod_insights['recommendations']:
        md += "### 💡 Recommandations actionnables\n\n"
        for rec in prod_insights['recommendations']:
            priority = rec.get('priority', 'MEDIUM')
            action = rec.get('action', 'N/A')
            details = rec.get('details', '')

            md += f"**[{priority}]** {action}\n"
            if details:
                md += f"- {details}\n"

            # Commandes gcloud si disponibles
            if 'command' in rec:
                md += f"- Commande: `{rec['command']}`\n"

            # Fichiers affectés
            if 'affected_files' in rec:
                files = rec['affected_files'][:3]
                if files:
                    md += f"- Fichiers: {', '.join(f'`{f}`' for f in files)}\n"

            md += "\n"

    # Commits récents
    if prod_insights['recent_commits']:
        md += "### 📝 Commits récents (contexte)\n\n"
        for commit in prod_insights['recent_commits'][:5]:
            md += f"- `{commit['hash']}` - {commit['message']} ({commit['author']}, {commit['time']})\n"
        md += "\n"

    md += "---\n\n"

    # Documentation (Anima)
    md += "## 📚 Documentation (Anima)\n\n"

    if docs_insights['insights']:
        for insight in docs_insights['insights']:
            md += f"### {insight['title']}\n\n"

            if insight['type'] in ['gap_high', 'gap_medium']:
                for gap in insight['details']:
                    md += f"**Fichier:** `{gap['file']}`  \n"
                    md += f"**Issue:** {gap['issue']}  \n"
                    md += f"**Docs affectées:** {', '.join(f'`{d}`' for d in gap.get('affected_docs', []))}  \n"
                    md += f"**Recommandation:** {gap['recommendation']}\n\n"

            elif insight['type'] == 'updates':
                for update in insight['details']:
                    md += f"**Fichier:** `{update['file']}`  \n"
                    md += f"**Action:** {update['action']}  \n"
                    md += f"**Raison:** {update['reason']}  \n"
                    if 'related_changes' in update:
                        md += f"**Changements liés:** {', '.join(f'`{c}`' for c in update['related_changes'][:3])}\n"
                    md += "\n"
    else:
        md += "*Aucun gap de documentation détecté.*\n\n"

    md += "---\n\n"

    # Intégrité (Neo)
    md += "## 🔐 Intégrité Système (Neo)\n\n"

    if integrity_insights['insights']:
        for insight in integrity_insights['insights']:
            md += f"### {insight['title']}\n\n"

            if insight['type'] in ['critical', 'warning']:
                for issue in insight['details']:
                    md += f"**Sévérité:** {issue.get('severity', 'N/A')}  \n"
                    md += f"**Message:** {issue.get('message', 'N/A')}  \n"
                    if 'file' in issue:
                        md += f"**Fichier:** `{issue['file']}`  \n"
                    md += "\n"

            elif insight['type'] == 'backend':
                for endpoint in insight['details']:
                    md += f"- `{endpoint}`\n"
                md += "\n"

            elif insight['type'] == 'frontend':
                for api_call in insight['details']:
                    md += f"- `{api_call}`\n"
                md += "\n"
    else:
        md += "*Aucun problème d'intégrité détecté.*\n\n"

    md += "---\n\n"

    # Rapport unifié (Nexus)
    md += "## 🎯 Rapport Unifié (Nexus)\n\n"

    if unified_insights['insights']:
        for insight in unified_insights['insights']:
            md += f"### {insight['title']}\n\n"

            if insight['type'] == 'actions':
                for action in insight['details']:
                    md += f"- {action}\n"
                md += "\n"
    else:
        md += "*Aucune action prioritaire.*\n\n"

    # Statistics globales
    if unified_insights.get('statistics'):
        stats = unified_insights['statistics']
        md += "### 📈 Statistiques globales\n\n"
        md += f"- Fichiers backend modifiés: {stats.get('backend_files', 0)}\n"
        md += f"- Fichiers frontend modifiés: {stats.get('frontend_files', 0)}\n"
        md += f"- Fichiers docs modifiés: {stats.get('docs_files', 0)}\n"
        md += f"- Issues par sévérité:\n"
        issues_by_severity = stats.get('issues_by_severity', {})
        for severity, count in issues_by_severity.items():
            md += f"  - {severity}: {count}\n"
        md += "\n"

    md += "---\n\n"

    # Section "Que faire maintenant ?"
    md += "## ⚡ Que faire maintenant ?\n\n"

    # Prioriser les actions
    actions = []

    if prod_insights['errors_count'] > 0:
        actions.append("1. **🔴 PRIORITÉ HAUTE** - Corriger les erreurs production (voir section Production ci-dessus)")

    if integrity_insights['critical_count'] > 0:
        actions.append("2. **🔴 PRIORITÉ HAUTE** - Résoudre les problèmes d'intégrité critiques")

    if docs_insights['gaps_count'] > 0:
        actions.append("3. **🟡 PRIORITÉ MOYENNE** - Mettre à jour la documentation (gaps détectés)")

    if prod_insights['warnings_count'] > 0:
        actions.append("4. **🟡 PRIORITÉ MOYENNE** - Investiguer les warnings production")

    if not actions:
        actions.append("✅ **Tout va bien !** Aucune action urgente requise.")

    for action in actions:
        md += f"{action}\n"

    md += "\n---\n\n"
    md += "*Ce rapport est généré automatiquement par Guardian. Pour plus de détails, consulte les rapports JSON individuels dans `reports/`.*\n"

    return md


def main():
    """Point d'entrée principal."""
    print("=" * 60)
    print("GENERATE CODEX SUMMARY - Enrichissement rapports Guardian")
    print("=" * 60)
    print()

    # Charger tous les rapports
    print("📂 Chargement des rapports...")
    prod_report = load_json_report("prod_report.json")
    docs_report = load_json_report("docs_report.json")
    integrity_report = load_json_report("integrity_report.json")
    unified_report = load_json_report("unified_report.json")

    # Extraire insights
    print("🔍 Extraction des insights...")
    prod_insights = extract_prod_insights(prod_report)
    docs_insights = extract_docs_insights(docs_report)
    integrity_insights = extract_integrity_insights(integrity_report)
    unified_insights = extract_unified_insights(unified_report)

    # Générer markdown
    print("📝 Génération du résumé markdown...")
    markdown = generate_markdown_summary(
        prod_insights,
        docs_insights,
        integrity_insights,
        unified_insights
    )

    # Sauvegarder
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(markdown)

    print(f"✅ Résumé généré: {OUTPUT_FILE}")
    print()
    print("=" * 60)
    print("SUCCÈS - Codex GPT peut maintenant lire reports/codex_summary.md")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
