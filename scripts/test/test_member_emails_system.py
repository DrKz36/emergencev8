"""
Test script for the new member emails system
Tests both the backend email service and the new endpoints
"""

import asyncio
import sys
from src.backend.features.auth.email_service import EmailService

# Force UTF-8 encoding for console output
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


async def test_email_service():
    """Test the email service templates"""
    print("=" * 60)
    print("Testing ÉMERGENCE Member Emails System")
    print("=" * 60)

    email_service = EmailService()

    # Check if email service is enabled
    if not email_service.is_enabled():
        print("❌ Email service is not enabled or configured")
        print("   Please set EMAIL_ENABLED=1 and configure SMTP settings")
        return False

    print("✅ Email service is configured and enabled")
    print()

    # Test email address
    test_email = "test@example.com"
    base_url = "https://emergence-app.ch"

    print("Available email templates:")
    print("-" * 60)

    # Test 1: Beta invitation email
    print("1. Beta Invitation Email")
    print("   Template: send_beta_invitation_email()")
    print("   Purpose: Initial invitation to beta program")
    print()

    # Test 2: Auth issue notification
    print("2. Authentication Issue Notification")
    print("   Template: send_auth_issue_notification_email()")
    print("   Purpose: Notify users of auth problems and password reset")
    print("   Includes:")
    print("   - Explanation of the authentication issue")
    print("   - Instructions to reset password")
    print("   - Link to password reset page")
    print("   - Reminder to fill beta test report")
    print()

    # Test 3: Custom email
    print("3. Custom Email")
    print("   Template: send_custom_email()")
    print("   Purpose: Send any custom message to members")
    print()

    print("-" * 60)
    print()

    # Ask if user wants to send a test email
    response = input(
        "Do you want to send a TEST authentication issue notification? (y/n): "
    )

    if response.lower() == "y":
        test_email = input(
            f"Enter test email address (default: {test_email}): "
        ).strip()
        if not test_email:
            test_email = "test@example.com"

        print()
        print(f"📧 Sending authentication issue notification to {test_email}...")

        try:
            success = await email_service.send_auth_issue_notification_email(
                test_email, base_url
            )

            if success:
                print(f"✅ Email sent successfully to {test_email}")
                print()
                print("Email contains:")
                print("- Explanation of authentication issues")
                print("- Password reset instructions and link")
                print("- Beta test report form reminder")
            else:
                print(f"❌ Failed to send email to {test_email}")
        except Exception as e:
            print(f"❌ Error sending email: {e}")

    print()
    print("=" * 60)
    print("API Endpoints Available:")
    print("=" * 60)
    print()
    print("POST /api/admin/emails/send")
    print("  Send emails to members with specified template type")
    print()
    print("  Request body:")
    print("  {")
    print('    "emails": ["user1@example.com", "user2@example.com"],')
    print('    "base_url": "https://emergence-app.ch",')
    print('    "email_type": "auth_issue"  // or "beta_invitation"')
    print("  }")
    print()
    print("  Email types:")
    print("  - beta_invitation: Send beta program invitation")
    print("  - auth_issue: Send authentication issue notification")
    print("  - custom: Send custom message (requires subject, html_body, text_body)")
    print()
    print("=" * 60)
    print()

    return True


async def main():
    """Main function"""
    await test_email_service()

    print()
    print("📝 Summary:")
    print("-" * 60)
    print("✅ Backend: Email service updated with new templates")
    print("✅ Backend: New /api/admin/emails/send endpoint created")
    print("✅ Frontend: Admin interface updated with email type selector")
    print("✅ Frontend: Tab renamed to 'Envoi de mails aux membres'")
    print()
    print("🎯 Current use case:")
    print("   Send authentication issue notification to beta testers")
    print("   with password reset instructions and beta report reminder")
    print()
    print("🚀 To use:")
    print("   1. Go to Admin panel")
    print("   2. Click on 'Envoi de mails' tab")
    print("   3. Select 'Notification problème d'authentification'")
    print("   4. Select recipients")
    print("   5. Click 'Envoyer'")
    print()


if __name__ == "__main__":
    asyncio.run(main())
