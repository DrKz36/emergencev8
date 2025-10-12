"""
Script to trigger a password reset email via the API
This creates a real password reset token and sends the email
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.core.database.manager import DatabaseManager
from backend.features.auth.service import AuthService
from backend.features.auth.email_service import EmailService


async def trigger_reset_for_email(email: str):
    """Trigger a password reset email for the given email address"""

    # Initialize database
    db_path = Path(__file__).parent.parent / "emergence.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    # Initialize services
    auth_service = AuthService(db=db)
    email_service = EmailService()

    print(f"📧 Triggering password reset for: {email}")
    print()

    # Check if email exists in allowlist
    user = await db.fetch_one(
        "SELECT email, role FROM auth_allowlist WHERE email = ?",
        (email,)
    )

    if not user:
        print(f"❌ Email not found in allowlist: {email}")
        print("   Add the email to the allowlist first using the admin dashboard")
        await db.close()
        return

    print(f"✅ Found user: {user['email']} (role: {user['role']})")
    print()

    # Create password reset token
    try:
        token = await auth_service.create_password_reset_token(email)
        print(f"✅ Password reset token created: {token[:20]}...")
        print()
    except Exception as e:
        print(f"❌ Failed to create token: {e}")
        await db.close()
        return

    # Check email service configuration
    if not email_service.is_enabled():
        print("⚠️  Email service is not configured")
        print(f"   Reset link (copy this to browser):")
        print(f"   https://emergence-app.ch/reset-password?token={token}")
        print()
        print("To enable emails, configure these environment variables:")
        print("  EMAIL_ENABLED=1")
        print("  SMTP_USER=your-email@gmail.com")
        print("  SMTP_PASSWORD=your-app-password")
    else:
        # Send the email
        print(f"📤 Sending email to: {email}")
        success = await email_service.send_password_reset_email(
            to_email=email,
            reset_token=token,
            base_url="https://emergence-app.ch",
        )

        if success:
            print("✅ Email sent successfully!")
            print(f"   Check inbox at: {email}")
        else:
            print("❌ Failed to send email")
            print(f"   Manual reset link:")
            print(f"   https://emergence-app.ch/reset-password?token={token}")

    await db.close()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/trigger_password_reset_email.py <email>")
        print("Example: python scripts/trigger_password_reset_email.py gonzalefernando@gmail.com")
        sys.exit(1)

    email = sys.argv[1]
    await trigger_reset_for_email(email)


if __name__ == "__main__":
    asyncio.run(main())
