#!/usr/bin/env python3
"""
Script to send beta invitation emails to multiple users

Usage:
    python send_beta_invitations.py email1@example.com email2@example.com email3@example.com

Or with a file:
    python send_beta_invitations.py --from-file emails.txt

Environment variables required:
    EMAIL_ENABLED=1
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your_email@gmail.com
    SMTP_PASSWORD=your_app_password
    SMTP_FROM_EMAIL=your_email@gmail.com
"""

import asyncio
import sys
from pathlib import Path

# Add src/backend to Python path
backend_path = Path(__file__).parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

from features.auth.email_service import EmailService, build_email_config_from_env


async def send_invitations(
    emails: list[str], base_url: str = "https://emergence-app.ch"
):
    """Send beta invitations to a list of emails"""

    # Build email service
    email_service = EmailService(build_email_config_from_env())

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
        return

    print(f"📧 Sending beta invitations to {len(emails)} email(s)...\n")

    results = {"sent": [], "failed": []}

    for i, email in enumerate(emails, 1):
        print(f"[{i}/{len(emails)}] Sending to {email}... ", end="", flush=True)

        try:
            success = await email_service.send_beta_invitation_email(
                to_email=email, base_url=base_url
            )

            if success:
                results["sent"].append(email)
                print("✅ Sent")
            else:
                results["failed"].append(email)
                print("❌ Failed (email service returned False)")

        except Exception as e:
            results["failed"].append(email)
            print(f"❌ Failed: {e}")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total: {len(emails)}")
    print(f"✅ Sent: {len(results['sent'])}")
    print(f"❌ Failed: {len(results['failed'])}")

    if results["sent"]:
        print("\n✅ Successfully sent to:")
        for email in results["sent"]:
            print(f"  - {email}")

    if results["failed"]:
        print("\n❌ Failed to send to:")
        for email in results["failed"]:
            print(f"  - {email}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Send beta invitation emails",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send to specific emails
  python send_beta_invitations.py user1@example.com user2@example.com

  # Send to emails from a file (one email per line)
  python send_beta_invitations.py --from-file emails.txt

  # Use custom base URL
  python send_beta_invitations.py --base-url https://my-app.com user@example.com
        """,
    )

    parser.add_argument(
        "emails", nargs="*", help="Email addresses to send invitations to"
    )

    parser.add_argument(
        "--from-file",
        "-f",
        type=str,
        help="Read email addresses from a file (one per line)",
    )

    parser.add_argument(
        "--base-url",
        "-u",
        type=str,
        default="https://emergence-app.ch",
        help="Base URL of the application (default: https://emergence-app.ch)",
    )

    args = parser.parse_args()

    # Collect emails
    emails = []

    if args.from_file:
        # Read from file
        try:
            with open(args.from_file, "r", encoding="utf-8") as f:
                file_emails = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
                emails.extend(file_emails)
            print(f"📄 Loaded {len(file_emails)} email(s) from {args.from_file}")
        except FileNotFoundError:
            print(f"❌ Error: File '{args.from_file}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            sys.exit(1)

    if args.emails:
        # Add emails from command line
        emails.extend(args.emails)

    # Remove duplicates while preserving order
    emails = list(dict.fromkeys(emails))

    if not emails:
        print("❌ No email addresses provided!")
        print("\nUsage:")
        print("  python send_beta_invitations.py email1@example.com email2@example.com")
        print("  python send_beta_invitations.py --from-file emails.txt")
        sys.exit(1)

    # Run async function
    asyncio.run(send_invitations(emails, args.base_url))


if __name__ == "__main__":
    main()
