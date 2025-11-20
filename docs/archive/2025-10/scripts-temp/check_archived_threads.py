#!/usr/bin/env python3
"""Check archived threads in database"""

import asyncio
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager


async def main():
    db = DatabaseManager("backend/data/db/emergence_v7.db")
    await db.connect()

    # Schema de la table threads
    schema = await db.fetch_all("PRAGMA table_info(threads)")
    print("=" * 70)
    print("SCHEMA TABLE THREADS:")
    print("=" * 70)
    for col in schema:
        print(f"  {col[1]} ({col[2]})")

    # Chercher les threads archivés
    archived_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM threads WHERE archived = 1"
    )
    print(f"\nThreads archives: {archived_count[0] if archived_count else 0}")

    # Threads archivés avec détails
    threads = await db.fetch_all("""
        SELECT id, user_id, title, archived_at, meta
        FROM threads
        WHERE archived = 1
        ORDER BY archived_at DESC
        LIMIT 10
    """)

    print(f"\nDetails des {len(threads)} derniers threads archives:")
    print("-" * 70)
    for i, t in enumerate(threads, 1):
        thread_id = t[0]
        title = t[2] or "Sans titre"
        archived_at = t[3]
        meta = t[4]

        # Compter les messages du thread
        msg_count = await db.fetch_one(
            "SELECT COUNT(*) FROM messages WHERE thread_id = ?", (thread_id,)
        )

        print(f"{i}. {thread_id[:12]}... '{title[:40]}'")
        print(f"   Messages: {msg_count[0] if msg_count else 0}")
        print(f"   Archive: {archived_at}")
        print()

    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
