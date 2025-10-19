#!/usr/bin/env python3
"""Test rapide d'envoi email audit sans emojis (compatible Windows)"""
import asyncio
import os
from datetime import datetime
import sys
from pathlib import Path

# Charger le .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Ajouter le chemin du backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))

async def test_email():
    from features.auth.email_service import EmailService

    print("Test envoi email audit...")
    print(f"Timestamp: {datetime.now().isoformat()}")

    # HTML stylisé
    html_body = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 40px;
            color: #e2e8f0;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            margin: 10px 0;
            background: #10b981;
            color: white;
        }
        .metric {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid #3b82f6;
        }
        .metric-title {
            color: #3b82f6;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 10px;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 14px;
            color: #94a3b8;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Audit Cloud EMERGENCE V8 - TEST</h1>
            <div class="status-badge">Statut: OK</div>
            <p style="color: #94a3b8; font-size: 14px;">Test rapide - """ + datetime.now().strftime("%d/%m/%Y à %H:%M:%S") + """</p>
        </div>

        <div class="metric">
            <div class="metric-title">Score de Santé Global</div>
            <div style="font-size: 32px; font-weight: 700; color: #10b981;">100%</div>
        </div>

        <div class="metric">
            <div class="metric-title">Health Endpoints</div>
            <div>OK - Test réussi</div>
        </div>

        <div class="metric">
            <div class="metric-title">Métriques Cloud Run</div>
            <div>OK - Production stable</div>
        </div>

        <div class="metric">
            <div class="metric-title">Logs Récents (15 min)</div>
            <div>OK - Aucune erreur</div>
        </div>

        <div class="footer">
            <p><strong>Audit Cloud Automatisé - TEST</strong></p>
            <p>ÉMERGENCE V8 Production Monitoring</p>
            <p style="margin-top: 15px; font-size: 12px;">
                Contact: gonzalefernando@gmail.com
            </p>
        </div>
    </div>
</body>
</html>
"""

    text_body = f"""
AUDIT CLOUD ÉMERGENCE V8 - TEST
============================================================

Généré le: {datetime.now().strftime("%d/%m/%Y à %H:%M:%S")}

STATUT GLOBAL: OK
Score de Santé: 100%

RÉSUMÉ:
- Health Endpoints: OK
- Cloud Run Metrics: OK
- Logs Récents: OK

============================================================

Audit Cloud Automatisé - TEST
ÉMERGENCE V8 Production Monitoring
Contact: gonzalefernando@gmail.com
"""

    email_service = EmailService()

    if not email_service.is_enabled():
        print("Service email non activé - vérifier SMTP_PASSWORD")
        return False

    print("Envoi de l'email...")
    subject = f"[TEST] Audit Cloud ÉMERGENCE - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    success = await email_service.send_custom_email(
        to_email="gonzalefernando@gmail.com",
        subject=subject,
        html_body=html_body,
        text_body=text_body
    )

    if success:
        print("Email envoyé avec succès à gonzalefernando@gmail.com!")
        print("Vérifie ta boîte mail!")
        return True
    else:
        print("Échec envoi email")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_email())
    sys.exit(0 if result else 1)
