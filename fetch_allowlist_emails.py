#!/usr/bin/env python3
"""
Script to fetch all emails from the allowlist and save them to a file

Usage:
    python fetch_allowlist_emails.py
    python fetch_allowlist_emails.py --output my_emails.txt
"""
import asyncio
import sys
from pathlib import Path

# Add src/backend to Python path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.service import AuthService
from core.config import build_auth_config_from_env


async def fetch_allowlist_emails(output_file: str = "beta_testers_emails.txt"):
    """Fetch all active emails from allowlist"""

    print("="*60)
    print("FETCH ALLOWLIST EMAILS")
    print("="*60)
    print()

    # Build auth service
    config = build_auth_config_from_env()
    auth_service = AuthService(config)

    print("📋 Fetching allowlist from database...")

    try:
        # Fetch all active allowlist entries
        items, total = await auth_service.list_allowlist(
            status="active",
            search=None,
            limit=1000,  # Get all entries
            offset=0,
        )

        if not items:
            print("⚠️  No active emails found in allowlist")
            return

        print(f"✅ Found {len(items)} active email(s) in allowlist")
        print()

        # Extract emails
        emails = [item.email for item in items]

        # Sort emails alphabetically
        emails.sort()

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Beta Testers Email List - Fetched from Allowlist\n")
            f.write(f"# Total: {len(emails)} emails\n")
            f.write(f"# Generated automatically on {Path(__file__).name}\n\n")

            for email in emails:
                f.write(f"{email}\n")

        print(f"✅ Saved {len(emails)} email(s) to '{output_file}'")
        print()
        print("Emails:")
        for i, email in enumerate(emails, 1):
            print(f"  {i}. {email}")

        print()
        print("="*60)
        print("Next steps:")
        print(f"  1. Review the emails in '{output_file}'")
        print(f"  2. Send invitations: python send_beta_invitations.py --from-file {output_file}")
        print("="*60)

    except Exception as e:
        print(f"❌ Error fetching allowlist: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch all emails from allowlist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="beta_testers_emails.txt",
        help="Output file path (default: beta_testers_emails.txt)"
    )

    args = parser.parse_args()

    # Run async function
    asyncio.run(fetch_allowlist_emails(args.output))


if __name__ == "__main__":
    main()
