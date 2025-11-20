"""
Test script for email sending functionality
Tests the SMTP configuration and email service
"""

import asyncio
import sys
from pathlib import Path

# Add src/backend to path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService


async def test_email_service():
    """Test the email service configuration and sending"""

    print("=" * 80)
    print("ÉMERGENCE - Test d'envoi d'email")
    print("=" * 80)
    print()

    # Initialize email service
    email_service = EmailService()

    # Check configuration
    print("📋 Configuration:")
    print(f"  - Email activé: {email_service.config.enabled}")
    print(f"  - SMTP Host: {email_service.config.smtp_host}")
    print(f"  - SMTP Port: {email_service.config.smtp_port}")
    print(f"  - SMTP User: {email_service.config.smtp_user}")
    print(f"  - From Email: {email_service.config.from_email}")
    print(f"  - From Name: {email_service.config.from_name}")
    print(f"  - Use TLS: {email_service.config.use_tls}")
    print()

    # Check if service is enabled
    if not email_service.is_enabled():
        print("❌ Le service d'email n'est pas activé ou mal configuré!")
        print()
        print("Vérifiez que ces variables d'environnement sont définies:")
        print("  - EMAIL_ENABLED=1")
        print("  - SMTP_HOST")
        print("  - SMTP_USER")
        print("  - SMTP_PASSWORD")
        return False

    print("✅ Service d'email configuré correctement")
    print()

    # Prompt for test email
    test_email = input(
        "Entrez l'adresse email pour le test (ou appuyez sur Entrée pour utiliser gonzalefernando@gmail.com): "
    ).strip()
    if not test_email:
        test_email = "gonzalefernando@gmail.com"

    print()
    print(f"📧 Envoi d'un email de test à {test_email}...")
    print()

    # Choose test type
    print("Quel type d'email voulez-vous tester ?")
    print("1. Email de réinitialisation de mot de passe")
    print("2. Email d'invitation beta")
    choice = input("Votre choix (1 ou 2): ").strip()

    print()

    try:
        if choice == "2":
            # Test beta invitation email
            print("Envoi de l'email d'invitation beta...")
            success = await email_service.send_beta_invitation_email(
                to_email=test_email, base_url="https://emergence-app.ch"
            )
        else:
            # Test password reset email (default)
            print("Envoi de l'email de réinitialisation de mot de passe...")
            success = await email_service.send_password_reset_email(
                to_email=test_email,
                reset_token="test_token_123456789",
                base_url="http://localhost:5173",
            )

        if success:
            print()
            print("✅ Email envoyé avec succès!")
            print(f"📬 Vérifiez la boîte de réception de {test_email}")
            print()
            return True
        else:
            print()
            print("❌ Échec de l'envoi de l'email")
            print()
            print("Causes possibles:")
            print("  - Identifiants SMTP incorrects")
            print("  - Mot de passe d'application Google incorrect")
            print("  - Port bloqué par le firewall")
            print("  - Compte Gmail nécessite un mot de passe d'application")
            print()
            return False

    except Exception as e:
        print()
        print(f"❌ Erreur lors de l'envoi: {type(e).__name__}: {e}")
        print()

        if "authentication" in str(e).lower():
            print("💡 Suggestion: Vérifiez vos identifiants SMTP")
            print("   Pour Gmail, vous devez utiliser un 'mot de passe d'application'")
            print("   Créez-en un sur: https://myaccount.google.com/apppasswords")

        return False


async def main():
    """Main test function"""
    success = await test_email_service()

    print()
    print("=" * 80)
    if success:
        print("✅ Test terminé avec succès!")
    else:
        print("❌ Test échoué")
    print("=" * 80)

    return success


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    # Run test
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
