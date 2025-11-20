"""
Migration script to add password_reset_tokens table
Run this to add support for password reset functionality
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.core.database.manager import DatabaseManager


async def add_password_reset_table():
    """Add password_reset_tokens table to the database"""
    db_path = Path(__file__).parent.parent / "emergence.db"
    db = DatabaseManager(str(db_path))
    await db.initialize()

    print("Adding password_reset_tokens table...")

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            used_at TEXT,
            FOREIGN KEY (email) REFERENCES auth_allowlist(email) ON DELETE CASCADE
        )
        """,
        commit=True,
    )

    print("Creating index on email...")
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_email
        ON password_reset_tokens(email)
        """,
        commit=True,
    )

    print("Creating index on expires_at...")
    await db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at
        ON password_reset_tokens(expires_at)
        """,
        commit=True,
    )

    print("Password reset tokens table created successfully!")

    await db.close()


if __name__ == "__main__":
    asyncio.run(add_password_reset_table())
