"""
Simple email test script without emojis for Windows compatibility
"""

import asyncio
import sys
from pathlib import Path

# Add src/backend to path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService


async def test_password_reset_email():
    """Test password reset email"""
    print("=" * 80)
    print("EMERGENCE - Test envoi email reinitialisation mot de passe")
    print("=" * 80)
    print()

    email_service = EmailService()

    print("Configuration:")
    print(f"  Email active: {email_service.config.enabled}")
    print(f"  SMTP Host: {email_service.config.smtp_host}")
    print(f"  SMTP Port: {email_service.config.smtp_port}")
    print(f"  SMTP User: {email_service.config.smtp_user}")
    print(f"  From Email: {email_service.config.from_email}")
    print()

    if not email_service.is_enabled():
        print("[ERREUR] Service email non active ou mal configure")
        return False

    print("[OK] Service email configure correctement")
    print()

    # Test with your email
    test_email = "gonzalefernando@gmail.com"
    print(f"Envoi email de test a: {test_email}")
    print()

    try:
        success = await email_service.send_password_reset_email(
            to_email=test_email,
            reset_token="test_token_abc123xyz",
            base_url="http://localhost:5173",
        )

        print()
        if success:
            print("[SUCCES] Email envoye avec succes!")
            print(f"Verifiez la boite de reception de {test_email}")
            return True
        else:
            print("[ECHEC] Echec envoi email")
            print()
            print("Verifications:")
            print("  1. Identifiants SMTP corrects dans .env")
            print("  2. Pour Gmail: utiliser un mot de passe d'application")
            print("  3. Creer sur: https://myaccount.google.com/apppasswords")
            return False

    except Exception as e:
        print()
        print(f"[ERREUR] {type(e).__name__}: {e}")
        print()
        if "authentication" in str(e).lower() or "535" in str(e):
            print("SUGGESTION: Probleme authentification SMTP")
            print("Pour Gmail, vous devez creer un mot de passe d'application:")
            print("  1. Allez sur https://myaccount.google.com/apppasswords")
            print("  2. Creez un nouveau mot de passe d'application")
            print("  3. Copiez-le dans .env comme SMTP_PASSWORD")
        return False


async def test_beta_invitation_email():
    """Test beta invitation email"""
    print("=" * 80)
    print("EMERGENCE - Test envoi email invitation beta")
    print("=" * 80)
    print()

    email_service = EmailService()

    if not email_service.is_enabled():
        print("[ERREUR] Service email non active")
        return False

    test_email = "gonzalefernando@gmail.com"
    print(f"Envoi invitation beta a: {test_email}")
    print()

    try:
        success = await email_service.send_beta_invitation_email(
            to_email=test_email, base_url="https://emergence-app.ch"
        )

        print()
        if success:
            print("[SUCCES] Email invitation envoye!")
            return True
        else:
            print("[ECHEC] Echec envoi")
            return False

    except Exception as e:
        print(f"[ERREUR] {e}")
        return False


async def main():
    """Main test function"""

    print()
    print("Quel test voulez-vous executer?")
    print("1. Email reinitialisation mot de passe")
    print("2. Email invitation beta")
    print()

    # Default to password reset for automated testing
    choice = "1"

    if choice == "2":
        success = await test_beta_invitation_email()
    else:
        success = await test_password_reset_email()

    print()
    print("=" * 80)
    if success:
        print("Test termine avec SUCCES")
    else:
        print("Test ECHOUE")
    print("=" * 80)

    return success


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTest interrompu")
        sys.exit(1)
