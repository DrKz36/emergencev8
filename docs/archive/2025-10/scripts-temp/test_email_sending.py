#!/usr/bin/env python3
"""
Quick test script to verify email sending configuration

This script will send a test email to verify your SMTP configuration is working.
"""

import asyncio
import sys
from pathlib import Path

# Add src/backend to Python path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService, build_email_config_from_env


async def test_email():
    """Test email configuration"""

    print("=" * 60)
    print("EMERGENCE EMAIL SERVICE - TEST")
    print("=" * 60)
    print()

    # Build email service
    email_service = EmailService(build_email_config_from_env())

    # Display configuration (hiding password)
    config = email_service.config
    print("Configuration:")
    print(f"  Enabled: {config.enabled}")
    print(f"  SMTP Host: {config.smtp_host}")
    print(f"  SMTP Port: {config.smtp_port}")
    print(f"  SMTP User: {config.smtp_user}")
    print(
        f"  SMTP Password: {'*' * len(config.smtp_password) if config.smtp_password else 'NOT SET'}"
    )
    print(f"  From Email: {config.from_email}")
    print(f"  From Name: {config.from_name}")
    print(f"  Use TLS: {config.use_tls}")
    print()

    # Check if email service is enabled
    if not email_service.is_enabled():
        print("❌ Email service is not configured!")
        print("\nPlease set the following environment variables:")
        print("  EMAIL_ENABLED=1")
        print("  SMTP_HOST=smtp.gmail.com")
        print("  SMTP_PORT=587")
        print("  SMTP_USER=gonzalefernando@gmail.com")
        print("  SMTP_PASSWORD=dfshbvvsmyqrfkja")
        print("  SMTP_FROM_EMAIL=gonzalefernando@gmail.com")
        print()
        print("Or use the .env.beta.example file as a template:")
        print("  cp .env.beta.example .env")
        print("  # Edit .env with your credentials")
        return False

    print("✅ Email service is configured")
    print()

    # Ask for test email
    test_email_address = input(
        "Enter your email to receive a test invitation (or press Enter to skip): "
    ).strip()

    if not test_email_address:
        print("Test skipped.")
        return True

    print(f"\n📧 Sending test invitation to {test_email_address}...")

    try:
        success = await email_service.send_beta_invitation_email(
            to_email=test_email_address, base_url="https://emergence-app.ch"
        )

        if success:
            print("✅ Test email sent successfully!")
            print(f"\nPlease check your inbox at {test_email_address}")
            print("(Don't forget to check spam folder)")
            return True
        else:
            print("❌ Failed to send test email (email service returned False)")
            return False

    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function"""
    success = asyncio.run(test_email())

    print()
    print("=" * 60)

    if success:
        print("✅ All tests passed!")
        print()
        print("You can now send invitations with:")
        print("  python send_beta_invitations.py --from-file beta_testers_emails.txt")
    else:
        print("❌ Tests failed. Please check your configuration.")

    print("=" * 60)


if __name__ == "__main__":
    main()
