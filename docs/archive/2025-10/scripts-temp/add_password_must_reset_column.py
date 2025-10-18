#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration script to add password_must_reset column to auth_allowlist table
and set it to False for admin users, True for others
"""
import sqlite3
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def migrate_password_must_reset(db_path: str = "./data/emergence.db"):
    """Add password_must_reset column and configure it properly"""

    db_file = Path(db_path)
    if not db_file.exists():
        alternatives = [
            Path("emergence.db"),
            Path("data/emergence.db"),
            Path("src/backend/data/db/emergence_v7.db"),
        ]

        for alt in alternatives:
            if alt.exists():
                db_file = alt
                break
        else:
            print("❌ No database file found!")
            return False

    print(f"\n📂 Using database: {db_file}")

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(auth_allowlist)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if 'password_must_reset' in column_names:
            print("⚠️  Column 'password_must_reset' already exists")
        else:
            print("➕ Adding column 'password_must_reset' to auth_allowlist table...")

            # Add the column with default value TRUE (1)
            cursor.execute(
                """
                ALTER TABLE auth_allowlist
                ADD COLUMN password_must_reset INTEGER NOT NULL DEFAULT 1
                """
            )
            conn.commit()
            print("✅ Column added successfully")

        # Now, set password_must_reset = 0 for admin users
        print("\n🔧 Configuring password_must_reset for users...")

        # Get current status
        cursor.execute(
            """
            SELECT email, role, password_must_reset
            FROM auth_allowlist
            ORDER BY role DESC, email
            """
        )
        users_before = cursor.fetchall()

        print("\n📋 Users BEFORE update:")
        for email, role, must_reset in users_before:
            emoji = "👑" if role == "admin" else "👤"
            status = "🔒 MUST RESET" if must_reset else "✅ NO RESET"
            print(f"  {emoji} {email:<40} {role:<10} {status}")

        # Update admin users to NOT require password reset
        cursor.execute(
            """
            UPDATE auth_allowlist
            SET password_must_reset = 0
            WHERE role = 'admin'
            """
        )

        admin_count = cursor.rowcount

        # Keep other users at default (1 = TRUE)
        # (No action needed, they already have the default value)

        conn.commit()

        # Verify the changes
        cursor.execute(
            """
            SELECT email, role, password_must_reset
            FROM auth_allowlist
            ORDER BY role DESC, email
            """
        )
        users_after = cursor.fetchall()

        print("\n📋 Users AFTER update:")
        for email, role, must_reset in users_after:
            emoji = "👑" if role == "admin" else "👤"
            status = "🔒 MUST RESET" if must_reset else "✅ NO RESET"
            print(f"  {emoji} {email:<40} {role:<10} {status}")

        print(f"\n✅ Migration completed successfully!")
        print(f"   - {admin_count} admin user(s) set to NOT require password reset")
        print(f"   - Admin users can now login without forced password change")

        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Add password_must_reset column to ÉMERGENCE database"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./data/emergence.db",
        help="Path to database file (default: ./data/emergence.db)",
    )

    args = parser.parse_args()

    success = migrate_password_must_reset(db_path=args.db)
    sys.exit(0 if success else 1)
