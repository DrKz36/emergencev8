import asyncio
import sys
from pathlib import Path


def _import_backend():
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from backend.core.database.manager import DatabaseManager

    return DatabaseManager


async def disable_password_reset(email: str, db_path: str):
    DatabaseManager = _import_backend()

    db = DatabaseManager(db_path)
    await db.connect()
    try:
        # Update password_must_reset to 0
        await db.execute(
            "UPDATE auth_allowlist SET password_must_reset = 0 WHERE email = ?",
            (email,),
        )

        # Verify the change
        result = await db.fetch_one(
            "SELECT email, role, password_must_reset FROM auth_allowlist WHERE email = ?",
            (email,),
        )

        if result:
            print(f"[OK] Password reset disabled for {result['email']}")
            print(f"     Role: {result['role']}")
            print(f"     password_must_reset: {result['password_must_reset']}")
        else:
            print(f"[ERROR] User {email} not found")

    finally:
        await db.disconnect()


if __name__ == "__main__":
    email = "gonzalefernando@gmail.com"
    db_path = "src/backend/data/db/emergence_v7.db"
    asyncio.run(disable_password_reset(email, db_path))
