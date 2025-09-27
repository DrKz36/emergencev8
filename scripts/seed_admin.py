import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from backend.core.database.manager import DatabaseManager
from backend.features.auth.service import AuthService, build_auth_config_from_env

DEFAULT_EMAIL = "gonzalefernando@gmail.com"
DEFAULT_PASSWORD = "WinipegMad2015"
DEFAULT_ROLE = "admin"
DEFAULT_NOTE = "seed-admin"
DEFAULT_DB_PATH = "src/backend/data/db/emergence_v7.db"


async def _seed_admin(db_path: Path, email: str, password: str, role: str, note: str | None) -> None:
    db = DatabaseManager(str(db_path))
    await db.connect()
    try:
        config = build_auth_config_from_env()
        service = AuthService(db_manager=db, config=config)
        await service.upsert_allowlist(
            email,
            role=role or DEFAULT_ROLE,
            note=note if note is not None else DEFAULT_NOTE,
            actor="seed-admin",
            password=password,
        )
    finally:
        await db.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create or update the default admin account in auth_allowlist. "
            "Defaults can be overridden with CLI flags or environment variables."
        )
    )
    parser.add_argument(
        "--email",
        default=os.getenv("EMERGENCE_ADMIN_EMAIL", DEFAULT_EMAIL),
        help="Admin email to seed (default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("EMERGENCE_ADMIN_PASSWORD", DEFAULT_PASSWORD),
        help="Plain password that will be hashed (default provided by spec)",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("EMERGENCE_DB_PATH", DEFAULT_DB_PATH),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--role",
        default=os.getenv("EMERGENCE_ADMIN_ROLE", DEFAULT_ROLE),
        help="Role to apply for the admin entry (default: %(default)s)",
    )
    parser.add_argument(
        "--note",
        default=os.getenv("EMERGENCE_ADMIN_NOTE", DEFAULT_NOTE),
        help="Optional note stored alongside the allowlist entry",
    )
    args = parser.parse_args()

    email = (args.email or "").strip().lower()
    if not email:
        raise SystemExit("--email must not be empty")

    password = (args.password or "").strip()
    if len(password) < 8:
        raise SystemExit("--password must contain at least 8 characters")

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"[seed-admin] Warning: database file {db_path} does not exist yet. It will be created if possible.")

    role = (args.role or DEFAULT_ROLE).strip().lower() or DEFAULT_ROLE

    asyncio.run(_seed_admin(db_path, email, password, role, args.note))
    print(f"[seed-admin] Admin account ready for {email} (role={role}).")


if __name__ == "__main__":
    main()
