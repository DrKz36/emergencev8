"""
Test beta invitation email
"""
import asyncio
import sys
from pathlib import Path

# Add src/backend to path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService


async def main():
    print("=" * 80)
    print("EMERGENCE - Envoi invitation beta")
    print("=" * 80)
    print()

    email_service = EmailService()

    if not email_service.is_enabled():
        print("[ERREUR] Service email non active")
        return False

    test_email = "gonzalefernando@gmail.com"
    print(f"Destinataire: {test_email}")
    print("Type: Email invitation programme Beta EMERGENCE V8")
    print()
    print("Envoi en cours...")

    try:
        success = await email_service.send_beta_invitation_email(
            to_email=test_email,
            base_url="https://emergence-app.ch"
        )

        print()
        if success:
            print("[SUCCES] Email invitation beta envoye avec succes!")
            print()
            print("Contenu de l'email:")
            print("  - Titre: Bienvenue dans le programme Beta EMERGENCE V8")
            print("  - Dates: 13 octobre - 3 novembre 2025")
            print("  - Lien acces: https://emergence-app.ch")
            print("  - Formulaire rapport: https://emergence-app.ch/beta_report.html")
            print("  - 8 phases de test detaillees")
            print()
            print(f"Verifiez votre boite mail: {test_email}")
            return True
        else:
            print("[ECHEC] Echec envoi")
            return False

    except Exception as e:
        print(f"[ERREUR] {e}")
        return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nInterrompu")
        sys.exit(1)
