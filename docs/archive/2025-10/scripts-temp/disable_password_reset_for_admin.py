#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to disable password_must_reset for admin users
"""
import sqlite3
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def disable_password_reset_for_admins(db_path: str = "./data/emergence.db"):
    """Disable password_must_reset for all admin users"""

    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ Database not found at: {db_path}")
        print(f"Looking for alternatives...")

        # Try alternate locations
        alternatives = [
            Path("emergence.db"),
            Path("data/emergence.db"),
            Path("src/backend/data/db/emergence_v7.db"),
        ]

        for alt in alternatives:
            if alt.exists():
                db_file = alt
                print(f"✓ Found database at: {alt}")
                break
        else:
            print("❌ No database file found!")
            return False

    print(f"\n📂 Using database: {db_file}")

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    try:
        # First, let's see admin users and their password_must_reset status
        cursor.execute(
            """
            SELECT email, role, password_must_reset
            FROM auth_allowlist
            WHERE role = 'admin'
            ORDER BY email
            """
        )
        admins = cursor.fetchall()

        if not admins:
            print("❌ No admin users found in database")
            return False

        print(f"\n📋 Admin users before update:")
        for email, role, must_reset in admins:
            status = "🔒 MUST RESET" if must_reset else "✅ NO RESET"
            print(f"  {status} - {email}")

        # Update all admin users to set password_must_reset = False
        cursor.execute(
            """
            UPDATE auth_allowlist
            SET password_must_reset = 0
            WHERE role = 'admin'
            """
        )

        updated_count = cursor.rowcount
        conn.commit()

        # Verify the update
        cursor.execute(
            """
            SELECT email, role, password_must_reset
            FROM auth_allowlist
            WHERE role = 'admin'
            ORDER BY email
            """
        )
        updated_admins = cursor.fetchall()

        print(f"\n📋 Admin users after update:")
        for email, role, must_reset in updated_admins:
            status = "🔒 MUST RESET" if must_reset else "✅ NO RESET"
            print(f"  {status} - {email}")

        print(f"\n✅ Success! Updated {updated_count} admin user(s)")
        print(f"   Admin users will no longer be forced to reset their password.")

        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Disable password reset requirement for admin users in ÉMERGENCE"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./data/emergence.db",
        help="Path to database file (default: ./data/emergence.db)",
    )

    args = parser.parse_args()

    success = disable_password_reset_for_admins(db_path=args.db)
    sys.exit(0 if success else 1)
