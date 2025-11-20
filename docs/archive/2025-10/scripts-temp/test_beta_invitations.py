"""
Test script for beta invitations endpoints
Quick verification that the new endpoints work correctly
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from backend.features.auth.service import AuthService
from backend.features.auth.email_service import EmailService
from backend.core.database.manager import DatabaseManager


async def test_email_service():
    """Test that email service is configured"""
    print("\n=== Testing Email Service ===")

    email_service = EmailService()

    if email_service.is_enabled():
        print("[OK] Email service is enabled")
        print(f"   SMTP Host: {email_service.config.smtp_host}")
        print(f"   SMTP Port: {email_service.config.smtp_port}")
        print(f"   From Email: {email_service.config.from_email}")
    else:
        print("[FAIL] Email service is NOT enabled")
        print("   Check your .env configuration")

    return email_service.is_enabled()


async def test_allowlist():
    """Test that we can retrieve allowlist emails"""
    print("\n=== Testing Allowlist Retrieval ===")

    try:
        db_manager = DatabaseManager()
        await db_manager.connect()

        auth_service = AuthService(db_manager)

        # Get allowlist entries
        entries, total = await auth_service.list_allowlist(status="active", limit=100)

        print(f"[OK] Found {total} active allowlist entries")

        if entries:
            print("\nFirst 5 emails:")
            for i, entry in enumerate(entries[:5], 1):
                print(f"   {i}. {entry.email}")

        await db_manager.disconnect()

        return total > 0

    except Exception as e:
        print(f"[FAIL] Error retrieving allowlist: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("BETA INVITATIONS ENDPOINTS TEST")
    print("=" * 60)

    email_ok = await test_email_service()
    allowlist_ok = await test_allowlist()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Email Service:  {'[OK]' if email_ok else '[FAIL]'}")
    print(f"Allowlist:      {'[OK]' if allowlist_ok else '[FAIL]'}")

    if email_ok and allowlist_ok:
        print("\n[SUCCESS] All tests passed! Ready to send beta invitations.")
        print("\nNext steps:")
        print("1. Start the backend server")
        print("2. Login as admin")
        print("3. Go to Admin > Invitations Beta tab")
        print("4. Select emails and send invitations")
    else:
        print(
            "\n[WARNING] Some tests failed. Fix the issues before sending invitations."
        )

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
