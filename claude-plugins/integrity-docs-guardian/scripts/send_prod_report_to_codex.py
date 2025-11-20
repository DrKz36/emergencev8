#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Send ENRICHED Production Guardian Report to Codex GPT via Email
Includes full context, stack traces, code snippets, patterns for autonomous debugging
"""

import os
import sys
import json
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Fix encoding pour Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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
    repo_root = Path(__file__).parent.parent.parent.parent
    env_path = repo_root / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

# Ajouter le chemin du backend pour importer EmailService
backend_path = Path(__file__).parent.parent.parent.parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService

# Configuration
CODEX_GPT_EMAIL = os.getenv(
    "CODEX_GPT_EMAIL", "gonzalefernando@gmail.com"
)  # Email où Codex GPT récupère ses tâches
REPORTS_DIR = Path(__file__).parent.parent / "reports"
SCRIPTS_DIR = Path(__file__).parent


def load_prod_report() -> Optional[Dict]:
    """Charge le dernier rapport de production"""
    prod_report_path = REPORTS_DIR / "prod_report.json"
    try:
        if prod_report_path.exists():
            with open(prod_report_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"❌ Erreur lors du chargement du rapport prod: {e}")
        return None


def generate_html_from_report(report: Dict) -> str:
    """
    Génère le HTML enrichi depuis le rapport JSON
    Utilise le script generate_html_report.py
    """
    try:
        # Sauvegarder temporairement le rapport
        temp_report_path = REPORTS_DIR / "temp_prod_report_for_email.json"
        with open(temp_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Exécuter generate_html_report.py
        generate_script = SCRIPTS_DIR / "generate_html_report.py"
        result = subprocess.check_output(
            [sys.executable, str(generate_script), str(temp_report_path)],
            text=True,
            encoding="utf-8",
        )

        # Nettoyer le fichier temporaire
        temp_report_path.unlink()

        return result

    except Exception as e:
        print(f"❌ Erreur lors de la génération HTML: {e}")
        import traceback

        traceback.print_exc()
        return None


def generate_plain_text_summary(report: Dict) -> str:
    """
    Génère un résumé texte du rapport (fallback si HTML échoue)
    """
    status = report.get("status", "UNKNOWN")
    timestamp = report.get("timestamp", "N/A")
    errors_count = report.get("summary", {}).get("errors", 0)
    warnings_count = report.get("summary", {}).get("warnings", 0)
    critical_count = report.get("summary", {}).get("critical_signals", 0)

    text = f"""
🛡️ PRODUCTION GUARDIAN REPORT - EMERGENCE V8
{"=" * 70}

Status: {status}
Timestamp: {timestamp}
Service: {report.get("service", "N/A")} ({report.get("region", "N/A")})
Logs Analyzed: {report.get("logs_analyzed", 0)} (last {report.get("freshness", "N/A")})

SUMMARY:
  - Errors: {errors_count}
  - Warnings: {warnings_count}
  - Critical Signals: {critical_count}
  - Latency Issues: {report.get("summary", {}).get("latency_issues", 0)}

"""

    # Error Patterns
    if report.get("error_patterns"):
        patterns = report["error_patterns"]

        if patterns.get("by_endpoint"):
            text += "\nERROR PATTERNS - BY ENDPOINT:\n"
            for endpoint, count in list(patterns["by_endpoint"].items())[:5]:
                text += f"  - {endpoint}: {count} errors\n"

        if patterns.get("by_error_type"):
            text += "\nERROR PATTERNS - BY ERROR TYPE:\n"
            for error_type, count in list(patterns["by_error_type"].items())[:5]:
                text += f"  - {error_type}: {count} occurrences\n"

        if patterns.get("by_file"):
            text += "\nERROR PATTERNS - BY FILE:\n"
            for file_path, count in list(patterns["by_file"].items())[:5]:
                text += f"  - {file_path}: {count} errors\n"

    # Detailed Errors (top 3)
    if report.get("errors_detailed"):
        text += "\nDETAILED ERRORS (Top 3):\n"
        text += "=" * 70 + "\n"
        for i, error in enumerate(report["errors_detailed"][:3], 1):
            text += f"\n[ERROR {i}]\n"
            text += f"Time: {error.get('timestamp', 'N/A')}\n"
            text += f"Severity: {error.get('severity', 'N/A')}\n"
            if error.get("endpoint"):
                text += (
                    f"Endpoint: {error.get('http_method', '')} {error['endpoint']}\n"
                )
            if error.get("error_type"):
                text += f"Type: {error['error_type']}\n"
            if error.get("file_path"):
                text += f"File: {error['file_path']}:{error.get('line_number', '')}\n"
            text += f"\nMessage:\n{error.get('message', '')[:500]}\n"
            if error.get("stack_trace"):
                text += f"\nStack Trace:\n{error['stack_trace'][:500]}\n"
            text += "\n" + "-" * 70 + "\n"

    # Code Snippets
    if report.get("code_snippets"):
        text += "\nSUSPECT CODE SNIPPETS:\n"
        text += "=" * 70 + "\n"
        for snippet in report["code_snippets"][:2]:
            text += f"\nFile: {snippet['file']} (Line {snippet['line']}, {snippet.get('error_count', 0)} errors)\n"
            text += f"Lines {snippet['start_line']}-{snippet['end_line']}:\n\n"
            text += snippet["code_snippet"]
            text += "\n" + "-" * 70 + "\n"

    # Recent Commits
    if report.get("recent_commits"):
        text += "\nRECENT COMMITS (Potential Culprits):\n"
        for commit in report["recent_commits"][:3]:
            text += f"  - {commit['hash']} by {commit['author']} ({commit['time']})\n"
            text += f"    {commit['message']}\n"

    # Recommendations
    if report.get("recommendations"):
        text += "\nRECOMMENDATIONS:\n"
        text += "=" * 70 + "\n"
        for rec in report["recommendations"]:
            priority = rec.get("priority", "MEDIUM")
            text += f"\n[{priority}] {rec.get('action', '')}\n"
            text += f"{rec.get('details', '')}\n"
            if rec.get("command"):
                text += f"Command: {rec['command']}\n"
            if rec.get("rollback_command"):
                text += f"Rollback: {rec['rollback_command']}\n"
            if rec.get("suggested_fix"):
                text += f"Suggested Fix: {rec['suggested_fix']}\n"
            if rec.get("affected_endpoints"):
                text += f"Affected Endpoints: {', '.join(rec['affected_endpoints'])}\n"
            if rec.get("affected_files"):
                text += f"Affected Files: {', '.join(rec['affected_files'])}\n"
            text += "\n"

    text += """
{'='*70}

🤖 Guardian System 3.0.0 - Production Monitoring
This report is optimized for Codex GPT autonomous debugging.
All context (stack traces, code snippets, patterns) is included.

ÉMERGENCE V8 Production - Generated {timestamp}
"""

    return text


async def send_prod_report_to_codex():
    """
    Charge le rapport de production enrichi et l'envoie à Codex GPT
    """
    print("🤖 Préparation de l'envoi du rapport production à Codex GPT...")

    # Charger le rapport
    report = load_prod_report()
    if not report:
        print("❌ Aucun rapport de production disponible")
        return False

    status = report.get("status", "UNKNOWN")
    print(f"\n📊 Status production: {status}")

    # Générer le HTML enrichi
    print("🎨 Génération du rapport HTML enrichi...")
    html_body = generate_html_from_report(report)

    if not html_body:
        print("⚠️  Échec génération HTML, utilisation du texte brut uniquement")
        html_body = None

    # Générer le texte brut
    text_body = generate_plain_text_summary(report)

    # Initialiser le service email
    email_service = EmailService()

    if not email_service.is_enabled():
        print("❌ Service email non activé ou mal configuré")
        print("   Vérifiez les variables d'environnement:")
        print("   - EMAIL_ENABLED=1")
        print("   - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD")
        return False

    # Déterminer le sujet selon le status
    status_emoji = {"OK": "✅", "DEGRADED": "⚠️", "CRITICAL": "🚨"}.get(status, "📊")

    subject = f"{status_emoji} [CODEX GPT] Production {status} - EMERGENCE V8 ({datetime.now().strftime('%d/%m %H:%M')})"

    print(f"\n📤 Envoi du rapport à Codex GPT: {CODEX_GPT_EMAIL}")
    print(f"   Sujet: {subject}")

    # Envoyer l'email
    success = await email_service.send_custom_email(
        to_email=CODEX_GPT_EMAIL,
        subject=subject,
        html_body=html_body if html_body else text_body,  # HTML si dispo, sinon texte
        text_body=text_body,
    )

    if success:
        print(f"✅ Rapport envoyé avec succès à Codex GPT ({CODEX_GPT_EMAIL})")
        print("\n📋 Rapport contient:")
        print(
            f"   - {report.get('summary', {}).get('errors', 0)} erreurs détaillées avec stack traces"
        )
        print(f"   - {len(report.get('code_snippets', []))} code snippets suspects")
        print(f"   - {len(report.get('recent_commits', []))} commits récents")
        print("   - Patterns d'erreurs par endpoint/fichier/type")
        print("   - Recommandations actionnables avec commandes")
        print("\n🤖 Codex GPT peut maintenant débugger de manière autonome !")
        return True
    else:
        print("❌ Échec de l'envoi du rapport")
        return False


async def main():
    """Point d'entrée principal"""
    try:
        success = await send_prod_report_to_codex()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Vérifier si on doit forcer l'envoi même si status OK
    force = "--force" in sys.argv

    if not force:
        # Charger le rapport pour vérifier le status
        report = load_prod_report()
        if report and report.get("status") == "OK":
            print(
                "ℹ️  Status production: OK - Pas d'envoi d'email (utilisez --force pour envoyer quand même)"
            )
            sys.exit(0)

    asyncio.run(main())
