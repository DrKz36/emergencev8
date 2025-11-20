"""
Send connection issues notification email to selected beta testers
"""

import asyncio
import sys
import io
from pathlib import Path

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Load .env file from project root
from dotenv import load_dotenv

# Go up two directories to reach project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

from src.backend.features.auth.email_service import EmailService


# LISTE DES DESTINATAIRES - FOURNIE PAR L'ADMIN
RECIPIENTS = [
    "pepin1936@gmail.com",
    "stephane.cola@bluewin.ch",
    "degeo81@gmail.com",
    "fernando36@bluewin.ch",
]


async def send_connection_issues_notification():
    """Send connection issues notification to selected members"""

    base_url = "https://emergence-app.ch"

    print("=" * 80)
    print("ENVOI D'EMAILS - PROBLÈMES DE CONNEXION RÉSOLUS")
    print("=" * 80)
    print()
    print("📧 Type d'email : Notification problèmes de connexion + conseils")
    print(f"🌐 Base URL : {base_url}")
    print()
    print("=" * 80)
    print("LISTE DES DESTINATAIRES")
    print("=" * 80)
    print()

    for i, email in enumerate(RECIPIENTS, 1):
        print(f"  {i}. {email}")

    print()
    print(f"📊 TOTAL : {len(RECIPIENTS)} destinataires")
    print()
    print("=" * 80)
    print()

    # CONFIRMATION (skip if --yes flag provided)
    skip_confirmation = "--yes" in sys.argv or "-y" in sys.argv

    if not skip_confirmation:
        print(
            "⚠️  ATTENTION : Vous êtes sur le point d'envoyer cet email à ces adresses."
        )
        print()
        confirmation = (
            input("Confirmez-vous l'envoi à ces adresses uniquement ? (oui/non) : ")
            .strip()
            .lower()
        )

        if confirmation not in ["oui", "yes", "o", "y"]:
            print()
            print("❌ Envoi annulé par l'utilisateur.")
            return False
    else:
        print("✅ Confirmation automatique activée (--yes)")
        print()

    print()
    print("=" * 80)
    print("ENVOI EN COURS...")
    print("=" * 80)
    print()

    # Initialize email service
    email_service = EmailService()

    # Check if email service is enabled
    if not email_service.is_enabled():
        print("❌ ERREUR : Le service email n'est pas activé ou configuré")
        return False

    results = {
        "total": len(RECIPIENTS),
        "sent": 0,
        "failed": 0,
        "sent_to": [],
        "failed_emails": [],
    }

    # Email content
    subject = "Mise à jour importante - Résolution des problèmes de connexion"

    for email in RECIPIENTS:
        try:
            print(f"📤 Envoi à {email}...", end=" ")

            # HTML version
            html_body = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
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
        .header img {
            max-width: 120px;
            margin-bottom: 15px;
        }
        .header h1 {
            color: #3b82f6;
            margin: 0;
            font-size: 28px;
        }
        .content {
            margin: 20px 0;
        }
        .highlight {
            background: rgba(59, 130, 246, 0.1);
            border-left: 4px solid #3b82f6;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }
        .success {
            background: rgba(16, 185, 129, 0.1);
            border-left: 4px solid #10b981;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }
        .warning {
            background: rgba(251, 191, 36, 0.1);
            border-left: 4px solid #f59e0b;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 14px;
            color: #94a3b8;
        }
        .signature {
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-style: italic;
            color: #cbd5e1;
        }
        ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        li {
            margin: 8px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://emergence-app.ch/assets/emergence_logo.png" alt="ÉMERGENCE Logo">
            <h1>🔧 ÉMERGENCE V8</h1>
            <p>Mise à jour importante - Programme Beta</p>
        </div>

        <div class="content">
            <p>Bonjour,</p>

            <p>Je vous contacte suite aux problèmes de connexion que plusieurs d'entre vous ont rencontrés ces derniers jours sur l'application. Je tiens tout d'abord à m'excuser pour ces désagréments.</p>

            <h2 style="color: #3b82f6; margin-top: 30px;">🔍 Problèmes identifiés et résolus</h2>
            <ul>
                <li>Connexions impossibles</li>
                <li>Instances persistantes empêchant l'accès</li>
                <li>Vérifications d'email itératives (normalement corrigé - une seule réinitialisation de mot de passe devrait désormais suffire)</li>
            </ul>

            <div class="success">
                <strong>✅ Situation actuelle :</strong><br>
                Depuis environ 24 heures, l'application est beaucoup plus stable et robuste. Les principaux problèmes de connexion sont résolus.
            </div>

            <h2 style="color: #3b82f6; margin-top: 30px;">⚠️ Point d'attention - Chargement de la dernière session</h2>

            <p>Il subsiste un problème potentiel lors de l'interaction avec un agent : <strong>la dernière session n'est pas toujours chargée automatiquement</strong>, ce qui peut affecter la mémoire conversationnelle.</p>

            <div class="warning">
                <strong>🔧 Solutions de contournement :</strong><br><br>
                Si vous constatez que l'agent ne se souvient pas du contexte précédent :
                <ol style="margin-top: 10px;">
                    <li>Recharger la page une fois dans l'application</li>
                    <li>Aller dans "Conversations" et sélectionner manuellement la dernière conversation active</li>
                    <li>Attendre quelques secondes avant d'envoyer votre premier message pour permettre le chargement complet de la mémoire</li>
                </ol>
            </div>

            <h2 style="color: #3b82f6; margin-top: 30px;">🙏 Votre aide est précieuse</h2>

            <p>En tant que bêta-testeurs, je vous invite vivement à <strong>me signaler tout problème dès qu'il survient</strong>. Les bugs peuvent varier d'une session à l'autre et d'un utilisateur à l'autre, ce qui rend vos retours essentiels pour identifier et corriger rapidement les anomalies.</p>

            <div class="highlight">
                <strong>📧 Si vous rencontrez :</strong>
                <ul>
                    <li>Des problèmes de vérification d'email répétés</li>
                    <li>Des difficultés de connexion</li>
                    <li>Tout autre comportement anormal</li>
                </ul>
                <strong>N'hésitez pas à me contacter immédiatement : gonzalefernando@gmail.com</strong>
            </div>

            <div class="signature">
                <p>Merci pour votre patience et votre collaboration précieuse dans cette phase de test ! 🙏<br><br>
                Cordialement,<br><br>
                L'équipe d'Émergence<br>
                <strong>FG, Claude et Codex</strong></p>
            </div>
        </div>

        <div class="footer">
            <p><strong>Besoin d'aide ?</strong><br>
            📧 Email : gonzalefernando@gmail.com</p>

            <p style="margin-top: 20px;">Cet email a été envoyé automatiquement par ÉMERGENCE.<br>
            Merci de ne pas répondre à cet email.</p>
        </div>
    </div>
</body>
</html>
            """

            # Plain text version
            text_body = """
MISE À JOUR IMPORTANTE - RÉSOLUTION DES PROBLÈMES DE CONNEXION

Bonjour,

Je vous contacte suite aux problèmes de connexion que plusieurs d'entre vous ont rencontrés ces derniers jours sur l'application. Je tiens tout d'abord à m'excuser pour ces désagréments.

🔍 PROBLÈMES IDENTIFIÉS ET RÉSOLUS
- Connexions impossibles
- Instances persistantes empêchant l'accès
- Vérifications d'email itératives (normalement corrigé - une seule réinitialisation de mot de passe devrait désormais suffire)

✅ SITUATION ACTUELLE
Depuis environ 24 heures, l'application est beaucoup plus stable et robuste. Les principaux problèmes de connexion sont résolus.

⚠️ POINT D'ATTENTION - CHARGEMENT DE LA DERNIÈRE SESSION

Il subsiste un problème potentiel lors de l'interaction avec un agent : la dernière session n'est pas toujours chargée automatiquement, ce qui peut affecter la mémoire conversationnelle.

🔧 SOLUTIONS DE CONTOURNEMENT

Si vous constatez que l'agent ne se souvient pas du contexte précédent :
1. Recharger la page une fois dans l'application
2. Aller dans "Conversations" et sélectionner manuellement la dernière conversation active
3. Attendre quelques secondes avant d'envoyer votre premier message pour permettre le chargement complet de la mémoire

🙏 VOTRE AIDE EST PRÉCIEUSE

En tant que bêta-testeurs, je vous invite vivement à me signaler tout problème dès qu'il survient. Les bugs peuvent varier d'une session à l'autre et d'un utilisateur à l'autre, ce qui rend vos retours essentiels pour identifier et corriger rapidement les anomalies.

📧 SI VOUS RENCONTREZ :
- Des problèmes de vérification d'email répétés
- Des difficultés de connexion
- Tout autre comportement anormal

N'hésitez pas à me contacter immédiatement : gonzalefernando@gmail.com

Merci pour votre patience et votre collaboration précieuse dans cette phase de test !

Cordialement,

L'équipe d'Émergence
FG, Claude et Codex

---
BESOIN D'AIDE ?
Email : gonzalefernando@gmail.com

Cet email a été envoyé automatiquement par ÉMERGENCE.
Merci de ne pas répondre à cet email.
            """

            success = await email_service.send_custom_email(
                to_email=email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
            )

            if success:
                results["sent"] += 1
                results["sent_to"].append(email)
                print("✅ Envoyé")
            else:
                results["failed"] += 1
                results["failed_emails"].append(email)
                print("❌ Échec")

        except Exception as e:
            results["failed"] += 1
            results["failed_emails"].append(email)
            print(f"❌ Erreur : {e}")

    print()
    print("=" * 80)
    print("RÉSULTATS DE L'ENVOI")
    print("=" * 80)
    print()
    print(f"📊 Total : {results['total']}")
    print(f"✅ Envoyés : {results['sent']}")
    print(f"❌ Échoués : {results['failed']}")
    print()

    if results["sent"] > 0:
        print("✅ Emails envoyés avec succès à :")
        for email in results["sent_to"]:
            print(f"   • {email}")
        print()

    if results["failed"] > 0:
        print("❌ Emails échoués pour :")
        for email in results["failed_emails"]:
            print(f"   • {email}")
        print()

    print("=" * 80)

    return results["failed"] == 0


async def main():
    """Main function"""
    success = await send_connection_issues_notification()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
