"""
Migration script to add password_must_reset field to auth_allowlist
This field tracks if user needs to reset their password on first login
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.core.database.manager import DatabaseManager


async def add_password_must_reset_field():
    """Add password_must_reset field to auth_allowlist table"""
    db_path = Path(__file__).parent.parent / "emergence.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    print("Adding password_must_reset field to auth_allowlist...")

    # Add column (SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS directly)
    try:
        await db.execute(
            """
            ALTER TABLE auth_allowlist
            ADD COLUMN password_must_reset INTEGER DEFAULT 1
            """,
            commit=True,
        )
        print("Column added successfully!")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("Column already exists, skipping...")
        else:
            raise

    # Set password_must_reset to 0 for existing users who already have a password
    print("Updating existing users with passwords...")
    await db.execute(
        """
        UPDATE auth_allowlist
        SET password_must_reset = 0
        WHERE password_hash IS NOT NULL AND password_hash != ''
        """,
        commit=True,
    )

    # Explicitly set to 0 for admin and test user
    print("Exempting admin and test user (fernando36@bluewin.ch)...")
    await db.execute(
        """
        UPDATE auth_allowlist
        SET password_must_reset = 0
        WHERE email IN (
            SELECT email FROM auth_allowlist WHERE role = 'admin'
        ) OR email = 'fernando36@bluewin.ch'
        """,
        commit=True,
    )

    print("Migration completed successfully!")

    await db.close()


if __name__ == "__main__":
    asyncio.run(add_password_must_reset_field())
