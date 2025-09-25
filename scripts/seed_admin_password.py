import argparse
import asyncio
from pathlib import Path

from backend.core.database.manager import DatabaseManager
from backend.features.auth.service import AuthService, build_auth_config_from_env


async def seed_password(db_path: Path, email: str, password: str, role: str, note: str | None) -> None:
    db = DatabaseManager(str(db_path))
    await db.connect()
    config = build_auth_config_from_env()
    service = AuthService(db_manager=db, config=config)

    existing = await db.fetch_one(
        "SELECT role, note FROM auth_allowlist WHERE email = ?",
        (email,),
    )

    effective_role = role or (existing["role"] if existing else "admin")
    effective_note = note if note is not None else (existing["note"] if existing else "seed-script")

    try:
        await service.upsert_allowlist(
            email,
            role=effective_role,
            note=effective_note,
            actor="seed-script",
            password=password,
        )
    finally:
        await db.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or update an admin password in auth_allowlist.")
    parser.add_argument("--email", required=True, help="Email address to seed/update")
    parser.add_argument("--password", required=True, help="Plain password that will be hashed")
    parser.add_argument("--db", default="./data/emergence.db", help="Path to the SQLite database")
    parser.add_argument("--role", default="admin", help="Role to apply when creating the entry (default: admin)")
    parser.add_argument("--note", default=None, help="Optional note stored on the allowlist entry")
    args = parser.parse_args()

    email = args.email.strip().lower()
    if not email:
        raise SystemExit("--email must be provided")
    if not args.password or len(args.password) < 8:
        raise SystemExit("--password must contain at least 8 characters")

    db_path = Path(args.db).expanduser().resolve()
    asyncio.run(seed_password(db_path, email, args.password, args.role, args.note))
    print(f"[OK] Password updated for {email} in {db_path}")


if __name__ == "__main__":
    main()

