"""
Test script pour vérifier la configuration email avec emergence.app.ch@gmail.com
Quick test pour valider SMTP Gmail avec app password
"""
import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Add src to path for imports
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir / "src"))

# Load .env file
from dotenv import load_dotenv
load_dotenv(root_dir / ".env")

from backend.features.auth.email_service import EmailService, build_email_config_from_env


async def test_email_config():
    """Test email configuration and send a test email"""
    print("=" * 60)
    print("TEST EMAIL CONFIGURATION - ÉMERGENCE")
    print("=" * 60)
    print()

    # Build config from env
    config = build_email_config_from_env()

    print("📧 Email Configuration:")
    print(f"  SMTP Host: {config.smtp_host}")
    print(f"  SMTP Port: {config.smtp_port}")
    print(f"  SMTP User: {config.smtp_user}")
    print(f"  From Email: {config.from_email}")
    print(f"  From Name: {config.from_name}")
    print(f"  Use TLS: {config.use_tls}")
    print(f"  Enabled: {config.enabled}")
    print(f"  Password: {'SET ✅' if config.smtp_password else 'NOT SET ❌'}")
    print()

    # Create email service
    email_service = EmailService(config)

    if not email_service.is_enabled():
        print("❌ Email service is NOT enabled or not properly configured")
        return False

    print("✅ Email service is properly configured")
    print()

    # Send test email
    print("📤 Sending test email...")
    test_recipient = "gonzalefernando@gmail.com"

    success = await email_service.send_custom_email(
        to_email=test_recipient,
        subject="✅ Test ÉMERGENCE Email System - emergence.app.ch@gmail.com",
        html_body="""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2563eb;">✅ Email System Test</h2>
            <p>Ceci est un email de test du système ÉMERGENCE.</p>
            <p><strong>Configuration:</strong></p>
            <ul>
                <li>SMTP: Gmail (smtp.gmail.com:587)</li>
                <li>Compte: emergence.app.ch@gmail.com</li>
                <li>App Password: Configuré ✅</li>
            </ul>
            <p>Si tu reçois cet email, la configuration est <strong>OPÉRATIONNELLE</strong> 🔥</p>
            <hr>
            <p style="font-size: 12px; color: #666;">
                ÉMERGENCE V8 - Système Email
            </p>
        </body>
        </html>
        """,
        text_body="""
        ✅ Email System Test

        Ceci est un email de test du système ÉMERGENCE.

        Configuration:
        - SMTP: Gmail (smtp.gmail.com:587)
        - Compte: emergence.app.ch@gmail.com
        - App Password: Configuré ✅

        Si tu reçois cet email, la configuration est OPÉRATIONNELLE 🔥

        ---
        ÉMERGENCE V8 - Système Email
        """
    )

    print()
    print("=" * 60)
    if success:
        print(f"✅ Email de test envoyé avec succès à {test_recipient}")
        print("Vérifie ta boîte mail (inbox ou spam)")
    else:
        print("❌ Échec de l'envoi de l'email de test")
        print("Vérifie les logs pour plus de détails")
    print("=" * 60)

    return success


if __name__ == "__main__":
    result = asyncio.run(test_email_config())
    sys.exit(0 if result else 1)
