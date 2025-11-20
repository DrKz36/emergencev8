#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to fix admin role for current user
Updates the role to 'admin' in auth_allowlist table
"""

import sqlite3
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def fix_admin_role(db_path: str = "./data/emergence.db", email: str = None):
    """Set admin role for specified email or all users"""

    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ Database not found at: {db_path}")
        print("Looking for alternatives...")

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
        # First, let's see what users exist
        cursor.execute("SELECT email, role FROM auth_allowlist ORDER BY email")
        users = cursor.fetchall()

        if not users:
            print("❌ No users found in auth_allowlist table")
            return False

        print("\n📋 Current users in database:")
        for user_email, role in users:
            print(f"  - {user_email}: {role}")

        # Update role to admin
        if email:
            # Update specific email
            cursor.execute(
                "UPDATE auth_allowlist SET role = 'admin' WHERE email = ?",
                (email.lower().strip(),),
            )
            if cursor.rowcount == 0:
                print(f"\n❌ Email '{email}' not found in database")
                return False
            print(f"\n✅ Updated {email} to admin role")
        else:
            # Update all users to admin
            cursor.execute("UPDATE auth_allowlist SET role = 'admin'")
            print(f"\n✅ Updated {cursor.rowcount} user(s) to admin role")

        conn.commit()

        # Verify the update
        cursor.execute("SELECT email, role FROM auth_allowlist ORDER BY email")
        updated_users = cursor.fetchall()

        print("\n📋 Updated users:")
        for user_email, role in updated_users:
            emoji = "👑" if role == "admin" else "👤"
            print(f"  {emoji} {user_email}: {role}")

        print(
            "\n✅ Success! You need to log out and log back in for changes to take effect."
        )
        print("   The new JWT token will include the 'admin' role.")

        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix admin role in ÉMERGENCE database")
    parser.add_argument(
        "--email",
        type=str,
        help="Specific email to update (if not provided, updates all users)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./data/emergence.db",
        help="Path to database file (default: ./data/emergence.db)",
    )

    args = parser.parse_args()

    success = fix_admin_role(db_path=args.db, email=args.email)
    sys.exit(0 if success else 1)
