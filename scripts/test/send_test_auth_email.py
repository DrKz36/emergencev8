"""
Send test authentication issue email to admin
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

print(f"🔧 Loading environment from: {env_path}")
print(f"   EMAIL_ENABLED={os.getenv('EMAIL_ENABLED', 'NOT SET')}")
print(f"   SMTP_HOST={os.getenv('SMTP_HOST', 'NOT SET')}")
print(f"   SMTP_USER={os.getenv('SMTP_USER', 'NOT SET')}")
print()

from src.backend.features.auth.email_service import EmailService


async def send_test_email():
    """Send test authentication issue notification to admin"""

    admin_email = "gonzalefernando@gmail.com"
    base_url = "https://emergence-app.ch"

    print("=" * 80)
    print("ENVOI D'EMAIL DE TEST - NOTIFICATION PROBLÈME D'AUTHENTIFICATION")
    print("=" * 80)
    print()
    print(f"📧 Destinataire : {admin_email}")
    print(f"🌐 Base URL : {base_url}")
    print(f"🔗 Lien reset : {base_url}/reset-password.html")
    print(f"🔗 Lien formulaire : {base_url}/beta_report.html")
    print()

    # Initialize email service
    email_service = EmailService()

    # Check if email service is enabled
    if not email_service.is_enabled():
        print("❌ ERREUR : Le service email n'est pas activé ou configuré")
        print()
        print("Vérifiez les variables d'environnement :")
        print("  - EMAIL_ENABLED=1")
        print("  - SMTP_HOST")
        print("  - SMTP_USER")
        print("  - SMTP_PASSWORD")
        print()
        return False

    print("✅ Service email configuré et activé")
    print()
    print("📤 Envoi en cours...")
    print()

    try:
        # Send the authentication issue notification email
        success = await email_service.send_auth_issue_notification_email(
            to_email=admin_email,
            base_url=base_url
        )

        if success:
            print("=" * 80)
            print("✅ EMAIL ENVOYÉ AVEC SUCCÈS !")
            print("=" * 80)
            print()
            print(f"📬 Vérifiez votre boîte mail : {admin_email}")
            print()
            print("L'email contient :")
            print("  ✅ Design HTML avec logo ÉMERGENCE")
            print("  ✅ Explication du problème d'authentification")
            print("  ✅ Bouton CTA 'Réinitialiser mon mot de passe'")
            print("  ✅ Lien : https://emergence-app.ch/reset-password.html")
            print("  ✅ Instructions étape par étape")
            print("  ✅ Note pour ceux sans problème")
            print("  ✅ Bouton CTA 'Remplir le formulaire beta'")
            print("  ✅ Lien : https://emergence-app.ch/beta_report.html")
            print("  ✅ Arguments sur l'importance du feedback")
            print()
            print("💡 Si l'email vous convient, vous pouvez l'envoyer aux membres")
            print("   de la waitlist via l'interface Admin > Envoi de mails")
            print()
            return True
        else:
            print("=" * 80)
            print("❌ ÉCHEC DE L'ENVOI")
            print("=" * 80)
            print()
            print("L'email n'a pas pu être envoyé.")
            print("Vérifiez :")
            print("  - La configuration SMTP")
            print("  - Les credentials")
            print("  - La connexion réseau")
            print()
            return False

    except Exception as e:
        print("=" * 80)
        print("❌ ERREUR LORS DE L'ENVOI")
        print("=" * 80)
        print()
        print(f"Erreur : {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main function"""
    success = await send_test_email()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
