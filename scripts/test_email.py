"""
Test script to send a password reset email
Usage: python scripts/test_email.py <recipient_email>
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.features.auth.email_service import EmailService


@pytest.fixture
def recipient_email() -> str:
    """
    Resolve recipient email for pytest execution.

    Pytest collection skips the test unless TEST_EMAIL_RECIPIENT or
    SMTP_TEST_RECIPIENT is defined in the environment.
    """
    from_env = os.getenv("TEST_EMAIL_RECIPIENT") or os.getenv("SMTP_TEST_RECIPIENT")
    if not from_env:
        pytest.skip(
            "Email smoke test disabled. Set TEST_EMAIL_RECIPIENT or SMTP_TEST_RECIPIENT to run it."
        )
    return from_env


async def test_send_email(recipient_email: str):
    """Send a test password reset email"""

    # Build email service from environment variables
    email_service = EmailService()

    print("📧 Email Service Configuration:")
    print(f"   Enabled: {email_service.is_enabled()}")
    print(f"   SMTP Host: {email_service.config.smtp_host}")
    print(f"   SMTP Port: {email_service.config.smtp_port}")
    print(f"   SMTP User: {email_service.config.smtp_user}")
    print(f"   From Email: {email_service.config.from_email}")
    print(f"   From Name: {email_service.config.from_name}")
    print()

    if not email_service.is_enabled():
        print("❌ Email service is not enabled or not properly configured!")
        print()
        print("To enable email service, set these environment variables:")
        print("  EMAIL_ENABLED=1")
        print("  SMTP_HOST=smtp.gmail.com")
        print("  SMTP_PORT=587")
        print("  SMTP_USER=your-email@gmail.com")
        print("  SMTP_PASSWORD=your-app-password")
        print()
        print("For Gmail, you need to create an App Password:")
        print("  1. Go to https://myaccount.google.com/")
        print("  2. Security > 2-Step Verification (enable it)")
        print("  3. Security > App Passwords")
        print("  4. Generate a new app password")
        print()
        return

    # Generate a test token
    test_token = "test-token-12345-abcdef-67890"
    base_url = "https://emergence-app.ch"

    print(f"📤 Sending test email to: {recipient_email}")
    print(f"   Reset token: {test_token}")
    print(f"   Reset link: {base_url}/reset-password?token={test_token}")
    print()

    # Send the email
    success = await email_service.send_password_reset_email(
        to_email=recipient_email,
        reset_token=test_token,
        base_url=base_url,
    )

    if success:
        print("✅ Email sent successfully!")
        print(f"   Check your inbox at: {recipient_email}")
    else:
        print("❌ Failed to send email")
        print("   Check the logs above for error details")


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_email.py <recipient_email>")
        print("Example: python scripts/test_email.py gonzalefernando@gmail.com")
        sys.exit(1)

    recipient_email = sys.argv[1]
    await test_send_email(recipient_email)


if __name__ == "__main__":
    asyncio.run(main())
