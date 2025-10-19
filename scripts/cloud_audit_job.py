#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÉMERGENCE V8 - Cloud Audit Job (Cloud Run)
Script d'audit automatisé qui tourne sur Cloud Run via Cloud Scheduler
Envoie un email à l'admin 3x/jour avec l'état de la prod
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# Configuration
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "gonzalefernando@gmail.com")
TARGET_REVISION = "emergence-app-00501-zon"
SERVICE_URL = os.getenv("SERVICE_URL", "https://emergence-app-574876800592.europe-west1.run.app")


class CloudAuditJob:
    """Job d'audit cloud pour Cloud Run"""

    def __init__(self):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.results = {}

    async def check_production_health(self) -> Dict:
        """Vérifie la santé de la production via les endpoints health"""
        import aiohttp

        health_endpoints = [
            f"{SERVICE_URL}/api/health",
            f"{SERVICE_URL}/health/liveness",
            f"{SERVICE_URL}/health/readiness"
        ]

        results = {}
        all_ok = True

        async with aiohttp.ClientSession() as session:
            for endpoint in health_endpoints:
                try:
                    async with session.get(endpoint, timeout=10) as response:
                        status_code = response.status
                        data = await response.json()

                        is_ok = status_code == 200 and data.get('status') in ['ok', 'healthy']
                        results[endpoint] = {
                            'status': 'OK' if is_ok else 'FAILED',
                            'status_code': status_code,
                            'response': data
                        }

                        if not is_ok:
                            all_ok = False

                        print(f"{'✅' if is_ok else '❌'} {endpoint}: {status_code} - {data.get('status', 'N/A')}")

                except Exception as e:
                    results[endpoint] = {
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    all_ok = False
                    print(f"❌ {endpoint}: ERROR - {e}")

        return {
            'status': 'OK' if all_ok else 'CRITICAL',
            'endpoints_checked': len(health_endpoints),
            'endpoints_ok': sum(1 for r in results.values() if r.get('status') == 'OK'),
            'details': results,
            'timestamp': self.timestamp
        }

    async def check_cloud_run_metrics(self) -> Dict:
        """Vérifie les métriques Cloud Run via API Google Cloud"""
        try:
            from google.cloud import run_v2
            from google.cloud import logging_v2

            # Client Cloud Run
            client = run_v2.ServicesClient()
            service_path = f"projects/emergence-app-prod/locations/europe-west1/services/emergence-app"

            try:
                service = client.get_service(name=service_path)

                # Extraire les métriques
                metrics = {
                    'service_name': service.name.split('/')[-1],
                    'generation': service.generation,
                    'observed_generation': service.observed_generation,
                    'conditions': []
                }

                # Vérifier les conditions du service
                for condition in service.conditions:
                    metrics['conditions'].append({
                        'type': condition.type_,
                        'status': condition.status,
                        'reason': condition.reason,
                        'message': condition.message
                    })

                # Vérifier si le service est ready
                ready_condition = next((c for c in service.conditions if c.type_ == 'Ready'), None)
                is_ready = ready_condition and ready_condition.status == 'True'

                print(f"{'✅' if is_ready else '❌'} Service Cloud Run: {'Ready' if is_ready else 'Not Ready'}")

                return {
                    'status': 'OK' if is_ready else 'WARNING',
                    'metrics': metrics,
                    'timestamp': self.timestamp
                }

            except Exception as e:
                print(f"⚠️  Cloud Run API error: {e}")
                return {
                    'status': 'UNKNOWN',
                    'error': str(e),
                    'timestamp': self.timestamp
                }

        except ImportError:
            print("⚠️  google-cloud-run library not installed")
            return {
                'status': 'SKIPPED',
                'reason': 'Library not installed',
                'timestamp': self.timestamp
            }

    async def check_logs_recent_errors(self) -> Dict:
        """Vérifie les logs récents pour détecter les erreurs"""
        try:
            from google.cloud import logging_v2

            # Client Cloud Logging
            client = logging_v2.Client()

            # Requête pour les logs d'erreur des 15 dernières minutes
            filter_str = f"""
                resource.type="cloud_run_revision"
                resource.labels.service_name="emergence-app"
                severity>=ERROR
                timestamp>="{(datetime.now(timezone.utc).replace(minute=datetime.now(timezone.utc).minute - 15)).isoformat()}"
            """

            entries = list(client.list_entries(filter_=filter_str, max_results=50))

            error_count = len(entries)
            critical_count = sum(1 for e in entries if e.severity_label == 'CRITICAL')

            status = 'OK'
            if critical_count > 0:
                status = 'CRITICAL'
            elif error_count > 5:
                status = 'WARNING'

            print(f"{'✅' if status == 'OK' else '⚠️' if status == 'WARNING' else '🚨'} Logs récents: {error_count} errors, {critical_count} critical")

            return {
                'status': status,
                'error_count': error_count,
                'critical_count': critical_count,
                'sample_errors': [
                    {
                        'timestamp': e.timestamp.isoformat(),
                        'severity': e.severity_label,
                        'message': str(e.payload)[:200]
                    }
                    for e in entries[:5]  # Max 5 exemples
                ],
                'timestamp': self.timestamp
            }

        except ImportError:
            print("⚠️  google-cloud-logging library not installed")
            return {
                'status': 'SKIPPED',
                'reason': 'Library not installed',
                'timestamp': self.timestamp
            }
        except Exception as e:
            print(f"⚠️  Logs check error: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': self.timestamp
            }

    async def generate_cloud_audit_report(self) -> Dict:
        """Génère le rapport d'audit cloud complet"""
        print("🔍 Démarrage de l'audit cloud...")
        print(f"⏰ Timestamp: {self.timestamp}")
        print(f"🎯 Target: {TARGET_REVISION}\n")

        # 1. Vérifier la santé de la production
        print("☁️  [1/3] Vérification health endpoints...")
        health_check = await self.check_production_health()
        self.results['health'] = health_check

        # 2. Vérifier les métriques Cloud Run
        print("\n📊 [2/3] Vérification métriques Cloud Run...")
        metrics_check = await self.check_cloud_run_metrics()
        self.results['metrics'] = metrics_check

        # 3. Vérifier les logs récents
        print("\n📝 [3/3] Vérification logs récents...")
        logs_check = await self.check_logs_recent_errors()
        self.results['logs'] = logs_check

        # Déterminer le statut global
        statuses = [
            health_check.get('status', 'UNKNOWN'),
            metrics_check.get('status', 'UNKNOWN'),
            logs_check.get('status', 'UNKNOWN')
        ]

        if 'CRITICAL' in statuses:
            global_status = 'CRITICAL'
        elif 'WARNING' in statuses or 'ERROR' in statuses:
            global_status = 'WARNING'
        elif all(s in ['OK', 'SKIPPED'] for s in statuses):
            global_status = 'OK'
        else:
            global_status = 'UNKNOWN'

        # Calculer le score
        total_checks = 3
        passed_checks = sum(1 for s in statuses if s == 'OK')
        health_score = int((passed_checks / total_checks * 100))

        report = {
            'timestamp': self.timestamp,
            'revision_checked': TARGET_REVISION,
            'status': global_status,
            'health_score': f"{health_score}%",
            'checks': {
                'total': total_checks,
                'passed': passed_checks,
                'failed': total_checks - passed_checks
            },
            'summary': {
                'health_endpoints': health_check.get('status'),
                'cloud_run_metrics': metrics_check.get('status'),
                'recent_logs': logs_check.get('status')
            },
            'details': self.results
        }

        print(f"\n{'='*60}")
        print(f"🎯 RÉSUMÉ AUDIT CLOUD")
        print(f"{'='*60}")
        print(f"Révision: {TARGET_REVISION}")
        print(f"Statut: {self._format_status_emoji(global_status)} {global_status}")
        print(f"Score santé: {health_score}%")
        print(f"Checks: {passed_checks}/{total_checks} passés")
        print(f"{'='*60}\n")

        return report

    async def send_email_report(self, report: Dict) -> bool:
        """Envoie le rapport par email"""
        print("📧 Envoi du rapport par email...")

        try:
            # Construire le corps HTML
            status = report.get('status', 'UNKNOWN')
            health_score = report.get('health_score', '0%')
            timestamp_str = datetime.fromisoformat(report['timestamp']).strftime("%d/%m/%Y à %H:%M:%S")

            status_color = {
                "OK": "#10b981",
                "WARNING": "#f59e0b",
                "CRITICAL": "#ef4444"
            }.get(status, "#6b7280")

            status_emoji = self._format_status_emoji(status)

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
        .status-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            margin: 10px 0;
            background: {status_color};
            color: white;
        }}
        .metric {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid #3b82f6;
        }}
        .metric-title {{
            color: #3b82f6;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 14px;
            color: #94a3b8;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>☁️ Audit Cloud ÉMERGENCE V8</h1>
            <div class="status-badge">{status_emoji} Statut: {status}</div>
            <p style="color: #94a3b8; font-size: 14px;">Généré le {timestamp_str}</p>
        </div>

        <div class="metric">
            <div class="metric-title">📊 Score de Santé Global</div>
            <div style="font-size: 32px; font-weight: 700; color: {status_color};">{health_score}</div>
        </div>

        <div class="metric">
            <div class="metric-title">☁️ Health Endpoints</div>
            <div>{self._format_status_emoji(report['summary']['health_endpoints'])} {report['summary']['health_endpoints']}</div>
            <div style="margin-top: 10px; font-size: 14px; color: #cbd5e1;">
                {report['details']['health']['endpoints_ok']}/{report['details']['health']['endpoints_checked']} endpoints OK
            </div>
        </div>

        <div class="metric">
            <div class="metric-title">📊 Métriques Cloud Run</div>
            <div>{self._format_status_emoji(report['summary']['cloud_run_metrics'])} {report['summary']['cloud_run_metrics']}</div>
        </div>

        <div class="metric">
            <div class="metric-title">📝 Logs Récents (15 min)</div>
            <div>{self._format_status_emoji(report['summary']['recent_logs'])} {report['summary']['recent_logs']}</div>
            {f'<div style="margin-top: 10px; font-size: 14px; color: #cbd5e1;">Erreurs: {report["details"]["logs"].get("error_count", 0)}, Critical: {report["details"]["logs"].get("critical_count", 0)}</div>' if report['summary']['recent_logs'] != 'SKIPPED' else ''}
        </div>

        <div class="footer">
            <p><strong>🤖 Audit Cloud Automatisé - 3x/jour</strong></p>
            <p>ÉMERGENCE V8 Production Monitoring</p>
            <p style="margin-top: 15px; font-size: 12px;">
                Révision: {TARGET_REVISION}<br>
                Contact: {ADMIN_EMAIL}
            </p>
        </div>
    </div>
</body>
</html>
"""

            # Texte simple pour fallback
            text_body = f"""
☁️ AUDIT CLOUD ÉMERGENCE V8
{'='*60}

Généré le: {timestamp_str}
Révision: {TARGET_REVISION}

STATUT GLOBAL: {status_emoji} {status}
Score de Santé: {health_score}

RÉSUMÉ:
- Health Endpoints: {report['summary']['health_endpoints']} ({report['details']['health']['endpoints_ok']}/{report['details']['health']['endpoints_checked']} OK)
- Cloud Run Metrics: {report['summary']['cloud_run_metrics']}
- Logs Récents: {report['summary']['recent_logs']}

{'='*60}

🤖 Audit Cloud Automatisé - 3x/jour
ÉMERGENCE V8 Production Monitoring
Contact: {ADMIN_EMAIL}
"""

            # Envoyer l'email (utilise le EmailService existant)
            # Import ici pour éviter les dépendances circulaires
            sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "backend"))
            from features.auth.email_service import EmailService

            email_service = EmailService()

            if not email_service.is_enabled():
                print("❌ Service email non activé")
                return False

            subject = f"☁️ Audit Cloud ÉMERGENCE - {status} - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

            success = await email_service.send_custom_email(
                to_email=ADMIN_EMAIL,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )

            if success:
                print(f"✅ Email envoyé à {ADMIN_EMAIL}")
            else:
                print(f"❌ Échec envoi email")

            return success

        except Exception as e:
            print(f"❌ Erreur envoi email: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _format_status_emoji(self, status: str) -> str:
        """Retourne un emoji selon le statut"""
        status_lower = str(status).lower()
        if status_lower in ['ok', 'healthy', 'success']:
            return '✅'
        elif status_lower in ['warning', 'degraded', 'skipped']:
            return '⚠️'
        elif status_lower in ['error', 'critical', 'failed']:
            return '🚨'
        else:
            return '📊'


async def main():
    """Point d'entrée principal pour Cloud Run Job"""
    try:
        print("""
============================================================
  EMERGENCE V8 - Cloud Audit Job
============================================================
""")

        job = CloudAuditJob()

        # Générer le rapport d'audit
        report = await job.generate_cloud_audit_report()

        # Envoyer l'email
        email_sent = await job.send_email_report(report)

        # Déterminer le code de sortie
        status = report.get('status', 'UNKNOWN')

        if status == 'OK':
            print("\n✅ Audit cloud terminé - Production saine")
            sys.exit(0)
        elif status == 'WARNING':
            print("\n⚠️  Audit cloud terminé - Avertissements détectés")
            sys.exit(0)  # Ne pas fail le job pour des warnings
        else:
            print("\n🚨 Audit cloud terminé - Problèmes critiques détectés")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
