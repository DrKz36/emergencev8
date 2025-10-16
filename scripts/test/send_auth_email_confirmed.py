"""
Send authentication issue email to selected beta testers - CONFIRMED
"""
import asyncio
import sys
import io
import os
from pathlib import Path

# Force UTF-8 encoding for console output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from src.backend.features.auth.email_service import EmailService


# LISTE DES DESTINATAIRES - CONFIRMÉE PAR L'ADMIN
RECIPIENTS = [
    "degeo81@gmail.com",
    "fernando36@bluewin.ch",
    "gonzalefernando@gmail.com",
    "pepin1936@gmail.com",
    "stephane.cola@bluewin.ch"
]


async def send_to_confirmed_members():
    """Send authentication issue notification to confirmed members"""

    base_url = "https://emergence-app.ch"

    print("=" * 80)
    print("ENVOI D'EMAILS AUX MEMBRES - CONFIRMÉ")
    print("=" * 80)
    print()
    print("📧 Type d'email : Notification problème d'authentification")
    print(f"🌐 Base URL : {base_url}")
    print()
    print("📋 Destinataires :")
    for i, email in enumerate(RECIPIENTS, 1):
        print(f"   {i}. {email}")
    print()
    print(f"📊 TOTAL : {len(RECIPIENTS)} destinataires")
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
        "failed_emails": []
    }

    for email in RECIPIENTS:
        try:
            print(f"📤 Envoi à {email}...", end=" ", flush=True)

            success = await email_service.send_auth_issue_notification_email(
                to_email=email,
                base_url=base_url
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
    print(f"✅ Envoyés avec succès : {results['sent']}")
    print(f"❌ Échoués : {results['failed']}")
    print()

    if results['sent'] > 0:
        print("✅ Emails envoyés avec succès à :")
        for email in results['sent_to']:
            print(f"   • {email}")
        print()

    if results['failed'] > 0:
        print("❌ Emails échoués pour :")
        for email in results['failed_emails']:
            print(f"   • {email}")
        print()

    print("=" * 80)
    print()

    if results['sent'] == results['total']:
        print("🎉 SUCCÈS TOTAL ! Tous les emails ont été envoyés.")
    elif results['sent'] > 0:
        print("⚠️  SUCCÈS PARTIEL : Certains emails n'ont pas pu être envoyés.")
    else:
        print("❌ ÉCHEC : Aucun email n'a pu être envoyé.")

    print()
    print("=" * 80)

    return results['failed'] == 0


async def main():
    """Main function"""
    success = await send_to_confirmed_members()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
