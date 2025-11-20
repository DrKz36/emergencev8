#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check database schema for auth_allowlist table
"""

import sqlite3
import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def check_schema(db_path: str = "./data/emergence.db"):
    """Check and display schema of auth_allowlist table"""

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

    print(f"📂 Using database: {db_file}\n")

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    try:
        # Get table schema
        cursor.execute("PRAGMA table_info(auth_allowlist)")
        columns = cursor.fetchall()

        print("📋 auth_allowlist table schema:")
        print("-" * 80)
        print(f"{'Column':<30} {'Type':<15} {'Not Null':<10} {'Default':<15}")
        print("-" * 80)

        for col in columns:
            cid, name, type_, notnull, default, pk = col
            print(
                f"{name:<30} {type_:<15} {'YES' if notnull else 'NO':<10} {str(default) if default else '':<15}"
            )

        print("\n" + "=" * 80)

        # Check if password_must_reset exists
        has_password_must_reset = any(
            col[1] == "password_must_reset" for col in columns
        )

        if has_password_must_reset:
            print("✅ Column 'password_must_reset' EXISTS")
        else:
            print("❌ Column 'password_must_reset' MISSING")
            print("\n💡 This column needs to be added via migration!")

        # Show sample data
        print("\n📊 Sample data from auth_allowlist:")
        print("-" * 80)
        cursor.execute("SELECT * FROM auth_allowlist LIMIT 3")
        rows = cursor.fetchall()

        if rows:
            col_names = [desc[0] for desc in cursor.description]
            print(" | ".join(col_names))
            print("-" * 80)
            for row in rows:
                print(
                    " | ".join(str(val) if val is not None else "NULL" for val in row)
                )
        else:
            print("(No data)")

        return True

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    check_schema()
